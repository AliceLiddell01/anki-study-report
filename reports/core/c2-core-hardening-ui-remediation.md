# C2 — итоговый отчёт по усилению Core 1.0 и исправлению UI после C1

**Дата закрытия:** 2026-07-22  
**Репозиторий:** `AliceLiddell01/anki-study-report`  
**Базовая ветка:** `core`  
**Базовый SHA:** `1e7beafae16c6259ad6e93f393cda39bd9449dbb`  
**Рабочая ветка:** `c2-core-hardening-ui-remediation`  
**Финальный проверенный head:** `9d5d7724aedac375fde3c9a6752baf1b4aee86ba`  
**Pull request:** `#128`  
**Статус:** реализация и обязательная exact-SHA verification campaign завершены; merge в `core` остаётся отдельным решением владельца.

## 1. Итог этапа

C2 завершил обязательное усиление уже существующего Core после C1 без добавления нового продуктового слоя. Работа закрыла известные технические, security- и UI/UX-findings, усилила границы предпросмотра карточек, устранила ошибки поколений запросов и операций, ограничила дополнительную память Search, сузила публичную диагностику локального сервера и привела Cards/Inspection Profiles к более последовательной визуальной и интерактивной модели.

Финальная проверочная последовательность для текущего head выполнена успешно:

```text
Fast CI на exact SHA: PASS
standard/cards с verify_restart=true: PASS
standard/full: PASS
```

Успех трёх финальных запусков подтверждён владельцем проекта 2026-07-22. Номера этих трёх финальных GitHub Actions runs отсутствуют в доступном контексте, поэтому они не выдумываются. Исторические номера предыдущих запусков приведены только там, где они фактически известны.

C2 не выполнял merge, release, deployment, публикацию `.ankiaddon` или обновление AnkiWeb.

## 2. Основание и границы работы

Работа выполнялась как точечная remediation известных findings из итоговых материалов C1:

- `C1_FINAL_CODE_AND_SECURITY_REPORT.md`;
- `C1_UI_UX_FINAL_REPORT.md`.

Каждый finding повторно сопоставлялся с актуальным production path от exact base. Новый полный аудит всего репозитория не выполнялся.

### В scope

- parser-backed политика пользовательского CSS карточек;
- усиление browser boundary и response security headers;
- authority точной карточки без влияния нерелевантных Inspection Profiles;
- разделение поколений query, inspect, cache и non-abortable mutations;
- ограничение дополнительной памяти и конкуренции широкого Search;
- минимизация публичного server status и корректное владение idle timer;
- extraction только доказанных policy seams;
- behavior-based E2E helpers;
- targeted UI remediation Cards и Inspection Profiles;
- exact-SHA Fast CI → targeted real-Anki E2E → full real-Anki E2E.

### Вне scope

- C1.6B и массовые действия;
- новые продуктовые функции;
- C3 Contextual Additions;
- перестройка delivery infrastructure;
- новая система аккаунтов, геймификации или расширений;
- release, deployment и публикация;
- широкая перепись legacy-модулей без доказанной необходимости.

## 3. Основные изменения

### 3.1. Безопасная обработка CSS карточек

Полный CSS типа заметки больше не контролируется преимущественно regex denylist. Добавлен parser-backed pipeline на базе vendored pure-Python `tinycss2` и `webencodings`:

- синтаксический разбор stylesheet;
- allowlist допустимых правил и свойств;
- scoping selectors в границу карточки;
- ограничение размера и сложности результата;
- fail-closed для malformed и неподдерживаемого CSS;
- безопасная обработка локальных media/font URL;
- запрет внешних и опасных ссылок;
- полные лицензии и third-party notices в пакете.

Regex остаётся вспомогательным инструментом, но не является primary security control.

### 3.2. CSP и browser defense in depth

Локальный dashboard получил deny-by-default Content Security Policy и дополнительные headers:

- `default-src 'none'`;
- same-origin script/connect/media/font policy;
- `object-src 'none'`;
- `frame-src 'none'`;
- `frame-ancestors 'none'`;
- `base-uri 'none'`;
- `form-action 'none'`;
- `Referrer-Policy: no-referrer`;
- `X-Content-Type-Options: nosniff`.

`style-src 'unsafe-inline'` сохранён узко и осознанно, поскольку Shadow DOM preview создаёт runtime styles. Основной security boundary при этом остаётся parser-backed CSS policy.

Во время targeted E2E был обнаружен конфликт строгого CSP с ранним inline theme bootstrap. Исправление не ослабило CSP: bootstrap перенесён в Vite-managed same-origin module, загружаемый до основного entry.

### 3.3. Authority точной карточки

