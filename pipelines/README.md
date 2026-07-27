# Pipelines

End-to-end run order. Each stage reads config from `config/` and writes to
`data/` or `outputs/`. Nothing here is orchestrated yet — run stages manually
until the volume justifies a runner.

## Phase 1 — France pilot

```bash
# 1. Ingest DVF transactions (agent:data)
python -m pomap.ingestion.france_dvf --department 34 --years 2020 2021 2022 2023 2024

# 2. Build features (agent:geo)  [not yet implemented]
python -m pomap.features.build --country france --vintage 2024

# 3. Train models (agent:model)  [not yet implemented]
python -m pomap.models.fair_value --config config/model.yml
python -m pomap.models.appreciation --config config/model.yml

# 4. Backtest (agent:backtest)  [not yet implemented]
python -m pomap.backtesting.point_in_time --config config/model.yml

# 5. Score + publish (agent:publish)
python -m pomap.scoring.opportunity --config config/model.yml
python -m pomap.publishing.export_geojson --scores data/processed/scores.parquet \
    --out web/data/opportunities.geojson
```

GitHub Pages deploys `web/` automatically on push to `main`
(`.github/workflows/pages.yml`).
