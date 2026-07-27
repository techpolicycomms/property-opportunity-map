# Limitations

Read this before trusting any output. Additions are expected — especially
backtest failures.

## Structural

- **Not financial advice.** Research decision-support only.
- **Survivor bias in drivers.** Infrastructure effects estimated from past
  projects may not transfer to future corridors or different macro regimes.
- **Endogeneity.** Transport investment targets places already expected to
  grow; causal estimates carry wide uncertainty.
- **National cycles dominate.** Local excess-return forecasts are more
  reliable than absolute forecasts; interest rates and credit conditions can
  overwhelm any local signal.

## Data

- **DVF coverage.** DVF excludes some sale types and has known reporting
  lags; geolocation quality varies (DVF+ improves but does not eliminate
  this). Alsace-Moselle historically had limited coverage.
- **Asking vs transaction prices.** Listing data (where used) overstates
  clearing prices; the ask-vs-transaction gap is itself a feature.
- **Cross-country harmonisation** (phases 3+): completed-sale data in Italy
  and Spain is less open than DVF; zone-level intervals are not transactions.
- **Crime and subjective quality-of-life** indicators are not comparable
  across jurisdictions; only within-jurisdiction trends are used.
- **Broadband and climate layers** are often aggregated above the property
  level; local precision is limited.

## Model

- **Uncertainty is real.** p10–p90 bands are wide by design; a "Medium"
  confidence score is not a recommendation.
- **Backtests are few.** Two or three historical windows cannot validate a
  20-year horizon claim.
- **Depopulation trap.** Cheap-plus-shrinking locations can produce seductive
  yields and near-zero exit liquidity.

## Changelog of known failures

- *(none yet — the Backtester fills this in; see `AGENTS.md` Gate B)*
