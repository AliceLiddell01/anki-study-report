# Модель безопасности и границы защиты

**Снимок документации:** 2026-07-22

Проект работает локально, но обрабатывает HTML, CSS и media карточек и поднимает HTTP-server. Поэтому модель безопасности является обязательным продуктовым контрактом.

## Основные инварианты

- server слушает только `127.0.0.1`;
- все чувствительные API защищены токеном dashboard;
- frontend не читает collection Anki или файловую систему профиля напрямую;
- публичные payload и API ограничены и строго типизированы;
- mutations доступны только через операции из allowlist;
- HTML, CSS и media карточек проходят sanitizer и validation;
- запрещено выполнение произвольных SQL, RPC, JavaScript, Python, shell и шаблонов;
- токен, URL с токеном, пути, содержимое и идентификаторы не попадают в обычные логи, публичные артефакты или удалённую телеметрию;
- runtime- и сгенерированные артефакты не коммитятся.

## Loopback-server и токен

`dashboard_server.py` слушает только:

```text
127.0.0.1
```

Открытие server на внешнем интерфейсе требует отдельной проверки безопасности.

Токен создаётся через:

```python
secrets.token_urlsafe(32)
```

и проверяется `secrets.compare_digest(...)`.

Недопустимый токен возвращает HTTP `403` с обобщённой ошибкой. Токен и полный URL с токеном запрещено сохранять в логах, скриншотах, DOM-dumps, отчётах и телеметрии.

## Публично безопасные артефакты

Необработанный каталог `e2e-artifacts/` не публикуется. Данные readiness с токеном заменяются отредактированным JSON. Параметры query с токеном и приватные пути удаляются из текстовых подтверждений.

Exporter:

- разрешает только ожидаемые категории артефактов;
- проверяет относительные пути manifest;
- отклоняет secrets, приватные домашние пути и сигнатуры токена;
- не копирует dumps окружения, credentials, локальные входные данные, caches или layers.

Workflow использует только `permissions: contents: read`, не получает secrets или OIDC и хранит публично безопасные артефакты ограниченное время.

Не коммитить:

```text
e2e-artifacts/
web-dashboard/screenshots/
anki_study_report/user_files/logs/
anki_study_report/user_files/*.sqlite3
web-dashboard/dist/
anki_study_report/web_dashboard/
*.ankiaddon
```

## Граница frontend

Frontend получает опубликованный JSON и вызывает узкие API. Он не читает напрямую:

```text
collection.anki2
profile folder
media directories
```

Payload dashboard публикует только ограниченные проекции и агрегаты. Необработанный revlog, dump collection, значения карточек и заметок, исходный код шаблонов, токены и runtime-пути наружу не передаются.

## Граница Search

```text
POST /api/search/query
POST /api/search/inspect
```

Endpoints защищены токеном, принимают только POST и JSON и имеют строгие ограничения.

Нативный query валидируется Anki. Структурированные фильтры строятся без ручной SQL-подобной конкатенации. Произвольные SQL и sort отсутствуют.

Search v2 возвращает только ограниченные проекции Cards и Notes. Необработанный query и токен не логируются и не попадают в артефакты E2E.

## Запрос Triage и recheck конкретной карточки

```text
POST /api/triage/query    schema v4
POST /api/triage/recheck  schema v1
```

Оба endpoints:

- защищены токеном;
- принимают только POST и JSON;
- ограничены телом 8 КиБ;
- сериализованы через `QueryOp`;
- принимают только строгие ограниченные ID, scope и поля schema.

Recheck принимает одну карточку, ожидаемый ID заметки, от 1 до 4 стабильных ID причин и текущий scope.

Он переиспользует канонические детекторы Triage v4. Запрещены произвольный query, SQL и HTML-ввод, неограниченная проверка, второй стек детекторов и клиентское определение устранения.

Частичное, недоступное или ошибочное подтверждение, изменение authority профиля, несовпадение идентичности и отсутствующая или изменённая сущность работают по принципу fail closed. Успех действия и `action.no_changes` не являются подтверждением устранения.

## Граница Inspection Profiles

Endpoints:

```text
POST /api/inspection-profiles/query
POST /api/inspection-profiles/validate
POST /api/inspection-profiles/update
```

Они защищены токеном, принимают только POST и JSON и ограничены 64 КиБ.

Путь store вычисляется только из активного профиля Anki. Пользовательский путь не принимается.

Документ:

- ограничен 1 МиБ;
- записывается атомарно;
- использует optimistic revision;
- помещает повреждённые данные в quarantine;
- сохраняет будущую schema и работает по принципу fail closed.

Правила представлены только жёстко заданным декларативным union. Запрещены произвольные regex, код, SQL, shell, network, filesystem и проверки существования media.

Содержимое профиля, mappings полей, checks и выборки заметок не отправляются в телеметрию и не логируются. Подтверждение исключает необработанные значения, HTML, имена файлов, исходный код шаблонов, пути, токены и исключения.

## Граница formatter отображения карточки

Formatter хранится отдельно в локальном для профиля `card_display_formatters.json`.

Schema и API не содержат JavaScript, Python, SQL, shell, regex, selectors, expressions, callbacks, imports, paths, URL, HTML или CSS шаблона и удалённые endpoints.

Runtime не использует `eval`, `exec`, динамические imports, subprocess или callbacks plugins.