Aggregate health всех Inspection Profiles больше не используется как authority для перепроверки одной карточки. Recheck учитывает точный note type, только релевантные profile-dependent reasons и текущие revision/fingerprint. Stale, unavailable и partial evidence работают fail closed.

### 3.4. Generation-safe Cards workspace

Разделены независимые query generation, inspect generation, cache generation и non-abortable mutation operation. Результат операции больше не теряется из-за refresh, смены scope или нового query. Stale inspect completion игнорируется, а cache привязан к generation, ограничен 50 элементами и очищается на refresh/scope change.

### 3.5. Ограниченный Search

После возврата native Anki result add-on хранит не более cap лучших уникальных ID и не создаёт несколько полноразмерных копий результата. Одновременно выполняется не более одного широкого native query; конфликт возвращает `409 search_busy`.

Benchmark на 100 000 ID:

```text
время: 246.96 ms
peak additional memory: 406 680 bytes
бюджет времени: 500 ms
бюджет памяти: 2 MiB
результат: PASS
```

Ограничение Anki остаётся: `find_cards` и `find_notes` уже материализуют полную `Sequence` и не предоставляют streaming/limit API.

### 3.6. Локальный server status и idle lifecycle

Публичный `/api/status` сужен до минимальной формы `ok/status`. Подробная диагностика остаётся только в token-protected `/api/server/status`; пути редактируются до безопасного basename-представления для Windows и POSIX.

Idle timer больше не обновляется до authentication. Failed token requests и неизвестные routes не продлевают lifetime сервера.

### 3.7. Behavior-based E2E contracts

Проверки исходного текста helper-файлов заменены исполняемыми contracts и behavior assertions для CSS, inspection requests, server/security responses, exact package handoff и Cards lifecycle.

### 3.8. UI remediation Cards

Cards сохраняет semantic attention inbox, один Inspector, exact-card lifecycle, non-modal drawer ниже 1200 px и true modal для ответа. При этом local filters отделены от query scope, queue row получил стабильную anatomy, lifecycle/actions/result перестали конкурировать, metadata выделена семантически, а drawer стал непрозрачным и получил внутренний scroll.

Targeted E2E выявил устаревший test hook после UI-рефакторинга. Production behavior было корректным, но browser test ожидал старую DOM-границу. `cards-resolution-state` возвращён авторитетному lifecycle banner, а result section получила отдельный `cards-resolution-result`.

### 3.9. UI remediation Inspection Profiles

Basic path представлен как семь последовательных пользовательских разделов. Machine IDs, ordinals и mappings остаются в Advanced. Сохранены один strict draft, явное подтверждение, отсутствие autosave/autoconfirm и fail-closed lifecycle. Validation стала persistent inline и не перекрывает форму.

## 4. Finding ledger

### Technical/security

| ID | Итог | Краткий результат | Остаточный риск |
| --- | --- | --- | --- |
| `U-C1-001` | исправлено | Parser-backed CSS allowlist, selector scoping, safe media/font rewrite, CSP | Runtime browser остаётся integration boundary, закрытым real-Anki E2E |
| `U-C1-002` | исправлено | Authority ограничена exact note type и релевантными reasons | Известного residual в изменённой границе нет |
| `U-C1-003` | исправлено | Mutation отделена от query generation | Native operation может быть долгой, UI остаётся busy |
| `U-C1-004` | исправлено | Generation-keyed bounded inspect cache | Cache не сохраняется между reload |
| `U-C1-005` | смягчено | `O(cap)` additional memory и gate широкого Search | Полная materialization остаётся ограничением Anki API |
| `U-C1-006` | смягчено | Выделены доказанные policy seams | Broad legacy services не переписаны полностью |
| `U-C1-007` | исправлено | E2E proof переведён на behavior contracts | Full real-Anki остаётся авторитетным gate |
| `U-C1-008` | исправлено | Минимальный public status и защищённая diagnostics projection | Local observer видит loopback port, что ожидаемо |
| `U-C1-009` | исправлено | Idle activity принадлежит authenticated/trusted request | Public readiness доверен по контракту |

### UI/UX

| ID | Итог | Краткий результат | Остаточный риск |
| --- | --- | --- | --- |
| `C1-UI-001` | исправлено | Разведены page/region/interactive/selected surfaces | Platform raster зависит от браузера |
| `C1-UI-002` | исправлено | Общие typography roles | Шрифтовой raster платформозависим |
| `C1-UI-003` | исправлено | Basic стал guided path | Сложные профили требуют Advanced |
| `C1-UI-004` | исправлено | Opaque non-modal drawer и boundary 1199/1200 | Scrollbar остаётся browser detail |
| `C1-UI-005` | исправлено | Компактная anatomy queue row | Очень длинные данные зависят от wrapping |
| `C1-UI-006` | исправлено | Filters отделены от scope | Много фильтров переносится строками |
| `C1-UI-007` | исправлено | Один lifecycle/action path | Backend semantics C1.6 не расширялись |
| `C1-UI-008` | исправлено | Понятный unselected state | Декоративная иллюстрация не добавлялась |
| `C1-UI-009` | смягчено и проверено | Более различимые light/dark surfaces | Абсолютный contrast зависит от дисплея |
| `C1-UI-010` | исправлено | Технический copy вынесен в Advanced | Реальные field names намеренно видимы |
| `C1-UI-011` | исправлено | Inline validation | Native zoom остаётся browser behavior |
| `C1-UI-012` | исправлено | Компактный answer modal | Security boundary preview не менялась |

