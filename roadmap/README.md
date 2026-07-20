# Roadmap Anki Study Report

Снимок: **2026-07-20**.

Roadmap состоит из одного обязательного core path и нескольких независимых или условных tracks. Номер больше не означает глобальную очередь между несвязанными направлениями. При конфликте production code/tests и current contracts имеют приоритет над roadmap и historical reports.

## Текущее положение

Завершённый product contour: **Stage 0–9.5**.

```text
Foundation / IA / Settings / Profile / Activity / Decks
→ Statistics / FSRS / Localization
→ Search / Safe Actions
→ Notices / opt-in Telemetry / Signals / Notifications
```

Следующая обязательная работа основного add-on:

```text
C1 Cards v2 / Problem Triage
→ C2 Core 1.0 Hardening
→ C3 Contextual Additions, только если выявлен доказанный gap
```

Параллельные направления не блокируют `C1`/`C2`:

- `G` — Gamification research/product;
- `O` — telemetry operations и условные операции будущего cloud-сервиса;
- `I` — Identity continuity, conditional;
- `E` — Extension ecosystem, deferred/conditional;
- `CI` — platform, delivery and real-Anki verification.

## Карта tracks

| Track | Роль | Текущий статус | Не блокирует |
| --- | --- | --- | --- |
| [Core `C`](core/README.md) | единственный critical path add-on | `C1` Next | — |
| [Gamification `G`](gamification/README.md) | parallel research → optional product | `G0` Next; production not approved | C1, C2 |
| [Operations `O`](operations/README.md) | protected telemetry admin tooling; conditional paid-cloud operations | `O1` Next; `O2` Conditional | C1, C2, local G |
| [Identity `I`](identity/README.md) | optional continuity gate | `I1` Conditional | telemetry, C1, C2, local gamification |
| [Extensions `E`](extensions/README.md) | first-party extension discovery | `E1` Conditional | core release/maturity |
| [Platform `CI`](platform/README.md) | CI/CD/E2E/release | CI 6B Complete; future measured | all product tracks |

## Dependency view

```text
Completed Stage 0–9.5
        │
        └──────────────→ C1 → C2 → C3?
                           │
                           ├─ enables stable production architecture work when needed
                           └─ does not wait for G/O/I/E

G0 → G1 → G2 → G3 → G4 → G5 → G6 → G7?/G8?
                         │
                         └─ G5 may wait for stable C2 contracts

O1 Telemetry Operations
├─ starts independently from current master contracts
├─ does not wait for Core or Gamification branches
└─ delivers automatic metrics + protected minimal admin console

I1 Identity / approved Cloud Sync product contract
└─ enables O2 Paid Cloud Sync Operations
   ├─ account/device/entitlement operations
   ├─ capacity and sync-health monitoring
   └─ backup/export/restore and deletion lifecycle

Local gamification remains independent.
Remote gamification continuity may later use I1/cloud sync and O2 operations.

E1 → E2 → E3?/E4?
E1 starts only with a concrete reference pack and stable C2 contracts.

CI 7 measurement → at most one justified CI 8/9/10 optimization.
CI 11/12 remain independently conditional.
```

## Operations direction accepted on 2026-07-20

`O1` is activated as the next stage inside the Operations track because the project owner requires automatic operational metrics and an early minimal read-only admin surface.

The accepted O1 contour is:

```text
Cloudflare Access
→ separate Admin Worker
→ fixed typed query registry
→ TELEMETRY_DB application metrics
+ Cloudflare GraphQL provider metrics
→ bounded ADMIN_DB snapshots and freshness state
→ Overview / Usage / Reliability / Privacy
```

Future optional cloud synchronization is not part of O1. Its operational support is placed in conditional `O2` and depends on a separately approved Identity/Cloud Sync product stage.

Accepted future boundaries:

- free local-first functionality remains usable without account or subscription;
- optional paid cloud sync may provide account continuity, multi-device sync, remote restore and profile media;
- telemetry installation identity, account identity and sync-device identity remain separate;
- manual Boosty entitlement uses a short-lived one-time claim code and protected admin verification;
- unofficial Boosty API automation is not a production dependency;
- the preferred initial cloud-service candidate is Supabase Auth/PostgreSQL/Storage in an EU region, but identifiers and sync contracts remain provider-neutral;
- low-cost Early Access may use provider Free capacity only with measured admission limits, encrypted external backups, a second physically separate copy and recurring restore drills;
- account/cloud implementation remains outside the telemetry Worker and outside the Operations implementation scope itself.

See [Operations `O`](operations/README.md) for phases, contracts, activation criteria and completion criteria.

## Completed product history

Historical Stage 0–9.5 files remain under [roadmap/product/](product/README.md). They are not mass-renamed because their accepted sequence and links remain useful.

## Old → new future mapping

| Previous placement | New placement |
| --- | --- |
| Stage 10 Cards v2 | `C1` Core track |
| Stage 10.5 Core 1.0 Hardening | `C2` Core track |
| Stage 11 Contextual Analytics | `C3` conditional contextual additions |
| Stage 12 Extension Foundation | `E1` discovery → `E2` minimal foundation |
| Stage 13 Analytics Pack | `E3` conditional |
| Unscheduled Telemetry Admin Dashboard | `O1` next operational stage |
| Unscheduled Identity continuity | `I1` conditional gate |
| Future paid cloud-service operations | `O2` conditional on approved Identity/Cloud Sync |
| Gamification branch without main-roadmap placement | `G0–G8` parallel track |

Previous future-stage paths are retained as compatibility pointers.

## Status vocabulary

- **Complete** — accepted implementation/evidence exists.
- **Next** — recommended next stage inside its track.
- **Planned** — sequenced after explicit dependencies.
- **Conditional** — activates only when named evidence/trigger exists.
- **Blocked** — dependency or research gap prevents start.
- **Deferred** — intentionally outside current planning horizon.
- **Research-only** — not production-ready and not included in package/CI.

## Folder boundaries

```text
docs/       current architecture/API/UX/security/operations contracts
roadmap/    tracks, stages, dependencies and activation criteria
reports/    historical handoff, audits, measurements and closeout evidence
```

- [Documentation index](../docs/README.md)
- [Historical reports](../reports/README.md)
- [Decision log](../docs/decision-log.md)
- [AI handoff](../docs/ai-handoff.md)

## Rules for roadmap changes

1. Production code/tests outrank roadmap claims.
2. Every stage states goal, status, dependencies, scope, out of scope, activation and completion criteria.
3. Parallel work does not become a core blocker without a documented dependency.
4. No placeholder route, setting, account, pack or gamification UI before its implementation stage.
5. Payload/public behavior changes remain synchronized across backend, frontend types, tests and docs.
6. Research candidates are not production economies.
7. Historical evidence remains in `reports/`; generated/runtime artifacts never enter git.
8. Verification follows `docs/test-matrix.md` and `docs/verification-run-policy.md`; docs-only work does not justify Docker E2E.
