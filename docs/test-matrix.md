# Матрица проверок

**Снимок документации:** 2026-07-22

Минимальная проверка — нижняя граница для небольшого изменения. Желательная проверка нужна перед merge или release либо когда diff затрагивает несколько слоёв.

Полный real-Anki E2E — интеграционный gate, а не обычный цикл разработки.

## Общая матрица

| Изменение | Минимальная проверка | Желательная проверка | Docker или live Anki | Причина |
| --- | --- | --- | --- | --- |
| только документация | `git diff --check` | вручную проверить links, code fences и paths | нет | код и runtime не менялись |
| чистая логика Python | профильный pytest | `compileall` затронутых модулей add-on | обычно нет | чистые модули тестируются без Anki |
| hooks, startup и жизненный цикл профиля Anki | целевой pytest | smoke в live Anki или real-Anki E2E | да | `aqt`, hooks и restart не видны unit-тестам |
| payload dashboard или публичная schema | backend-тесты контракта | parser и types frontend и сборка | иногда | backend, frontend и docs должны меняться синхронно |
| UI и types frontend | профильный Vitest и typecheck | `pnpm run build:addon` | нет для чистого UI | типы, состояние и normalization |
| рендер, media и предпросмотр карточки | frontend-тесты предпросмотра и pytest sanitizer | целевой real-Anki smoke Cards | да для финальной проверки | нативный рендер, media и Shadow DOM требуют runtime |
| server dashboard, токен и действия | pytest server и действий | frontend-тесты API и локальный smoke | иногда | токен, allowlist, ошибки HTTP и QueryOp |
| Search и Safe Actions | тесты Search, runtime и entity actions и frontend | Fast CI и целевой `standard/global`; полный запуск при общем diff | да | чтения latest-wins, точные ID, отменяемые mutations и bridge Browser |
| C2 hardening и UI remediation | parser/security, exact authority, generation/cache, Search/server, visual contract tests и benchmark | Fast CI, `standard/cards` с restart и финальный `standard/full` | да | CSS/CSP, общий server, Cards, Profiles, package и E2E visual contracts |
| запрос Triage v4 | тесты candidates, service, runtime, dashboard, parser и hook | Fast CI и целевой `standard/cards` | да для финальной проверки | независимые источники, согласованность cursor и живые профили |
| решение конкретной карточки C1.6 | тесты backend, API, parser, client, hook, page и фокуса | Fast CI, целевой `standard/cards` с restart и финальный `standard/full` при общем diff runtime | да | повторное использование детекторов, fail-closed-reconciliation, фокус и E2E-передача |
| Inspection Profiles | store, service, runtime, schema, dashboard и frontend-editor | Fast CI и целевой `standard/cards` с restart | да | fingerprints, persistence, изоляция профиля и живые типы заметок |
| API Settings и Profile | тесты config, profile и dashboard и frontend | проверка пакета; real-Anki при изменении жизненного цикла | иногда | allowlists, атомарное хранение и reload |
| Statistics и FSRS | service и dashboard и frontend | Fast CI и целевой `standard/stats`; финальный полный запуск при общем diff | да для финальной проверки | нативная конфигурация, память, simulator и скриншоты |
| Signals и Notifications | detector, store, server и тесты Bell, Center и Settings | целевой `standard/notifications` с restart и один финальный полный запуск | да | App Shell, persistence и локальный API |
| client телеметрии и privacy | тесты контракта, store, client и dashboard | `standard/settings` с fake loopback и restart | да при изменениях очереди, сети или удаления | consent, ограниченная очередь, повтор и удаление |
| scripts упаковки и сборки | `package_addon.py --check` | сборка точного `.ankiaddon` | нет | запрещённые файлы, assets и metadata |
| Docker E2E и поведение runtime | целевые локальные проверки | cloud E2E с точным пакетом, когда требует риск | да | реальный Anki Desktop, импорт, restart и browser |
| артефакты E2E и редактирование чувствительных данных | тесты helpers и exporter | один соответствующий E2E-запуск | да | manifest, удаление токена и путей и публично безопасный артефакт |
| workflows CI и передача артефактов | профильные тесты workflow и handoff и статические проверки YAML | одно ручное наблюдение точного SHA после локального PASS | по риску | идентичность checkout и пакета, hashes и семантика ошибок |
| release и publisher | тесты release, package и publisher и `-SkipDocker` | точный release-артефакт и `standard/full` | да | паритет SHA сборки, E2E, GitHub и AnkiWeb |

