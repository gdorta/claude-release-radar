# Changelog

All notable changes to Claude Release Radar are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [1.1.0] — 2026-06-04

### Added
- **Claude Desktop plugin support.** Install in two clicks via the "Install in Claude"
  badge, drag-and-drop the `.plugin`, or `/plugin marketplace add gdorta/claude-release-radar`
  for auto-updates — with zero changes to the existing CLI install paths.
- `.claude-plugin/plugin.json` manifest and `.claude-plugin/marketplace.json` so the
  Desktop loader and marketplace recognize the skill.
- `skills/claude-release-radar/` — an auto-synced mirror of the canonical root files that
  the Desktop plugin loader reads.
- `tools/sync-skill.sh` (refresh the mirror) and `tools/build-plugin.sh` (zip the
  distributable `.plugin`), wired up as `npm run sync` and `npm run build:plugin`.
- CI: `verify-sync` fails any PR where the mirror drifts from the canonical files;
  `release` builds and attaches `claude-release-radar.plugin` to each tagged GitHub release.
- First-run framing and an install-help section in `SKILL.md`.

### Changed
- README leads with the Desktop install path, then marketplace, CLI, and manual — every
  existing CLI/standalone command is preserved byte-for-byte.

### Unchanged (backward-compatibility guarantee)
- `npx claude-release-radar install`, `git clone … ~/.claude/skills/claude-release-radar`,
  and `python3 scripts/radar.py check` all behave exactly as before. `bin/cli.js` still
  copies the canonical root files; the root `SKILL.md`, `scripts/`, and `reference/` did
  not move.

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
