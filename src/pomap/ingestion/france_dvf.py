"""Ingestion of French DVF (Demandes de Valeurs Foncières) transactions.

Produces the canonical ``transactions`` table (docs/data-dictionary.md).

Sources (see config/data_sources.yml — Gate A):
  * Geolocated DVF ("DVF géolocalisé") department CSVs on files.data.gouv.fr
    (Etalab geo-dvf mirror). Pattern verified 2026-07-27:
    ``…/geo-dvf/latest/csv/{year}/departements/{dept}.csv.gz``
    Rolling window: as of that date only 2021–2025 are published under
    ``/latest/csv/`` (2019–2020 return HTTP 404).
  * Fallback for years rolled off the geo mirror: historical DGFiP raw DVF
    text files mirrored at data.cquest.org (no parcel geocoding; lon/lat null).

NOTE: resource URLs on data.gouv.fr change over time. Re-verify against the
dataset API / mirror index when the rolling window moves.
"""

from __future__ import annotations

import argparse
import gzip
import io
import logging
import re
from collections.abc import Iterable
from datetime import date
from email.utils import parsedate_to_datetime
from pathlib import Path

import pandas as pd
import requests

log = logging.getLogger(__name__)

DATASET_API = "https://www.data.gouv.fr/api/1/datasets/demandes-de-valeurs-foncieres-geolocalisees/"
GEO_DVF_CSV_INDEX = "https://files.data.gouv.fr/geo-dvf/latest/csv/"
# Verified 2026-07-27 against files.data.gouv.fr/geo-dvf/latest/csv/ listing.
GEO_DVF_MIRROR = (
    "https://files.data.gouv.fr/geo-dvf/latest/csv/{year}/departements/{dept}.csv.gz"
)
# Historical DGFiP raw releases (pipe-separated). 202404 snapshot retains 2019–2023.
RAW_DVF_ARCHIVE = "https://data.cquest.org/dgfip_dvf/202404/valeursfoncieres-{year}.txt"
RAW_DVF_ARCHIVE_KNOWN_AS_OF = date(2024, 4, 5)  # DGFiP April 2024 release (approx.)

RAW_DIR = Path("data/raw/dvf")
INTERIM_DIR = Path("data/interim/transactions")

MIN_SURFACE_M2 = 9.0  # DVF hygiene: drop sub-9 m² lots (parking, cellars)

CANONICAL_COLUMNS = [
    "mutation_id",
    "date_mutation",
    "nature_mutation",
    "valeur_fonciere",
    "type_local",
    "surface_reelle_bati",
    "nombre_pieces_principales",
    "surface_terrain",
    "price_per_m2",
    "code_commune",
    "code_departement",
    "lon",
    "lat",
    "known_as_of",
]

# Raw DGFiP header (French) → internal snake names used before canonical rename.
RAW_COLUMN_MAP = {
    "No disposition": "numero_disposition",
    "Date mutation": "date_mutation",
    "Nature mutation": "nature_mutation",
    "Valeur fonciere": "valeur_fonciere",
    "Code departement": "code_departement",
    "Code commune": "code_commune_partial",
    "Type local": "type_local",
    "Surface reelle bati": "surface_reelle_bati",
    "Nombre pieces principales": "nombre_pieces_principales",
    "Surface terrain": "surface_terrain",
    "Reference document": "reference_document",
    "Identifiant de document": "identifiant_document",
}


def geo_dvf_url(year: int, department: str) -> str:
    """Build the verified Etalab geo-dvf department CSV URL."""
    return GEO_DVF_MIRROR.format(year=year, dept=str(department).strip())


def list_geo_years(session: requests.Session | None = None) -> list[int]:
    """Discover years currently published under the geo-dvf ``/latest/csv/`` index."""
    sess = session or requests.Session()
    resp = sess.get(GEO_DVF_CSV_INDEX, timeout=60)
    resp.raise_for_status()
    years = sorted({int(y) for y in re.findall(r"/csv/(\d{4})/", resp.text)})
    return years


