# Security and safety model

## Signal/notification boundary

Signals, evidence, entity IDs, notification history и preferences остаются в
per-profile SQLite. Они не расширяют remote telemetry taxonomy и не отправляются
Cloudflare. Evidence имеет per-code allowlist и 2048-byte cap; history — 180
дней/5000 items; repeated-Again query — максимум 50 cards. Local API требует
loopback dashboard token, session handoff не пишет ID в hash/localStorage, а
E2E artifacts исключают DB, Authorization и полные ID lists.

FSRS API is read-only and strict: token required, no arbitrary search/SQL/raw
protobuf/parameter vector, no raw revlog or card/note content, bounded output,
revalidated normal-deck/config IDs and no generic RPC or Helper dependency.

Снимок документации: 2026-07-14.

Этот проект локальный, но он все равно обрабатывает HTML/CSS/media из карточек
и открывает HTTP server. Поэтому security model является частью контракта.

## Local-only server

`dashboard_server.py` использует host:

```text
127.0.0.1
```

Dashboard не должен слушать внешний интерфейс без отдельного security review.

## Token-protected API

Server генерирует token через `secrets.token_urlsafe(32)` при start. URL имеет
вид:

```text
http://127.0.0.1:<port>/?token=<token>
```

Token проверяется через `secrets.compare_digest(...)`. Неверный token получает
HTTP `403` и JSON:

```json
{
  "error": "invalid_dashboard_token",
  "ok": false,
  "message": "Недействительная ссылка dashboard. Откройте dashboard из Anki Study Report."
}
```

## Token-bearing artifacts

Token может попасть в:

- screenshots;
- copied dashboard URL;
- browser artifacts;
- E2E readiness files;
- logs, если добавить неаккуратный logging.

Не коммитить:

```text
e2e-artifacts/
web-dashboard/screenshots/
anki_study_report/user_files/logs/
```

`extension_logging.redact(...)` и `_redact_token(...)` в server code помогают,
но не заменяют ручную осторожность.

`artifact-manifest.json` индексирует readiness file только по relative path и
никогда не копирует его token-bearing content. Canonical add-on log path в E2E:
`diagnostics/anki_study_report.log`.

## Public settings allowlist

`GET/POST /api/dashboard/settings` требует token. Backend публикует и изменяет
только nested sections `dashboard`, `report`, `data`, `server`; unknown keys,
token/runtime paths/package identity и E2E settings отклоняются. Partial write
сохраняет internal config keys и возвращает normalized saved state.

## Profile allowlist and privacy

`GET/POST /api/profile` также требует token. POST принимает только дату начала
и enum сортировки; metrics, Anki profile name, paths и unknown fields менять
нельзя. Public model агрегирован, не содержит card content, collection dump,
token, absolute path, avatar/banner blobs или remote URL. `profile.json` лежит
в per-profile runtime и пишется атомарно.

## Frontend не читает Anki collection

Frontend получает уже опубликованный JSON и вызывает ограниченные API. Он не
читает `collection.anki2`, profile folder или media директории напрямую.

Activity Hub также приходит внутри `/api/report`: только bounded daily и
deck-day aggregates плюс deterministic derived events. В нём нет raw revlog,
card/note content, token или runtime paths; новый endpoint/SQL query API не
добавлен.

Statistics использует additive bounded `statisticsHub` и
`POST /api/statistics/query`. Query принимает только scope enum/current deck
ID, period/granularity enum и boolean comparison, ограничен 8 KiB и отклоняет
unknown fields, arbitrary search и SQL-like payload. Frontend получает только
daily/deck aggregates и grouped current state/due snapshot: raw revlog,
individual card/note IDs/text, token и paths не публикуются.

Search foundation — отдельное осознанное исключение для Search v1:
token-protected `POST /api/search/query` и `/api/search/inspect` возвращают
только выбранные bounded plain-text Card/Note projections. Native query
валидируется Anki, structured filters собираются без ручной конкатенации,
arbitrary SQL/sort отсутствуют. Query/body/result/field
limits, string IDs, safe text и generic runtime errors описаны в
`docs/search-query-foundation.md`. Raw query и token не попадают в normal logs
или E2E public artifact.

