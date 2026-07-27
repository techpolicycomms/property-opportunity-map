# Model card

> Filled in by the Modeller and Backtester. A model version may not be
> published (Gate B, `AGENTS.md`) until every section below is complete.

## v0 — scaffold (no trained model yet)

- **Intended use:** identify affordable European locations with potential
  long-term housing-market outperformance. Decision support, not advice.
- **Out of scope:** individual-property AVM pricing, short-term (<5y)
  trading, commercial property.
- **Training data:** France DVF/DVF+ transactions; INSEE demographics;
  Eurostat HPI; accessibility and risk layers per `config/data_sources.yml`.
- **Targets:** 5y/10y real CAGR; 10y excess CAGR vs national HPI.
- **Metrics (planned):** Spearman rank of predicted vs realised excess
  returns; p10–p90 calibration; top-decile hit rate.
- **Backtests survived:** none yet.
- **Out-of-sample results:** none yet.
- **Ethical considerations:** risk of amplifying displacement/gentrification
  pressure in scored areas; scores are published with uncertainty and driver
  explanations to reduce misuse as a black-box "buy signal".
