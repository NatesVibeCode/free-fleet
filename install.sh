#!/usr/bin/env bash
#
# One-click installer for harness-fleet (macOS / Linux).
#
# Creates a private Python environment in this repo's `.venv`, installs the
# harness-fleet CLI into it, sets up a workspace, runs the offline demo, and
# registers the harness-fleet MCP tools with Claude Desktop (or Cursor).
#
# Usage:
#   ./install.sh [workspace-directory]
#
# The workspace defaults to ~/harness-fleet-workspace when no argument is given.

set -euo pipefail

# Resolve this script's own directory so the installer works no matter which
# directory the caller starts in (and even when invoked via a symlink).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

VENV_DIR="$SCRIPT_DIR/.venv"
VENV_PY="$VENV_DIR/bin/python"
CLI="$VENV_DIR/bin/harness-fleet"
LOG="$VENV_DIR/install.log"

# --- tiny, friendly output helpers ------------------------------------------

say()  { printf '%s\n' "$*"; }
ok()   { printf '  \342\234\223 %s\n' "$*"; }
warn() { printf '  \342\232\240 %s\n' "$*"; }
fail() {
  printf '  \342\234\227 %s\n' "$*" >&2
  exit 1
}

# --- 1. find a Python 3.10+ interpreter -------------------------------------

PYTHON_BIN=""

try_python() {
  # $1 = interpreter name or absolute path. Sets PYTHON_BIN and returns 0 when
  # the interpreter exists and is new enough.
  command -v "$1" >/dev/null 2>&1 || return 1
  "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1 || return 1
  PYTHON_BIN="$1"
}

find_python() {
  local v dir
  try_python python3 && return 0
  for v in 14 13 12 11 10; do
    try_python "python3.$v" && return 0
  done
  # Homebrew and similar install locations are not always on PATH, so check
  # them explicitly (newest version first).
  for dir in /opt/homebrew/bin /usr/local/bin; do
    [ -d "$dir" ] || continue
    for v in 14 13 12 11 10; do
      try_python "$dir/python3.$v" && return 0
    done
  done
  return 1
}

say "harness-fleet installer"
say ""
say "Step 1/7 — Finding Python 3.10+"
if ! find_python; then
  say ""
  say "  Your Python is too old or missing."
  say "  Install it with:  brew install python@3.13   (macOS)"
  say "  or download from: https://www.python.org/downloads/"
  say "  Then run this installer again."
  say ""
  exit 1
fi
ok "Using $PYTHON_BIN"

# --- 2. create/reuse the virtualenv and install the package ------------------

say ""
say "Step 2/7 — Preparing a private Python environment (.venv)"
# mkdir first so the log redirect below always has somewhere to write.
mkdir -p "$VENV_DIR"
if [ ! -x "$VENV_PY" ]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR" >"$LOG" 2>&1 \
    || fail "Could not create the .venv environment. See $LOG for details."
fi

# pip upgrades are a nice-to-have and fail harmlessly offline; never block on it.
if "$VENV_PY" -m pip install --upgrade pip >>"$LOG" 2>&1; then
  :
else
  warn "Could not upgrade pip (offline?). Continuing with the bundled version."
fi

say "Installing harness-fleet (this can take a minute the first time)…"
if ! ( cd "$SCRIPT_DIR" && "$VENV_PY" -m pip install . ) >>"$LOG" 2>&1; then
  fail "Installing harness-fleet failed. See $LOG for details. (Usually a network problem reaching PyPI.)"
fi

if ! "$VENV_PY" -c 'import harness_fleet' >>"$LOG" 2>&1; then
  fail "harness-fleet installed but could not be imported. See $LOG for details."
fi
ok "harness-fleet installed at $CLI"

# --- 3. choose and create the workspace -------------------------------------

say ""
say "Step 3/7 — Creating the workspace"
WS="${1:-$HOME/harness-fleet-workspace}"
mkdir -p "$WS" || fail "Could not create the workspace directory: $WS"
# Canonicalize to an absolute path. Every step below cds into the workspace, so a
# relative --db would otherwise resolve against the *new* working directory and
# land in a nested path (./install.sh myws created myws/myws/ and then failed).
WS="$(cd "$WS" && pwd)" || fail "Could not resolve the workspace directory: $WS"
ok "Workspace at $WS"

