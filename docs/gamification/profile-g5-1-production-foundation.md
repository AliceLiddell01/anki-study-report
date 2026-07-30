# G5.1 Profile Production Foundation

Статус документа: production adaptation contract для implementation candidate.

```text
G5: IN PROGRESS
G5.0: COMPLETE
G5.1: REMEDIATED CANDIDATE / OWNER ACCEPTANCE PENDING
G5.1 owner visual acceptance: PENDING
G5.1 merge: NOT PERFORMED
G5.2: NOT STARTED
G5 overall: NOT COMPLETE
```

## Reference integrity

Источник: внешний `profile-mock-v0.4-fixed.zip`; архив и извлечённые материалы не
копируются в repository.

```text
ZIP CRC: PASS
archive SHA-256: 8713ddd025512b2d47d85adb4c50f08e9b79020496685f1267eff883815aeb09
checksums.sha256: PASS, 75/75 entries
inventory: 76 files
```

Фактически открыты обязательные README, changelog, design/IA/status/responsive/
motion/accessibility/performance документы, machine-readable audits, полный
`prototype.html`, обязательные 1024/1440/QHD light/dark screenshots, low-data,
long-identity, gamification-disabled и v0.3/v0.4 comparison. WebM в доступной
Codex surface не воспроизводился; вместо него открыты representative page
entrance, reduced-motion, customization-save и skills storyboards. Поэтому
video inspection имеет статус `NOT INSPECTED`.

## Production truth

G5.1 не расширяет существующий public contract:

```text
StudyReport.profile.identity
StudyReport.profile.studyHistory
StudyReport.profile.activity
StudyReport.profile.decks
StudyReport.profile.preferences
```

Разрешённые mutations остаются прежними:

```text
POST /api/profile
customStudyStartedOn
deckOverviewSort
```

Frontend не читает collection, raw revlog, profile paths или media и не
использует `localStorage` как source of truth для Profile.

## Production adaptation ledger