Обработка media принимает только ограниченные плоские локальные имена файлов. Formatter не открывает media, не проверяет существование файлов, не разрешает путь файловой системы и не выполняет удалённую загрузку.

## Поверхность mutations и allowlists действий

```text
POST /api/entities/cards/actions
POST /api/entities/notes/actions
```

Endpoints защищены токеном, принимают только POST, ограничены телом 8 КиБ и принимают только жёстко заданный union действий.

Allowlist карточек:

```text
suspend
unsuspend
set_flag
clear_flag
bury
unbury
move_to_deck
```

Allowlist заметок:

```text
add_tags
remove_tags
```

Ограничения:

```text
ID в пакете      1..200
tags              20 / 1000 символов
```

Весь пакет валидируется до mutation. Записи используют один официальный wrapper Anki и один нативный шаг undo.

Generic method invocation, delete, произвольные команды и SQL запрещены.

Действия отчёта:

```text
copy-markdown
save-markdown
open-browser
open-browser-search
open-deck-browser
open-search-selection
open-problematic
open-again
open-new
open-dashboard
open-native-stats
```

Действия server:

```text
restart
stop
open-dashboard
copy-url
```

Новые действия требуют allowlist, validation и тестов.

## Allowlists Settings и Profile

`GET/POST /api/dashboard/settings` публикует и изменяет только публичные разделы из allowlist. Неизвестные и внутренние поля, токен, runtime-пути, идентичность пакета и настройки E2E отклоняются.

`GET/POST /api/profile` принимает только ограниченные доступные для записи поля. Метрики, идентичность профиля Anki, пути и неизвестные поля доступны только для чтения или запрещены.

## Statistics и FSRS

API Statistics принимает только типизированные scope, period, granularity и comparison. API FSRS работает только на чтение и принимает документированный union операций.

Запрещены произвольные Search, SQL, необработанный protobuf, vectors параметров и строки revlog, карточек и заметок.

## Signals, Notifications и телеметрия

Signals, подтверждения, ID сущностей, история уведомлений и preferences остаются в SQLite на уровне профиля и не расширяют taxonomy удалённой телеметрии.

Ограничения:

```text
подтверждение на код      2048 байт
хранение истории          180 дней / 5000 элементов
запрос repeated Again     максимум 50 карточек
```

Удалённая телеметрия исключает:

- содержимое collection, карточек и заметок;
- имена и значения полей;
- queries Search;
- ID карточек, заметок и колод;
- компактный отображаемый текст;
- имена media-файлов;
- URL с токеном;
- mappings профилей и проверок;
- необработанную диагностику.

Фактические purposes по умолчанию и при ошибке чтения отключены.

## Endpoint media

```text
/api/media?name=<media-name>&token=<token>
```

Проверка имени файла отклоняет:

- schemes `file:` и `javascript:`;
- traversal `..`;
- пути со slash или backslash;
- пути с диском Windows;
- неподдерживаемые расширения;
- управляющие символы.

## Sanitizer HTML, CSS и media

Удаляются или нормализуются:

- `script`, `style`, `iframe`, `object`, `embed`, `meta`, `link`;
- inline-обработчики событий;
- `srcset`;
- опасный CSS: `url(...)`, `@import`, `javascript:`, `vbscript:`, `data:`, `behavior`, `position`, `z-index`;
- локальные пути и `file://`;
- fragments query с токеном.

Безопасные inline-styles ограничены allowlist. Ссылки media переписываются только в проверенные URL `/api/media`.

Sanitizer нельзя ослаблять ради визуальной точности. Если карточка после sanitizer выглядит хуже, добавляется точечный безопасный allowlist и регрессионный тест.

Предпросмотр Cards не использует iframe и не выполняет JavaScript карточки или шаблона. Shadow DOM не позволяет CSS карточки влиять на dashboard.

## Проверка

Рендер и media:

```powershell
node scripts/run_python.mjs -m pytest tests/test_note_intelligence.py
cd web-dashboard
pnpm run test:frontend
```

Server, токен, действия и Triage:

```powershell
node scripts/run_python.mjs -m pytest \
  tests/test_dashboard_server.py \
  tests/test_dashboard_actions.py \
  tests/test_triage_service.py \
  tests/test_triage_runtime.py
```

Пакет:

```powershell
node scripts/run_python.mjs scripts/package_addon.py --check
```

Нативный рендер, media, startup, restart и интеграция QueryOp окончательно проверяются в live Anki или real-Anki Docker или cloud E2E по [`test-matrix.md`](test-matrix.md) и [`verification-run-policy.md`](verification-run-policy.md).

## Credentials выпуска

Credentials AnkiWeb существуют только как защищённые secrets окружения. Они не передаются через аргументы CLI, не записываются в docs, reports или artifacts и не сохраняются в профиле browser.

Publisher работает по принципу fail closed при challenge или 2FA, изменившемся DOM, неоднозначности, несовпадении ветки или артефакта и hash.

## Лицензия и публичные материалы

Репозиторий использует `GPL-3.0-only`; корневой `LICENSE` является источником условий.

Материалы третьих сторон обязаны иметь совместимые условия и отдельные notices. Отслеживаемая E2E-фикстура создана владельцем или санитизирована и разрешена для распространения в репозитории, тестах и CI.
