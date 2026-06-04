# Security & Privacy

## Privacy model

Claude Release Radar is designed to keep your machine's details on your machine.

- **Environment detection is read-only and records names only.** The engine looks at
  your installed Claude Code version, skill/plugin directory names, and MCP **server
  names** to personalize the briefing. It never reads MCP credentials, tokens, or any
  config *values* — only keys/names. See `detect_mcp_servers()` in
  [`scripts/radar.py`](scripts/radar.py); this guarantee is covered by a test in
  [`tests/test_radar.py`](tests/test_radar.py).
- **State is local and minimal.** `~/.claude/claude-release-radar/state.json` stores
  seen-item ids, a timestamp, and the last seen CLI version. Nothing else.
- **No telemetry, no network egress of your data.** The engine only makes outbound
  requests to the public release sources listed in `scripts/sources.json` to *read*
  them. It never transmits anything about your setup. If you wire up a Slack/email
  digest yourself, that delivery is entirely under your control.
- **Zero runtime dependencies.** Pure Python stdlib + Node — no third-party packages
  that could exfiltrate data.

## Reporting a vulnerability

Please report security issues privately via
[GitHub Security Advisories](https://github.com/gdorta/claude-release-radar/security/advisories/new)
rather than a public issue. We'll acknowledge within a few days and keep you posted on
a fix.

## Supported versions

The latest released version receives fixes. This is a community project provided as-is
under the [MIT License](LICENSE).
