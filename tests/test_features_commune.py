"""Tests for the point-in-time commune feature builder."""

from __future__ import annotations

import json
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
import yaml

from pomap.features.commune import (
    FEATURES_COMMUNE_COLUMNS,
    build_features_commune,
    load_feature_config,
)


def _write_zip_csv(path: Path, member: str, frame: pd.DataFrame) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(member, frame.to_csv(sep=";", index=False))


def _config(tmp_path: Path) -> Path:
    population = tmp_path / "population.zip"
    housing = tmp_path / "housing.zip"
    transactions = tmp_path / "transactions.parquet"
    _write_zip_csv(
        population,
        "population.csv",
        pd.DataFrame(
            {
                "CODGEO": ["34001", "34002"],
                "P21_POP": [1000, 200],
                "P21_POP1529": [100, 20],
                "P21_POP3044": [50, 30],
                "P21_POP4559": [50, 20],
            }
        ),
    )
    _write_zip_csv(
        housing,
        "housing.csv",
        pd.DataFrame({"CODGEO": ["34001", "34002"], "P21_LOG": [500, 100], "P21_LOGVAC": [25, 20]}),
    )
    pd.DataFrame(
        {
            "date_mutation": ["2023-01-01", "2023-02-01", "2024-01-01"],
            "price_per_m2": [2000.0, 3000.0, 4000.0],
            "code_commune": ["34001", "34001", "34002"],
            "known_as_of": [date(2024, 7, 1), date(2024, 7, 1), date(2025, 7, 1)],
        }
    ).to_parquet(transactions, index=False)
    config = {
        "features_commune": {
            "transactions_path": str(transactions),
            "output_path": str(tmp_path / "features.parquet"),
            "transaction_date_column": "date_mutation",
            "transaction_price_column": "price_per_m2",
            "transaction_commune_column": "code_commune",
            "transaction_known_as_of_column": "known_as_of",
            "strict_demographic_coverage": True,
            "insee": {
                "reference_year": 2021,
                "known_as_of": "2024-06-27",
                "download_timeout_seconds": 1,
                "population": {
                    "path": str(population),
                    "url": "https://example.invalid/population.zip",
                    "archive_member": "population.csv",
                    "commune_column": "CODGEO",
                    "population_column": "P21_POP",
                    "working_age_columns": ["P21_POP1529", "P21_POP3044", "P21_POP4559"],
                    "working_age_definition": "population_15_59_share",
                },
                "housing": {
                    "path": str(housing),
                    "url": "https://example.invalid/housing.zip",
                    "archive_member": "housing.csv",
                    "commune_column": "CODGEO",
                    "dwellings_column": "P21_LOG",
                    "vacant_dwellings_column": "P21_LOGVAC",
                    "vacancy_rate_unit": "percent",
                },
            },
        }
    }
    config_path = tmp_path / "indicators.yml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return config_path


def test_build_features_commune_matches_schema_and_tracks_availability(tmp_path: Path):
    features = build_features_commune(load_feature_config(_config(tmp_path)))

    assert list(features.columns) == FEATURES_COMMUNE_COLUMNS
    assert features[["unit_id", "vintage"]].to_dict("records") == [
        {"unit_id": "34001", "vintage": 2023},
        {"unit_id": "34002", "vintage": 2024},
    ]
    assert features.loc[0, "population"] == 1000
    assert features.loc[0, "working_age_share"] == pytest.approx(0.2)
    assert features.loc[0, "vacancy_rate"] == pytest.approx(5.0)
    assert features.loc[0, "median_price_m2"] == pytest.approx(2500.0)
    assert features.loc[0, "annual_transactions"] == 2
    assert features["known_as_of"].tolist() == [date(2024, 7, 1), date(2025, 7, 1)]
    assert all(json.loads(value)["insee_population"]["reference_year"] == 2021 for value in features.source_refs)


def test_build_features_commune_rejects_null_transaction_availability(tmp_path: Path):
    config = load_feature_config(_config(tmp_path))
    transactions = pd.read_parquet(config["transactions_path"])
    transactions.loc[0, "known_as_of"] = pd.NaT
    transactions.to_parquet(config["transactions_path"], index=False)

    with pytest.raises(ValueError, match="known_as_of"):
        build_features_commune(config)
