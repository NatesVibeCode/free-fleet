# Fleet rename to harness-fleet + universal harness providers + lint plan

Supersedes `2026-09-13-fleet-packaging-lint.md` (kept for history; its ruff/mypy
content is carried forward here as Phase L0/L1, and its Phase 2A is replaced by
the rename below). Extended with Phase H (universal harness providers, no
OpenCode preference) per user direction, guided by the seven
`*-harness-handoff` skills in `~/.claude/skills/`.

## Goal

Rename everything brand-bearing to `harness-fleet` — repo, distribution,
package, CLI, MCP surface, skills, docs — in bulk-lanes, with the same engine
rename mirrored to account-fleet and career-fleet, then make the provider
layer harness-agnostic (OpenCode becomes one of seven equal CLI-harness
providers, with no default preference anywhere), then land the ruff and mypy
gates. Stored values cut over via a tested migration; runtime behavior does
not change except the specified registry fallback removal (fail-closed).

## Success Criteria

- bulk-lanes is `harness-fleet` everywhere a user or installer can see:
  directory, GitHub repo, PyPI name, package `harness_fleet/`, single `harness-fleet`
  console script, MCP server + all 17 tools, skill name + install paths, docs.
- account-fleet and career-fleet keep their product/dist names and CLIs; their
  engine copy is the same renamed `harness_fleet` package, byte-identical per
  the drift contract.
- Triaged-grep gate: no `free_fleet` / `free-fleet` / `FreeFleet` /
  `bulk_lanes` / `bulk-lanes` / `BulkLanes` / `bulk_meta` / `FREE_FLEET_*` /
  `BULK_LANES_*` remains except the keep-list (§Rename Map: cost domain,
  product names) and the one migration-notes section per repo README.
- Suites green at prior counts (407 / 408 / 453); drift script clean apart
  from the accepted career `cli.py` overlay; `check_wheel.py` + `uv tool
  install` round-trip pass per repo.
- Seven equal CLI-harness providers (opencode, claude, codex, cursor, grok,
  muse, antigravity) behind one typed `HarnessSpec`/`CLIHarnessProvider`
  interface; argv is always a structured list, never a built string, and
  `shell=True` appears nowhere.
- No default preference anywhere: registry resolves explicit provider names
  only (prefix-sniffing, substring matching, and the opencode default
  fallback are all deleted); unknown providers fail closed with a typed
  error; doctor/setup/skills treat all harnesses equally.
- Ruff gate (curated set) and mypy baseline gate green in CI, all repos.
- Zero behavior change; zero data loss: old SQLite workspaces auto-migrate
  on open (values rewritten, CHECK rebuilt, `bulk_meta` renamed — proven by
  an upgrade test with row-count asserts); old packets are re-exported from
  SQLite (single-value read, no dual-read).

## Context And Current Facts

- bulk-lanes remotes: `origin → NatesVibeCode/free-fleet.git` (repo exists,
  PyPI `free-fleet` v0.2.4 is also ours) plus a second remote
  `account-fleet → NatesVibeCode/account-fleet.git` (purpose unknown —
  untouched by this plan). Current branch: `sync/upstream-scoring`.
  `harness-fleet` is free on PyPI (404) and GitHub (404); no publishing in
  this plan, so availability is context only.
- Brand-string footprint in bulk-lanes: **80 tracked files** (tests 33,
  `free_fleet/` 7 + providers 3, schemas 5, skill copies ×9 paths, scripts 2,
  examples 4, migrations 1, plus README/CONTRIBUTING/SECURITY/`.env.example`/
  `pyproject.toml`/`.mmd`), plus known **untracked live files**
  (`free_fleet/calibrate.py`, `free_fleet/candidates.py`,
  `tests/test_calibrate.py`, `tests/test_mechanical_calibration.py`) that the
  suites run against and must be renamed too. Sibling footprints are near-identical;
  each phase starts by re-inventorying (`git status --short` + brand grep).
- Precedent: `bulk-lanes` is already deprecated in favor of `free-fleet`
  (`_maybe_emit_deprecation_notice`, "removed in 0.3.0"). This rename finishes
  that direction; the deprecation shim is deleted, not extended.
- argv[0]-sensitive code: `_package_version` dist lookup table, `prog=`,
  `mcp install` server key, and one self-invocation (`cli.py:476`
  `"free-fleet", "validate", ...`) — all renamed, covered by suites.
- Wire/data values carrying brand (see D2 for the hard-cutover verdicts):
  - task rows: `free_fleet_task_v1` / `bulk_lanes_task_v1` — in a Pydantic
    `Literal`, a SQLite `CHECK` constraint (migration 001), and every stored row.
  - packet exports: `free_fleet_v2` / `bulk_lanes_v2` — Pydantic `Literal` only.
  - run rows: `free_fleet_run_v1` — written once (`store.py:905`), never
    validated anywhere.
  - table `bulk_meta` (2 code sites: schema_version INSERT/SELECT) — the only
    branded table/column name in the schema.
  - `migrate()` runs on every `Store.__init__`, before any read — so cutover
    logic there upgrades old DBs transparently on first open.
