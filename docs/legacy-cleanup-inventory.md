# Legacy cleanup inventory

Снимок: 2026-07-06.

Этот документ - карта мест, которые выглядят как legacy, fallback,
compatibility layer или cleanup-кандидаты. Это не список на удаление. Его цель -
сначала сохранить контракт и контекст, а уже потом помогать точечно чистить код.

Перед любым удалением или упрощением нужно доказать, что слой больше не нужен
текущему add-on runtime, dashboard payload, packaged artifact, Docker E2E и
пользовательским отчетам.

## Статусы

| Статус | Что означает | Правило |
| --- | --- | --- |
| Keep | Текущий runtime/source-of-truth. | Не удалять; менять только через обычные тесты и docs. |
| Compatibility bridge | Поддерживает старые или альтернативные формы данных. | Сначала characterization tests, потом staged deprecation. |
| Transitional adapter | Связывает новый внутренний слой со старым публичным контрактом. | Не менять публичную форму данных без frontend/tests/docs. |
| Fallback/diagnostic | Нужен для понятной деградации или диагностики. | Удалять только если есть эквивалентная замена. |
| Dev/test helper | Не production surface, но нужен разработке или тестам. | Не использовать как доказательство production behavior. |
| Generated/runtime | Производный или локальный output. | Не править руками и не коммитить. |
| Candidate for verification | Похоже на неиспользуемый код по статическому поиску. | Не удалять без targeted проверки и теста. |
| Product decision | Вопрос не технический, а продуктовый. | Сначала решить, нужна ли функция/route пользователю. |

## Короткий инвентарь

