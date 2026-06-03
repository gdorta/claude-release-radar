# Changelog

All notable changes to Claude Release Radar are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [1.0.1] — 2026-06-02

### Changed
- Tuned the skill `description` for more reliable triggering: added natural phrasings
  ("should I update Claude Code?", "what can the API do now?") and an explicit
  "do NOT use for…" clause to suppress near-misses (running updates, summarizing the
  user's own changelog, other products).

### Added
- `evals/trigger-eval.json` — 20 labelled trigger queries (10 positive, 10 near-miss)
  plus `evals/README.md` for running the description optimizer.

### Verified
- Live smoke test against the real npm registry and Claude Code CHANGELOG confirmed the
  npm and markdown-changelog parsers, personalization, and graceful-degradation paths.

## [1.0.0] — 2026-06-02

### Added
- Stdlib-only engine (`scripts/radar.py`) with `check`, `env`, `sources`, and
  `mark-seen` commands.
- Stateful "since you last checked" diffing against `~/.claude/claude-release-radar/state.json`.
- Source registry (`scripts/sources.json`) covering Claude Code (npm version, GitHub
  releases, CHANGELOG), Models & API, and Claude apps; plus optional ClaudeLog and
  docs sources.
- Deterministic parsers for npm, Atom/RSS, and Markdown changelogs; `agent`-type
  sources handed to the orchestrating model for narrative pages.
- Read-only environment detection (CLI version, skills, plugins, MCP server names) and
  personalized impact tagging with "try this" suggestions.
- `--input` mode so the agent can supply pre-fetched pages when the engine has no network.
- `SKILL.md` orchestration with trigger-rich description.
- npm CLI installer (`npx claude-release-radar install`).
- Scheduling recipes (Cowork task, cron, GitHub Action, launchd).
