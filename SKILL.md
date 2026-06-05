---
name: claude-release-radar
description: >-
  Personalized "what's new in Claude" briefing. Aggregates the official Claude release
  sources — new models, pricing and API changes, the Claude Code CHANGELOG and npm
  version, and Claude app (web/desktop/mobile) updates — then shows ONLY what changed
  since the user last checked and flags which releases affect the user's own setup,
  with copy-paste commands to try them. Use this skill whenever the user wants to catch
  up on or stay current with Claude, even if they don't say "release notes" — e.g.
  "what's new in Claude", "any new Claude models?", "did Claude Code update?", "is my
  claude-code out of date / should I update Claude Code?", "latest Claude changelog",
  "catch me up on Anthropic releases", "what changed in Claude this week", "what can the
  API do now?". Also use it to set up a recurring daily or weekly Claude-updates digest.
  Do NOT use it to actually run an update, to write release notes for the user's own
  product, or to summarize an unrelated CHANGELOG file from the user's repo — it is
  specifically about keeping the user current on Anthropic's Claude releases.
---

# Claude Release Radar 🛰️

Keep the user effortlessly current on everything Claude. Instead of making them
check five pages, this skill pulls the official sources, **diffs against what they
already saw**, and surfaces only the genuinely new stuff — then tells them which
items matter for *their* setup and what to do about each.

The payoff is the personalization: a generic feed is noise; "you're two versions
behind and v2.4.2 adds the `/hooks` you don't have yet — run `claude update`" is
signal. Aim for that every time.

## When to reach for this
- "What's new in Claude / Claude Code / the API?", "catch me up", "anything I missed?"
- "Is my Claude Code up to date?" / version questions
- "Are there new Claude models?" / pricing / deprecation questions
- The user wants updates delivered automatically (daily/weekly) — see *Recurring digest*.

## The engine (do this first, every time)

A stdlib-only Python engine does the heavy lifting: fetching structured feeds,
diffing against saved state, detecting the user's environment, and rendering the
briefing. **Always run it before composing your answer** — don't hand-roll the diff.

```bash
python3 scripts/radar.py check
```

This fetches the structured sources (npm version, GitHub releases, the Claude Code
CHANGELOG), compares them to `~/.claude/claude-release-radar/state.json`, detects the
local environment, and prints a ready-to-share markdown briefing. Add `--json` if you
want the structured object to reason over instead.

State is **not** committed by default, so you can show the briefing first. Once the
user has seen it, mark everything as read so the next check is clean:

```bash
python3 scripts/radar.py check --commit     # render AND mark seen
# or, after presenting:
python3 scripts/radar.py mark-seen
```

For a read-only catch-up window that ignores saved state and does not mark anything
as seen:

```bash
python3 scripts/radar.py since 2026-05-01
```

### If the engine can't reach the network
Some environments block the engine's own HTTP. If `check` reports fetch errors, fetch
the structured sources yourself with **WebFetch**, save each response into a directory
named `<source_id>.raw` (ids come from `scripts/radar.py sources`), then run:

```bash
python3 scripts/radar.py check --input /path/to/fetched/
```

The engine parses your saved files instead of hitting the network. Everything else
(diff, personalization, rendering) is local and always works.

## Narrative sources (the engine hands these to you)

Model launches, API changes, and Claude-app updates live on narrative HTML pages with
no clean feed, so the engine **does not** scrape them — it lists them under
"Check these narrative sources." For each one:

1. **WebFetch** the URL.
2. If it 404s or returns a JS shell, **WebSearch** the source label (e.g.
   "Anthropic API release notes", "new Claude model") and use the official result.
3. Report only entries **newer than `state.last_checked`** (in the engine's JSON
   output) — keep it to genuinely new items, not the whole page.
4. Fold these into the briefing under the right category (Models & API / Claude apps).

This split is deliberate: deterministic diffing where feeds are structured, your
judgement where pages are messy. Don't try to make the engine parse the HTML.

## Personalization (what makes this worth running)

`scripts/radar.py env` detects, best-effort and read-only:
- installed **Claude Code version** (`claude --version`) → compared to npm latest,
- the user's **skills** (`~/.claude/skills`, `./.claude/skills`),
- **plugins** (`~/.claude/plugins`),
- **MCP server names** (from `~/.claude.json` / `.mcp.json` — names only, never secrets).

