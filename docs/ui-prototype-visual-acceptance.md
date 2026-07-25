# Процесс UI-прототипирования и визуальной приёмки

**Статус документа:** актуальный обязательный процесс для крупных изменений dashboard UI  
**Снимок:** 2026-07-23  
**Основной пример:** `#/cards` как эталон общей UI-системы; Inspection Profiles как эталон сложного editor/form workflow

## Назначение

Этот документ определяет, как проектируетcя, проверяется, принимается и только затем переносится в production сложный интерфейс Anki Study Report.

Процесс применяется, когда изменение затрагивает хотя бы одно из следующего:

- общий App Shell или композицию нескольких страниц;
- новую визуальную грамматику;
- сложный workspace с несколькими областями;
- очередь, Inspector, drawer или modal;
- многошаговый action/status/recheck workflow;
- формы с draft, validation и несколькими режимами;
- responsive/reflow-контракт desktop UI;
- motion, focus, live regions или другую существенную accessibility-семантику;
- поверхность, которая должна стать примером для следующих страниц.

Для локальной однозначной правки текста, одного control или исправления уже принятого production-компонента отдельный полный prototype package не требуется. Объём evidence всегда выбирается по риску изменения.

## Главный принцип

```text
фактический контекст
→ независимое UI/content review
→ standalone prototype
→ evidence package
→ независимое ревью
→ ограниченный revision pass
→ owner visual acceptance
→ production implementation
→ focused verification
→ integration gate по риску
→ post-implementation owner acceptance
```

Прототипирование не является декоративным предварительным этапом. Оно отделяет дешёвую проверку продукта и интерфейса от дорогой реализации, тестов и real-Anki E2E.

Нельзя заменять эту последовательность схемой:

```text
сначала реализовать production
→ затем пытаться принять дизайн по зелёным тестам
```

Тесты подтверждают технические контракты, но не доказывают, что интерфейс понятен, композиционно целостен и принят владельцем.

## Термины

### Prototype

Standalone HTML/CSS/JavaScript artifact или другой изолированный интерактивный макет, предназначенный для проверки композиции, состояний, текста, motion и accessibility-поведения до production implementation.

Prototype:

- не является production source;
- не меняет backend/API/schema;
- не входит в package add-on;
- не доказывает production integration;
- может использовать упрощённый локальный state model, если ограничения явно задокументированы;
- обязан достоверно показывать заявленные пользовательские сценарии.

### Evidence package

Набор prototype, screenshots, comparison sheets, videos, audits и reports, достаточный для независимой проверки конкретного UI-кандидата.

### Visual acceptance

Решение о композиции, hierarchy, content, state semantics, responsive behavior, motion и общей понятности интерфейса.

Visual acceptance не означает, что production-код уже написан или что real-Anki integration проверена.

### Owner acceptance

Явное решение владельца проекта:

```text
APPROVE
APPROVE WITH REQUIRED REVISION
REJECT
```

Только владелец переводит принятый prototype в implementation boundary.

### Reference implementation

Страница или класс интерфейса, который закрепляет общие принципы дизайн-системы для следующих production surfaces.

Reference implementation не означает, что все страницы должны копировать её layout.

### Integration gate

Техническая проверка готового production-кандидата: focused tests, build, package validation, targeted или full real-Anki E2E согласно риску и действующей test policy.

## Разделение решений

Следующие решения независимы:

```text
одобрить направление prototype
одобрить финальный prototype
начать implementation
влить PR в core
синхронизировать core/master
выпустить release
```

Одно решение не подразумевает другое автоматически.

## Почему Cards является основным эталоном

`#/cards` — основной reference workspace общей UI-системы, потому что он одновременно содержит почти все сложные классы desktop-интерфейса проекта:

- полноширинный App Shell;
- плотную, но семантическую очередь;
- active selection;
- постоянный Inspector на широком desktop;
- немодальный drawer на узком desktop;
- безопасный preview внешнего пользовательского HTML/CSS;
- real `.apkg` templates и local media;
- modal расширенного ответа;
- причины, recommendation и primary action;
- pending, success, failure, no-changes, recheck и resolved states;
- Refresh, независимый от mutation lifecycle;
- focus restoration;
- live status announcements;
- restrained motion и reduced-motion;
- light/dark;
- FHD, QHD, 4K и 1024 reflow;
- локальные технические сведения без засорения normal path.

Поэтому Cards используется для доказательства общей визуальной грамматики:

- page/header hierarchy;
- desktop width model;
- spacing rhythm;
- typography levels;
- surface roles;
- shapes и radii;
- interactive item states;
- status hierarchy;
- motion tokens;
- focus token;
- Refresh pattern;
- modal/drawer behavior;
- light/dark semantic parity.

### Что другие страницы наследуют от Cards

Другие сохраняемые страницы должны переиспользовать:

- App Shell и внешние gutters;
- shared `PageHeader` contract;
- typography hierarchy;
- spacing tokens;
- shape/radius tokens;
- роли `page`, `region`, `soft group`, `interactive item`, `status`;
- ограниченное число surface levels;
- правила Refresh;
- visible focus;
- live-message architecture;
- motion duration/easing и reduced-motion policy;
- light/dark semantic hierarchy;
- content rule: каждый текст должен помогать понять состояние, риск, действие или следующий шаг.

### Что нельзя копировать механически

Cards не является универсальным page template.

Нельзя автоматически переносить на каждую страницу:

- трёхколоночную композицию;
- queue + Inspector;
- resolution rail;
- card preview canvas;
- drawer threshold;
- причины и recheck lifecycle;
- технические chips;
- размеры колонок Cards;
- локальные Cards-specific classes.

Страница наследует общие primitives и tokens, но получает composition, соответствующую своей пользовательской задаче.

## Inspection Profiles как второй эталон

Inspection Profiles является reference class для сложных settings/editor workflows:

- catalog + editor;
- exact selected identity;
- Basic/Advanced как взаимоисключающие режимы одного draft;
- semantic tabs;
- container-aware form layout;
- field mappings;
- inline validation;
- draft/dirty state;
- unresolved suggestion;
- navigation overflow/disclosure;
- 1024 reflow;
- focus preservation при rerender;
- validation error → correction → success.

Cards задаёт общий visual foundation. Inspection Profiles дополняет его контрактами форм, editor state и validation.

## Применение reference principles по классам страниц

| Класс страницы | Что брать из Cards | Что брать из Inspection Profiles | Что не копировать |
|---|---|---|---|
| Cards, Search, сложные workspaces | Shell, queue/detail hierarchy, states, refresh, focus, motion | Только form patterns при наличии | Cards-specific reasons и preview lifecycle |
| Decks и аналитические workspaces | Shell, surfaces, typography, spacing, responsive columns | Form controls при настройке scope | Queue/Inspector без реального сценария |
| Statistics/FSRS | Shell, PageHeader, surface/status grammar | Filters и validation при необходимости | Resolution rail и card preview |
| Settings | Shell, typography, disclosures, status hierarchy | Catalog/editor, tabs, draft, validation | Cards queue layout |
| Today/Profile | Только shared foundation | Только подходящие editable patterns | Продуктовую композицию Cards или Profiles |
| Modal/drawer flows | Focus, motion, close/return contracts | Form error handling | Конкретную геометрию Cards без основания |

## Когда нужен prototype-first процесс

Полный prototype-first процесс обязателен, если:

- меняется общий UI foundation;
- владелец ещё не принял композицию;
- production iteration уже приводила к повторным visual regressions;
- страница должна стать reference implementation;
- существует реальная развилка layout или information architecture;
- нужно доказать несколько responsive/state contours;
- сложное взаимодействие нельзя честно оценить по статическому Figma-like макету;
- дорого запускать production/E2E итерации до утверждения UX.

