## Goal

Close gaps 1–3 from the provider-seams review: make `ProviderReceipt` the carrier end-to-end (providers → engine/eval), introduce a `RouteId` boundary type for route identity, and type `RoutePolicy` end-to-end (DAG nodes → engine → providers). No behavior change: same argv construction, same parsers, same fail-closed semantics, same stored rows.

## Success Criteria

- `BaseProvider.run_prompt` returns `tuple[bool, str | None, ProviderReceipt]` on all ten bundled providers; the live provider path (providers → engine/eval) carries no unvalidated receipt dicts (stored-JSON handling in export/resume validates at load).
- The eval path validates receipts exactly like the engine path (invalid receipt → `transport_failed`, never into attempt records unvalidated).
- Route strings are parsed into a validated `RouteId` at the provider entry, registry, and engine ladder; catalog JSON and SQLite rows keep storing plain strings.
- Provider signature is `policy: RoutePolicy | None`; openrouter reads attributes (no `getattr` chains); the `inspect.signature` hack in the engine is gone; DAG `run`/`rescore` nodes accept `policy` as `RoutePolicy | None`.
- Full suite green (baseline 464 passed + 6 skipped; counts move up with new tests), `ruff`, `mypy`, and `check_harness_drift.py` green on the finished tree.

## Context And Current Facts

- `ProviderReceipt` already exists as a `ClosedModel` (strict, `extra="forbid"`) with a cost-consistency validator (`harness_fleet/models.py:745`). `BatchTestResult.receipt` is already typed (`models.py:868`). Published schemas are unaffected — `test_published_schemas.py` pins task/input/output/packet only, never receipts.
- Providers still build raw dicts (`_new_receipt`, `harness_fleet/providers/harness.py:190`) mutated by every parser. The engine reads a dozen `.get()`s into `attempt_record` (`engine.py:213-236`) *before* validating-and-discarding (`engine.py:239`). The eval path never validates (`eval.py:111-157`). Export re-validates stored JSON (`export.py:271`) and resume re-validates (`engine.py:644`).
- Route identity is a string mini-language: `split_route` accepts `/` or `:`; `model_from_route=False` adapters bypass validation; opencode overrides with its own prefix rule (`providers/harness.py:41-58, 212-224`). Registry is explicit-name-only (`providers/registry.py:84-96`). `RoutePolicy.allowed_routes` is `list[str]` (`models.py:719`); catalog stores route dicts.
- Policy seam: CLI builds a real `RoutePolicy` (`cli.py:126`); engine takes it typed (`engine.py:80`); providers declare `policy: Any`; openrouter reads it via `getattr` chains (`providers/openrouter.py:118-134`); the engine passes it only `if "policy" in sig.parameters` via an `inspect` hack (`engine.py:198-202`); DAG `RunNode`/`RescoreNode` carry `policy: dict[str, Any] | None` (`dag.py:50,80`). The other three node kinds (calibrate, filter, export) take no policy.
- Test blast radius for the receipt change: ~11 files assert `receipt[...]` dict access (`test_harness`, `test_opencode`, `test_codex`, `test_muse`, `test_grok`, `test_cursor`, `test_antigravity`, `test_openrouter`, `test_openrouter_policy`, `test_safety_fixes`, `test_audit_fixes`). Test fakes lacking a `policy` parameter: `test_engine.py:15`, `test_calibrate.py:179` (`test_status.py:10` uses `**kwargs` and is fine).
- `execute_batch` receipts are serialized at `cli.py:550-552` and `mcp_server.py:187-191` — Unit 1 verifies the concrete type and JSON conversion at both sites during implementation.

## Constraints And Non-goals

- Hard user constraints in force: no legacy shims (callers and tests are converted inside each unit; no `receipt_dict` back-compat properties left behind), deterministic code only, local commits only, career `cli.py` overlay untouched (this plan is bulk-lanes only).
- Non-goals: gap 4 (live verification beyond codex), gap 5 (`assert` at `providers/harness.py:300`), gap 6 (career mirror doctor hunk) — separate small fixes, not this plan. No storage migration for routes, no published-schema changes, no sibling mirroring inside this plan (R2 picks the merged result up afterward).

## Key Decisions

