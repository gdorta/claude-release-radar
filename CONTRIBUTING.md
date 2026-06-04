# Contributing

Thanks for helping make Claude Release Radar better — new sources and parsers are
especially welcome.

## The one rule: root files are canonical

The repo serves two install targets from a single source of truth:

- **`SKILL.md`, `scripts/`, `reference/`** at the repo root are **canonical**. Edit these.
- **`skills/claude-release-radar/`** is an **auto-generated mirror** the Claude Desktop
  plugin loader reads. **Never edit it by hand.**

After changing any canonical file, refresh the mirror before committing:

```bash
npm run sync          # = bash tools/sync-skill.sh
```

CI (`.github/workflows/verify-sync.yml`) fails any PR where the mirror has drifted.

## Dev setup

No build step and no runtime dependencies — the engine is Python 3.8+ stdlib only,
and the CLI is plain Node.

```bash
git clone https://github.com/gdorta/claude-release-radar.git
cd claude-release-radar
python3 scripts/radar.py check      # run the engine locally
node bin/cli.js help                # exercise the CLI
```

## Tests

```bash
npm test                            # python3 -m unittest discover -s tests
```

Please add a test for any parser or logic change. The suite is stdlib `unittest`
(no pytest) so it runs anywhere the engine does. CI runs it on Python 3.8–3.12.

## Adding a source

Edit [`scripts/sources.json`](scripts/sources.json):

- Structured feeds (`npm`, `atom`/`rss`, `markdown-changelog`) are parsed
  deterministically by the engine.
- Narrative HTML pages use `type: "agent"` — the engine hands them to the
  orchestrating model to fetch and summarize rather than scraping them.

Full guide: [`reference/sources.md`](reference/sources.md). If you add a new structured
`type`, register a parser in `scripts/radar.py` and cover it with a test.

## Building the plugin

```bash
npm run build:plugin                # → dist/claude-release-radar.plugin
```

## Pull requests

- Keep changes focused; one logical change per PR.
- Run `npm test` and `npm run sync` before pushing.
- Describe the user-facing effect in the PR body.

## Releasing (maintainers)

Bump the version in `package.json`, `.claude-plugin/plugin.json`, and
`.claude-plugin/marketplace.json`, update `CHANGELOG.md`, run `npm run sync`, then:

```bash
git tag vX.Y.Z && git push origin vX.Y.Z   # CI builds + attaches the .plugin
npm publish
```
