# Диагностика типовых проблем

Снимок документации: 2026-07-06.

Этот документ помогает быстро понять, где искать причину, прежде чем менять
production code. Для выбора проверок см. `docs/test-matrix.md`.

## Быстрые симптомы

| Симптом | Вероятная причина | Где смотреть | Безопасное действие |
| --- | --- | --- | --- |
| Dashboard показывает forbidden | Нет token или token устарел | URL, `/api/report`, `dashboard_server.py` | Открыть dashboard из Anki заново |
| После свежей установки видны старые стили | Anki использует старую папку add-on/assets | `addons21`, `web_dashboard/assets` | Удалить старую установленную папку, переустановить, перезапустить Anki |
| Docker E2E не доходит до readiness | Add-on не импортирован, профиль не создан, server/report не стартовал | `e2e-artifacts/addon-e2e-events.jsonl` | Читать markers по порядку, проверить layout и `prefs21.db` |
| Cards preview пустой или smoke ждет не тот DOM | Несовпадение display mode и ожиданий smoke | `CardsPage.tsx`, `smoke-browser.mjs` | Проверить mode: `table`/`tiles` или `ankiPreview` |
| Media preview возвращает 400/404 | Unsafe name, файла нет, token не передан | `/api/media`, `note_intelligence.py` | Проверить `name`, token и provider media file |
| Payload test упал на точной форме | Контракт реально изменился или устарел тест | `dashboard_payload.py`, `report.ts`, tests | Сначала проверить фактический payload |
| Package validation падает | Нет linked asset, запрещенный файл, stale build | `scripts/package_addon.py` | Пересобрать dashboard и проверить archive validation |
| Cache показывает stale/error | Cache schema/status не ready, требуется rebuild | `stats_cache.py`, Settings page | Запустить cache rebuild, проверить статус и fallbackReason |
| В dev все выглядит нормально, а в Anki нет | `mockReport` замаскировал API проблему | `web-dashboard/src/app/App.tsx` | Проверить production dashboard через token URL |

## Dashboard/API/token problems

### Признаки

- `/api/report` возвращает `403`.
- Frontend показывает forbidden или сообщает о недействительном dashboard token.
- Actions, logs, settings или cache endpoints не выполняются.

### Вероятные причины

- Dashboard открыт не из текущего URL, сгенерированного server manager.
- Server был перезапущен, старый token сброшен.
- Token не передан в query string.

### Что проверить

- URL должен иметь вид `http://127.0.0.1:<port>/?token=<token>#/home`.
- `dashboard_server.py` создает token при `DashboardServerManager.start(...)`.
- Forbidden response подтвержден кодом: HTTP `403` с JSON
  `{"error":"invalid_dashboard_token","ok":false,...}`.

### Команды / файлы

```text
anki_study_report/dashboard_server.py
web-dashboard/src/app/App.tsx
web-dashboard/src/lib/actionsApi.ts
```

### Как исправлять безопасно

Открыть dashboard заново из Anki Study Report. Если проблема в тестах,
проверить, что тест передает актуальный token из `manager.url()`.

### Чего не делать

Не отключать token validation и не логировать полный URL с token.

## Старые dashboard assets после установки свежего `.ankiaddon`

### Признаки

- Новый archive собран, но в Anki видны старые CSS/JS.
- В package validation все pass, а ручная проверка не совпадает.

### Вероятные причины

- Anki не заменил старую папку add-on полностью.
- Dashboard server не перезапущен после установки.
- Проверяется старый `web_dashboard/assets`.

### Что проверить

- Installed add-on folder в `addons21`.
- Наличие свежего `web_dashboard/index.html` и assets внутри установленной
  папки.
- Package validator видит linked assets и CSS markers.

### Команды / файлы

```powershell
node scripts/run_python.mjs scripts/package_addon.py --check-only
```

```text
scripts/package_addon.py
anki_study_report/web_dashboard/
```

### Как исправлять безопасно

Удалить старую установленную папку add-on, установить свежий `.ankiaddon`,
перезапустить Anki и заново открыть/restart dashboard server.

### Чего не делать

Не править `anki_study_report/web_dashboard/` руками. Это generated output.

## Docker E2E startup/import/readiness failures

### Признаки

- `scripts/run_full_check.ps1 -DockerOnly` падает на wait/readiness.
- Нет `dashboard-ready.json`.
- Browser/API smoke не стартует.

