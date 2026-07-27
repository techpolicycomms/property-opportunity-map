# Claude Code entry point

Read **`AGENTS.md`** first — it is the single source of truth for the
multi-agent team operating this repo (roles, contracts, review gates,
prohibited actions). Then read `docs/methodology.md` and
`docs/data-dictionary.md`.

Default role for Claude Code sessions in this repo: **Modeller** or
**Reviewer**, unless the human assigns something else.

Key rules (full list in AGENTS.md §6):

- Every feature record carries `known_as_of`; no look-ahead data.
- No forecast without uncertainty intervals.
- No fabricated metrics — mark unverified claims as unverified.
- Config in `config/*.yml`, never hard-coded constants.
- PRs only, never push to `main`.