Mutation surface отделён от generic dashboard actions:
`POST /api/entities/cards/actions` и `/api/entities/notes/actions`. Оба
token-protected, POST-only, ограничены 8 KiB и принимают только hard-coded
action union. Batch cap — 200, tag cap — 20/1000 chars. Backend разрешает всю
пачку до mutation, не логирует IDs/tags/deck names и запускает один official
Anki wrapper. Move принимает только deck ID, повторно проверяет normal deck и
отклоняет filtered destination/source. См. `docs/search-v1-and-safe-actions.md`.

## Dashboard actions allowlist

Разрешенные report actions описаны в `actionsApi.ts` и
`dashboard_actions.py`:

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

Server actions:

```text
restart
stop
open-dashboard
copy-url
```

Это не произвольный RPC. Новые actions должны проходить allowlist, validation и
tests.

`open-deck-browser` принимает только deck ID и enum `subtree|direct`. Backend
проверяет current normal deck, отклоняет filtered/deleted/unknown ID и сам
экранирует canonical name. Frontend не передаёт raw Browser query для Decks v2.

`deckHub` содержит только aggregate metrics и current deck identity; token,
paths, card/note content и raw revlog отсутствуют.

## `/api/media`

Media отдается только через token-protected endpoint:

```text
/api/media?name=<media-name>&token=<token>
```

`sanitize_media_filename(...)` и `_safe_media_name(...)` отбрасывают:

- URL schemes вроде `file:` или `javascript:`;
- path traversal `..`;
- slash/backslash paths;
- Windows drive paths;
- неподдержанные extensions.

## HTML/CSS/media sanitizer

`note_intelligence.py` удаляет или нормализует:

- `<script>`, `<style>`, `<iframe>`, `<object>`, `<embed>`, `<meta>`, `<link>`;
- inline event handlers вроде `onclick`;
- `srcset`;
- dangerous style values: `url(...)`, `@import`, `javascript:`, `vbscript:`,
  `data:`, `behavior:`, `position`, `z-index`;
- local paths и `file://`;
- token query fragments.

Safe inline styles ограничены allowlist. Safe media refs переписываются в
`/api/media?name=...`.

## Почему нельзя ослаблять sanitizer ради preview

Card preview рендерит пользовательский HTML из карточек. Ослабление sanitizer
может превратить dashboard в execution surface для scripts, local file leaks
или CSS, который ломает весь dashboard. Если карточка выглядит хуже после
sanitizer, лучше добавить точечную safe allowlist с тестом, чем разрешить
опасный класс значений.

Cards preview не использует iframe и не исполняет JavaScript templates.
`table`, `tiles` и текущий `ankiPreview` rendered path используют
`AnkiCardShadowPreview` / Shadow DOM host, чтобы CSS карточек не протекал в
document-level dashboard styles. В `ankiPreview` этот host работает как
answer-only preview из уже sanitized `renderedPreview.backHtml`. Эти
ограничения являются частью security contract, а не только визуальной
реализации.

## Что проверять при изменениях

Rendering/media:

```powershell
node scripts/run_python.mjs -m pytest tests/test_note_intelligence.py
cd web-dashboard
pnpm run test:frontend
```

Server/token/actions:

```powershell
node scripts/run_python.mjs -m pytest tests/test_dashboard_server.py tests/test_dashboard_actions.py
```

Package/runtime:

```powershell
node scripts/run_python.mjs scripts/package_addon.py --check
```

Для native render/media/startup финально нужен live Anki или Docker E2E.

## GitHub Actions Fast CI

`.github/workflows/ci-fast.yml` использует только `permissions: contents: read`,
отключает сохранение checkout credentials и не получает repository secrets,
write token или OIDC. Используемые Actions закреплены полными upstream commit
SHA. Fast CI не запускает пользовательский Anki profile, Docker или внешний
deployment.

`ci-fast/` и загружаемый `.ankiaddon` являются краткоживущими runtime outputs:
они не коммитятся и не считаются release. Summary содержит commit/run/runtime
metadata, но не tokens, token-bearing URLs, абсолютные приватные пути или Anki
profile data. Полный artifact/fallback contract: `docs/ci-cd.md`.