### Вероятные причины

- Add-on установлен не в base-level `addons21`.
- Не создан base-level `prefs21.db`.
- Anki не импортировал add-on.
- Hook сработал, но report build/server publish упали.

### Что проверить

В первую очередь смотреть:

```text
e2e-artifacts/dashboard-ready.json
e2e-artifacts/addon-e2e-events.jsonl
e2e-artifacts/anki-data-tree.txt
e2e-artifacts/addons-tree.txt
e2e-artifacts/anki-startup-tail.txt
```

Ожидаемый add-on path внутри контейнера:

```text
/e2e/anki-data/addons21/anki_study_report_e2e
```

Ожидаемый profile DB:

```text
/e2e/anki-data/prefs21.db
```

Типовая цепочка markers:

```text
import_start
addon_folder_present
e2e_env_detected
hook_registered
import_done
hook_fired
bootstrap_scheduled
collection_available
report_build_start
report_build_done
server_start_start
server_start_done
report_publish_start
report_publish_done
readiness_write_start
readiness_write_done
```

### Команды / файлы

```powershell
.\scripts\run_full_check.ps1 -DockerOnly
.\scripts\run_full_check.ps1 -CleanDocker
```

```text
docker/anki-e2e/run-e2e.sh
docker/anki-e2e/wait-for-dashboard.py
docker/anki-e2e/start-anki.sh
anki_study_report/__init__.py
```

### Как исправлять безопасно

Идти по markers. Если нет `import_start`, проверять install layout. Если есть
import/hook, но нет readiness, проверять report build, `/api/health` и server
publish. Если нет профиля, проверять `bootstrap-prefs.py` и очистку volume.

### Чего не делать

Не переносить add-on под `/e2e/anki-data/E2E/addons21/...`.

## Cards page / preview / Shadow DOM / Anki-like preview failures

### Признаки

- Cards page есть, но preview пустой.
- Browser smoke падает на Shadow DOM preview host или answer-only секцию.
- Table/tiles проходят, а `ankiPreview` падает, или наоборот.

### Вероятные причины

- Активный display mode не совпадает с DOM selector.
- `renderedPreview` отсутствует или sanitizer удалил опасный HTML.
- Media refs нормализованы без token и frontend не добавил token.

### Что проверить

- `table` и `tiles` используют `AnkiCardShadowPreview` и
  `data-testid="anki-card-shadow-preview"`.
- `ankiPreview` использует `data-testid="anki-preview-answer"` и
  `AnkiCardShadowPreview` host с `data-shadow-preview-mode="preview"` /
  `data-preview-side="answer"`; штатный source - answer-only HTML из
  `renderedPreview.backHtml`, front отдельно не дублируется.
- Если `backHtml` отсутствует, ожидается diagnostic fallback внутри answer
  section, а не обычное отдельное front preview.
- `CardsPage.tsx` хранит display mode в
  `anki-study-report.cards.displayMode`.
- `cardAttention.ts` сначала нормализует canonical `attentionCards`, затем
  fallback aliases `cards`, `cardIssues`.

### Команды / файлы

```text
web-dashboard/src/pages/CardsPage.tsx
web-dashboard/src/components/AnkiCardShadowPreview.tsx
web-dashboard/src/lib/cardAttention.ts
docker/anki-e2e/smoke-browser.mjs
tests/test_note_intelligence.py
```

### Как исправлять безопасно

Сначала определить mode и фактическую DOM форму. Если sanitizer удалил HTML,
проверить, был ли HTML опасным. Для rendering/media изменений нужна проверка
выше unit tests: live Anki или Docker E2E.

### Чего не делать

Не ослаблять sanitizer ради красивого preview.

Не добавлять iframe или исполнение JS templates ради более похожего preview.

## Media preview failures

### Признаки

- `/api/media` возвращает `400 Invalid media name`.
- `/api/media` возвращает `404 Media not found`.
- В preview нет gif/audio.

### Вероятные причины

- Media name содержит `..`, slash, Windows path, URL scheme или неподдержанное
  расширение.
- Файл не найден через media provider.
- Token не добавлен к media URL.

### Что проверить

- `sanitize_media_filename(...)` в `note_intelligence.py`.
- `_safe_media_name(...)` в `dashboard_server.py`.
- Frontend `normalizeMediaRefs(...)` и добавление token в `CardsPage.tsx`.

### Команды / файлы

