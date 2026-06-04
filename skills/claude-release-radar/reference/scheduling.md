# Recurring digest recipes

Turn the one-off check into a standing briefing. Pick the recipe that matches where
the user runs Claude. Always confirm cadence + delivery before creating anything.

## A. Cowork / Claude desktop app (easiest)

Use the scheduled-tasks capability (or a `schedule` skill if present). Create a task
with this prompt:

> Run the **claude-release-radar** skill: check for new Claude releases since last
> time, commit the state, and give me the briefing. If nothing is new, just say so in
> one line.

Suggested cadences:
- Daily at 8:00am — `0 8 * * *`
- Monday mornings — `0 8 * * 1`
- Hourly during a launch window — `0 * * * *`

## B. Claude Code CLI via cron (Unix/macOS)

The CLI has no built-in scheduler, but `cron` + headless mode works well. The engine
runs standalone — you don't even need Claude for the structured-feed digest:

```bash
# Edit your crontab:  crontab -e
# Every weekday at 8am, write a digest file and (optionally) notify.
0 8 * * 1-5 cd /path/to/claude-release-radar && \
  /usr/bin/python3 scripts/radar.py check --commit > "$HOME/claude-radar-$(date +\%F).md" 2>&1
```

For a richer, AI-narrated digest, pipe through headless Claude Code:

```bash
0 8 * * 1-5 cd /path/to/claude-release-radar && \
  claude -p "Run the claude-release-radar skill and give me today's briefing." \
  >> "$HOME/claude-radar.log" 2>&1
```

## C. GitHub Action (team-wide, posts to Slack/email)

Commit the skill to a repo and let CI run the radar on a schedule. The structured
engine needs no API key; only the optional Slack post does.

```yaml
# .github/workflows/claude-radar.yml
name: Claude Release Radar
on:
  schedule:
    - cron: "0 8 * * 1-5"   # weekdays 08:00 UTC
  workflow_dispatch:
jobs:
  radar:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.x" }
      # Persist state between runs so the diff stays incremental.
      - uses: actions/cache@v4
        with:
          path: ~/.claude/claude-release-radar
          key: claude-radar-state
      - name: Run radar
        run: |
          python3 scripts/radar.py check --commit > digest.md
          cat digest.md
      - name: Post to Slack (optional)
        if: ${{ env.SLACK_WEBHOOK != '' }}
        env:
          SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
        run: |
          python3 - <<'PY'
          import json, os, urllib.request
          body = open("digest.md").read()[:3500]
          req = urllib.request.Request(
              os.environ["SLACK_WEBHOOK"],
              data=json.dumps({"text": body}).encode(),
              headers={"Content-Type": "application/json"})
          urllib.request.urlopen(req)
          PY
```

> Tip: the `actions/cache` step is what keeps the digest incremental — without a
> persisted `state.json`, every run looks like a first run.

## D. macOS launchd (alternative to cron)

Save as `~/Library/LaunchAgents/com.user.claude-radar.plist`, then
`launchctl load` it. Use `<integer>` keys under `StartCalendarInterval` for `Hour`
and `Minute`. Cron (recipe B) is simpler unless you specifically prefer launchd.
