# E2E observability, diagnostics and build identity roadmap

**Status:** Planned  
**Track:** Platform / CI  
**Base:** real-deck E2E foundation from PR #133  
**Scope:** Fast CI and real-Anki Docker E2E observability, diagnostics, cancellation, preflight, non-release build identity and performance evidence.

## Why this roadmap exists

The real-deck E2E foundation already provides a strong execution contour:

- exact Fast CI or release package handoff;
- three committed working APKG packages;
- deterministic real-card scenarios without synthetic content;
- API, browser, restart, telemetry and artifact evidence;
- structured Fast CI timing and E2E phase/resource telemetry;
- package/harness identity separation with fail-closed reuse.

The remaining problem is not absence of diagnostics. Existing diagnostics are fragmented across GitHub workflow YAML, PowerShell, Bash, Python and Node.js. A developer still has to reconstruct what is running, where it failed, whether cancellation was handled correctly and which exact non-release build produced the evidence.

This roadmap turns the existing pieces into one coherent run protocol. It is intentionally divided into six large deliverable stages. Do not create nested implementation stages such as `E2E-I2.1` or `E2E-I4a`; a stage may use ordinary implementation tasks and commits without changing the roadmap hierarchy.

## Delivery order

```text
E2E-I1 Unified live run protocol
→ E2E-I2 Browser smoke progress
→ E2E-I3 Stable failure diagnostics
→ E2E-I4 Preflight and cancellation
→ E2E-I5 Non-release build identity
→ E2E-I6 Final summary and performance history
```

Each stage must leave the repository in a useful, independently verifiable state. A later stage may extend an earlier schema, but it must not require all six stages to land before the earlier result becomes usable.

## Shared invariants

All stages must preserve the existing platform and security contracts:

- real Anki Desktop remains the integration boundary;
- cloud E2E uses an immutable GHCR digest;
- package bytes remain exact and SHA-256 verified;
- package/harness reuse remains ancestry- and full-diff-validated;
- no source-build fallback in cloud E2E;
- no token-bearing URL, private absolute path, profile data or credential in public evidence;
- no synthetic notes/cards/templates/media are reintroduced;
- release remains manual, approval-gated and exact-artifact based;
- successful unchanged package/harness pairs are not rerun without a concrete reason;
- runtime artifacts, metrics, logs and screenshots are never committed.

## E2E-I1 — Unified live run protocol

**Goal:** make Fast CI and Docker E2E report progress through one stable event model while preserving readable local console output.

### Deliverables

- Introduce one schema-versioned run-event contract for Fast CI and real-Anki E2E.
- Write every event to both:
  - immediate stdout/stderr output;
  - a structured JSONL evidence stream such as `run-events.jsonl`.
- Standardize the minimum event fields:
  - UTC timestamp;
  - elapsed duration;
  - producer;
  - phase ID;
  - event kind;
  - status;
  - optional progress counters;
  - optional bounded message;
  - optional failure code reserved for E2E-I3.
- Add thin adapters for PowerShell, Bash, Python and Node.js instead of introducing a logging service.
- Use stable phase identifiers shared by console output, timing reports and final summaries.
- Make Docker/Compose output deterministic in CI: plain progress, no interactive menu and no TTY-only animation.
- Preserve detailed raw diagnostics in artifacts while keeping the primary console stream readable.

### Expected console shape

```text
[00:37.842] [E2E] [browser-smoke] START plan routes=10 previews=6
[00:39.106] [E2E] [browser-smoke] [1/18] PASS page=home theme=light duration=1264ms
[00:40.511] [E2E] [browser-smoke] [2/18] PASS page=home theme=dark duration=1405ms
```

### Completion criteria

- Local PowerShell execution and GitHub Actions display the same phase names and statuses.
- A schema validator rejects unknown status values, unsafe paths and token-bearing values.
- Fast CI and Docker E2E each produce a validated event stream on success and controlled failure.
- Existing package, sanitizer and real-deck gates remain unchanged in meaning.

### Out of scope

- browser scenario expansion;
- visual regression;
- performance thresholds;
- migration to an external logging stack.

## E2E-I2 — Browser smoke progress

**Goal:** eliminate the long silent interval inside `smoke-browser.mjs` and expose useful item-level timing.

### Deliverables

- Print a browser smoke plan before Chromium starts:
  - routes and themes;
  - native previews;
  - state checks;
  - telemetry contour when enabled;
  - expected screenshot count.
- Report START/PASS/FAIL and duration for every route/theme capture.
- Report START/PASS/FAIL and duration for every native preview anchor.
- Report progress for scenario-card checks, Cards route inspection and telemetry lifecycle.
- Preserve page errors, failed requests, console errors and external-request evidence.
- Extend browser performance evidence with per-item durations and the slowest items.
- Keep the direct Playwright API architecture unless a separate evidence-backed decision justifies migration to Playwright Test.

