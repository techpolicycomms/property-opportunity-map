"""Export a descriptive commune snapshot GeoJSON for the web viewer.

This is NOT the Gate-C scores export (see export_geojson.py): it carries no
forecasts and no opportunity score, because no model has survived Gate B yet.
It exists so the public map shows real, honestly-labelled descriptive data
(real DVF median prices, transaction counts, INSEE demographics) instead of
synthetic sample points while the modelling stages are incomplete.

Coordinates are the median location of a commune's geocoded transactions —
an approximation of the commune centroid, labelled as such in the output.
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

COLUMNS = [
    "unit_id",
    "vintage",
    "median_price_m2",
    "annual_transactions",
    "population",
    "working_age_share",
    "vacancy_rate",
    "known_as_of",
    "lon",
    "lat",
]


def build_snapshot(features: pd.DataFrame, transactions: pd.DataFrame, vintage: int | None) -> pd.DataFrame:
    """Join latest-vintage commune features to median transaction locations."""
    if vintage is None:
        vintage = int(features["vintage"].max())
    frame = features[features["vintage"] == vintage].copy()
    log.info("vintage %s: %d communes", vintage, len(frame))

    located = transactions.dropna(subset=["lon", "lat"])
    centroids = (
        located.groupby("code_commune")[["lon", "lat"]]
        .median()
        .reset_index()
        .rename(columns={"code_commune": "unit_id"})
    )
    frame = frame.merge(centroids, on="unit_id", how="inner", validate="one_to_one")
    dropped = len(features[features["vintage"] == vintage]) - len(frame)
    if dropped:
        log.info("%d communes without geocoded transactions excluded", dropped)

    for col in ("median_price_m2", "population", "working_age_share", "vacancy_rate"):
        frame[col] = pd.to_numeric(frame[col], errors="coerce").round(2)
    frame["annual_transactions"] = frame["annual_transactions"].astype(int)
    frame["vintage"] = frame["vintage"].astype(int)
    return frame[COLUMNS].sort_values("unit_id").reset_index(drop=True)


def to_geojson(frame: pd.DataFrame) -> dict:
    features = []
    for row in frame.itertuples(index=False):
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [row.lon, row.lat]},
                "properties": {
                    "unit_id": row.unit_id,
                    "vintage": row.vintage,
                    "median_price_m2": row.median_price_m2,
                    "annual_transactions": row.annual_transactions,
                    "population": row.population,
                    "working_age_share": row.working_age_share,
                    "vacancy_rate": row.vacancy_rate,
                    "known_as_of": str(row.known_as_of),
                    "location_note": "median of geocoded transactions, not the official centroid",
                },
            }
        )
    return {
        "type": "FeatureCollection",
        "name": "descriptive commune snapshot — real data, NOT model scores",
        "generated_on": str(datetime.now(UTC).date()),
        "features": features,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=Path("data/processed/features_commune_34.parquet"))
    parser.add_argument("--transactions", type=Path, default=Path("data/interim/transactions/transactions_34.parquet"))
    parser.add_argument("--vintage", type=int, default=None, help="default: latest in the features table")
    parser.add_argument("--out", type=Path, default=Path("web/data/communes.geojson"))
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    frame = build_snapshot(pd.read_parquet(args.features), pd.read_parquet(args.transactions), args.vintage)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(to_geojson(frame), ensure_ascii=False), encoding="utf-8")
    log.info("wrote %d communes → %s", len(frame), args.out)


if __name__ == "__main__":
    main()
