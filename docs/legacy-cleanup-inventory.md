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
| Card payload aliases | `anki_study_report/dashboard_payload.py`, `web-dashboard/src/types/report.ts`, `web-dashboard/src/lib/cardAttention.ts`, `tests/test_attention_cards.py`, `web-dashboard/src/lib/cardAttention.test.ts` | Compatibility bridge | Backend сейчас публикует `attentionCards` и `attentionCardsStatus`; frontend предпочитает `attentionCards`, а `cards`, `cardIssues`, `problemCards` читает как fallback. | Доказать отсутствие старых producers/fixtures/users перед удалением aliases, обновить dashboard API docs и frontend tests. |
| Cache/report bridge | `anki_study_report/report_from_cache.py`, `anki_study_report/stats_cache.py`, `anki_study_report/dashboard_payload.py`, `anki_study_report/__init__.py` | Transitional adapter | Cache snapshot переводится в публичную форму отчета/dashboard без изменения внешнего контракта. | Проверить mixed/cache fallback, `dataSource`, `fallbackReason`, payload shape, Python tests и frontend consumption. |
| Markdown/HTML report | `anki_study_report/report_builder.py`, `anki_study_report/__init__.py`, `tests/test_report_builder.py` | Keep / Product decision | Отдельный пользовательский report surface: dialog, Markdown copy/export, HTML render. Dashboard не заменяет его автоматически. | Сначала решить product status; затем проверить UI dialog, report text, HTML render и tests. |
| Anki entrypoint/orchestration | `anki_study_report/__init__.py` | Keep | Anki hooks, dialogs, dashboard lifecycle, cache wiring, menu/actions, integration diagnostics. | Не рассматривать файл как legacy целиком. Извлекать только чистую логику с сохранением hook/runtime behavior. |
| Dashboard static fallback | `anki_study_report/dashboard_server.py`, `web-dashboard/dist/`, `anki_study_report/web_dashboard/` | Fallback/diagnostic | Сервер умеет сообщать о missing static assets и отдавать диагностическую страницу/статус вместо молчаливого blank dashboard. | Проверить `/api/status`, packaged asset path, fallback HTML, package validation, Stage 2 stale-asset guard. |
| Frontend `mockReport` | `web-dashboard/src/data/mockReport.ts`, `web-dashboard/src/app/App.tsx`, frontend tests/docs | Dev/test helper | В DEV dashboard может показать mock payload при ошибке загрузки `/api/report` не из-за 403. | Не считать production proof; держать fixture sanitized и синхронной с типами. |
| Cards rendering, sanitizer, media | `anki_study_report/note_intelligence.py`, `anki_study_report/dashboard_server.py`, `web-dashboard/src/pages/CardsPage.tsx`, `web-dashboard/src/components/AnkiCardShadowPreview.tsx`, `docker/anki-e2e/smoke-browser.mjs` | Keep | Shadow DOM preview, sanitized HTML, token-protected local media and mode-specific Cards behavior. | Не возвращать iframe/JS execution, не ослаблять sanitizer, проверять real Anki/Docker/browser smoke. |
| Generated/runtime outputs | `e2e-artifacts/`, `web-dashboard/dist/`, `web-dashboard/screenshots/`, `anki_study_report/web_dashboard/`, `anki_study_report/user_files/`, `*.ankiaddon`, `__pycache__/`, `.pytest_cache/`, `node_modules/` | Generated/runtime | Локальные outputs сборки, тестов, package и runtime. | Не коммитить; чистить через build/test hygiene. Package validator остается guard. |
| Build/package pipeline | `scripts/package_addon.py`, `scripts/run_full_check.ps1`, `build_ankiaddon.ps1`, `web-dashboard/package.json` | Keep / Transitional risk | Сборка dashboard assets, package validation, full-check/Docker gates. | Не ослаблять `build:addon` и package checks; при изменениях запускать package validation или полный build. |
| Placeholder/simple dashboard pages | `web-dashboard/src/pages/StatsPage.tsx`, `web-dashboard/src/pages/FsrsPage.tsx`, `web-dashboard/src/pages/BrowsePage.tsx`, `web-dashboard/src/pages/IntegrationsPage.tsx`, `web-dashboard/src/app/router.tsx` | Product decision | `Stats`, `FSRS`, `Browse` сейчас placeholder/simple pages. `Integrations` - легкий read-only status surface через `/api/integrations/status`. | Решить, развивать ли routes или убрать из nav; обновить router/nav/frontend-map/tests. |
| Possible dead-code helpers | См. раздел ниже | Candidate for verification | Имена найдены статическим поиском как слабо используемые или только определенные. | Подтвердить runtime отсутствием вызовов, добавить targeted regression test, затем удалять узким commit. |

