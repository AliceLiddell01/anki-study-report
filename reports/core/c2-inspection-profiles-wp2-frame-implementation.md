# C2 / PR #130 — Inspection Profiles WP2 workspace frame

> **Исторический статус original candidate: `REQUEST CHANGES`.**
> Этот отчёт сохранён как baseline исходного WP2 candidate и superseded
> [bounded corrective pass](c2-inspection-profiles-wp2-corrective-pass.md).
> Его evidence не является подтверждением принятия исправленного candidate.

Дата evidence run: 2026-07-29
Ветка: `c2-manual-acceptance-remediation`
Remote branch до WP2 push: `dc095698e223bfe55bacece1a515abe847ec513b`
Implementation commit: `702ad734e3867aa615b7384c01ab848247cf3226`
Evidence harness commit: `8dbd80302a9629fb0726f141435b52817ba5aba6`

## Статус

```text
WP2 original Inspection Profiles frame candidate:
REQUEST CHANGES

Cards:
ACCEPTED / COMPLETE / FROZEN

Inspection Profiles inner implementation:
NOT STARTED
```

Этот исторический WP2 продолжал существующий C2 / PR #130 и не являлся новым
roadmap stage. После внешнего review original candidate получил `REQUEST
CHANGES`; корректирующий implementation candidate и его актуальное evidence
описаны в отдельном отчёте. Автоматизированные проверки исходного candidate не
заменяли visual verdict или owner acceptance.

## Реализованный scope

- route header сокращён до одного H1, короткого описания и refresh action;
- удалены отдельный safety paragraph и крупная summary surface;
- каталог note types стал ограниченной по ширине колонкой с search, state
  filter, count, компактными rows и стабильным backend order;
- editor frame получил интегрированную identity выбранного note type:
  display name, detected kind, lifecycle, generated/dirty state, число fields
  и templates;
- Basic и Advanced оформлены как один `tablist` с взаимоисключающими
  `tabpanel`, Arrow Left/Right, Home и End;
- при 1024 catalog и editor остаются рядом, при QHD catalog остаётся
  ограниченным, а editor расширяется;
- browser font stack явно выбирает установленный proportional sans-serif,
  исключая непреднамеренную Linux Chromium substitution на monospace.

`BasicProfileEditor` и `AdvancedProfileDisclosure` внутри tabpanels не
перекомпоновывались. Backend, API/schema, workspace hook, validation flow и
Cards production не менялись.

## Production-browser evidence

In-app browser bridge не дошёл до page setup: WSL workspace URI был отклонён
ошибкой `sandboxCwd is not a local file URI`. Согласно контракту выполнен
разрешённый fallback: Vite production preview и repository-owned
Playwright/Chromium harness.

Объективный результат:

- 14 full-page captures;
- 72 locator-based region captures;
- 14 ARIA snapshots;
- RU/EN, light/dark, 1440×900, 1024×768 и 2560×1440;
- loading, load error, store unavailable, empty, no matches и dirty;
- Basic/Advanced keyboard contract: PASS;
- compact Settings overflow keyboard contract: PASS;
- horizontal page overflow: отсутствует во всех scenarios;
- proportional computed font: подтверждён во всех scenarios;
- axe: два запуска, в каждом 0 violations и 0 incomplete;
- unexpected requests / request failures: 0 / 0;
- console errors / page errors / external requests: 0 / 0 / 0.

Прямые prototype/production comparisons включают side-by-side, overlay и
difference для 1440 light Basic, 1440 dark Advanced, 1024 light compact и QHD
light Advanced. Внутренности Basic/Advanced editor симметрично исключены из
сравнения, потому что относятся к следующему scope.

## Consolidated verification

Поддерживаемый toolchain: Node `v24.18.0`, pnpm `9.15.9`.

- focused Profiles/Settings/localization/validation: 31 PASS;
- full Vitest: 75 files, 387 tests, all PASS;
- TypeScript: PASS;
- Vite production build: PASS;
- bundle guard: PASS;
- final production-browser matrix: PASS;
- `git diff --check`: PASS.

Cards production code и Cards-specific styles отсутствуют в WP2 diff. Поэтому
тяжёлый frozen Cards real-Anki gate не перезапускался: нового Cards-specific
риска не создано.

## Evidence artifact

Artifact расположен вне repository и не коммитится:

```text
/home/kykla/asr-work/pr130-wp2-profiles-frame-evidence.zip
```

```text
size: 10 559 221 bytes
SHA-256: 3eb24e151c128d6e7aaf29f16f11895a879cb7eacec350d5c1b046410ac1b59f
ZIP CRC: PASS
payload files declared / present: 131 / 131
missing / unexpected / checksum mismatches: 0 / 0 / 0
```

В package входят full-page и region screenshots, prototype references,
geometry/font metrics, ARIA snapshots, axe output, console/network ledgers,
comparisons, deviation report, harness source, manifest и `SHA256SUMS`.

## Оставшиеся границы

- original candidate: REQUEST CHANGES;
- исправления: см. [bounded corrective pass](c2-inspection-profiles-wp2-corrective-pass.md);
- WP3 Inspection Profiles Basic: NOT STARTED;
- PR-wide merge decision: NOT PERFORMED;
- PR #130 должен оставаться `OPEN / DRAFT / UNMERGED`;
- C3, ready-for-review, merge и release не активированы.
