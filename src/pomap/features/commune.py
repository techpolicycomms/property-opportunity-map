"""Build the point-in-time ``features_commune`` table for France.

The table is restricted to communes represented in the configured canonical
``transactions`` Parquet file.  INSEE releases are cached under ``data/raw``;
their URLs, field mappings, and release date are configuration, not code.
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import zipfile
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import yaml

log = logging.getLogger(__name__)

FEATURES_COMMUNE_COLUMNS = [
    "unit_id",
    "vintage",
    "population",
    "working_age_share",
    "vacancy_rate",
    "median_price_m2",
    "annual_transactions",
    "known_as_of",
    "source_refs",
]


def load_feature_config(path: str | Path) -> dict[str, Any]:
    """Load the ``features_commune`` block from the indicators configuration."""
    with Path(path).open(encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    try:
        return config["features_commune"]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"{path} has no features_commune configuration") from exc


def _download_if_missing(url: str, path: Path, timeout_seconds: int) -> Path:
    """Download a configured INSEE archive only when no local cache exists."""
    if path.exists() and path.stat().st_size > 0:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    log.info("downloading %s", url)
    response = requests.get(url, timeout=timeout_seconds)
    response.raise_for_status()
    path.write_bytes(response.content)
    return path


def _read_insee_zip(
    spec: dict[str, Any], *, timeout_seconds: int, usecols: list[str]
) -> pd.DataFrame:
    """Read configured semicolon-delimited INSEE fields from a ZIP archive."""
    archive_path = _download_if_missing(spec["url"], Path(spec["path"]), timeout_seconds)
    with zipfile.ZipFile(archive_path) as archive:
        member = spec["archive_member"]
        try:
            with archive.open(member) as source:
                return pd.read_csv(
                    io.TextIOWrapper(source, encoding="utf-8"),
                    sep=";",
                    decimal=",",
                    usecols=usecols,
                    dtype={spec["commune_column"]: "string"},
                )
        except KeyError as exc:
            raise ValueError(f"{archive_path} does not contain configured member {member}") from exc


def load_insee_demographics(config: dict[str, Any]) -> pd.DataFrame:
    """Load population, working-age proxy, and vacancy rate by commune."""
    insee = config["insee"]
    timeout_seconds = int(insee["download_timeout_seconds"])
    population_spec = insee["population"]
    housing_spec = insee["housing"]

    population_columns = [
        population_spec["commune_column"],
        population_spec["population_column"],
        *population_spec["working_age_columns"],
    ]
    population = _read_insee_zip(
        population_spec, timeout_seconds=timeout_seconds, usecols=population_columns
    ).rename(columns={population_spec["commune_column"]: "unit_id"})

    housing_columns = [
        housing_spec["commune_column"],
        housing_spec["dwellings_column"],
        housing_spec["vacant_dwellings_column"],
    ]
    housing = _read_insee_zip(
        housing_spec, timeout_seconds=timeout_seconds, usecols=housing_columns
    ).rename(columns={housing_spec["commune_column"]: "unit_id"})

    population["unit_id"] = population["unit_id"].astype("string")
    housing["unit_id"] = housing["unit_id"].astype("string")
    if population["unit_id"].duplicated().any() or housing["unit_id"].duplicated().any():
        raise ValueError("configured INSEE source has duplicate commune codes")

    numeric_columns = [
        population_spec["population_column"],
        *population_spec["working_age_columns"],
    ]
    for column in numeric_columns:
        population[column] = pd.to_numeric(population[column], errors="coerce")
    for column in (housing_spec["dwellings_column"], housing_spec["vacant_dwellings_column"]):
        housing[column] = pd.to_numeric(housing[column], errors="coerce")

    demographics = population[["unit_id", population_spec["population_column"]]].copy()
    demographics = demographics.rename(columns={population_spec["population_column"]: "population"})
    demographics["working_age_share"] = (
        population[population_spec["working_age_columns"]].sum(axis=1, min_count=1)
        / demographics["population"]
    )
    demographics = demographics.merge(
        housing[
            [
                "unit_id",
                housing_spec["dwellings_column"],
                housing_spec["vacant_dwellings_column"],
            ]
        ],
        on="unit_id",
        how="inner",
        validate="one_to_one",
    )
    demographics["vacancy_rate"] = (
        demographics[housing_spec["vacant_dwellings_column"]]
        / demographics[housing_spec["dwellings_column"]]
    )
    if housing_spec["vacancy_rate_unit"] == "percent":
        demographics["vacancy_rate"] *= 100
    elif housing_spec["vacancy_rate_unit"] != "fraction":
        raise ValueError("vacancy_rate_unit must be percent or fraction")

    return demographics[["unit_id", "population", "working_age_share", "vacancy_rate"]]


def aggregate_transactions(config: dict[str, Any]) -> pd.DataFrame:
    """Calculate annual transaction counts and median prices by commune."""
    path = Path(config["transactions_path"])
    transactions = pd.read_parquet(path)
    date_column = config["transaction_date_column"]
    price_column = config["transaction_price_column"]
    commune_column = config["transaction_commune_column"]
    known_column = config["transaction_known_as_of_column"]
    required = {date_column, price_column, commune_column, known_column}
    missing = required - set(transactions.columns)
    if missing:
        raise ValueError(f"transactions input lacks columns: {sorted(missing)}")

    transactions = transactions[[date_column, price_column, commune_column, known_column]].copy()
    transactions[date_column] = pd.to_datetime(transactions[date_column], errors="coerce")
    transactions[known_column] = pd.to_datetime(transactions[known_column], errors="coerce")
    transactions[price_column] = pd.to_numeric(transactions[price_column], errors="coerce")
    transactions[commune_column] = transactions[commune_column].astype("string")
    if transactions[[date_column, price_column, commune_column, known_column]].isna().any().any():
        raise ValueError("transactions input has null dates, prices, commune codes, or known_as_of")

    transactions["vintage"] = transactions[date_column].dt.year.astype("int64")
    grouped = (
        transactions.groupby([commune_column, "vintage"], as_index=False)
        .agg(
            median_price_m2=(price_column, "median"),
            annual_transactions=(price_column, "size"),
            transactions_known_as_of=(known_column, "max"),
        )
        .rename(columns={commune_column: "unit_id"})
    )
    return grouped


def _source_refs(config: dict[str, Any]) -> str:
    """Return deterministic per-row source provenance as JSON."""
    insee = config["insee"]
    population = insee["population"]
    housing = insee["housing"]
    return json.dumps(
        {
            "transactions": {"path": config["transactions_path"], "aggregation": "annual commune median/count"},
            "demographic_commune_code_aliases": config.get("demographic_commune_code_aliases", {}),
            "insee_population": {
                "url": population["url"],
                "reference_year": insee["reference_year"],
                "known_as_of": insee["known_as_of"],
                "working_age_definition": population["working_age_definition"],
            },
            "insee_housing": {
                "url": housing["url"],
                "reference_year": insee["reference_year"],
                "known_as_of": insee["known_as_of"],
            },
        },
        sort_keys=True,
    )


def build_features_commune(config: dict[str, Any]) -> pd.DataFrame:
    """Assemble and validate the canonical commune feature rows."""
    transactions = aggregate_transactions(config)
    demographics = load_insee_demographics(config)
    aliases = config.get("demographic_commune_code_aliases", {})
    transactions["_demographics_unit_id"] = transactions["unit_id"].replace(aliases)
    features = transactions.merge(
        demographics,
        left_on="_demographics_unit_id",
        right_on="unit_id",
        how="left",
        validate="many_to_one",
        suffixes=("", "_insee"),
    )
    if config["strict_demographic_coverage"] and features[
        ["population", "working_age_share", "vacancy_rate"]
    ].isna().any().any():
        missing_codes = sorted(features.loc[features["population"].isna(), "unit_id"].unique())
        raise ValueError(f"INSEE demographics missing for transaction communes: {missing_codes}")

    insee_known_as_of = pd.Timestamp(insee_date(config["insee"]["known_as_of"]))
    features["known_as_of"] = features["transactions_known_as_of"].where(
        features["transactions_known_as_of"] >= insee_known_as_of, insee_known_as_of
    ).dt.date
    features["source_refs"] = _source_refs(config)
    features = features.drop(columns=["transactions_known_as_of", "_demographics_unit_id", "unit_id_insee"])
    features = features[FEATURES_COMMUNE_COLUMNS].sort_values(["unit_id", "vintage"]).reset_index(drop=True)
    if features["known_as_of"].isna().any():
        raise ValueError("features_commune rows must all carry known_as_of")
    return features


def insee_date(value: str | date) -> date:
    """Parse a configured INSEE publication date without using runtime time."""
    parsed = pd.Timestamp(value)
    if pd.isna(parsed):
        raise ValueError("insee.known_as_of must be a valid date")
    return parsed.date()


def write_features_commune(config: dict[str, Any]) -> tuple[Path, pd.DataFrame]:
    """Build the table and write it to the configured Parquet destination."""
    features = build_features_commune(config)
    output = Path(config["output_path"])
    output.parent.mkdir(parents=True, exist_ok=True)
    features.to_parquet(output, index=False)
    return output, features


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/indicators.yml")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    config = load_feature_config(args.config)
    output, features = write_features_commune(config)
    log.info("wrote %d feature rows to %s", len(features), output)


if __name__ == "__main__":
    main()
