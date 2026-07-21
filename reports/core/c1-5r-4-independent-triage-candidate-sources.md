# C1.5R.4 — независимые источники кандидатов Triage

## Подтверждённое состояние

- начальный HEAD `core`: `8a91a69f147e78133673924d20bee296a15f562f`;
- проверенный HEAD реализации: `31b3b795e055f6be963c129b3edc1afdfc9dcd57`;
- проверенное дерево реализации: `2aa017edbd992402e11b97967adccd33c56f7a02`;
- финальный запуск проверки: `29701478622` — PASS;
- запуск после переноса: `29701642665` — PASS;
- перенос: точный fast-forward в `core` без конфликтов и force;
- PR, merge в `master`, выпуск и deployment: отсутствуют.

## Восстановление реализации

Долговечная реализация была восстановлена из последнего временного кандидата R4 поверх точного состояния `core`. Чистая история реализации содержит один логический коммит и 25 долговечных файлов. Scripts применения и проверки, временный YAML workflow, triggers, файлы статуса, логи, сгенерированные assets dashboard и результат сборки пакета исключены из дерева реализации.

Теперь backend отвечает за независимые ограниченные loaders:

- `learningCandidates` — источник из истории повторений, ограниченный запрошенным периодом;
- `contentCandidates` — источник текущего содержимого, не зависящий от истории повторений;
- авторитетные подтверждённые Inspection Profiles разрешаются до проверки заметок;
- текущее содержимое использует keyset-окно на 500 заметок по условию `note.id > contentCursor` и одно пакетное чтение карточек и заметок;
- каждая заметка оценивается один раз и привязывается к детерминированно выбранной подходящей карточке;
- идентичность Search определяется только для карточек с объединёнными причинами.

Schema запроса и ответа Triage является строгой v4. Search остаётся на schema v2. Компактная идентичность R1 и семантика предпросмотра R3 не изменены. Работа над компоновкой R5 не начиналась.

## Проверка

| Контур | Код завершения | Длительность, с |
| --- | ---: | ---: |
| Материализация и проверка diff | 0 | 0,3 |
| Установка Python-зависимостей | 0 | 3,1 |
| Установка frontend-зависимостей | 0 | 1,3 |
| Начальная сборка `pnpm run build:addon` | 0 | 18,7 |
| Профильный backend | 0 | 11,8 |
| Профильный frontend | 0 | 2,6 |
| TypeScript typecheck | 0 | 10,2 |
| Production-сборка | 0 | 17,8 |
| Сборка и проверка пакета | 0 | 0,2 |
| Пакет `--check-only` | 0 | 0,1 |
| API smoke | 0 | 1,5 |
| Канонический `run_full_check.ps1 -SkipDocker` | 0 | 63,9 |
| Гигиена Git и denylist | 0 | 0,0 |

Профильный backend: `104 passed`.

Профильный frontend: 3 файла, `21 passed`.

Канонический gate без Docker: `788 Python tests passed`; набор frontend-тестов, сборка, ограничение bundle, сборка и проверка пакета и целостность ZIP прошли. Пакет содержал 73 записи, `ZipFile.testzip() = None`.

Проверки после переноса выполнялись на точном detached SHA `core` `31b3b795e055f6be963c129b3edc1afdfc9dcd57`:

| Контур | Код завершения | Длительность, с |
| --- | ---: | ---: |
| Профильный backend | 0 | 12 |
| Профильный frontend | 0 | 3 |
| Typecheck | 0 | 10 |
| API smoke | 0 | 1 |
| Гигиена Git | 0 | 0 |

## Сценарии приёмки

- отсутствие повторений при подтверждённом требовании audio в Japanese → `content.audio_missing`;
- профиль Programming без требования audio → отсутствие ложной проблемы audio;
- изменение периода не меняет кандидатов по текущему содержимому;
- scope колоды и шаблонов профиля применяется до выбора representative card;
- продолжение использует строго возрастающий cursor ID заметки, ограничено 500 заметками и не содержит дубликатов или автоматического цикла;
- отсутствие подтверждённых профилей → отсутствие SQL-проверки содержимого;
- ошибки источников представлены независимо и не скрывают другой источник;
- сбор текущего содержимого использует два ограниченных чтения DB без N+1-запросов профилей и проверок;
- проверка кандидатов не выполняет рендер предпросмотра и не читает media-файлы.

## Классификация ошибок

Временные попытки проверки выявили только дефекты восстановления и тестовых контрактов:

- устаревшие backend-assertions v3 и старые monkeypatch общего collector;
- неполные строгие frontend-фикстуры v4;
- test regex, ошибочно помещавший `contentCursor` в фикстуру ответа.

Production-поведение не менялось ради устаревших тестов. После каждого исправления выполнялся полный профильный контур, а финальная реализация прошла канонический gate.

## Подтверждения workflow и артефактов

