# Матрица проверок

**Снимок документации:** 2026-07-24.

Минимальная проверка — нижняя граница для небольшого изменения. Желательная проверка нужна перед merge/release либо когда diff затрагивает несколько слоёв.

Полный real-Anki E2E — integration gate, а не обычный цикл разработки.

Перед выбором gate сначала определите тип изменения:

```text
package-impacting
harness-only
docs-only
```

Связанные контракты:

- package reuse: [`e2e-package-harness-reuse.md`](e2e-package-harness-reuse.md);
- run events и browser items: [`run-event-protocol.md`](run-event-protocol.md).

## Общая матрица

| Изменение | Минимальная проверка | Желательная проверка | Docker / Fast CI |
| --- | --- | --- | --- |
| только документация | `git diff --check`, links/paths/code fences | ручной просмотр индексов и терминологии | без Fast CI/Docker после уже успешных gates, если нет отдельного требования |
| чистая логика Python | профильный pytest | `compileall` затронутых модулей | обычно без Docker |
| hooks/startup/profile lifecycle | целевой pytest | live Anki или real-Anki E2E | новый Fast CI только при package impact |
| dashboard payload/public schema | backend contract tests | frontend parser/types/build и docs | package-impacting; Fast CI обязателен |
| чистый frontend UI/types | профильный Vitest/typecheck | `pnpm run build:addon` | Fast CI перед package E2E; Docker только по runtime risk |
| card render/media/preview | frontend preview tests + sanitizer pytest | `standard/cards` на committed real decks | package-impacting изменения требуют Fast CI |
| Search/Safe Actions | Search/runtime/action/frontend tests | `standard/global`; full при общем diff | по package impact |
| Triage/Cards/Inspection Profiles | backend/API/frontend/profile tests | `standard/cards`, restart | по package impact |
| Settings/privacy/telemetry | config/store/client/frontend tests | `standard/settings`, restart при queue/network/delete | по package impact |
| Signals/Notifications | detector/store/server/frontend tests | `standard/notifications`, restart; full при shared contour | по package impact |
| package/build scripts/dependencies | package tests/check | exact `.ankiaddon` Fast CI | новый Fast CI обязателен |
| release/publisher | release/package/publisher tests | exact release-artifact `standard/full` | release package обязателен |
| committed APKG/manifest/anchors | real-deck contract tests | targeted real-Anki proof | новый Fast CI нужен, если package tree или producer изменён; сам APKG не входит в add-on, но full risk оценивается отдельно |
| только `docker/anki-e2e/` harness | focused harness tests | один risk-required Docker proof с reused package | новый Fast CI не нужен при allowlisted diff |
| browser plan/item/report contract | Node unit tests + static pytest + screenshot/run-event tests | один `standard/cards` proof; full только при shared runner lifecycle change | reused package разрешён fail closed; package Fast CI только по complete diff |
| E2E artifact/sanitizer/handoff consumer | focused exporter/security/reuse tests | один соответствующий Docker proof | reused package разрешён fail closed |
| run-event schema/registry/writer | schema/security/concurrency/integration tests | controlled failure + один затронутый Fast CI/E2E proof | новый Fast CI только при package/producer impact |
| `.github/workflows/ci-e2e.yml` | workflow/handoff tests | одно ручное наблюдение | reused package разрешён, если полный diff проходит allowlist |
| Fast CI producer | workflow/package/run-event tests | новый exact package-producing Fast CI | обязателен |

## Решение о новом Fast CI

Новый Fast CI нужен, когда diff может изменить `.ankiaddon` bytes или production behavior.

Примеры package-impacting paths:

```text
anki_study_report/
web-dashboard/
requirements/lockfiles
package/build scripts
manifest/config/changelog packaged assets
release packaging
Fast CI producer
```

Новый Fast CI не нужен, когда весь diff между package commit и current harness commit принят `scripts/validate_e2e_harness_reuse.py`.

