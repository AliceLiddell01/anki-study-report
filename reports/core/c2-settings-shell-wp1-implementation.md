# C2 WP1 Settings shared shell

Дата evidence run: 2026-07-28  
Ветка: `c2-manual-acceptance-remediation`  
Baseline до локальной реализации: `edf94a86959bed41f75a9de5a110ce61b888c9a1`

## Статус

```text
WP1 Settings shell:
IMPLEMENTATION CANDIDATE DELIVERED
EXTERNAL VISUAL REVIEW PENDING

Cards:
ACCEPTED / COMPLETE / FROZEN

Inspection Profiles inner implementation:
NOT STARTED
```

Codex не выставляет числовую визуальную оценку и не заявляет owner acceptance. Финальный visual verdict должен быть вынесен внешним reviewer по объективному evidence package.

## Реализованный scope

- единая canonical-модель восьми Settings routes;
- shared route header, который расположен перед navigation и route content;
- desktop sidebar и compact horizontal navigation;
- overflow menu с четырьмя routes, `menu`/`menuitem`, Arrow Up/Down, Home/End, Escape, outside pointer и focus return;
- перевод keyboard focus на реальный H1 выбранного route, включая lazy-loaded route;
- Settings-only QHD width без изменения non-Settings max-width;
- RU/EN и light/dark состояния;
- scoped tests для shell, router и стабильного heading ownership.

## Heading ownership audit

| Route | Header owner | Состояния |
| --- | --- | --- |
| `#/settings` | `SettingsPageHeader` → `SettingsRouteHeader` | stable |
| `#/settings/data` | `SettingsPage` shared wrapper | stable |
| `#/settings/inspection-profiles` | page header → `SettingsRouteHeader` | stable; internals unchanged |
| `#/settings/privacy` | shared route header | loading / error / ready |
| `#/settings/notifications` | shared route header outside state branch | loading / error / ready |
| `#/settings/server` | `SettingsPageHeader` → `SettingsRouteHeader` | stable |
| `#/settings/sources` | page header → `SettingsRouteHeader` | stable |
| `#/settings/logs` | page header → `SettingsRouteHeader` | stable |

Каждый browser scenario подтвердил один H1 внутри Settings shell. Overflow activation для Notifications, Server, Sources и Logs переводит focus на видимый, не перекрытый H1; `document.activeElement` не остаётся `BODY`.

## Production browser evidence

Repository-owned Playwright/Chromium contour запущен против Vite production preview. In-app browser bridge не стартовал из-за отдельной ошибки преобразования Linux workspace URI, поэтому применён прямо разрешённый fallback.

Объективный результат:

- 9 full-page captures;
- 24 locator-based region captures;
- 1440×900: RU/EN, light/dark;
- 1024×768: RU/EN compact, overflow open, route-target focus;
- 2560×1440: RU light;
- 4 prototype/production side-by-side, overlay и pixel-diff набора;
- Escape focus return, outside pointer close и browser back/forward: PASS;
- все 4 overflow routes: focus target visible и not obscured;
- axe violations: 0;
- axe incomplete: 0;
- unexpected requests / request failures: 0 / 0;
- console errors / page errors: 0 / 0.

## Объективные deviations

| Область | Наблюдение | Решение |
| --- | --- | --- |
| Inspection Profiles internals | Production editor/catalog composition отличается от Prototype | Out of WP1; исключено shell-only locator captures и masks |
| Global app navigation at 1024 | Полный diagnostic capture показывает ограниченную ширину верхней навигации | Out of WP1; shell evidence изолирован locator captures, AppLayout/Cards не изменялись |
| Prototype language coverage | Prototype references доступны только для исходных RU states | EN подтверждён production captures, geometry, ARIA и audits без искусственной замены reference |

## Scope boundaries

- Cards production code, Cards styles, native preview, AV/audio/GIF/media и Shadow DOM не менялись.
- Inspection Profiles backend, API/schema, workspace hook, catalog behavior, Basic/Advanced editors и validation flow не менялись.
- Единственное изменение `InspectionProfilesSettingsPage.tsx` — wrapper ownership существующего page header.
- C3, merge, ready-for-review и release не активированы.

## Verification source of truth

Полный post-remediation stdout, browser ledgers, ARIA snapshots, axe output, screenshots, geometry, comparisons, inventory и checksum verification находятся во внешнем artifact:

```text
pr130-wp1-settings-shell-final-evidence.zip
```

Artifact не коммитится в repository. Его `diagnostics/final-verification.log`, `manifest.json`, `SHA256SUMS` и external ZIP CRC являются источником истины для финального automated gate.

Локальная среда использует Node `26.5.0`, тогда как `package.json` объявляет `>=20 <25`. Для Node 26 Vitest запускается с явным `--localstorage-file`; full-suite выполняется с `--no-file-parallelism`, чтобы несколько workers не разделяли один experimental file-backed storage. Это не исключает tests из набора и не меняет production behavior.