- `career_fleet/` (career-only product, no MCP surface) imports the engine in
  exactly one file (`lanes/lane1_sourcing.py`: docstring + import + error
  string).
- `SCHEMA_BASE` points at the `free-fleet` GitHub repo (`.../master/schemas`);
  branch segment untouched by this plan (separate issue if wrong).
  `test_published_schemas.py` compares `schemas/*.json` to runtime models
  locally (no network) — schema files must be regenerated after model edits.
- Env/DB today: `ACCOUNT_FLEET_DB → FREE_FLEET_DB → BULK_LANES_DB` fallback
  chain (historical accumulation, not product routing) and default file
  `free-fleet.db`, in drift-synced files (`cli.py`, `mcp_server.py`,
  `setup.py`).
- `.gitignore` already covers `build/`, `dist/`, `*.egg-info/` — stale
  generated dirs on disk need no cleanup and regenerate under new names.
- OpenCode-only preference inventory (all drift-synced unless noted):
  `registry.resolve()` default-falls-back to opencode (plus route-id
  prefix-sniffing and an `"openrouter" in route_id` substring check);
  `configured_routes()` special-cases opencode; opencode is the sole
  CLI-harness provider; `catalog.refresh_from_opencode()` (+ `refresh_all`
  entry); `engine.opencode_prov` seam (used by `tests/test_engine.py`);
  `routes.seed.json` seeds opencode/openrouter only (31 routes, rev 2);
  CLI + MCP doctor check only the `opencode` binary; skill invariant #7
  mandates the OpenCode transport; operations.md transports list + stops;
  README/CONTRIBUTING/account-skill wordings.
- Provider mechanics today: `BaseProvider.run_prompt(route_id, prompt,
  ...) -> (ok, text, receipt)`; `OpenCodeProvider` builds list-argv
  `run --format json --model M <prompt>`, runs via an injectable runner
  (temp-dir + task-local `opencode.json` deny-all config), parses JSONL
  events (`text`/`step_finish`/`error`), and builds the standard receipt.
  `tests/test_opencode.py` is the fake-runner test template to copy per
  harness (argv asserts, event parsing, missing-cost-unknown, timeout).
- Per-harness CLI contracts (mined from the seven handoff skills — the
  implementer follows this table, never invents a flag):

  | Harness | Binary | Headless run (prompt delivery) | Output shape | Discovery | Continue (NOT implemented) |
  |---|---|---|---|---|---|
  | opencode | `opencode` | `run --dir W --format json [--model M] [--file F] MSG` (argv msg) | JSONL events: text / step_finish(cost,tokens) / error | `opencode models ...` | `--session` |
  | claude | `claude` | `-p --output-format json` (stdin from prompt file) | single JSON object (result + usage) | binary + `--version` only | `--resume` |
  | codex | `codex` | `exec -C W --json -o OUT -` (stdin from prompt file) | JSONL events | binary + `--version` only | none (its skill mandates fresh-only) |
  | cursor | `cursor-agent` | `--workspace W --print --output-format json TASK` (prompt as ONE argv element — no file flag; never shell) | JSON object (conservative extraction) | `cursor-agent models` | `--resume` |
  | grok | `grok` | `--cwd W --prompt-file F --output-format json` (file flag) | JSON object (conservative extraction) | binary + `--version` only | `--resume` |
  | muse | `muse` | `exec --json --workspace W --worktree off --prompt-file F` (file flag) | JSON object (conservative extraction) | binary + `--version` only | interactive-only (fresh-only) |
  | antigravity | `agy` | `--output-format json --print TASK` (prompt as ONE argv element) | JSON object (conservative extraction) | binary + `--version` only | `--conversation` |

### Handoff context (do not re-derive)

- Drift contract: `free_fleet/*.py` (+ route-policy test, operations.md
  copies, routes seed, the drift script itself) must land byte-identical in
  all three repos. After R1 the synced paths are `harness_fleet/*.py` and
  the script is `scripts/check_harness_drift.py` — same rule, new paths.
- `pyproject.toml`, CI, `check_wheel.py`, skill `SKILL.md` files, READMEs
  are per-repo: change per repo, keep conventions aligned.
- Synced docs (operations.md) use the harness CLI name in all three repos —
  status-quo pattern (they say `free-fleet` everywhere today, including in
  account-fleet); preserved, not fixed.
