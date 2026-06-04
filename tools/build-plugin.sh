#!/usr/bin/env bash
# Builds the distributable Claude Desktop plugin file.
# Output: dist/claude-release-radar.plugin

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="$ROOT/dist"
OUT_FILE="$OUT_DIR/claude-release-radar.plugin"

# Always sync first so the .plugin reflects the canonical root files.
bash "$ROOT/tools/sync-skill.sh"

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

cd "$ROOT"
zip -r "$OUT_FILE" \
  .claude-plugin \
  skills \
  README.md \
  LICENSE \
  -x "*.DS_Store" "*/__pycache__/*" "*.pyc"

echo ""
echo "Built: $OUT_FILE"
echo "Contents:"
unzip -l "$OUT_FILE"
