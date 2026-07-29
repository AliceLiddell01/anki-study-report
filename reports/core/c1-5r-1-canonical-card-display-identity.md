# C1.5R.1 — каноническая идентичность отображения карточки

**Дата:** 2026-07-19

**Ветка:** `core`

**Исходное состояние:** `219fe515ef58e55bc3b8866b4ec4832148126df3`

**Проверенный HEAD реализации:** `a46116e43756eceb3820f4eca76b28645a54a3ff`

**HEAD итоговой документации:** зафиксирован отдельным Markdown-коммитом завершения

**Статус:** завершено

## Назначение

C1.5R.1 исправляет компактную идентичность карточки, не поглощая последующие этапы исправлений. Теперь один backend-projector конкретной карточки обслуживает Search, Triage и актуальные поверхности Cards. Произвольное поле сортировки заметки и первое непустое поле больше не используются как идентичность карточки.

Этот отчёт фиксирует профильную проверку и завершение C1.5R.1. Он не является продуктовой приёмкой владельцем всего комплекса исправлений C1.5R.

## Выполненный scope

### Backend-projector

Добавлен файл:

```text
anki_study_report/card_display_identity.py
```

Projector использует следующий приоритет:

```text
нативный вопрос Browser
→ нативная лицевая сторона reviewer
→ явное состояние media_only или unavailable
```

Он:

- выбирает первую содержательную строку отрендеренного текста;
- удаляет маркеры воспроизведения звука и Anki;
- распознаёт media-элементы как media, не раскрывая имена файлов или URL;
- удаляет scripts, styles и небезопасное встроенное содержимое;
- сохраняет соседний inline-текст на японском без искусственных пробелов;
- нормализует пробелы и декодирует entities;
- ограничивает текст 240 символами и одним многоточием;
- работает по принципу fail closed для повреждённой запрещённой разметки;
- никогда не перебирает произвольные поля заметки;
- никогда не рендерит ответ или обратную сторону;
- никогда не читает media-файлы;
- никогда не раскрывает исключения renderer.

Точная японская фикстура с большим количеством media даёт:

```text
【に】（する）
```

а не несвязанное значение поля сортировки:

```text
「Существительное」
```

### Schema v2 Search

Обычные запросы и ответы Search для поиска и просмотра теперь требуют точное значение `schemaVersion: 2`.

Строки и подробности карточек содержат:

```text
displayText
displaySource      browser_question | reviewer_front | none
displayStatus      available | media_only | unavailable
displayTruncated
```

Поле `primaryText` карточки удалено. Строки и подробности заметок сохраняют `primaryText` в режиме заметок. Metadata Search остаётся независимым вариантом schema v1.

Строки карточек Search, просмотр карточки в Search и определение конкретной карточки используют один Python-projector.

### Schema v3 Triage

Запрос и ответ Triage теперь требуют точное значение `schemaVersion: 3`.

Элементы Triage содержат те же четыре поля отображения и не содержат `primaryText`. Доступные элементы копируют идентичность конкретной карточки из Search. Отсутствующие или повреждённые элементы resolver используют явное состояние unavailable. Устаревшее поле `attention.frontPreview` не используется как fallback.

### Строгий parsing во frontend

Runtime-parsers Search и Triage отклоняют:

- старые schema;
- неизвестные верхнеуровневые, вложенные или относящиеся к элементам ключи;
- alias `primaryText` у карточки;
- отсутствующие поля отображения;
- недопустимые enum source/status;
- слишком длинный текст;
- несогласованные сочетания текста, source, status и truncation;
- расхождения count, ID и вложенной структуры.

### Общее представление в UI

Добавлен файл:

```text
web-dashboard/src/lib/cardDisplayText.ts
```

В состоянии `available` helper возвращает backend-текст без изменений и локализует только два явных fallback-состояния:

| Состояние | RU | EN |
| --- | --- | --- |
| `media_only` | Карточка только с медиа | Card with media only |
| `unavailable` | Текст карточки недоступен | Card text unavailable |

Он используется в:

```text
строке карточки Search
заголовке Inspector карточки Search
фильтре Cards по видимому тексту
элементе очереди Cards
заголовке Inspector Cards
```

Текущее табличное split-пространство Cards не перерабатывалось и остаётся историческим UI C1.5, отклонённым на продуктовом уровне.

## Добавленные и обновлённые тесты

Python:

```text
tests/test_card_display_identity.py
tests/test_search_service.py
tests/test_search_metadata.py
tests/test_search_runtime.py
tests/test_triage_service.py
tests/test_triage_runtime.py
tests/test_dashboard_server.py
```

Frontend:

```text
web-dashboard/src/lib/cardDisplayText.test.ts
web-dashboard/src/lib/searchApi.test.ts
web-dashboard/src/lib/triageApi.test.ts
web-dashboard/src/hooks/useCardsTriageWorkspace.test.tsx
web-dashboard/src/pages/SearchPage.test.tsx
web-dashboard/src/pages/SearchMetadataIntegration.test.tsx
web-dashboard/src/pages/CardsPage.test.tsx
web-dashboard/src/pages/SearchPageActions.test.tsx
```

Покрыто поведение приоритетов Browser/reviewer, состояний media-only и unavailable, точной японской фикстуры, удаления небезопасной разметки, truncation, запрета чтения ответа и media-файлов, паритета Search/Triage, отклонения schema и неизвестных ключей, fallback RU/EN, передачи точного ID и просмотра только активной карточки.

## Синхронизированная документация

```text
docs/card-display-identity.md
docs/search-query-foundation.md
docs/search-v1-and-safe-actions.md
docs/cards-v2-triage-read-api.md
docs/dashboard-api.md
docs/frontend-map.md
docs/ai-handoff.md
roadmap/README.md
roadmap/core/README.md
```

