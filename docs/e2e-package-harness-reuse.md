# Повторное использование Fast CI package при изменениях E2E harness

**Статус:** обязательный актуальный контракт, 2026-07-23.

Этот документ определяет, когда Docker real-Anki E2E обязан получить новый `.ankiaddon` из Fast CI, а когда разрешено повторно использовать уже проверенный package artifact с более новым E2E harness.

Исторический отчёт реализации: [`../reports/ci/real-deck-e2e-foundation-closeout.md`](../reports/ci/real-deck-e2e-foundation-closeout.md).

## Зачем разделены две идентичности

`.ankiaddon` и E2E harness имеют разный жизненный цикл:

```text
package tested commit
— commit, на котором Fast CI собрал и проверил package bytes

E2E harness commit
— текущий commit, из которого запускаются Docker orchestration, smoke и exporter
```

Изменение browser smoke, artifact sanitizer или Docker orchestration не меняет уже собранный add-on. Повторная сборка того же `.ankiaddon` в таком случае не добавляет доказательств, но расходует время и CI quota.

Одновременно нельзя просто запустить произвольный новый код с любым старым package: reuse разрешается только после fail-closed проверки ancestry и полного diff.

## Режимы

### `exact-tree`

```text
package tested commit == E2E harness commit
changed paths = empty
```

Это обычный режим, когда Fast CI и E2E используют одно дерево.

### `harness-only`

```text
package tested commit != E2E harness commit
package commit является предком harness commit
каждый changed path разрешён E2E allowlist
```

Package bytes, metadata, size и SHA-256 остаются привязаны к исходному successful Fast CI run. Текущий checkout используется только как E2E harness.

## Когда нужен новый Fast CI package

Новый Fast CI обязателен, если diff может изменить `.ankiaddon` или его production-поведение, в том числе:

- `anki_study_report/`;
- `web-dashboard/` и generated package assets;
- `scripts/package_addon.py`, package metadata или build scripts;
- Python/frontend dependencies и lockfiles;
- add-on manifest/config/changelog, если они входят в package;
- Fast CI package producer;
- release packaging;
- любой файл вне разрешённого harness-only allowlist;
- rebase/conflict resolution, затронувший package-impacting paths.

В этом случае последовательность:

```text
focused/local checks
→ Fast CI на package-impacting head
→ exact package artifact
→ targeted E2E по риску
→ standard/full только по matrix/policy
```

## Когда новый Fast CI не нужен

Reuse может быть разрешён для изменений, ограниченных:

- `docker/anki-e2e/`;
- `.github/workflows/ci-e2e.yml`;
- E2E artifact preparation/sanitizer;
- Fast CI handoff consumer и reuse validator;
- focused tests этих E2E contracts;
- документацией, если runtime/package tree не меняется.

Фактическим источником истины является `scripts/validate_e2e_harness_reuse.py`, а не этот общий список. Любой неразрешённый path блокирует reuse.

Изменение только документации после уже успешных package и E2E gates не требует повторного Fast CI или Docker E2E, если branch protection или отдельная задача не требует иного. Достаточны `git diff --check` и проверка ссылок/путей/code fences.

## Алгоритм cloud consumer

Для `fast-ci-artifact` workflow выполняет:

1. Checkout текущего workflow/harness commit.
2. Получение явно указанного `fast_ci_run_id`.
3. Проверку same-repository successful Fast CI run и artifact IDs.
4. Проверку diagnostics и package metadata.
5. Получение package tested commit из Fast CI evidence.
6. Проверку ancestry `package commit → harness commit`.
7. Получение полного списка changed paths.
8. Fail-closed validation allowlist.
9. Проверку package size, SHA-256 и transport identity.
10. Staging exact `.ankiaddon` в `docker/anki-e2e/local-input/` только как package handoff.
11. Запуск текущего E2E harness с read-only package mount.
12. Повторную проверку package SHA после real-Anki execution.
13. Публикацию обеих SHA и reuse evidence.

Fallback на source build запрещён.

