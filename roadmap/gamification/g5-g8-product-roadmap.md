# Gamification G5–G8 — product roadmap после G4

**Track:** `G`  
**Canonical branch:** `gamification`  
**Planning status:** owner-approved direction  
**Implementation status:** `G5 IN PROGRESS / NOT COMPLETE`<br>
**Prepared from:** merged G4 state at `d70eb173af2d4618d82d8dfa7a149d212cd5710d`  
**Date:** 2026-07-29

> G5 должен закончиться первым рабочим MVP игрофикации, а не ещё одним этапом чистой теории. Архитектурный минимум создаётся внутри bounded vertical slice и только в объёме, необходимом этому MVP.

## 1. Исходное состояние после G4

```text
G4: COMPLETE
G4.4: COMPLETE
accepted evidence version: v4
final G4 outcome: REJECT
recommended integrated bundle: NONE
production integration: PROHIBITED
Review research winner: P-TAPER-ZERO-30D
Learn research winner: C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
Learn evidence status: CONFIRMATORY_INCONCLUSIVE
Learn limitation: DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE
Create domain: EXCLUDED
```

G4 дал воспроизводимое synthetic-only исследовательское решение, но не передал в production:

- общую Review + Learn XP формулу;
- допустимый integrated bundle;
- production payload или API;
- persistence/event-ledger contract;
- migrations и reconciliation;
- UI contract;
- production approval.

Все recommendation-eligible integrated bundles провалили хотя бы один non-compensable hard gate:

```text
HG-FALSE-POSITIVE-CONTEXT-HARM-BOUNDED
HG-EXTREME-VOLUME-BOUNDED
```

Passing isolated candidates нельзя объединять post hoc. G5 не переименовывает rejected bundle и не внедряет его скрытно.

## 2. Owner direction для G5–G8

Старая краткая последовательность:

```text
G5 — Production architecture foundation
G6 — Gamification MVP
```

заменяется продуктовой последовательностью:

```text
G5 — Study Rhythm MVP
G6 — Personal Progression Economy v1
G7 — Achievements Foundation
G8 — Skills, Quests and Domain Expansion
```

Новый статус:

```text
G5 — IN PROGRESS / NOT COMPLETE
G6 — CONDITIONAL / NOT STARTED
G7 — CONDITIONAL / NOT STARTED
G8 — DEFERRED / CONDITIONAL / NOT STARTED
```

Roadmap не активирует implementation автоматически. Для каждой нетривиальной реализации требуется отдельный bounded task contract и отдельная owner-authorized задача.

## 3. Общая концепция

```text
G4 REJECT integrated XP economy
        │
        ▼
G5 Study Rhythm MVP
real local data
opt-in settings
weekly plan
planned rest
today + weekly progress
no XP / no levels
        │
        ▼
G6 Personal Progression Economy v1
only after a new prospective economy gate
versioned ledger
Review-first XP/levels
explanations and reconciliation
Learn reward only after limitation closure
        │
        ▼
G7 Achievements Foundation
minimal explainable achievements
only for a concrete feedback gap
        │
        ▼
G8 Skills / Quests / Domain Expansion
one named workflow or domain at a time
Create XP only after its separate activation gate
```

Principles:

1. Local-first and profile-bound.
2. Frontend never reads the Anki collection directly.
3. No external server, mandatory account, leaderboard, marketplace or social pressure.
4. Every state is explainable and can be disabled.
5. Planned rest is neutral, not a failure.
6. No speculative routes, APIs, aliases or generic plugin framework.
7. UI must use real data and packaged execution; mock-only screens do not close a stage.
8. Design reference is adapted, not copied 1:1.
9. Motion is functional, bounded and reduced-motion safe.
10. G4 research winners remain research inputs, not production approval.

---

# G5 — Study Rhythm MVP

## 4. G5 goal

Create the first complete, visually polished and packaged Gamification feature on real local Anki Study Report data.

The user sets a realistic weekly study rhythm, sees today's state and weekly progress, and can plan rest without XP, levels or a rejected Review + Learn economy.

