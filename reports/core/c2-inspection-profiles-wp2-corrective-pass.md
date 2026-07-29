# C2 / PR #130 — Inspection Profiles WP2 bounded corrective pass

- Дата финального Windows evidence run: 2026-07-29
- Ветка: `c2-manual-acceptance-remediation`
- Implementation commit: `d507a3d5f235f15fb0f3ffb6fca397784c2c58d3`
- Implementation tree: `27803dffb6846c6f5a864d8c611e889fe4bd10f4`
- Evidence harness blob: `f5231ea5f98c4cc68b617c641ac456ca11478bdf`

## Статус

```text
WP1 Settings shell:
STRUCTURAL FOUNDATION DELIVERED
OWNER VISUAL ASSESSMENT: 6/10
VISUAL LANGUAGE: PROVISIONAL

WP2 original frame candidate:
REQUEST CHANGES

WP2 bounded corrective pass:
IMPLEMENTATION CANDIDATE DELIVERED
EXTERNAL VISUAL REVIEW PENDING

WP3 Basic:
NOT STARTED

Cards:
ACCEPTED / COMPLETE / FROZEN
```

`6/10` выше — исторический verdict владельца для WP1, а не оценка этого
corrective candidate. Численная visual self-assessment не выполнялась. Текущий
результат готов только к внешнему visual review и не является owner acceptance,
ready-for-review, merge или release decision.

## Источники и границы

Corrective pass выполнен в Windows checkout по bounded prompt, внешнему review,
prototype v3.2.3 и evidence исходного WP2 candidate. Production code и tests
оставались источником истины при расхождениях.

Сохранены без изменения:

- Cards production composition, styles, preview, AV/audio/GIF/media и Shadow DOM;
- backend, API/schema и frontend payload contract;
- workspace lifecycle, persistence и validation flow;
- внутренности `BasicProfileEditor` и `AdvancedProfileDisclosure`;
- Settings routes за пределами общего regression coverage.

Новые ветки и PR не создавались. WSL, Docker и real-Anki E2E не использовались.

## Реализованные исправления

- state priority зафиксирован immutable map в порядке `needs_review`,
  `confirmed`, `suggested`, `not_configured`, `disabled`;
- после фильтрации применяется locale-aware сортировка по display name со
  стабильным исходным индексом для полного tie;
- catalog и editor identity извлечены в отдельные
  `InspectionProfilesCatalog` и `InspectionProfileEditorIdentity`;
- catalog получил компактные controls, rows, полный title для длинного имени и
  отдельные selected, hover и keyboard focus states;
- active tab, tab focus, dirty state и warning semantics визуально разведены;
- editor identity стала компактнее и truthfully показывает сохранённое имя,
  meaningful suggestion, независимый draft или явный fallback;
- тяжёлые вложенные surfaces и borders ослаблены без изменения editor internals;
- QHD workspace ограничивает identity content до `1230px`, lifecycle control до
  `360px`; catalog остаётся ограниченным, editor использует доступную ширину;
- repository-owned harness расширен до Windows production matrix, prototype
  comparisons, geometry, state, keyboard, ARIA, axe и network diagnostics.

## Automated verification

Windows baseline: Node `v22.23.1`, pinned pnpm `9.15.9`, Playwright `1.55.1`,
Chromium `140.0.7339.186` (build `1193`).

- `pnpm.cmd exec vitest run`: PASS — 75 files, 391 tests;
- `pnpm.cmd run build`: PASS — TypeScript, Vite production build, 2285 modules,
  bundle guard, 21 JavaScript chunks;
- `python -m compileall -q anki_study_report`: PASS;
- final repository-owned production-browser harness: PASS;
- `git diff --check`: PASS перед implementation commit.

Docker и real-Anki E2E: NOT RUN — bounded frame-only изменение не создало
backend, collection, Cards или package lifecycle риска, а prompt запрещал
расширять проверку в эту область.

## Production-browser matrix

Финальный Windows run:

- 18 full-page captures, 117 locator region captures, 18 ARIA snapshots;
- RU/EN, light/dark, 1440×900, 1024×768 и 2560×1440;
- representative loading, error, unavailable, empty, no-match, generated,
  selected, hover, focus, active-tab, dirty и warning states;
- axe: 2 profiles, 0 violations, 0 incomplete;
- Basic/Advanced tablist keyboard и tab exit: PASS;
- compact overflow ArrowDown/Home/End/Escape: PASS;
- dirty Basic/Advanced round trip с сохранением значения: PASS;
- unexpected requests, failed requests, expected aborts, console errors, page
  errors и external requests: по `0`;
- horizontal page overflow: отсутствует во всех scenarios;
- длинная catalog row не перекрывает state/count: минимальный зазор `2.25px`.

Объективная geometry:

| Viewport | Catalog / editor | Identity | Inner bound | Lifecycle | Page overflow |
| --- | --- | --- | --- | --- | --- |
| 1440×900 | `288 / 796.25px` | `108.03px` | `769.25px` | `326.13px` | нет |
| 1024×768 | `270 / 643.25px` | `104.06px` | `616.25px` | `270px` | нет |
| 2560×1440 | `320 / 1882.75px` | `108.03px` | `1230px` | `360px` | нет |

По сравнению с исходным candidate identity уменьшилась на `60.60px` при 1440
и на `97.46px` при 1024. Production identity+tabs остаются выше prototype
header на `35.28px`, `31.31px` и `22.15px` для 1440, 1024 и QHD
соответственно; это зафиксировано как остаточное отклонение, а не visual score.

## Finding ledger

| Finding | Статус | Объективное основание |
| --- | --- | --- |
| `LOGIC-01` state priority/order | CLOSED | immutable priority map, filter-then-sort и focused tests |
| `VISUAL-01` selected/active ambiguity | CLOSED | отдельные computed colors/outlines для selected, hover, focus, active tab, dirty и warning |
| `VISUAL-02` oversized identity | PARTIAL | высота снижена на 60.60–97.46px, но prototype delta 22.15–35.28px остаётся |
| `VISUAL-03` stretched QHD workspace | CLOSED | inner width `1230px`, lifecycle `360px`, overflow отсутствует |
| `VISUAL-04` administrative catalog | PARTIAL | controls/rows уплотнены и длинное имя не перекрывает metadata; итоговый visual verdict внешний |
| `VISUAL-05` misleading generated identity | CLOSED | явная tested precedence stored/suggested/draft/fallback |
| `VISUAL-06` heavy nested canvas | PARTIAL | surfaces и borders ослаблены; visual parity остаётся на внешнюю проверку |
| `ARCH-01` monolithic page | CLOSED | catalog и identity извлечены в самостоятельные components |

## Evidence artifact

Artifact расположен вне repository и не коммитится:

```text
C:\Users\KykLa\Documents\Anki Study Report Evidence\pr130-wp2-corrective-evidence.zip
```

```text
size: 9 343 216 bytes
SHA-256: 364c6c5ddff887134ea494bc70bdf4795c100a851c8edc2e7a6277bc468d732e
ZIP entries: 183
uncompressed bytes: 10 224 530
manifest inventory: PASS
manifest hashes: PASS
SHA256SUMS: PASS
JSON parse: PASS
sensitive/token-bearing scan: PASS
ZIP inventory: PASS
ZIP full-entry read / CRC: PASS
```

Package содержит source identities, prototype references, production full-page
и region captures, side-by-side comparisons, overlays, pixel diffs, geometry,
ARIA/axe, keyboard/state/network diagnostics, reports, harness source,
`manifest.json` и `SHA256SUMS`.

## Delivery и незакрытые решения

- implementation commit отправлен в существующую remote branch;
- этот отчёт и синхронизация status docs поставляются отдельным docs-only
  commit;
- draft PR #130 остаётся `OPEN / DRAFT / UNMERGED`;
- внешний visual review и owner acceptance: PENDING;
- WP3 Basic: NOT STARTED и заблокирован до WP2 owner acceptance;
- PR-wide merge decision, C3, ready-for-review и release: NOT PERFORMED.