# The database path is pinned explicitly (rather than relying on the default or
# the HARNESS_FLEET_DB environment variable) so every step below agrees on the
# same control-plane file.
DB="$WS/harness-fleet.db"

# --- 4. configure the workspace (skills + database) --------------------------

say ""
say "Step 4/7 — Configuring the workspace"
if ! ( cd "$WS" && "$CLI" setup --workspace-root "$WS" --db "$DB" ) >>"$LOG" 2>&1; then
  fail "Workspace setup failed. See $LOG for details."
fi
ok "Workspace configured"

# --- 5. refresh model routes (fixes fresh-DB onboarding; offline-safe) -------

say ""
say "Step 5/7 — Refreshing model routes (needs internet)"
if ( cd "$WS" && "$CLI" routes --db "$DB" --refresh ) >>"$LOG" 2>&1; then
  ok "Routes refreshed"
else
  warn "Could not refresh routes (offline?). This is fine — the demo still works."
  say "  Refresh later with:"
  say "    $CLI routes --db \"$DB\" --refresh"
fi

# --- 6. run the offline demo -------------------------------------------------

say ""
say "Step 6/7 — Running the offline demo (no API keys needed)"
DEMO_JSON="$WS/runs/demo-01/clean_packet.json"
DEMO_CSV="$WS/runs/demo-01/clean_packet.csv"
if [ -f "$DEMO_JSON" ] && [ -f "$DEMO_CSV" ]; then
  ok "Demo already present — skipping"
else
  if ! ( cd "$WS" && "$CLI" quickstart --demo --run-id demo-01 --db "$DB" ) >>"$LOG" 2>&1; then
    fail "The demo run failed. See $LOG for details."
  fi
  ok "Demo complete"
fi
# Verify the expected outputs exist no matter which branch above ran.
if [ ! -f "$DEMO_JSON" ] || [ ! -f "$DEMO_CSV" ]; then
  fail "The demo did not produce its expected output files. See $LOG for details."
fi

# --- 7. register with Claude Desktop / Cursor --------------------------------

say ""
say "Step 7/7 — Registering harness-fleet with Claude Desktop / Cursor"
# Desktop apps do not inherit this shell's environment, so hand the caller's
# OpenRouter key to the MCP server when one is set (the CLI never prints values).
MCP_INSTALL_ARGS=(--workspace-root "$WS" --db "$DB")
if [ -n "${OPENROUTER_API_KEY:-}" ]; then
  MCP_INSTALL_ARGS+=(--env OPENROUTER_API_KEY)
fi
if "$CLI" mcp install "${MCP_INSTALL_ARGS[@]}" >>"$LOG" 2>&1; then
  ok "MCP server registered"
  if [ -n "${OPENROUTER_API_KEY:-}" ]; then
    say "  OPENROUTER_API_KEY passed into the client config (value not shown)"
  fi
else
  warn "Could not register with Claude Desktop / Cursor automatically."
  say "  Add this entry to your MCP client config manually, then restart the client:"
  cat <<JSON
{
  "mcpServers": {
    "harness-fleet": {
      "command": "$CLI",
      "args": ["serve", "--workspace-root", "$WS", "--db", "$DB"]
    }
  }
}
JSON
fi

# --- 8. summary --------------------------------------------------------------

say ""
say "──────────────────────────────────────────────────────────────"
say "  harness-fleet is ready!"
say "──────────────────────────────────────────────────────────────"
say ""
say "  Installed:"
say "    Python environment : $VENV_DIR"
say "    harness-fleet CLI  : $CLI"
say "    Workspace          : $WS"
say "    Demo CSV           : $DEMO_CSV"
say ""
say "  Next steps:"
say "    1. Restart Claude Desktop (or Cursor) now to load the harness-fleet tools."
say "    2. Sanity check:  $CLI doctor --workspace-root \"$WS\""
say "    3. Settings UI:   $CLI studio --workspace-root \"$WS\"  →  http://127.0.0.1:8080"
say ""