```text
G5 status: IN PROGRESS / NOT COMPLETE
G5.0: COMPLETE
G5.1: REMEDIATED CANDIDATE / OWNER ACCEPTANCE PENDING
G5.1 owner visual acceptance: PENDING
G5.1 merge: NOT PERFORMED
G5.2: NOT STARTED
G5 closes with: WORKING PACKAGED MVP
XP economy: OUT OF SCOPE
level system: OUT OF SCOPE
Learn XP: OUT OF SCOPE
Create XP: OUT OF SCOPE
production release: OUT OF SCOPE
```

## 5. Main user scenario

1. The user opens `#/gamification`.
2. First run shows a local opt-in onboarding.
3. The user chooses:
   - weekly active-day target `1..7`;
   - planned rest weekdays;
   - whether soft progress feedback is enabled.
4. Settings are saved atomically in profile-level runtime data.
5. The backend uses canonical existing `activityHub` and `profile` projections.
6. A pure service derives:
   - today's planned state;
   - activity present or absent;
   - completed active days;
   - weekly target progress;
   - planned rest;
   - remaining opportunities;
   - week completion;
   - coverage and limitations.
7. Strict token-protected API returns schema v1.
8. UI displays Today, weekly path, progress, recent context and calculation explanation.
9. After an Anki activity refresh, progress updates without full layout shift.
10. Settings survive restart and profile switching.
11. The user can change the plan or disable the feature without modifying collection data.

## 6. Why this is a real Gamification MVP

The MVP contains a complete loop:

```text
personal goal
→ real activity
→ visible progress
→ completion feedback
→ persistent plan
→ planned rest
→ history context
→ explanation
```

It is not merely another statistics page, because the user defines a persistent goal and receives stateful progress feedback. It is not an XP system, because G4 did not approve one.

## 7. Source data and boundaries

Allowed existing sources:

```text
StudyReport.activityHub
StudyReport.profile
existing report refresh lifecycle
existing current/best streak as supporting context only
```

Required boundaries:

- use canonical day/date semantics from `activityHub`;
- do not query raw revlog from frontend;
- do not create a second collection-reading path merely for Gamification;
- do not manually mark a day complete;
- do not mutate cards, notes, scheduler or FSRS;
- do not send telemetry;
- do not expose local paths, token-bearing URLs or raw collection content.

Existing streak fields may be displayed as context, but the new planned-rest-aware concept is named `Study Rhythm` / «учебный ритм», not silently redefined as the old streak.

## 8. G5 settings contract v1

Planned profile-level runtime file:

```text
<profile>/addon_data/<addon_id>/gamification_settings.json
```

Minimum settings:

```text
schemaVersion
revision
enabled
weeklyTargetDays: 1..7
plannedRestWeekdays: unique weekday ids
feedbackEnabled
```

Store requirements:

- strict schema v1;
- deterministic defaults;
- atomic write;
- optimistic revision;
- corrupt quarantine;
- future-schema fail closed;
- profile isolation;
- restart restoration;
- disable/reset semantics;
- no collection mutation.

## 9. Derived API model v1

Recommended endpoints:

```text
GET  /api/gamification
POST /api/gamification/settings
```

Minimum response:

```text
schemaVersion
generatedAt
availability
settings
coverage
today
week
historySummary
existingStreakContext
explanations
limitations
```

Suggested stable errors:

```text
400 invalid_gamification_request
403 forbidden
409 gamification_revision_conflict
503 gamification_unavailable
503 gamification_store_unavailable
```

API constraints:

- current dashboard token;
- loopback only;
- strict JSON and unknown-key rejection;
- bounded body size;
- exact schema version;
- no arbitrary query/RPC;
- no raw revlog, fields or media;
- no generic future extension payload.

## 10. Visual direction

The owner will provide one primary reference. It is a quality target, not an asset source or 1:1 template.

Before implementation, extract and map:

| Reference area | Extract | Map to current product | Do not copy |
|---|---|---|---|
| Layout | hierarchy, density, rhythm | route composition | brand-specific IA |
| Surfaces | elevation, borders, depth | existing surface tokens | exact effects/colors |
| Shape | radii and silhouettes | current radius scale | arbitrary giant rounding |
| Type | hierarchy and spacing | current font stack | proprietary fonts |
| Motion | duration and spatial relation | current motion tokens | decorative choreography |
| Interaction | focus, hover, loading | accessible states | mouse-only behavior |
| Feedback | progress and completion | semantic bounded animation | default confetti |

