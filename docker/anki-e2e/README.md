# Docker real-Anki E2E

**Снимок документации:** 2026-07-23.

Этот контур запускает exact add-on package в реальном Anki Desktop 26.05 внутри Docker, поднимает loopback token-protected dashboard и проверяет API, browser behavior, native rendering, media, notifications, telemetry, restart и публично безопасные artifacts.

Полный Docker E2E — integration gate. Политика: [`../../docs/verification-run-policy.md`](../../docs/verification-run-policy.md).

Package/harness reuse: [`../../docs/e2e-package-harness-reuse.md`](../../docs/e2e-package-harness-reuse.md).

## Collection source

Disposable collection содержит только данные из:

```text
fixtures/real-decks/words-n1.apkg
fixtures/real-decks/grammar-n5.apkg
fixtures/real-decks/java-core.apkg
```

Manifest:

```text
fixtures/real-decks/manifest.json
```

Запрещены:

- synthetic notes/cards/note types/templates/media;
- `asr-e2e-render-fixtures.apkg` как runtime source;
- external/local-only APKG override;
- fallback collection;
- legacy importer/backend fallback;
- cloning notes/cards;
- concrete fixture identifiers вне manifest.

## Pipeline

1. Использовать current E2E harness checkout.
2. Для local `source-build` собрать frontend/package; для cloud установить exact prebuilt package.
3. Создать fresh disposable profile и empty collection.
4. Валидировать manifest, sizes и SHA-256.
5. Импортировать три packages через `Collection.import_anki_package(ImportAnkiPackageRequest)`.
6. Построить inventory и доказать zero synthetic content.
7. Разрешить anchors по GUID/template ordinal.
8. Проверить fingerprints, fields, media capabilities и HTML classes.
9. Применить только scheduling/revlog/due/interval/ease/suspended/buried scenarios.
10. Установить add-on.
11. Для `full/notifications` seed notification state из real-deck anchors.
12. Запустить Anki и дождаться readiness.
13. Выполнить API и browser smoke.
14. Подготовить offline telemetry queue.
15. При необходимости выполнить restart и persistence proof.
16. Проверить package SHA после E2E.
17. Создать redacted public artifact.
18. Cleanup и restore canonical exit code.

Thin adapters:

```text
seed-collection.py                  empty collection only
import-apkg-fixture.py              mandatory manifest-driven import
mark-apkg-cards-problematic.py      generic study-state scenarios only
```

## Live logging

Длительные real-deck стадии используют prefix:

```text
[real-decks]
```

Ожидаются сообщения о manifest/checksum/import/inventory/anchors/scenarios/browser result.

При ошибке `real-deck-failure.json` содержит stage, subject ID, error type/message, last completed step и traceback. Fallback не выполняется.

## Package sources

### Local `source-build`

```powershell
./scripts/run_anki_e2e_docker.ps1
./scripts/run_full_check.ps1 -DockerOnly
```

Контейнер использует prepared dependency store, собирает dashboard и package.

### Cloud `fast-ci-artifact`

Manual/reusable workflow получает `fast_ci_run_id` и exact package.

Package commit и current harness commit могут различаться. Reuse допускается только после ancestry + complete changed-path allowlist validation.

Изменение только allowlisted E2E harness не требует нового Fast CI.

### `release-artifact`

Release caller передаёт exact current release archive и SHA-256. Это отдельный production proof.

## Local commands

```powershell
./scripts/run_anki_e2e_docker.ps1
./scripts/run_full_check.ps1 -DockerOnly
./scripts/run_full_check.ps1 -DockerOnly -CleanDocker
./scripts/run_anki_e2e_docker.ps1 -BuildOnly
./scripts/run_anki_e2e_docker.ps1 -NoBuild
./scripts/run_full_check.ps1 -DockerOnly -Perf100
```

WSL:

```bash
pwsh -NoProfile -File ./scripts/run_anki_e2e_docker.ps1
```

## Cloud command

```bash
gh workflow run ci-e2e.yml \
  --repo AliceLiddell01/anki-study-report \
  --ref <branch> \
  -f mode=standard \
  -f scope=<scope> \
  -f screenshot_workers=auto \
  -f resource_telemetry=true \
  -f verify_restart=<auto|true|false> \
  -f fast_ci_run_id=<successful-package-producing-run>
```

## Modes

```text
standard
perf100
```

`perf100` выбирает 100 distinct imported cards и не клонирует content.

Legacy `strict-apkg` input нормализуется в `standard`.

## Scopes

```text
full
global
stats
decks
activity
cards
settings
notifications
```

Scope не отключает imports/checksums/inventory/anchors/scenarios.

`full` автоматически требует restart.

## Required reports

```text
reports/real-deck-manifest-report.json
reports/real-deck-import-report.json
reports/collection-inventory.json
reports/anchor-resolution-report.json
reports/scenario-application-report.json
reports/api-smoke-first.json
reports/browser-smoke-first.json
reports/e2e-phase-timings.json
reports/e2e-performance-summary.json
```

При restart дополнительно создаются restart API/telemetry reports.

## Inventory and scenario invariants

```text
contentSource = committed-real-apkg-only
syntheticNotes = 0
syntheticCards = 0
syntheticMedia = 0
notesCreated = 0
cardsCreated = 0
notesOrCardsCloned = 0
```

## Browser evidence

```text
screenshots/pages/<route>/<light|dark>.png
screenshots/cards/real-decks/<preview>/<light|dark>.png
screenshots/states/cards/real-deck-inbox/<light|dark>.png
```

Проверяются native front/back, real media, Java class contour, Cards states, no page/console/request errors и no unexpected external network.

## Notifications

`seed-notification-lifecycle.py` использует PASS reports:

```text
anchor-resolution-report.json
scenario-application-report.json
```

Card anchors:

```text
cards-action-recheck
cards-low-success
```

Public proof schema v2 не содержит raw entity IDs.

## Telemetry

Browser harness проверяет consent/purpose batches, затем создаёт offline persistent queue. Restart verifier проверяет восстановление, delivery, deletion и credential destruction.

## Package/harness reuse reports

```text
ci-e2e-raw/e2e-harness-reuse.json
artifacts/reports/e2e-harness-reuse.json
```

Evidence содержит package commit, harness/workflow commit, reuse mode, count/hash/list changed paths.

## Security

- loopback-only dashboard;
- token не логируется;
- raw readiness не публикуется;
- read-only workspace/package mounts;
- media traversal/absolute path rejection;
- no iframe/JS card execution;
- private absolute path redaction;
- safe relative path preservation;
- secret/private-key rejection;
- runtime outputs не коммитятся.

## Failure contract

Hard failure при package/import/anchor/fingerprint/content mutation, package reuse boundary, package hash, API/browser/restart/notification/telemetry, artifact manifest или sanitizer error.

Public artifact загружается даже после failure, когда это безопасно, но canonical result восстанавливается после upload/cleanup.

## Updating working decks

1. Заменить только нужный `.apkg`.
2. Проверить provenance/authorization.
3. Пересчитать size/SHA-256.
4. Получить inventory.
5. Проверить anchors/fingerprints/media.
6. Обновить manifest.
7. Выполнить focused tests.
8. Выполнить policy-compliant real-Anki proof.

Не менять generic harness ради конкретного слова/media filename. Identifiers хранятся в manifest.

## Verified closeout

```text
Fast CI package run: 30013925137
Targeted cards: 30020601292 — PASS
Final full: 30022393738 — PASS
```

Отчёт: [`../../reports/ci/real-deck-e2e-foundation-closeout.md`](../../reports/ci/real-deck-e2e-foundation-closeout.md).