| Область | Файлы | Статус | Текущее назначение | Что проверить перед cleanup |
| --- | --- | --- | --- | --- |
| Card payload aliases | `anki_study_report/dashboard_payload.py`, `web-dashboard/src/types/report.ts`, `web-dashboard/src/lib/cardAttention.ts`, `tests/test_attention_cards.py`, `web-dashboard/src/lib/cardAttention.test.ts` | Keep / cleanup complete | Backend публикует `attentionCards` и `attentionCardsStatus`; frontend принимает `attentionCards` как единственный card-level payload key. `problemCards` удален в Stage 9, `cardIssues` - в Stage 10, `cards` - в Stage 11. | Сохранять canonical contract tests и negative tests для удаленных aliases, пока cleanup line не устаканится. |
| Cache/report bridge | `anki_study_report/report_from_cache.py`, `anki_study_report/stats_cache.py`, `anki_study_report/dashboard_payload.py`, `anki_study_report/__init__.py`, `scripts/smoke_report_cache_adapter.py`, `scripts/smoke_report_cache_merge.py` | Transitional adapter | Cache snapshot переводится в публичную форму отчета/dashboard без изменения внешнего контракта. `report_from_cache.py` overlays only selected cache-backed sections and preserves live-only fields. | Проверить mixed/cache fallback, `dataSource`, `fallbackReason`, `periodSummary`, `cacheDeckSummary`, payload shape, Python tests, smoke scripts и frontend consumption. |
| Markdown/HTML report | `anki_study_report/report_builder.py`, `anki_study_report/__init__.py`, `tests/test_report_builder.py` | Keep / Product decision | Отдельный пользовательский report surface: dialog, Markdown copy/export, HTML render. Dashboard не заменяет его автоматически. | Сначала решить product status; затем проверить UI dialog, report text, HTML render и tests. |
| Anki entrypoint/orchestration | `anki_study_report/__init__.py` | Keep | Anki hooks, dialogs, dashboard lifecycle, cache wiring, menu/actions, integration diagnostics. | Не рассматривать файл как legacy целиком. Извлекать только чистую логику с сохранением hook/runtime behavior. |
| Dashboard static fallback | `anki_study_report/dashboard_server.py`, `scripts/package_addon.py`, `build_ankiaddon.ps1`, `scripts/run_full_check.ps1`, `web-dashboard/dist/`, `anki_study_report/web_dashboard/` | Fallback/diagnostic | Сервер умеет сообщать о missing static assets и отдавать диагностическую страницу/статус вместо молчаливого blank dashboard. Package validation проверяет linked assets и CSS markers. | Проверить `/api/status`, packaged asset path, fallback HTML, package validation, Stage 2 stale-asset guard. |
| Frontend `mockReport` | `web-dashboard/src/data/mockReport.ts`, `web-dashboard/src/app/App.tsx`, frontend tests/docs | Dev/test helper | В DEV dashboard может показать mock payload при ошибке загрузки `/api/report` не из-за 403. | Не считать production proof; держать fixture sanitized и синхронной с типами. |
| Cards rendering, sanitizer, media | `anki_study_report/note_intelligence.py`, `anki_study_report/dashboard_server.py`, `web-dashboard/src/pages/CardsPage.tsx`, `web-dashboard/src/components/AnkiCardShadowPreview.tsx`, `docker/anki-e2e/smoke-browser.mjs` | Keep | Shadow DOM preview, sanitized HTML, token-protected local media and mode-specific Cards behavior. | Не возвращать iframe/JS execution, не ослаблять sanitizer, проверять real Anki/Docker/browser smoke. |
| Generated/runtime outputs | `e2e-artifacts/`, `web-dashboard/dist/`, `web-dashboard/screenshots/`, `anki_study_report/web_dashboard/`, `anki_study_report/user_files/`, `*.ankiaddon`, `__pycache__/`, `.pytest_cache/`, `node_modules/` | Generated/runtime | Локальные outputs сборки, тестов, package и runtime. | Не коммитить; чистить через build/test hygiene. Package validator остается guard. |
| Build/package pipeline | `scripts/package_addon.py`, `scripts/run_full_check.ps1`, `build_ankiaddon.ps1`, `web-dashboard/package.json` | Keep / Transitional risk | Сборка dashboard assets, package validation, full-check/Docker gates. | Не ослаблять `build:addon` и package checks; при изменениях запускать package validation или полный build. |
| Placeholder/simple dashboard pages | `web-dashboard/src/pages/StatsPage.tsx`, `web-dashboard/src/pages/FsrsPage.tsx`, `web-dashboard/src/pages/BrowsePage.tsx`, `web-dashboard/src/pages/IntegrationsPage.tsx`, `web-dashboard/src/app/router.tsx` | Product decision | `Stats`, `FSRS`, `Browse` сейчас placeholder/simple pages. `Integrations` - легкий read-only status surface через `/api/integrations/status`. | Решить, развивать ли routes или убрать из nav; обновить router/nav/frontend-map/tests. |
| Possible dead-code helpers | См. раздел ниже | Candidate for verification | Имена найдены статическим поиском как слабо используемые или только определенные. | Подтвердить runtime отсутствием вызовов, добавить targeted regression test, затем удалять узким commit. |

## Stage 12 audit snapshot

Stage 12 проверил cleanup-поверхность вокруг cache/report fallback,
dashboard/static diagnostics, Markdown/HTML report, frontend dev fallback,
placeholder routes и security boundaries. Вывод: это audit/prep stage, не
массовое удаление.

### Cache/report bridge snapshot