## Команды

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
```

В WSL точки входа `.ps1` запускаются через установленный PowerShell Core согласно контракту окружения репозитория.

## Stop-loss

- после ошибки сначала анализируются артефакты, логи и первопричина;
- повтор разрешён только после конкретного исправления или для отдельно подтверждённой инфраструктурной ошибки;
- вторая одинаковая ошибка прекращает слепые перезапуски;
- успешный запуск точного SHA не повторяется;
- локальный полный Docker не дублирует успешный полный cloud-gate с точным пакетом;
- повторы с тёплым cache и performance-workers не запускаются без отдельной задачи.

## Когда не запускать Docker E2E

Не запускать Docker E2E для:

- изменений только документации;
- небольших чистых helpers;
- изменений, не затрагивающих startup, рендер, media, server, структуру пакета или поведение live collection.

## Cards C1.5R.5

Профильное завершение включает:

- Vitest hook, page, components и helpers Cards;
- pytest Triage, Search и dashboard;
- typecheck;
- production-сборку и ограничение bundle;
- проверку пакета;
- изолированное browser-подтверждение;
- канонический gate без Docker.

Матрица browser покрывает широкую компоновку light и dark, 100 элементов, очередь, панель и модальный диалог при 1024 px, частичные источники, профили needs-review, продолжение и пустое состояние.

## Triage C1.5R.4

Проверяются:

- независимые источники обучения за период и текущего содержимого;
- граница подтверждённого профиля;
- keyset-ограничение 500 заметок;
- явный согласованный cursor;
- детерминированная representative card;
- отсутствие чтения предпросмотра и media при поиске кандидатов.

## Пошаговая настройка Inspection Profiles C1.5R.6

Обязательный контур:

- тесты page, hook, Basic, Advanced, validation, projection и API;
- регрессии store, service, runtime, dashboard, Triage и package;
- typecheck и production-сборка;
- проверка пакета;
- gate без Docker;
- подтверждение Chromium для Japanese, Programming, жизненного цикла, light, dark и 1024 px.

## Канонический цикл решения одной карточки C1.6

Профильный контур:

```text
triage candidates/service/runtime/dashboard
parser/client API Triage
hook/page/detail/inbox Cards
поведение гонок и latest-wins
reconciliation причин
восстановление фокуса
E2E helpers и smoke-assertions
```

Зафиксированные финальные подтверждения:

```text
профильные backend- и E2E-вспомогательные тесты: 81 тест — PASS
frontend: 324 теста — PASS
Python compileall: PASS
production-сборка и ограничение bundle: PASS — entry 429 516 байт
пакет: PASS — 77 записей
каноническая проверка без Docker: PASS — 324 frontend-теста, 802 Python-теста, 5 пропусков платформенных тестов
Fast CI 29862254960: PASS
Fast CI для финального head 29863609253: PASS
целевой standard/cards с restart 29862551442: PASS
финальный standard/full 29862800106: PASS
```

Локальный Docker не повторялся после успешного cloud E2E с точным пакетом. Проверка на приватном профиле Anki владельца не выполнялась.

## C2 Core hardening и C1 UI remediation

Обязательный локальный контур:

- parser-backed CSS policy, preview и CSP/security headers;
- exact-card authority для релевантного note type;
- deferred-promise tests поколений query, mutation и inspect cache;
- Search runtime/server/status/idle и E2E behavior helpers;
- Cards и Inspection Profiles visual contracts, RU/EN, light/dark и границы 1199/1200;
- benchmark 100 000 ID с фиксацией времени, peak add-on memory и upstream materialization;
- полный Python/frontend, typecheck, production build, bundle guard, package validation и `-SkipDocker`.

После локального PASS выполняются Fast CI exact SHA, один `standard/cards` с restart и один `standard/full`. `strict-apkg`, `perf100`, warm repeats и локальный full Docker не требуются. Политика запусков не меняется; подробности остаются в [`verification-run-policy.md`](verification-run-policy.md).

Post-merge manual acceptance remediation дополнительно фиксирует computed styles для `.card` root/background без внешних requests, ownership wheel/page/queue/drawer scroll, взаимоисключающие Basic/Advanced modes, container-query layout 3→2→1, сохранение current content и active item при refresh, pending/status feedback и reduced-motion path. Private-profile действия владельца остаются отдельным manual gate.

## Поставка release

Изменения версии, пакета, publisher и workflow release требуют профильные тесты:

```text
test_release_automation.py
test_ankiweb_publisher.py
test_release_workflow.py
test_package_build.py
tests/publish_ankiweb.test.mjs
```

Финальный production-gate — `standard/full` на точном SHA release-артефакта. Тяжёлая задача release запускается только вручную из разрешённой ветки после отдельного решения владельца.

## Product notices и consent

Обязательны:

- тесты product notices, changelog, dashboard, package и release;
- тесты coordinator, API и frontend;
- паритет RU/EN;
- целевой `standard/settings`;
- финальный `standard/full` только при общем diff App Shell, server, E2E или package.

Real-Anki smoke проверяет порядок consent-first, отсутствие предварительного выбора, сохранение отказа, отсутствие повторного What’s New, ручное повторное открытие и маршрут Privacy.
