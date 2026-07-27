# AGENTS.md — Multi-Agent Operating Manual

This repository is developed by a **coordinated team of AI coding agents**
supervised by a human owner. This file is the single source of truth for how
the team works. Tool-specific files (`CLAUDE.md`, `.cursor/rules/`) defer to
it. Every agent — regardless of which product it runs in — must read this
file, `docs/methodology.md` and `docs/data-dictionary.md` before editing
anything.

---

## 1. Why multi-agent

The project spans five disciplines that rarely fit in one context window:
geospatial ETL, econometrics, machine learning, causal inference, and web
publishing. Splitting them into specialised roles with explicit contracts
between them produces better code and — more importantly — prevents the
classic failure mode where one agent silently changes a data schema and
breaks a model three stages downstream.

## 2. The roster

| Role | Label | Mission | Owns (write access) | Reads but never edits |
|---|---|---|---|---|
| **Orchestrator** | `agent:orchestrator` | Decompose goals into issues, sequence work, resolve contract disputes, enforce review gates | Issues, milestones, this file, `agent-handoffs/INDEX.md` | Everything |
| **Data Engineer** | `agent:data` | Ingest and harmonise public datasets into the feature store, point-in-time correct | `src/pomap/ingestion/`, `src/pomap/harmonisation/`, `src/pomap/geocoding/`, `config/data_sources.yml` | `docs/data-dictionary.md` (proposes changes via PR only) |
| **Geospatial Feature Engineer** | `agent:geo` | Turn harmonised data into model-ready features: accessibility, demographics, supply, amenities, risk | `src/pomap/features/`, `config/indicators.yml` | ingestion outputs |
| **Modeller** | `agent:model` | Fair-value, appreciation, infrastructure-catalyst and ensemble models; uncertainty quantification | `src/pomap/models/`, `config/model.yml`, `docs/model-card.md` | features, `docs/methodology.md` |
| **Backtester** | `agent:backtest` | Point-in-time historical validation, leakage audits, forecast honesty | `src/pomap/backtesting/`, `docs/limitations.md` | models and features (read-only) |
| **Publisher** | `agent:publish` | Export GeoParquet/PMTiles/GeoJSON, maintain `web/` viewer and GitHub Pages deploy | `src/pomap/publishing/`, `web/`, `.github/workflows/pages.yml` | scoring outputs |
| **Reviewer** | `agent:review` | Adversarial review of every PR: methodology, leakage, honesty of claims, licence compliance | Review comments only — no code writes | Everything |

### Suggested tool mapping (current setup)

The owner has access to Claude Code, Codex, Cursor, Antigravity and DeepSeek.
A sensible assignment — not binding, the orchestrator may reassign:

- **Claude Code** → Modeller, Reviewer (strong at methodology critique and
  careful refactors)
- **Codex / Cursor** → Data Engineer, Geospatial Feature Engineer, Publisher
  (high-throughput implementation inside an IDE)
- **DeepSeek (API)** → bulk, mechanical transforms the Data Engineer delegates
  (e.g. schema-aligned cleaning of many department files) — cost-effective
  batch work, always behind a review gate
- **Antigravity** → Orchestrator + browser QA of the published map
- **Human owner** → final merge authority, all outward-facing actions
  (releases, tweets, data-licence questions)

## 3. Shared contracts (the things that keep agents aligned)

Agents coordinate through **artifacts, not chat**. Three contracts matter:

1. **Data schemas** — `docs/data-dictionary.md` defines the canonical
   columns of every table passed between stages (transactions, features,
   scores). Changing a schema requires a PR that the orchestrator and one
   downstream role approve.
2. **Configuration** — all knobs live in `config/*.yml`. Code never
   hard-codes paths, thresholds, hyperparameters or source URLs.
3. **Handoff notes** — when a role finishes work another role depends on, it
   writes `agent-handoffs/YYYYMMDD-<role>-<topic>.md` using the template in
   `agent-handoffs/TEMPLATE.md` and adds a line to
   `agent-handoffs/INDEX.md`. A handoff note states: what changed, what was
   verified, what is known-broken, and what the next role should do.

### The point-in-time rule (most important contract)

Every record in the feature store carries `known_as_of` — the date on which
the information was publicly available. A feature whose availability date is
unknown is treated as unavailable for backtesting. The Backtester audits this
relentlessly; violations block merge.

## 4. Workflow

```text
Human sets goal
   ↓
Orchestrator files issues labelled agent:<role>, orders them, notes blockers
   ↓
Role agent picks issue → branch agent/<role>/<slug> → implement + tests
   ↓
PR: author fills "Contract impact" + "Verification" sections
   ↓
Reviewer agent comments (methodology, leakage, honesty); Backtester
reviews anything touching models or features
   ↓
Human merges. Publisher deploys web/ when outputs change.
```

### Pull-request checklist (every PR)

- [ ] Schemas unchanged, or schema PR approved by orchestrator + downstream role
- [ ] New features carry `known_as_of`
- [ ] Tests pass (`pytest`), lint clean (`ruff check .`)
- [ ] No raw data committed
- [ ] Claims in docs/comments match what the code actually does
- [ ] Handoff note written if another role depends on this

## 5. Review gates (hard stops)

1. **Gate A — Data honesty:** ingestion PRs must document source licence,
   update frequency and known defects in `config/data_sources.yml`.
2. **Gate B — Leakage:** any model PR must name the backtest it survived and
   its out-of-sample metrics in `docs/model-card.md`.
3. **Gate C — Publication:** the Publisher may only deploy scores that carry
   uncertainty intervals, driver explanations and `known_as_of`.

## 6. Prohibited actions (all agents)

- Never commit raw data, credentials, or `.env` files.
- Never fabricate metrics, backtest results, or data-source properties. If
  you could not verify it, write "unverified" and say why.
- Never silently reweight or rescore: scoring changes go through
  `config/model.yml` and are documented in `docs/methodology.md`.
- Never present the output as financial advice.
- Never push directly to `main`; PRs only.

## 7. Current phase

**Phase 0 — scaffold complete.** Next issues (in order):

1. `agent:data` — verify DVF ingestion against real files for department 34
   (Hérault) and document row counts in a handoff note.
2. `agent:geo` — municipal demographics from INSEE + BAN geocoding join.
3. `agent:model` — baseline hedonic fair-value model on one department.
4. `agent:backtest` — 2014→2019→2024 point-in-time backtest harness.
5. `agent:publish` — wire real scores into `web/` viewer.
