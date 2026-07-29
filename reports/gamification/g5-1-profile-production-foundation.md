# G5.1 Profile Production Foundation — delivery and remediation report

Дата: 2026-07-30
Mode: Codex
Repository: `AliceLiddell01/anki-study-report`
Checkout: `C:\Users\KykLa\Documents\anki-study-report`
Branch / base: `chatGPT/G5` / `gamification`
Remediation initial HEAD: `9330f79bf68c72f36c9f43898a72d8e55bdaa40a`
Initial package-impacting SHA: `5fd9c68dc1bd75b0ca1a6de20cc82a9957e1caab`
Final package-impacting SHA: `18a39594e51848ad0355bed39d5e1dcf65e41402`
Draft PR: [#182](https://github.com/AliceLiddell01/anki-study-report/pull/182)

## Статус

```text
G5: IN PROGRESS
G5.0: COMPLETE
G5.1: REMEDIATED CANDIDATE / OWNER ACCEPTANCE PENDING
G5.1 owner visual acceptance: PENDING
G5.1 merge: NOT PERFORMED
G5.2: NOT STARTED
G5 overall: NOT COMPLETE
```

Это технически подтверждённый кандидат для повторного owner visual review.
Документ не назначает visual score, не объявляет owner acceptance и не разрешает
merge.

## Reference integrity и production mapping

Исходный `profile-mock-v0.4-fixed.zip` был проверен в предыдущем delivery pass:

- archive SHA-256:
  `8713ddd025512b2d47d85adb4c50f08e9b79020496685f1267eff883815aeb09`;
- ZIP CRC: `PASS`;
- `checksums.sha256`: `PASS`, 75/75 entries;
- extracted inventory: 76 files;
- archive, extracted materials и reference screenshots не копировались в
  repository.

Полный pattern-by-pattern ledger находится в
`docs/gamification/profile-g5-1-production-foundation.md`.

- `ADAPT`: factual identity metadata, canonical deck rows, recent history,
  semantic light/dark hierarchy и bounded responsive layout.
- `IMPROVE`: integrated identity hero, truthful main-deck presentation, factual
  Status hierarchy, compact/full Activity presentation, accessible settings
  dialog и fail-open motion.
- `DEFER`: Level/XP, achievements и explainability до отдельного approved product
  contract; для них не резервируется пустое место.
- `REJECT`: skill XP/levels, next achievement, hardcoded mock domains/numbers,
  standalone `localStorage`, demo avatar/banner assets, HTML/CSS copy,
  speculative routes/APIs и domain inference из deck names.

Production foundation остаётся factual:

- identity: `profile.identity`;
- dates, reviews, streaks, study time и success rate:
  `profile.studyHistory`;
- heatmap и recent rows:
  `profile.activity.days`, `rangeStart`, `rangeEnd`,
  `recentActiveDays`;
- canonical deck rows:
  `profile.decks.overview`, `profile.decks.total`;
- editable settings:
  `profile.preferences.customStudyStartedOn`,
  `profile.preferences.deckOverviewSort`;
- mutation:
  `saveProfilePreferences()` → existing token-protected `POST /api/profile`.

Backend, public payload, API и persistence contract не изменены. Frontend не
получил direct collection access, новый store, browser storage, upload/media
storage или дополнительные requests.

## Реализованная remediation

Порядок `#/profile` сохранён:

1. compact identity-first hero с deterministic initials, factual metadata и
   anchored settings action;
2. до четырёх canonical main decks плюс truthful deck remainder;
3. factual Status с двумя primary и четырьмя secondary metrics;
4. factual Activity с deterministic compact/full presentation;
5. recent history;
6. один portal-based settings dialog.

### Accessibility

- initial focus остаётся на dialog heading
  `#profile-settings-title`;
- `Shift+Tab` от initial heading направляется к последнему enabled control;
- forward `Tab` от последнего control замыкается на первый enabled control;
- при save state без enabled controls `Tab` остаётся на heading;
- `Escape` закрывает dialog, когда save не выполняется, и не нарушает save state;
- focus после закрытия возвращается на исходный trigger;
- dirty backdrop click не отбрасывает изменения;
- dialog сохраняет `aria-modal`, body portal и visible focus styles;
- reduced motion отключает decorative transitions и не зависит от animation
  callback.

### Product honesty и visual hierarchy

- RU/EN используют `Основные колоды` / `Main decks`, а remainder считает decks,
  не areas;
- hierarchical `::` names показываются как parent path + leaf, но полный
  canonical name сохраняется в `aria-label`, `title` и
  `data-canonical-name`;
- sorting продолжает задаваться существующим backend preference;
- typography floor: minor non-critical labels не ниже `0.72rem`, normal
  supporting text не ниже `0.75rem`;
- hero стал компактнее и объединяет banner, avatar, identity и settings action;
- Status выделяет total reviews и active days как primary factual group,
  остальные четыре значения остаются compact secondary metrics;
- Activity использует compact composition для короткого фактического диапазона и
  full bounded heatmap для более длинного диапазона;
- light/dark surfaces получили различимую глубину и иерархию через существующие
  semantic tokens;
- Profile root остаётся neutral container и не создаёт nested `<main>`.

Не добавлены XP, levels, mastery, achievements, rewards, quests, goals,
Study Rhythm behavior, fake profile completion или G5.2 mechanics. Существующие
Profile links по-прежнему ограничены `#/decks` и `#/calendar`.

## Resolved review findings

- `P0`: findings отсутствуют.
- `P1`: incomplete reverse focus boundary от initial heading исправлена;
  forward/reverse wrapping, save-state containment, Escape и focus return
  покрыты component tests и final-SHA browser evidence.
- `P2`: устранены rejected micro typography, misleading learning-area
  terminology, weak/empty hero composition, flat Status, excessive low-data
  Activity space, недостаточная light/dark hierarchy и неполный visual-evidence
  set.
- `P3`: roadmap и focused docs согласованы с состоянием
  `G5 IN PROGRESS`, `G5.1 REMEDIATED CANDIDATE / OWNER ACCEPTANCE PENDING`,
  `G5.2 NOT STARTED`.

Открытых `P0/P1` после bounded self-review нет. Это self-review,
automated/cloud verification и real-Anki evidence, а не внешний review и не
owner acceptance.

## Verification

### Local focused and canonical checks

- focused frontend:
  `pnpm.cmd exec vitest run src/pages/ProfilePage.test.tsx src/pages/ProfileVisualContract.test.ts src/pages/LocalizationSmoke.test.tsx src/pages/SettingsHub.test.tsx src/lib/profileApi.test.ts`:
  `PASS`, 5 files / 26 tests;
- `pnpm.cmd run typecheck`: `PASS`;
- `pnpm.cmd run build:addon`: `PASS`;
- bundle guard: `PASS`, 21 JS chunks, entry `451579` bytes,
  total `1438991` bytes / `406705` gzip;
- `node scripts/run_python.mjs scripts/package_addon.py --check`:
  `PASS`, 97 entries;
- `node scripts/run_python.mjs scripts/package_addon.py --check-only`: `PASS`;
- Python compilation:
  `node scripts/run_python.mjs -m compileall -q anki_study_report`: `PASS`;
- `.\scripts\run_full_check.ps1 -SkipDocker`: `PASS`,
  77 frontend files / 418 tests, build/package checks and Python
  1131 passed / 8 skipped;
- `node scripts/run_python.mjs scripts/check_task_scope.py`: `PASS`,
  15 paths in the complete base diff;
- `git diff --check`: `PASS`;
- final diff against `origin/gamification`, remediation diff, conflict markers,
  added-line secret heuristic, generated/binary surprises, forbidden labels and
  routes, external assets, `localStorage` and direct collection access:
  checked, no remediation blocker found.

`SettingsHub.test.tsx` already existed in the branch diff before this remediation
and was not modified by the corrective pass. It remains in the task-contract
allowlist because the required focused command explicitly includes that
consumer test.

### Final Fast CI

- run:
  [30497162295](https://github.com/AliceLiddell01/anki-study-report/actions/runs/30497162295);
- result: `PASS`;
- tested SHA:
  `18a39594e51848ad0355bed39d5e1dcf65e41402`;
- package artifact ID: `8742138952`;
- package artifact:
  `ci-package-18a39594e51848ad0355bed39d5e1dcf65e41402-30497162295-1`;
- package size: `782828` bytes;
- exact package SHA-256:
  `62d20838efafa6cd296a850549ce78c0dd268e64953ec86cb189882333777eca`;
- artifact transport digest:
  `sha256:b17fc121c03aaf1aa1b5baa4bdee498749b82e0c240bc06f6b9f52ddb6dc34b3`;
- diagnostics artifact ID/digest:
  `8742138277` /
  `sha256:a0c0c5aca34e22a9ad7341116535e3bac38a6af4aa5baa678695932569fba52f`;
- downloaded package evidence:
  `C:\Users\KykLa\AppData\Local\Temp\anki-profile-g5-1-fast-ci-18a39594e51848ad0355bed39d5e1dcf65e41402`.

### Exact-package real-Anki proof

Risk-selected gate: `standard/global`; the existing E2E contract maps Profile to
`global`. Restart не запускался, поскольку remediation меняет frontend
composition/accessibility и не меняет persistence/runtime.

- run:
  [30497569031](https://github.com/AliceLiddell01/anki-study-report/actions/runs/30497569031):
  `PASS`;
- workflow, checkout и trigger SHA:
  `18a39594e51848ad0355bed39d5e1dcf65e41402`;
- source: exact successful Fast CI package;
- package SHA-256:
  `62d20838efafa6cd296a850549ce78c0dd268e64953ec86cb189882333777eca`;
- preflight: `PASS`, 20/20;
- API: `PASS`;
- browser plan: `PASS`, 23/23;
- screenshots: `PASS`, 18/18;
- `route.profile.light` / `route.profile.dark`: `PASS`, one full-page
  screenshot each;
- landmark invariant: `PASS`; both canonical Profile route captures completed
  under the unique application-main check, а component regression сохраняет
  neutral Profile root;
- real-deck manifest: `PASS`, 3 packages, 11 anchors,
  `syntheticFallback: false`;
- collection inventory: 921 notes, 921 cards, 28 decks, 2153 media;
- exact package hash verification: `PASS`;
- artifact preparation, public validation, source validation и cleanup: `PASS`;
- restart: `NOT RUN`;
- artifact ID: `8742244301`;
- artifact:
  `ci-e2e-standard-30497569031-1`;
- artifact transport digest:
  `sha256:f978892e948da472692f495e1a2c76ff9b6f2496084eb4b4d19884fcfd891d0d`;
- artifact inventory: 64 files / 6258769 uncompressed bytes;
- downloaded evidence:
  `C:\Users\KykLa\AppData\Local\Temp\anki-profile-g5-1-e2e-18a39594e51848ad0355bed39d5e1dcf65e41402`.

## Final-SHA visual and interaction evidence

Evidence directory:

`C:\Users\KykLa\AppData\Local\Temp\anki-profile-g5-1-remediation-18a39594e51848ad0355bed39d5e1dcf65e41402`

Inventory:

- 20 PNG total;
- deterministic frontend fixture, representative populated:
  760, 1024, 1440, 2560 и 3840 in light/dark;
- deterministic special states:
  empty, long identity, settings open, settings save failure, initial focus,
  `Shift+Tab` boundary, keyboard focus-visible и reduced motion;
- explicitly labelled canonical real-Anki low-data:
  light/dark from run `30497569031`;
- every record contains viewport, theme, state, source type and
  package-impacting SHA;
- PNG decode and per-file SHA-256/dimension match: `PASS`, 20/20;
- inventory SHA-256:
  `0b5649263ffa17a9ce6f36bffdfd2ff804414ede75a8f287e2818ca87ea9d497`;
- page horizontal overflow: none in every measured fixture state;
- application main: exactly one in every measured fixture viewport/state;
- normal fixture console: 0 errors / 0 warnings;
- intentional save-failure fixture: one expected failed-resource event from
  HTTP 500 / 0 warnings, with handled UI error;
- canonical real-Anki browser report: no console events, page errors, failed
  requests or unexpected external requests.

The deterministic fixture imports the exact committed Profile component and uses
a synthetic deterministic report. It is not real user data. The two real-Anki
images are separately labelled and come from the exact Fast CI package exercised
by canonical Docker E2E.

### Before/after visual ledger

| Finding | Change | Final evidence | Result |
| --- | --- | --- | --- |
| Initial-heading reverse boundary allowed focus escape | Route `Shift+Tab` to last enabled control and cover both wrap directions | `fixture-1440-light-initial-focus.png`, `fixture-1440-light-shift-tab-boundary.png` | `PASS` |
| Supporting labels used rejected micro sizes | Enforce Profile-specific `0.72rem` / `0.75rem` floors and rebalance spacing | populated 760/1024/1440 light/dark | `PASS` |
| Canonical decks were described as semantic areas | Use main-deck terminology and parent-path/leaf rendering while preserving canonical identity | `fixture-1440-light-populated.png`, `real-anki-low-data-light-run-30497569031.png` | `PASS` |
| Hero was tall and visually detached | Integrate avatar, identity, metadata and action in one compact surface | populated fixture set and both real-Anki images | `PASS` |
| Six Status metrics had equal weight | Introduce two-metric primary group plus four secondary metrics | `fixture-1440-light-populated.png`, `fixture-1440-dark-populated.png` | `PASS` |
| Short Activity range left unjustified empty composition | Select compact presentation from factual available range | `real-anki-low-data-light-run-30497569031.png`, `real-anki-low-data-dark-run-30497569031.png` | `PASS` |
| Light/dark hierarchy was too uniform | Differentiate hero, main content, Status, Activity and history with semantic surfaces/depth | 1440/2560/3840 light/dark | `PASS` |
| Empty, long identity, failure, focus and motion evidence was incomplete | Capture and inventory all required final-SHA special states | corresponding `fixture-1440-*` PNGs | `PASS` |

Screenshots, JSON evidence, logs, archive material и `.ankiaddon` не tracked и не
committed.

Owner visual acceptance: `PENDING`.

## Git delivery

Remediation package-impacting commit:

- `18a39594e51848ad0355bed39d5e1dcf65e41402` —
  `fix: remediate profile focus and visual hierarchy`.

Evidence report доставляется отдельным docs-only descendant, поэтому этот файл
намеренно не содержит self-referential commit SHA. Exact final PR HEAD
фиксируется в PR body и delivery handoff после push.

Все commits pushed normal fast-forward в `origin/chatGPT/G5`. Draft PR #182
направлен в `gamification`. Merge, release, publication, branch deletion и
history rewrite не выполнялись.

## Не запускалось и ограничения

- WebM reference motion evidence: `NOT INSPECTED`; motion conclusions опираются
  на written contract, storyboards и final-SHA reduced-motion checks;
- real-Anki restart: `NOT RUN`, не требуется для frontend-only diff;
- `standard/full`: `NOT RUN`, targeted `standard/global` соответствует Profile
  integration risk;
- owner visual review: `PENDING`;
- merge/release/publication: `NOT PERFORMED`;
- G5.2: `NOT STARTED`.

## Следующий шаг

Владельцу нужно выполнить повторный visual review G5.1 candidate в Draft PR
#182 по final-SHA evidence. Только отдельное owner decision может разрешить
merge и canonical completion; G5.2 не начинался.
