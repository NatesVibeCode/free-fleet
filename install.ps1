<#
.SYNOPSIS
  One-click installer for harness-fleet (Windows).

.DESCRIPTION
  Creates a private Python environment in this repo's `.venv`, installs the
  harness-fleet CLI into it, sets up a workspace, runs the offline demo, and
  registers the harness-fleet MCP tools with Claude Desktop (or Cursor).

  Usage:
    .\install.ps1 [workspace-directory]

  The workspace defaults to ~\harness-fleet-workspace when no argument is given.

.NOTES
  If PowerShell script execution is blocked, run this instead:

    powershell -ExecutionPolicy Bypass -File install.ps1
#>

$ErrorActionPreference = "Stop"

# Directory containing this script, resolved to an absolute path so the
# installer works regardless of the caller's working directory.
$scriptDir = $PSScriptRoot
if (-not $scriptDir) { $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }
if (-not $scriptDir) { $scriptDir = (Get-Location).Path }

$venvDir = Join-Path $scriptDir ".venv"
$venvPy  = Join-Path $venvDir "Scripts\python.exe"
$cli     = Join-Path $venvDir "Scripts\harness-fleet.exe"
$log     = Join-Path $venvDir "install.log"

# --- tiny, friendly output helpers ------------------------------------------

function Say([string]$Text)  { Write-Host $Text }
function Ok([string]$Text)   { Write-Host "  [OK]  $Text" -ForegroundColor Green }
function Warn([string]$Text) { Write-Host "  [!]   $Text" -ForegroundColor Yellow }
function Fail([string]$Text) {
  Write-Host "  [X]   $Text" -ForegroundColor Red
  exit 1
}

# --- 1. find a Python 3.10+ interpreter -------------------------------------

$script:pythonExe = $null
$script:pythonArgs = @()

function Test-PythonCandidate {
  param(
    [Parameter(Mandatory = $true)][string]$Exe,
    [string[]]$VersionArgs = @()
  )
  $cmd = Get-Command $Exe -ErrorAction SilentlyContinue
  if (-not $cmd) { return $false }
  # The Microsoft Store ships a stub python.exe that opens the Store instead of
  # running Python; skip it so we never pop up a window mid-install.
  if ($cmd.Source -and $cmd.Source -like "*\WindowsApps\*") { return $false }
  $code = 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)'
  try {
    & $Exe @VersionArgs -c $code *> $null
    return ($LASTEXITCODE -eq 0)
  } catch {
    return $false
  }
}

function Find-Python {
  # Prefer the `py` launcher (ships with python.org installs) and walk down from
  # the newest version; then fall back to a bare `python` / `python3` on PATH.
  $candidates = @(
    @{ Exe = "py"; Args = @("-3.14") },
    @{ Exe = "py"; Args = @("-3.13") },
    @{ Exe = "py"; Args = @("-3.12") },
    @{ Exe = "py"; Args = @("-3.11") },
    @{ Exe = "py"; Args = @("-3.10") },
    @{ Exe = "py"; Args = @() },
    @{ Exe = "python"; Args = @() },
    @{ Exe = "python3"; Args = @() }
  )
  foreach ($c in $candidates) {
    if (Test-PythonCandidate -Exe $c.Exe -VersionArgs @($c.Args)) {
      $script:pythonExe = $c.Exe
      $script:pythonArgs = @($c.Args)
      return $true
    }
  }
  return $false
}

Say "harness-fleet installer"
Say ""
Say "Step 1/8 - Finding Python 3.10+"
if (-not (Find-Python)) {
  Say ""
  Say "  Your Python is too old or missing."
  Say "  Install it with:  winget install Python.Python.3.13   (Windows)"
  Say "  or download from: https://www.python.org/downloads/"
  Say "  Then run this installer again."
  Say ""
  exit 1
}
Ok "Using $pythonExe $($pythonArgs -join ' ')"

# --- 2. create/reuse the virtualenv and install the package ------------------

Say ""
Say "Step 2/8 - Preparing a private Python environment (.venv)"
# Create the directory first so the log redirect below always has somewhere to write.
New-Item -ItemType Directory -Force -Path $venvDir | Out-Null
if (-not (Test-Path $venvPy)) {
  & $pythonExe @pythonArgs -m venv $venvDir *> $log
  if ($LASTEXITCODE -ne 0) { Fail "Could not create the .venv environment. See $log for details." }
}

# pip upgrades are a nice-to-have and fail harmlessly offline; never block on it.
& $venvPy -m pip install --upgrade pip *>> $log
if ($LASTEXITCODE -ne 0) {
  Warn "Could not upgrade pip (offline?). Continuing with the bundled version."
}

Say "Installing harness-fleet (this can take a minute the first time)..."
Push-Location $scriptDir
try {
  & $venvPy -m pip install . *>> $log
  $pipCode = $LASTEXITCODE
} finally {
  Pop-Location
}
if ($pipCode -ne 0) {
  Fail "Installing harness-fleet failed. See $log for details. (Usually a network problem reaching PyPI.)"
}

& $venvPy -c "import harness_fleet" *>> $log
if ($LASTEXITCODE -ne 0) {
  Fail "harness-fleet installed but could not be imported. See $log for details."
}
Ok "harness-fleet installed at $cli"

# --- 3. choose and create the workspace -------------------------------------

Say ""
Say "Step 3/8 - Creating the workspace"
$ws = if ($args.Count -ge 1) { $args[0] } else { Join-Path $HOME "harness-fleet-workspace" }
New-Item -ItemType Directory -Force -Path $ws | Out-Null
# Canonicalize to an absolute path. Every step below Push-Location's into the
# workspace, so a relative --db would otherwise resolve against the *new*
# working directory and land in a nested path.
$ws = (Resolve-Path -LiteralPath $ws).Path
Ok "Workspace at $ws"