- Each repo's git history is independent; no history rewrite anywhere.
- Prior green counts 407 / 408 / 453; prior commits `22eb657` / `41b9690` /
  `2ad2a02`.
- Phase H guide: the seven `*-harness-handoff` skills under
  `~/.claude/skills/` (claude 139 lines, codex 65, cursor 103, grok 125,
  muse 96, antigravity 94, opencode 101; each has `references/` with
  history-and-continuation notes). The contracts table above is mined from
  their CLI recipes; the implementer consults the skills only for
  discrepancies, never for new flags.

### Rename Map (normative — the implementer follows this table, not judgment)

| # | Old | New | Scope |
|---|---|---|---|
| R1 | local dir `bulk-lanes/` | `harness-fleet/` | harness repo, plain `mv` at end of R1 |
| R2 | GitHub `NatesVibeCode/free-fleet` | `NatesVibeCode/harness-fleet` | USER manual step (gate before remote-url update) |
| R3 | `origin` remote URL | new repo URL | implementer, after R2; second remote `account-fleet` UNTOUCHED |
| R4 | pyproject `name = "account-fleet"` + desc/URLs | `name = "harness-fleet"`, harness desc, harness URLs | harness repo; version → 0.3.0 per R22 |
| R5 | package dir `free_fleet/` | `harness_fleet/` (`git mv`) | all three repos |
| R6 | console scripts | harness: `{harness-fleet}` only; account: `{account-fleet}` only; career: `{career-fleet, career-lanes}` only — all engine aliases deleted | per repo |
| R7 | `FreeFleetStore` + `BulkLanesStore =` alias | single `HarnessStore`, alias deleted | all three repos (drift-synced) |
| R8 | MCP server name + `mcpServers` key + 17 `free_fleet_*` tools | `harness-fleet` / `harness_fleet_*` | all three repos (drift-synced) + skill references |
| R9 | skill dirs `skills/free-fleet`, `.agents/skills/free-fleet`, `resources/skill` | `.../harness-fleet`, `resources/harness_skill`; frontmatter `name:` likewise; `setup.py` destination + source paths | per repo, same map |
| R10 | `prog=`, argv dispatch table, `_package_version` names, self-invoke string | harness-fleet entries; bulk-lanes/free-fleet entries removed | all three repos |
| R11 | `_maybe_emit_deprecation_notice` + call | DELETED (no bulk-lanes name left to warn about) | all three repos |
| R12 | default DB `free-fleet.db`; env chain | `harness-fleet.db`; single `HARNESS_FLEET_DB` | all three repos + `.env.example` |
| R13 | `SCHEMA_BASE` repo segment | `harness-fleet` (branch segment untouched); regenerate `schemas/*.json` from models | all three repos |
| R14 | packet `format_version` | single value `harness_fleet_v2` for writes AND reads (old packets re-exported) | models Literal + export write + tests |
| R15 | run `format_version` write | `harness_fleet_run_v1` | store.py (write-only, no readers) |
| R21 | task values + CHECK + `bulk_meta` table | values → `harness_fleet_task_v1` (single-value Literal); 001 CHECK text → new value; `bulk_meta` → `harness_meta`; `migrate()` rewrites old rows (guarded `UPDATE`), rebuilds the CHECK (guarded table rebuild from live `PRAGMA table_info` + new CHECK), renames the table (guarded `ALTER TABLE ... RENAME`), all idempotent | store.py + 001 SQL + tests (incl. new upgrade test) |
| R22 | version | `0.3.0` in pyproject + `__version__` | all three repos (breaking rename; matches the old "removed in 0.3.0" promise) |
| R16 | drift script paths + discovery dir + filename + docstring | `harness_fleet/*`, `harness-fleet`, `check_harness_drift.py`; CI invocations updated | all three repos |
| R17 | `check_wheel.py` import + `--distribution` choices + smoke names | per-repo names | per repo (not synced) |
| R18 | README/CONTRIBUTING/SECURITY/examples/`.mmd`/skill bodies/`mcp-recipes` | mechanical renames; SECURITY repo URL after R2 | per repo |
| R19 | `career_fleet/lanes/lane1_sourcing.py` 3 lines | harness import/docstring/error | career only |
| R20 | tests (imports, store names, db/env names, tool names, packet asserts) | mechanical | per repo |

KEEP — never renamed (triaged, with reason):

- Cost domain: `free_only`, `--free-only`, `--free`, `price_observed_zero`,
  "free route(s)/model(s)", "free and local", "Free/Local" prose, and "bulk"
  prose ("bulk classification" — domain language, not the `bulk_meta` table).
- Product names: `account-fleet`, `career-fleet`, `career-lanes`, account
  skill, career product surface.