| Слой | Текущий статус | Доказательство | Cleanup-риск | Рекомендация |
| --- | --- | --- | --- | --- |
| `report_from_cache.py` | Transitional adapter | `build_cached_report_parts` возвращает `mixed` только для cache-backed `activity`/`comparison`; fallback возвращает `legacy` с `fallbackReason`. `merge_cached_report_parts` не стирает live-only поля. | Высокий: легко изменить публичный report shape или потерять live-only `attentionCards`/`forecast`. | Не удалять целиком. Следующий stage - characterization/hardening вокруг merge/fallback, если нужно менять adapter. |
| `stats_cache.py` | Keep | `StatsCacheManager` хранит schema/status/snapshot; tests покрывают status, rebuild, mixed/fallback shape. | Высокий: cache schema и readiness влияют на dashboard Settings и report fallback. | Чистить только узкими cache-schema-aware patches. |
| `dashboard_payload.py` | Keep / public contract mapper | Backend экспортирует canonical `attentionCards` и `attentionCardsStatus`; cache snapshot явно дает empty card-level payload с diagnostic reason. | Высокий: frontend/API contract и card-level diagnostics. | Не менять payload keys без backend, frontend, smoke и docs вместе. |
| `__init__.py` cache wiring | Keep / orchestration | Импортирует `build_cached_report_parts`/`merge_cached_report_parts`, публикует dashboard report, отдает cache status/settings. | Высокий: Anki hooks, menu/dialogs, dashboard lifecycle. | Не считать файл legacy целиком; извлекать только чистую логику с live/Docker smoke. |
| Cache smoke scripts | Keep / characterization | `scripts/smoke_report_cache_adapter.py` и `scripts/smoke_report_cache_merge.py` проверяют JSON safety, mixed/fallback и сохранение live-only полей. | Средний: scripts могут устареть относительно tests, но полезны как быстрый внешний smoke. | Сохранять или обновлять вместе с cache adapter changes. |

### Dashboard fallback/static snapshot

| Слой | Текущий статус | Доказательство | Cleanup-риск | Рекомендация |
| --- | --- | --- | --- | --- |
| Static lookup | Fallback/diagnostic | `_find_static_dir()` ищет packaged `anki_study_report/web_dashboard` и dev `web-dashboard/dist`. | Средний: неправильный путь дает blank dashboard. | Не удалять dev/package lookup без package and dashboard smoke. |
| Built-in dashboard | Fallback/diagnostic | Если static assets отсутствуют, server отдает встроенную HTML diagnostics page вместо silent blank. | Средний: fallback помогает неполным checkout/package installs. | Не удалять без равной diagnostic replacement. |
| `/api/status` and server status | Keep / diagnostics | State включает `static_available`, `static_dir`, `report_available`, port collision и lifecycle details. | Средний: Settings/server pages и troubleshooting используют эти признаки. | Сохранять поля или менять синхронно с frontend/docs. |
| Package validator | Keep / release guard | `scripts/package_addon.py` проверяет required entries, linked dashboard assets, empty/unreferenced assets и CSS markers. | Высокий: ослабление вернет stale/missing assets в `.ankiaddon`. | Не ослаблять; при изменениях запускать package validation. |

### Stage 13 dashboard static fallback snapshot

Stage 13 hardened dashboard static diagnostics without deleting fallback
surface. Runtime static lookup now treats a directory as available only when:

- `index.html` exists;
- local linked `assets/...` script/stylesheet files from `index.html` stay
  inside the static root;
- those linked files exist and are non-empty.

Packaged static path still wins over dev `web-dashboard/dist` when both are
complete. If packaged assets are incomplete, server can fall through to a
complete dev build. If neither static directory is complete, `/api/status`
reports `static_available=false`, `static_dir=null`, and the root route serves
the built-in fallback page with a visible fallback diagnostic. The status
payload keeps token-bearing URL redacted.

Package validation remains the release guard for archives: required
`web_dashboard/index.html`, linked JS/CSS assets, empty linked assets,
unreferenced dashboard assets, forbidden entries and CSS markers are still
checked by `scripts/package_addon.py`.

### Stage 14 cache/report bridge characterization snapshot

Stage 14 kept the cache/report bridge as a transitional adapter and narrowed the
contract around its diagnostics. `report_from_cache.py` now carries cache status
diagnostics into the report `cache` summary: `version`, `isBuilding`, `error`
and `lastError` travel with `status`, counts and `fallbackReason`. Error text is
kept to a single short line for dashboard safety.

The characterization boundary is:

- fallback returns `dataSource=legacy`, empty `usedFor`, `fallbackReason` and
  `cacheDebug.reason`;
- mixed cache can overlay only `cache`, `cacheDebug`, `performance`,
  `activity` and `comparison`;
- live-only report fields such as `metadata`, `attentionCards`,
  `attentionCardsStatus`, `noteTypeCatalog`, `forecast` and `recommendations`
  remain owned by the live payload path;
