# C2 — Core 1.0 Hardening and C1 UI Remediation

**Дата:** 2026-07-22

**Base:** `origin/core` at `1e7beafae16c6259ad6e93f393cda39bd9449dbb`

**Branch:** `c2-core-hardening-ui-remediation`

**Scope:** targeted remediation известных C1 findings; без C1.6B, новых функций, merge, release и deployment

## Исходные evidence

Фактически открыты входные отчёты:

- `C1_FINAL_CODE_AND_SECURITY_REPORT.md`;
- `C1_UI_UX_FINAL_REPORT.md`.

Каждый finding был повторно сопоставлен с текущим production path от exact base. Новый полный security или UI audit не выполнялся.

## Реализация

- Полный card stylesheet проходит parser-backed allowlist, selector scoping и safe local media rewrite; dashboard отправляет CSP и защитные headers.
- Exact-card recheck использует authority только релевантного note type и прежних profile-dependent reasons.
- Query generation, inspect generation и non-abortable mutation operation разделены; cache ограничен и не пересекает refresh.
- Search сохраняет `O(cap)` add-on memory после native result, сериализует широкие queries и честно фиксирует upstream materialization.
- Публичный status минимален, подробный status token-protected, failed auth не продлевает idle lifetime.
- Cards и Inspection Profiles используют общие surface/type/spacing/action/state roles и переработанную hierarchy без изменения product model.

## Finding ledger — technical/security

| ID | Status | Old root cause | Changed files | New invariant | Tests/evidence | Residual risk | Release blocker closed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `U-C1-001` | fixed | Полный CSS типа заметки проходил regex denylist и попадал в Shadow DOM | `card_css_policy.py`, `note_intelligence.py`, `dashboard_server.py`, vendored `tinycss2`/`webencodings`, preview/package tests | Parser grammar, allowlist, `.card` scope, bounded fail-closed output, safe local media; CSP default deny | 146 focused Python tests; 11 preview tests; package validation; malicious/obfuscated grammar fixtures | Runtime browser request capture и exact-package real-Anki являются integration evidence | yes |
| `U-C1-002` | fixed | Aggregate health всех profiles использовался как authority exact card | `exact_card_authority.py`, `inspection_profile_service.py`, `triage_service.py` и tests | Учитываются exact note type и только reasons, зависящие от profile authority | 73 authority/profile/triage tests; дополнительно 30 profile/triage tests; обязательный A/B scenario | Нет известного residual в изменённой границе | yes |
| `U-C1-003` | fixed | Busy-state mutation принадлежал query generation и исчезал после refresh/scope change | `cardsWorkspacePolicy.ts`, `useCardsTriageWorkspace.ts`, `CardsPage.tsx` и tests | Non-abortable operation живёт до фактического completion независимо от чтений; конфликтующие actions блокированы | Deferred-promise regression suite, 25 focused и 21 integration frontend tests | Native completion всё ещё может быть долгим; UI честно остаётся busy | yes |
| `U-C1-004` | fixed | Inspect cache мог восстановить preview предыдущей generation | те же workspace policy/hook/page files | Cache generation-keyed, max 50, очищается на refresh/scope; stale completion игнорируется | Deferred refresh/deck/stale-completion/cache-bound tests | Нет persistence между reload, что соответствует контракту | yes |
| `U-C1-005` | mitigated with residual risk | Полный native ID result затем копировался в дополнительные full-size set/sort structures | `search_service.py`, `search_runtime.py`, benchmark и tests | После native return хранится не более cap лучших unique IDs; один широкий query одновременно; exact inspect отдельно | 100 000 IDs: 246.96 ms, 406 680 bytes peak, бюджеты 500 ms/2 MiB | Anki `find_cards/find_notes` уже возвращает полную `Sequence` и не имеет limit/streaming API | yes |
| `U-C1-006` | mitigated with residual risk | Authority, orchestration и projection были сцеплены в широких модулях | `exact_card_authority.py`, `cardsWorkspacePolicy.ts`, `_SearchQueryGate` | Доказанные policy seams чистые и отдельно тестируются; broad rewrite не выполнен | Pure-policy unit tests и integration regressions | Legacy services остаются широкими вне доказанных seams | yes |
| `U-C1-007` | fixed | Часть E2E proof зависела от сравнений исходного текста helper | `docker/anki-e2e/smoke-api.py`, `test_docker_smoke_helpers.py` | CSS asset и inspection request behavior проверяются исполняемыми helpers/contracts | Focused helper tests в составе 101 Search/server/E2E tests | Полный real-Anki smoke остаётся финальным integration proof | yes |
| `U-C1-008` | fixed | Публичный status раскрывал подробную server/runtime диагностику и пути | `dashboard_server.py`, dashboard tests/docs | `/api/status` строго минимален; подробности требуют токен; пути сведены к basename | Status payload, auth и Windows/POSIX path-redaction tests | Process-level localhost observer всё ещё видит порт, что ожидаемо | yes |
| `U-C1-009` | fixed | Общий request path обновлял idle timer до authentication | `dashboard_server.py` и tests | Idle touch происходит после valid auth либо для явно trusted public/static path; unknown path 404 | Failed-auth/unknown/trusted/valid lifecycle tests | Публичный readiness считается доверенной активностью по явному контракту | yes |