- Branch names, git history, the `account-fleet` remote.
- Migration-note docs: each repo README gains ONE "Migrating from free-fleet"
  section that legitimately names old strings (`db backup` first, then `mv
  free-fleet.db harness-fleet.db`, MCP re-install, skill re-setup,
  re-export old packets). The grep gate allows old-name hits only inside
  these sections plus the keep-list above.

## Constraints And Non-goals

- **No behavior changes.** The rename is identifiers + strings + paths only.
  Any diff that changes executed logic is out of scope.
- **Forward-only data cutover, no downgrade.** Old DBs auto-migrate on first
  open (R21); there is no path back except restoring the user's own `db
  backup` (migration note leads with it). No new `.sql` migration file —
  cutover lives as guarded inline logic in `migrate()`, so the drift file
  list stays untouched.
- **No repo merge, no shared fourth package, no package splitting.** Engine
  stays mirrored; one-fleet-per-environment stays documented; extraction
  remains the follow-up 2B.
- **No `ruff format`, no `--strict`, no Docker, no PyInstaller** (carried from
  the superseded plan with the same rationale and reopen triggers).
- **No pushes, publishes, or tags.** The GitHub repo rename and any PyPI
  reservation are explicit USER steps; the implementer touches only local git
  state (commits still need their own per-unit ask).
- **No GitHub redirect reliance.** Nothing in the plan assumes renamed-repo
  redirects work; all references are updated to final URLs.
- **No stringly harness layer.** argv is `list[str]` built from typed
  `HarnessSpec` fields — no format-string commands, no `shell=True`
  anywhere, prompt text never interpolated into a command line (file,
  stdin, or single argv element per spec). Registry dispatch uses the
  explicit `provider` field only — no prefix-sniffing, no substring
  matching, no silent default.
- **No invented harness surface.** Every flag, command, and output shape
  must cite its handoff skill; no invented model IDs (hence no new route
  seeds), no guessed JSON keys beyond documented + conservative fallbacks.
- **No approval-bypass flags in providers.** Fleet workers run tool-less
  JSON prompts unattended; a harness demanding approvals for that fails
  closed with an error receipt. This deliberately deviates from the codex
  skill's bypass-by-default (different use: agentic coding vs batch
  inference) — see D11.
- **No session/continue/resume implementation.** The engine fresh-runs every
  prompt (as today — `session_id` is echoed in receipts, never executed);
  continue commands stay documented-but-unimplemented. No MCP transports,
  servers, relays, or lane managers (every handoff skill forbids them).

## Key Decisions

- **D1 — Same engine rename in all three repos (R5–R22 apply everywhere
  marked).** Alternatives: (a) path-mapped drift (siblings keep `free_fleet/`)
  — rejected: every future mirror would need translation and the drift
  script would compare unlike paths; (b) extraction now — rejected: unscoped
  (still 2B follow-up). Uniform rename keeps the drift contract byte-identical
  and the mirror workflow mechanical. Account/career keep their dist names,
  product CLIs, and skills — only the engine copy is renamed.
- **D2 — Wire values: hard cutover, tables included (user-directed).**
  Single new values everywhere: task rows → `harness_fleet_task_v1` (rows
  rewritten, CHECK rebuilt, `bulk_meta` → `harness_meta`), packets →
  `harness_fleet_v2` for reads and writes, runs → `harness_fleet_run_v1`.
  Cutover runs inside `migrate()` on first open (guarded, idempotent), fresh
  DBs get new DDL text, and an upgrade test with row-count asserts proves no
  data loss. Old packets are re-exported from SQLite (the record), not
  dual-read. Downgrade is unsupported — the migration note leads with `db
  backup`. The sharpest boundary is now the reverse: the ONLY old strings
  left anywhere are cost-domain words, product names, and the migration
  notes themselves.
- **D3 — Single `HARNESS_FLEET_DB`.** The 3-var chain exists for past renames,
  not product routing, and shared engine code must stay byte-identical, which
  forbids per-repo var names. One name, documented; old vars stop working
  (migration note covers it).
- **D4 — DB filename: rename + docs `mv`, no fallback reader.** Explicit
  beats magic; fallback chains are exactly the legacy this project deletes.
- **D5 — One script per product (R6), deprecation shim deleted (R11).**
  No compat aliases: anyone invoking `free-fleet`/`bulk-lanes`/`account-fleet`
  from the wrong install gets "command not found" and the migration note.
  Precedent supports this (bulk-lanes was already slated for removal).
- **D6 — Ruff (curated, no S/BLE/TRY, no format) then mypy baseline (no
  strict), same as the superseded plan.** Order changes: lint runs AFTER the
  rename (Phase L) so fixes land once on final names and the grep-zero gate
  validates the finished tree.
- **D7 — Every dist ships its runtime.** Correction of the superseded plan's
  career wheel-exclusion idea: excluding the engine from career's wheel while
  account's wheel ships it was inconsistent. All three wheels ship what their
  CLI imports; one-fleet-per-environment stays documented; extraction stays 2B.
- **D8 — Version bump to 0.3.0 in all three repos (R22).** A breaking rename
  (entry points, MCP names, DB cutover, no downgrade) earns a minor bump;
  it also fulfills the old "bulk-lanes removed in 0.3.0" promise. pyproject
  + `__version__` move together; approval of this plan covers it.
- **D9 — Universal provider = typed `HarnessSpec` + `CLIHarnessProvider`,
  one spec per harness.** New `providers/harness.py` holds a `ClosedModel`
  spec (binary, argv template over typed fields, prompt-delivery enum
  {argv_last, stdin, file_flag}, parser id, task-config strategy, discovery
  argv or None) and a `BaseProvider` that detects the binary, stages the
  prompt, builds `list[str]` argv, runs via the existing injectable-runner
  pattern, parses per spec, and builds the standard receipt. Each adapter
  (`opencode`, `claude`, `codex`, `cursor`, `grok`, `muse`, `antigravity`)
  is a spec + a small parser (~20 lines) + availability. Model derivation
  from `route_id` lives in exactly one validated `split_route()` helper
  (typed error on malformed input); opencode keeps its tested
  native-prefix rule as an override.
- **D10 — Registry resolves explicit provider names only; everything else
  raises.** `resolve()` drops prefix-sniffing, the `"openrouter" in
  route_id` substring check, and the opencode default fallback, and takes
  the explicit name (engine call sites updated; missing/unknown →
  `ProviderResolutionError` naming the available providers). Routes must
  declare `provider` — fail-closed at dispatch, never silent-opencode.
  `configured_routes()` generalizes: a harness route is available iff its
  binary is on PATH (same rule for all seven).
- **D11 — Tool lockdown: opencode keeps its deny-all config; cursor passes
  skill-documented `--sandbox enabled`; the rest are prompt-level only;
  bypass flags nowhere.** Rationale: only opencode documents a task-local
  deny-all config; cursor's sandbox flag is the safe direction and is
  covered by its live smoke; anything else would be invented surface.
  Anything demanding approvals for a tool-less prompt fails closed.
- **D12 — Discovery only where the guide documents a command
  (opencode + cursor `models`); no new route seeds, ever.** `refresh_all()`
  keeps its `{provider: count}` shape; discovery-less harnesses contribute
  0 with a code-comment reason, and per-harness availability is surfaced by
  the doctor matrix instead. Routes for new harnesses enter via `routes
  add` / refresh — model IDs are never invented.

## Recommended Approach

Order: R1 (harness repo rename, ends with local dir `mv`) → R2 (sibling
mirror) → H0 (provider base + opencode port, zero behavior change) → H1
(six adapters + registry/catalog/skills/doctor, the behavior-change seam) →
L0 (ruff) → L1 (mypy) → P (verification-only). H runs after the rename so
new provider files are born with final names; lint stays last. Each phase
ends with suites + drift re-verification. User steps (GitHub rename,
workspace/skill/MCP re-setup) are placed as explicit gates, never assumed
done. Publish as one commit per repo per content phase (R1 ×1, R2 ×2, H0
×3, H1 ×3, L0 ×3, L1 ×3 = 15 commits), in phase order — binding at publish;
each commit still needs its own explicit ask.

## Work Plan

### Phase R1 — Rename the harness repo (bulk-lanes → harness-fleet)

Steps in order (implementer runs `git status --short` + brand-grep count
first to confirm the inventory, including untracked live files):

1. Code: `git mv free_fleet harness_fleet`; plain-`mv` + `git add` the
   untracked live files into the new dir; apply R5/R7/R8/R10/R11/R12/R15
   (imports, store class + usages, MCP names, argv/prog/self-invoke,
   deprecation deletion, env/db); models/store edits for R13/R14/R21
   (single-value Literals, 001 DDL text, `migrate()` cutover logic);
   `test_published_schemas`-driven schema regen comes with the models edit.
2. Tests: R20 renames (task AND packet asserts → new values); add the
   required upgrade test — build an old-shape DB by raw SQL in tmp_path
   (old CHECK, old row values, `bulk_meta` table), open it with the new
   Store, assert values rewritten, CHECK text updated, table renamed,
   row counts preserved, and re-open idempotent; plus minimum new-name
   coverage (argv dispatch, `mcp install` key) and nothing else.
3. Skills: R9 dir/file/frontmatter renames across `skills/`, `.agents/`,
   `resources/`; update command + MCP-tool references in bodies and
   `mcp-recipes.md`; keep the three skill copies byte-identical (existing
   sync test enforces it).
4. Packaging/meta: R4/R6/R16/R17/R18/R22 (pyproject incl. 0.3.0, scripts,
   drift script + CI invocations, check_wheel, docs); README gains the
   migration-notes section (KEEP carve-out: `db backup` first, `mv`,
   re-setup, re-export packets); `.env.example`, `.mmd`, SECURITY (URL
   text now, valid after user step U1).
5. Local gates, then commit (on explicit ask), then `mv bulk-lanes
   harness-fleet`, then re-verify from the new path (suite + drift
   `--self` + `check_wheel --distribution harness-fleet`).
6. After user step U1 (GitHub rename): `git remote set-url origin
   <harness-fleet URL>` + `git ls-remote origin HEAD` read-only check. The
   `account-fleet` remote is not touched.

Boundaries — does NOT touch: cost-domain vocabulary; `career_fleet/`
(other repo); lint config (Phase L); PyPI; behavior beyond the specified
cutover. Sync obligation: none yet (siblings still old) — but every edit
must follow the Rename Map verbatim so R2 is mechanical.

### Phase R2 — Mirror the engine rename to account-fleet + career-fleet

Per sibling, same inventory-first step, then:

- account-fleet: R5/R7/R8/R10/R11/R12/R13/R14/R15/R16/R20/R21 + skills R9
  + docs R18; pyproject keeps `name = "account-fleet"` (+ 0.3.0 bump R22);
  scripts trimmed to `{account-fleet}` (R6); check_wheel keeps
  `--distribution account-fleet` with updated import/smoke names.
- career-fleet: same engine map; R19 lane import; pyproject keeps
  `name = "career-fleet"` (+ 0.3.0 bump R22); scripts trimmed to
  `{career-fleet, career-lanes}` (the three engine aliases deleted — same
  breaking-intentional rule); `career_fleet/` product code otherwise
  untouched; check_wheel keeps `--distribution career-fleet` with updated
  names.
- career `cli.py` overlay: re-apply the rename inside the overlay hunks the
  same way (it stays the accepted drift).

Boundaries — does NOT touch: product names/CLIs/skills, cost vocabulary,
behavior beyond the specified cutover. Sync obligation: FULL — every
drift-synced file
must be byte-identical across all three repos afterward (except the career
`cli.py` overlay); the drift script gates each sibling commit.

### Phase H0 — Universal provider base + opencode port (zero behavior change)

Per repo (mirrored byte-identical — all touched files are drift-synced):

1. New `providers/harness.py`: `HarnessSpec` (ClosedModel per D9),
   `CLIHarnessProvider(BaseProvider)` implementing the detect → stage →
   build-argv → run → parse → receipt flow over the existing
   injectable-runner pattern, and the single validated `split_route()`
   helper. `shell=False` always; no `shell=True` string anywhere (gate).
2. Port `providers/opencode.py` to a thin spec + parser + provider
   preserving its exact argv, task-local deny-all config, event parsing,
   receipt shape, and constructor (`OpenCodeProvider(runner=...)`).
   `tests/test_opencode.py` must pass without H0 modifying it (plus new
   spec tests for the base: argv-list type asserts, prompt-delivery modes,
   malformed route error, timeout receipt).

Boundaries — does NOT touch: registry dispatch (still old behavior),
other providers, catalog, engine, seeds, doctor, skills, or any behavior.
Sync obligation: FULL — new and ported files byte-identical across repos;
drift gates each commit.

### Phase H1 — Six adapters + preference removal (the behavior-change seam)

Per repo (mirrored byte-identical unless marked per-repo):

1. New adapters `providers/claude.py`, `codex.py`, `cursor.py`, `grok.py`,
   `muse.py`, `antigravity.py`: spec + ~20-line parser + availability,
   argv/flags strictly from the contracts table; each cites its handoff
   skill in a code comment. Parsers: documented shapes exact (opencode
   events, claude object, codex JSONL); cursor/grok/muse/agy conservative
   extraction (documented keys, then `text`/`result`/`output`/`message`/
   `content` and `usage`/`tokens`/`cost` fallbacks) that fails closed to
   an error receipt when no text is found — never garbage.
2. Registry: register all seven; `resolve()` takes the explicit provider
   name only (prefix-sniff, substring check, and opencode default all
   deleted; unknown → `ProviderResolutionError` listing available
   providers); engine call sites updated (found via grep; suites prove);
   `configured_routes()` generalized to binary-on-PATH for all harnesses.
3. Engine seam: replace `engine.opencode_prov` property with generic
   `engine.set_provider(name, provider)` (+ getter as needed); update the
   `tests/test_engine.py` call sites. The `openrouter_prov` seam is NOT
   touched (not a harness; out of scope).
4. Catalog: generic `refresh_from_harness(spec)`; opencode keeps its exact
   behavior through it; cursor gains `models` discovery; the other five
   are `discovery: none` (0 count + code-comment reason);
   `refresh_all()` keeps `{provider: count}` shape. NO seed changes (D12).
5. Doctor (CLI + MCP): single-binary opencode check → per-harness matrix
   (one `DoctorCheck` per spec: binary path or "not found in PATH").
6. Skills + docs (per-repo, same map): invariant #7 rewritten
   harness-neutral (task-local lockdown where the harness documents one;
   prompt-level JSON-only otherwise; bypass flags never); operations.md
   transports list + stops line; README/CONTRIBUTING/account-skill
   wordings; all skill copies kept byte-identical.
7. Tests: per-adapter stub-test file mirroring `test_opencode.py` (argv
   asserts incl. `isinstance(argv, list)`, parsing incl. missing-cost and
   error/timeout receipts); registry tests (explicit resolve ×7,
   unknown-raises, no-default); `configured_routes` matrix test
   (monkeypatched `which`); doctor matrix test; new
   `tests/test_harness_live.py` with per-harness opt-in skips
   (`skipif(shutil.which(...) is None)`) running one PING prompt through
   the real binary and asserting a complete receipt containing PING.

Boundaries — does NOT touch: session/continue/resume (unimplemented by
design); MCP transports/servers/relays; route seeds; `openrouter_prov`
seam; non-harness providers; behavior of opencode runs (same argv, same
receipts). Sync obligation: FULL on code + synced docs; skill SKILL.md
files per-repo same-map; new tests same-content by convention.

### Phase L0 — Ruff gate (on the renamed tree)

Identical to the superseded plan's Phase 0 with new paths: `[tool.ruff]`
per repo (curated select, `py310`, no line-length), `ruff check --fix` for
enabled rules only, hand-triage of the 2 PLR0124 findings, one CI step +
one CONTRIBUTING line per repo. Boundaries unchanged: no `ruff format`, no
S/BLE/TRY churn, no behavior, `career_fleet/` linted with no mirror
obligation. Sync obligation: same-fix-same-bytes across repos, drift-gated.

### Phase L1 — mypy baseline gate (on the renamed tree)

Identical to the superseded plan's Phase 1: `[tool.mypy]` per repo
(`python_version 3.10`, `warn_unused_ignores`), annotations-only diffs,
narrow per-file ignores for providers/CLI, one CI step + one CONTRIBUTING
line. Boundaries unchanged: no `--strict`/`disallow_any_*`, no executed-code
changes, minimal test annotations. Sync obligation: same as L0.

### Phase P — Distribution verification (no code; gates the whole plan)

Per repo from a clean checkout state: `check_wheel.py --distribution <name>`;
fresh-venv wheel install + `<cli> --help` + one JSON smoke (`--help` counts
only with `--json`-shaped output check where applicable — reuse the wheel
script's smoke, don't invent new ones); `uv tool install <repo-path>` →
`<cli> --help` → `uv tool uninstall <name>` round-trip; document the
one-liner + one-fleet-per-environment note in README/CONTRIBUTING (this
docs touch rides in the R1/R2 commits, not a new commit — P itself is
verification-only).

### User steps (explicit gates, not implementer work)

- U1 (before R1 step 6): rename GitHub `NatesVibeCode/free-fleet` →
  `NatesVibeCode/harness-fleet`.
- U2 (after R1): in own workspaces, `db backup` first, then `mv free-fleet.db
  harness-fleet.db`, re-run setup (skill reinstall), re-run `mcp install`
  for client configs, re-export any kept packets (old ones no longer read).
- U3 (optional, any time): reserve `harness-fleet` on PyPI. No publishing
  in this plan.

## Validation Plan

- **Rename gate (R1 per repo, R2 per repo):** triaged grep
  `git grep -nE "free_fleet|free-fleet|FreeFleet|BulkLanes|bulk-lanes|bulk_lanes|bulk_meta|FREE_FLEET|BULK_LANES" -- . ':!*.pyc' ':!.agents/plans'`
  filtered against the KEEP list — every remaining hit must be a keep-list
  string (cost domain, product names) or inside the README migration-notes
  section, otherwise the phase fails. (Plans dir excluded: plan docs
  legitimately name old strings.)
- **R1 gate:** suite green (407 + new upgrade/coverage tests); `check_wheel.py
  --distribution harness-fleet` passes; drift `--self` passes (intra-repo);
  post-`mv` re-run of all three from the new path; `git ls-remote origin
  HEAD` succeeds after step 6.
- **Upgrade gate (R1 + R2, part of the suite):** the new upgrade test builds
  an old-shape DB (old CHECK, old row values, `bulk_meta`), opens it, and
  asserts rewritten values, rebuilt CHECK, renamed table, preserved row
  counts, and idempotent re-open. A red upgrade test blocks the phase even
  if everything else is green.
- **R2 gate (per sibling):** suite green (408 / 453 + new upgrade/coverage tests); full cross-repo
  `check_harness_drift.py` clean except the career `cli.py` overlay;
  `check_wheel.py` per repo passes.
- **H0 gate (per repo):** `tests/test_opencode.py` passes unmodified by H0
  (as left by R2 — H0 must not touch the file); new spec tests green; full
  suite green; drift clean; `git grep -n "shell=True" -- providers/`
  empty; `git diff` review confirms the port changed structure only (same
  argv, same receipts).
- **H1 gate (per repo):** six adapter stub-test files green; registry
  tests prove explicit-resolve ×7 and unknown-raises (and that no
  prefix/substring/default path survives — grep `re.split\|in route_id`
  in `registry.py` must be empty); engine seam tests updated + green;
  doctor matrix test green; `refresh_all()` shape test green; suite
  green; drift clean; `tests/test_harness_live.py` runs whatever binaries
  exist (skips otherwise) and the H1 commit message records the
  ran/skipped matrix.
- **L0/L1 gates:** same commands as the superseded plan on new paths
  (`ruff check harness_fleet/ tests/ [career_fleet/]`, `mypy
  harness_fleet/ [career_fleet/]`), suites green, drift clean, plus the
  annotation-only `git diff` review for L1.
- **P gate:** the three per-repo round-trips above, all green.
- **Highest-risk validation:** the R21 data cutover (upgrade test), then the
  R1 post-`mv` re-verification combined with the cross-repo drift gate at R2
  end. If the upgrade test shows any row loss or a missed CHECK/table, R1
  pauses for a migration-logic fix — never for weakening the asserts. If
  drift reports anything beyond the career overlay after R2, R2 pauses for
  a file-level diff review instead of weakening the gate.
- Manual checks that can't be automated: U1/U2/U3 (user-owned environment
  steps). Everything else is a command.

## Risks / Rollback

- Mechanical rename misses a surface (a string the grep didn't catch):
  mitigated by the allowlisted grep-zero gate running before every rename
  commit; rollback is `git revert` of that repo's R commit.
- Data cutover corrupts or drops rows: mitigated by the upgrade test
  (row-count + value + CHECK + table asserts, idempotent re-open) and by
  the migration note leading with `db backup`; the cutover is forward-only
  with no downgrade path by design (D2), so a failed upgrade means fix
  forward, never dual-read.
- `_package_version`/argv dispatch/self-invoke behave differently under the
  new entry name: mitigated by the new-name coverage tests (R1 step 2) and
  the fresh-venv + `uv tool` smokes, which exercise the real installed
  entry points rather than source checkouts.
- User workspaces/DBs/MCP configs referencing old names: not code risk but
  migration risk — contained by the README migration section (U2:
  backup-first, `mv`, re-setup, packet re-export) and the upgrade-tested
  auto-migration of old DBs on first open.
- GitHub rename (U1) breaks external links (SECURITY.md, schema `$id`s,
  skill references): accepted and bounded — all in-repo references are
  updated to final URLs in R1/R2; nothing relies on redirects.
- Local dir `mv` breaks absolute paths elsewhere (shell aliases, other
  checkouts' drift discovery, IDE configs): bounded — drift discovery is
  updated in the same phase; anything outside the three repos is called out
  in the R1 commit message, not chased.
- Conservative parsers misread a harness's real JSON shape (cursor/grok/
  muse/agy shapes aren't pinned in the guide): mitigated by documented-keys
  + narrow fallbacks, fail-closed-to-error (never garbage text), and the
  live-smoke matrix — an adapter whose smoke fails keeps its stub tests
  green but is recorded unproven in the H1 commit message, never papered
  over with a weakened assert.
- Registry fallback removal breaks a caller relying on silent-opencode:
  mitigated by the typed error (names available providers), engine
  fail-closed surfacing, and suites proving every dispatch path; rollback
  is `git revert` of that repo's H1 commit (H0 stays — the seam holds).
- Rollback order: revert in reverse phase order (L1 → L0 → H1 → H0 → R2
  → R1) per repo; repos independent. The local dir `mv` is undone with a reverse `mv`
  (no git content involved). U1 (GitHub rename) is user-reversible from the
  GitHub UI and is the only step the implementer cannot roll back.

## Open Questions

None. All three draft questions were answered in conversation: (1) same
`harness_fleet` engine rename in siblings — confirmed; (2) wire values —
hard cutover including tables, per user direction (D2 rewritten, no
`migration_004` file — cutover is guarded inline `migrate()` logic); (3)
local dir `mv` — confirmed. Phase H adds no new questions: the 7-harness
scope follows from "universal" + the seven guide skills, and the judgment
calls (no-bypass D11, no-new-seeds D12, conservative parsers) are
approval-gated via this plan.
