# Python test performance roadmap

**Role:** supporting engineering roadmap for Core; not a new `C` stage
**Status:** Planned / measurement-gated
**Primary relationship:** supports `C2 Core 1.0 Hardening`
**Platform relationship:** implementation in mandatory Fast CI is governed by `CI 7 → CI 8`

## Why this exists

The Python suite is approaching one thousand tests and remains part of the canonical non-Docker gate. Test count alone is not a defect, but an increasingly slow feedback loop raises the cost of every Core change, encourages overly broad reruns and makes local reproduction less practical.

This roadmap reduces verified wall time without removing coverage, weakening security contracts or creating a second test system. It covers test architecture, fixtures, deterministic parallel execution and developer ergonomics. Workflow-level adoption remains coordinated with the Platform / CI track.

## Position in the roadmap

```text
C1 Cards v2
→ C2 Core 1.0 Hardening
   └─ Python test performance roadmap, when activated by measurements

CI 7 rolling baseline
→ CI 8 Fast CI critical path, if Python is the selected bottleneck
```

The initiative may begin during `C1` only when Python test cost materially blocks Cards work or when a required isolation fix belongs to the changed test area. It does not block `C1` completion by default and does not become a permanent prerequisite for unrelated product work.

## Goal

Establish a fast, deterministic and maintainable Python test contour with:

- one authoritative test inventory;
- a reliable serial fallback;
- an evidence-backed parallel mode only if it is safe and beneficial;
- bounded fixture and database setup cost;
- focused local commands that do not replace the complete Fast CI gate;
- reproducible timing evidence for later regressions.

## Non-goals

- deleting tests merely to improve timing;
- reducing sanitizer, token, media, action, APKG, migration or package coverage;
- hiding worker-dependent failures through retries, quarantine or larger timeouts;
- changing production behavior to satisfy slow or outdated tests;
- enabling path-based skipping of the full mandatory Fast CI gate;
- introducing self-hosted runners, larger runners or broad CI sharding as the first solution;
- optimizing real-Anki Docker E2E under this roadmap;
- turning benchmark artifacts into committed runtime output.

## Activation criteria

Start implementation only when at least one condition is supported by current evidence:

- Python tests are a top Fast CI critical-path contributor selected by `CI 7`;
- Python phase p50 is at least 20% of canonical Fast CI wall time;
- a controlled estimate shows at least 30 seconds or 20% Python-phase direct saving;
- local full Python runs materially delay active Core development;
- repeated fixture, SQLite, import or polling cost is visible in duration evidence.

If measurements do not show a material problem, keep this roadmap Planned and do not add parallelism or maintenance overhead pre-emptively.

## Required baseline

Before optimization, capture a reproducible baseline on an exact commit and stable toolchain.

Required evidence:

- Python and pytest versions;
- operating system, runner class and logical CPU count;
- collected test count and deselected/skipped counts;
- total collection and execution wall time;
- slowest setup/call/teardown entries;
- time by test module or another stable grouping;
- serial first-run pass/failure result;
- current Fast CI Python phase p50/p95 from ordinary runs when available;
- known platform-specific skips and Anki stub boundaries.

Canonical diagnostic examples:

```powershell
node scripts/run_python.mjs -m pytest --collect-only -q
node scripts/run_python.mjs -m pytest --durations=50 --durations-min=0.05
```

A dedicated performance task may run a bounded controlled comparison. It must not create routine warm-cache reruns or repeatedly exercise unrelated mandatory gates.

## Milestone 1 — Measurement and classification

Produce one baseline report that classifies the dominant cost rather than assuming parallelism is the answer.

Classify time into:

- collection/import;
- fixture setup and teardown;
- test body execution;
- SQLite/database construction and copying;
- filesystem and archive work;
- sleeps, polling and retry loops;
- subprocess or PowerShell/Node bridging;
- a small number of long tests versus distributed per-test overhead.

Deliverables:

- machine-readable timing output or reproducible analysis command;
- top slow tests and modules;
- top expensive fixtures;
- one selected optimization candidate;
- expected direct saving, implementation cost, regression risk and stop condition.

Do not start multiple optimization candidates in parallel.

## Milestone 2 — Isolation and determinism audit

Audit the suite before any parallel execution is accepted.

Required checks:

- shared mutable module and process state;
- writes to `os.environ`, `sys.path`, `sys.modules` and global registries;
- fixed temporary paths, archive names and SQLite filenames;
- session/module fixtures that return mutable state;
- `autouse=True` fixtures and their transitive dependencies;
- tests that depend on execution order or leftovers from earlier tests;
- nondeterministic parametrization from sets or unordered data;
- shared Anki stubs and monkeypatch restoration;
- platform-specific assumptions, path separators, permissions and line endings;
- subprocesses, ports and background threads that can collide;
- generated package/dashboard paths used by more than one test.

Every discovered collision receives one of four outcomes:

- isolate with worker-specific temporary state;
- make the fixture immutable/read-only;
- group genuinely coupled tests deliberately;
- keep the affected scope serial with a documented reason.

A parallel failure is a regression to diagnose, not a flaky result to rerun away.

## Milestone 3 — One bounded parallel pilot

After the isolation audit, evaluate `pytest-xdist` as a candidate rather than an assumed dependency.

Compare on the same source and test inventory:

```text
serial
-n 2
-n 4
-n 4 --dist=worksteal
-n 4 --dist=loadscope
```

The `loadscope` candidate is included only when the audit shows that fixture locality may matter.

Rules:

- do not use `-n auto` as the initial project default;
- use a fixed bounded worker count in CI;
- preserve a documented serial command;
- compare collected, passed, failed, skipped and deselected counts;
- include worker startup, repeated collection and per-worker session-fixture cost;
- test on the authoritative Fast CI platform before changing the mandatory gate;
- do not combine the pilot with runner migration, coverage changes or job splitting.

Adopt parallel execution only when it produces a material direct saving and remains deterministic. Otherwise reject it and continue with serial hotspot optimization.

## Milestone 4 — Hotspot optimization

Apply only optimizations supported by the baseline.

Preferred order:

1. Remove accidental repeated work in fixtures and helpers.
2. Narrow unnecessary `autouse` fixtures and move them to local `conftest.py` scopes.
3. Raise fixture scope only for immutable or safely reset state.
4. Replace repeated SQLite schema/data construction with validated template-copy patterns where migration behavior is not under test.
5. Replace real sleeps with injected clocks, events or deterministic state transitions where wall time is not the contract.
6. Reuse parsed read-only fixture data without sharing mutable results.
7. Reduce repeated package/archive work inside tests while preserving package validation coverage.
8. Optimize pathological production-independent test helpers when profiling proves their cost.
9. Consider bounded test grouping or sharding only after in-process parallelism and fixture work are insufficient.

Each change must state which measured cost it removes. Refactors without a timing hypothesis are outside this performance task.

## Milestone 5 — Adoption and regression budget

When the selected solution is accepted:

- keep the same canonical non-Docker entrypoint;
- expose focused local Python commands without making them merge evidence;
- update `requirements-dev.txt` and dependency policy only if a new test dependency is adopted;
- update `run_full_check.ps1`, Fast CI, timing schema and tests together if execution semantics change;
- update `docs/test-matrix.md`, `docs/verification-run-policy.md`, `docs/ci-cd.md` and a closeout report;
- retain serial execution as a diagnostic fallback;
- record worker count and distribution strategy explicitly rather than deriving them from host CPU count;
- observe ordinary post-change runs for p50/p95 and first-run pass-rate regression.

## Acceptance criteria

All criteria are required for adoption:

- complete Python test inventory is preserved;
- serial and accepted optimized modes collect equivalent tests;
- mandatory checks and coverage contracts are not removed;
- no new ordering dependency, shared-path collision or worker-only failure remains;
- Python phase p50 improves by at least 20%, or the project records a justified alternative material threshold from the baseline;
- Fast CI p95 does not regress materially;
- first-run pass rate does not decrease in ordinary runs;
- local canonical command and cloud command graph remain aligned;
- exact package metadata, inventory and SHA-256 contracts remain unchanged;
- Windows/platform-specific coverage remains explicit if the primary runner changes later;
- the maintenance cost of the solution is lower than the saved developer and CI time.

If these criteria are not met, retain the serial contour, document the rejected candidate and close the performance task without forcing adoption.

## Verification plan for implementation

Minimum implementation verification:

- focused tests for changed fixtures/helpers/configuration;
- one full serial Python run;
- one full candidate-mode Python run on the same exact commit;
- explicit inventory/result comparison;
- `git diff --check` and dependency/config validation;
- canonical `run_full_check.ps1 -SkipDocker` after the final implementation;
- one authorized exact-SHA Fast CI run when workflow or canonical execution changes.

Docker/real-Anki E2E is not required for test-runner-only changes unless the actual diff also changes runtime, package, APKG or E2E contracts.

## Evidence and closeout

Store historical measurements and the final decision under `reports/`; do not commit raw caches, profiles, temporary databases or benchmark output directories.

The closeout report must state:

- baseline and exact source identity;
- selected and rejected candidates;
- direct before/after Python phase comparison;
- Fast CI wall-time and Actions-minutes impact;
- flake/determinism evidence;
- dependency and maintenance impact;
- preserved fallback and rollback procedure;
- remaining known slow scopes;
- decision: `adopt`, `defer` or `reject`.

## Rollback

Rollback is required when ordinary runs show worker-only failures, p95 regression, unstable test inventory, hidden state leakage or maintenance cost greater than the measured benefit.

Rollback restores the previous serial canonical execution without reverting independent fixture correctness improvements. The closeout report records the reason and prevents repeating the same rejected experiment without new evidence.