Можно обойтись targeted production change без отдельного prototype, если:

- visual contract уже принят;
- правка локальна и однозначна;
- не меняется composition или state model;
- риск покрывается existing component tests и representative screenshot;
- владелец прямо разрешил implementation-first для этой задачи.

## Этап 1. Восстановить фактический контекст

Перед prototype необходимо открыть:

1. `README.md`;
2. `docs/ai-handoff.md`;
3. профильный roadmap;
4. актуальный production code и tests затрагиваемых страниц;
5. текущие UX/product contracts;
6. последний relevant report и screenshots;
7. текущий PR/branch, если работа продолжает существующий remediation.

Приоритет источников:

```text
current production code and tests
→ current README and focused docs
→ fresh reports and artifacts
→ older plans and messages
→ assumptions
```

Нельзя утверждать, что открыт или проверен файл, который фактически не был изучен.

На этом этапе фиксируются:

- текущая пользовательская задача;
- уже принятые решения;
- отклонённые варианты;
- текущий production contour;
- scope и out of scope;
- security/privacy ограничения;
- что именно должен доказать prototype.

## Этап 2. Провести независимое UI/content review

До создания нового дизайна необходимо оценить существующий интерфейс.

Review должен отвечать:

- что пользователь пытается сделать;
- какая информация нужна первой;
- какие области дублируют друг друга;
- какие тексты не несут функции;
- где нарушена hierarchy;
- где страница использует слишком узкую centered область;
- где дополнительные пиксели не дают дополнительного рабочего пространства;
- какие состояния отсутствуют или противоречат друг другу;
- какие controls выглядят рабочими, но не имеют interaction;
- какие accessibility contracts затронуты;
- какие страницы будут удалены и не должны полироваться.

Review не является отдельным roadmap stage и не создаёт лестницу `C3.1.a`.

Результат review — bounded acceptance brief, а не implementation plan.

## Этап 3. Зафиксировать acceptance questions

До рисования prototype формулируются вопросы, на которые artifact должен дать проверяемый ответ.

Для Cards:

- какая карточка выбрана;
- почему она находится в очереди;
- что пользователь должен сделать;
- где primary action;
- что произошло после action;
- почему action success не равен resolution;
- что делает Recheck;
- как выглядит resolved state;
- что происходит с queue и focus после resolution;
- как Refresh влияет на active content;
- как работают modal и drawer.

Для Inspection Profiles:

- какой exact note type/profile выбран;
- Basic или Advanced активен;
- относится ли editor content к выбранному item;
- что изменено в draft;
- что блокирует confirmation;
- как реально получить validation error;
- как исправить ошибку;
- где находится focus после validation;
- как работает 1024 navigation overflow.

Acceptance questions должны проверять пользовательскую задачу, а не внутреннее устройство prototype.

## Этап 4. Создать standalone prototype

Prototype создаётся отдельно от production tree или как временный некоммитимый artifact.

Допустимо:

- один standalone `prototype.html`;
- локальные CSS и JavaScript;
- bounded state machine;
- query parameters для прямого открытия state screenshots;
- локальный media bundle;
- упрощённые fixtures;
- temporary CSS exploration, если она явно помечена как prototype-only.

Недопустимо:

- менять production только для удобства prototype;
- менять backend/API/schema без отдельного решения;
- ослаблять sanitizer/CSP/media validation;
- загружать remote scripts/styles/fonts;
- выполнять arbitrary JavaScript карточек;
- читать private Anki profile автоматически;
- выдавать synthetic state за production proof;
- включать prototype artifacts в add-on package или Fast CI;
- коммитить ZIP, screenshots, videos, tokens, profile data или generated artifacts.

## Использование real `.apkg` и карточек

Для Cards synthetic placeholders недостаточны как единственное доказательство.

Prototype должен использовать representative real templates, когда проверяется:

- native background;
- typography;
- alignment;
- long content;
- media/GIF;
- front/back distinction;
- light card на dark dashboard;
- template night mode;
- Java/code cards;
- safe local highlighting.