Allowlist — источник истины. Нельзя вручную объявить произвольный diff `harness-only`.

## Основные команды

```powershell
git diff --check
node scripts/run_python.mjs -m pytest
cd web-dashboard
pnpm run test:frontend
pnpm run typecheck
pnpm run build:addon
```

```powershell
./build_ankiaddon.ps1
./scripts/run_full_check.ps1 -SkipDocker
./scripts/run_full_check.ps1 -CleanDocker
./scripts/run_full_check.ps1 -DockerOnly
./scripts/run_full_check.ps1 -DockerOnly -Perf100
```

В WSL `.ps1` запускаются через PowerShell Core.

Проверка завершённого run-event stream:

```bash
python docker/anki-e2e/run_event_protocol.py validate \
  --output <run-events.jsonl> \
  --producer <fast-ci|docker-e2e>
```

Browser syntax/unit contract:

```bash
node --check docker/anki-e2e/browser-progress.mjs
node --check docker/anki-e2e/smoke-browser.mjs
node --test tests/browser_progress.test.mjs
```

Cloud targeted E2E с existing package:

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

## Real-deck Docker foundation

Docker всегда импортирует:

```text
docker/anki-e2e/fixtures/real-decks/words-n1.apkg
docker/anki-e2e/fixtures/real-decks/grammar-n5.apkg
docker/anki-e2e/fixtures/real-decks/java-core.apkg
```

Focused minimum для import/manifest/scenario harness:

```text
tests/test_real_deck_e2e_contract.py
related orchestration/action/inspect/notification/reuse tests
Python syntax/compile затронутых scripts
Node syntax check browser smoke
git diff --check
```

Контракт включает:

- package ID/path uniqueness;
- missing package и checksum mismatch как hard failure;
- public Anki package importer без fallback;
- unique deterministic anchors;
- media capabilities без hardcoded generic filenames;
- отсутствие insert/clone notes/cards;
- 100 distinct cards для `perf100`;
- zero-synthetic inventory;
- zero content mutations после import.

Успешный artifact обязан содержать PASS:

```text
real-deck-manifest-report.json
real-deck-import-report.json
collection-inventory.json
anchor-resolution-report.json
scenario-application-report.json
run-events.jsonl
```

## Run-event focused minimum

При изменении `run_event_protocol.py`, Fast CI timing adapter, Docker phase wiring или artifact boundary обязательны:

```text
tests/test_run_event_protocol.py
tests/test_run_event_integration.py
tests/test_run_event_controlled_failure.py
tests/test_ci_fast_run_events.py
```

В зависимости от diff также запускаются:

```text
tests/test_ci_fast_workflow.py
tests/test_ci_e2e_workflow.py
tests/test_prepare_ci_e2e_artifacts_reimport.py
tests/test_telemetry_e2e_harness.py
tests/test_telemetry_threshold_delivery.py
```

Минимальные инварианты:

- success и controlled failure stream валидны;
- unknown/unsafe values отклоняются;
- concurrent append не повреждает строки;
- timing/phase registry не расходятся;
- success manifest требует stream;
- public exporter валидирует source и copied stream;
- transient `.lock`/`.state.json` не входят в artifact inventory.

## Browser progress focused minimum

При изменении `browser-progress.mjs`, `smoke-browser.mjs`, browser report schema или screenshot accounting обязательны:

```text
tests/browser_progress.test.mjs
tests/test_browser_progress_node.py
tests/test_e2e_screenshot_contract.py
tests/test_docker_smoke_helpers.py
tests/test_telemetry_e2e_harness.py
tests/test_run_event_protocol.py
tests/test_run_event_integration.py
tests/test_run_event_controlled_failure.py
```

Если затронуты exporter/manifest/reuse boundaries, также:

```text
tests/test_prepare_ci_e2e_artifacts_reimport.py
tests/test_ci_e2e_workflow.py
tests/test_e2e_harness_reuse.py
artifact manifest/sanitizer tests
```

