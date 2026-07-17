# Platform / CI roadmap

Платформенная линия развивает GitHub Actions, packaging и real-Anki E2E. Она не добавляет пользовательские функции и не должна перенумеровывать product stages.

## Состояние

| Этап | Статус | Результат |
| --- | --- | --- |
| CI 1 | Complete | Gated delivery baseline и устранение duplicate release work |
| CI 2 | Complete | Exact Fast CI package producer |
| CI 3 | Complete | Fast CI → Docker E2E exact-package handoff |
| CI 4 | Complete | Package reuse measurement |
| CI 5 | Complete | Stable GHCR environment producer foundation и initial publication |
| CI 5A/5B | Complete | Structured timing и duplicate typecheck removal |
| CI 6A | Complete | Digest-pinned GHCR consumer и matched BuildKit/GHCR validation |
| CI 6B | **Complete** | Permanent GHCR-only cloud E2E cutover; local Docker build fallback сохранён |
| CI 7 | Conditional | Post-cutover runtime/flake/Fast CI optimization только по новым измерениям |

## Инварианты

- Environment image ≠ checkout ≠ tested `.ankiaddon` ≠ artifacts.
- Add-on package всегда подаётся отдельно и проверяется exact SHA.
- Cloud real-Anki E2E использует только immutable GHCR digest.
- Cloud BuildKit/Buildx/containerd build-load path и `type=gha` cache удалены.
- Local Dockerfile/Compose build path остаётся development/diagnostic fallback.
- Release остаётся manual/approval-gated и использует exact release artifact.
- Успешные same-SHA scopes не повторяются без изменения релевантного contract.
- Локальный Docker запускается только по прямому разрешению или для доказанного локального воспроизведения.
