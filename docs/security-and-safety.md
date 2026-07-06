# Security and safety model

Снимок документации: 2026-07-06.

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

## Frontend не читает Anki collection

Frontend получает уже опубликованный JSON и вызывает ограниченные API. Он не
читает `collection.anki2`, profile folder или media директории напрямую.

## Dashboard actions allowlist

Разрешенные report actions описаны в `actionsApi.ts` и
`dashboard_actions.py`:

```text
copy-markdown
save-markdown
open-browser
open-browser-search
open-problematic
open-again
open-new
open-dashboard
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