1. **Receipt: change the return type, don't validate at the edges.** Keeping `dict` returns and sprinkling validation cannot fix the eval hole or the engine's read-before-validate. `run_prompt` returns the model; the engine keeps one `model_validate` coercion so third-party `BaseProvider` implementations returning plain dicts still fail closed as `invalid_receipt`.
2. **Route: boundary value type, storage stays string.** Migrating catalog JSON rows, SQLite tables, and `RoutePolicy` string lists buys zero behavioral change for real migration risk. `RouteId` validates at parse boundaries; everything stored or compared stays `str(route)`.
3. **Policy: type it end-to-end and delete the `inspect` hack.** The hack exists only because the provider signature is untyped. Two test fakes gain `policy=None`; openrouter gets attribute access.
4. **No shims, per standing constraint.** Each unit converts its callers and tests atomically; the suite is green after every unit.
5. **Three units, one local commit each, in order receipt → policy → route.** Receipt first (deepest leaf change, proves the carrier pattern); policy second (narrowest); route last (widest consumer surface, benefits from the established pattern).

## Recommended Approach

- **Unit 1 (receipt carrier).** `_new_receipt` constructs a `ProviderReceipt`; parsers set attributes instead of keys; all ten providers return the model. Engine coerces via `model_validate` (keeps `invalid_receipt` fail-closed for foreign providers) and consumes attributes; eval gains the same coerce-and-fail-closed block it lacks today. Export and resume re-validation stay as-is. Convert the ~11 test files from `receipt[...]` to attribute access; add one new test proving an invalid adapter receipt fails closed in the eval path.
- **Unit 2 (policy end-to-end).** `BaseProvider.run_prompt` and all providers take `policy: RoutePolicy | None = None`; openrouter uses attribute access; engine drops the `inspect` hack and always passes `self.policy`; DAG `RunNode`/`RescoreNode` take `RoutePolicy | None` (pydantic validates dict input, so existing YAML/JSON DAG specs keep working). Update the two test fakes; add one test proving a dict policy in a DAG node reaches the provider typed.
- **Unit 3 (route identity).** New `RouteId` `ClosedModel` (`provider: str`, `model: str | None`) with a `parse()` classmethod accepting the legacy `/` and `:` spellings and a canonical `str()`. Wire it at provider entry (`run_prompt` coerces), `registry.resolve`, and the engine ladder; `RoutePolicy` route lists keep comparing as strings. Add a parse-table test covering both separators, bare-provider ids, and malformed ids failing closed.

## Work Plan

1. Unit 1 — receipt carrier. Surfaces: `providers/harness.py` (`_new_receipt`, `run_prompt`), `providers/base.py` (abstract signature), all ten provider modules (attribute-style parsing), `engine.py` (attribute consumption + coercion), `eval.py` (new coercion block), `export.py:90, 271` (dict-at-rest handling stays valid), `cli.py:550-552` + `mcp_server.py:187-191` (serialization check), ~11 test files + 1 new test. Depends on nothing.
2. Unit 2 — policy end-to-end. Surfaces: `providers/base.py`, `providers/openrouter.py`, `engine.py:198-202`, `dag.py` (2 nodes), `cli.py:126` (verify, likely unchanged), 2 test fakes + 1 new test. Depends on Unit 1 (touches the same signatures).
3. Unit 3 — route identity. Surfaces: `models.py` (`RouteId`), `providers/harness.py` (`split_route`/`derive_model` funnel into it), `providers/registry.py`, engine ladder + catalog comparisons (string form), 1 new parse-table test. Depends on Units 1–2 (same call paths).

## Validation Plan

- Per unit: run the touched test files first (expect strict-mode coercion failures in adapter tests on Unit 1 — that is the mechanism working; fix forward), then the full suite: `python3 -m pytest tests/ -q --ignore=tests/__pycache__ -p no:cacheprovider` (green, counts at or above the 464+6 baseline), plus `uvx ruff check`, `mypy harness_fleet/`, `python3 scripts/check_harness_drift.py`.
- Highest-risk step: Unit 1 strict-mode coercion across ten providers' parsers (`extra="forbid"` + `strict=True` will reject any stray key or mistyped value a parser sets — including `usage` payloads with non-`JsonValue` content). Mitigation: per-adapter test files run before the full suite; today's 12 receipt keys all exist on the model, verified by inspection.
- Manual check per unit: `git status` shows only the unit's files; each unit committed locally before the next begins.

## Risks / Rollback

- Strict-model construction inside hot parser paths could reject a real harness payload shape seen only live (only codex is live-verified here). Parsers already fail closed on unexpected shapes, so worst case is a failed attempt, not bad data — and the eval-path test plus existing parser tests pin current shapes.
- `RouteId` canonicalization must preserve both `/` and `:` spellings on input (existing catalog rows and CLI usage use both). The parse-table test pins this before wiring.
- Rollback is per-unit `git revert` (local commits, never pushed). No database migration ships, so there is nothing to roll forward.

## Open Questions

None. Every material fact above was verified in the tree during planning.