## 5. API и публичные контракты

Wire schema Search v2, Triage v4/recheck v1 и Inspection Profiles v1 сохранены. Добавлены типизированный `409 search_busy`, минимальный `/api/status`, защищённый подробный status и безопасные локальные font media types. Backend, frontend, tests и docs синхронизированы в пределах изменённых контрактов.

## 6. Проверка

| Проверка | Результат |
| --- | --- |
| TypeScript typecheck | PASS |
| frontend Vitest | PASS — 342 tests до финальных интеграционных исправлений; текущий head подтверждён новым Fast CI |
| Vite production build | PASS — 2272 modules |
| bundle guard | PASS — 20 JS chunks, entry 430 646 bytes, total 1 375 572 bytes |
| Python full | PASS — 841 passed, 1 ожидаемый package-artifact skip |
| Python compileall | PASS |
| package build/check | PASS — 96 entries |
| package check-only | PASS — 96 entries |
| Search benchmark | PASS — 100 000 IDs, 246.96 ms, peak 406 680 bytes |
| focused handoff contract | PASS — 35 tests |
| final exact-SHA Fast CI | PASS — подтверждено владельцем для `9d5d7724...` |
| targeted `standard/cards` + restart | PASS — подтверждено владельцем |
| final `standard/full` | PASS — подтверждено владельцем |

### История exact-package E2E

1. Fast CI `29882753539` создал exact package для предыдущего head `c7bfbf26600caac5c01ba798db690bbfe48761b8`.
2. Targeted run `29882991519` прошёл handoff resolution, diagnostics validation, exact checkout, package validation, GHCR pull, Compose validation и Docker setup.
3. Он упал в browser smoke из-за устаревшего Cards hook и одновременно выявил CSP error inline theme bootstrap.
4. Оба дефекта исправлены без изменения product model и без ослабления CSP.
5. Для текущего head `9d5d7724aedac375fde3c9a6752baf1b4aee86ba` новый Fast CI, targeted `standard/cards` с restart и final `standard/full` завершились успешно.

## 7. Остаточные риски

- Anki native Search материализует полный result до add-on processing;
- broad legacy services остаются широкими вне выделенных policy seams;
- `style-src 'unsafe-inline'` требуется runtime Shadow DOM styles, но ограничен parser policy и deny-by-default CSP;
- отдельная проверка на приватном профиле владельца не выполнялась;
- после merge необходимо сопоставить production tree с проверенным candidate tree.

## 8. Что не выполнялось

- merge PR #128 в `core`;
- merge/rebase `core` в `master`;
- release tag, GitHub Release и production `.ankiaddon`;
- deployment и AnkiWeb publish;
- C1.6B и C3;
- unrelated cleanup и broad legacy rewrite.

## 9. Рекомендованное решение

C2 candidate технически готов к отдельному решению владельца о merge PR #128 в `core`.

После merge необходимо зафиксировать merge SHA, подтвердить соответствие production tree проверенному candidate tree и обновить handoff. Release, C1.6B и C3 не следуют автоматически.

## 10. Финальная классификация

```text
C1: завершён и принят
C2 implementation: завершена
C2 findings: закрыты или документированно смягчены
C2 exact-SHA Fast CI: PASS
C2 targeted standard/cards + restart: PASS
C2 final standard/full: PASS
C2 candidate: готов к решению о merge
merge в core: не выполнен
release/deployment/publication: не выполнялись
```

## 11. Post-merge manual acceptance remediation

После включения C2 в `core` владелец провёл ручную проверку Cards и Inspection Profiles. Этот раздел — append-only follow-up к C2, а не новый C2.x stage. Восстановленный base: `edb140b1197910aae31500a40e4a8287cc46b760`; рабочая ветка: `c2-manual-acceptance-remediation`.

Owner evidence было передано как пять screenshots в `C:\Users\KykLa\Desktop\cards`: APKG/wide/light, synthetic/expanded/light, synthetic/wide light/dark и synthetic/1024/light. Оно подтвердило потерю native background в preview, вложенную прокрутку/лишний нижний объём широкого Inspector и конфликт drawer с узким layout. Screenshots Inspection Profiles не были переданы; эти замечания воспроизведены по current DOM/CSS и покрыты deterministic frontend/browser contracts.