```text
tests/test_note_intelligence.py
tests/test_dashboard_server.py
web-dashboard/src/lib/cardAttention.ts
```

### Как исправлять безопасно

Использовать относительные Anki media names вроде `front.gif` или `voice.mp3`.
Проверить, что media URL остается `/api/media?name=...`, а token добавляется
только frontend-side при рендере.

### Чего не делать

Не разрешать `file:`, `http:`, `https:`, absolute paths или path traversal.

## Payload contract mismatch

### Признаки

- Python payload tests падают.
- TypeScript typecheck падает после backend изменения.
- Frontend показывает пустые блоки при наличии данных.

### Вероятные причины

- Изменился `dashboard_payload.py`, но не обновлен `report.ts`.
- Тестовая exact-форма устарела.
- Cache adapter отдал форму, отличающуюся от legacy contract.

### Что проверить

```text
anki_study_report/dashboard_payload.py
web-dashboard/src/types/report.ts
tests/test_dashboard_payload.py
web-dashboard/src/lib/cardAttention.test.ts
```

### Как исправлять безопасно

Сначала подтвердить фактический payload. Если production payload корректен, а
assertion устарел, править тест. Если меняется contract, обновить backend,
frontend types, normalizers, tests и `docs/dashboard-api.md`.

### Чего не делать

Не менять production payload только ради старого теста.

## Package validation failures

### Признаки

- `package_addon.py --check` возвращает non-zero.
- Missing linked dashboard assets.
- Forbidden entries или missing CSS markers.

### Вероятные причины

- Dashboard не пересобран.
- В архив попал `__pycache__`, `user_files`, `.pyc`, `tests`, `node_modules`.
- `web_dashboard/index.html` ссылается на отсутствующий asset.

### Что проверить

```powershell
cd web-dashboard
pnpm run build:addon
cd ..
node scripts/run_python.mjs scripts/package_addon.py --check
```

### Команды / файлы

```text
scripts/package_addon.py
tests/test_package_build.py
tests/test_package_artifact.py
tests/test_addon_structure.py
```

### Как исправлять безопасно

Пересобрать frontend assets через `build:addon`, удалить Python caches,
пересобрать archive. Если validator запрещает файл, сначала понять источник
этого файла, а не добавлять exception.

### Чего не делать

Не ослаблять package validator без причины.

## Cache/stale data/fallback behavior

### Признаки

- Settings page показывает `stale`, `empty`, `error`.
- Dashboard dataSource становится `legacy` или `mixed`.
- Период в dashboard не совпадает с ожидаемым.

### Вероятные причины

- Cache schema outdated.
- Cache еще building/scheduled.
- `use_stats_cache_for_report` выключен.
- Deck daily aggregates имеют ограничения current-deck history.

### Что проверить

```text
anki_study_report/stats_cache.py
anki_study_report/report_from_cache.py
anki_study_report/dashboard_payload.py
web-dashboard/src/pages/SettingsPage.tsx
```

### Как исправлять безопасно

Запустить refresh/rebuild через Settings page или `/api/cache/rebuild`. Если
cache adapter меняется, проверить, что публичный dashboard contract не меняется.

### Чего не делать

Не использовать cache-only форму как новый frontend contract без миграции типов
и тестов.

## Frontend dev mockReport masking real problems

### Признаки

- `pnpm run dev` показывает рабочий dashboard, но Anki dashboard падает.
- API недоступен, но UI все равно наполнен данными.

### Вероятные причины

В `import.meta.env.DEV` `App.tsx` подставляет `mockReport` для non-403 ошибок.

### Что проверить

```text
web-dashboard/src/app/App.tsx
web-dashboard/src/data/mockReport.ts
```

### Как исправлять безопасно

Для runtime проверки открывать dashboard из Anki с token и проверять real
`/api/report`.

### Чего не делать

Не считать dev mock успешной проверкой dashboard server/API.

## Что проверять в первую очередь

1. `git status --short --branch`.
2. Фактический endpoint/route/payload по коду.
3. `git diff --check`.
4. Минимальные тесты из `docs/test-matrix.md`.
5. Для runtime/rendering/startup - live Anki или Docker E2E.

## Что не делать

- Не ослаблять sanitizer.
- Не менять production payload ради устаревшего теста.
- Не править generated assets руками.
- Не коммитить runtime artifacts.
- Не логировать и не прикладывать token-bearing URL как обычный артефакт.
