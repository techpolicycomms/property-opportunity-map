# Data dictionary

Canonical schemas for tables passed between pipeline stages. Changing any of
these requires a dedicated PR approved by the orchestrator and the downstream
role (see `AGENTS.md` §3.1).

Every table carries `known_as_of` (DATE) — the date the information was
publicly knowable. This is the backbone of point-in-time backtesting.

## `transactions` (per sale; from DVF/DVF+)

| Column | Type | Notes |
|---|---|---|
| `mutation_id` | string | DVF `id_mutation` |
| `date_mutation` | date | sale date |
| `nature_mutation` | string | e.g. Vente |
| `valeur_fonciere` | float | € |
| `type_local` | string | Maison / Appartement / … |
| `surface_reelle_bati` | float | m² |
| `nombre_pieces_principales` | int | |
| `surface_terrain` | float | m², nullable |
| `price_per_m2` | float | derived: valeur_fonciere / surface_reelle_bati |
| `code_commune` | string | INSEE commune code |
| `code_departement` | string | |
| `lon`, `lat` | float | WGS84 (DVF+ / BAN-geocoded) |
| `known_as_of` | date | DVF publication date of the containing release |

## `features_grid` / `features_commune` (one row per unit per vintage)

| Column group | Examples |
|---|---|
| identity | `unit_id` (H3 index or commune code), `vintage` (YYYY) |
| A demand | `pop_cagr_5y`, `net_migration_rate`, `vacancy_rate` |
| B accessibility | `jobs_reachable_45min`, `rail_freq_daily`, `planned_project_stage`, `accessibility_delta_jobs` |
| C economy | `emp_cagr_5y`, `business_creation_rate`, `wage_cagr_5y` |
| D supply | `permits_per_1k`, `completions_per_1k`, `developable_land_share` |
| E valuation | `median_price_m2`, `price_income_ratio`, `gross_yield`, `peer_discount`, `annual_transactions` |
| F amenities | `schools_access`, `gp_access_min`, `green_space_share` |
| G digital | `ftth_coverage`, `vhcn_coverage`, `median_down_mbps` |
| H risk | `flood_zone_share`, `wildfire_risk`, `heat_stress_days`, `dpe_liability_share` |
| meta | `known_as_of`, `source_refs` (JSON) |

## `scores` (one row per unit per run)

| Column | Notes |
|---|---|
| `unit_id`, `run_id`, `known_as_of` | identity |
| `median_price_m2`, `annual_transactions` | context |
| `pred_cagr_10y_p10/p50/p90` | nominal forecast distribution |
| `expected_excess_return_10y` | vs national HPI, percentage points |
| `score_fundamental`, `score_catalyst`, `score_investability` | sub-scores 0–100 |
| `risk_penalty` | 0–100 |
| `opportunity_score` | combined, 0–100 |
| `drivers_positive`, `drivers_risk` | JSON arrays of human-readable strings |
| `budget_eligible` | bool: median purchasable ≤ €200,000 |

## `projects_transport` (catalyst register)

`project_id`, `name`, `mode`, `corridor`, `stage`
(proposed/funded/contracted/under_construction/operational),
`announcement_date`, `funding_date`, `expected_opening`,
`completion_probability`, `affected_units` (JSON), `known_as_of`.