## Finding ledger — UI

| ID | Status | Old root cause | Changed files | New invariant | Tests/evidence | Residual risk | Release blocker closed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `C1-UI-001` | fixed | Вложенные panel/card поверхности размывали hierarchy | shared styles, Cards/Profiles pages и components | Page, region, interactive и selected surfaces имеют разные роли; обычные sections не становятся cards | `CardsVisualContract`, `InspectionProfilesVisualContract`, component tests | Финальная оценка raster/computed styles выполняется в browser E2E | yes |
| `C1-UI-002` | fixed | Metadata и headings использовали несогласованные размеры/вес | `styles.css`, page-specific styles | Общие page/section/body/label/meta type roles | Visual contract tests и production build | Шрифтовой raster зависит от runtime platform | yes |
| `C1-UI-003` | fixed | Basic читался как developer schema editor | Profiles page, Basic/Advanced components, styles, locale | Семь plain-language milestones; machine details только Advanced | Profiles visual/page/component tests RU/EN | Complex custom profiles по-прежнему требуют Advanced | yes |
| `C1-UI-004` | fixed | Drawer просвечивал и конфликтовал с utility dock при 1024 | `CardsDetailDrawer.tsx`, `cardsInbox.css`, tests | `<1200` opaque non-modal drawer, sticky header/internal scroll; dock снаружи; 1199/1200 exact | Boundary, Escape, focus-return и containment tests | Platform scrollbar width проверяется integration browser | yes |
| `C1-UI-005` | fixed | Queue row было трудно сканировать из-за повторов anatomy/scope | `CardsInbox.tsx`, `CardsPage.tsx`, styles | Priority/identity/evidence/meta имеют стабильный компактный порядок | Cards page/inbox/visual contract tests | Реальные длинные значения требуют browser fixture | yes |
| `C1-UI-006` | fixed | Filters, summary, query scope и utilities конкурировали | `CardsPage.tsx`, styles, locales | Local queue filters отделены от scope; active filters явны; coverage одно disclosure | Cards page/visual contract/localization tests | При множестве активных фильтров используется wrapping | yes |
| `C1-UI-007` | fixed | Lifecycle, result и actions фрагментировались по badges/panels | `CardsDetail.tsx`, Profiles action zone, styles/locales | Одна lifecycle surface и не более одного primary action; result операции не равен resolution | Lifecycle/action-label/state tests | Backend C1.6 semantics намеренно не изменены | yes |
| `C1-UI-008` | fixed | Unselected Profiles выглядел как незаконченный placeholder | Profiles page/styles/locales | Одна спокойная empty surface объясняет выбор и отсутствие autosave/autoconfirm | Profiles visual/page tests RU/EN | Нет декоративной иллюстрации по design contract | yes |
| `C1-UI-009` | mitigated with residual risk | Theme surfaces недостаточно разделялись | shared/page-specific tokens and styles | Light/dark roles разделяют page, region, interaction, selection и focus | Theme selectors/structural visual tests; production CSS build | Финальные contrast/raster screenshots ожидаются от browser E2E | yes |
| `C1-UI-010` | fixed | Технический copy попадал в normal Profiles path | Basic/Advanced components и locales | ID/ordinal/mode находятся только в Advanced; Basic использует Anki terms | RU/EN visual and page tests | Exact field names остаются намеренно видимыми | yes |
| `C1-UI-011` | fixed | Validation toast мог перекрыть form | Profiles page/result/styles | Результат persistent inline; toast статичен и вторичен; conflict блокирует рядом с actions | Validation success/error/conflict tests | Native browser zoom проверяется integration browser | yes |
| `C1-UI-012` | fixed | Answer modal имел лишний chrome/dead space | Cards detail/modal styles and tests | Один preview frame, компактный chrome, visible close/X, Escape, trap и long-answer scroll | Cards visual/detail/accessibility tests | Security boundary preview не изменена | yes |

