# Fleet packaging, distribution, and lint plan

> SUPERSEDED by `2026-09-13-fleet-rename-harness.md` (full rename to
> harness-fleet). Kept for history; do not execute.

## Goal

Adopt the sound parts of the other session's proposal — canonical distribution
names, a verified install path, ruff, and mypy — with explicit per-phase
boundaries, without breaking the three-repo drift contract and without changing
runtime behavior.

## Success Criteria

- Each repo builds a wheel whose distribution name, scripts, and shipped
  packages are truthful and don't shadow a sibling's install (proven in fresh
  venvs, one fleet per environment documented).
- The `uv tool install` path is documented and smoke-verified (install, run,
  uninstall).
- A ruff gate is green in CI on a curated rule set in all three repos, and the
  two `PLR0124` (comparison-with-itself) findings are triaged as bugs or
  false positives.
- A mypy baseline gate (not `--strict`) is green in CI in all three repos.
- Full suites stay green (bulk-lanes 407, account-fleet 408, career-fleet 453),
  and `check_fleet_drift.py` reports no *new* drift — career `cli.py` overlay
  remains the only accepted DRIFT.
- Zero behavior change: no engine, store/schema, MCP protocol, provider, or
  skill-content changes.

## Context And Current Facts

Packaging today (all read from the repos this session):

| Repo | `pyproject` name / version | Ships packages | Console scripts |
|---|---|---|---|
| bulk-lanes | `account-fleet` 0.2.8 (**wrong name**) | `free_fleet` | `account-fleet`, `free-fleet`, `bulk-lanes` → `free_fleet.cli:main` |
| account-fleet | `account-fleet` 0.2.8 | `free_fleet` | same three scripts → same package (**mutual shadowing**) |
| career-fleet | `career-fleet` 0.2.2 | `career_fleet` **and** `free_fleet` | `career-fleet`, `career-lanes` → `career_fleet.cli:main`, plus the same three `free_fleet` scripts (**shadows both siblings**) |

- `career_fleet/` is a real second product (lanes, store, profile,
  community_sources), not a shim — career-fleet cannot collapse to one package
  without killing a product surface.
- Install docs today: `python -m pip install .` (`README.md:81`),
  `pip install -e ".[dev]"` (`CONTRIBUTING.md:20`). No uv docs anywhere.
- CI in all three repos is identical in shape: `pip install -e .`,
  `pytest -q`, `check_fleet_drift.py --self`, `check_wheel.py --distribution
  <name>` (bulk-lanes/account-fleet pass `account-fleet`; career passes
  `career-fleet`). Python matrix 3.10–3.14 plus win/mac jobs.
- `check_wheel.py` builds a wheel, installs it in a fresh venv outside the
  checkout, and smoke-runs the CLI. It is **per-repo, not drift-synced**
  (career already carries its own `career-fleet` choice).
- `check_fleet_drift.py` `EXACT_FILES` covers: itself, the route-policy
  contract test, every `free_fleet/*.py` file (including `cli.py`, where the
  career overlay is the known accepted DRIFT — the script reports it and still
  exits 0), the operations.md copies, and the routes seed. It does **not**
  cover `pyproject.toml`, CI workflows, `check_wheel.py`, skill `SKILL.md`
  files, `mcp-recipes.md`, READMEs, examples, or `career_fleet/`.
- Lint/type gauges (observed via `uvx`, no config files exist anywhere):
  - `ruff check free_fleet/`: 322 findings, 188 auto-fixable. Top rules:
    UP045 (80), BLE001 (55), UP006 (41), I001 (24), S110 (23), F401 (22),
    UP035 (21); plus 2× PLR0124 comparison-with-itself (possible real bugs).
  - `mypy --strict` on `models.py` alone: **156 errors across 19 files**
    (`no-untyped-def`, `type-arg`, stale `type: ignore`s, `no-untyped-call`).
    `--strict` is a project, not a flag flip.
  - The S/BLE/TRY findings conflict with intentional fail-closed design
    (e.g. `except Exception: bias_map = None` in `cmd_export`), so a curated
    rule set is required — defaults-all would fight the architecture.