### 11.1 Выполненные изменения

- Parser-backed selector rewrite переносит `.card`, `.card.card1`, `.card .child` и root night-mode selectors на Shadow preview `:scope`, сохраняя fail-closed policy, запрет document/host escape и отсутствие внешних loads.
- Compact preview больше не создаёт вертикальный scroll container и не выводит dashboard dark theme как native night mode. Wide Inspector участвует в page scroll; собственный scroll остаётся у queue, drawer и modal.
- Metadata, причины и actions сгруппированы как различимые soft regions. `Suspend`, `Bury`, `Open in Anki` и recheck показывают отдельные pending/success/failure/no-change результаты рядом с action zone.
- Basic и Advanced стали взаимоисключающими tabpanels одного strict draft. Basic остаётся default; mode switch не сохраняет и не подтверждает профиль. Dirty/error count видны на Advanced tab.
- Внутренние grids Inspection Profiles используют container width editor и переходят 3→2→1 columns. Operation status перенесён в action region; catalog refresh сохраняет draft.
- Field-role suggestion использует Unicode NFKC, CamelCase/PascalCase/кириллические границы, token/phrase scoring и ограниченные RU/EN aliases. Близкие и low-confidence результаты остаются unresolved; несколько уверенных exact fields одной роли сохраняются с name+ordinal.
- Общий dashboard foundation получил bounded motion/radius/surface tokens и shared refresh control. Refresh сохраняет старый usable content и active item под `aria-busy`; ошибка не уничтожает предыдущую очередь. Reduced motion выключает rotation/transform motion, сохраняя функциональный loading state.

### 11.2 Acceptance ledger

| ID | Статус | Результат и evidence |
| --- | --- | --- |
| `MA-CARDS-01` | fixed | `.card` root/background и descendants применяются через parser-token `:scope`; computed-style browser regression проверяет exact colors без external requests |
| `MA-CARDS-02` | fixed | compact front и expanded answer сохраняют native background; dark dashboard не навязывает night mode |
| `MA-CARDS-03` | fixed | compact preview имеет clipped overflow и не владеет wheel; wide Inspector использует page scroll |
| `MA-CARDS-04` | fixed | отдельный scroll оставлен queue/drawer/modal; artificial Inspector safe-area удалён |
| `MA-CARDS-05` | fixed | action/Open/recheck feedback разделяет pending, result, no changes, failure и canonical outcome |
| `MA-PROFILES-01` | fixed | Basic/Advanced взаимоисключающие, Basic default, один strict draft без autosave/autoconfirm |
| `MA-PROFILES-02` | fixed | editor container queries обеспечивают 3→2→1 grids и отсутствие overlap на 1024 px |
| `MA-PROFILES-03` | fixed | понятные CamelCase/PascalCase/кириллические field names получают weighted role suggestions |
| `MA-PROFILES-04` | mitigated | multiple exact fields одной роли сохраняются; ambiguous/low-confidence fields остаются unresolved для ручного решения |
| `MA-PROFILES-05` | fixed | notice hierarchy сокращена, validation/conflict/action status находятся рядом с action region |
| `MA-UI-01` | fixed | shared refresh сохраняет usable content, active item, control dimensions и focus; pending/error/success доступны через ARIA |
| `MA-UI-02` | fixed | общие motion/radius/surface roles применены к Cards, Profiles и shared controls; reduced-motion path статичен |

### 11.3 Security и контракты

Wire payload/schema, Inspection Profiles v1, Triage v4/recheck v1 и exact-card authority не изменены. Preview по-прежнему не использует iframe или JavaScript, не читает network/filesystem при sanitization и разрешает media только через локальную validated boundary. CSP не ослаблена. Field inference остаётся локальной, детерминированной suggestion-only эвристикой: raw note values не логируются и не отправляются наружу.

### 11.4 Проверка follow-up

На момент фиксации раздела выполнены focused Python role/profile tests, focused frontend hook/page/component/visual-contract tests, TypeScript typecheck, `node --check` browser smoke и `git diff --check`. Полный локальный контур, Fast CI exact SHA, targeted `standard/cards` с restart и final `standard/full` должны быть сопоставлены с exact head в draft PR; их run IDs нельзя предзаписывать в коммит.

Manual real-profile gate остаётся `PENDING`: владелец должен повторно проверить native compact/expanded backgrounds и реальные `Suspend`, `Bury`, `Open in Anki`, recheck и Inspection Profiles на своей установке. Автоматический доступ к приватному профилю не выполнялся.