- removed card aliases `cards`, `cardIssues` and `problemCards` must not be
  reintroduced by cache merge.

Tests and smoke scripts now cover these boundaries:

```text
tests/test_stats_cache.py
scripts/smoke_report_cache_adapter.py
scripts/smoke_report_cache_merge.py
```

### Markdown/HTML report snapshot

`report_builder.py` не legacy целиком. `build_markdown_report` и
`render_html_report` вызываются из `StudyReportDialog`, clipboard/export paths
и dashboard publish context. `build_short_report` и `build_detailed_report`
выглядят как тонкие wrappers без текущего caller по source search, но их нельзя
удалять вместе с пользовательской report surface.

Минимум для future cleanup report wrappers: targeted search, import/API
decision, `tests/test_report_builder.py`, и live/manual report window check,
если меняется dialog path.

### Frontend dev fallback snapshot

`web-dashboard/src/app/App.tsx` подставляет `mockReport` только в
`import.meta.env.DEV` и только для non-403 `/api/report` errors. `403` остается
настоящей forbidden state. `mockReport.ts` - dev/test helper, а не production
proof. Fixture должен оставаться sanitized и synchronized с
`web-dashboard/src/types/report.ts`.

### Placeholder routes snapshot

`StatsPage`, `FsrsPage` и `BrowsePage` - product decision, а не dead code по
одному факту placeholder UI. Они подключены через router/navigation и ведут к
существующим dashboard areas. `IntegrationsPage` не placeholder: он читает
token-protected `/api/integrations/status` и показывает read-only diagnostics.

### Security boundary snapshot

Token-protected local server, `secrets.compare_digest`, `/api/media`
sanitization, action allowlists, Shadow DOM preview, media URL normalization и
no iframe/JS execution являются safety boundary. Их нельзя относить к legacy
cleanup. Любое упрощение требует точечных security/regression tests и, для
Cards/media, browser or Docker smoke.

## Детали по областям

### Card payload aliases

`attentionCards` - текущий и единственный supported backend/frontend ключ для
карточек внимания. Frontend helper `buildCardAttentionRows(report)` читает:

```text
attentionCards
```

Legacy aliases больше не являются runtime compatibility surface. Обычные слова
`cards`, `newCards`, `cardsTotal`, `candidateCards`, `fieldScanCards` и Cards UI
остаются нормальными не-alias usage.

Текущий contract после Stage 11:

```text
attentionCards
```

`attentionCards: []` считается явным canonical source; это сохраняет смысл
"карточек внимания нет" в backend payload.

Detailed alias evidence and readiness map: `docs/card-alias-audit.md`.
Stage 8 aligned Docker browser/API smoke to canonical-first lookup.
Stage 9 removed the top-level `problemCards` payload alias from frontend
normalization, TS types, Docker API smoke fallback, and compatibility tests.
Stage 10 removed the top-level `cardIssues` payload alias from frontend
normalization, TS types, Docker API smoke fallback, and compatibility tests.
Stage 11 removed the top-level `cards` payload alias from frontend
normalization, TS types, Docker API/browser smoke fallback, and compatibility
tests.

Cleanup path:

1. Добавить/сохранить tests, которые явно фиксируют новый canonical key.
2. Проверить fixtures и docs на старые ключи.
3. Если старые keys больше не нужны, удалить aliases одним узким commit.
4. Обновить `docs/dashboard-api.md`, `docs/frontend-map.md` и frontend tests.

### Cache/report bridge

`report_from_cache.py` не стоит считать "старым отчетом" только из-за слова
cache/fallback. Это adapter между `StatsCacheManager` и публичной формой отчета.
Он важен потому, что внутреннее хранение статистики может меняться быстрее, чем
dashboard/API contract.

Особенно рискованные поля:

```text
dataSource
fallbackReason
attention_cards / attentionCards
forecast / forecast_status
deck_stats
```

Cleanup здесь должен доказывать, что новый путь дает ту же публичную форму
данных для frontend и Markdown/HTML report. Если cache snapshot неполный, лучше
сохранить явный diagnostic/fallback, чем молча подставлять пустые данные.