Некоторые step names workflow сохраняют историческое имя `Check out exact Fast CI tested commit`. Фактический checkout identity после handoff определяется validated output и для `harness-only` остаётся текущим E2E harness SHA. Package tested SHA хранится отдельно в evidence.

## Fail-closed boundary

`validate_e2e_harness_reuse.py` проверяет:

- точный lowercase 40-character SHA;
- совпадение workflow source SHA и harness SHA;
- ancestry package commit;
- отсутствие absolute/traversal/unsafe changed paths;
- непустой diff для `harness-only`;
- пустой diff для `exact-tree`;
- разрешённость каждого changed path;
- детерминированный hash списка paths.

При любой ошибке workflow завершается до запуска Anki.

## Evidence contract

Raw и public evidence должны сохранять:

```text
packageTestedCommitSha
sourceFastCiRunId
sourcePackageSha256
e2eHarnessCommitSha / e2eCheckoutSha
workflowSourceSha
reuseMode
changedFileCount
changedPathsSha256
changedPaths
```

Основной report:

```text
artifacts/reports/e2e-harness-reuse.json
```

Summary writer обязан независимо пересчитать boundary и сравнить его с raw handoff report. Разные SHA допустимы только при `reuseMode=harness-only` и полном совпадении evidence.

## Package identity остаётся неизменной

Reuse не означает пересборку или модификацию package. Проверяются:

- artifact ID и run ID;
- `testedCommitSha`;
- `sourceHeadSha`;
- `packageSha256`;
- `packageSizeBytes`;
- transport digest;
- package hash после E2E.

`local-input` не является collection fixture. В нём находится только exact `.ankiaddon`.

## Release boundary

Release не использует старый Fast CI package по harness-only правилу.

Release caller передаёт exact current release artifact и SHA-256. Финальный release `standard/full` доказывает именно публикуемые bytes. Package/harness reuse относится к manual/development cloud E2E с `fast-ci-artifact`.

## Команды

Новый package-impacting head:

```bash
gh workflow run ci-fast.yml \
  --repo AliceLiddell01/anki-study-report \
  --ref <branch>
```

Targeted E2E с уже проверенным package:

```bash
gh workflow run ci-e2e.yml \
  --repo AliceLiddell01/anki-study-report \
  --ref <branch> \
  -f mode=standard \
  -f scope=cards \
  -f screenshot_workers=auto \
  -f resource_telemetry=true \
  -f verify_restart=true \
  -f fast_ci_run_id=<successful-package-producing-run>
```

Final full gate запускается только когда его требует [`test-matrix.md`](test-matrix.md) или [`verification-run-policy.md`](verification-run-policy.md).

## Stop-loss

- Не запускать новый Fast CI только потому, что изменился разрешённый E2E harness.
- Не повторять успешный package-producing Fast CI для тех же package bytes.
- Не повторять успешный targeted/full gate для неизменной пары package/harness.
- После failure сначала изучить artifact и root cause.
- Новый run разрешён после конкретного исправления либо подтверждённой infrastructure failure.
- Второе одинаковое падение прекращает слепые reruns.

## Security

Разделение identity не ослабляет:

- token validation;
- loopback-only server;
- package SHA verification;
- GHCR digest lock;
- sanitizer/private-path checks;
- read-only workspace/package mounts;
- запрет fallback build;
- запрет коммита runtime artifacts;
- action/media/preview security contracts.

## Подтверждённая реализация

Финальный доказанный пример:

```text
Fast CI package run: 30013925137
package commit: bd0355c315197cfb659cb28b32b63a4931b73458
package SHA-256: 3ae8439ba18cac82b7e8bb6b240223970cb6403130abf1f909168273ff39baf8

final E2E run: 30022393738
harness commit: 1a84eabaacb5c368f92ae4952e732d8610619f95
reuse mode: harness-only
result: PASS
```

Новый Fast CI после harness-only исправлений не выполнялся; package bytes остались неизменными и были повторно проверены до и после real-Anki E2E.