- Local toolchain: `uv` and `docker` installed; `ruff`/`mypy` not installed
  (usable via `uvx` without touching the project env).
- No Dockerfiles, no PyInstaller specs, no ruff/mypy configs exist.

### Handoff context (do not re-derive)

- The three repos are one mirrored engine plus overlays; the drift script is
  the sync contract. Any edit to a drift-synced file must land byte-identical
  in all three repos (except the accepted career `cli.py` overlay and the
  operations.md schema-version normalization).
- `pyproject.toml`, CI, and `check_wheel.py` are intentionally per-repo:
  change them per repo with no mirror obligation, but keep conventions
  aligned (same ruff/mypy config text, same CI step shape).
- `requires-python >= 3.10`; PEP 604/585 syntax (`X | None`, builtin
  generics) is already used and is safe on the whole CI matrix.
- Prior suites-at-green counts: 407 / 408 / 453. Prior commit series:
  `22eb657` (bulk-lanes), `41b9690` (account-fleet), `2ad2a02`
  (career-fleet) — each repo's history is independent.

## Constraints And Non-goals

- **No Docker image and no PyInstaller binary in this plan.** No consumer for
  either was found: the tool is local-first (SQLite workspace, MCP stdio),
  and a frozen binary risks skew against the skills it ships with. Reopen
  triggers: an explicit MCP-host-isolation need (Docker) or a must-serve user
  with no Python (PyInstaller).
- **No `ruff format`.** Whole-tree reformatting would churn every drift-synced
  file for no behavior gain. `ruff check` (+ its safe autofixes) only.
- **No `mypy --strict` in this plan.** Baseline gate now; strict is an
  explicit follow-up ratchet after the baseline is green and stable.
- **No repo merge, no package-dir renames, no shared fourth package.**
  Phase 2A fixes metadata only. Full engine extraction is documented as
  follow-up Phase 2B, not scoped here.
- **No behavior changes** of any kind (see Success Criteria).
- **No pushes, no PyPI publishes, no tags.** Local commits only, and only on
  explicit ask per commit unit (plan steps never self-authorize history
  writes).

## Key Decisions

- **D1 — Packaging topology: minimal metadata fix (Phase 2A), not full
  extraction.** The install conflicts are real (shadowing proven by the
  package/script tables above), but the deep fix — one owned engine package
  plus per-repo namespaces — requires retiring or re-scoping the drift
  contract and is a design project of its own. Phase 2A removes the lies
  (bulk-lanes' wrong dist name, career shipping siblings' entry points) and
  documents one-fleet-per-environment; 2B stays a follow-up. Single-dist
  collapse was considered and rejected as the default: the repos are
  positioned as separate products and `career_fleet/` is a distinct second
  product — collapsing needs an explicit product call (see Open Questions).
- **D2 — bulk-lanes distribution name: user picks `bulk-lanes` vs
  `free-fleet`** (Open Question 1). Everything else in Phase 2A is fixed
  regardless; only the name string, description/URLs, and `check_wheel.py`
  choice/CI arg depend on it.
- **D3 — Ruff: curated select list, not defaults-all.** Enforce
  correctness/hygiene rules (`F`, `E` except line-length, `I`, `UP`, `B`,
  `SIM`, plus the two PLR0124-class rules that caught possible bugs).
  Exclude `S`, `BLE`, `TRY`: the codebase deliberately catches broadly at
  provider/store boundaries (fail-closed), and those rules would demand
  churn against the architecture. `target-version = "py310"`.
- **D4 — mypy: baseline gate first.** The 156-error strict gauge on a single
  module proves `--strict` needs its own project. Ship `[tool.mypy]` with
  default strictness, `python_version = "3.10"`, `warn_unused_ignores = true`,
  and narrow per-file ignores only where dynamism is by design (providers,
  argparse CLI surface). Fix everything else with annotations.
- **D5 — Distribution proof: `uv tool install` trial as validation, docs
  only.** Working hypothesis (to be proven by the round-trip gate, not
  assumed): a console-scripts project needs no code change for `uv tool
  install`. The plan installs, runs, and uninstalls per repo, documents
  the one-liner only after the gate passes, and treats a gate failure as
  a plan amendment trigger.