Правило fidelity:

```text
Dashboard оформляет workspace вокруг карточки.
Карточка сохраняет собственный HTML/CSS-контур в разрешённых security boundaries.
```

Prototype обязан явно различать:

- что сохранено из exact template;
- что восстановлено локальным trusted adapter;
- что заблокировано;
- что является только prototype simulation.

## Безопасность prototype preview

Даже дешёвый prototype не должен нормализовать опасную архитектуру.

Обязательные направления:

- zero external HTTP/HTTPS requests;
- arbitrary template JavaScript blocked;
- remote CSS/script blocked;
- media только из локального evidence package;
- bounded highlighting adapter;
- no private token/path/value exposure;
- fail-closed fallback для неизвестного языка или oversized content;
- визуальное доказательство не объявляется production security proof.

## State model prototype

Сложные интерфейсы проектируются не только по happy-path screenshot.

Для Cards минимальный state ledger включает применимые состояния:

```text
ready
action_pending
action_failed
awaiting_user_edit
recheck_pending
still_active
partially_resolved
resolved
recheck_failed
evidence_stale
refresh_pending
refresh_success
refresh_failed
```

Названия prototype state могут отличаться от production type names, но visual semantics должны быть однозначны.

Один state contract должен определять:

- header label;
- tone/color;
- visible reasons;
- recommendation;
- result panel;
- available primary action;
- live announcement;
- focus target;
- queue behavior.

Нельзя менять только зелёную/красную панель и оставлять противоречащие причины, priority или copy.

Для form/editor workflow минимальный ledger включает:

```text
clean
unsaved/dirty
unresolved suggestion
validation pending
validation error
validation success
confirmed
stale/needs review
```

## Этап 5. Подготовить evidence package

Evidence package должен быть достаточным, но не максимальным по умолчанию.

### Минимальный пакет

Для существенного статического UI-кандидата:

```text
README.md
prototype.html
checkpoint.md
prototype-overview.png
comparison sheet
representative screenshots
checksums.sha256
```

### Расширенный пакет

Для reference UI, сложных interactions или accessibility acceptance:

```text
state contract
changed-state screenshots
interaction video MP4/WebM
motion/transition sheets
interaction audit JSON
accessibility report
capture report
first-impression test kit
first-impression report
checksums.sha256
```

### Правило достаточности

Не нужно повторять полную matrix после каждой локальной правки.

```text
первый крупный candidate
→ broad representative evidence

следующий bounded revision
→ только изменённые states + regression anchors

финальный targeted pass
→ только незакрытые findings + owner gate
```

## Screenshot matrix

Для major reference UI проверяются representative contours, а не все возможные комбинации.

Базовые desktop widths:

```text
1920 или QHD wide reference
1440 normal desktop
1280 compact desktop
1024 narrow desktop/laptop
```

Scaling выбирается по риску:

```text
100%
125%
150%
200%
```

4K 100% может использоваться как diagnostic extreme, но не обязан быть главным visual target.

Light/dark и RU/EN должны сохранять одну semantic hierarchy. Необязательно захватывать каждую комбинацию на каждой итерации, если изменившаяся область не зависит от темы или локали.

Каждый screenshot должен иметь понятное имя:

```text
<page>-<viewport>-<theme>-<state>.png
```

Нельзя ссылаться в test kit или report на отсутствующий filename.

## Motion evidence

Если motion входит в acceptance criteria:

- source capture записывается нативно в 60 FPS;
- 30→60 interpolation запрещена;
- metadata фиксируются;
- modal/drawer/tab transitions должны иметь реальные intermediate frames;
- статические holds не выдаются за плавный transition;
- transition sheet показывает ключевое окно;
- video заканчивается стабильным UI, без случайного black tail;
- `prefers-reduced-motion` полностью отключает необязательное движение.

Motion должна помогать понять continuity, а не украшать страницу.