## Security decisions

Vendored pure-Python `tinycss2` и `webencodings` выбраны для совместимости с embedded Python Anki без compiled extensions. Полные license files и third-party notices включены в пакет. Regex больше не является primary control stylesheet.

`style-src 'unsafe-inline'` сохранён только потому, что frontend создаёт runtime styles внутри Shadow DOM. Остальные источники default-deny и same-origin; parser policy остаётся primary boundary.

## API/schema

Wire schema Search v2, Triage v4/recheck v1 и Inspection Profiles не менялись. Добавлен типизированный HTTP `409 search_busy`. Публичный `/api/status` сужен до `ok/status`; подробный `/api/server/status` остаётся token-protected.

## UI before/after

Cards сохраняет semantic list, exact-card workflow и non-modal drawer, но отделяет local filters от query scope, уплотняет queue anatomy и строит Inspector вокруг одного lifecycle/action path. Inspection Profiles сохраняет single strict draft и Basic/Advanced model, но Basic теперь читается как guided configuration с одной action zone.

## Verification

Focused checks выполнялись после каждой независимой группы и перечислены в ledger.

Финальный локальный контур:

| Проверка | Результат |
| --- | --- |
| `git diff --check` | PASS |
| TypeScript typecheck | PASS |
| frontend Vitest | PASS — 342 tests |
| Vite production build | PASS — 2272 modules |
| bundle guard | PASS — 20 JS chunks, entry 430 646 bytes, total 1 375 572 bytes |
| Python full | PASS — 841 passed, 1 expected package-artifact skip |
| Python compileall | PASS |
| package build/check | PASS — 96 entries |
| package check-only | PASS — 96 entries |
| Search boundedness benchmark | PASS — 100 000 IDs, 246.96 ms, peak 406 680 bytes |

Canonical PowerShell entrypoint первоначально выбрал Windows `pnpm.cmd` из WSL `PATH`; после изоляции Linux PATH выполнил frontend/typecheck/build/bundle, но его Python helper выбрал системный Python без pytest. Оставшиеся идентичные шаги выполнены напрямую на `.venv/bin/python` с явным Linux temp и без bytecode junk. Эти ошибки классифицированы как local environment, а не PASS entrypoint; полный эквивалентный non-Docker набор команд имеет PASS выше.

Exact-SHA Fast CI, targeted `standard/cards` с restart и final `standard/full` фиксируются в draft PR и итоговом handoff; до их PASS C2 не объявляется release-ready.

## Residual risks и граница merge

- Native Search materialization остаётся upstream limitation; mitigations ограничивают add-on memory и concurrency.
- Broad legacy modules не переписаны вне доказанных seams.
- Light/dark raster, внешние network negative controls, native rendering, restart и live fixture требуют exact-package real-Anki evidence.
- Merge в `core`, merge/rebase в `master`, release, deployment и AnkiWeb publish не выполняются этой задачей.
- Даже после PASS candidate production tree после merge должен быть сопоставлен с проверенным tree; release требует отдельного решения владельца.