### Completion criteria

- No browser smoke operation expected to take more than a few seconds remains silent.
- A controlled browser failure identifies the exact route, theme, anchor or telemetry step.
- Screenshot count and browser plan agree fail closed.
- Existing light/dark, native-preview and external-network assertions still pass.

### Out of scope

- new dashboard route coverage;
- pixel/perceptual baseline comparison;
- automatic browser retries.

## E2E-I3 — Stable failure diagnostics

**Goal:** replace generic exit status reconstruction with a stable machine-readable failure taxonomy and a concise human summary.

### Deliverables

- Introduce a reviewed registry of stable string failure codes, for example:
  - `ASR-E2E-PREFLIGHT-CONFIG`;
  - `ASR-E2E-COMPOSE-INVALID`;
  - `ASR-E2E-PACKAGE-HANDOFF`;
  - `ASR-E2E-REAL-DECK-CONTRACT`;
  - `ASR-E2E-ANKI-START`;
  - `ASR-E2E-READY-TIMEOUT`;
  - `ASR-E2E-API-SMOKE`;
  - `ASR-E2E-BROWSER-SMOKE`;
  - `ASR-E2E-RESTART`;
  - `ASR-E2E-ARTIFACT-SANITIZE`;
  - `ASR-E2E-CLEANUP`;
  - `ASR-E2E-CANCELLED`;
  - corresponding Fast CI categories where useful.
- Keep process exit codes coarse and documented; use the string code as the analytical source of truth.
- Capture the first functional failure as the primary failure.
- Record cleanup, sanitizer, uploader or summary failures as secondary failures instead of overwriting the root cause.
- Produce on every failure:
  - `reports/failure-summary.json`;
  - `reports/failure-summary.md`;
  - a short console/GitHub annotation.
- Include phase, elapsed time, last successful phase, safe message, exception type, cleanup status and relative evidence paths.
- Preserve full stack traces only in detailed diagnostics.

### Completion criteria

- The same controlled failure produces the same stable failure code locally and in GitHub Actions.
- A secondary cleanup failure cannot replace the primary browser/API/runtime failure.
- Failure summaries pass the existing redaction and public-artifact boundary.
- Tests lock the registry and prevent accidental renaming or reuse of published codes.

### Out of scope

- automatic rerun policy;
- flake classification and quarantine;
- issue creation from failures.

## E2E-I4 — Preflight and cancellation

**Goal:** reject invalid runs before expensive Docker work and terminate cancelled runs cleanly without disguising cancellation as an ordinary failure.

### Deliverables

- Add one host-side preflight used by local wrappers and cloud workflows before Docker pull/build/run.
- Validate at minimum:
  - mode, scope, workers and restart policy;
  - package-source combinations;
  - required files and writable artifact directory;
  - staged package metadata and SHA-256 when available;
  - real-deck manifest, package presence, sizes and checksums;
  - environment image lock and exact digest inputs;
  - safe relative paths and mount sources;
  - resolved `docker compose config --quiet` contract.
- Write a bounded `preflight-report.json`.
- Reorder cloud checks so static configuration validation occurs before GHCR login and image pull where possible.
- Audit `if: always()` usage in workflows. Keep only short emergency finalization where cancellation semantics require it.
- Handle `SIGINT`, `SIGTERM`, Ctrl-C and PowerShell interruption explicitly.
- Mark cancelled runs as `cancelled` with `ASR-E2E-CANCELLED`, not generic `failure`.
- Make process cleanup idempotent and bounded:
  - stop Anki;
  - stop telemetry fake and resource sampler;
  - stop/remove Compose resources when they exist;
  - restore artifact ownership when possible;
  - preserve the original cancellation/result.

### Completion criteria

- Invalid mode/package/manifest/Compose configurations fail before a container is launched.
- A cancellation test leaves no running E2E containers or background helper processes.
- Cancellation produces a partial but valid summary and does not run unnecessary heavy artifact work.
- The original functional result is restored after cleanup exactly once.

### Out of scope

- force-cancel automation through the GitHub REST API;
- self-hosted runner lifecycle management;
- broad Docker environment redesign.

## E2E-I5 — Non-release build identity

**Goal:** give every successful non-release Fast CI package a unique, traceable identity without changing canonical release SemVer or release preparation.

### Model

Keep two separate values:

```text
canonicalVersion = release/product version from version.py
buildIdentity     = exact non-release CI execution identity
```

A generated display version may use SemVer pre-release and build metadata, for example:

