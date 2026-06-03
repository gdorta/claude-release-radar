# Source registry reference

Claude Release Radar reads `scripts/sources.json`. Each entry:

| field      | meaning |
|------------|---------|
| `id`       | stable identifier; also the filename (`<id>.raw`) used in `--input` mode |
| `label`    | human name shown in the briefing |
| `category` | grouping in the briefing: `Claude Code` · `Models & API` · `Claude apps` · `Community` |
| `type`     | how it's parsed (see below) |
| `url`      | where to fetch |
| `enabled`  | include it or not |
| `homepage` | optional friendlier link used in output |
| `note`     | optional guidance for the agent |

## Parser types

- **`npm`** — npm registry `/latest` endpoint. Yields one item: the current version.
  Powers the "you're N versions behind" alert by comparing to `claude --version`.
- **`atom`** / **`rss`** / **`feed`** — XML feeds. The engine handles both Atom
  (`<entry>`) and RSS (`<item>`) and extracts title, link, date, and summary.
- **`markdown-changelog`** — a raw Markdown changelog. Split into per-version blocks by
  `## x.y.z` headers; the first few bullets become the teaser.
- **`agent`** — narrative HTML with no clean feed. The engine does **not** scrape these;
  it lists them for the orchestrating agent to WebFetch and summarize (entries newer
  than `state.last_checked` only). If a URL 404s, the agent WebSearches the label.

## Shipped sources

| id | type | default | what it covers |
|----|------|---------|----------------|
| `claude-code-npm` | npm | on | The published Claude Code CLI version |
| `claude-code-releases` | atom | on | GitHub release entries (titles + notes) |
| `claude-code-changelog` | markdown-changelog | on | The full per-version CHANGELOG |
| `api-release-notes` | agent | on | Claude API changes, structured outputs, limits |
| `anthropic-news` | agent | on | Model launches & product announcements |
| `claude-apps-release-notes` | agent | on | Web / desktop / mobile app updates |
| `claude-code-release-notes` | agent | off | Docs narrative companion to the CHANGELOG |
| `claudelog-youtube` | atom | off | Community "every update in 3 min" explainers |

> URLs for `agent` sources are best-effort. Anthropic occasionally reorganizes the
> docs; the agent is instructed to WebSearch the label as a fallback, so a moved page
> degrades gracefully rather than breaking the run.

## Adding your own source

Append to the `sources` array. Examples:

```jsonc
// A structured feed you already trust:
{ "id": "my-feed", "label": "My Claude feed", "category": "Community",
  "type": "rss", "url": "https://example.com/feed.xml", "enabled": true }

// A narrative page for the agent to summarize:
{ "id": "status", "label": "Claude status", "category": "Claude apps",
  "type": "agent", "url": "https://status.anthropic.com", "enabled": true }
```

Then verify it parses:

```bash
python3 scripts/radar.py sources                 # confirm it's listed/enabled
python3 scripts/radar.py check --json | less      # inspect parsed items
```

## State & privacy

- State lives at `~/.claude/claude-release-radar/state.json` (override with the
  `CLR_STATE` env var or `--state`). It stores seen-item ids, the last-checked
  timestamp, and the last npm version — nothing sensitive.
- Environment detection is read-only and records **names** only (skills, plugins, MCP
  server names). It never reads MCP credential values or any secrets.