## Выполненная проверка

### Проверенная реализация

```text
ветка: core
проверенный HEAD реализации: a46116e43756eceb3820f4eca76b28645a54a3ff
синхронизация с origin/core: 0 позади / 0 впереди
расхождение с origin/master: 0 позади / 71 впереди
открытые PR из core: отсутствуют
```

Профильный контур выполнен на точном проверенном HEAD реализации после исправления и отправки единственного дефекта проверки.

### Компиляция Python

```powershell
node scripts/run_python.mjs -m compileall -q anki_study_report
```

Результат:

```text
код завершения: 0
длительность: 2,75 с
оставшиеся __pycache__ / .pyc / .pyo: 0
```

### Профильные Python-тесты

```powershell
node scripts/run_python.mjs -m pytest -q `
  tests/test_card_display_identity.py `
  tests/test_search_service.py `
  tests/test_search_metadata.py `
  tests/test_search_runtime.py `
  tests/test_triage_service.py `
  tests/test_triage_runtime.py `
  tests/test_dashboard_server.py
```

Результат на проверенном HEAD реализации:

```text
85 passed
0 failed
1 warning
длительность pytest: 10,83 с
длительность команды: 12,69 с
код завершения: 0
```

Предупреждение относилось только к окружению: `PytestCacheWarning`, поскольку Windows запретила создание `.pytest_cache`. На выполнение тестов и код завершения это не повлияло, cache-артефакт в Git не попал.

### Профильный frontend Vitest

```powershell
pnpm exec vitest run `
  src/lib/cardDisplayText.test.ts `
  src/lib/searchApi.test.ts `
  src/lib/triageApi.test.ts `
  src/hooks/useCardsTriageWorkspace.test.tsx `
  src/pages/SearchPage.test.tsx `
  src/pages/SearchMetadataIntegration.test.tsx `
  src/pages/CardsPage.test.tsx `
  src/pages/SearchPageActions.test.tsx
```

Результат на проверенном HEAD реализации:

```text
8 test files passed
54 tests passed
0 failed
длительность Vitest: 3,60 с
длительность команды: 7,29 с
код завершения: 0
```

`SearchPageActions.test.tsx` прошёл и сохранил проверки pagination, выбора между страницами, ограничения в 200 элементов, обновления после действия, защиты от повторной отправки и остальных регрессий Safe Actions в Search, необходимых для завершения этапа.

### TypeScript typecheck

```powershell
pnpm run typecheck
```

Результат на проверенном HEAD реализации:

```text
tsc --noEmit
0 errors
длительность: 10,60 с
код завершения: 0
```

### Дефект проверки и исправление

Первый typecheck кандидата реализации `52c03c340c7a98b72d869ea42d6a9a46d56233e7` выявил 12 ошибок TypeScript в трёх тестовых файлах. Runtime-тесты проходили; mocks вывели tuple с нулём или одним аргументом, тогда как assertions проверяли необязательный второй аргумент `RequestInit`.

Исправление не изменило production-поведение. Затронутые mocks получили тип `typeof fetch` в файлах:

```text
web-dashboard/src/lib/searchApi.test.ts
web-dashboard/src/lib/triageApi.test.ts
web-dashboard/src/pages/SearchPage.test.tsx
```

Коммит исправления:

```text
a46116e43756eceb3820f4eca76b28645a54a3ff — test: type fetch mocks for strict contract checks
```

После исправления:

```text
узкий набор затронутых Vitest: 3 файла / 39 тестов passed
полный профильный Python-набор: 85 passed
полный профильный Vitest-набор: 8 файлов / 54 теста passed
typecheck: passed
```

Других дефектов проверки не обнаружено.

### Гигиена Git

```text
отслеживаемые изменения рабочего дерева перед завершением: 0
staged-изменения перед завершением: 0
запрещённые отслеживаемые артефакты: 0
git diff --check: passed
выполняющийся merge: нет
выполняющийся rebase: нет
выполняющийся cherry-pick: нет
```

Два несвязанных неотслеживаемых вспомогательных файла геймификации сохранены и исключены из scope:

```text
g0_6a_run.ps1
g0_6a_tool.py
```

### Намеренно не запускалось

```text
полный набор Python-тестов
полный набор frontend-тестов
сборка frontend
проверка или сборка пакета
run_full_check.ps1 -SkipDocker
Fast CI
Docker
real-Anki E2E
проверка выпуска
продуктовая приёмка владельцем
```

Это находилось за пределами политики профильной проверки C1.5R.1V. Тяжёлая комплексная проверка остаётся частью C1.5R.7.

## Явно не реализованный scope

```text
семантика предпросмотра лицевой и обратной стороны C1.5R.3
изменения источников кандидатов и явное состояние периода C1.5R.4
плотная очередь и немодальная панель для 1024 px C1.5R.5
пошаговая настройка Inspection Profiles C1.5R.6
пакет комплексной приёмки C1.5R.7
цикл действий, перепроверки и определения результата C1.6
```

## Границы Git

PR, merge, rebase, force-push, выпуск, deployment, публикация `.ankiaddon` или обновление AnkiWeb не выполнялись. Сгенерированные assets, скриншоты, логи, caches, данные профиля, токены и результаты E2E не коммитились.

## Финальное состояние этапа

```text
C1.5R.0 — завершено
C1.5R.1 — завершено
C1.5R.2 — следующий этап, не начат
C1.5R.3–R.7 — не начаты
C1.6 — заблокирован
Core C1 — выполняется
```

Следующая точная часть Core — C1.5R.2. Она не начиналась во время завершения этого этапа.
