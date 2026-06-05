# Roadmap

Claude Release Radar is small on purpose. The aim isn't to do everything — it's to
answer one question really well: *what's new in Claude, and what does it mean for me?*

So this is less a backlog and more a list of things I think would make the radar
quieter, sharper, and more useful. Nothing here is set in stone, and the order will
shift toward whatever people actually find helpful. If one of these scratches an itch
you have too, issues and PRs are genuinely welcome — especially new sources and parsers.

## Shipped

- **The core** — stateful "only what's new since you last checked," personalized to your
  setup, with copy-paste commands to try things.
- **v1.1.0 — Claude Desktop plugin.** One-click install alongside the CLI skill, with
  zero change to the existing install paths.
- Zero-dependency engine, with tests running on Python 3.8–3.12.

## Next up

The things I'd reach for first — each one makes the everyday briefing better.

- **Merge duplicate releases across sources** ([#5]) — one entry per version instead of
  three. Cleaner briefings are the whole point.
- **Flag deprecations loudly** ([#6]) — the stuff with a deadline deserves the top of the
  page.
- **"What did I miss?" catch-up mode** ([#7]) — `since <date>`, for when you've been away.

## Later

- **Lead with the big stuff** ([#8]) — headline first: new models and major versions
  above patch notes.
- **One command to wire up a digest** ([#9]) — turn "want this every morning?" into a
  single step.
- **Get quieter over time** ([#10]) — take the hint when a briefing wasn't relevant.

## Polish

- **Be polite to servers** ([#11]) — conditional fetches (ETag / If-Modified-Since).
- **`radar.py doctor`** ([#12]) — a health check so a broken source can't hide.

## Someday, maybe

A few ideas I'm still chewing on: smart digest timing from your calendar, richer
per-surface filters, a short "catch me up out loud" summary. If any of these sound right
to you, open an issue and let's talk it through.

---

If you'd like to jump in, the [good first issues][gfi] are a friendly place to start.
Thanks for being here. 🛰️

— Gabe

[#5]: https://github.com/gdorta/claude-release-radar/issues/5
[#6]: https://github.com/gdorta/claude-release-radar/issues/6
[#7]: https://github.com/gdorta/claude-release-radar/issues/7
[#8]: https://github.com/gdorta/claude-release-radar/issues/8
[#9]: https://github.com/gdorta/claude-release-radar/issues/9
[#10]: https://github.com/gdorta/claude-release-radar/issues/10
[#11]: https://github.com/gdorta/claude-release-radar/issues/11
[#12]: https://github.com/gdorta/claude-release-radar/issues/12
[gfi]: https://github.com/gdorta/claude-release-radar/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22