```text
1.2.0-ci.842+run.30013925137.attempt.1.pr.133.branch.test-real-deck.sha.bd0355c3
```

The numeric values above are examples only.

### Deliverables

- Generate a unique machine build ID such as `fast-<run-id>-a<attempt>`.
- Resolve and sanitize:
  - canonical version;
  - event type;
  - branch name;
  - Fast CI run ID and run number;
  - run attempt;
  - PR number when unambiguous;
  - exact commit SHA.
- For pull-request events, use the event payload PR number.
- For branch/manual events, resolve a PR only when exactly one safe match exists; otherwise record `null` or `ambiguous`, never guess.
- Add generated non-release build information to the package, for example `build_info.json`.
- Extend `package-metadata.json` with the same build identity under a new schema version.
- Expose bounded build information through runtime diagnostics so E2E can prove:

```text
package metadata identity
= packaged build_info identity
= running add-on identity
```

- Keep release artifacts clean:
  - `channel=release`;
  - canonical version unchanged;
  - no branch/PR/run-specific display version required.
- Document that reruns with different attempts intentionally produce different non-release package bytes because build identity is embedded.

### Completion criteria

- Two Fast CI attempts for the same commit have distinct build identities and exact package hashes.
- E2E rejects a mismatch between handoff metadata, packaged build info and runtime identity.
- Release preparation and release package identity remain unchanged.
- Branch slugs and metadata are bounded, deterministic and safe for JSON, logs and artifact names.

### Out of scope

- automatic canonical version bumping;
- changing AnkiWeb release semantics;
- replacing exact SHA-256 package identity with a version string.

## E2E-I6 — Final summary and performance history

**Goal:** produce one authoritative result summary and retain compact metrics suitable for future trend analysis.

### Deliverables

- Replace fragmented end-of-run summaries with one canonical aggregator that consumes available partial reports.
- Generate:
  - `run-summary.json`;
  - `run-summary.md`;
  - one compact `GITHUB_STEP_SUMMARY` section.
- Include:
  - SUCCESS / FAILURE / CANCELLED;
  - canonical version and build identity;
  - branch, PR and SHA;
  - package source and package SHA-256;
  - mode, scope, workers and restart status;
  - completed checks;
  - primary/secondary failure codes;
  - last successful phase;
  - total duration;
  - slowest phases and browser items;
  - peak CPU and memory;
  - screenshot count;
  - artifact and cleanup status.
- Normalize existing Fast CI timing, E2E phase timing, browser timing, image preparation, resource telemetry and artifact upload timing into `metrics/run-performance.json`.
- Store dimensions needed for comparison:
  - workflow;
  - mode and scope;
  - workers;
  - package source;
  - image digest/cache state;
  - Anki version;
  - build ID;
  - commit, branch and PR.
- Publish a compact metrics artifact with longer retention than heavy screenshots/logs when repository policy permits.
- Define comparison guidance for future p50/p95 and first-run pass-rate analysis.

### Completion criteria

- Success, controlled failure and cancellation each produce a valid canonical summary.
- Summary values are recomputed from source evidence instead of trusting unchecked environment strings.
- Timing/resource metrics remain informational; no run fails because a duration exceeded an unvalidated threshold.
- A future analyzer can compare compatible runs without parsing console text.

### Out of scope

- performance blocking thresholds;
- dashboards or external telemetry service for CI metrics;
- scheduled trend analyzer implementation;
- automatic optimization changes based on one run.

## Verification policy for the roadmap

Do not run a full Docker matrix after every small implementation commit. For each stage:

1. add focused unit/contract tests;
2. run relevant local non-Docker checks;
3. use one controlled negative case when the stage concerns failure or cancellation;
4. run targeted real-Anki E2E for the affected contour;
5. run one final `standard/full` only when the stage changes the end-to-end lifecycle, package identity or canonical summary boundary;
6. do not repeat a successful unchanged package/harness pair.

The whole roadmap is complete when all six stages are implemented, documented and owner-accepted. Completion does not automatically activate CI 7–12 optimization work, visual regression or release publication.

## External references used for the design

- GitHub Actions workflow commands and job summaries: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands
- GitHub Actions cancellation behavior: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-cancellation
- Docker Compose predefined output variables: https://docs.docker.com/compose/how-tos/environment-variables/envvars/
- Docker Compose CLI/config: https://docs.docker.com/reference/cli/docker/compose/ and https://docs.docker.com/reference/cli/docker/compose/config/
- Playwright test steps/reporters, retained as a reference rather than a required migration: https://playwright.dev/docs/api/class-test and https://playwright.dev/docs/test-reporters
- Semantic Versioning 2.0.0 pre-release and build metadata: https://semver.org/
