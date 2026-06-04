#!/usr/bin/env bash
# Mirrors the canonical root files (SKILL.md, scripts/, reference/) into
# skills/claude-release-radar/ so the Claude Desktop plugin loader can find them.
#
# Root files are CANONICAL. Do not edit skills/claude-release-radar/ directly.
# Run this script (or `npm run sync`) after touching any canonical file.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/skills/claude-release-radar"

# Wipe and rebuild from canonical sources — keeps the mirror byte-identical.
rm -rf "$DEST"
mkdir -p "$DEST"

cp    "$ROOT/SKILL.md"   "$DEST/SKILL.md"
cp -R "$ROOT/scripts"    "$DEST/scripts"
cp -R "$ROOT/reference"  "$DEST/reference"

# Drop any non-source artifacts that may have been copied from a dev tree.
find "$DEST" -name '__pycache__' -type d -prune -exec rm -rf {} +
find "$DEST" -name '*.pyc' -delete

echo "Synced: skills/claude-release-radar/ ← canonical root files"