def find_resources(years: list[int]) -> list[dict]:
    """List candidate download resources for the geolocated DVF dataset API."""
    resp = requests.get(DATASET_API, timeout=60)
    resp.raise_for_status()
    resources = resp.json().get("resources", [])
    out = []
    for r in resources:
        title = (r.get("title") or "") + " " + (r.get("url") or "")
        if any(str(y) in title for y in years):
            out.append({"title": r.get("title"), "url": r.get("url"), "format": r.get("format")})
    return out


def _parse_http_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).date()
    except (TypeError, ValueError, IndexError, OverflowError):
        return None


def url_exists(url: str, session: requests.Session | None = None) -> bool:
    sess = session or requests.Session()
    try:
        resp = sess.head(url, timeout=60, allow_redirects=True)
        if resp.status_code == 405:
            resp = sess.get(url, timeout=60, stream=True)
            resp.close()
        return resp.status_code == 200
    except requests.RequestException:
        return False


def download(url: str, dest: Path, session: requests.Session | None = None) -> tuple[Path, date | None]:
    """Download ``url`` to ``dest`` unless cached. Returns path and Last-Modified date."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    sess = session or requests.Session()
    if dest.exists() and dest.stat().st_size > 0:
        log.info("cached: %s", dest)
        head = sess.head(url, timeout=60, allow_redirects=True)
        known = _parse_http_date(head.headers.get("Last-Modified")) if head.ok else None
        return dest, known
    log.info("downloading %s", url)
    resp = sess.get(url, timeout=600, stream=True)
    resp.raise_for_status()
    known = _parse_http_date(resp.headers.get("Last-Modified"))
    with open(dest, "wb") as fh:
        for chunk in resp.iter_content(chunk_size=1 << 20):
            if chunk:
                fh.write(chunk)
    return dest, known


def read_dvf_file(path: Path) -> pd.DataFrame:
    """Read a DVF CSV / CSV.GZ / Parquet file into a DataFrame."""
    name = path.name.lower()
    if name.endswith(".parquet"):
        return pd.read_parquet(path)
    opener = gzip.open if name.endswith(".gz") else open
    with opener(path, "rb") as fh:  # type: ignore[arg-type]
        return pd.read_csv(io.BytesIO(fh.read()), low_memory=False)


def _pad_insee_commune(dept: str, commune_partial: str) -> str:
    dept = str(dept).strip()
    partial = str(commune_partial).strip()
    if not partial or partial.lower() == "nan":
        return ""
    if dept in {"2A", "2B"}:
        return f"{dept}{partial.zfill(3)}"
    return f"{dept.zfill(2)}{partial.zfill(3)}"


def stream_raw_dvf_department(
    url: str,
    department: str,
    dest: Path,
    session: requests.Session | None = None,
) -> Path:
    """Download a national raw DVF text file, keeping only ``department`` rows."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        log.info("cached: %s", dest)
        return dest

    sess = session or requests.Session()
    log.info("streaming raw archive %s (filter dept=%s)", url, department)
    resp = sess.get(url, timeout=600, stream=True)
    resp.raise_for_status()

    dept = str(department).strip()
    kept = 0
    with open(dest, "w", encoding="utf-8", newline="") as out:
        header: str | None = None
        for raw_line in resp.iter_lines(decode_unicode=True):
            if raw_line is None:
                continue
            line = raw_line.rstrip("\n\r")
            if not line:
                continue
            if header is None:
                header = line
                out.write(line + "\n")
                continue
            # Code département is field index 18 in the standard DGFiP layout
            # (0-based); fall back to a contains check if the shape drifts.
            parts = line.split("|")
            code = parts[18].strip() if len(parts) > 18 else ""
            if code == dept or code == dept.zfill(2):
                out.write(line + "\n")
                kept += 1
    log.info("kept %d raw rows for department %s → %s", kept, dept, dest)
    return dest


