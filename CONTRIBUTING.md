# Contributing

Contributions are welcome — from humans and from AI agents. The rules are the
same for both.

## Ground rules

1. **Read `AGENTS.md` and `docs/methodology.md` first.** They define the data
   contracts and the modelling philosophy.
2. **No look-ahead data.** Every feature must carry the date on which it was
   knowable. Backtests depend on this. If you cannot date it, do not use it.
3. **No unexplained scores.** Any change to scoring must also update the
   explanation fields surfaced in the map popups.
4. **Uncertainty is mandatory.** Never emit a point forecast without at least
   a 10th/90th percentile interval.
5. **No raw data in git.** `data/raw/`, `data/interim/`, `data/processed/` and
   `outputs/` are gitignored. Commit samples and schemas only.
6. **Honesty over impressiveness.** Report backtest failures in
   `docs/limitations.md`. Do not tune until a backtest looks good and hide the
   rest.

## Workflow

- Pick or file a GitHub Issue. Issues are labelled by agent role
  (`agent:data`, `agent:geo`, `agent:model`, `agent:backtest`,
  `agent:publish`, `agent:review`) — see `AGENTS.md`.
- Branch as `agent/<role>/<short-slug>`, open a PR, request review from the
  review agent (or a human) before merge.
- Add or update a handoff note in `agent-handoffs/` when you finish a task
  that another role depends on.

## Code

- Python 3.11+, `ruff` for lint/format, `pytest` for tests.
- Keep modules small and single-purpose; configuration lives in `config/`,
  not in code constants.
- Match the existing style of the file you are editing.