## Детали по областям

### Card payload aliases

`attentionCards` - текущий backend ключ для карточек внимания. Frontend helper
`buildCardAttentionRows(report)` читает несколько возможных ключей:

```text
attentionCards
cards
cardIssues
problemCards
```

Это выглядит как legacy surface, но пока является compatibility bridge. Он
защищает Cards page от старых fixtures, тестовых payload и возможных сохраненных
JSON samples. Удаление aliases может сломать не backend, а frontend preview,
offline/manual fixtures или старые тестовые сценарии.

Текущий приоритет после Stage 5:

```text
attentionCards > cards > cardIssues > problemCards
```

`attentionCards: []` считается явным canonical source и не fallback-ит к legacy
aliases; это сохраняет смысл "карточек внимания нет" в backend payload.

Detailed Stage 6 evidence map: `docs/card-alias-audit.md`.

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

| Символ | Файл | Почему кандидат | Перед удалением |
| --- | --- | --- | --- |
| `_deck_names_from_rows` | `anki_study_report/dashboard_payload.py` | Поиск по source/tests/docs показал только definition. | Проверить cache/deck summary планы, добавить payload regression test. |
| `_rendered_preview_fallback` | `anki_study_report/metrics.py` | Поиск показал только definition. | Проверить native preview fallback и Cards smoke, не ломать renderedPreview contract. |
| `_append_av_media_html` | `anki_study_report/note_intelligence.py` | Поиск показал только definition. | Проверить media/AV rendering paths и APKG fixture behavior. |
| `build_short_report` | `anki_study_report/report_builder.py` | Поиск показал definition без явного current caller. | Проверить UI/import history и report tests; не удалять вместе с report surface. |
| `build_detailed_report` | `anki_study_report/report_builder.py` | Поиск показал definition без явного current caller. | Проверить UI/import history и report tests; не удалять вместе с report surface. |
| `revlog_id_ms_to_local_day` | `anki_study_report/stats_cache.py` | Поиск показал definition без явного current caller. | Проверить rollover/date utilities и cache migration expectations. |
| `_integration_diagnostics_text` | `anki_study_report/__init__.py` | Поиск показал definition без явного current caller. | Проверить diagnostics dialog/export plans и Anki menu path. |

Если кандидат удаляется, commit должен быть narrow: один helper или одна
маленькая группа с одинаковым доказательством. Не смешивать с runtime refactor.

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

- `web-dashboard/src/lib/cardAttention.test.ts` covers `attentionCards`,
  `cards`, `cardIssues`, `problemCards`, snake_case row fields, and the current
  mixed-key precedence after Stage 5: `attentionCards` > `cards` >
  `cardIssues` > `problemCards`. Empty canonical `attentionCards: []` also wins
  over legacy aliases.
- `tests/test_dashboard_payload.py` covers canonical backend output keys:
  `attentionCards`, `attentionCardsStatus`, `noteTypeCatalog`, and absence of
  frontend legacy aliases in backend-generated payload.
- `tests/test_stats_cache.py` covers `report_from_cache.py` fallback/mixed
  adapter shape, `dataSource`, `fallbackReason`, `periodSummary`,
  `cacheDeckSummary`, parity diagnostics, and preserving live-only fields during
  cache merge.