Минимальные browser invariants:

- plan создаётся и печатается до Chromium launch;
- stable unique item IDs и known kinds;
- deterministic order/counts;
- telemetry items только при enabled endpoint;
- 10 route screenshots;
- 3 preview items × 2 screenshots;
- 2 Cards state screenshots;
- total 18;
- START предшествует operation;
- PASS/FAIL содержат exact item и duration;
- original exception rethrown;
- unknown/duplicate item fail closed;
- producer failure hard-fails;
- partial failure report сохраняется;
- slowest sorting deterministic;
- direct `playwright` import сохранён;
- `@playwright/test`, retries и dynamic phase IDs отсутствуют;
- existing diagnostics semantics сохранены;
- final run-event stream валиден.

### Required cloud proof

Обычный harness-only browser progress diff требует одного:

```text
mode=standard
scope=cards
verify_restart=false или auto для targeted scope
resource_telemetry=true
```

`standard/full` нужен только при изменении общего runner/artifact/run-event/restart lifecycle.

После одного успешного targeted proof не запускаются второй run «для уверенности», perf100, warm repeat, worker comparison или local full.

## Scope matrix

| Scope | Основной риск |
| --- | --- |
| `global` | Search и Safe Actions |
| `stats` | Statistics/FSRS |
| `decks` | Decks |
| `activity` | Calendar/Activity |
| `cards` | Cards/Triage/native preview/media/Inspection Profiles/browser progress |
| `settings` | Settings/privacy/telemetry |
| `notifications` | Notification lifecycle |
| `full` | общий startup/server/package/artifact/restart contour |

Targeted scope не отключает real-deck import/checksum/inventory/anchors/scenarios.

## Restart

Restart обязателен для:

- `standard/full`;
- persistent Cards/Inspection Profiles state, когда это acceptance criterion;
- Notifications;
- telemetry queue/network/delete lifecycle;
- startup/profile persistence changes.

Browser plan/report/screenshot progress без изменения persistence допускает targeted `cards` с `verify_restart=false`.

## Artifact security

Изменение artifact exporter/sanitizer/run-event/browser-report boundary требует focused tests на:

- token query redaction;
- private Linux/Windows absolute paths;
- сохранение безопасных relative paths вроде `screenshots/pages/home/...`;
- duplicate/traversal/missing paths;
- secret-like text/private keys;
- control characters/multiline/NUL;
- deterministic UTF-8 JSONL без BOM/partial lines;
- source/public stream validation;
- safe item IDs/context/error summaries;
- отсутствие raw stack в progress message;
- canonical result restoration после upload/cleanup.

Один соответствующий Docker run нужен только после concrete fix. Новый Fast CI не нужен, если package не изменён и reuse boundary проходит.

## Stop-loss

- Сначала анализировать artifact/log/root cause.
- Повторять gate только после конкретного исправления.
- Не считать финальный wrapper exception автоматическим root cause.
- Не повторять successful Fast CI для тех же package bytes.
- Не повторять successful E2E для неизменной package/harness пары.
- Не запускать local full после successful cloud full.
- Не запускать `perf100`, warm repeat или worker comparison без отдельной задачи.
- Вторая одинаковая ошибка прекращает blind reruns.
- Не менять production code ради устаревшего structural test; обновлять тест на фактический контракт.

## Исторические подтверждения

Числа и run IDs завершённых этапов не являются частью текущей матрицы. Они хранятся в [`../reports/`](../reports/README.md).

Closeout reports:

- [`../reports/ci/real-deck-e2e-foundation-closeout.md`](../reports/ci/real-deck-e2e-foundation-closeout.md);
- [`../reports/ci/e2e-i1-unified-live-run-protocol-closeout.md`](../reports/ci/e2e-i1-unified-live-run-protocol-closeout.md);
- [`../reports/ci/e2e-i2-browser-smoke-progress-closeout.md`](../reports/ci/e2e-i2-browser-smoke-progress-closeout.md).