| Reference pattern | Observed purpose | Production data source | Decision | Production implementation | Reason | Acceptance evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Hero/banner/avatar composition | Мгновенно сделать профиль личной поверхностью | `profile.identity`, `profile.studyHistory` | IMPROVE | Compact integrated hero, deterministic initials, factual dates и settings action | Внешние и demo assets не нужны; identity остаётся главным объектом | Profile tests; 760–4K light/dark screenshots |
| Identity label and metadata | Объяснить локальную природу и исторический диапазон | `identity.label`, `displayName`, `displayedStartedOn`, `statsAvailableFrom`, `activeDays` | ADAPT | Локализованный label и только фактические метаданные | Backend не предоставляет bio, account tier или editable name | RU/EN and long-identity tests |
| Persistent Level/XP strip | Показать общую progression identity | Нет approved production source | DEFER | Не рендерить в G5.1 | G4 outcome `REJECT`; approved economy отсутствует | Forbidden-label tests |
| Skills cards | Сделать реальные колоды заметнее analytics | `profile.decks.overview` | IMPROVE | `Main decks / Основные колоды`: canonical deck name, `totalReviews`, `activeDays`; до четырёх cards и bounded remainder | Deck остаётся колодой; UI не выдаёт её за domain, skill или learning area | Data mapping, arbitrary-name and order tests |
| Hardcoded Japanese/Grammar/Java/English domains | Дать mock выразительные разные области | Нет production source | REJECT | Не выводить mock domains или domain inference | Имена и порядок должны приходить из текущего Anki profile | Representative arbitrary-deck test |
| Status surface | Сконцентрировать локальный system-like акцент | `studyHistory` | IMPROVE | Factual surface: reviews и active days в primary group, четыре остальные lifetime metrics в secondary group | Сохраняет направление mock без оценок пользователя и устраняет равный вес шести cards | Metric hierarchy and unavailable-value tests |
| Study Rhythm preview | Показать план недели | Нет G5.2 settings/service | REJECT | Не рендерить plan, rest weekdays или judgment | Это отдельный store/API и будущий contract | Forbidden-copy tests |
| Activity heatmap | Быстро показать реальную плотность истории | `profile.activity.days`, `rangeStart`, `rangeEnd` | IMPROVE | Compact summary + factual grid для короткого диапазона; bounded 182-day composition для длинного; link `#/calendar` | Не создаёт пустое пространство и не дорисовывает дни вне доступного range | Compact/full, empty and responsive tests |
| Achievement sidebar | Добавить долгосрочные milestones | Нет achievement registry | DEFER | Не рендерить и не оставлять пустое место | G7 не активирован | Forbidden-label tests |
| Next achievement | Создать ближайший ориентир | Нет approved threshold/registry | REJECT | Не рендерить countdown или nearest milestone | Иначе значение было бы fabricated | Forbidden-label tests |
| Progress history | Дать компактный конец страницы | `profile.activity.recentActiveDays` | ADAPT | Три newest rows по умолчанию; disclosure до доступных семи | Это factual recent history, не milestones | Collapsed/expanded tests |
| Customization drawer | Объединить profile settings | `profile.preferences` | IMPROVE | Accessible dialog только для start date и deck sort | Upload/name/bio/accent controls не поддержаны backend | Focus, Escape, save/reset/failure tests |
| Explainability dialog | Объяснить mock XP/status | Нет отдельного factual contract сверх captions | REJECT | Не добавлять постоянную secondary dialog | Inline labels и source captions достаточны | No unexplained affordance review |
| Page entrance motion | Подчеркнуть hierarchy | Existing motion tokens | IMPROVE | Основной content видим сразу; Profile root не использует transform/opacity entrance | Убирает 780 ms choreography, invisible-parent risk и fixed-dialog containing block | CSS visual contract; reduced motion |
| Hover/focus motion | Показать интерактивность | Existing motion/focus tokens | ADAPT | 90–140 ms hover/press, visible focus, no persistent animation | Functional feedback без декоративного движения | CSS and keyboard tests |
| Light/dark palette | Сохранить semantic parity | Existing theme tokens | ADAPT | Только project tokens и bounded profile accents | Exact mock colors/shadows не копируются | Theme screenshots |
| 760/1024/QHD/4K layout | Использовать desktop пространство | Existing App Shell width plus Profile CSS | IMPROVE | Main decks reflow 1–3 columns, Status primary/secondary groups остаются различимы, Activity compact layout stacks на bounded breakpoint | Mock слишком плотный в 1024 и слишком мелкий в QHD | Geometry/overflow evidence |
| Low-data state | Не ломать hierarchy при малом объёме | Empty/short arrays and nullable metrics | IMPROVE | Честные empty blocks и unavailable values без fake zero progress | Production data может быть частичной или пустой | Focused low-data tests |
| Gamification-disabled state | Показать feature toggle | Toggle отсутствует | REJECT | Не добавлять fake disabled surface | Public contract не содержит feature state | No speculative state test |
| Long identity stress | Сохранить действия и полное имя | `identity.displayName` | ADAPT | Wrapping, `title`, min-width containment и responsive action | Имя нельзя обрезать без доступного полного значения | Long-identity focused test |
| External/demo assets | Усилить персональность | Нет безопасного media endpoint для Profile | REJECT | Не использовать `demo-avatar.svg`, `demo-banner.svg` или upload controls | Не расширять media/security scope | Dependency/source scan |
| Standalone `localStorage` behavior | Симулировать сохранение mock | Existing token-protected profile store | REJECT | Только `/api/profile` и `onReportUpdated` | Browser storage не является Profile source of truth | API request tests |
| Full HTML/CSS copy | Быстро повторить mock | Не применимо | REJECT | Новая React composition на существующих tokens | Prototype не является production source | Full diff review |

## Intended improvements over the mock

- Profile остаётся identity-first, но не занимает место несуществующими
  Level/XP/Achievements surfaces.
- Main decks используют текущие реальные canonical deck names и только factual
  review/active-day counts; hierarchy отображается без domain inference.
- Status визуально различает primary и secondary facts, но не делает judgment о
  дисциплине, интеллекте, стабильности или mastery.
- Short-range Activity использует компактную factual composition и не
  дорисовывает отсутствующие дни.
- Supporting text не опускается до 8–10 px; hierarchy читаема в RU и EN.
- Основной content видим до и независимо от animation callbacks.
- 1024 получает спокойный reflow, а QHD/4K — bounded readable composition вместо
  механического растягивания.
- Settings показывают только реально сохраняемые поля и используют существующий
  token-protected API.
- Empty, unavailable и long-text states являются обычными production states, а
  не debug-only screenshots.

## Objective acceptance

- DOM и visual order: hero → main decks → Status → Activity → recent history.
- Нет labels/values XP, levels, achievements, mastery, quests или speculative routes.
- `profile.decks.overview` является единственным источником main decks.
- `studyHistory` остаётся единственным источником Status.
- `activity.days` и `recentActiveDays` остаются единственными источниками Activity/history.
- Основной content fail-open; no persistent animation.
- Visible focus, initial focus, Tab/Shift+Tab containment, Escape и focus return работают.
- 760/1024/1440/2560/3840 не имеют page-level horizontal overflow.
- RU/EN и light/dark сохраняют одинаковую hierarchy.
- Owner visual acceptance остаётся отдельным human gate.
