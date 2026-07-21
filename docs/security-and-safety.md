# Модель безопасности и safety boundaries

**Снимок документации:** 2026-07-22

Проект работает локально, но обрабатывает HTML/CSS/media карточек и поднимает HTTP server. Поэтому security model является обязательным product contract.

## Основные инварианты

- server слушает только `127.0.0.1`;
- все чувствительные API защищены dashboard token;
- frontend не читает Anki collection или profile filesystem напрямую;
- public payloads и API bounded и строго типизированы;
- mutations доступны только через allowlisted operations;
- card HTML/CSS/media проходят sanitizer и validation;
- arbitrary SQL/RPC/JavaScript/Python/shell/template execution запрещены;
- token, token-bearing URL, paths, content и identifiers не попадают в normal logs, public artifacts или remote telemetry;
- runtime/generated artifacts не коммитятся.

## Loopback server и token

`dashboard_server.py` слушает только:

```text
127.0.0.1
```

Открытие server на external interface требует отдельного security review.

Token создаётся через:

```python
secrets.token_urlsafe(32)
```

и проверяется `secrets.compare_digest(...)`.

Invalid token возвращает HTTP `403` с generic error. Token и полный token-bearing URL запрещено сохранять в logs, screenshots, DOM dumps, reports и telemetry.

## Public-safe artifacts

Raw `e2e-artifacts/` не публикуются. Token-bearing readiness data заменяется redacted JSON. Token query parameters и private paths удаляются из text evidence.

Exporter:

- разрешает только ожидаемые artifact categories;
- проверяет manifest relative paths;
- отклоняет secrets, private home paths и token signatures;
- не копирует environment dumps, credentials, local input, caches или layers.

Workflow использует только `permissions: contents: read`, не получает secrets/OIDC и хранит public-safe artifacts ограниченное время.

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

## Frontend boundary

Frontend получает опубликованный JSON и вызывает narrow API. Он не читает напрямую:

```text
collection.anki2
profile folder
media directories
```

Dashboard payloads публикуют только bounded projections и aggregates. Raw revlog, collection dump, card/note values, template source, tokens и runtime paths наружу не передаются.

## Search boundary

```text
POST /api/search/query
POST /api/search/inspect
```

Endpoints token-protected, POST/JSON-only и bounded.

Native query валидируется Anki. Structured filters строятся без ручной SQL-like конкатенации. Arbitrary SQL/sort отсутствуют.

Search v2 возвращает только bounded Card/Note projections. Raw query и token не логируются и не попадают в E2E artifacts.

## Triage query и exact-card recheck

```text
POST /api/triage/query    schema v4
POST /api/triage/recheck  schema v1
```

Оба endpoints:

- token-protected;
- POST/JSON-only;
- body cap 8 KiB;
- serialized through `QueryOp`;
- принимают только strict bounded IDs, scope и schema fields.

Recheck принимает одну card, expected note ID, `1..4` stable reason IDs и current scope.

Он переиспользует canonical detectors Triage v4. Запрещены arbitrary query/SQL/HTML input, unbounded scan, second detector stack и client-side resolution inference.

Partial/unavailable/error evidence, profile-authority change, identity mismatch и missing/changed entity работают fail closed. Action success и `action.no_changes` не являются resolution evidence.

## Inspection Profiles boundary

Endpoints:

```text
POST /api/inspection-profiles/query
POST /api/inspection-profiles/validate
POST /api/inspection-profiles/update
```

Они token-protected, POST-only, JSON-only и ограничены 64 KiB.

Store path вычисляется только из active Anki profile. User-supplied path не принимается.

Document:

- cap 1 MiB;
- atomic write;
- optimistic revision;
- corruption quarantine;
- future-schema preserve/fail-closed.

Rules — только hard-coded declarative union. Запрещены arbitrary regex, code, SQL, shell, network, filesystem и media-existence checks.

Profile contents, field mappings, checks и note samples не отправляются в telemetry и не логируются. Evidence исключает raw values, HTML, filenames, template source, paths, tokens и exceptions.

## Card display formatter boundary

Formatter хранится отдельно в profile-local `card_display_formatters.json`.

Schema и API не содержат JavaScript, Python, SQL, shell, regex, selectors, expressions, callbacks, imports, paths, URLs, template HTML/CSS или remote endpoints.

Runtime не использует `eval`, `exec`, dynamic imports, subprocess или plugin callbacks.

