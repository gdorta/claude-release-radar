# 🛰️ Claude Release Radar

> A Claude Skill that keeps you effortlessly current on everything Claude — and tells you what each release means for *your* setup.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Skill](https://img.shields.io/badge/Claude-Skill-d97757.svg)](https://docs.claude.com)
[![Zero dependencies](https://img.shields.io/badge/dependencies-0-brightgreen.svg)](#)

Anthropic ships *fast*: new models, API changes, and near-weekly Claude Code releases.
Staying current means checking five different pages and remembering what you already saw.

**Claude Release Radar** collapses that into one ask — *"what's new in Claude?"* — and
answers with a briefing that shows **only what changed since you last checked**, then
flags the releases that actually affect your environment with copy-paste commands to try
them. It's the difference between a noisy feed and a useful one.

```
🛰️ Claude Release Radar — 2026-06-02  ·  since you last checked: 6 days ago

⚠️ Affects you
  • You're on Claude Code v2.1.160; latest is v2.4.2 — run `claude update`.
  • v2.4.2 adds `/hooks`, which pairs with your `pre-commit` skill.

🆕 What's new
  Claude Code
    • v2.4.2 — checkpoint/rewind, skill auto-discovery
  Models & API
    • Opus 4.8 — 1M-token context by default
    • Structured outputs now GA on Sonnet/Opus/Haiku 4.5

💡 Try this
  • `claude update` then `/hooks` to automate your lint-on-save
  • Switch to the new model with `/model`
```

## Why it's different

Most "changelog" tools are just a feed reader. This one is **stateful** and **personalized**:

- **Only what's new.** It remembers what you've seen (`state.json`) and diffs every run, so you never re-read old notes. A trustworthy radar is quiet when the sky is clear.
- **Tailored to you.** It inspects your installed CLI version, skills, plugins, and MCP servers (read-only, names only) and flags the releases that touch *your* setup.
- **Action, not just news.** Each item comes with a concrete next step — the exact command or slash-command to try the new thing.
- **Multi-surface.** Tracks Claude Code (npm version + GitHub releases + CHANGELOG), Models & API, and the Claude apps — in one call.
- **Zero dependencies.** Pure Python stdlib + Markdown. Nothing to `pip install`.

## Install

**As a Claude Skill (recommended).** Drop the folder into your skills directory:

```bash
git clone https://github.com/gdorta/claude-release-radar.git \
  ~/.claude/skills/claude-release-radar
```

…or via npm:

```bash
npx claude-release-radar install     # copies the skill into ~/.claude/skills/
```

Then just ask Claude **"what's new in Claude?"** (or "is my Claude Code up to date?",
"any new Claude models?", "catch me up on Anthropic releases"). The skill triggers
automatically.

**Standalone (no Claude needed for the structured digest).** The engine runs on its own:

```bash
python3 scripts/radar.py check          # render the briefing
python3 scripts/radar.py check --commit # render AND mark everything as seen
```

## How it works

```
        ┌─────────────── sources.json ───────────────┐
        │ npm version · GitHub releases · CHANGELOG   │  ← parsed deterministically
        │ API notes · Anthropic news · app updates    │  ← summarized by the agent
        └─────────────────────────────────────────────┘
                              │
                    scripts/radar.py
                              │
        fetch ─► diff vs state.json ─► detect your env ─► personalize ─► briefing
```

- **Structured feeds** (npm, Atom/RSS, Markdown changelog) are parsed deterministically by the engine.
- **Narrative pages** (model launches, API notes, app updates) have no clean feed, so the engine hands them to Claude to WebFetch and summarize — only entries newer than your last check.
- **State** lives at `~/.claude/claude-release-radar/state.json` (override with `CLR_STATE` or `--state`).

## Commands

```bash
python3 scripts/radar.py check        # aggregate + diff + personalize + render
python3 scripts/radar.py check --json # same, as a machine-readable object
python3 scripts/radar.py env          # show what it detected about your setup
python3 scripts/radar.py sources      # list configured sources
python3 scripts/radar.py mark-seen    # commit current items as a baseline
```

No network? Fetch the feeds yourself and point the engine at them:

```bash
python3 scripts/radar.py check --input ./fetched/   # reads <source_id>.raw files
```

## Recurring digest

Get updates pushed to you instead of asking. The skill can set up a daily/weekly
scheduled task in the Claude desktop app, or you can wire up cron / a GitHub Action
that posts to Slack or email. Ready-to-paste recipes: [`reference/scheduling.md`](reference/scheduling.md).

## Customize what you track

Edit [`scripts/sources.json`](scripts/sources.json) — toggle `enabled`, or add your own
feed (`npm` · `atom`/`rss` · `markdown-changelog` · `agent`). Two extras ship disabled:
the docs "Claude Code release notes" page and the **ClaudeLog** YouTube channel
("every Claude Code update explained in under 3 minutes"). Full guide:
[`reference/sources.md`](reference/sources.md).

## Privacy

Environment detection is **read-only** and records **names only** — your skills,
plugins, and MCP server names. It never reads MCP credentials or any secret values.
State stores seen-item ids, a timestamp, and the last CLI version. Nothing leaves your
machine unless *you* wire up a Slack/email step.

## Project layout

```
claude-release-radar/
├── SKILL.md                 # how Claude uses the skill (triggering + orchestration)
├── scripts/
│   ├── radar.py             # the engine — stdlib only
│   └── sources.json         # the source registry
├── reference/
│   ├── sources.md           # every source + how to add your own
│   └── scheduling.md        # cron / GitHub Action / scheduled-task recipes
├── bin/cli.js               # `npx claude-release-radar install`
└── examples/
    └── sample_briefing.md   # an example of the output
```

## Credits

Inspired by the [**ClaudeLog** YouTube channel](https://www.youtube.com/@claudelog) —
*"every Claude Code update, explained in under 3 minutes."* This project automates the
"never miss an update" part and adds the personalization layer.

A community project. Not affiliated with or endorsed by Anthropic. "Claude" is a
trademark of Anthropic; this tool merely reads Anthropic's public release sources.

## License

[MIT](LICENSE) © contributors. PRs welcome — especially new sources and parsers.