Допустимы:

- короткий fade backdrop;
- небольшой translate/scale modal;
- drawer translate;
- opacity/height result transition;
- restrained active-item transition.

Не допускаются длинные spring-анимации, декоративные перелёты и motion, скрывающая focus или изменение state.

## Accessibility evidence

Static screenshot не доказывает interaction accessibility.

Prototype audit должен выполнять реальные действия:

```text
click/select/input
→ state update
→ rerender
→ проверка visible DOM
→ проверка activeElement
→ проверка live announcement
```

Недостаточно открыть заранее подготовленный query state `?state=validation-error` и объявить validation flow проверенным.

### Focus

Проверяются:

- queue selection;
- action pending;
- Refresh pending/success/failure;
- modal initial focus;
- Tab/Shift+Tab внутри modal;
- Escape;
- focus return;
- drawer close;
- tabs arrow navigation;
- disclosure open/close/navigation;
- validation error/correction/success;
- resolved item removal и next focus.

`document.activeElement === BODY` после значимого действия считается дефектом, если только переход на новый document не является ожидаемым navigation result.

### Live regions

Надёжная схема:

```html
<div role="status" aria-live="polite" aria-atomic="true"></div>
<div role="alert" aria-atomic="true"></div>
```

Containers:

- существуют пустыми до события;
- не пересоздаются вместе с большой content region;
- содержат только concise text;
- не содержат buttons/links;
- не повторяют stale result при новом Refresh;
- используют один канал на одно событие.

### Modal

Modal обязан иметь:

- `role="dialog"`;
- `aria-modal="true"`;
- accessible label/title;
- initial focus внутри;
- focus trap;
- Escape;
- inert background;
- deterministic focus return.

### Tabs

Basic/Advanced как взаимоисключающие режимы одного draft используют:

- `tablist`;
- `tab`;
- `tabpanel`;
- `aria-selected`;
- `aria-controls`;
- roving tabindex;
- Left/Right keyboard navigation.

### Disclosure navigation

Для обычной Settings navigation предпочтительны:

- native button;
- `aria-expanded`;
- `aria-controls`;
- ordinary links;
- Tab/Shift+Tab;
- Escape;
- focus на route target после activation.

Не следует объявлять обычную навигацию ARIA command menu без реальной необходимости.

## Этап 6. Провести независимое ревью

Reviewer должен открыть сам archive и проверить artifacts, а не пересказывать README/capture report.

Для каждого существенного finding фиксируются:

- ID;
- severity;
- точный screenshot/state/video window;
- что видно;
- почему это проблема;
- пользовательское последствие;
- рекомендуемое bounded изменение;
- acceptance criterion.

### Severity

#### Blocker

Нельзя принять направление или продолжать implementation:

- потеря focus во всём workflow;
- небезопасная architecture;
- невозможность выполнить основную задачу;
- данные/состояния вводят в критическое заблуждение.

#### High

Обязательная правка до acceptance:

- противоречивый state;
- неработающий primary interaction;
- ложный success;
- недостоверное evidence;
- accessibility contract не работает в основном пути.

#### Medium

Нужно исправить в текущем bounded pass, если влияет на понятность или consistency, но не требует redesign.

#### Low

Необязательный polish, который не блокирует owner acceptance.

## Вердикты ревью

Используются только:

```text
APPROVE
APPROVE WITH REQUIRED REVISION
REJECT
```

### APPROVE

- основной и interaction contracts доказаны;
- нет Blocker/High;
- оставшийся Low polish не влияет на принятие;
- owner может решить начинать implementation.

### APPROVE WITH REQUIRED REVISION

- основное направление принято;
- новый redesign запрещён;
- перечислен конкретный короткий revision scope;
- implementation ещё не начинается.

### REJECT

- неверна основная композиция или продуктовая модель;
- bounded polish недостаточен;
- требуется новый candidate.

Нельзя выдавать `PASS` только потому, что package report или automated audit зелёный.

