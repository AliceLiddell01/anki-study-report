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

## Active Core baseline

- active branch: `core`;
- verified base branch: `master`;
- verified base SHA: `359c26f82a9ee78c8e27603f9ded5ca9bef2c71e`;
- Core HEAD before C1.1: `2b99b3468de0a46b00ce5be71e7c95da0930fb12`;
- C1.2 initial HEAD: `22c6820bee44d25c3d10b871eb008a91cd56da31`;
- C1.2 implementation commit: `13b1a20` (`feat: add the bounded canonical triage read API`);
- C1.2 contract/report commit: `e7c4ede` (`docs: document the canonical triage read contract`);
- C1.2 status: Complete;
- C1.3 initial HEAD: `e4292d090a79b857b81a987c8e0853656f178e0e`;
- C1.3 accepted implementation HEAD: `9e35f361aa786aedb44bbbe4a6224699239ecb0d`;
- C1.3 status: Complete;
- product contract: `docs/cards-v2-product-contract.md`;
- technical contract: `docs/cards-v2-triage-read-api.md`;
- supporting C1.2 report: `reports/core/c1-2-triage-model-read-api.md`;
- endpoint: token-protected `POST /api/triage/query`;
- local verification: focused backend/frontend checks and canonical `run_full_check.ps1 -SkipDocker` PASS;
- C1.2 cloud verification: Fast CI run [`29637594843`](https://github.com/AliceLiddell01/anki-study-report/actions/runs/29637594843) PASS on exact SHA `e7c4eded97886dc902499a0f4bdb44e842599bde` with exact package and diagnostics artifacts;
- C1.3 contracts: `docs/inspection-profiles-v1.md`, `schemas/inspection-profile-v1.schema.json`, triage schema v2 in `docs/cards-v2-triage-read-api.md`;
- C1.3 final pre-closeout Fast CI: run [`29641074560`](https://github.com/AliceLiddell01/anki-study-report/actions/runs/29641074560) PASS on exact SHA `9e35f361aa786aedb44bbbe4a6224699239ecb0d`;
- C1.3 real-Anki acceptance: run [`29641398848`](https://github.com/AliceLiddell01/anki-study-report/actions/runs/29641398848), `standard/cards`, `verify_restart=true`, source Fast CI `29641074560`, PASS on the same exact SHA;
- accepted restart assertions: revision remained 2; Japanese changed from `confirmed` to `needs_review` after the controlled fingerprint mutation; Programming remained `confirmed`; Japanese/Programming audio reasons changed from 1/0 to 0/0; the learning reason remained; profile evidence leaked no values;
- documentation closeout commit: the commit containing this handoff; its exact SHA is reported in the final closeout response to avoid a self-referential second commit;
- C1.4 accepted implementation HEAD: `b2e060d5c9676e6dfdbab7309927b854503d3c66`;
- C1.4 status: Complete;
- C1.4 route/contract: `#/settings/inspection-profiles`, `docs/inspection-profiles-ui.md`, report `reports/core/c1-4-inspection-profiles-ui.md`;
- C1.4 final pre-closeout Fast CI: run [`29644724894`](https://github.com/AliceLiddell01/anki-study-report/actions/runs/29644724894) PASS on exact accepted implementation HEAD with exact package artifact `8429718439`;
- C1.4 real-Anki acceptance: run [`29644836731`](https://github.com/AliceLiddell01/anki-study-report/actions/runs/29644836731), `standard/cards`, `verify_restart=true`, source Fast CI `29644724894`, PASS on the same exact SHA with redacted artifact `8429751360`;
- C1.4 accepted browser proof: confirmed lifecycle, dirty suggestion, bounded validate v2 preview, accessible unsaved-navigation guard and no horizontal overflow; restart preserved revision 2, changed Japanese to `needs_review`, kept Programming `confirmed`, preserved the learning reason and leaked no profile values;
- C1.5 accepted implementation HEAD: `0460afe472cd87029368924bdf5640e90271c03c`;
- C1.5 historical technical status: exact-SHA CI/E2E passed, but owner product acceptance was subsequently withdrawn;
- C1.5R status: In progress — Cards and Inspection Profiles UX remediation; C1.6 blocked and not started;
- C1.5 workspace: `#/cards` reads automatic triage v2 (7 days, limit 100), renders one native table queue plus persistent active-item Inspector, and obtains one sanitized preview through Search inspect;
- C1.5 local gate: canonical `run_full_check.ps1 -SkipDocker` PASS;
- C1.5 accepted Fast CI: run [`29648956309`](https://github.com/AliceLiddell01/anki-study-report/actions/runs/29648956309) PASS with exact package artifact `8430913583`;
- C1.5 real-Anki acceptance: run [`29649071545`](https://github.com/AliceLiddell01/anki-study-report/actions/runs/29649071545), `standard/cards`, `verify_restart=true`, PASS with redacted artifact `8430943370`;
- no pull request, merge, release, deployment or AnkiWeb publication was created.

Core remains an independent long-lived branch through C1 and C2. Do not merge or release it without a separate explicit owner decision after a stable Core build.

### Cards v2 product invariants

1. Cards is a local problem-triage workspace, not Search, Notification Center or Anki Browser.
2. The automatic surface is one `Требуют внимания / Requires attention` queue; reason families are filters, not tabs.
3. Explicit Search selections form a separate session-only `Выбрано в поиске / Selected in Search` workset.
4. One queue item is card-anchored and can aggregate several reasons; note-level scope and sibling implications are explicit.
5. Visible priority is categorical (`Высокий / Средний / Низкий`) and is explained by reason/evidence; numerical `riskScore` is not user-facing.
6. Content-quality issues are authoritative only under a confirmed Inspection Profile; learning-behavior issues remain profile-independent.
7. Successful actions lead to `Awaiting recheck`; only canonical detector/collector/profile re-evaluation resolves an issue.
8. The desktop default is a compact bounded queue plus Inspector with the existing sanitized Shadow DOM preview.
9. Search inspect, Safe Actions, Signals, Notification handoff and preview isolation are reused; no duplicate query/action/signal stack is allowed.
10. Active item, keyboard focus and bulk selection remain separate interaction states.

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

`C1.2 — Canonical triage model and read API` is complete. `C1.3 — Inspection
Profiles: contract and runtime` is also complete after exact-SHA Fast CI
`29641074560` and accepted real-Anki `standard/cards` restart run `29641398848`
on implementation HEAD `9e35f361aa786aedb44bbbe4a6224699239ecb0d`.
The evidence covers profile-local persistence, fingerprint mismatch,
fail-closed content checks, Programming/Japanese isolation, preserved learning
reasons and value-safe evidence. `C1.4 — Inspection Profiles: user
configuration` is complete with the lazy Settings editor, validate
v2 bounded sample, strict import/export, revision conflict handling, RU/EN and
real-Anki screenshot assertions. Canonical local checks, exact-SHA Fast CI
`29644724894` and targeted restart run `29644836731` are accepted on
`b2e060d5c9676e6dfdbab7309927b854503d3c66`. C1.5's old implementation on
`0460afe472cd87029368924bdf5640e90271c03c` passed Fast CI `29648956309` and
targeted `standard/cards` restart `29649071545`, but subsequent owner screenshot
and real-profile review rejected product acceptance. C1.5R is in progress to
correct compact identity, native front/answer preview semantics, independent
current-content candidates, the Cards inbox, and guided Inspection Profiles.
C1.6 is blocked and has not started.

C1 must reuse Search, Safe Actions, Signals, Notification Center and the existing isolated preview rather than create duplicate workflows. `C2` freezes/hardens contracts after C1, although prerequisite hardening may occur inside C1.

### Gamification

The source branch `chatgpt/gamification-concept-foundation` is research-only and materially diverged from `master`. Do not merge/rebase it wholesale.

Confirmed roadmap status:

- Progression and Anki XP foundations: `DRAFT v0.2`;
- Review concept documents: developed drafts;
- Review simulation closure: `PARTIAL`;
- blocker: cross-horizon retention-cycling evidence gap;
- Learn XP: not started;
- Create XP: not started;
- global conversion and production ledger/API/migrations/UI: not designed.

Direct spot-checks confirmed populated simulator implementation and tests, including a scenario test asserting 26 scenarios and 53 assertions. The branch checks were not executed in this roadmap task; `G0` must reconcile the diverged branch with current `master` and reproduce the documented evidence before further authoritative research work.

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

Use focused tests first, then exact Fast CI artifact, then only required targeted real-Anki scope. Do not repeat successful same-SHA gates. Docs-only product-contract work does not require Fast CI or Docker E2E.

Before closing work:

- confirm branch/base/head and unrelated changes;
- run `git diff --check` when a checkout is available;
- validate relative Markdown links;
- confirm no production/research code, workflow or generated artifact diff;
- inspect actual CI evidence before claiming PASS;
- do not merge, deploy or release without explicit authorization.
