# Methodology

Read with `research-question.md`. This file defines the modelling approach;
`data-dictionary.md` defines the tables; `AGENTS.md` defines who may change
what.

## Analytical geography

Two units simultaneously:

1. **Regular 1 km / H3 hexagonal grid** — comparable spatial features,
   amenity/accessibility aggregation, raster risk layers.
2. **Municipality (commune/LAU) boundaries** — demographics, fiscal and
   planning data.

Storage: GeoParquet (analysis), Parquet (time series), PMTiles (public map),
COG GeoTIFF (raster risk), GeoJSON (small outputs only), DuckDB (local
queries). PostGIS only if/when a server-backed system is needed.

## Feature groups (theory-informed, weights learned from history)

Feature weights are **learned from historical outcomes**, never hand-set.
Groups below organise engineering and explanation.

- **A. Demand trajectory** — population growth (3/5/10y), net migration,
  household formation, working-age population change, university enrolment,
  tourism nights, vacancy rates. Persistent depopulation is a strong penalty.
- **B. Transport & accessibility** — jobs reachable in 30/60/90 min,
  rail frequency (not just station distance), planned project stage
  (proposed/funded/contracted/under construction/operational), expected
  travel-time reduction, interchange potential, noise/severance penalties.
  Key derived variable: `accessibility improvement = future reachable jobs −
  current reachable jobs`.
- **C. Economic transformation** — employment growth, business creation,
  wage growth, sector diversification, major investment announcements,
  universities/hospitals/research centres, remote-work employment. Prefer
  *change and convergence* over current income levels (already capitalised).
- **D. Housing supply constraints** — permits per 1,000 residents,
  completions, developable land, zoning density, protected land, planning
  delays, construction costs, vacancy returning to market, STR restrictions.
  Demand growth + elastic supply ≠ price pressure.
- **E. Relative valuation & affordability** — median €/m², price-to-income,
  price-to-rent, gross/net yield, discount vs statistically comparable
  municipalities, real price vs previous peak, momentum, ask-vs-transaction
  gap, time on market, transaction volume/liquidity.
- **F. Services & quality of life** — schools, healthcare, daily services,
  green space, walkability, culture, air/noise pollution, safety (within-
  jurisdiction trends only; cross-country crime stats are not comparable),
  climate comfort.
- **G. Digital infrastructure** — FTTH availability, very-high-capacity
  network coverage, 4G/5G, measured speeds, rollout recency.
- **H. Risk & resilience** (negative/constraint layer) — river/coastal flood,
  wildfire, heat stress, drought/water availability, subsidence, seismic,
  coastal erosion, insurance availability, energy-performance liabilities,
  taxes/transaction costs, rental regulation, foreign-buyer restrictions.

## The four model components

### 1. Fair-value model — `pomap.models.fair_value`

Target: `log(transaction price per m²)`. Methods: hedonic baseline →
gradient-boosted trees → spatial variants (PySAL SAR/SDM) as comparators.
Output: **valuation gap** = actual − model-implied price. Purpose: find
places priced below what current observable fundamentals imply.

### 2. Long-term appreciation model — `pomap.models.appreciation`

Targets: 5y/10y real CAGR, and **10y excess CAGR over the national HPI**
(preferred: avoids merely predicting national credit cycles). Methods: panel
fixed effects, gradient boosting, Bayesian hierarchical pooling across
`property → commune → département → région` (essential for low-transaction
communes). Ensemble with disagreement-aware uncertainty.

### 3. Infrastructure catalyst model — `pomap.models.infrastructure_effect`

Stations are built where growth is already expected (endogeneity). Use event
studies around announcement/funding/construction/opening,
difference-in-differences with matched controls, synthetic controls for major
projects, distance bands. Output: `expected additional appreciation ×
P(project completion)`. Unfunded proposals get ~zero weight.

### 4. Investability & risk filter — `pomap.scoring`

Actionability for the €50k–€200k band: listings within budget, annual
transactions, time-to-resale, renovation needs, rental feasibility, taxes,
climate/insurance risk, legal restrictions, forecast confidence.

## Scoring

Three visible sub-scores — fundamental appreciation, catalyst, investability —
combined as:

```text
opportunity_score = expected_excess_return × forecast_confidence
                    × investability − risk_penalty
```

Every map cell must expose: predicted 10y CAGR, expected excess return,
p10/p50/p90, current median €/m², transaction count, principal positive
drivers, principal risks, future transport projects, and **`known_as_of`**
(the point-in-time date).

## Backtesting

Point-in-time only. Train on data knowable at T, predict T→T+5y/T+10y, score
against realised outcomes. Minimum harness: 2009→2014→2019 and 2014→2019→2024
windows. Metrics: Spearman rank of predicted vs realised excess returns,
calibration of the p10–p90 band, and hit-rate of the top decile. Failures are
recorded in `limitations.md`, not deleted.