## Этап 7. Ограниченный revision pass

После принятия основного направления layout замораживается.

Каждый следующий pass исправляет только:

- незакрытые Blocker/High;
- явно включённые Medium;
- evidence, необходимое для их доказательства.

Запрещено:

- снова проектировать страницу с нуля;
- добавлять соседние features;
- менять принятый shell без нового доказанного blocker;
- расширять screenshot matrix без связи с finding;
- повторять полный `.apkg` audit, если fidelity-контур не менялся;
- снова проверять неизменившийся exact state;
- создавать roadmap-ступени `C3.1.a`, `C3.1.b`;
- выдавать номер prototype revision за новый product stage.

Artifact versions вида:

```text
v3.2
v3.2.1
v3.2.2
```

являются только версиями evidence package.

Они не добавляются в roadmap и не означают новые этапы разработки.

## Stop-loss для prototype iterations

Процесс должен предотвращать бесконечное улучшение одного экрана.

Правила:

1. Один broad review на основной candidate.
2. После `APPROVE WITH REQUIRED REVISION` — только targeted follow-up.
3. Не проводить новый полный аудит неизменившихся областей.
4. Новый finding добавляется только при наблюдаемом дефекте, а не из желания сделать ещё лучше.
5. Low polish не создаёт очередной обязательный pass без решения владельца.
6. После закрытия последнего High и owner acceptance prototype iteration прекращается.
7. Production risk проверяется уже production tests/E2E, а не бесконечным standalone prototype.
8. Если два последовательных passes не дают новой информации, работа останавливается и фиксируется реальный blocker либо owner decision.

## First-impression test

Для нового reference workspace или существенной смены workflow проводится короткий blind test на 2–3 людях, не знакомых с внутренней архитектурой.

Участнику показывают screenshot/state без предварительного объяснения.

Для Cards задаются вопросы:

- что это за страница;
- какая карточка выбрана;
- почему она здесь;
- что сделать первым;
- где primary action;
- что уже произошло после action;
- что означает `Проверить изменения`;
- требует ли resolved карточка дальнейшего внимания.

Правила:

- не подсказывать термины;
- не объяснять resolution contract заранее;
- записывать фактический ответ;
- не выдумывать reviewers или результаты;
- test kit обязан ссылаться на существующие files;
- тест проводится один раз на финальном candidate, а не после каждой локальной правки.

Если доступ к независимым участникам отсутствует, report честно фиксирует `NOT PERFORMED`; owner решает, блокирует ли это текущую acceptance boundary.

## Этап 8. Owner visual acceptance

Финальный пакет должен отдельно показывать:

```text
что принято
что исправлено
какие findings закрыты
что не доказано
какой residual risk остаётся
```

Владелец принимает решение.

До явного решения запрещено:

- начинать production implementation;
- составлять implementation prompt как уже утверждённую задачу;
- менять backend/API/schema;
- запускать тяжёлый E2E;
- создавать новый production PR;
- объявлять Cards финальным production reference.

## Этап 9. Подготовить implementation handoff

Только после owner approval создаётся implementation task для ChatGPT/Codex.

Handoff содержит:

- accepted prototype version;
- screenshots/states, являющиеся reference;
- accepted design principles;
- exact scope;
- out of scope;
- shared primitives/tokens, которые требуется создать или переиспользовать;
- page-specific composition, которую нельзя превращать в global primitive;
- backend/frontend/API ограничения;
- security boundaries;
- accessibility contracts;
- localization requirements;
- required focused tests;
- risk-based E2E decision;
- Git/PR полномочия;
- ожидаемый final report.

Нельзя переносить standalone prototype буквально:

- `innerHTML` rerender;
- prototype-only CSS `zoom`;
- synthetic fixtures;
- query-state shortcuts;
- temporary tokenizers;
- screenshot-only error states;
- hardcoded route demo;
- local audit helpers.

Production implementation воспроизводит принятый контракт средствами production architecture.