### Markdown/HTML report

`report_builder.py` и `StudyReportDialog` остаются отдельной пользовательской
поверхностью. Dashboard не делает их автоматически legacy. Пользователь может
использовать Markdown copy/export, HTML preview или Anki dialog без открытия
dashboard.

Перед любым упрощением:

- проверить `tests/test_report_builder.py`;
- проверить вызовы `build_markdown_report` и `render_html_report` из
  `__init__.py`;
- вручную подтвердить, что report window больше не нужен, если планируется
  removal;
- не удалять `report_builder.py` целиком ради "dashboard-only" чистки.

### Anki entrypoint/orchestration

`anki_study_report/__init__.py` большой, но это не доказательство legacy. Сейчас
это adapter/orchestration layer:

- регистрация Anki hooks;
- menu/actions;
- report dialogs;
- dashboard server lifecycle;
- cache wiring;
- integration diagnostics;
- profile close/main window close cleanup.

Хороший cleanup здесь - перенос чистой логики в отдельные модули без изменения
runtime hooks. Плохой cleanup - удалить или "упростить" hook/menu/server paths
без Docker/live smoke.

### Dashboard static fallback

`dashboard_server.py` ищет static assets в packaged path
`anki_study_report/web_dashboard/` и dev path `web-dashboard/dist/`. Missing или
stale assets должны быть диагностируемыми. Stage 2 закрепил, что full check
валидирует fresh dashboard assets перед package validation.

После Stage 13 static directory считается доступной не только по наличию
`index.html`, но и по linked local `assets/...` из этого `index.html`: они
должны существовать, оставаться внутри static root и быть non-empty. Это
закрывает blank-dashboard риск для неполного generated bundle.

Не удалять fallback HTML/status только потому, что normal path работает. Эта
диагностика нужна, когда packaged artifact собран без свежего frontend build или
когда пользователь запускает add-on из неполного checkout.

### Frontend mock report

`mockReport.ts` - DEV/test fixture. В `App.tsx` он используется только для DEV
fallback, когда `/api/report` не загрузился и ошибка не 403. Это удобно для
frontend разработки, но может скрывать backend/API проблему в dev-среде.

Правило: fixture должен совпадать с типами и не содержать token/private data,
но успешный render `mockReport` не является доказательством production dashboard.

### Cards rendering, sanitizer, media

Эта область не legacy-cleanup, а safety/runtime contract. Текущий Cards preview:

- `table` и `tiles` показывают front-only Shadow DOM preview;
- `ankiPreview` показывает answer-only `AnkiCardShadowPreview` из
  `renderedPreview.backHtml`;
- iframe не используется;
- JS из шаблонов не выполняется;
- note CSS живет внутри Shadow DOM host;
- media идет через локальный token-protected server path.

Cleanup в этой зоне требует browser smoke или Docker E2E, потому что unit tests
легко пропускают реальное поведение Anki templates/media.

### Generated/runtime outputs

Эти пути не являются source code:

```text
e2e-artifacts/
web-dashboard/dist/
web-dashboard/screenshots/
anki_study_report/web_dashboard/
anki_study_report/user_files/
anki_study_report.ankiaddon
*.zip
__pycache__/
.pytest_cache/
node_modules/
```

Их появление в `git status --ignored` нормально. Их появление в staged files -
почти всегда ошибка. Чистить их можно локально, но не использовать как основу
для архитектурных выводов.

### Build/package pipeline

`scripts/package_addon.py` и `build_ankiaddon.ps1` являются guard rail для
релизного артефакта. Они проверяют форму архива, запрещенные outputs и наличие
dashboard assets. `scripts/run_full_check.ps1` добавляет Docker E2E и smoke
режимы.

Упрощение build pipeline без эквивалентной проверки может снова привести к
stale assets внутри `.ankiaddon`. Для package/build changes минимальная
проверка:

```powershell
node scripts/run_python.mjs scripts/package_addon.py --check
```

