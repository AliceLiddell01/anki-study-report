# G5.1 Profile Production Foundation — delivery report

Дата: 2026-07-30
Mode: Codex
Repository: `AliceLiddell01/anki-study-report`
Checkout: `C:\Users\KykLa\Documents\anki-study-report`
Branch / base: `chatGPT/G5` / `gamification`
Initial HEAD: `3c5c1b199b068dfdff0f9e05dca73fe6f060ae9a`
Fast-forwarded baseline HEAD: `e7edf48dd1b5286b8f432bbee46c6776bb9b463e`
Final package-impacting HEAD: `5fd9c68dc1bd75b0ca1a6de20cc82a9957e1caab`
Draft PR: [#182](https://github.com/AliceLiddell01/anki-study-report/pull/182)

## Статус

```text
G5.0: COMPLETE
G5.1 implementation candidate: DELIVERED
G5.1 owner visual acceptance: PENDING
G5.1 merge: NOT PERFORMED
G5.2: NOT STARTED
G5 overall: NOT COMPLETE
```

## Reference integrity и фактический аудит

- archive: `profile-mock-v0.4-fixed.zip`;
- archive SHA-256:
  `8713ddd025512b2d47d85adb4c50f08e9b79020496685f1267eff883815aeb09`;
- ZIP CRC: `PASS`;
- `checksums.sha256`: `PASS`, 75/75 entries;
- extracted inventory: 76 files;
- inventory:
  `C:\Users\KykLa\AppData\Local\Temp\anki-profile-g5-1-reference-10aa1f76f912417aa5533c0557781f4c\reference-inventory.json`;
- archive и extracted materials не копировались в repository.

Фактически прочитаны:

- `README.md`, `CHANGELOG-v0.4.md`, `prototype.html`;
- `docs/design-brief-v0.4.md`;
- `docs/information-architecture-v0.4.md`;
- `docs/hero-level-spec.md`;
- `docs/skills-system-spec.md`;
- `docs/achievements-list-spec.md`;
- `docs/status-system-spec-v0.4.md`;
- `docs/responsive-contract.md`;
- `docs/motion-system-v0.4.md`;
- `docs/accessibility-interaction-report.md`;
- `docs/performance-motion-report.md`;
- `docs/hotfix-v0.4.1.md`;
- `machine-readable/design-decisions.json`;
- `machine-readable/information-hierarchy-audit.json`;
- `machine-readable/finding-ledger.json`;
- `machine-readable/interaction-audit.json`;
- `machine-readable/motion-contract.json`;
- `machine-readable/performance-audit.json`.

Визуально открыты все обязательные reference screenshots:

- 1024, 1440 и QHD main в light/dark;
- low-data;
- long-identity stress;
- gamification-disabled;
- v0.3/v0.4 comparison.

Representative storyboards открыты. WebM files не воспроизводились и имеют статус
`NOT INSPECTED`; выводы о motion опираются на written contract, storyboards и
production reduced-motion checks.

## Production mapping

Полный pattern-by-pattern ledger находится в
`docs/gamification/profile-g5-1-production-foundation.md`.

- `ADAPT`: factual identity metadata, recent history, semantic light/dark hierarchy,
  bounded responsive layout.
- `IMPROVE`: hero/banner/avatar composition, learning areas из real decks,
  factual Status, 182-day Activity, единый accessible settings dialog, fail-open
  motion.
- `DEFER`: Level/XP strip, achievements и explainability для будущего одобренного
  product contract; эти surfaces не резервируют пустое пространство.
- `REJECT`: skill XP/levels, next achievement, hardcoded mock domains/numbers,
  standalone `localStorage`, demo avatar/banner assets, HTML/CSS copy и любые
  speculative routes/APIs.

Production result намеренно лучше reference в следующих границах:

- все видимые значения имеют существующий production source;
- identity и реальные learning areas находятся выше analytics;
- нет неподдержанных mechanics и пустых placeholders;
- long text, empty/low-data, unavailable metrics и save failure имеют явные states;
- keyboard/focus/reduced-motion работают без animation callback;
- QHD/4K content bounded, а 760/1024 не создают page-level overflow.

## Реализованный Profile

Порядок существующего `#/profile`:

1. identity hero с deterministic initials, factual profile label/dates и settings
   action;
2. до четырёх real learning areas плюс bounded remainder;
3. factual Status из шести метрик;
4. bounded 182-day Activity и summary;
5. recent history: три строки по умолчанию, disclosure до существующих семи;
6. один portal-based settings dialog для существующих
   `customStudyStartedOn` и `deckOverviewSort`.

Dialog использует один существующий token-protected `POST /api/profile`, имеет
validation, duplicate-submit guard, save failure recovery, focus trap, `Escape`
close и focus restoration. `profile === null/undefined` показывает честный
unavailable state без fabricated profile.

Единственные route links: `#/decks` и `#/calendar`.

Не добавлены:

- backend/public schema changes;
- direct collection access;
- dependencies, fonts, CDN или external/demo assets;
- routes, debug APIs или compatibility aliases;
- XP, levels, skill mastery, achievements, rewards или G5.2 behavior;
- изменения Cards, shared IA или generated dashboard assets.

## Production data sources

- identity: `profile.identity`;
- dates, reviews, streaks, study time и success rate:
  `profile.studyHistory`;
- heatmap и recent rows:
  `profile.activity.days`, `rangeStart`, `rangeEnd`,
  `recentActiveDays`;
- learning areas:
  `profile.decks.overview`, `profile.decks.total`;
- editable settings:
  `profile.preferences.customStudyStartedOn`,
  `profile.preferences.deckOverviewSort`;
- update transport: existing `saveProfilePreferences()` → `/api/profile`.

## Review и remediation

- `P0`: findings отсутствуют.
- `P1`, resolved: dialog первоначально наследовал transformed page containing
  block; portal в `document.body` восстановил viewport-fixed geometry и focus
  lifecycle.
- `P1`, resolved: первый real-Anki run обнаружил два `<main>` landmarks на
  Profile. Profile root заменён на neutral `div`, добавлен regression test на
  единственный application `main`.
- `P2`, resolved: synchronous save guard, normalization heatmap max и
  programmatic heading focus без лишнего outline.
- `P3`: открытых findings нет.

После final remediation открытых `P0/P1` нет. Это self-review и automated
evidence, а не внешний review и не owner acceptance.

## Verification

### Local focused and canonical checks

- `node scripts/run_python.mjs scripts/check_task_scope.py`: `PASS`, 14 paths;
- `git diff --check`: `PASS`;
- Profile, visual contract, localization, Settings consumer и profile API:
  `PASS`, 23/23 после landmark remediation;
- focused backend:
  `node scripts/run_python.mjs -m pytest tests/test_profile_service.py tests/test_dashboard_server.py -k profile`:
  `PASS`, 17 passed, 24 deselected;
- `pnpm run typecheck`: `PASS`;
- locale resource checks: `PASS`, 2/2;
- `pnpm run build:addon`: `PASS`;
- bundle guard: `PASS`, 21 JS chunks, entry 449824 bytes, total 1437236
  bytes / 406331 gzip;
- `node scripts/run_python.mjs scripts/package_addon.py --check`: `PASS`,
  97 entries;
- `node scripts/run_python.mjs scripts/package_addon.py --check-only`: `PASS`;
- `node scripts/run_python.mjs -m compileall -q anki_study_report`: `PASS`;
- `.\scripts\run_full_check.ps1 -SkipDocker`: `PASS` after stale Profile test
  expectations were synchronized with the current contract:
  77 frontend files / 415 tests, build and package checks, Python
  1131 passed / 8 skipped.

The local canonical run preceded the final landmark-only remediation. The same
canonical command ran successfully in final Fast CI on the exact final
package-impacting SHA.

### Final Fast CI

- run: [30492966246](https://github.com/AliceLiddell01/anki-study-report/actions/runs/30492966246);
- result: `PASS`;
- tested SHA:
  `5fd9c68dc1bd75b0ca1a6de20cc82a9957e1caab`;
- package artifact ID: `8740529133`;
- package artifact:
  `ci-package-5fd9c68dc1bd75b0ca1a6de20cc82a9957e1caab-30492966246-1`;
- artifact digest:
  `sha256:1d1c9ff10a0aa052b3f2f40eb4920f8210552dc59712fecf8a3319396398b78b`;
- package SHA-256:
  `f546e3f8269692cf6750413aae8f97183630a8d8e93866be34f20d2b84c19e3e`;
- package size: 782066 bytes;
- diagnostics artifact ID/digest:
  `8740528676` /
  `sha256:1379ebb7606e82958af625c8eaf217c0e6a10be380020c51e336d4d3b94bfc58`;
- downloaded evidence:
  `C:\Users\KykLa\AppData\Local\Temp\anki-profile-g5-1-final-fast-ci-e4c9970bfc6b4473948c0346301ef786`.

### Exact-package real-Anki proof

Risk-selected gate: `standard/global`, because the existing E2E contract maps
`profile` to `global`. Restart was not run: the diff changes frontend composition
only and keeps existing persistence/runtime behavior.

First run:

- [30492677856](https://github.com/AliceLiddell01/anki-study-report/actions/runs/30492677856):
  `FAIL`;
- exact earlier package SHA-256:
  `76049318a25a52583511b47a7ba75811f06d0050cb9df72b5c5f241a8fa47de1`;
- failure:
  `ASR-E2E-BROWSER-ITEM`, `route.profile.light`, duplicate `main` landmarks;
- artifact:
  `ci-e2e-standard-30492677856-1`, ID `8740363077`,
  digest
  `sha256:dfab0379f6e38dd59a57930b6d22ae619dec1f4c141ec4b478b9077646e4c9d9`;
- root cause fixed in `5fd9c68`.

Final run:

- [30493213517](https://github.com/AliceLiddell01/anki-study-report/actions/runs/30493213517):
  `PASS`;
- exact Fast CI package:
  `f546e3f8269692cf6750413aae8f97183630a8d8e93866be34f20d2b84c19e3e`;
- preflight: 20/20;
- API: `PASS`;
- browser plan: 23/23;
- screenshots: 18/18;
- `route.profile.light` / `route.profile.dark`: `PASS`, one screenshot each;
- real-deck manifest: `PASS`, three packages, 11 anchors, no synthetic fallback;
- collection inventory: `PASS`, 921 notes, 921 cards, 28 decks, 2153 media;
- package hash verification, artifact preparation и cleanup: `PASS`;
- artifact:
  `ci-e2e-standard-30493213517-1`, ID `8740585291`,
  digest
  `sha256:7f743f13c3415dc5b9685ff415c2b49672a45c996ff0ed7d6eabf9a43a7aa384`;
- artifact inventory: 64 files / 6075202 uncompressed bytes;
- downloaded evidence:
  `C:\Users\KykLa\AppData\Local\Temp\anki-profile-g5-1-final-e2e-a5d28e2e02634e72a39819ef1e05b30a`.

## Visual and interaction evidence

Local production-route evidence:

`C:\Users\KykLa\AppData\Local\Temp\anki-profile-g5-1-evidence-2026-07-30`

- 760, 1024, 1440, 2560 и 3840 in light/dark;
- 1440 settings open;
- 1440 save failure;
- 760 settings dialog;
- responsive geometry JSON for both themes;
- dialog/focus/error JSON;
- SHA-256 inventory;
- PNG decode: `PASS`, 13/13 captured PNGs;
- browser console errors/warnings: none;
- page-level horizontal overflow: none;
- 760 dialog is a direct `body` portal; `Escape` restores focus;
- reduced motion disables Profile button transitions.

The responsive/dialog set was captured before the final semantic-only
`main`→`div` remediation. Final-SHA real-Anki light/dark screenshots confirm the
same visual composition after that remediation.

Final real-Anki Profile screenshots:

- light SHA-256:
  `575ddb260c72d140e427e03142f40a05ca7ac57595fee1e57b3175f6ebabcd64`;
- dark SHA-256:
  `ff87adb700e88f1dbc77b5989f7d2d9f3ffabb1609fa2374c3ca932ff2ca179c`.

Low-data is represented by the final real-Anki profile with only two active days.
Long-identity and empty-data layout are covered by production component tests,
but a separate final-SHA long-identity PNG was not produced. This is an explicit
visual-evidence limitation, not a claimed visual PASS for that scenario.

Local screenshots, JSON evidence, archive material, logs and `.ankiaddon` files
are not tracked or committed.

Owner visual acceptance: `PENDING`.

## Git delivery

Commits:

- `ec37b9f07bbc4379ce7ac5cffd86afc1c9700237` —
  `docs: define production profile adaptation`;
- `f979dd60016f4b646f685203e07c06c62715404b` —
  `feat: build production profile foundation`;
- `5fd9c68dc1bd75b0ca1a6de20cc82a9957e1caab` —
  `fix: keep profile inside app main landmark`.

Все package-impacting commits pushed в `origin/chatGPT/G5`. Draft PR #182
направлен в `gamification`. Merge, release, publication и branch deletion не
выполнялись.

## Не запускалось и ограничения

- WebM reference motion evidence: `NOT INSPECTED`;
- real-Anki restart: `NOT RUN`, не требуется по фактическому frontend-only diff;
- `standard/full`: `NOT RUN`, targeted `standard/global` соответствует Profile
  mapping и shared runtime/server/package paths не менялись;
- owner visual review: `PENDING`;
- отдельный final-SHA long-identity screenshot: `NOT PRODUCED`;
- merge/release/publication: `NOT PERFORMED`;
- G5.2: `NOT STARTED`.

## Следующий шаг

Владельцу нужно выполнить visual review G5.1 candidate в Draft PR #182. Только
после отдельного owner decision допустимы merge/канонический статус; G5.2 не
начинался.