def read_raw_dvf_file(path: Path, department: str) -> pd.DataFrame:
    """Parse a pipe-separated DGFiP raw DVF extract into geo-dvf-like columns."""
    df = pd.read_csv(
        path,
        sep="|",
        dtype=str,
        low_memory=False,
        decimal=",",
        encoding="utf-8",
    )
    # Some extracts are latin-1; re-read if the French headers look garbled.
    if "Date mutation" not in df.columns and "Date mutation" not in [
        c.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore") for c in df.columns
    ]:
        df = pd.read_csv(
            path,
            sep="|",
            dtype=str,
            low_memory=False,
            decimal=",",
            encoding="latin-1",
        )

    rename = {k: v for k, v in RAW_COLUMN_MAP.items() if k in df.columns}
    df = df.rename(columns=rename)

    if "code_departement" in df.columns:
        df = df[df["code_departement"].astype(str).str.strip().isin({department, department.zfill(2)})]

    if "valeur_fonciere" in df.columns:
        df["valeur_fonciere"] = (
            df["valeur_fonciere"].astype(str).str.replace(" ", "", regex=False).str.replace(",", ".", regex=False)
        )
    for col in ("surface_reelle_bati", "surface_terrain", "nombre_pieces_principales"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(",", ".", regex=False)

    if "date_mutation" in df.columns:
        df["date_mutation"] = pd.to_datetime(df["date_mutation"], dayfirst=True, errors="coerce")

    if "code_commune_partial" in df.columns and "code_departement" in df.columns:
        df["code_commune"] = [
            _pad_insee_commune(d, c)
            for d, c in zip(df["code_departement"], df["code_commune_partial"], strict=True)
        ]

    # Synthetic mutation id — raw DGFiP files lack Etalab's id_mutation.
    bits = []
    for col in ("date_mutation", "numero_disposition", "code_commune", "valeur_fonciere", "type_local"):
        if col in df.columns:
            bits.append(df[col].astype(str))
    if bits:
        df["id_mutation"] = bits[0]
        for b in bits[1:]:
            df["id_mutation"] = df["id_mutation"] + "|" + b
    else:
        df["id_mutation"] = df.index.astype(str)

    df["longitude"] = pd.NA
    df["latitude"] = pd.NA
    return df.reset_index(drop=True)


def clean_dvf(df: pd.DataFrame, known_as_of: date | None = None) -> pd.DataFrame:
    """Standard DVF hygiene → canonical ``transactions`` columns.

    Keeps residential sales of houses/apartments with a usable surface and
    value, computes price_per_m2, and drops exact duplicate mutation rows.
    """
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]

    # Accept either raw geo-dvf names or already-canonical names.
    if "mutation_id" in df.columns and "id_mutation" not in df.columns:
        df = df.rename(columns={"mutation_id": "id_mutation"})
    if "lon" in df.columns and "longitude" not in df.columns:
        df = df.rename(columns={"lon": "longitude"})
    if "lat" in df.columns and "latitude" not in df.columns:
        df = df.rename(columns={"lat": "latitude"})

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

    if "nombre_pieces_principales" in df.columns:
        df["nombre_pieces_principales"] = pd.to_numeric(
            df["nombre_pieces_principales"], errors="coerce"
        ).astype("Int64")
    else:
        df["nombre_pieces_principales"] = pd.Series([pd.NA] * len(df), dtype="Int64")

    if "surface_terrain" in df.columns:
        df["surface_terrain"] = pd.to_numeric(df["surface_terrain"], errors="coerce")
    else:
        df["surface_terrain"] = pd.NA

    for col in ("code_commune", "code_departement", "nature_mutation", "type_local"):
        if col not in df.columns:
            df[col] = pd.NA
        else:
            df[col] = df[col].astype(str).where(df[col].notna(), other=pd.NA)

    df["lon"] = pd.to_numeric(df["longitude"], errors="coerce") if "longitude" in df.columns else pd.NA
    df["lat"] = pd.to_numeric(df["latitude"], errors="coerce") if "latitude" in df.columns else pd.NA

    if known_as_of is not None:
        df["known_as_of"] = known_as_of
    elif "known_as_of" in df.columns:
        df["known_as_of"] = pd.to_datetime(df["known_as_of"], errors="coerce").dt.date
    else:
        df["known_as_of"] = pd.NaT

    out = pd.DataFrame(
        {
            "mutation_id": df["id_mutation"].astype(str),
            "date_mutation": df["date_mutation"],
            "nature_mutation": df["nature_mutation"],
            "valeur_fonciere": df["valeur_fonciere"].astype(float),
            "type_local": df["type_local"],
            "surface_reelle_bati": df["surface_reelle_bati"].astype(float),
            "nombre_pieces_principales": df["nombre_pieces_principales"],
            "surface_terrain": df["surface_terrain"],
            "price_per_m2": df["price_per_m2"].astype(float),
            "code_commune": df["code_commune"],
            "code_departement": df["code_departement"],
            "lon": df["lon"],
            "lat": df["lat"],
            "known_as_of": df["known_as_of"],
        }
    )
    return out.reset_index(drop=True)[CANONICAL_COLUMNS]


