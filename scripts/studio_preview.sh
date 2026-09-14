#!/usr/bin/env bash
# Launch the local harness studio against a disposable preview workspace.
#
# Usage:
#   scripts/studio_preview.sh [workspace] [port]
#
# Defaults: workspace .studio-preview/, port 8099. On first run it seeds an
# offline demo run (registers the zero-cost demo/fake route) and a scoring task,
# so the panel has something to edit immediately.
#
# Iterating on the UI: index.html is read from disk on every request, so edit
# harness_fleet/resources/studio/index.html and refresh the browser. No restart.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
workspace="${1:-$root/.studio-preview}"
port="${2:-8099}"

if [ -x "$root/.venv/bin/python" ]; then
  python="$root/.venv/bin/python"
else
  python="python3"
fi

mkdir -p "$workspace"
cd "$workspace"

cli() { PYTHONPATH="$root" "$python" -c "from harness_fleet.cli import main; main()" "$@"; }

if [ ! -f "$workspace/harness-fleet.db" ]; then
  echo "Seeding preview workspace at $workspace ..."
  cli quickstart --demo --run-id preview-seed >/dev/null
  cli init studio-demo --preset account-research >/dev/null
fi

echo "Studio workspace: $workspace"
echo "Open http://127.0.0.1:$port  (Ctrl-C to stop; browser refresh picks up index.html edits)"
exec env PYTHONPATH="$root" "$python" -c "from harness_fleet.cli import main; main()" studio --port "$port"