Media handling принимает только bounded flat local filenames. Formatter не открывает media, не проверяет существование files, не разрешает filesystem path и не выполняет remote load.

## Mutation surface и action allowlists

```text
POST /api/entities/cards/actions
POST /api/entities/notes/actions
```

Endpoints token-protected, POST-only, body cap 8 KiB и принимают только hard-coded action union.

Card allowlist:

```text
suspend
unsuspend
set_flag
clear_flag
bury
unbury
move_to_deck
```

Note allowlist:

```text
add_tags
remove_tags
```

Bounds:

```text
batch IDs          1..200
tags               20 / 1000 characters
```

Весь batch валидируется до mutation. Writes используют один official Anki wrapper и один native undo step.

Generic method invocation, delete, arbitrary command и SQL запрещены.

Report actions:

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

Новые actions требуют allowlist, validation и tests.

## Settings и Profile allowlists

`GET/POST /api/dashboard/settings` публикует и изменяет только allowlisted public sections. Unknown/internal fields, token/runtime paths, package identity и E2E settings отклоняются.

`GET/POST /api/profile` принимает только bounded writable fields. Metrics, Anki profile identity, paths и unknown fields read-only/forbidden.

## Statistics и FSRS

Statistics API принимает только typed scope/period/granularity/comparison. FSRS API read-only и принимает только documented operation union.

Запрещены arbitrary search, SQL, raw protobuf, parameter vectors и raw revlog/card/note rows.

## Signals, Notifications и telemetry

Signals, evidence, entity IDs, notification history и preferences остаются в per-profile SQLite и не расширяют remote telemetry taxonomy.

Bounds:

```text
evidence per code     2048 bytes
history retention     180 дней / 5000 items
repeated-Again query  максимум 50 cards
```

Remote telemetry исключает:

- collection/card/note content;
- field names/values;
- Search queries;
- card/note/deck IDs;
- compact display text;
- media filenames;
- token-bearing URLs;
- profile/check mappings;
- raw diagnostics.

Effective purposes по умолчанию и при read error отключены.

## Media endpoint

```text
/api/media?name=<media-name>&token=<token>
```

Filename validation отклоняет:

- `file:` и `javascript:` schemes;
- traversal `..`;
- slash/backslash paths;
- Windows drive paths;
- unsupported extensions;
- control characters.

## HTML/CSS/media sanitizer

Удаляются или нормализуются:

- `script`, `style`, `iframe`, `object`, `embed`, `meta`, `link`;
- inline event handlers;
- `srcset`;
- dangerous CSS: `url(...)`, `@import`, `javascript:`, `vbscript:`, `data:`, `behavior`, `position`, `z-index`;
- local paths и `file://`;
- token query fragments.

Safe inline styles ограничены allowlist. Media refs переписываются только в validated `/api/media` URLs.

Sanitizer нельзя ослаблять ради visual fidelity. Если card после sanitizer выглядит хуже, добавляется точечный safe allowlist и regression test.

Cards preview не использует iframe и не выполняет card/template JavaScript. Shadow DOM не позволяет CSS карточки протекать в dashboard.

## Verification

Rendering/media:

```powershell
node scripts/run_python.mjs -m pytest tests/test_note_intelligence.py
cd web-dashboard
pnpm run test:frontend
```

Server/token/actions/Triage:

```powershell
node scripts/run_python.mjs -m pytest \
  tests/test_dashboard_server.py \
  tests/test_dashboard_actions.py \
  tests/test_triage_service.py \
  tests/test_triage_runtime.py
```

Package:

```powershell
node scripts/run_python.mjs scripts/package_addon.py --check
```

Native rendering, media, startup, restart и QueryOp integration финально проверяются live Anki или real-Anki Docker/cloud E2E по [`test-matrix.md`](test-matrix.md) и [`verification-run-policy.md`](verification-run-policy.md).

## Release credentials

AnkiWeb credentials существуют только как protected environment secrets. Они не передаются через CLI args, не записываются в docs/reports/artifacts и не сохраняются в browser profile.

Publisher fail closed при challenge/2FA, changed DOM, ambiguity, branch mismatch или artifact/hash mismatch.

## License и public materials

Repository использует `GPL-3.0-only`; root `LICENSE` является source of terms.

Third-party materials обязаны иметь совместимые условия и отдельные notices. Tracked E2E fixture является owner-authored/sanitized и разрешена для repository/tests/CI distribution.