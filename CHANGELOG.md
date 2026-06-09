# Changelog

All notable changes to vstack are documented in this file. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the
project adheres to [Semantic Versioning](https://semver.org/) from
`1.0.0` onward. During the `0.x` series, minor bumps may include
breaking changes (see API stability promise in `vstack/__init__.py`).

## [0.29.0] — 2026-06-09

Two more feature modules: signing + synth.

### Added

- **`vstack.signing`** — HMAC-based integrity signing for reports.
  `Signer` class with sign/verify methods. Canonical JSON
  serialization for stable hashing. SHA-256 + SHA-512 support.
  `VerificationError` on signature mismatch. Convenience
  functions `sign_report()` / `verify_report()`. Key-order
  independence verified.
- **`vstack.synth`** — programmatic synthetic trace generator.
  8 built-in generators: `generate_stuck_in_loop`,
  `generate_hallucination`, `generate_sycophancy`,
  `generate_over_apology`, `generate_premature_completion`,
  `generate_tool_misuse`, `generate_anxious_overhedge`,
  `generate_healthy`. Each takes parameters (retry_count,
  turns, etc.) for varying difficulty. `generate_batch()`
  produces N traces with parameterized seeds for reproducibility.
  Template registry with `register_template` / `get_template` /
  `list_templates` for custom generators.

### Changed

- Test count: 2,631 → 2,678 (+47 from the two new modules).

### Compatibility

- All 2,678 tests pass (1 skipped: crewai not installed).
- Public API surface strictly expanded.

## [0.28.0] — 2026-06-09

Two more feature modules: vbench + markers.

### Added

- **`vstack.vbench`** — in-process pattern benchmark harness.
  `BenchHarness` runs patterns × traces × reps and tabulates
  per-run metrics: latency, finding count, severity distribution.
  `BenchResult` aggregates with `Statistics` (mean/median/p95/p99).
  `compare_results()` flags regressions and improvements between
  two results. JSON-serializable.
- **`vstack.markers`** — structured markers for trace steps.
  Built-in marker constructors: `cost_marker`, `latency_marker`,
  `quality_marker`, `safety_marker`. `CustomMarker` for user-
  defined kinds. `attach_marker()` stores markers on dict or
  object-style steps. `analyze_markers()` aggregates across all
  steps with cost rollup, slow-step detection (configurable
  threshold), quality average, blocked-step count, and custom
  marker grouping.

### Changed

- Test count: 2,588 → 2,631 (+43 from the two new modules).
- `pyproject.toml` adds `_vbench`, `_markers` to force-include +
  testpaths.

### Compatibility

- All 2,631 tests pass (1 skipped: crewai not installed).
- Public API surface strictly expanded.

## [0.27.0] — 2026-06-09

Two more feature modules: calibrate + streaming.

### Added

- **`vstack.calibrate`** — confidence calibration curves.
  Pure-Python implementations of:
    - `IsotonicCalibration`: classical pool-adjacent-violators
      isotonic regression. Monotonic by construction. Block
      aggregation algorithm.
    - `PlattCalibration`: σ(ax+b) sigmoid calibration. Gradient
      descent on log loss.
    - `CalibrationMetrics`: Brier score, log loss, expected
      calibration error (ECE).
    - `evaluate_calibration()`: compute all metrics in one pass.
  Curves are JSON-serializable. No dependency on sklearn/scipy.
- **`vstack.streaming`** — SSE-friendly event stream for live
  diagnoses. `EventStream` emits `run_started` / `pattern_started`
  / `finding_emitted` / `pattern_completed` / `run_completed` /
  `error` events. Listener registration (decorator + add_listener),
  wildcard listeners, queue-based iteration, exception-swallowing
  for safe broadcast. `SSEStreamWriter` converts events to
  Server-Sent Events format for HTTP streaming.

### Changed

- Test count: 2,548 → 2,588 (+40 from the two new modules).
- `pyproject.toml` adds `_calibrate`, `_streaming` to force-
  include + testpaths.

### Compatibility

- All 2,588 tests pass (1 skipped: crewai not installed).
- Public API surface strictly expanded.

## [0.26.0] — 2026-06-09

Two new feature modules + trace zoo expansion.

### Added

- **`vstack.compose`** — declarative pattern pipeline composition.
  Fluent `Pipeline` builder with `step()`, `then()`, `when_severity()`,
  `when()`, `callback()`, `diagnose()`, `with_baseline()`. Each
  builder method returns a new immutable Pipeline. `run()` against
  a trace executes the pipeline and aggregates findings into a
  `PipelineResult` with severity summary, top-N findings, and
  to_dict() serialization. `Stop` exception lets callbacks halt
  early. 28 new tests.
- **`vstack.vdiff`** — structured diff between two DiagnoseReports.
  `diff_reports()` surfaces added/removed findings, severity
  changes, intervention changes, and pattern additions/removals.
  `ReportDelta.is_regression()` and `is_improvement()` for CI
  gates. Markdown + dict serialization. 19 new tests.
- **trace_zoo expansion** from 12 → 33 traces. New entries:
  silent_failure, decision_paralysis, cold_handoff,
  consensus_dilution, blame_spiral, performative_empathy,
  handoff_loss, expert_loafing, groupthink, role_thrash,
  hub_spoke_fragility, trust_collapse, culture_drift, grpi_break,
  psych_safety_low, bias_stack, devils_advocate_missing,
  smart_goal_missing, thomas_kilmann_avoiding,
  mcgregor_x_micromanage, aar_skipped. Includes team and
  individual shape coverage across all 5 categories.

### Changed

- Test count: 2,501 → 2,548 (+47 from new modules + zoo).
- `pyproject.toml` adds `_compose`, `_vdiff` to force-include +
  testpaths.

### Compatibility

- All 2,548 tests pass (1 skipped: crewai not installed).
- Public API surface strictly expanded.

## [0.25.0] — 2026-06-09

Three more feature modules: replay, vcache, otel.

### Added

- **`vstack.replay`** — replay historical diagnose() runs from
  JSONL logs without re-spending LLM calls. ``ReplayRecorder``
  wraps any client to capture request/response pairs to disk.
  ``ReplayClient`` reads the JSONL log and returns canned responses
  on hash match. Strict mode raises ``ReplayMissError`` on miss;
  permissive mode falls back to sequential matching. Use for
  regression testing, pattern development, and CI gates.
- **`vstack.vcache`** — LLM response cache with TTL + LRU eviction.
  ``LLMCache`` wraps any client and dedupes identical requests.
  Per-namespace isolation, configurable capacity and TTL, hit/miss
  stats with cost-saved tracking.
- **`vstack.otel`** — OpenTelemetry exporter. ``setup_otel()``
  configures the OTLP exporter; spans auto-emit on every
  ``diagnose()`` run and pattern call. ``OTelInstrumentedClient``
  wraps any LLM client to emit spans on every chat call. Graceful
  no-op if OTel isn't installed.

### Changed

- Test count: 2,450 → 2,501 (+51 from the three new modules).
- `pyproject.toml` adds `_replay`, `_vcache`, `_otel` to force-
  include + testpaths.

### Compatibility

- All 2,501 tests pass (1 skipped: crewai not installed).
- Public API surface strictly expanded.

## [0.24.0] — 2026-06-09

Three new feature modules: scorecard, budget, trace_zoo.

### Added

- **`vstack.scorecard`** — per-agent multi-pattern scorecard with
  letter grades. Aggregates findings from many patterns into
  per-dimension scores (Reasoning / Coordination / Trust / Workload
  / Culture), each with an A+ → F letter grade. Includes
  `compute_scorecard()`, `compare_scorecards()` (for drift
  detection), `is_blocking_regression()` (for CI gates), and
  text/markdown/HTML renderers. New `vstack-scorecard` CLI with
  `compute` / `render` / `compare` subcommands. 119 new tests.
- **`vstack.budget`** — cost-budget enforcement middleware. Wraps
  any LLM client with rolling-window limits on cost ($), call
  count, and token count. Per-minute / per-hour / per-day
  windows. `BudgetEnforcer` for single-budget enforcement;
  `BudgetRegistry` with contextvars-based active-client tracking
  for per-request budget scoping. `BudgetExceeded` exception
  carries kind/window/limit metadata. 42 new tests.
- **`vstack.trace_zoo`** — canonical library of named synthetic
  agent traces. 12 curated traces covering the main failure modes
  (stuck_in_loop, hallucinated_citation, sycophancy_drift,
  over_apology_loop, overconfidence_spiral, context_saturation,
  premature_completion, tool_misuse, refusal_cascade,
  motivation_collapse, anxious_overhedge, healthy_individual).
  Each carries category + shape + expected severity + expected
  dominant pattern. New `vstack-trace-zoo` CLI with `list` /
  `show` / `get` / `categories` / `shapes` subcommands. 37 new
  tests.

### Changed

- Test count: 2,252 → 2,450 (+198 from the three new modules).
- `pyproject.toml` adds `_scorecard`, `_budget`, `_trace_zoo` to
  the force-include block + testpaths + console scripts.

### Compatibility

- All 2,450 tests pass (1 skipped: crewai not installed).
- Public API surface strictly expanded. No removals, no
  argument-shape changes.
- Wire format unchanged.

## [0.23.0] — 2026-06-09

Documentation expansion: framework playbooks, concepts, tutorials,
cluster demos, migration guides.

### Added

- **6 framework integration playbooks** under `docs/integrations/`:
  LangChain, LangGraph, CrewAI, AutoGen, Pydantic-AI, LlamaIndex.
  Each covers the adapter, the 8 patterns most useful for that
  framework's failure modes, trace-capture mechanics, common
  pathologies, and a production wiring snippet.
- **5 per-cluster combined recipe demos** under `examples/clusters/`:
  reasoning, coordination, trust, workload, culture. Each runs
  the recipes for its cluster against representative traces and
  prints a comparative summary.
- **5 migration guides** under `docs/migrations/` covering the
  v0.10 → v0.22 upgrade path. Each names what changed, what broke,
  and what didn't.
- **4 new tutorials** under `docs/tutorials/`:
  - `07_dashboard_deployment`: stand up the dashboard server.
  - `08_baselines_and_drift`: per-pattern + fleet baselines + CI gates.
  - `09_async_fanout`: production-volume async with rate limiting.
  - `10_observability`: structured logging, metrics, tracing, alerts.
- **4 new concept deep-dives** under `docs/concepts/`:
  - `trace-shapes`: individual / team / org schema details.
  - `severity-and-confidence`: 2x2 matrix + calibration.
  - `llm-clients`: client protocol + custom integration.
  - `recipes-vs-bundles`: composition modes compared.

### Changed

- Pure-documentation release. No code, schema, or wire-format
  changes from v0.22.0.

### Compatibility

- All 2,252 tests pass (1 skipped: crewai not installed).
- Public API surface unchanged.

## [0.22.0] — 2026-06-09

Examples gallery expansion: cookbook + per-pattern starters + trace
fixtures library.

### Added

- **24 new cookbook scripts** under `examples/cookbook/` covering
  every named recipe in the catalog that didn't yet have an
  end-to-end stub-driven script: `15_stuck_in_loop`,
  `16_agents_arguing`, `17_silent_failure`, `18_bad_feedback_loop`,
  `19_culture_drift`, `20_goal_misalignment`, `21_trust_collapse`,
  `22_overconfidence_spiral`, `23_plan_collapse`,
  `24_premature_completion`, `25_tool_misuse`, `26_anxious_overhedge`,
  `27_motivation_collapse`, `28_handoff_loss`,
  `29_deference_cascade`, `30_expert_loafing`, `31_cold_handoff`,
  `32_performative_empathy`, `33_decision_paralysis`,
  `34_hub_spoke_fragility`, `35_role_thrash`,
  `36_espoused_actual_drift`, `37_policy_decay`,
  `38_hyper_specialization`. Each calls `diagnose()` with the
  named recipe and prints an intervention bundle.
- **34 per-pattern starter demos** under `examples/patterns/`, one
  per shipped pattern. Each demo is the minimum runnable invocation
  for that pattern: import + stub + trace + `diagnose(patterns=[...])`
  call + summary print. Auto-generated to a consistent shape so the
  gallery is browsable.
- **25 new trace builders** in `examples/_shared/traces.py`:
  `overconfidence_spiral_trace`, `premature_completion_trace`,
  `tool_misuse_trace`, `anxious_overhedge_trace`,
  `motivation_collapse_trace`, `hallucination_cascade_trace`,
  `silent_dependency_drop_trace`, `bottleneck_orchestrator_trace`,
  `consensus_dilution_trace`, `refusal_cascade_trace`,
  `context_saturation_trace`, `blame_spiral_trace`,
  `cold_handoff_trace`, `performative_empathy_trace`,
  `decision_paralysis_trace`, `role_thrash_trace`,
  `policy_decay_trace`, `healthy_individual_trace`,
  `healthy_team_messages`, `healthy_culture_samples`,
  `expert_loafing_messages`, `deference_cascade_messages`,
  `trust_collapse_messages`, `schein_drift_samples`,
  `hyper_specialized_messages`.

### Changed

- Pure-examples release. No changes to pattern surfaces, schemas,
  console scripts, or wire formats from v0.21.0.

### Compatibility

- All 2,252 tests pass (1 skipped: crewai not installed).
- Public API surface unchanged.

## [0.21.0] — 2026-06-09

Per-pattern WALKTHROUGH gallery — 34 end-to-end recipe documents.

### Added

- **34 `WALKTHROUGH.md` files**, one per pattern, under each
  `module-N-*/NN-name/WALKTHROUGH.md`. Each follows the same
  consistent shape so users can jump from any pattern's README
  to a runnable recipe pack without re-learning the structure:
  - When-to-reach decision lens (signals it's the right pattern;
    signals it's *not*).
  - The framework's named structure (e.g. the four Goleman
    domains, the five Lencioni dysfunctions, the seven Robbins-
    Judge dimensions).
  - Five concrete scenarios with `StubClient` code that runs
    without LLM credentials. Each scenario names the trace
    shape, the call site, the expected output, and the
    intervention.
  - CLI walkthrough for the pattern's console script.
  - Composition chain naming the next pattern to run based on the
    detected sub-pattern, with explicit links to the downstream
    WALKTHROUGHs.
  - Async fan-out snippet.
  - Baseline drift detection snippet using the pattern's
    `record_baseline` / `compare_to_baseline` helpers.
  - Anti-patterns + FAQ + forensic-mode cost.
  - Reference section linking the source, schema, prompts, demo,
    tests, essay, and pattern README.
- Total documentation surface added: ~10,000 LOC across the 34
  walkthroughs. Module-1 (individual): 12 files. Module-2 (team):
  18 files. Module-3 (organization): 4 files.

### Changed

- No code changes. WALKTHROUGHs are pure documentation; the
  pattern surfaces, schemas, and console scripts are unchanged
  from v0.20.0.

### Compatibility

- All 2,252 tests pass (1 skipped: crewai not installed).
- Wire format unchanged. All 34 patterns unchanged.
- Public API surface unchanged.

## [0.20.0] — 2026-06-09

CLI + cookbook + docs expansion on top of v0.19.x.

### Added

- **`vstack-recipes` CLI**: terminal browser for the recipe catalog.
  Supports listing all recipes (default, grouped by cluster),
  filtering by `--cluster` / `--shape`, substring search via `--q`,
  free-text trigger routing via `--match`, and per-recipe detail
  via `--show <slug>` (with `--json` / `--md` output formats).
  13 new tests in `_diagnose/tests/test_recipes_cli.py`.
- Three new cookbook recipes demonstrating v0.19.0 named-recipe
  expansions: 12 `refusal_cascade` (Grant Strengths + HEXACO),
  13 `context_saturation` (Yerkes-Dodson forensic + Lewin), and
  14 `blame_spiral` (Lewin + Lencioni).
- **`docs/PATTERNS_OVERVIEW.md`**: comprehensive single-page map
  of all 34 patterns with module groupings, literature-anchor map,
  and failure-surface → patterns table.
- **`docs/RECIPES_OVERVIEW.md`**: catalog overview of all 33 named
  recipes with per-cluster tables, invocation examples (Python /
  CLI / MCP / HTTP), and the free-text router walkthrough.

### Changed

- Repo-wide `ruff format` sweep: 11 pre-existing files were brought
  into format compliance (mostly pre-existing tests + a few module
  files that hadn't been formatted since their last edit). Lint
  is now green across the full CI scope.

### Compatibility

- All 2,252 tests pass (1 skipped: crewai not installed). +13
  recipes-CLI tests on top of v0.19.1's 2,239.
- Wire format unchanged. All 34 patterns unchanged. The 33 recipes
  from v0.19.0 ship verbatim; the new `vstack-recipes` CLI is a
  read-only browser.
- Public API surface strictly expanded (new `vstack-recipes`
  console script). No removals.

## [0.19.1] — 2026-06-09

CI hotfix on top of v0.19.0.

### Fixed

- 8 unused-import F401 errors in cookbook recipes 07/08/10/etc.
  (`datetime.datetime`, `datetime.timezone`, `vstack.lencioni.AgentMessage`,
  `vstack.lencioni.MultiAgentTrace`).
- 1 unused-variable F841 error in
  `examples/cookbook/08_groupthink_cascade.py:225` (`base_time`).

CI lints `examples/` in addition to the source tree; my local
`ruff check` runs were scoped to `_dashboard/` and missed the
cookbook offenders.

### Compatibility

- All 2,239 tests pass unchanged. ruff check + ruff format check
  clean across the full source tree.

## [0.19.0] — 2026-06-09

Catalog + dashboard + cookbook expansion. Four substantial additions
on top of the v0.18.x diagnose runner + MCP + REST surfaces:

### Recipes catalog 8 → 34

Recipes catalog grew from 8 to 33 named recipes organized into 5
thematic clusters:

- **reasoning** (12): stuck_in_loop, hallucination_cascade,
  overconfidence_spiral, sycophancy_drift, refusal_cascade,
  plan_collapse, premature_completion, tool_misuse, over_apology_loop,
  anxious_overhedge, motivation_collapse, goal_misalignment.
- **coordination** (8): agents_arguing, bottleneck_agent,
  bad_feedback_loop, silent_dependency_drop, handoff_loss,
  consensus_dilution, deference_cascade, expert_loafing.
- **trust** (5): silent_failure, trust_collapse, cold_handoff,
  performative_empathy, blame_spiral.
- **workload** (5): context_saturation, decision_paralysis,
  bottleneck_orchestrator, hub_spoke_fragility, role_thrash.
- **culture** (4): culture_drift, espoused_actual_drift, policy_decay,
  hyper_specialization.

`Recipe.cluster` field + `list_recipes_by_cluster()` for CLI / UI
sectioned listings. Each recipe's `triggers` list seeds the keyword
router, so `recipe_for_trigger("the agent keeps apologizing in
circles")` now returns `over_apology_loop` without manual picking.

### vstack.dashboard module

New dark-mode HTML report generator + FastAPI dashboard server,
modeled after the superlog observability aesthetic:

- `render_report(report)` / `render_reports_overview(reports)`:
  self-contained HTML output with Chart.js panels (findings by
  severity, findings by pattern, cost by pattern, per-pattern table,
  top-N findings, error panel). Pure Python; opens in any browser.
- `DiagnoseReport.to_html(report_id="...")`: convenience method on
  the runner output for one-call rendering.
- `vstack.dashboard.server.build_app()`: FastAPI app with 7 routes
  (overview, per-run detail, pattern catalog, recipe catalog,
  `POST /v1/reports` ingest, `GET /v1/reports` list, `/healthz`).
- `vstack-dashboard` CLI: `render` (pipe report JSON in, HTML
  out) + `serve` (start the dashboard server).
- 29 tests across `_dashboard/tests/` (render, server, CLI).

### Examples cookbook + shared traces

`examples/_shared/traces.py`: 12 reusable synthetic agent traces
(`stuck_in_loop_trace`, `hallucinated_citation_trace`,
`sycophancy_trace`, `over_apology_trace`,
`silent_dependency_drop_messages`, `groupthink_messages`,
`silent_dissent_messages`, `social_loafing_messages`,
`hyper_specialized_roster`, `hub_and_spoke_roster`,
`balanced_team_roster`, `well_executed_individual_trace`).

`examples/cookbook/` grew by 8 stub-driven end-to-end recipes
demonstrating the new named-recipe expansions:
04 hallucination_cascade, 05 sycophancy_drift, 06 over_apology_loop,
07 silent_dependency_drop, 08 groupthink_cascade,
09 bottleneck_orchestrator, 10 consensus_dilution,
11 diagnose_full_walkthrough.

### docs/tutorials/ markdown gallery

Six new markdown walkthroughs covering the surfaces that landed in
v0.10.0 → v0.18.0:
01 first_diagnosis (15-minute intro),
02 chaining_patterns (manual composition),
03 framework_integrations (LangChain / LangGraph / CrewAI / AutoGen /
LlamaIndex / Pydantic-AI / OpenAI Assistants),
04 building_a_custom_pattern (full skeleton),
05 mcp_deployment (Claude Desktop / Cursor / Cline),
06 fastapi_deployment (production hardening).

### Added

- `vstack-dashboard` console script + the `vstack/dashboard/` import
  path (force-included from `_dashboard/lib/`).
- `Recipe.cluster` field; default value `"general"` for backward compat.
- `vstack.diagnose.list_recipes_by_cluster()` public function.
- `DiagnoseReport.to_html()` convenience renderer.

### Compatibility

- All 2,239 tests pass (1 skipped: crewai not installed). +29 dashboard
  tests on top of v0.18.1's 2,210.
- Wire format of all 34 patterns unchanged.
- Public surface of `vstack.diagnose` strictly expanded (new
  `list_recipes_by_cluster`, new `Recipe.cluster` field, new
  `DiagnoseReport.to_html`). No removals or signature changes.
- The 8 v0.10.0 recipes ship verbatim; the 26 new recipes are
  pure additions.

## [0.18.1] — 2026-06-08

CI hotfix on top of v0.18.0.

### Fixed

- `ruff format --check` failures on `_api/lib/_app.py`,
  `_api/tests/test_api_diagnose.py`, and `_mcp/lib/_server.py`:
  applied `ruff format` to bring the new code from v0.17.0/v0.18.0
  into project format conventions.
- `mypy --strict` failure on `_api/lib/_app.py:821`:
  `payload.shape` is `str | None` (from the `DiagnoseRequestEnvelope`
  Pydantic model) but `diagnose()` expects the
  `TraceShape` Literal. The validation block above the runner call
  already rejects non-canonical values; added a narrowed
  `shape_arg: TraceShape | None` local with a `# type: ignore` cast
  so mypy accepts it.

### Compatibility

- All 2,210 tests pass unchanged. ruff check clean. mypy `--strict`
  on the touched files clean.

## [0.18.0] — 2026-06-08

`POST /v1/diagnose` FastAPI endpoint.

Symmetric exposure of `vstack.diagnose.diagnose()` on the HTTP
surface. v0.17.0 added the MCP `vstack_diagnose` tool; this release
adds the matching REST endpoint so callers without an MCP transport
(internal services, dashboards, CI bots) can hit the same
cross-pattern runner.

### Added

- `POST /v1/diagnose` endpoint with `DiagnoseRequestEnvelope` body
  schema (trace + shape + recipe + patterns + mode + model + cache +
  top) and `DiagnoseResponseEnvelope` response schema (shape +
  findings + per_pattern + errors + cost + optional cache_stats).
- `DiagnoseRequestEnvelope`, `DiagnoseResponseEnvelope`,
  `DiagnoseFinding`, `DiagnosePerPatternSummary`,
  `DiagnoseCostSummary`, `DiagnoseCacheStats` Pydantic models so
  OpenAPI clients get typed return values instead of `dict[str, Any]`.
- 8 new tests in `_api/tests/test_api_diagnose.py` covering:
  - End-to-end ranked-findings response from synthetic patterns.
  - `top` truncation behavior.
  - Validation 400s for unknown recipe / unknown pattern / recipe+
    patterns mutex / unknown shape.
  - 422 for missing-trace body.
  - OpenAPI spec inclusion + correct response-schema reference.

### Compatibility

- All 2,210 tests pass (1 skipped: crewai adapter, extra not
  installed in dev). +8 new tests on top of v0.17.0's 2,202.
- All existing `/v1/analyze/{name}` per-pattern routes are
  unchanged. The new endpoint sits alongside them, reusing the same
  auth + rate-limit + size-enforcement + Prometheus middleware stack.
- Endpoint runs the runner via `asyncio.to_thread` to keep the
  event loop responsive, with the standard
  `state.limits.request_timeout_seconds` deadline + 504 timeout
  response (mirrors the analyze endpoint).
- OpenAPI schema is generated automatically from the Pydantic
  envelopes; `/openapi.json` includes the new path under `/v1/diagnose`.

## [0.17.0] — 2026-06-08

`vstack_diagnose` cross-pattern MCP tool.

The MCP server already exposed one tool per pattern
(`vstack_lewin`, `vstack_lencioni`, ... 34 tools). Callers who knew
*which* pattern to run were well served, but the "I have a
misbehaving agent and do not yet know where to start" case still
required reading the catalogue and picking a tool manually.

This release adds `vstack_diagnose` as a 35th MCP tool that wraps
`vstack.diagnose.diagnose()` — the cross-pattern runner that infers
trace shape, picks the default bundle, executes every pattern with
per-pattern error isolation, and returns a severity-ranked findings
report.

### Added

- `vstack.mcp._server.DIAGNOSE_TOOL_NAME = "vstack_diagnose"` constant.
- `_build_diagnose_tool()` synthesizes the MCP Tool definition with
  an opt-in input schema:
  - `trace` (required): generic JSON object passed to the runner.
  - `shape`: optional override of inferred trace shape.
  - `recipe`: optional named recipe slug (mutually exclusive with
    `patterns`).
  - `patterns`: optional explicit list of pattern slugs.
  - `mode`: `quick` / `standard` / `forensic`.
  - `model`: LLM model identifier override.
  - `cache`: opt-in shared-response cache wrapper.
  - `top`: optional truncation of the ranked findings list.
- `_dispatch_diagnose_call()` routes the request through
  `vstack.diagnose.diagnose()`, with input validation guards for
  unknown recipes, unknown patterns, and recipe/patterns mutual
  exclusivity.
- `_serialize_diagnose_report()` renders the DiagnoseReport as
  indented JSON: shape, ranked findings, per-pattern summary,
  errors, cost summary, optional cache stats.
- 7 new tests in `_mcp/tests/test_server_diagnose.py` covering tool
  listing, input schema shape, end-to-end dispatch with synthetic
  patterns, and validation-error paths.

### Changed

- `_list_tools` now returns 35 tools (1 cross-pattern + 34
  per-pattern) instead of 34.
- The existing `test_list_tools_returns_all_patterns` assertion
  updated to expect 35 tools and include `vstack_diagnose` in the
  expected name set.

### Compatibility

- All 2,202 tests pass (1 skipped: crewai adapter, extra not
  installed in dev). +7 new tests on top of v0.16.0's 2,195.
- All 34 per-pattern tools' input schemas are unchanged.
- MCP wire protocol unchanged; the new tool follows the same
  `name` / `description` / `inputSchema` Tool shape as the existing
  tools.
- The cross-pattern runner is the same `vstack.diagnose.diagnose()`
  function exposed in v0.10.0+; this release only adds the MCP
  surface to it.

## [0.16.0] — 2026-06-08

Lossless per-pattern findings extraction in `vstack.diagnose`.

The old `_coerce_findings` reflective normalizer only recognized the
generic `findings` and `top_findings` attribute names. Almost no real
vstack pattern exposes either of those, so the runner fell back to
the score-only path and surfaced exactly ONE `Finding` per pattern
run. That was lossy: a real Lencioni report has FIVE dysfunction
evidence entries; a Bias Stack run has FOUR bias scores; an AAR run
has 1-5 lessons. Each should land as its own ranked finding.

### Added

- `vstack.diagnose.adapters` module with a smart `extract_findings`
  function that walks the field-name inventory vstack patterns
  actually use:
  - 47 evidence-list field names (`dysfunctions`, `legs`, `domains`,
    `factors`, `triggers`, `strengths`, `pathologies`, `quadrants`,
    `behaviors`, `loci`, `terms`, `traps`, `needs`, `biases`,
    `characteristics`, `dimensions`, `phases`, `zones`, `styles`,
    `metrics`, `lessons`, `branches`, plus `_evidence`-suffix
    variants and collection accessors).
  - 24 categorical-title field names so per-item titles populate
    correctly from the pattern-specific axis name (`dysfunction`,
    `leg`, `factor`, `quadrant`, `behavior`, etc.).
  - 6 severity field names (`severity`, `severity_of_gap`,
    `severity_of_absence`, `severity_of_overuse`, `mismatch_severity`,
    `risk`) so per-pattern severity wire formats normalize to the
    canonical 7-point scale.
  - 9 score field names (`score`, `weight`, `presence_score`,
    `wobble_score`, `overuse_score`, `observed_score`, `fit_score`,
    `substantive_score`, `value`, `coherence_score`) used when
    severity is absent and we need to derive one.
- `vstack.diagnose.register_adapter` decorator for registering
  per-pattern override adapters when the smart extractor's
  conventions do not fit a pattern's schema.
- `vstack.diagnose.ADAPTERS` dispatch table exposing the registered
  overrides.
- Built-in AAR override adapter: `Lesson` carries no severity field
  by design (it is a narrative finding, not scored evidence), so the
  override emits each Lesson as a `moderate`-severity Finding with
  pattern slug + description in the title and root_cause + framework
  anchor in evidence.

### Changed

- `vstack.diagnose.runner` now delegates findings extraction to
  `extract_findings` from the adapters module. The legacy private
  name `_coerce_findings` is preserved as an alias for backward
  compatibility.
- `Finding` is now defined in `vstack.diagnose.adapters` (was
  previously in `runner`); it is re-exported from `runner` and from
  the top-level `vstack.diagnose` package so all import paths
  continue to work.
- `_score_to_severity` band boundaries tightened to match the
  seven-band calibration the prompt-engineering pass standardized
  on (0.10/0.25/0.40/0.55/0.70/0.85 thresholds).

### Tests

- 14 new tests in `_diagnose/tests/test_diagnose_adapters.py`
  covering:
  - Multi-finding extraction from `dysfunctions` (5), `biases` (4),
    `lessons` (2) shapes.
  - Pattern-specific severity field name normalization
    (`severity_of_gap`, `severity_of_absence`).
  - Per-pattern adapter override precedence.
  - Override-raises-fall-through-to-smart graceful degradation.
  - Backward compatibility with legacy `findings=[...]` lists and
    `top_findings` alias.
  - Score-only fallback path.
  - Severity-and-title-at-top-level fallback path.
  - None / empty-list / vague-item edge cases.

### Compatibility

- All 2,195 tests pass (1 skipped: crewai adapter, extra not
  installed in dev). This is 14 new tests on top of the 2,181 from
  v0.15.0.
- `Finding`, `extract_findings`, `_coerce_findings`, `ADAPTERS`,
  `register_adapter` are all importable from `vstack.diagnose`
  AND from `vstack.diagnose.runner` (where applicable) for
  backward-compat.
- Wire format of every analyzer's LLM output is unchanged. Only
  the runner-side extraction logic was lifted.

## [0.15.0] — 2026-06-08

Prompt-engineering uplift pass COMPLETE — every shipped pattern (34
of 34) now ships the uniform uplift template introduced in v0.13.0.

### Patterns uplifted in this release

The remaining 24 patterns received the same uplift the v0.13.0/v0.14.0
top-10 received: explicit OUTPUT SCHEMA literals, one-shot examples,
DO NOT rules covering common failure modes, severity calibration
anchors, canonical-order enforcement.

| Module | # | Pattern | Anchor literature |
|--------|---|---------|--------------------|
| 1 (individual) | 2 | Goleman EI | Goleman 2002; Mayer-Salovey 1997; Joseph-Newman 2010 |
| 1 | 3 | Johari Window | Luft 1969; Stone-Heen 2014; Kadavath 2022 |
| 1 | 4 | DANVA Emotion Reader | Nowicki-Duke; Ekman; Plutchik; Russell |
| 1 | 5 | Cognitive Reappraisal | Gross 1998/2014; Sheppes-Suri-Gross 2015 |
| 1 | 7 | HEXACO Personality | Lee-Ashton 2004-2018; Bourdage 2007 |
| 1 | 8 | Grant Strengths | Grant-Schwartz 2011; Kaiser-Kaplan 2009 |
| 1 | 9 | Motivation Traps | Saxberg-Hess 2013; Weiner 1985; Bandura 1977 |
| 1 | 10 | SDT Intrinsic Reward | Deci-Ryan; Pink 2009; Casper 2023 |
| 1 | 11 | McGregor Orchestrator | McGregor 1960; Eisenhardt 1989 agency theory |
| 1 | 12 | Vroom Expectancy | Vroom 1964; Porter-Lawler 1968; Bandura 1977 |
| 2 (team) | 13 | GRPI Working Agreement | Beckhard 1972; Rubin-Plovnick-Fry 1977 |
| 2 | 15 | Social Loafing | Latane 1979; Karau-Williams 1993 |
| 2 | 16 | Heffernan Superflocks | Heffernan 2014; Muir 1996; Page 2007 |
| 2 | 19 | McAllister Trust | McAllister 1995 (cognitive vs affective) |
| 2 | 21 | Glaser Conversation | Glaser 2014 Conversational Intelligence |
| 2 | 22 | Stone-Heen Feedback | Stone-Heen 2014 Thanks for the Feedback |
| 2 | 23 | Plus/Delta Feedback | Joiner Associates; Brown 2018 |
| 2 | 24 | SMART Goal | Doran 1981; Locke-Latham 1990 |
| 2 | 25 | Group Decision Models | Kaner 2014; Vroom-Yetton 1973 |
| 2 | 29 | Thomas-Kilmann | Thomas-Kilmann 1974 conflict modes |
| 3 (org) | 31 | Schein Iceberg Culture | Schein 1985/2010/2017 |
| 3 | 32 | Robbins-Judge 7 Culture | Robbins-Judge OB 17th ed. 2017 |
| 3 | 33 | Org Structure Matrix | Galbraith Star Model; Mintzberg 1983 |
| 3 | 34 | Span of Control | Galbraith 1977; Mintzberg 1983 |

### Changed

- Every `prompts.py` across the 24 patterns listed above. Public
  template constant names and `{placeholder}` fields are unchanged;
  `assemble_prompt` semantics are unchanged; all downstream callers
  see no API break.
- System prompts now ship explicit posture rules, anti-pattern
  instructions, calibration tables (severity / fit / quality /
  motivation thresholds), and per-category symptom signatures.
- Each task prompt that the generator parses now ships a literal
  OUTPUT SCHEMA block with the exact JSON shape.
- Pattern-specific DO NOT rules prevent the most common failure modes
  observed in the v0.12.x baseline (invented quotes, vague
  interventions, schema-violating labels, sycophantic mimicry being
  scored as relationship_management, performative care being scored
  as affective trust, mid-superflocks "make the top agent better"
  recommendations, identity-trigger apology spirals being escalated,
  etc.).
- One-shot examples on each pattern's main scoring prompt demonstrate
  the textbook failure signature for that pattern with verbatim
  evidence quotes and named-framework anchoring.

### Why

This closes the prompt-layer quality gap across the entire pattern
library. The 0.10–0.12 releases shipped the runner, cost tracking,
and shared cache; the 0.13–0.14 releases lifted the top 10
prompts; 0.15.0 brings the long tail (24 patterns) to the same bar.
The diagnose pipeline now has uniform per-pattern prompt quality
regardless of which sub-bundle the caller invokes.

### Compatibility

- All 2,181 tests pass unchanged (1 skipped: crewai adapter, extra
  not installed in dev).
- Wire format of every analyzer's LLM output is preserved.
- Public template constant names + `{placeholder}` field sets are
  unchanged across all 34 patterns.
- `assemble_prompt` semantics are unchanged.

## [0.14.0] — 2026-06-08

Prompt-engineering uplift pass — top 10 patterns completed.

The uplift template (introduced in 0.13.0 on Lencioni) has now been
applied uniformly across the ten highest-leverage patterns. Each
pattern's `prompts.py` now ships:

  1. An explicit **OUTPUT SCHEMA block** with the literal JSON shape
     the generator parses, so the LLM does not have to
     reverse-engineer the schema from a one-line "return JSON" hint.
  2. A **one-shot example** of a well-calibrated answer demonstrating
     verbatim evidence quotation and named-source anchoring.
  3. **`DO NOT` rules** covering the most common failure modes
     (invented quotes, name-dropped citations without anchoring,
     vague interventions, schema-violating labels, scope creep
     between phases).
  4. **Severity calibration anchors** tied to score bands (where the
     pattern uses numeric scoring), mapped down to the wire-format
     severity labels.
  5. **Canonical ordering rules** so downstream parsers do not have
     to reorder arrays.

### Patterns uplifted in this release

| #  | Pattern            | Anchor literature                            |
|----|--------------------|----------------------------------------------|
| 1  | Lewin Formula      | Lewin 1936; Kelley 1967; Cemri et al. 2025  |
| 6  | Yerkes-Dodson      | Yerkes-Dodson 1908; Sweller; Liu et al. 2024|
| 14 | Process Gain/Loss  | Steiner 1972; Hill 1982; Diehl & Stroebe    |
| 17 | Lencioni Diagnostic| Lencioni 2002 + 2005; Edmondson 1999        |
| 18 | Trust Triangle     | Frei & Morriss 2020                          |
| 20 | Psych Safety       | Edmondson 1999, 2018                         |
| 26 | Debate Pathology   | Janis 1972; Stoner 1968; Hatfield et al.    |
| 27 | Bias Stack         | Kahneman/Tversky 1974, 1979, 2011; Staw 1976|
| 28 | Devil's Advocate   | Janis 1972; Schwenk 1990                     |
| 30 | AAR Generator      | Wharton; US Army TC 25-20; Edmondson 1999    |

### Changed

- Every `prompts.py` file across the ten patterns above. Public
  template constant names and `{placeholder}` fields are unchanged;
  `assemble_prompt` semantics are unchanged; all downstream callers
  see no API break.
- System prompts now ship explicit posture rules, anti-pattern
  instructions, severity calibration tables, and per-category
  symptom signatures so the LLM has a consistent grounding across
  modes (quick / standard / forensic).

### Why

The 0.10–0.12 releases shipped the cross-pattern runner, cost
tracking, and shared LLM-response cache for the diagnose pipeline.
Pattern quality at the prompt layer was the next ceiling on
signal-to-noise. This release closes that gap across the top ten
patterns by leverage; the remaining 24 patterns will receive the
same lift on the same template in future releases.

### Compatibility

- All 2,181 tests pass unchanged (1 skipped: crewai adapter, extra
  not installed in dev).
- Wire format of every analyzer's LLM output is preserved for
  downstream tooling.
- Public template constant names and `{placeholder}` field sets are
  unchanged.
- `assemble_prompt` semantics are unchanged across all ten patterns.

## [0.13.0] — 2026-06-08

Prompt-engineering uplift pass, starting with Lencioni #17. Each prompt
in the pattern now ships an explicit OUTPUT SCHEMA block, a one-shot
example of a good answer, "DO NOT" rules covering the most common
failure modes, and a seven-level severity calibration table on the
system prompt. The wire format is unchanged.

### Changed

- `vstack.lencioni` (module 17): rewrote `prompts.py` for all six
  templates (`PYRAMID_SCORE_PROMPT`, `INTERVENTIONS_PROMPT`,
  `QUICK_DIAGNOSTIC_PROMPT`, `FORENSIC_CASCADE_PROMPT`,
  `FORENSIC_PSYCH_SAFETY_PROMPT`, `FORENSIC_INTERVENTIONS_PROMPT`).
  Public template constant names and `{placeholder}` fields are
  unchanged; `assemble_prompt` semantics are unchanged. Downstream
  callers see no API break.
- `LENCIONI_SYSTEM_PROMPT` now defines a seven-level severity
  calibration anchored in score bands (none / trace / low / moderate /
  medium / high / critical) and lists explicit anti-pattern rules
  (no invented quotes, no invented citations, no refusals on thin
  traces).
- Each task prompt now ships a literal OUTPUT SCHEMA block, so the
  LLM does not have to reverse-engineer the JSON shape from a
  one-line "return JSON" hint.
- `PYRAMID_SCORE_PROMPT` ships a one-shot example demonstrating good
  severity calibration plus two distinct verbatim evidence quotes.

### Why

The 0.10–0.12 releases gave the pattern bundle a runner, cost
tracking, and a shared cache. Pattern quality at the prompt layer was
the next ceiling on the diagnose pipeline's signal-to-noise ratio.
Lencioni is the first pattern to receive the lift; AAR, Lewin, Bias
Stack, Psych Safety, Trust Triangle, Process Gain/Loss, Debate
Pathology, Devil's Advocate, and Yerkes-Dodson follow on the same
template.

### Compatibility

- All 44 Lencioni tests pass unchanged.
- All 84 `vstack.diagnose` tests pass unchanged (the runner
  reflectively introspects analyzer output; prompt-text changes do
  not affect the runner contract).
- Wire format of the LLM output (DysfunctionEvidence severity values
  are still high/medium/low/none) is preserved for downstream tooling.

## [0.12.0] — 2026-06-08

Shared LLM-response cache across patterns in one `diagnose()` run.
When a bundle of patterns hits the LLM with identical prompts, the
cache returns the cached completion without paying twice.

### Added

- `vstack.diagnose.CachingLLMClient`: thin wrapper around any
  LLM client that memoizes `complete(prompt, system)` calls keyed on
  `(prompt, system, model)`. SHA-256 keys; LRU eviction at
  `maxsize=256` (configurable).
- `vstack.diagnose.CachingClientStats`: hit / miss / insert counters
  plus a `hit_rate` property and `bytes_saved` heuristic.
- `diagnose(cache=True, ...)` and `diagnose_async(cache=True, ...)`:
  opt-in shared cache for the duration of one call. The wrapper is
  threaded through to every analyzer in the bundle.
- `DiagnoseReport.cache_stats`: populated when caching was on,
  `None` otherwise so callers can tell whether the cache was active.
- `to_markdown()` renders a cache line in the cost section when
  `cache_stats` is present.
- `__getattr__` forwarding on the wrapper: analyzers that read
  unknown attributes off the client (e.g. `last_usage`, `model`)
  see the real underlying client transparently.

### Tests

- 8 new tests in `_diagnose/tests/test_diagnose_cache.py`:
  - hash key stability + collision resistance
  - wrapper returns cached on second identical call
  - wrapper misses on different prompts
  - LRU eviction when `maxsize` exceeded
  - attribute forwarding to inner client
  - `diagnose()` without cache: two patterns -> two inner calls
  - `diagnose(cache=True)`: identical prompts -> one inner call
  - `cache=True` with no client is a graceful no-op
- Total `_diagnose` suite: 84 passing.
- Full repository suite: 2181 passing, 1 skipped (crewai).

### Compatibility

- Caching is opt-in (`cache=False` by default).
- Pattern analyzers see no API change; the wrapper exposes the same
  `complete()` signature as the underlying client.

## [0.11.0] — 2026-06-08

Cost tracking in `vstack.diagnose`. The runner now installs an
in-memory telemetry sink for the duration of each `diagnose()` call
and aggregates LLM-call events into a `CostSummary` attached to the
report.

### Added

- `vstack.diagnose.CostSummary` dataclass: aggregate token + latency
  stats with per-pattern and per-model breakdowns.
- `DiagnoseReport.cost`: populated automatically when participating
  analyzers emit telemetry via `vstack.aar.record_llm_call`.
- `DiagnoseReport.to_markdown()` renders a `## Cost summary` section
  when `cost.llm_calls > 0` (skipped silently otherwise).
- The previously-installed telemetry sink is restored after the run,
  so callers who had their own sink installed see no global-state
  mutation.

### Tests

- 5 new tests in `_diagnose/tests/test_diagnose_cost.py`:
  - empty cost summary when no telemetry
  - aggregation across multiple emitting analyzers
  - per-pattern and per-model breakdowns
  - sink restoration after the run
  - Markdown render gated by `cost.llm_calls`
- Total `_diagnose` suite: 76 passing.
- Full repository suite: 2173 passing, 1 skipped (crewai).

### Compatibility

- Patterns that don't emit telemetry contribute nothing to the cost
  summary; the report's other fields are unchanged.
- All existing imports continue to work.

## [0.10.0] — 2026-06-08

Named recipes layer for `vstack.diagnose`. Until now, callers had to
either accept the shape-default bundle or hand-pick patterns; this
release adds an opinionated layer in between.

### Added — recipes

- `vstack.diagnose.RECIPES`: catalog of 8 named bundles, each curated
  for a specific recognizable failure mode:
  - `stuck_in_loop` (individual)
  - `agents_arguing` (team)
  - `silent_failure` (team)
  - `bottleneck_agent` (team)
  - `bad_feedback_loop` (team)
  - `culture_drift` (org)
  - `goal_misalignment` (individual)
  - `trust_collapse` (team)
- Each recipe has a description, applicable shape, ordered pattern
  list, and trigger-keyword phrases.
- `diagnose(recipe="stuck_in_loop", ...)`: pick a recipe by name.
  Explicit `patterns=` still wins if both are supplied.
- `recipe_for_trigger("agent keeps making the same mistake")`:
  free-text keyword matcher.
- `vstack-diagnose --recipe <name>` and `--match "<text>"` CLI flags.
- `vstack-diagnose --list-recipes` enumerates the catalog.
- Catalog validation runs at import time: a recipe that references
  an unknown pattern slug raises immediately instead of failing at
  call time.

### Tests

- 12 new tests in `_diagnose/tests/test_diagnose_recipes.py`.
- Total `_diagnose` suite: 71 passing.
- Total repository suite: 2168 passing, 1 skipped (crewai).

## [0.9.0] — 2026-06-08

CLI surface for `vstack.diagnose`. Adds the `vstack-diagnose` entry
point so the cross-pattern runner is reachable from a shell, not only
from Python.

### Added

- `vstack-diagnose` CLI: reads a JSON trace from `--trace <path>` or
  stdin and prints either Markdown (default) or `--json` output of the
  cross-pattern report.
- `--list`: enumerates every shipped pattern with its applicable
  shapes and one-line summary.
- `--shape {individual|team|org}`: force trace-shape inference.
- `--patterns slug [slug ...]`: override the default bundle with an
  explicit list.
- `--client {anthropic|openai|ollama|none}`: pick the LLM client. The
  CLI defaults to `none` so no paid call is ever made without explicit
  opt-in.
- `--mode {quick|standard|forensic}`: forward pipeline mode to
  analyzers that accept one.
- `--top <N>`: number of top findings to surface in Markdown.
- Permissive trace JSON parsing: required AAR `TraceStep` fields
  (timestamp/type/content) are auto-filled from common alternative
  names (`action`, `note`, etc.) so a single line of test JSON
  produces a valid trace.

### Tests

- 6 new CLI tests in `_diagnose/tests/test_diagnose_cli.py`.
- Total `_diagnose` suite: 59 passing.
- Total repository suite: 2156 passing, 1 skipped (crewai).

## [0.8.0] — 2026-06-08

Curated public API + cross-pattern diagnostic runner. Until this
release, using vstack at scale meant importing each of the 34
pattern sub-packages by hand and calling their analyzers separately.
0.8.0 adds a top-level entry point that wraps the patterns into a
single call.

### Added — `vstack.diagnose` (new surface module)

- `diagnose(trace, llm_client=...)`: runs a curated bundle of patterns
  against one agent or multi-agent trace and returns a single ranked
  `DiagnoseReport`. Bundle selection is shape-aware: a single-agent
  trace runs the individual-failure-mode patterns; a crew trace runs
  the team patterns; an org-scale trace runs the org-design patterns.
  Callers can override the bundle with `patterns=[...]`.
- `diagnose_async(...)`: concurrent variant that uses each pattern's
  async analyzer with a configurable in-flight bound.
- `PATTERNS`: a declarative registry of every shipped pattern with
  module path, main analyzer class name, async variant, applicable
  trace shapes, summary, and tags. Enumerable for tooling that wants
  to iterate every pattern without hand-importing.
- `DiagnoseReport.to_markdown()`: opinionated single-document
  render with a "Top findings" section and a per-pattern errors
  section.
- Findings normalization: the runner reflects on common return-shape
  attributes (`findings`, `severity`, `score`, …) so new patterns
  work without changes to the runner.
- Error isolation: one failing pattern does not kill the report.
  Failures land in `DiagnoseReport.errors` and the rest of the bundle
  still produces findings.

### Added — top-level package

- `vstack.__init__` now documents the curated API and exposes
  `diagnose` / `PATTERNS` via PEP 562 lazy attributes.
- `vstack.diagnose` is the canonical import path: `from
  vstack.diagnose import diagnose, PATTERNS`.

### Tests

- 53 new tests across `_diagnose/tests/`:
  - 44 registry-shape invariants over every shipped pattern.
  - 9 runner tests covering ranking, error isolation, shape inference,
    explicit-shape override, markdown rendering, and the async runner.
- Total repository test count after this release: 2150 passing.

### Compatibility

- All existing single-pattern import paths (`from vstack.aar import
  AARAnalyzer`, etc.) continue to work unchanged.
- No pattern source files modified.

## [0.7.0] — 2026-05-25

Onboarding + launch-polish release. Closes the gap between "library
shipped" and "users can pick it up and feel productive in 30 seconds."

### Added — `vstack.hello` (new surface module)

- `vstack-hello` CLI: a 30-second first-run demo that builds a
  synthetic agent-failure trace (8 steps, a recognizable
  edit-before-read failure mode), resolves an LLM client from the
  environment, and runs the AAR pattern against the trace.
- `--offline` flag: skip LLM resolution and print a pre-rendered
  sample AAR. Useful for CI smoke tests, demo recordings, and
  air-gapped environments.
- `--json` flag: machine-readable envelope.
- `--no-banner` flag: pipe-friendly output.
- Graceful fallback: if no API key is set, the command still prints
  a complete sample so users see the shape of vstack's output
  without ever hitting an error path.

### Added — GitHub Pages docs site

- `.github/workflows/docs.yml` builds the mkdocs-material site on
  every push to `main` that touches `docs/`, `mkdocs.yml`, or the
  workflow itself, and publishes to <https://valani9.github.io/vstack/>.
- `mkdocs.yml` `site_url` updated to the hosted URL.

### Added — supply-chain + community polish

- `.github/dependabot.yml`: weekly pip + github-actions + docker
  updates, with grouped PRs for framework adapters / LLM clients /
  dev-tooling so reviewer load stays low.
- `.github/workflows/codeql.yml`: CodeQL static analysis on push +
  PR + a weekly cron, with the `security-extended` and
  `security-and-quality` query packs enabled.
- `.github/ISSUE_TEMPLATE/` with three forms (bug / feature /
  question), plus `config.yml` linking to `vstack-doctor`, the
  security policy, and the hosted docs.
- `.github/PULL_REQUEST_TEMPLATE.md`: explicit test plan +
  public-API-impact + release-notes-line checklist.

### Added — release notes plumbing

- `.github/RELEASE_TEMPLATE.md` + `.github/render_release_notes.py`:
  the GitHub Release body is now rendered from the matching
  `CHANGELOG.md` section + a template, instead of inlined into
  `release.yml`. Falls back to the `[Unreleased]` section if the
  exact-version section is missing.

### Changed

- `pyproject.toml`: 14 new keywords (`agent-debugging`,
  `agent-observability`, `agent-evaluation`, `llm-evaluation`,
  `prompt-engineering`, `post-mortem`, `after-action-report`,
  `retrospective`, `agent-failure-modes`, `multi-agent-systems`,
  `model-context-protocol`, `mcp-server`, `llmops`, `agent-ops`).
- `pyproject.toml`: `vstack-hello` registered as a `[project.scripts]`
  entry; `_hello/lib` added to the force-include map and the
  pytest testpaths.
- `release.yml`: the smoke-test step now also imports `vstack.hello`
  to catch any wheel-mapping regressions.
- `ci.yml`: mypy + test + lint extended to cover `_hello/`.
- Shell completions (bash + zsh + fish) for `vstack-hello`'s flags.

### Operational

- mkdocs site builds clean under `--strict` (no broken links, no
  ambiguous nav entries) as a precondition for the Pages workflow.

### Surfaces now live (12 total, +1 since v0.6.0)

1. Python imports
2. 34 per-pattern CLIs
3. MCP server (`vstack-mcp`)
4. REST API (`vstack-api`)
5. Docker (`ghcr.io/valani9/vstack:0.7.0`)
6. Claude Code skills (7)
7. Framework adapters (LangChain / LangGraph / CrewAI / AutoGen /
   LlamaIndex / Pydantic AI)
8. OpenAI / Anthropic tool JSON
9. Open WebUI plugin manifest
10. Tier B platform generators (`vstack-config gen-platform`)
11. Browser dev tooling (`vstack-browser`)
12. **First-run smoke (`vstack-hello`)** — new in 0.7.0

## [0.6.0] — 2026-05-25

Production-hardening release. Adds the security + cache + observability +
diagnostic infrastructure that takes `vstack-api` from "fine for localhost"
to "ready for thousands of concurrent users."

### Added — `vstack.security`

- `APIKeyStore` + `APIKey` — SHA-256-hashed in-memory keys with
  constant-time verification. Load from `VSTACK_API_KEYS` /
  `VSTACK_API_KEYS_FILE`.
- `InMemoryRateLimiter` — sliding-window per-key (or per-IP) limiter
  with `RateLimitDecision` + `Retry-After` semantics.
- `RequestLimits` — declarative caps on body size, trace steps,
  message count, per-string chars, total chars, request timeout.
  Configured via `VSTACK_API_MAX_*` env vars.
- `audit_input_for_injection` / `safe_pattern_name` / `safe_path` /
  `safe_subprocess_argv` / `warn_on_suspicious_inputs` — defense-in-
  depth helpers for the parts of vstack that take user input.

### Added — `vstack.cache`

- `InMemoryLRUCache` + `NullCache` + `CacheBackend` protocol +
  `CacheEntry` + `CacheStats`.
- `build_cache_key(pattern, mode, model, trace)` — SHA-256 over the
  canonical JSON of the trace + run params; identical traces hit
  the cache cleanly.
- `resolve_cache_from_env()` honors `VSTACK_CACHE=memory|off`,
  `VSTACK_CACHE_CAPACITY`, `VSTACK_CACHE_TTL_SECONDS`.

### Added — `vstack.observability`

- `MetricsRegistry` + `Counter` + `Histogram` + `render_prometheus()`
  — hand-rolled Prometheus text-format exporter, no
  `prometheus_client` dependency.
- `record_request` / `time_request` — request-level helpers that
  populate `vstack_requests_total{surface,pattern,mode,status}` +
  `vstack_request_duration_seconds{surface,pattern,mode}`.
- `REQUEST_ID_HEADER` constant + `get_or_create_request_id` /
  `set_current_request_id` / `current_request_id` — `X-Request-ID`
  round-trip + contextvar binding for log correlation.
- `install_sentry_if_configured()` — optional `sentry-sdk`
  integration via `SENTRY_DSN`. Silently no-ops if the SDK isn't
  installed or `SENTRY_DSN` is unset.

### Added — `vstack.api` hardening

- **Auth middleware** — `Authorization: Bearer` + `X-API-Key`
  support; constant-time comparison; rejects with `401` +
  `WWW-Authenticate` when `require_auth=True` and the key is
  missing/wrong.
- **Rate-limit middleware** — `429` + `Retry-After` + the
  `X-RateLimit-Limit` / `X-RateLimit-Remaining` headers on every
  response.
- **Body-size middleware** — rejects oversized POSTs with `413`
  before they're decoded.
- **Security-headers middleware** — `X-Content-Type-Options`,
  `X-Frame-Options`, `CSP`, `Referrer-Policy`, conditional HSTS.
- **Request-ID middleware** — generates / echoes `X-Request-ID`;
  binds to a contextvar for log correlation.
- **CORS middleware** — opt-in via `VSTACK_API_CORS_ORIGINS`.
- **`/readyz` + `/livez` + `/metrics`** — separated K8s probe
  semantics (`readyz` flips to `draining` on shutdown); Prometheus
  metrics endpoint at `/metrics`.
- **Graceful shutdown** — FastAPI lifespan handler drains in-flight
  requests on `SIGTERM`.
- **Async analyze path** — uses analyzer `*Async` mirrors when the
  LLM client has `acomplete`; falls back to a thread executor for
  the sync analyzer so concurrent HTTP requests don't serialize on
  the event loop.
- **Cache integration** — cache lookup happens BEFORE LLM resolution
  so a cache hit costs zero LLM round-trips.
- **Request timeout** — server-side per-request deadline
  (`VSTACK_API_REQUEST_TIMEOUT`, default 120s); returns `504` on
  exceedance.

### Added — File-store safety

- `vstack.memory.atomic_write_text` / `atomic_write_bytes` — tmp-
  file + `os.replace` for crash-safe writes. Wired into
  `save_config()` and `LearningStore.update_outcome()`.
- `vstack.memory.append_locked` / `shared_read_lock` / `FileLock` —
  POSIX advisory locks (with Windows `msvcrt` fallback) for cross-
  process JSONL append + read. Wired into `LearningStore.record()`
  and `FileTelemetrySink.record()`.

### Added — `vstack-doctor` diagnostic CLI

- Audits 25+ checks across Python version, vstack install, pattern
  registry, `~/.vstack/` writability, LLM client resolvability,
  every documented CLI on PATH, every optional extra, gbrain
  reachability, Node.js availability for browser, API auth
  misconfiguration, and PyPI upgrade availability.
- `--json` for machine-readable output; `--skip-network` for
  air-gapped CI; `--only-errors` for terse output.
- Exit code 1 when any check is ERROR-level; 0 otherwise.

### Added — Shell completions

- `completions/vstack.bash`, `completions/_vstack` (zsh), and
  `completions/vstack.fish` — tab-completion for all 10 top-level
  CLIs + subcommands + key arguments (pattern names, platform
  names, path kinds, config keys).
- `completions/README.md` installs instructions.

### Added — Production docs

- `docs/operations/deploy.md` — minimum production checklist;
  Docker-only + Kubernetes Deployment manifests; auth + rate
  limiting + request limits + cache + observability config; what
  stays in-process vs. needs a shared backend at scale;
  troubleshooting.
- `docs/operations/security.md` — three-ring security model
  (library guards, configurable API guards, deployment
  responsibilities), threat model, audit posture, vulnerability
  reporting.

### Packaging

- 4 new force-include lines (`_security/lib`, `_cache/lib`,
  `_observability/lib`, `_doctor/lib`).
- 1 new `[project.scripts]` entry: `vstack-doctor`.
- 4 new testpaths.
- Version bump 0.5.0 → 0.6.0.

### Tests

- +113 new tests across `_security/tests/` (53),
  `_cache/tests/` (15), `_observability/tests/` (17),
  `_doctor/tests/` (8), and `_api/tests/test_api_security.py` (21
  new hardening + caching tests).
- Suite total: **2,088 passing** (up from 1,969 in v0.5.0).
- Mypy strict clean across all 14 surface lib dirs (the 10 from
  v0.5.0 + `_security`, `_cache`, `_observability`, `_doctor`).

## [0.5.0] — 2026-05-25

Phase 3 surface + depth-pass release. Adds the browser dev tooling
(Tier C #I5), the gbrain integration (semantic search over the
pattern catalogue), the canonical Span-of-Control calibration
baselines, the cross-pattern composition runbook, the in-repo
mkdocs-material documentation site, runnable framework demos under
`examples/`, the benchmark + comparative-eval harness, and the first
six narrative essays at Substack depth.

### Added — `vstack.browser` (Chrome DevTools MCP integration)

- Wraps the upstream `chrome-devtools-mcp` server. Scrape agent
  traces from LangSmith / Phoenix / Helicone / Langfuse without
  screen-scraping; screenshot detection reports; drive agents in
  the browser for evaluation.
- `BrowserSession`, `open_session` async context manager,
  `scrape_trace`, `screenshot_url`, `fill_form`, `KNOWN_DASHBOARDS`
  recipe catalogue (5 vendors).
- `vstack-browser` CLI: `scrape`, `screenshot`, `tools`
  subcommands.
- New `[browser]` optional extra (`pip install valanistack[browser]`).
- 28 new tests; all mock the upstream MCP boundary so Chrome
  doesn't need to be installed in CI.

### Added — `vstack.gbrain` (semantic search over patterns)

- Detects gbrain on PATH; semantic search via the gbrain CLI when
  available; graceful keyword-fallback when not.
- `indexed_corpus()` builds 34 documents (summary + group +
  schema info + playbook keys + composition); `sync_corpus()`
  writes them into gbrain idempotently.
- `vstack-gbrain` CLI: `status`, `sync`, `search`, `corpus`.
- 18 new tests; all mock `shutil.which` and `subprocess.run` so
  gbrain doesn't need to be installed in CI.

### Added — canonical calibration baselines (`_baselines/`)

- Three pre-computed Span-of-Control baselines covering the
  textbook crew topologies (small-flat, two-layer, hub-and-spoke).
  Deterministic because Span-of-Control's math is gated to Python.
- `_baselines/scripts/generate_canonical.py` regenerates them
  reproducibly.
- `_baselines/README.md` documents the recipe for users to build
  per-pattern baselines for the 33 LLM-bearing patterns.

### Added — `COMPOSITION-RUNBOOK.md`

- Repo-root document mapping the five canonical chains (F1
  confidently-wrong, T1 audit-crew, S1 bottleneck, C1 culture, D1
  calibration). Code + per-chain decision tables + cross-chain
  transitions + the shared executive-readout template.

### Added — in-repo documentation site (`docs/` + `mkdocs.yml`)

- mkdocs-material configuration with full navigation: Home, Quick
  start, Concepts, Patterns (3 modules), Surfaces (7), Workflows
  (5), Reference (4), Recipes (4 worked examples), Changelog.
- Build offline with `pip install valanistack[docs] && mkdocs
  build` (writes `site/` — no hosting required).
- 18 pages of structured content; integrates with the existing
  README + COMPOSITION-RUNBOOK + per-pattern docs.

### Added — `examples/` (runnable framework demos)

- 7 demo scripts: `langchain_demo.py`, `langgraph_demo.py`,
  `crewai_demo.py`, `autogen_demo.py`, `llamaindex_demo.py`,
  `pydantic_ai_demo.py`, `openai_assistants_demo.py`.
- Each script is self-contained (~50 lines) and exercises the
  adapter end-to-end with a tiny canonical Lewin / AAR / Lencioni
  invocation.

### Added — `vstack.benchmarks` + `vstack-bench` CLI

- `BenchmarkCase`, `BenchmarkSuite`, `BenchmarkRunner`,
  `BenchmarkReport` for running pattern suites end-to-end.
- Canonical 3-case suite (Lewin / AAR / Schein) ships built-in;
  custom suites loaded from JSON via `load_suite(path)`.
- Comparative harness: quick / standard / forensic side-by-side
  with elapsed-ms + severity + dominant-finding agreement signal.
- Stub-LLM friendly: the test suite drives the harness without
  burning API spend. Real numbers arrive when the user runs with
  their own LLM client.
- `vstack-bench` CLI: `list`, `run`, `compare` subcommands.
- 30 new tests.

### Added — `essays/` (Substack-ready narrative essays)

- `_TEMPLATE.md` canonical structure.
- Six anchor essays at depth (~700-900 words each): Lewin (#01),
  Lencioni (#17), Edmondson psych safety (#20), AAR (#30), Schein
  (#31), Span-of-Control (#34). The remaining 28 essays follow
  the template; quality bar established here.

### Packaging

- 3 new `[project.scripts]` entries: `vstack-browser`,
  `vstack-gbrain`, `vstack-bench`.
- 2 new optional extras: `[browser]` (pulls `mcp>=1.20.0`),
  `[docs]` (mkdocs + mkdocs-material).
- 3 new force-include lines.
- 3 new testpaths.

### Docker

- Refactored Dockerfile to install from the release.yml-built
  wheel artifact when present in `dist/`, with a PyPI fallback
  for local builds. Bypasses the PyPI CDN-propagation race that
  bit v0.4.0's docker workflow.
- docker.yml now triggers on `workflow_run` of Release (success),
  downloads the `release-dist` artifact, and feeds it to buildx.
  No PyPI calls inside the build.

### CI

- mypy strict loop covers all 10 surface lib dirs (the 7 from
  v0.4.0 + `_browser`, `_gbrain`, `_benchmarks`).
- Test job runs the new test dirs.
- Lint job covers the new dirs + `examples/` + `_baselines/scripts/`.
- Release smoke test imports `vstack.browser` / `vstack.gbrain` /
  `vstack.benchmarks`.

### Tests

- +74 new tests (28 browser + 18 gbrain + 30 benchmarks). Suite
  total: **1,969 passing** (up from 1,895 in v0.4.0).
- Mypy strict clean across all 10 surface lib dirs.

## [0.4.0] — 2026-05-25

Phase 2 of the expansion roadmap lands. v0.4.0 adds framework
adapters, a learning store, a telemetry aggregator, and config
generators for the remaining Tier B native platforms. vstack is now
reachable from LangChain / LangGraph / CrewAI / AutoGen / LlamaIndex
/ Pydantic AI / Open WebUI / OpenAI Assistants / Anthropic Messages
in addition to the v0.2.0+v0.3.0 surfaces.

### Added — `vstack.adapters` (framework bindings)

- Unified, registry-driven adapter module: same 34 patterns, eight
  framework-native shapes.
  - ``as_openai_tool_schemas()`` — OpenAI Chat / Assistants
    ``tools`` array. Pure JSON; no extra dependency.
  - ``as_anthropic_tool_schemas()`` — Anthropic Messages ``tools``
    array. Pure JSON.
  - ``as_autogen_function_manifest()`` + ``as_autogen_callables()``
    — Microsoft AutoGen function manifest + Python callables. Pure
    Python; no autogen import required.
  - ``as_openwebui_manifest(api_base_url=...)`` — Open WebUI tool-
    plugin manifest pointing at a running ``vstack-api``.
  - ``as_langchain_tools()`` — ``StructuredTool`` instances; needs
    ``valanistack[langchain]``.
  - ``as_langgraph_nodes()`` / ``node_for(pattern_name)`` — state-
    delta node factories; needs ``valanistack[langgraph]``.
  - ``as_crewai_tools()`` — ``BaseTool`` subclass instances; needs
    ``valanistack[crewai]``.
  - ``as_llamaindex_tools()`` — ``FunctionTool`` instances; needs
    ``valanistack[llamaindex]``.
  - ``as_pydantic_ai_tools()`` — ``(name, description, func)``
    triples; needs ``valanistack[pydantic_ai]``.
- Shared dispatcher (``run_pattern_dispatch``) — every adapter
  validates input against the pattern's Pydantic model, resolves an
  LLM client, runs the analyzer, and returns the detection as a
  JSON-safe dict (or a structured ``{"error", "message"}`` envelope).
- Adapter spec types (``PatternToolSpec``,
  ``list_pattern_tool_specs``) are framework-neutral and reusable
  for any custom adapter you want to write.

### Added — `vstack.learnings` + `vstack-learn` CLI

- Append-only JSONL store at ``~/.vstack/learnings.jsonl``.
- ``LearningRecord`` schema: pattern, mode, agent_id / crew_id,
  severity, profile_pattern, dominant_finding, interventions_applied,
  follow_up_outcome, notes, extra.
- ``LearningStore.record / recall / update_outcome / outcomes /
  iter_records / clear`` — streaming reads, latest-open-record
  mutation for outcome tagging.
- ``OutcomeAggregate`` rolls up ``(pattern, intervention) ->
  improved / no_change / worse / unknown`` counts with an
  ``improvement_rate`` property.
- ``vstack-learn`` subcommands: ``record``, ``recall``,
  ``outcome``, ``outcomes``, ``path``, ``clear``; all support
  ``--json``.

### Added — `vstack.analytics` + `vstack-analytics` CLI

- ``FileTelemetrySink`` — drop-in for ``vstack.aar.TelemetrySink``
  that appends one JSONL line per ``record_llm_call`` event to
  ``~/.vstack/analytics/telemetry.jsonl``. Activate once with
  ``enable_file_telemetry()`` at process start.
- ``TelemetryAggregator`` — streaming roll-ups: ``per_pattern()``,
  ``per_model()``, ``per_day()``, ``top_costs(n)``, ``total_cost()``.
- ``CostEstimator`` — baseline $/1k token rates for the major model
  ids (Claude 4 / 3.5, GPT-5 / 4o / 4-turbo, o1, local). Override
  per-model rates via the ``rates`` kwarg.
- ``vstack-analytics`` subcommands: ``summary``, ``top-costs``,
  ``cost``, ``raw``, ``path``; all support ``--json``.

### Added — `vstack-config gen-platform` (Tier B platforms)

- One-command config generators for the platforms that aren't already
  covered by ``vstack-mcp config-snippet``:
  ``cursor``, ``cline``, ``continue``, ``roo-code``, ``windsurf``,
  ``zed``, ``aider``, ``goose``, ``kiro``, ``openclaw``,
  ``codex-cli``, ``opencode``, ``docker-compose``.
- ``--write`` + ``--out`` + ``--force`` for writing the snippet
  directly to its suggested path.

### Packaging

- New optional extras: ``valanistack[langchain]``,
  ``valanistack[langgraph]``, ``valanistack[crewai]``,
  ``valanistack[llamaindex]``, ``valanistack[pydantic_ai]``,
  ``valanistack[adapters]`` (bundles all five). ``valanistack[all]``
  now includes everything.
- 2 new ``[project.scripts]`` entries: ``vstack-learn``,
  ``vstack-analytics``.
- Force-include extended with ``_adapters/lib``,
  ``_learnings/lib``, ``_analytics/lib``; pytest testpaths
  extended to include the new test dirs.

### CI

- mypy strict loop now covers ``_adapters``, ``_learnings``,
  ``_analytics`` alongside the v0.2.0 / v0.3.0 surfaces. Loop
  installs ``langchain-core langgraph llama-index-core pydantic-ai``
  so the framework-gated tests don't all skip in CI.
- Test job runs the new test dirs and installs the same lightweight
  framework extras. CrewAI stays gated locally (heavier dep tree).
- Lint job covers the new dirs.
- Release smoke test imports ``vstack.adapters`` /
  ``vstack.learnings`` / ``vstack.analytics`` so a dropped force-
  include can't ship.

### Tests

- ``_adapters/tests/`` (51), ``_learnings/tests/`` (15),
  ``_analytics/tests/`` (15), plus 7 new ``gen-platform`` tests in
  ``_memory/tests/`` bring the suite to **1,895 passing** (up from
  1,811 in v0.3.0; +84 new).

## [0.3.0] — 2026-05-25

Phase 1 of the expansion roadmap is complete. v0.3.0 lands four additional
invocation surfaces alongside the v0.2.0 MCP server, plus the persistent
local state store everything else can build on.

### Added — `vstack.memory` + `vstack-config` CLI

- New ``~/.vstack/`` home directory with subdirs for ``baselines/``,
  ``sessions/``, ``analytics/``. Override via the ``VSTACK_HOME`` env var.
- ``vstack-config`` CLI: ``get`` / ``set`` / ``list`` / ``unset`` / ``path``
  / ``keys`` / ``install-skills`` subcommands.
- 8 documented preference keys (default_mode, default_model, telemetry,
  log_level, preferred_llm, api_host, api_port, skills_install_path).
- Helpers exposed for downstream callers:
  ``baseline_path_for(name)``, ``get_baselines_dir()``,
  ``load_config()`` / ``save_config()``.

### Added — `vstack.upgrade` + `vstack-upgrade` CLI

- Hits the PyPI JSON index for ``valanistack``, picks the highest stable
  version (or pre-release if ``--allow-prereleases``), compares against
  the runtime ``vstack.__version__``, and prints the matching
  CHANGELOG.md section as migration notes. Never execs pip; the user
  runs the printed install command.
- ``--json`` for machine-readable output, ``--quiet`` for CI.
- 19 new tests; HTTP is mocked at the ``urllib.request`` boundary so
  CI never touches PyPI.

### Added — `vstack.api` + `vstack-api` CLI (FastAPI)

- HTTP surface for every pattern. Endpoints: ``/healthz``,
  ``/v1/patterns``, ``/v1/patterns/{name}`` (+ playbooks / citations /
  composition subpaths), ``/v1/analyze/{name}`` (POST). Accepts the
  trace either flat or wrapped in ``{trace, mode, model}``.
- FastAPI auto-generates the OpenAPI spec under ``/openapi.json`` and
  serves Swagger UI at ``/docs``.
- ``vstack-api`` CLI: ``serve`` (default), ``routes``, ``openapi``.
- New optional extra ``valanistack[api]`` (pulls FastAPI + uvicorn).
- 13 new tests via FastAPI's TestClient.

### Added — Docker (`ghcr.io/valani9/vstack`)

- ``Dockerfile`` at the repo root installs ``valanistack[all]``,
  sets ``VSTACK_HOME=/var/lib/vstack``, drops to a non-root user, and
  defaults ``CMD`` to ``vstack-mcp serve``. tini as PID 1 for clean
  signal handling.
- New ``.github/workflows/docker.yml`` builds multi-arch
  (linux/amd64 + linux/arm64) on every ``v*`` tag, publishes to GHCR
  with semver tags + ``latest``, generates SBOM + provenance
  attestations.

### Added — Claude Code skills (`_skills/`)

- 7 task-shaped SKILL.md essays: ``/vstack`` (meta router),
  ``/vstack-pick-pattern`` (interview), ``/vstack-post-incident``
  (AAR + Lewin + downstream chain), ``/vstack-audit-crew`` (5-pattern
  crew health), ``/vstack-bottleneck`` (Span + Structure + behavioral),
  ``/vstack-culture-check`` (Schein + Robbins + optional McGregor),
  ``/vstack-baseline`` (calibration roundtrip).
- Skills are *task-shaped*, not pattern-direct — each one composes
  multiple patterns into a real workflow.
- One-command install via ``vstack-config install-skills``.

### Added — CLIs

- ``vstack-mcp``, ``vstack-api``, ``vstack-config``, ``vstack-upgrade``
  all registered in ``[project.scripts]``. Together with the 34
  per-pattern CLIs from v0.1.0, every pattern + every surface is one
  command away.

### Tests

- ``_memory/tests/`` (16), ``_upgrade/tests/`` (19), ``_api/tests/`` (13)
  bring the suite to **1,811 passing** (up from 1,756 in v0.2.0).
- CI mypy loop extended with ``_memory``, ``_upgrade``, ``_api``;
  CI lint + test job paths extended to include the new surface dirs.
- Release smoke test now also imports ``vstack.mcp``, ``vstack.memory``,
  ``vstack.upgrade``, ``vstack.api`` to guard against force-include
  drift.

## [0.2.0] — 2026-05-25

First non-CLI invocation surface. vstack can now be driven from any
MCP-compatible client (Claude Desktop, Cursor, Cline, Continue,
ChatGPT, OpenAI Assistants, and the rest of the MCP ecosystem) in
addition to direct Python imports and per-pattern CLIs.

### Added — `vstack.mcp` (MCP server)

- **`vstack-mcp` CLI** — `vstack-mcp serve` runs a local stdio MCP
  server. Zero hosting cost: the user's MCP client spawns the server
  as a subprocess, exchanges JSON-RPC over stdin/stdout, and never
  reaches a network socket.
- **34 tools, one per pattern** — `vstack_lewin`, `vstack_aar`,
  `vstack_schein_culture`, `vstack_span_of_control`, etc. Each tool's
  input schema is the pattern's Pydantic input model merged with two
  optional top-level params (`mode`, `model`); each tool's output is
  the pattern's detection model serialized to JSON.
- **Resources** — `vstack://patterns/index` lists every registered
  pattern; `vstack://patterns/<name>/citations` exposes the per-
  pattern `CITATIONS.md`; `vstack://patterns/<name>/playbooks`
  exposes the failure-mode playbooks dict;
  `vstack://patterns/<name>/composition` exposes the cross-pattern
  handoff manifest.
- **Prompts** — `vstack_pick_pattern` is a meta routing prompt that
  takes a free-form problem description and recommends the right
  pattern + tool call. Each pattern also gets a
  `vstack_<name>_invoke` template (35 prompts total).
- **LLM client resolution** — env-var-driven: prefer Anthropic if
  `ANTHROPIC_API_KEY` is set, else OpenAI, else Ollama. Override
  via `VSTACK_MCP_LLM=anthropic|openai|ollama|stub`. A structured
  error response is returned when no API key is configured; the
  server never crashes silently.
- **Utility subcommands** — `vstack-mcp list-tools`,
  `vstack-mcp list-resources`, `vstack-mcp config-snippet
  {claude-desktop|cursor|cline|continue|generic}` for paste-ready
  client config.

### Added — packaging

- New `[mcp]` optional dependency: `pip install valanistack[mcp]`
  pulls in `mcp>=1.20.0`.
- `valanistack[all]` now also includes the MCP server alongside the
  three LLM-client extras.
- `vstack-mcp` registered as a new `[project.scripts]` entry point.

### Added — tests

- 222 new tests under `_mcp/tests/` exercising registry resolution
  (all 34 patterns introspect cleanly), tool / resource / prompt
  enumeration, full server-handler round-trips, and a stub-LLM
  end-to-end call through the Lewin pattern. Brings the suite total
  to 1,756 passing.

### Repo layout

- New `_mcp/` source folder mirroring the per-pattern `module-*/`
  shape: source in `_mcp/lib/` (force-included as `vstack/mcp/` at
  wheel build time), tests in `_mcp/tests/`. CI's mypy loop now
  includes `_mcp` alongside the 34 patterns.

## [0.1.0] — 2026-05-23

First production-ready release. All 34 patterns from the roadmap ship at
the 5-layer quality bar (README + library + demo + benchmark + essay).

### Added — top-level package

- `vstack.__version__` is now defined at the namespace root.
- `py.typed` marker ships in the wheel — downstream consumers now pick
  up the library's type hints by default.
- API stability promise documented in the top-level package docstring.

### Added — shared production-grade infrastructure (`vstack.aar.*`)

- **Structured logging** with run-id correlation: `new_run_id`,
  `run_context`, `get_logger`, `JsonFormatter`,
  `configure_json_logging`. Patterns can correlate every log line
  from a single diagnostic run via a stable identifier, and ship JSON
  logs to structured backends without per-pattern changes.
- **Token / cost telemetry**: `TelemetrySink` protocol,
  `InMemoryTelemetrySink`, `NullTelemetrySink`, `record_llm_call`,
  `time_call`, `set_default_sink`. Default is off (Null sink); when
  enabled, every LLM call emits an event with model + token counts +
  elapsed_ms + run_id + pattern.
- **Prompt-injection input guards**: `sanitize_for_prompt`,
  `detect_injection`, `fence`. Strip control characters, cap absurd
  field sizes, detect known impersonation phrases, and provide
  unambiguous delimiters for fencing user content inside prompt
  templates.
- **Async LLM client adapters**: `AnthropicAsyncClient`,
  `OpenAIAsyncClient`, `OllamaAsyncClient` — same constructor surface
  as the sync clients, with `async def complete(...)`. Enables
  parallel pattern fan-out in server traffic.
- **Token-usage tracking** on every sync + async client: `last_usage`
  attribute returns an `LLMUsage` dataclass (input/output/total
  tokens + model). Cost layers can read this after each call without
  changing the `complete(...) -> str` return signature.
- **Configurable timeouts** on all real clients
  (`DEFAULT_TIMEOUT_SECONDS = 120.0`). LLM calls can no longer hang
  indefinitely on a stalled provider.

### Added — security, release engineering, and docs

- `SECURITY.md` with vulnerability reporting policy.
- `CHANGELOG.md` (this file).
- Pre-commit hooks config (`.pre-commit-config.yaml`): ruff, ruff
  format, mypy, bandit, pip-audit.
- PyPI release workflow (`.github/workflows/release.yml`) — publishes
  to PyPI on git tag push via trusted publisher.
- CI extended with: bandit security scan, pip-audit dependency scan,
  coverage gate, all-34-namespaces import verification in the build
  job.
- README badges (CI status, PyPI version, Python versions, license).
- `examples/cookbook/` directory with cross-pattern composition
  examples (orchestrator + diagnostic, parallel fan-out, telemetry
  wiring).
- Per-pattern micro-benchmark harness
  (`benchmarks/_perf/run_perf_suite.py`) measuring stub-client
  latency p50/p95 across all 34 patterns for regression detection.

### Changed

- `Development Status` classifier promoted from `2 - Pre-Alpha` to
  `4 - Beta`.
- `Python :: 3.13` classifier added (already covered by CI matrix).
- `vstack.aar.__version__` synced to `0.1.0`.
- Documentation updated to reflect the production-readiness layer.

### Compatibility

All existing public APIs from `0.0.14` continue to work unchanged.
The new infrastructure modules are purely additive — patterns that
do not adopt structured logging, telemetry, or input guards still
function exactly as they did in `0.0.14`.

## [0.0.14] — 2026-05-22

Closing batch. Patterns #04, #05, #07, #12 ship — completing the
34-pattern roadmap.

- `vstack.danva_emotion` (#04) — DANVA-style emotion-recognition
  diagnostic. Per-emotion accuracy + intensity calibration + confusion
  patterns computed deterministically; LLM contributes only
  interventions.
- `vstack.cognitive_reappraisal` (#05) — Gross's reappraisal vs
  suppression vs rumination vs avoidance vs expression classifier with
  two LLM passes (strategy detection + interventions).
- `vstack.hexaco` (#07) — Lee & Ashton 6-factor personality fit
  diagnostic. H-factor (honesty-humility) risk reported separately
  from overall fit.
- `vstack.vroom_expectancy` (#12) — Victor Vroom's
  Expectancy × Instrumentality × Valence motivation calculus. Product
  computed deterministically in Python; LLM cannot override the math.

## [0.0.13] — 2026-05-22

- `vstack.goleman_ei` (#02) — Goleman's 2×2 emotional-intelligence
  diagnostic (self × other × recognition × regulation).
- `vstack.sdt_reward` (#10) — Self-Determination Theory intrinsic
  reward diagnostic (autonomy, competence, relatedness).
- `vstack.span_of_control` (#34) — six deterministic
  org-structure metrics computed in Python (max_span, mean_span,
  centralization_index, hierarchy_depth, span_gini,
  decision_bottleneck).

## [0.0.12] — 2026-05-22

- `vstack.org_structure` (#33) — six-dimensional org structure
  matrix + archetype classifier.
- `vstack.motivation_traps` (#09) — Saxberg's four motivation
  traps (values, self_efficacy, emotions, attribution).
- `vstack.glaser_conversation` (#21) — conversational-intelligence
  steering across three states × three levels.

## [0.0.11 and earlier]

See git history for v0.0.11 and prior batches. Roadmap kickoff at
`v0.0.1` with pattern #30 (AAR generator); v0.0.2–v0.0.11 shipped
patterns #17, #18, #03, #13, #27, #20, #29, #22, #28, #01, #19, #15,
#26, #14, #24, #11, #25, #31, #08, #23, #32, #16, #06 incrementally.

[0.1.0]: https://github.com/valani9/vstack/releases/tag/v0.1.0
[0.0.14]: https://github.com/valani9/vstack/releases/tag/v0.0.14
[0.0.13]: https://github.com/valani9/vstack/releases/tag/v0.0.13
[0.0.12]: https://github.com/valani9/vstack/releases/tag/v0.0.12