Current Core design primitives should be reused:

```text
surface roles
border/text/accent/status tokens
motion 90/140/190/240 ms
standard easing
control/item/region/panel radii
workspace page/region/interactive/selected roles
light and dark themes
RU and EN localization
```

Only minimal semantic Gamification aliases may be introduced, for example:

```text
--gamification-progress
--gamification-progress-soft
--gamification-rest
--gamification-complete
--gamification-planned
```

They must resolve through existing theme-aware tokens.

Motion rules:

- progress interpolation `190–240ms`;
- state transitions `140–190ms`;
- hover/press `90–140ms`;
- prefer transform/opacity;
- no blocking sequence or persistent animation;
- `prefers-reduced-motion` provides an equivalent non-motion state;
- no information conveyed by motion or color alone.

## 11. Planned UI composition

```text
GamificationPage
├─ page header
├─ GamificationOnboarding or enabled state
├─ RhythmHero
├─ TodayRhythmCard
├─ WeeklyPath
├─ RhythmProgress
├─ RhythmSummary
├─ RhythmExplanation
└─ RhythmSettingsPanel
```

Required states:

```text
disabled / first run
loading
ready
saving
saved
revision conflict
partial coverage
no activity
completed week
planned rest today
corrupt/future settings
unavailable
error
```

Required qualities:

- desktop-first at 1024 and QHD;
- stable skeleton geometry;
- no horizontal overflow;
- full keyboard operation;
- visible focus in light/dark;
- screen-reader labels and live save status;
- 200% zoom usability;
- route remains lazy-loaded;
- no regression to frozen Cards composition/styles.

## 12. G5 work packages

### G5.0 — Sync current Core into Gamification

**Goal:** establish a current production baseline before adding feature code.

Current starting fact at roadmap publication:

```text
gamification HEAD: d70eb173af2d4618d82d8dfa7a149d212cd5710d
core observed HEAD: 078b7358e31c68ba467608769e81ad5cf4a91d15
merge base: 62cd4c1fc1dda6354f3e30cb3ae4aee5dfb4891f
branches: diverged
```

Deliverable:

- separate bounded `core → gamification` sync PR;
- current production code/tests and AI rules imported;
- Gamification research tree preserved;
- shared docs manually reconciled;
- no G5 feature code in the sync PR.

Checks are selected by the complete diff. Because the package baseline changes, focused checks, non-Docker checks, frontend build, package validation and a package-producing Fast CI are expected; E2E scope follows the verification planner.

### G5.1 — Profile Production Foundation

**Goal:** adapt the supplied Profile reference into a production-quality
foundation on the existing live `#/profile` route and existing
`StudyReport.profile` contract.

Candidate deliverable:

- reference CRC/checksum/inventory and adaptation ledger;
- identity-first composition;
- real main decks from `profile.decks.overview`, with canonical hierarchy
  preserved and no domain inference;
- factual six-metric Status with primary/secondary hierarchy, compact/full
  factual Activity and quiet recent history;
- one accessible settings dialog for existing `customStudyStartedOn` and
  `deckOverviewSort`;
- RU/EN, light/dark, responsive and reduced-motion-safe behavior;
- objective visual evidence and explicit ADAPT/IMPROVE/DEFER/REJECT decisions.

The implementation candidate changes no backend/public schema and introduces no
XP, levels, achievements, skills, new routes or placeholder systems. Canonical
completion remains blocked on exact-SHA gates, owner visual acceptance and
merge. G5.2 is not started.

### G5.2 — Freeze minimal MVP contract

**Goal:** freeze only the settings, source-data and derived-state fields required by the vertical slice.

Deliverable:

- human contract;
- strict schemas or validators where appropriate;
- backend/frontend type agreement;
- calculation/version identifiers;
- no XP, levels, achievements or quest placeholders.

### G5.3 — Implement local store and pure rhythm service

**Goal:** create the smallest backend foundation required by the MVP.

Deliverable:

- profile-level settings store;
- deterministic pure service;
- ordinary and boundary fixtures;
- corrupt/future/revision behavior;
- profile-switch and restart behavior.