## Recommended Approach

Run three ordered phases, each mirrored across the three repos and each ending
with suites + drift re-verification. Phase 0 and Phase 1 are independent of
the naming decision and can start immediately; Phase 2A needs only the D2
answer. Publish as one commit per repo per phase, in phase order (binding at
publish time; each commit still needs its own explicit ask).

## Work Plan

### Phase 0 — Ruff gate (no-regrets, topology-independent)

Touches per repo:

- `pyproject.toml`: add a `[tool.ruff]` block (identical text in all three
  by convention, not by drift enforcement): curated `select`, `target-version
  = "py310"`, no line-length rule.
- `free_fleet/**/*.py`: apply `ruff check --fix` for the enabled rules only;
  hand-triage the 2 PLR0124 findings (fix if bugs, else narrow `noqa` with a
  comment explaining why the comparison is intentional).
- `.github/workflows/ci.yml`: add one step running the ruff gate after the
  test step (same step text in all three).
- `CONTRIBUTING.md`: one line documenting the gate command.

Boundaries — does NOT touch: `ruff format` (forbidden this plan); `S`/`BLE`/
  `TRY` rules (left unenforced, no code churn for them); tests (no test edits
  expected — autofixes are behavior-neutral; if a fix touches a test file,
  it must be import-modernization only); `career_fleet/` package (lint it too
  — same gate — but it has no mirror obligation); behavior of any kind.
Sync obligation: ruff churn inside drift-synced files must be produced by the
  same `ruff check --fix` invocation in each repo so all three stay
  byte-identical; verify with the drift script before committing.

### Phase 1 — mypy baseline gate (topology-independent)

Touches per repo:

- `pyproject.toml`: add `[tool.mypy]` (`python_version = "3.10"`,
  `warn_unused_ignores = true`, narrow per-file ignores for providers/CLI).
- `free_fleet/**/*.py` (+ `career_fleet/**/*.py` in career only): add
  missing annotations, type bare generics, delete stale `type: ignore`s.
- `.github/workflows/ci.yml`: add one mypy step (same text, all three repos).
- `CONTRIBUTING.md`: one line for the mypy command.

Boundaries — does NOT touch: `--strict` (not enabled; no `disallow_any_*`
  flags); runtime behavior (annotation-only diffs — any diff that changes
  executed code is out of scope and must be split out or dropped); test
  logic (test files get the minimum annotations to pass, nothing more);
  third-party stubs or `ignore_missing_imports` widening beyond what's
  needed for the pinned deps.
Sync obligation: same as Phase 0 — annotation edits in drift-synced files
  must be byte-identical across repos; drift script gates each repo commit.

### Phase 2A — Truthful packaging metadata (needs D2 answer)

Touches per repo:

- bulk-lanes: `pyproject.toml` `name` → D2 pick, plus matching description/
  URLs keywords as needed; `scripts/check_wheel.py` `--distribution` choices
  + `.github/workflows/ci.yml` wheel step updated to the new name; console
  `scripts` table UNCHANGED (compat — existing entry-point names keep
  working).
- account-fleet: verify-only. Name/scripts already truthful; expected diff
  is docs only.
- career-fleet: `pyproject.toml` — remove the three `free_fleet` scripts
  from `[project.scripts]` (keep `career-fleet`/`career-lanes`) and narrow
  `[tool.setuptools.packages.find]` so the wheel ships `career_fleet` only;
  `free_fleet/` source stays in the repo untouched (drift + tests run from
  source as today). Implementer must read career's `check_wheel.py` body
  first — its smoke flow may assume the `free_fleet` entry points.
- All three: `README.md` install section + `CONTRIBUTING.md` gain the `uv
  tool install` one-liner and a "one fleet per environment" note.

