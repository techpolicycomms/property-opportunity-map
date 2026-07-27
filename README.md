# Property Opportunity Map

An open, reproducible, point-in-time spatial forecasting system that identifies
affordable European locations with the highest probability of materially
outperforming their national housing market over 5–20 year horizons.

**Status: early scaffold (Phase 0).** France-first pilot using DVF/DVF+
transaction data. See [`docs/methodology.md`](docs/methodology.md) and
[`docs/limitations.md`](docs/limitations.md) before trusting any output.

**This is not financial advice.** It is a research and decision-support tool.
Every score ships with uncertainty intervals and known limitations.

## The question

Not *"what is this property worth?"* (that is a solved AVM problem), but:

> Which currently affordable European locations have the highest probability of
> materially outperforming their national housing market over the next 10–20
> years?

A location is an opportunity only when several things are true at once:

```text
Low current valuation
+ rising future demand
+ constrained future supply
+ credible infrastructure catalyst
+ manageable physical and regulatory risk
+ sufficient market liquidity
```

For calibration: 4× over 20 years ≈ 7.2% nominal CAGR; 10× over 20 years ≈
12.2%. The model reports expected CAGR **distributions**, never "high
potential" labels.

## Architecture

```text
Public and national datasets (DVF+, INSEE, Eurostat, TENtec, EEA, …)
            ↓
Data ingestion and harmonisation          (src/pomap/ingestion)
            ↓
Historical geospatial feature store       (GeoParquet / DuckDB)
            ↓
Econometric + causal + ML models          (src/pomap/models)
   1. fair value    2. appreciation    3. infrastructure catalyst
            ↓
Investability filter + opportunity score  (src/pomap/scoring)
            ↓
GeoParquet / PMTiles / GeoJSON outputs    (src/pomap/publishing)
            ↓
Interactive public web map                (web/, GitHub Pages)
```

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
# Download and clean DVF transactions for one department:
python -m pomap.ingestion.france_dvf --department 34 --years 2020 2021 2022 2023 2024
```

See [`pipelines/README.md`](pipelines/README.md) for the full phase plan.

## Deployment

The site is static. It is currently live on GitHub Pages; Firebase Hosting +
a Namecheap custom domain is the production path, and OpenShift is parked for
a possible future backend. Full step-by-step: [`docs/deployment.md`](docs/deployment.md).

## Multi-agent development

This repository is designed to be built by a coordinated team of AI coding
agents (Claude Code, Codex, Cursor, Antigravity, DeepSeek) supervised by a
human. The roster, role charters, shared data contracts, handoff protocol and
review gates live in **[`AGENTS.md`](AGENTS.md)**. Tool-specific entry points
(`CLAUDE.md`, `.cursor/rules/`) point back to it.

## Repository layout

| Path | Purpose |
|---|---|
| `src/pomap/` | Python package: ingestion → features → models → scoring → publishing |
| `config/` | Country, indicator, data-source and model configuration |
| `docs/` | Research question, methodology, data dictionary, limitations, model card |
| `notebooks/` | Exploratory analysis (numbered, throwaway-friendly) |
| `pipelines/` | How to run the end-to-end pipeline |
| `web/` | Static MapLibre viewer, deployed to GitHub Pages |
| `agent-handoffs/` | Structured notes passed between agents |
| `data/`, `outputs/` | Gitignored working data (see `data/README.md`) |

## License

MIT — see [LICENSE](LICENSE). Data remain subject to their original licences
(see `config/data_sources.yml`).