- финальная изолированная проверка: запуск `29701478622`, точный trigger `2d14e9eb8eed37791f80ded4b358de4254c67c14`, PASS;
- проверка после переноса: запуск `29701642665`, точный trigger `39859c3529fe8eb47382ca192c3743f5ed25adb0`, PASS;
- узкая проверка фикстуры: запуск `29701445382`, завершён;
- прежние временные неудачные попытки сохранены как исторические подтверждения: `29699284419`, `29699354074`, `29699584092`, `29699696383`, `29699845625`, `29701073993`, `29701152231`, `29701316740`;
- финальный и post-transfer-запуски не публиковали артефакты Actions;
- connector не предоставляет действие удаления workflow-run или артефакта, поэтому записи завершённых запусков остаются неизменяемыми; активных временных запусков R4 нет.

## Очистка

Все сохранившиеся временные refs были передвинуты fast-forward-коммитами к состояниям, дерево которых точно совпадает с чистым деревом реализации. Это сохраняет исторические подтверждения в ancestry, но удаляет все workflow, scripts применения и проверки, triggers, логи и файлы статуса из текущих вершин refs. Connector не поддерживает удаление refs, поэтому нейтрализованные refs остаются чистыми неисполняемыми указателями. Канонические workflows не изменены.

```json
{
  "canonicalWorkflowsTouched": false,
  "coreR4MarkerFiles": [],
  "coreTemporaryScripts": [],
  "coreTemporaryWorkflowFiles": [],
  "localTaskBranch": "not_created",
  "localWorktree": "not_created",
  "temporaryActionsRuns": "completed; deletion API unavailable",
  "temporaryArtifacts": [],
  "temporaryRemoteRefs": {
    "c1-5r-4-candidate-sources": "neutralized",
    "c1-5r-4-final-run": "neutralized",
    "c1-5r-4-final-status": "neutralized",
    "c1-5r-4-verify-run": "neutralized",
    "c1-5r-4v-closeout-exec-20260720": "neutralized_after_closeout",
    "c1-5r-4v-closeout-status-20260720": "neutralized_after_closeout",
    "c1-5r-4v-exec-20260720": "neutralized",
    "c1-5r-4v-post-status-20260720": "neutralized",
    "c1-5r-4v-posttransfer-20260720": "neutralized",
    "c1-5r-4v-status-20260720": "neutralized"
  }
}
```

## Безопасность и конфиденциальность

- необработанные значения заметок остаются внутри backend и отсутствуют в контрактах ответов и логов;
- сбор кандидатов не читает media-файлы и не рендерит предпросмотр;
- SQL является внутренним, read-only и параметризованным; произвольный SQL-ввод отсутствует;
- границы loopback, токена, content type и размера тела не изменены;
- URL с токеном, приватные пути, данные профиля владельца и runtime-логи не попали в долговечную историю Git.

## Изменённые файлы

- `anki_study_report/triage_candidates.py`;
- `anki_study_report/triage_service.py`;
- `docker/anki-e2e/README.md`;
- `docs/README.md`;
- `docs/architecture.md`;
- `docs/cards-v2-product-contract.md`;
- `docs/cards-v2-triage-read-api.md`;
- `docs/dashboard-api.md`;
- `docs/frontend-map.md`;
- `docs/security-and-safety.md`;
- `docs/test-matrix.md`;
- `docs/triage-candidate-sources-v4.md`;
- `tests/test_dashboard_server.py`;
- `tests/test_package_build.py`;
- `tests/test_triage_candidates.py`;
- `tests/test_triage_runtime.py`;
- `tests/test_triage_service.py`;
- `web-dashboard/src/hooks/useCardsTriageWorkspace.test.tsx`;
- `web-dashboard/src/hooks/useCardsTriageWorkspace.ts`;
- `web-dashboard/src/i18n/locales/en.ts`;
- `web-dashboard/src/i18n/locales/ru.ts`;
- `web-dashboard/src/lib/triageApi.test.ts`;
- `web-dashboard/src/lib/triageApi.ts`;
- `web-dashboard/src/pages/CardsPage.test.tsx`;
- `web-dashboard/src/types/triage.ts`;
- `roadmap/core/README.md`;
- `roadmap/README.md`;
- `docs/ai-handoff.md`;
- `reports/core/c1-5r-4-independent-triage-candidate-sources.md`.

## Не проверено

- Fast CI;
- Docker и real-Anki E2E;
- приватный профиль Anki владельца;
- продуктовая приёмка владельцем;
- приёмка UI C1.5R.5.

## Границы Git

```text
отправлено в origin/core: да
PR: нет
merge в master: нет
force-push: нет
выпуск: нет
deployment: нет
публикация на AnkiWeb: нет
```

## Статус

```text
C1.5R.0 — завершено
C1.5R.1 — завершено
C1.5R.2 — завершено
C1.5R.3 — завершено
C1.5R.4 — завершено
C1.5R.5 — следующий этап, не начат
C1.5R.6–R.7 — не начаты
C1.6 — заблокирован
Core C1 — выполняется
```
