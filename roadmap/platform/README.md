# Platform / CI roadmap

Платформенная линия развивает GitHub Actions, packaging, release delivery и
real-Anki E2E. Она не добавляет пользовательские функции и не перенумеровывает
product stages.

## Состояние

| Этап | Статус | Результат / цель |
| --- | --- | --- |
| [CI 1](ci-01-gated-delivery-baseline.md) | Complete | Gated delivery baseline и устранение duplicate release work |
| [CI 2](ci-02-exact-fast-package.md) | Complete | Exact Fast CI package producer |
| [CI 3](ci-03-exact-package-e2e-handoff.md) | Complete | Fast CI → Docker E2E exact-package handoff |
| [CI 4](ci-04-package-reuse-measurement.md) | Complete | Package reuse measurement |
| [CI 5](ci-05-ghcr-environment-image.md) | Complete | Stable GHCR environment producer и initial publication |
| [CI 5A/5B](ci-05a-05b-fast-ci-observability.md) | Complete | Structured timing и duplicate typecheck removal |
| [CI 6A/6B](ci-06-ghcr-consumer-cutover.md) | **Complete** | Digest-pinned validation и permanent GHCR-only cloud cutover |
| [CI 7](ci-07-post-cutover-optimization.md) | Conditional | Rolling baseline, performance/reliability budget и выбор одного bottleneck |
| [CI 8](ci-08-fast-ci-critical-path.md) | Conditional | Fast CI critical-path optimization без потери canonical coverage |
| [CI 9](ci-09-real-anki-e2e-efficiency.md) | Conditional | GHCR/Anki/browser/artifact efficiency при неизменном evidence contract |
| [CI 10](ci-10-reliability-and-flake-governance.md) | Conditional | Failure taxonomy, deterministic tests и bounded retry governance |
| [CI 11](ci-11-release-reproducibility.md) | Conditional | Reproducible `.ankiaddon`, dependency integrity и release evidence hardening |
| [CI 12](ci-12-scale-and-delivery-operations.md) | Unscheduled | Branch/runner/operations scaling только при росте contributors и CI volume |

## Как активируются будущие этапы

CI 7 является measurement gate. Он не обязан автоматически вести в CI 8, 9 и
10. После baseline выбирается только один candidate с доказанным expected saving
или reliability benefit.

```text
CI 7 measurement
├─ Fast CI bottleneck       → CI 8
├─ real-Anki/E2E bottleneck → CI 9
├─ repeated flake/failures  → CI 10
└─ no material problem      → defer
```

CI 11 может быть активирован отдельно после стабилизации release contracts. CI 12
остаётся ненумерованной по времени дальней перспективой, пока solo/small-project
режим не создаёт реальной operational нагрузки.

## Общие decision rules

- Использовать историю обычных runs; не создавать тяжёлые runs только ради
  красивой выборки.
- Не смешивать targeted и `full`, разные scopes, Anki versions или изменившийся
  screenshot/restart contract.
- Отделять direct removed work от observational workflow delta.
- Перед изменением фиксировать baseline, expected saving, risk и stop condition.
- После изменения проверять p50/p95, first-run pass rate и Actions minutes, а не
  только один лучший run.
- Успешный same-SHA gate не повторять без relevant contract change.
- Любой новый cache, runner, retry или split job должен доказать пользу выше своей
  setup, storage и maintenance стоимости.

## Инварианты

- Environment image ≠ checkout ≠ tested `.ankiaddon` ≠ artifacts.
- Add-on package всегда подаётся отдельно и проверяется exact SHA.
- Cloud real-Anki E2E использует только immutable GHCR digest.
- Cloud BuildKit/Buildx/containerd build-load path и `type=gha` cache удалены.
- Local Dockerfile/Compose build path остаётся development/diagnostic fallback.
- Release остаётся manual/approval-gated и использует exact release artifact.
- Один canonical Fast CI сохраняет Python/frontend/package coverage.
- Второй canonical TypeScript typecheck не возвращается.
- Retry не маскирует project/test/security/package failure.
- Local machine не становится automatic CI runner.
- Self-hosted/larger runners, merge queue и scheduled heavy E2E не вводятся без
  подтверждённого масштаба, budget и security model.

## Общий out of scope долгосрочной линии

- ускорение за счёт удаления реального Anki Desktop;
- автоматическая публикация после merge или tag;
- mutable package/image identity;
- возврат cloud source-build fallback;
- снижение sanitizer, token, media, action, APKG или release checks;
- отдельная сложная CI platform для текущего небольшого проекта.