# The database path is pinned explicitly (rather than relying on the default or
# the HARNESS_FLEET_DB environment variable) so every step below agrees on the
# same control-plane file.
$db = Join-Path $ws "harness-fleet.db"

# --- 4. configure the workspace (skills + database) --------------------------

Say ""
Say "Step 4/8 - Configuring the workspace"
Push-Location $ws
try {
  & $cli setup --workspace-root $ws --db $db *>> $log
  $setupCode = $LASTEXITCODE
} finally {
  Pop-Location
}
if ($setupCode -ne 0) { Fail "Workspace setup failed. See $log for details." }
Ok "Workspace configured"

# --- 5. refresh model routes (fixes fresh-DB onboarding; offline-safe) -------

Say ""
Say "Step 5/8 - Refreshing model routes (needs internet)"
Push-Location $ws
try {
  & $cli routes --db $db --refresh *>> $log
  $routesCode = $LASTEXITCODE
} finally {
  Pop-Location
}
if ($routesCode -eq 0) {
  Ok "Routes refreshed"
} else {
  Warn "Could not refresh routes (offline?). This is fine - the demo still works."
  Say "  Refresh later with:"
  Say "    $cli routes --db `"$db`" --refresh"
}

# --- 6. run the offline demo -------------------------------------------------

Say ""
Say "Step 6/8 - Running the offline demo (no API keys needed)"
$demoJson = Join-Path $ws "runs\demo-01\clean_packet.json"
$demoCsv  = Join-Path $ws "runs\demo-01\clean_packet.csv"
if ((Test-Path $demoJson) -and (Test-Path $demoCsv)) {
  Ok "Demo already present - skipping"
} else {
  Push-Location $ws
  try {
    & $cli quickstart --demo --run-id demo-01 --db $db *>> $log
    $demoCode = $LASTEXITCODE
  } finally {
    Pop-Location
  }
  if ($demoCode -ne 0) { Fail "The demo run failed. See $log for details." }
  Ok "Demo complete"
}
# Verify the expected outputs exist no matter which branch above ran.
if (-not (Test-Path $demoJson) -or -not (Test-Path $demoCsv)) {
  Fail "The demo did not produce its expected output files. See $log for details."
}

# --- 7. register with Claude Desktop / Cursor --------------------------------

Say ""
Say "Step 7/8 - Registering harness-fleet with Claude Desktop / Cursor"
# Desktop apps do not inherit this shell's environment, so hand the caller's
# OpenRouter key to the MCP server when one is set (the CLI never prints values).
$mcpInstallArgs = @("mcp", "install", "--workspace-root", $ws, "--db", $db)
if ($env:OPENROUTER_API_KEY) {
  $mcpInstallArgs += @("--env", "OPENROUTER_API_KEY")
}
& $cli @mcpInstallArgs *>> $log
if ($LASTEXITCODE -eq 0) {
  Ok "MCP server registered"
  if ($env:OPENROUTER_API_KEY) {
    Say "  OPENROUTER_API_KEY passed into the client config (value not shown)"
  }
} else {
  Warn "Could not register with Claude Desktop / Cursor automatically."
  Say "  Add this entry to your MCP client config manually, then restart the client:"
  $manualEntry = @{
    mcpServers = @{
      "harness-fleet" = @{
        command = $cli
        args    = @("serve", "--workspace-root", $ws, "--db", $db)
      }
    }
  } | ConvertTo-Json -Depth 5
  Say $manualEntry
}

# --- 8. getting free model access ------------------------------------------

Say ""
Say "Step 8/8 - Getting free model access (2 minutes)"
if ($env:OPENROUTER_API_KEY) {
  Ok "OpenRouter key detected - free OpenRouter models are ready"
} elseif (Get-Command opencode -ErrorAction SilentlyContinue) {
  Ok "OpenCode is installed - sign in once if you have not: opencode auth login"
} else {
  Warn "No free models are connected yet, so a real run cannot start."
  Say "  Pick whichever is easiest for you:"
  Say ""
  Say "  1. OpenRouter - one signup, works with every fleet:"
  Say "       https://openrouter.ai/          (create the account)"
  Say "       https://openrouter.ai/keys      (create a key, copy it)"
  Say "     then set it for your terminals:"
  Say "       setx OPENROUTER_API_KEY \"sk-or-...\""
  Say ""
  Say "  2. OpenCode - free hosted models:"
  Say "       npm install -g opencode-ai      (or: choco install opencode)"
  Say "       opencode auth login"
  Say ""
  Say "  3. Your own computer - no signup at all:  https://ollama.com/download"
  Say ""
  Say "  Full walkthrough, including what the free tiers actually allow:"
  Say "    $scriptDir\FREE-ACCESS.md"
}

# --- 8. summary --------------------------------------------------------------

Say ""
Say "--------------------------------------------------------------"
Say "  harness-fleet is ready!"
Say "--------------------------------------------------------------"
Say ""
Say "  Installed:"
Say "    Python environment : $venvDir"
Say "    harness-fleet CLI  : $cli"
Say "    Workspace          : $ws"
Say "    Demo CSV           : $demoCsv"
Say ""
Say "  Next steps:"
Say "    1. Restart Claude Desktop (or Cursor) now to load the harness-fleet tools."
Say "    2. Sanity check:  $cli doctor --workspace-root `"$ws`""
Say "    3. Settings UI:   $cli studio --workspace-root `"$ws`"  ->  http://127.0.0.1:8080"
Say ""
