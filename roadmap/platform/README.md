# Roadmap Platform / CI

Platform-трек развивает delivery, packaging и real-Anki E2E независимо от продуктовых stages.

## Карта delivery contour

```mermaid
flowchart LR
    C1[CI 1–6B<br/>exact delivery + GHCR] --> F[Real-deck E2E foundation]
    F --> I1[E2E-I1<br/>run events]
    I1 --> I2[E2E-I2<br/>browser progress]
    I2 --> I3[E2E-I3<br/>failure diagnostics]
    I3 --> I4[E2E-I4<br/>preflight + cancellation]
    I4 --> I5[E2E-I5<br/>build identity]
    I5 --> I6[E2E-I6<br/>final summary + history]

    M[CI 7 measurement gate] -. measured bottleneck .-> C8[CI 8 Fast CI]
    M -. measured bottleneck .-> C9[CI 9 real-Anki efficiency]
    M -. repeated flakes .-> C10[CI 10 reliability]
    C11[CI 11 release reproducibility]:::conditional
    C12[CI 12 scale/operations]:::conditional

    classDef conditional stroke-dasharray: 5 5;
```

## Текущее состояние

```text
CI 1–6B — COMPLETE
real-deck E2E foundation — COMPLETE / merged
E2E-I1 — COMPLETE / merged
E2E-I2 — COMPLETE / merged
E2E-I3 — COMPLETE / merged
E2E-I4 — COMPLETE / merged через PR #137
E2E-I5 — COMPLETE / cloud acceptance через PR #141
E2E-I6 — следующий planned stage
CI 7–12 — conditional
```

## Current invariants

```text
cloud environment: immutable GHCR digest
manual package: exact successful Fast CI artifact
release package: exact release artifact
collection source: three committed real APKG
package identity and harness identity: separate
harness reuse: ancestry + complete-diff fail closed
run events: current schema v2; historical v1 validated
failure summary: schema v1, failure-only
cancellation summary: schema v1 + run/cancel
preflight: deterministic 20-check static/runtime report
non-release build identity: schema v1, digest over canonical identity only
browser: plan v1, report v3, 23 items, 18 screenshots
```

Новый Fast CI package создаётся только при package-impacting diff либо когда exact artifact недоступен/невалиден. Allowlisted harness-only changes могут использовать existing package через fail-closed validator.

## Текущий roadmap E2E-I1–I6

- [Полный roadmap observability/build identity](e2e-observability-build-identity.md)
- [Run-event contract](../../docs/run-event-protocol.md)
- [Failure diagnostics](../../docs/failure-diagnostics.md)
- [Preflight и cancellation](../../docs/e2e-preflight-cancellation.md)
- [Package/harness reuse](../../docs/e2e-package-harness-reuse.md)
- [Non-release build identity](../../docs/non-release-build-identity.md)

Исторические SHA, run IDs и artifacts: [reports/ci](../../reports/README.md).

## Условные optimization tracks

CI 7 — measurement gate, а не автоматическое разрешение менять caches, runners, retries, splitting или coverage.

```mermaid
flowchart TD
    B[Ordinary run history] --> M[CI 7 bounded measurement]
    M --> Q{Есть material bottleneck?}
    Q -->|Fast CI| C8[Рассмотреть CI 8]
    Q -->|real-Anki E2E| C9[Рассмотреть CI 9]
    Q -->|repeated flakes| C10[Рассмотреть CI 10]
    Q -->|нет| D[Отложить optimization]
```

Не более одного optimization candidate активируется одновременно. Он обязан иметь baseline, expected benefit, cost, risk и stop condition.

## Общие правила

- сначала ordinary run history, затем controlled runs;
- не повторять successful unchanged package/harness pair;
- Docker E2E — integration gate, не debugger;
- retries не заменяют root-cause fix;
- performance thresholds требуют отдельного measurement decision;
- docs-only commits после successful gates не требуют нового Fast CI/Docker;
- завершение E2E-I stage не запускает следующий автоматически;
- Platform не меняет product scope без documented dependency.
