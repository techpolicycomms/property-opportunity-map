"""Ingestion of French DVF (Demandes de Valeurs Foncières) transactions.

Produces the canonical ``transactions`` table (docs/data-dictionary.md).

Sources (see config/data_sources.yml — Gate A):
  * Geolocated DVF ("DVF géolocalisé") on data.gouv.fr, queried via its API.
  * Fallback: Etalab geo-dvf CSV mirrors on files.data.gouv.fr.

NOTE: resource URLs on data.gouv.fr change over time. The first real run must
verify them and record the outcome in an agent-handoffs note (AGENTS.md §7,
issue 1). Nothing here is considered verified until then.
"""

from __future__ import annotations

import argparse
import gzip
import io
import logging
from pathlib import Path

import pandas as pd
import requests

log = logging.getLogger(__name__)

DATASET_API = "https://www.data.gouv.fr/api/1/datasets/demandes-de-valeurs-foncieres-geolocalisees/"
# Best-effort mirror pattern — UNVERIFIED, see module docstring.
GEO_DVF_MIRROR = "https://files.data.gouv.fr/geo-dvf/latest/csv/{year}/departements/{dept}.csv.gz"

RAW_DIR = Path("data/raw/dvf")
INTERIM_DIR = Path("data/interim/transactions")

MIN_SURFACE_M2 = 9.0  # DVF hygiene: drop sub-9 m² lots (parking, cellars)


def find_resources(years: list[int]) -> list[dict]:
    """List candidate download resources for the geolocated DVF dataset."""
    resp = requests.get(DATASET_API, timeout=60)
    resp.raise_for_status()
    resources = resp.json().get("resources", [])
    out = []
    for r in resources:
        title = (r.get("title") or "") + " " + (r.get("url") or "")
        if any(str(y) in title for y in years):
            out.append({"title": r.get("title"), "url": r.get("url"), "format": r.get("format")})
    return out


def download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        log.info("cached: %s", dest)
        return dest
    log.info("downloading %s", url)
    resp = requests.get(url, timeout=600, stream=True)
    resp.raise_for_status()
    with open(dest, "wb") as fh:
        for chunk in resp.iter_content(chunk_size=1 << 20):
            fh.write(chunk)
    return dest


def read_dvf_file(path: Path) -> pd.DataFrame:
    """Read a DVF CSV / CSV.GZ / Parquet file into a DataFrame."""
    name = path.name.lower()
    if name.endswith(".parquet"):
        return pd.read_parquet(path)
    opener = gzip.open if name.endswith(".gz") else open
    with opener(path, "rb") as fh:  # type: ignore[arg-type]
        return pd.read_csv(io.BytesIO(fh.read()), low_memory=False)


def clean_dvf(df: pd.DataFrame) -> pd.DataFrame:
    """Standard DVF hygiene → canonical ``transactions`` columns.

    Keeps residential sales of houses/apartments with a usable surface and
    value, computes price_per_m2, and drops exact duplicate mutation rows.
    """
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]

    required = {"id_mutation", "date_mutation", "valeur_fonciere"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"input is missing required DVF columns: {sorted(missing)}")

    if "nature_mutation" in df.columns:
        df = df[df["nature_mutation"].isin(["Vente", "Vente en l'état futur d'achèvement"])]
    if "type_local" in df.columns:
        df = df[df["type_local"].isin(["Maison", "Appartement"])]

    df["valeur_fonciere"] = pd.to_numeric(df["valeur_fonciere"], errors="coerce")
    df["surface_reelle_bati"] = pd.to_numeric(df.get("surface_reelle_bati"), errors="coerce")
    df = df[(df["valeur_fonciere"] > 0) & (df["surface_reelle_bati"] > MIN_SURFACE_M2)]

    df["price_per_m2"] = df["valeur_fonciere"] / df["surface_reelle_bati"]
    # Outlier guard: keep the broad plausible band; tails are audited, not modelled raw.
    df = df[df["price_per_m2"].between(100, 100_000)]

    df = df.drop_duplicates(subset=["id_mutation", "type_local", "surface_reelle_bati"])
    df["date_mutation"] = pd.to_datetime(df["date_mutation"], errors="coerce").dt.date
    return df.reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--department", required=True, help="e.g. 34 for Hérault")
    parser.add_argument("--years", nargs="+", type=int, required=True)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    frames = []
    for year in args.years:
        url = GEO_DVF_MIRROR.format(year=year, dept=args.department)
        dest = RAW_DIR / f"dvf_{args.department}_{year}.csv.gz"
        try:
            path = download(url, dest)
        except requests.HTTPError:
            log.warning(
                "mirror miss for %s/%s — falling back to data.gouv API resource listing "
                "(see module docstring: URLs must be verified on first run)",
                args.department,
                year,
            )
            resources = find_resources([year])
            if not resources:
                raise SystemExit(f"no DVF resources found for {year}; update data_sources.yml")
            log.info("candidate resources: %s", [r["title"] for r in resources])
            path = download(resources[0]["url"], RAW_DIR / f"dvf_{year}_{resources[0]['title']}")
        frames.append(read_dvf_file(path))

    cleaned = clean_dvf(pd.concat(frames, ignore_index=True))
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    out = INTERIM_DIR / f"transactions_{args.department}.parquet"
    cleaned.to_parquet(out, index=False)
    log.info("wrote %d rows → %s", len(cleaned), out)


if __name__ == "__main__":
    main()