Для релизного confidence:

```powershell
.\build_ankiaddon.ps1
```

### Placeholder/simple dashboard pages

`StatsPage`, `FsrsPage` и `BrowsePage` сейчас описаны как placeholder/simple
pages. Это не баг, но и не "мертвый код" автоматически: routes могут быть частью
ожидаемой навигации и будущего UX.

`IntegrationsPage` не placeholder: она читает `/api/integrations/status` и
показывает read-only диагностику. Убирать ее можно только вместе с backend route
и docs/tests.

## Candidate for verification

Следующие имена стоит проверять отдельно перед удалением. Статический поиск
показывает слабое использование или только definition, но это не доказывает, что
runtime path невозможен.

| Symbol | File | Current references | Likely classification | Runtime risk | Tests that would catch removal | Recommendation | Suggested future stage |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `_deck_names_from_rows` | `anki_study_report/dashboard_payload.py` | Source search shows definition only. | Candidate for verification | Low/medium: helper is isolated, but deck naming affects cache/deck summary if reintroduced. | `tests/test_dashboard_payload.py`; targeted payload fixture around deck summary. | Verify no planned cache/deck caller, then remove in a narrow helper-only commit. | Stage 16 verified helper cleanup |
| `_rendered_preview_fallback` | `anki_study_report/metrics.py` | Source search shows definition only. | Candidate for verification | Medium/high: Cards preview fallback contract is user-visible and safety-sensitive. | `tests/test_attention_cards.py`, `web-dashboard/src/lib/cardAttention.test.ts`, Docker/browser Cards smoke. | Do not remove in generic cleanup; first prove native preview fallback path cannot call it. | Stage 16 verified helper cleanup |
| `_append_av_media_html` | `anki_study_report/note_intelligence.py` | Source search shows definition only. | Candidate for verification | Medium/high: media/AV rendering touches sanitizer and APKG fixture behavior. | `tests/test_note_intelligence.py`, APKG/Docker Cards smoke with media fixture. | Keep until a media-specific audit proves no hidden AV path depends on equivalent behavior. | Stage 16 verified helper cleanup |
| `build_short_report` | `anki_study_report/report_builder.py` | Source search shows definition only; `build_report(..., "short")` still supports the template. | Candidate for verification / public helper decision | Medium: external/import usage is possible and report surface remains user-facing. | `tests/test_report_builder.py`; import/API compatibility check; manual report dialog only if UI path changes. | Decide whether helper wrappers are public API; do not remove with Markdown/HTML report cleanup. | Stage 16 verified helper cleanup |
| `build_detailed_report` | `anki_study_report/report_builder.py` | Source search shows definition only; `build_report(..., "detailed")` still supports the template. | Candidate for verification / public helper decision | Medium: external/import usage is possible and report surface remains user-facing. | `tests/test_report_builder.py`; import/API compatibility check; manual report dialog only if UI path changes. | Decide whether helper wrappers are public API; do not remove with Markdown/HTML report cleanup. | Stage 16 verified helper cleanup |
| `revlog_id_ms_to_local_day` | `anki_study_report/stats_cache.py` | Source search shows definition only. | Candidate for verification | Medium: date/rollover utility sits near cache schema and historical aggregation. | `tests/test_stats_cache.py`; targeted rollover/day-boundary test if removed or replaced. | Verify no migration/read path needs it, then remove separately or add coverage if kept. | Stage 16 verified helper cleanup |
| `_integration_diagnostics_text` | `anki_study_report/__init__.py` | Source search shows definition only; integration diagnostics UI/status still exists elsewhere. | Candidate for verification | Low/medium: diagnostics are user-visible but helper appears disconnected. | Integration status smoke or targeted test around `_integration_status_response`; manual diagnostics dialog if UI changes. | Verify no menu/dialog path references it dynamically, then remove in a diagnostics-only commit. | Stage 16 verified helper cleanup |

Если кандидат удаляется, commit должен быть narrow: один helper или одна
маленькая группа с одинаковым доказательством. Не смешивать с runtime refactor.

