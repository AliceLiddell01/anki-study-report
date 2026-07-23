# Roadmap Platform / CI

Platform-трек развивает GitHub Actions, packaging, release delivery и real-Anki E2E. Он независим: не перенумеровывает продуктовую работу и не блокирует Core, Gamification, Operations, Identity или Extensions, пока конкретный этап явно не вводит delivery dependency.

## Состояние

| Этап | Статус | Результат / цель |
| --- | --- | --- |
| [CI 1](ci-01-gated-delivery-baseline.md) | Завершён | базовый gated delivery contour |
| [CI 2](ci-02-exact-fast-package.md) | Завершён | producer exact Fast CI package |
| [CI 3](ci-03-exact-package-e2e-handoff.md) | Завершён | handoff exact package в E2E |
| [CI 4](ci-04-package-reuse-measurement.md) | Завершён | измерение повторного использования package |
| [CI 5](ci-05-ghcr-environment-image.md) | Завершён | стабильный GHCR environment producer |
| [CI 5A/5B](ci-05a-05b-fast-ci-observability.md) | Завершён | timing и устранение duplicate typecheck |
| [CI 6A/6B](ci-06-ghcr-consumer-cutover.md) | **Завершён** | cloud consumer только immutable GHCR digest |
| Real-deck E2E foundation | **Завершён в PR #133** | три committed рабочие колоды, zero synthetic content, package/harness reuse |
| [E2E observability и build identity](e2e-observability-build-identity.md) | **В работе; E2E-I1 и E2E-I2 завершены** | live phase protocol и browser item progress подтверждены; следующий этап — E2E-I3 |
| [CI 7](ci-07-post-cutover-optimization.md) | Условный | rolling baseline и один измеренный bottleneck |
| [CI 8](ci-08-fast-ci-critical-path.md) | Условный | оптимизация critical path Fast CI |
| [CI 9](ci-09-real-anki-e2e-efficiency.md) | Условный | эффективность real-Anki E2E |
| [CI 10](ci-10-reliability-and-flake-governance.md) | Условный | governance failures/flakes |
| [CI 11](ci-11-release-reproducibility.md) | Условный | reproducible release evidence |
| [CI 12](ci-12-scale-and-delivery-operations.md) | Отложен / условный | contributor/runner scale только при реальной необходимости |

## Текущие инварианты

```text
cloud E2E environment: immutable GHCR digest only
manual package source: exact successful Fast CI artifact
release package source: exact release artifact
collection source: three committed real APKG
package tested commit: independent identity
E2E harness/workflow commit: independent identity
harness-only reuse: ancestry + complete-diff fail-closed allowlist
local Docker build: development/diagnostic fallback
cloud BuildKit/GHA cache: removed
live run evidence: schema-v1 run-events.jsonl for Fast CI and Docker E2E
browser evidence: deterministic plan schema v1 + browser report schema v2
browser screenshot contract: 10 route + 6 native preview + 2 Cards state = 18
```

Новый Fast CI package создаётся только при package-impacting diff либо когда подходящий artifact недоступен, истёк или невалиден. Allowlisted E2E harness changes используют existing successful package без повторной сборки add-on. Complete-diff validator работает fail closed.

Актуальные контракты:

- [`../../docs/e2e-package-harness-reuse.md`](../../docs/e2e-package-harness-reuse.md);
- [`../../docs/run-event-protocol.md`](../../docs/run-event-protocol.md);
- [`../../docs/docker-e2e.md`](../../docs/docker-e2e.md).

Исторические closeout reports:

- [`../../reports/ci/real-deck-e2e-foundation-closeout.md`](../../reports/ci/real-deck-e2e-foundation-closeout.md);
- [`../../reports/ci/e2e-i1-unified-live-run-protocol-closeout.md`](../../reports/ci/e2e-i1-unified-live-run-protocol-closeout.md);
- [`../../reports/ci/e2e-i2-browser-smoke-progress-closeout.md`](../../reports/ci/e2e-i2-browser-smoke-progress-closeout.md).

## Текущий delivery contour

Контур [`e2e-observability-build-identity.md`](e2e-observability-build-identity.md) состоит ровно из шести крупных этапов:

```text
E2E-I1 — COMPLETE
E2E-I2 — COMPLETE
E2E-I3 — следующий, не начат
E2E-I4 — запланирован
E2E-I5 — запланирован
E2E-I6 — запланирован
```

Implementation tasks и commits внутри этапа не создают новые уровни roadmap.

### Подтверждение E2E-I1

```text
implementation SHA: a376a1e5556b26043d29fadcf01698972bd1b2ba
Fast CI:             30039103625 — PASS
standard/full:       30039372012 — PASS
final standard/full: 30039708429 — PASS
PR #134:             merged в core
core merge SHA:      38483b3c6ff59f7bc71b03806e9dcdaadb255fa3
```

### Подтверждение E2E-I2

```text
implementation SHA: e25bd0b24e32ce4717ed2dbda138d802f707f6d5
Fast CI:             30048028664 — PASS
standard/cards:      30049216529 — PASS
browser plan:        23/23 items PASS
screenshots:         18/18
browser diagnostics: 0 page, request, external и console errors
PR в core:           открывается после documentation closeout
merge в core:        не выполнен
```

## Активация оптимизационных этапов

`CI 7` — measurement gate, а не автоматическое разрешение менять caches, runners, retries, splitting или coverage.

```text
CI 7 measurement
├─ Fast CI bottleneck       → рассмотреть CI 8
├─ real-Anki/E2E bottleneck → рассмотреть CI 9
├─ повторяющиеся flakes     → рассмотреть CI 10
└─ material problem нет     → отложить
```

Выбирается не более одного optimization candidate с baseline, expected benefit, cost, risk и stop condition. `CI 11` может активироваться независимо после стабилизации release contracts. `CI 12` требует реального contributor/volume pressure и security model.

Package/harness reuse уже является принятым delivery invariant и сам по себе не активирует CI 7–10. Future optimization должна измерять оставшийся bottleneck, а не возвращать бессмысленную пересборку неизменённого package.

E2E observability roadmap улучшает evidence quality и execution UX. Он не разрешает автоматически cache/runner/retry/split/coverage/release изменения из CI 7–12.

## Общие правила

- сначала использовать ordinary run history, затем controlled runs;
- разделять scopes, direct savings и observational deltas;
- отслеживать p50/p95, first-run pass rate, minutes и artifact footprint;
- не повторять successful package-producing Fast CI для тех же package bytes;
- не повторять successful unchanged package/harness pair;
- проверять harness-only reuse fail closed;
- новый cache/runner/retry/split обязан окупать setup и maintenance cost;
- не жертвовать Anki Desktop, exact identity, sanitizer/token/media/action/APKG или release gates;
- docs-only commits после successful gates не требуют нового Fast CI/Docker без отдельной причины;
- завершение одного E2E-I этапа не означает автоматический старт следующего;
- browser item timings являются evidence, а не blocking performance gate;
- controlled failure доказывается focused test, если намеренно сломанный cloud run не нужен.

Этот трек остаётся независимым от [Core](../core/README.md), [Gamification](../gamification/README.md), [Operations](../operations/README.md), [Identity](../identity/README.md) и [Extensions](../extensions/README.md).