После перехода репозитория в public Actions logs, summaries и artifacts нужно
считать потенциально публичными. В них запрещены secrets, token-bearing URLs,
PII, пользовательские профили/коллекции и чувствительные абсолютные пути.
Перед первым переключением видимости обязателен аудит всей reachable Git
history, refs, существующих Actions outputs и будущего artifact contract.

## License and public materials

Публичная видимость и лицензирование являются отдельными решениями. Текущий
репозиторий распространяется по `GPL-3.0-only`; корневой файл `LICENSE` является
источником условий. Файлы или сторонние материалы с отдельным notice сохраняют
свои собственные условия и должны быть совместимы с распространением проекта.

Tracked `asr-e2e-render-fixtures.apkg` является owner-authored, sanitized и
authorized test fixture. Её notes/cards/templates/CSS и 13 созданных владельцем
media распространяются как часть repository, tests, Docker E2E и CI artifacts
по текущей лицензии проекта. Это разрешение не отменяет отдельные notices,
которые могут появиться у будущих сторонних fixtures или материалов.

## Public Full Docker E2E artifacts

Cloud workflow не загружает raw `e2e-artifacts/`. Token-bearing
`runtime/dashboard-ready.json` заменяется redacted JSON без token; token query
parameters удаляются из text evidence. Exporter разрешает только ожидаемые
artifact categories, проверяет manifest paths, отклоняет secret signatures и
private home paths и не копирует environment dumps, Docker credentials,
local-input, caches или layers.

Artifact preparation и upload выполняются после success/failure, но исходный
canonical exit code восстанавливается после diagnostics и cleanup. Ошибка
redaction также завершает job ошибкой. Workflow использует только
`permissions: contents: read`, не получает secrets/OIDC и хранит public-safe
artifact 7 дней.

## Release credentials и publisher

`ANKIWEB_EMAIL` и `ANKIWEB_PASSWORD` являются только environment secrets
`ankiweb-production`. PR/Fast CI/E2E и GitHub Release jobs их не получают.
Publisher принимает их только из process environment: значения запрещено
передавать аргументами, писать в fixtures/reports/docs или сохранять в browser
profile. Playwright context временный; storage state, cookies, trace,
screenshots и authenticated HTML не сохраняются.

Publisher fail-closed останавливается при challenge/2FA, изменившемся DOM,
неоднозначных controls, лишней branch, несовпадении metadata/description/hash.
Разрешён ровно один Save существующей `Branch 1`; `Add New Branch` только
проверяется как элемент контракта. Отчёт содержит status, timestamps, публичные
IDs и SHA-256, но не credentials или private paths.

Post-publisher audit проверяет только правдоподобные owned persistence paths в
`GITHUB_WORKSPACE` и остаточные `RUNNER_TEMP/asr-ankiweb-*`. Он отклоняет
`playwright/.auth/**`, `.auth/*.json`, storage-state JSON, trace ZIP и
persistent browser profiles, но исключает `.git`, dependency trees (`node_modules`,
`.pnpm`) и tool caches. Поэтому source-файлы зависимостей с `cookie` в имени не
считаются auth state. Audit выводит только относительные пути и никогда не читает
или печатает содержимое найденных файлов; sanitized publisher report и release
bundle разрешены.

## Consent и product notices

Privacy/notices state хранится в profile `addon_data`, а не в package,
localStorage или report cache. UI вызывает только token-protected loopback
endpoints; remote endpoint/credential в frontend отсутствуют. Python хранит
write token только в per-profile `telemetry.sqlite3`, выдаёт наружу лишь
bounded status и выполняет сеть в одном background sender. По умолчанию и
при ошибке чтения effective purposes выключены. Unknown request fields,
не-boolean choices и non-POST mutations отклоняются. Точный запрет на content,
names, IDs, queries, secrets и raw diagnostics описан в
`docs/privacy-telemetry.md`. Queue/retry/deletion boundary описана в
`docs/telemetry-client.md`.

Ручной `POST /api/telemetry/check-send` также loopback-only, требует dashboard
token, принимает только `{}` и возвращает bounded codes без remote endpoint,
credential или arbitrary exception. Timer разрешает active-profile client в
момент tick; enrollment retry metadata хранится только в per-profile SQLite.