The engine uses this to (a) raise a standing "you're N versions behind" alert and
(b) tag any new item that mentions one of the user's skills/plugins/connectors as
"affects your setup." When you present results, **lead with what affects them**, then
the general what's-new, then concrete "try this" commands. If you spot a release that
clearly interacts with something they use, say so explicitly and give the exact
command or `/slash-command` to try it. That single sentence is the value.

## Output: how to present

Run the engine, then deliver a tight briefing. Keep the engine's structure but make it
human — trim to what matters, and never pad a quiet week. Template:

```
🛰️ Claude Release Radar — <date>  ·  since you last checked: <when>

⚠️ Affects you        (only if true: version gap, or a release touching their setup)
🆕 What's new          (grouped: Claude Code · Models & API · Claude apps)
💡 Try this            (1–3 concrete, copy-paste actions tied to the new features)
```

If nothing changed, say so in one line — "✅ You're all caught up since <date>" — and
stop. A trustworthy radar is quiet when the sky is clear; don't manufacture updates.

Always include source links so the user can dig in. After presenting, offer to (a)
mark these as seen and/or (b) set up a recurring digest.

## Recurring digest (offer this — most users don't know it's possible)

Turning a one-off check into a standing briefing is the highest-leverage upsell.

- **In Cowork / the Claude desktop app:** use the scheduled-tasks capability to create
  a task (e.g. daily 8am or Monday mornings) whose prompt is:
  *"Run the claude-release-radar skill: check for new Claude releases since last time,
  commit state, and give me the briefing. If nothing's new, just say so."*
  If a `schedule` skill is available, use it; otherwise create the scheduled task directly.
- **In the Claude Code CLI (no built-in scheduler):** offer the user a cron line or a
  GitHub Action. See `reference/scheduling.md` for ready-to-paste examples (including
  one that posts the digest to Slack/email).

Always confirm cadence and delivery with the user before creating anything that runs
on its own.

## Configuring sources

`scripts/sources.json` is the registry. Each entry has an `id`, `category`, `type`
(`npm` · `atom`/`rss` · `markdown-changelog` · `agent`), `url`, and `enabled`.
Flip `enabled` to scope what the user tracks, or add new feeds. Two optional sources
ship disabled: the docs "Claude Code release notes" page and the **ClaudeLog** YouTube
channel (a community "every update explained in 3 minutes" layer) — enable them if the
user wants a more narrative or human companion. Full reference: `reference/sources.md`.

## Guardrails
- Don't invent releases or version numbers. If a source is unreachable, say so plainly
  and report what you *could* confirm — accuracy is the whole point of a radar.
- Treat undated narrative items conservatively; if you can't tell whether something is
  new, check it against `state.last_checked` rather than assuming.
- The engine reads MCP **server names** only, never credential values. Keep it that way.
- Keep the briefing skimmable. The user wants the signal, not a wall of changelog.

## Files
- `scripts/radar.py` — the engine (check · env · sources · mark-seen).
- `scripts/sources.json` — the source registry.
- `reference/sources.md` — every source explained + how to add your own.
- `reference/scheduling.md` — cron / GitHub Action / scheduled-task recipes.

## First-run framing

If `state.json` doesn't exist yet (first invocation after install), prepend a one-line
intro to the briefing:

> *First run — here's the last 30 days. Every future check will only show what's changed
> since the last time you asked.*

Then render the briefing as normal, cap-limited to the last 30 days, and end with the
standing offer to set up a daily/weekly digest. Don't repeat the framing on subsequent
runs.

## If the user asks to install / re-install this skill

If the user says "install claude-release-radar", "set up the release radar", or similar
**and you're reading this**, the skill is already loaded. Confirm it's already active and
offer to run a first check.

If the user wants to install it on **another machine** or get auto-updates, point them to
the right path for their environment:

- **Claude Desktop:** click the "Install in Claude" badge at
  <https://github.com/gdorta/claude-release-radar>, or drag the `.plugin` from the latest
  release into a chat. Or, for auto-updates:
  ```
  /plugin marketplace add gdorta/claude-release-radar
  /plugin install claude-release-radar
  ```
- **Claude Code (terminal):** `npx claude-release-radar install`
- **Manual:** `git clone https://github.com/gdorta/claude-release-radar.git ~/.claude/skills/claude-release-radar`