## Этап 10. Production implementation

При реализации общей UI-системы:

- Cards служит первым production consumer shared foundation;
- primitives извлекаются по реальному повторному использованию, а не заранее;
- другие страницы мигрируют на shared foundation без механического копирования Cards layout;
- shared tokens не должны ломать native card preview;
- API/payload изменения синхронно обновляют backend, frontend types, tests и docs;
- generated dashboard assets вручную не редактируются;
- security contracts не ослабляются ради visual fidelity;
- obsolete UI удаляется только в scope соответствующего этапа.

## Этап 11. Проверки после реализации

Проверки выбираются по `test-matrix.md` и `verification-run-policy.md`.

Обычная последовательность:

```text
focused component/unit tests
→ typecheck
→ production build
→ focused browser tests
→ package validation при необходимости
→ targeted real-Anki E2E по риску
→ один final full gate для готового кандидата
```

Docker E2E не используется как пошаговый visual debugger.

Не повторяется successful same-SHA gate без изменения кандидата или нового диагностического основания.

Post-implementation visual acceptance проверяет:

- production соответствует accepted prototype;
- real content не сломал hierarchy;
- focus/live regions работают в production framework;
- light/dark и RU/EN сохраняют semantics;
- 1024/normal/wide contours не имеют overflow;
- Cards остаётся эталоном foundation, а не локальным исключением;
- другие страницы переиспользуют primitives, не копируя Cards-specific composition.

## Документация и artifacts

Границы каталогов:

```text
docs/       актуальный процесс и обязательные контракты
roadmap/    этапы, зависимости и критерии завершения
reports/    исторические review/closeout решения
```

Prototype ZIP, screenshots, videos, interaction logs и generated evidence не коммитятся в repository.

После acceptance в repository фиксируются только:

- актуальный процесс;
- принятые product/UI contracts;
- при необходимости итоговый historical report без private data и generated outputs.

## Роли

### Владелец

- задаёт продуктовую цель;
- принимает или отклоняет направление;
- решает, когда прекратить prototype iterations;
- разрешает implementation;
- принимает production result;
- отдельно решает merge/release.

### ChatGPT

Подходит для:

- восстановления контекста;
- independent UI/content review;
- анализа evidence package;
- severity ledger;
- prototype acceptance;
- подготовки bounded handoff;
- ограниченных docs/GitHub changes.

ChatGPT не должен принимать собственный prototype только по его README или автоматическому report.

### Codex

Подходит для:

- standalone prototype generation при наличии локального checkout;
- production implementation после approval;
- focused tests;
- build/package checks;
- Git workflow;
- artifact generation по точному acceptance brief.

Codex не должен переносить prototype в production до owner approval.

## Антипаттерны

### Production-first visual iteration

Проблема: дорогие frontend/backend/tests/E2E циклы выполняются до утверждения интерфейса.

Решение: сначала standalone prototype и visual acceptance.

### Tests as design approval

Проблема: зелёные tests используются как доказательство хорошего UX.

Решение: tests и visual acceptance являются разными gates.

### Report-only review

Проблема: reviewer пересказывает `README.md`, не открывая screenshots/video/HTML.

Решение: независимая проверка самого artifact.

### Static-state substitution

Проблема: query parameter показывает красивый error state, но реальное interaction не приводит к нему.

Решение: audit обязан выполнить настоящий input/change/click flow.

### Fake affordance

Проблема: button/menu/tab выглядит рабочим, но не имеет activation, focus или state.

Решение: prototype controls должны быть интерактивны либо явно помечены как static demonstration.

### Endless redesign

Проблема: каждый follow-up снова меняет layout и создаёт новые версии без завершения.

Решение: после принятия направления layout freeze и targeted findings only.

### Universal Cards layout

Проблема: queue/Inspector/rail копируются на страницы без соответствующей задачи.

Решение: Cards задаёт foundation, а не универсальную композицию.

### Global narrow container