Focused Python tests and `compileall` are mandatory. The service should be testable without installed Anki.

### G5.4 — Implement bounded local API

**Goal:** expose canonical settings and derived state through strict token-protected endpoints.

Deliverable:

- GET projection;
- settings update;
- exact error mapping;
- token, method, body, schema and conflict tests;
- synchronized API documentation.

### G5.5 — Create route shell and design primitives

**Goal:** integrate `#/gamification` into current navigation and establish a polished, extensible page foundation.

Deliverable:

- lazy route;
- RU/EN strings;
- stable skeleton;
- reference-adapted composition;
- minimal semantic tokens;
- visual contract tests.

No redesign of Cards, Statistics, Settings or shared IA is included.

### G5.6 — Implement onboarding and settings interaction

**Goal:** complete first-run opt-in and configuration.

Deliverable:

- strict frontend parser/client;
- latest-wins reads;
- serialized mutation;
- field validation;
- revision-conflict recovery;
- accessible save/error status.

### G5.7 — Implement real-data weekly rhythm loop

**Goal:** complete the main user scenario on real `activityHub` data.

Deliverable:

- Today state;
- weekly path;
- target progress;
- planned rest;
- remaining opportunities;
- recent summary;
- existing streak context;
- explanation and limitations;
- refresh update without layout jump.

### G5.8 — Accessibility, motion and performance hardening

**Goal:** bring the MVP to production-quality interaction.

Deliverable:

- reduced motion;
- keyboard/focus behavior;
- semantic progress;
- contrast-safe states;
- bounded rerenders;
- bundle-size verification;
- loading and error geometry.

### G5.9 — Packaged integration and real-Anki evidence

**Goal:** prove the full vertical slice in the packaged add-on.

Required contour:

```text
focused backend tests
focused frontend tests
typecheck
frontend production build
package validation
package-producing Fast CI
one risk-selected real-Anki gate
restart verification
light/dark screenshots
reduced-motion proof
```

Representative scenarios:

1. first-run disabled;
2. enable and save;
3. active current week;
4. planned rest;
5. completed week;
6. no activity;
7. partial or unavailable data;
8. restart and restore;
9. invalid token;
10. revision conflict.

Prefer a bounded extension of `standard/activity` with `verify_restart=true`. Escalate to `standard/full` only when the actual shared server/profile/package diff requires it.

### G5.10 — Bounded remediation and owner acceptance

**Goal:** fix only evidence-backed deviations.

Deliverable:

- severity-ordered deviation ledger;
- one implementation remediation pass;
- one independent diff review;
- rerun only affected checks;
- explicit owner visual verdict.

No adjacent Core cleanup or G6 work is allowed.

### G5.11 — Closeout and canonical synchronization

**Goal:** close G5 only after a working packaged MVP exists.

Closeout records:

```text
exact branch/base/HEAD
commits and PR
route
API schema
store schema
calculation version
implemented states
tests/build/package/Fast CI
E2E identities and artifacts
visual evidence
known limitations
deferred G6–G8 work
```

Canonical README, AI handoff, API, architecture, frontend map, test matrix and roadmap are synchronized only with facts that were actually implemented and verified.

## 13. G5 completion criteria

G5 is complete only when all are true:

- `#/gamification` runs from the packaged add-on;
- the route is reachable from the production UI;
- it uses real local data, not mock-only fixtures;
- opt-in settings persist per Anki profile;
- profile switch and restart are correct;
- planned rest is neutral and understandable;
- all normal, empty, partial, conflict and error states exist;
- RU/EN, light/dark and reduced motion work;
- backend/API/frontend tests pass;
- typecheck and production build pass;
- package validation and package-producing Fast CI pass;
- risk-required real-Anki evidence passes;
- owner visual acceptance is explicitly granted;
- XP, levels, Learn XP and Create XP were not smuggled into the scope;
- documentation records exact evidence and what was not run.

The following do **not** close G5:

- Markdown-only design;
- static mockup;
- component gallery;
- mock-only route;
- unpersisted controls;
- screenshots without packaged execution;
- XP values without an approved economy;
- starting G6 before G5 closeout.

---

# G6 — Personal Progression Economy v1

## 14. Activation gate

