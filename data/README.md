# data/

Never commit raw or processed data (see `.gitignore`).

- `raw/` — downloads exactly as received, plus a `SOURCES.md` per download
  noting URL and date.
- `interim/` — cleaned, stage-specific outputs.
- `processed/` — the canonical feature store (GeoParquet/Parquet).
- `samples/` — small, committable extracts for tests and demos (≤ a few MB).