Boundaries — does NOT touch: any `free_fleet/*.py` source (zero drift
  risk by construction — packaging files aren't drift-synced); package
  directory names; the drift script's file list; PyPI publishing or
  versioning policy; the `career_fleet` product surface.
Sync obligation: none at the file level (all touched files are per-repo),
  but the drift script + full suites still run as the phase gate to prove
  nothing else moved.

### Phase 2B — Shared-engine extraction (follow-up, NOT in this plan)

One paragraph for context: the durable end-state is a single-owned engine
(one repo owns `free_fleet/`, the others depend on it or vendor a pinned
copy) with per-repo namespaces, at which point the drift script is retired
or reduced to an API-contract check. Requires its own design plan (repo
topology, versioning, offline/air-gap story for pinned deps). Trigger:
recurring mirror toil or a real co-install customer.

## Validation Plan

- **Phase 0 gate (per repo):** `uvx ruff check free_fleet/ tests/
  career_fleet/` (career path only in career-fleet) exits 0; `python3 -m
  pytest tests/ -q` green (407 / 408 / 453); `python3
  scripts/check_fleet_drift.py` shows no new DRIFT; PLR0124 pair each have a
  fix commit-hunk or a commented `noqa`.
- **Phase 1 gate (per repo):** project-env `mypy free_fleet/` (plus
  `career_fleet/` in career) exits 0; suites green; drift clean; `git diff`
  review confirms annotation-only changes in executed code (spot-check at
  least the store/engine diffs).
- **Phase 2A gate (per repo):** `python3 scripts/check_wheel.py
  --distribution <name>` passes with updated choices; fresh-venv wheel
  install + `<cli> --help` smoke; `uv tool install <repo-path>` →
  `<cli> --help` → `uv tool uninstall <name>` round-trip; career-only:
  fresh venv with career wheel installed must FAIL `python -c "import
  free_fleet"` (proves exclusion) while career's suite still passes from
  source; suites green; drift clean.
- **Highest-risk validation:** the career wheel exclusion — it is the only
  step that changes install topology. If career's `check_wheel.py` smoke
  flow depends on `free_fleet` entry points, Phase 2A pauses for a revised
  smoke flow rather than weakening the exclusion.
- Manual checks that can't be automated: none — every gate above is a command.
  (PyPI-side name availability is deliberately not a gate: no publishing in
  this plan.)

## Risks / Rollback

- Ruff autofix churn breaks something subtle: low risk (mechanical fixes),
  gated by full suites per repo; rollback is `git revert` of the phase
  commit in that repo.
- UP modernization vs Python 3.10 floor: `target-version = "py310"` pins
  rule behavior; the CI matrix (3.10–3.14, win/mac) proves it.
- mypy baseline forces an annotation that misrepresents dynamic code:
  mitigation is narrow per-file ignores for providers/CLI (pre-approved
  boundary); anything broader needs a plan amendment, not a quiet ignore.
- Career wheel exclusion breaks a hidden assumption (e.g. docs cross-linking
  `free-fleet` inside career guides, or the smoke flow): mitigation is the
  read-career-`check_wheel.py`-first boundary plus the exclusion proof gate;
  rollback is revert of the career Phase 2A commit (other repos unaffected —
  no file-level coupling).
- Bulk-lanes rename breaks a downstream script installing `account-fleet`
  from the bulk-lanes path: mitigation is unchanged entry-point names
  (only the distribution name changes); the plan notes but does not chase
  downstream consumers.
- Rollback order across repos/phases: revert in reverse phase order (2A →
  1 → 0); repos are independent (separate histories), no cross-repo
  ordering constraint.

## Open Questions

1. **D2 — what should the bulk-lanes distribution be named: `bulk-lanes`
   or `free-fleet`?** Blocks Phase 2A only; Phases 0–1 proceed regardless.
   (Repo-local evidence: README and skills say `free-fleet`; the directory
   says `bulk-lanes`.)
2. **Confirm the three products stand** (no single-distribution collapse).
   The plan assumes yes; a "collapse to one dist" answer replaces Phase 2A
   with a repo-consolidation design plan.
3. **Is there a Docker consumer after all?** Default assumption is no
   (plan excludes Docker). Only answer if someone concrete needs a
   containerized MCP server or isolated eval runner.
