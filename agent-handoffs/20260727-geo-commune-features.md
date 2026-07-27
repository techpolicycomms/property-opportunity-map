# Handoff: geo — Hérault commune features

- **Date:** 2026-07-27
- **Author role:** agent:geo (tool: Codex)
- **Issue/PR:** AGENTS.md §7 issue 2 / branch `agent/geo/commune-features`

## What changed

- Added `src/pomap/features/commune.py`, a config-driven builder for the
  canonical `features_commune` table.
- Added `features_commune` runtime inputs, INSEE source mappings, release
  date, code-alias policy, and implementation flags to
  `config/indicators.yml`.
- The builder emits exactly these columns: `unit_id`, `vintage`, `population`,
  `working_age_share`, `vacancy_rate`, `median_price_m2`,
  `annual_transactions`, `known_as_of`, and JSON `source_refs`.
- Built the local, gitignored artifact
  `data/processed/features_commune_34.parquet` from
  `data/interim/transactions/transactions_34.parquet` and the cached official
  INSEE RP2021 commune indicator archives.
- Added tests in `tests/test_features_commune.py` for schema, aggregation,
  provenance, and rejection of a transaction input with no `known_as_of`.

## What was verified

```bash
.venv/bin/ruff check src/pomap/features tests/test_features_commune.py
.venv/bin/pytest -q
.venv/bin/python -m pomap.features.commune --config config/indicators.yml
```

- Lint passed; `pytest` passed (8 tests).
- Output has 1,980 rows: 343 transaction communes across vintages 2019–2024.
- All output fields, including `known_as_of` and `source_refs`, are non-null.
- `annual_transactions` sums to 156,351, exactly the configured transaction
  input row count.
- `known_as_of` is the later of the aggregate transaction availability and
  the INSEE archive revision date (2025-12-16): 664 rows are 2025-12-16 and
  1,316 rows are 2026-05-18.
- Transaction code 34330 (the delegated commune Vérargues) is mapped by the
  configured alias to successor commune 34246 (Entre-Vignes) for its INSEE
  demographic join; the output still retains `unit_id=34330`.

## Known-broken / unverified

- The official INSEE RP2021 archive currently served includes corrections
  released 2025-12-16. It must not be used in a backtest cutoff before that
  date; earlier point-in-time INSEE releases need their own archived sources.
- `working_age_share` is the exact RP2021 15–59 share. The current commune
  base does not separate ages 60–64 from 65–74, so it is not labelled as a
  15–64 share and no estimate was invented.
- This table is keyed by already-present DVF `code_commune`; it does not
  geocode the 2019–2020 transaction coordinates. BAN/parcelle enrichment of
  null lon/lat remains a separate transaction-level task.

## Next role should

**`agent:model`** should consume only rows whose `known_as_of` is no later
than the model/backtest cutoff, and should treat `working_age_share` as a
15–59 proxy. **`agent:backtest`** should enforce this release-date filter and
decide whether an archived pre-2025 INSEE release is needed for historical
windows.