## Recommended next stages

1. Stage 14: cache/report bridge characterization. Focus:
   `report_from_cache.py`, `StatsCacheManager`, `dataSource`, `fallbackReason`,
   `periodSummary`, `cacheDeckSummary`, and live-only field preservation.
2. Stage 15: placeholder route product decision. Decide whether `Stats`,
   `FSRS`, and `Browse` should be developed, hidden, or removed from nav.
3. Stage 16: verified helper cleanup. One helper or one tightly related helper
   group per commit, with targeted tests before deletion.
4. Stage 17: security boundary review only if a concrete change is needed.
   Treat token, media sanitizer, action allowlists and Cards rendering as
   protected runtime boundaries.

## Что не считать legacy

- `anki_study_report/__init__.py` целиком: это runtime adapter, а не просто
  исторический файл.
- `report_builder.py` целиком: Markdown/HTML report остается user-facing.
- `report_from_cache.py` целиком: это adapter, который сохраняет внешний
  payload/report contract.
- Sanitizer, Shadow DOM preview, tokenized media routes: это safety boundary.
- `package_addon.py` и build validators: это release guard rail.
- Generated dashboard assets в `anki_study_report/web_dashboard/`: это
  package output, не source, но он должен существовать внутри `.ankiaddon`.

## Cleanup rules

1. Сначала определить тип слоя: compatibility, fallback, adapter, generated,
   helper или product decision.
2. Не удалять compatibility/fallback слой без теста, который фиксирует новый
   desired behavior.
3. Не менять dashboard payload без синхронного обновления:

```text
anki_study_report/dashboard_payload.py
web-dashboard/src/types/report.ts
tests/test_dashboard_payload.py
web-dashboard/src/lib/*.test.ts
docs/dashboard-api.md
```

4. Для Cards/rendering/media изменений нужен browser/Docker/live smoke, а не
   только unit tests.
5. Для package/build изменений запускать package validation как минимум.
6. Для docs-only inventory updates достаточно `git diff --check` и ссылочной
   проверки.

## Suggested verification matrix

| Cleanup type | Minimum verification |
| --- | --- |
| Payload alias removal | Python payload tests, frontend cardAttention tests, dashboard API docs update. |
| Cache adapter cleanup | `node scripts/run_python.mjs -m pytest tests/test_stats_cache.py tests/test_dashboard_payload.py`, targeted frontend build/test if payload changes. |
| Report builder cleanup | `node scripts/run_python.mjs -m pytest tests/test_report_builder.py` plus manual/live report window if UI path changes. |
| Cards rendering/media cleanup | Frontend Cards tests plus Docker/browser smoke with APKG fixture. |
| Dashboard static/build cleanup | `pnpm run build:addon`, `node scripts/run_python.mjs scripts/package_addon.py --check`, and full build for release. |
| Placeholder route cleanup | Router/nav tests, `docs/frontend-map.md`, screenshots/smoke if visible navigation changes. |
| Pure docs inventory update | `git diff --check`, link search for `legacy-cleanup-inventory`. |

## Current characterization coverage

Stage 4 added targeted tests for the compatibility bridge; Stage 5 changed the
frontend priority to canonical-first:

- `web-dashboard/src/lib/cardAttention.test.ts` covers canonical
  `attentionCards`, snake_case row fields, mixed canonical-plus-removed-alias
  payloads, and the current Stage 11 contract: `attentionCards` only. Empty
  canonical `attentionCards: []` remains explicit, and `cards`-only /
  `problemCards`-only / `cardIssues`-only payloads are ignored.
- `tests/test_dashboard_payload.py` covers canonical backend output keys:
  `attentionCards`, `attentionCardsStatus`, `noteTypeCatalog`, and absence of
  frontend legacy aliases in backend-generated payload.
- `tests/test_stats_cache.py` covers `report_from_cache.py` fallback/mixed
  adapter shape, `dataSource`, `fallbackReason`, `periodSummary`,
  `cacheDeckSummary`, parity diagnostics, and preserving live-only fields during
  cache merge.
