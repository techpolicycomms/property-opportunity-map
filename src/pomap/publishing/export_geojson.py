"""Export the ``scores`` table to GeoJSON for the web viewer (agent:publish).

Gate C (AGENTS.md): export refuses to write rows that lack uncertainty
intervals, driver explanations, or known_as_of.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import geopandas as gpd
import pandas as pd

log = logging.getLogger(__name__)

REQUIRED_COLUMNS = {
    "unit_id",
    "known_as_of",
    "median_price_m2",
    "annual_transactions",
    "pred_cagr_10y_p10",
    "pred_cagr_10y_p50",
    "pred_cagr_10y_p90",
    "expected_excess_return_10y",
    "opportunity_score",
    "drivers_positive",
    "drivers_risk",
    "lon",
    "lat",
}


def scores_to_geodataframe(scores: pd.DataFrame) -> gpd.GeoDataFrame:
    missing = REQUIRED_COLUMNS - set(scores.columns)
    if missing:
        raise ValueError(f"scores table missing Gate-C columns: {sorted(missing)}")
    incomplete = scores[scores[list(REQUIRED_COLUMNS - {"lon", "lat"})].isna().any(axis=1)]
    if len(incomplete):
        raise ValueError(f"{len(incomplete)} rows lack mandatory fields (Gate C); fix or filter first")
    return gpd.GeoDataFrame(
        scores,
        geometry=gpd.points_from_xy(scores["lon"], scores["lat"]),
        crs="EPSG:4326",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scores", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    gdf = scores_to_geodataframe(pd.read_parquet(args.scores))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(args.out, driver="GeoJSON")
    log.info("wrote %d features → %s", len(gdf), args.out)


if __name__ == "__main__":
    main()