Проблема: desktop dashboard использует одну узкую centered колонку для всех pages.

Решение: full-width shell, adaptive gutters и локальные max-width только для конкретного content.

### Excessive surface nesting

Проблема:

```text
card inside card inside card
```

Решение: не более трёх–четырёх различимых surface levels и ясные semantic roles.

### E2E as debugger

Проблема: real-Anki full gate запускается после каждого visual tweak.

Решение: prototype → focused checks → targeted E2E → один final gate.

## Финальный checklist prototype candidate

### Product

- [ ] Пользовательская задача сформулирована.
- [ ] Scope и out of scope зафиксированы.
- [ ] Основные acceptance questions имеют ответы.
- [ ] Нет вымышленных features или placeholder routes.

### Cards reference

- [ ] Queue быстро сканируется.
- [ ] Active card очевидна.
- [ ] Preview является главным объектом.
- [ ] Native template individuality сохранена.
- [ ] Reasons, recommendation и action разделены.
- [ ] Refresh независим от resolution.
- [ ] Action success не выдаётся за resolution.
- [ ] Resolved state не показывает active reasons/priority.
- [ ] Queue/focus transition после resolved определён.

### Inspection Profiles

- [ ] Selected catalog identity и editor content совпадают.
- [ ] Basic/Advanced взаимоисключающие.
- [ ] Draft сохраняется между modes.
- [ ] Validation error достигается реальным interaction.
- [ ] Correction и success доказаны.
- [ ] Focus не становится `BODY`.
- [ ] 1024 navigation не обрезана.

### Layout

- [ ] Full-width desktop используется функционально.
- [ ] Нет глобального узкого `max-width`.
- [ ] Local max-width обоснованы content.
- [ ] 1024 не имеет horizontal overflow.
- [ ] QHD/4K не выглядят случайно уменьшенным FHD.

### Visual system

- [ ] PageHeader hierarchy едина.
- [ ] Typography roles едины.
- [ ] Spacing и shapes ограничены shared tokens.
- [ ] Surface levels ограничены.
- [ ] Status color соответствует state.
- [ ] Light/dark сохраняют одну semantic hierarchy.

### Accessibility

- [ ] Visible focus присутствует.
- [ ] Modal focus lifecycle доказан.
- [ ] Drawer close/return доказан.
- [ ] Tabs используют standard semantics.
- [ ] Disclosure navigation использует native links.
- [ ] Stable live regions существуют заранее.
- [ ] Status text не содержит controls.
- [ ] Reduced motion отключает transitions.
- [ ] Audit выполняет реальные interactions.

### Evidence

- [ ] Screenshots имеют точные filenames.
- [ ] Comparison sheet отражает фактические изменения.
- [ ] Videos нативно записаны в требуемом FPS.
- [ ] Reports не заявляют отсутствующие scenarios.
- [ ] Checksums проходят.
- [ ] Private data отсутствует.
- [ ] Blind report не содержит вымышленных участников.

### Boundary

- [ ] Production source не изменён до approval.
- [ ] Backend/API/schema не изменены.
- [ ] E2E не использован как visual debugger.
- [ ] Новый redesign не начат после принятия направления.
- [ ] Owner verdict записан явно.

## Краткая каноническая последовательность

```text
1. Открыть актуальный код, docs и последний artifact.
2. Провести независимое UI/content review.
3. Выбрать reference page и acceptance questions.
4. Создать standalone prototype с representative real content.
5. Собрать bounded evidence package.
6. Провести независимое ревью artifact, а не README.
7. Зафиксировать severity ledger и verdict.
8. Исправить только обязательные findings.
9. Провести targeted re-review и один blind test.
10. Получить owner visual acceptance.
11. Только теперь подготовить implementation handoff.
12. Реализовать shared foundation, используя Cards как первый reference consumer.
13. Выполнить focused checks и risk-based integration gate.
14. Провести production owner acceptance.
15. Отдельно решить merge/release.
```