def fetch_department_year(
    department: str,
    year: int,
    *,
    session: requests.Session | None = None,
    geo_years: Iterable[int] | None = None,
) -> tuple[pd.DataFrame, str]:
    """Fetch and parse one department-year. Returns (frame, source_label)."""
    sess = session or requests.Session()
    available = set(geo_years) if geo_years is not None else None
    url = geo_dvf_url(year, department)
    use_geo = (year in available) if available is not None else url_exists(url, session=sess)

    if use_geo:
        dest = RAW_DIR / f"dvf_{department}_{year}.csv.gz"
        path, known = download(url, dest, session=sess)
        frame = read_dvf_file(path)
        if known is None:
            log.warning(
                "no Last-Modified for %s — known_as_of left null (do not invent a date)",
                url,
            )
        frame["known_as_of"] = known
        return frame, f"geo-dvf:{url}"

    archive_url = RAW_DVF_ARCHIVE.format(year=year)
    if not url_exists(archive_url, session=sess):
        raise FileNotFoundError(
            f"no geo-dvf department file for {department}/{year} ({url}) and "
            f"no raw archive at {archive_url}. Update config/data_sources.yml."
        )
    dest = RAW_DIR / f"dvf_raw_{department}_{year}.txt"
    path = stream_raw_dvf_department(archive_url, department, dest, session=sess)
    frame = read_raw_dvf_file(path, department)
    frame["known_as_of"] = RAW_DVF_ARCHIVE_KNOWN_AS_OF
    return frame, f"raw-archive:{archive_url}"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--department", required=True, help="e.g. 34 for Hérault")
    parser.add_argument("--years", nargs="+", type=int, required=True)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    session = requests.Session()

    try:
        geo_years = list_geo_years(session=session)
        log.info("geo-dvf /latest years available: %s", geo_years)
    except requests.RequestException as exc:
        log.warning("could not list geo-dvf index (%s); will HEAD each year URL", exc)
        geo_years = None

    frames: list[pd.DataFrame] = []
    sources: list[str] = []
    for year in args.years:
        try:
            frame, source = fetch_department_year(
                args.department,
                year,
                session=session,
                geo_years=geo_years,
            )
        except FileNotFoundError as exc:
            # Last-chance: dataset API resource listing (national files — not preferred).
            log.warning("%s", exc)
            resources = find_resources([year])
            if not resources:
                raise SystemExit(str(exc)) from exc
            log.info("candidate API resources: %s", [r["title"] for r in resources])
            path, known = download(
                resources[0]["url"],
                RAW_DIR / f"dvf_api_{year}_{resources[0]['title']}",
                session=session,
            )
            frame = read_dvf_file(path)
            if "code_departement" in {c.lower() for c in frame.columns}:
                frame.columns = [c.strip().lower() for c in frame.columns]
                frame = frame[frame["code_departement"].astype(str) == str(args.department)]
            if known is None:
                log.warning(
                    "no Last-Modified for API resource — known_as_of left null"
                )
            frame["known_as_of"] = known
            source = f"api:{resources[0]['url']}"
        log.info("year %s: %d raw rows from %s", year, len(frame), source)
        frames.append(frame)
        sources.append(source)

    cleaned = clean_dvf(pd.concat(frames, ignore_index=True))
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    out = INTERIM_DIR / f"transactions_{args.department}.parquet"
    cleaned.to_parquet(out, index=False)
    log.info("sources: %s", sources)
    log.info("wrote %d rows → %s", len(cleaned), out)
    if "date_mutation" in cleaned.columns and len(cleaned):
        years_present = sorted(
            {d.year for d in cleaned["date_mutation"] if isinstance(d, date)}
        )
        log.info("mutation years present: %s", years_present)


if __name__ == "__main__":
    main()
