# Передача контекста новому чату/нейронке

Снимок: **2026-07-18**.

## Начать отсюда

1. `README.md`
2. `roadmap/README.md`
3. `docs/project-overview.md`
4. `docs/architecture.md`
5. профильный current-contract документ
6. `reports/README.md` только для historical evidence

При конфликте:

```text
production code/tests
→ current docs
→ roadmap
→ reports
→ old plans/assumptions
```

## Product state

Anki Study Report — local add-on for Anki 26.05+ with Python runtime, React/TypeScript dashboard and token-protected loopback server. Frontend does not access the collection directly.

Accepted product contour is complete through Stage 9.5:

```text
Stage 0–5.5  foundation, IA, Settings, Profile, Activity, Decks, UI controls
Stage 6–7    Statistics, FSRS analytics, RU/EN localization
Stage 8      Search and undoable Safe Actions
Stage 9–9.5  notices, opt-in telemetry, Signals, Notification Center, toasts
```

## Roadmap model

Future work is organized by tracks:

```text
C  Core: C1 Cards v2 → C2 Core 1.0 → C3? contextual additions
G  Gamification: research reconciliation through optional MVP
O  Operations: protected telemetry admin dashboard
I  Identity: conditional continuity/linking gate
E  Extensions: conditional first-party ecosystem
CI Platform: delivery/E2E/release
```

Only `C1 → C2` is the mandatory add-on path.

### Core

`C1 Cards v2 / Problem Triage` remains the recommended next core stage. It must reuse Search, Safe Actions, Signals, Notification Center and the existing isolated preview rather than create duplicate workflows. `C2` freezes/hardens contracts after C1, although prerequisite hardening may occur inside C1.

### Gamification

The source branch `chatgpt/gamification-concept-foundation` is research-only and materially diverged from `master`. Do not merge/rebase it wholesale.

Confirmed roadmap status:

- Progression and Anki XP foundations: `DRAFT v0.2`;
- Review concept documents: developed drafts;
- Review simulation closure: `PARTIAL`;
- blocker: cross-horizon retention-cycling evidence gap;
- Learn XP: not started;
- Create XP: not started;
- global conversion and production ledger/API/migrations/UI: not designed;
- branch contains zero-length implementation/test files and requires `G0` reconciliation.

Research candidates are not production economy. Gamification does not block core.

### Telemetry operations

Current telemetry service has only bounded ingestion/schema/deletion endpoints, no dashboard or generic query API. `O1` is a separate Access-protected read-only admin application with Worker-side JWT validation and prepared bounded D1 queries. It never becomes a route or secret-bearing mode in the add-on.

### Identity and extensions

`I1` activates only for a proven cross-installation requirement. `installation_id != person_id`; `person_id` is absent by default and requires explicit opt-in, unlink/revoke/export/delete and a separate threat/privacy migration. Fingerprinting is forbidden.

Extensions are non-critical. `E1` begins only with one concrete first-party reference pack; no marketplace, remote code or placeholders.

## Platform state

CI Stage 6B is Complete:

```text
cloud environment: exact immutable GHCR digest
manual E2E: exact Fast CI package
release E2E: exact release artifact
local Docker build: diagnostic fallback
cloud BuildKit/GHA cache: removed
```

CI 7 is a measurement gate. CI 8/9/10 activate only for one proven bottleneck/flake class. Release remains manual and approval-gated.

## Technical invariants

1. Payload/public behavior changes synchronize backend, frontend types/validators, tests and docs.
2. Frontend never reads Anki collection directly.
3. Server remains loopback-only and token-protected.
4. Sanitizer, media validation, action allowlists and preview isolation are not weakened.
5. Generated assets/runtime artifacts/profile data/tokens are not committed.
6. Signals/evidence/entity refs stay local and outside telemetry taxonomy.
7. Telemetry/admin/identity/gamification data purposes remain separated.
8. Research packages do not silently enter Fast CI or `.ankiaddon`.
9. Release uses exact artifacts and never occurs automatically after merge.

## Verification

Canonical non-Docker check:

```powershell
.\scripts\run_full_check.ps1 -SkipDocker
```

Use focused tests first, then exact Fast CI artifact, then only required targeted real-Anki scope. Do not repeat successful same-SHA gates. Docs-only roadmap work does not require Docker E2E.

Before closing work:

- confirm branch/base/head and unrelated changes;
- run `git diff --check` when a checkout is available;
- validate relative Markdown links;
- confirm no production/research code, workflow or generated artifact diff;
- inspect actual CI evidence before claiming PASS;
- do not merge, deploy or release without explicit authorization.