```text
G5 COMPLETE
AND explicit owner approval
AND new prospective economy protocol published before result access
AND uncertainty hard gate passed
AND high-volume bounding passed
AND production integration explicitly approved
```

G6 must not reinterpret G4 v4 or tune it post hoc.

## 15. Intended result

Add explainable local XP/levels and deterministic reconciliation on top of the stable Study Rhythm MVP.

Likely bounded direction if Learn limitation remains open:

```text
Review-first XP only
Learn XP disabled
cross-domain conversion absent
```

Planned foundations:

- versioned event ledger;
- idempotency and duplicate protection;
- undo/replay semantics;
- deterministic recomputation;
- migrations;
- formula versioning;
- XP history and explanation;
- level curve;
- opt-out/reset;
- no spendable currency.

G6 research must resolve the causes of `G4 REJECT`, not bypass them.

---

# G7 — Achievements Foundation

## 16. Activation gate

G7 starts only after G5/G6 evidence identifies a concrete feedback gap that cannot be solved by the existing rhythm/progression UI.

## 17. Intended result

Add a small deterministic achievement registry with stable IDs, local unlock history and transparent criteria.

Possible bounded categories, subject to evidence:

- first weekly plan completion;
- sustained weekly rhythm;
- return after a break;
- long-term consistency milestone.

Do not reward:

- raw clicks or refreshes;
- repeated Again loops;
- previews;
- destructive volume farming;
- arbitrary content creation.

Required properties:

- deterministic and idempotent unlock;
- no duplicate unlock;
- bounded retroactive policy;
- optional notifications;
- accessible non-motion feedback;
- no external asset dependency;
- migration/version behavior.

---

# G8 — Skills, Quests and Domain Expansion

## 18. Intended result

Add one named, evidence-backed workflow or domain at a time without creating a generic life-tracking framework.

Possible sequence:

1. Review-focused skill path.
2. Learn-focused path only after identity limitation closure.
3. Deck-specific goal only after anti-farming semantics are proven.
4. Create domain only after its original activation gate:

```text
FIRST_STABLE_GAMIFICATION_RELEASE
AND SEPARATE_OWNER_DECISION
AND CONCRETE_EVIDENCE_BACKED_PRODUCT_TRIGGER
```

Required boundaries:

- no arbitrary user scripting;
- no generic plugin framework;
- no marketplace or social layer;
- deterministic quest completion;
- explicit expiration/rest semantics;
- versioned local state;
- no speculative empty routes;
- no Create XP without a separate accepted contract.

---

## 19. Dependency graph

```text
G4 COMPLETE / REJECT
│
├─ preserves research winners
├─ rejects integrated production economy
└─ requires separate production decisions
        │
        ▼
G5.0 Core sync
        │
        ▼
G5.1 Reference adaptation
        │
        ▼
G5.2 Minimal MVP contract
        │
        ├───────────────┐
        ▼               ▼
G5.3 Store/service   G5.5 UI shell
        │               │
        ▼               │
G5.4 API               │
        └───────┬───────┘
                ▼
G5.6 Onboarding/settings
                ▼
G5.7 Real-data rhythm loop
                ▼
G5.8 UX/a11y/performance
                ▼
G5.9 Fast CI/E2E/evidence
                ▼
G5.10 Remediation/acceptance
                ▼
G5.11 Closeout
                │
                ▼
G6 conditional economy
                │
                ▼
G7 achievements
                │
                ▼
G8 bounded expansion
```

## 20. Production boundary at planning time

G5.1 has an owner-authorized remediated candidate. Owner visual acceptance and
merge remain pending; later stages remain planning only.

```text
production code changed: G5.1 FRONTEND CANDIDATE ONLY
frontend changed: YES — existing #/profile composition
payload/API changed: NO
persistence changed: NO
package changed: PACKAGE-IMPACTING FRONTEND CANDIDATE
release changed: NO
G5.1: REMEDIATED CANDIDATE / OWNER ACCEPTANCE PENDING
G5.1 owner visual acceptance: PENDING
G5.1 merge: NOT PERFORMED
G5.2 started: NO
G6/G7/G8 started: NO
```

`gamification → master`, package inclusion, production integration, release and publication remain prohibited without separate owner decisions and the required verification evidence.
