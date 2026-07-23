# Roadmap Anki Study Report

**Снимок:** 2026-07-24

Roadmap содержит один обязательный путь Core и несколько независимых или условных треков. Больший номер этапа не создаёт общей очереди между несвязанными направлениями. Production-код и тесты имеют приоритет над roadmap и историческими отчётами.

## Текущее положение

Принятый продуктовый контур до Stage 9.5 завершён.

```text
Foundation / IA / Settings / Profile / Activity / Decks
→ Statistics / FSRS / Localization
→ Search / Safe Actions
→ Notices / opt-in telemetry / Signals / Notifications
```

Текущий Core:

```text
C1 Cards v2 / Problem Triage — завершён и принят
→ C2 Core 1.0 Hardening — реализован, проверен и влит в core
   → post-merge manual acceptance remediation — текущая незакрытая граница C2
→ C3 Core UI & Shell Consolidation
→ C4 First-party Data Independence
→ C5 Today v2
→ C6 Profile v2 Foundation
→ owner acceptance Core 1.0
→ отдельное решение о release
```

`C1.6B` остаётся условным и не входит в обязательную очередь. Прежний общий этап `C3 Contextual Additions` отменён: будущие contextual additions активируются только как отдельные evidence-backed предложения.

Текущий production head `core` после merge C2:

```text
edb140b1197910aae31500a40e4a8287cc46b760
```

Полный отчёт C2:

- [C2 — усиление Core 1.0 и исправление UI после C1](../reports/core/c2-core-hardening-ui-remediation.md).

Актуальный обязательный путь:

- [Продуктовая ветка Core](core/README.md).

## Почему roadmap пересмотрен

C2 успешно закрыл технические и security findings, но ручная проверка после merge выявила:

- незакрытые регрессии Cards/Inspection Profiles;
- отсутствие цельной site-wide UI/content grammar;
- искусственно узкий centered layout на desktop;
- перегруженные и дублирующиеся тексты;
- obsolete Tools/Report/Sources surfaces;
- функционально размытый Today;
- недостаточно развитый Profile;
- зависимость части data-source contour от внешних add-ons.

Поэтому Core 1.0 больше не следует непосредственно за C2. Новый обязательный путь сначала закрывает ручную приёмку C2, затем стабилизирует общий shell/design, first-party data boundary и две ключевые продуктовые страницы.

## Карта треков

| Трек | Роль | Текущий статус | Что не блокирует |
| --- | --- | --- | --- |
| [Core `C`](core/README.md) | единственный критический путь add-on | C2 влит; manual acceptance remediation следующая; C3–C6 обязательны до Core 1.0 | — |
| [Геймификация `G`](gamification/README.md) | параллельное исследование и необязательный продукт | production не одобрен | Core; Profile v2 подготавливает только foundation |
| [Эксплуатация `O`](operations/README.md) | защищённые административные инструменты телеметрии | отдельный трек | Core |
| [Идентификация `I`](identity/README.md) | необязательный opt-in gate непрерывности | условный | Core и локальную геймификацию |
| [Расширения `E`](extensions/README.md) | first-party extension ecosystem | условный/отложенный | зрелость Core |
| [Платформа `CI`](platform/README.md) | CI/CD, exact artifacts и real-Anki E2E | `E2E-I1` завершён; `E2E-I2` следующий; независимый delivery track | продуктовый scope |

## Текущий Platform / CI contour

```text
CI 6B — завершён
real-deck E2E foundation — завершён
E2E-I1 unified live run protocol — завершён
E2E-I2 browser smoke progress — следующий, не начат
```

Подтверждение `E2E-I1`:

```text
implementation SHA: a376a1e5556b26043d29fadcf01698972bd1b2ba
Fast CI: 30039103625 — PASS
standard/full: 30039372012 — PASS
final standard/full: 30039708429 — PASS
PR в core: не создан
merge в core: не выполнен
```

- [Platform / CI roadmap](platform/README.md);
- [E2E observability и build identity](platform/e2e-observability-build-identity.md);
- [Технический контракт run events](../docs/run-event-protocol.md);
- [Итоговый отчёт E2E-I1](../reports/ci/e2e-i1-unified-live-run-protocol-closeout.md).

## Зависимости

```text
Stage 0–9.5 завершены
        │
        └─→ C1 завершён
              │
              └─→ C2 реализован, проверен и влит
                    │
                    └─→ ручная приёмка C2
                          │
                          └─→ C3 UI & Shell
                                │
                                └─→ C4 Data Independence
                                      │
                                      └─→ C5 Today v2
                                            │
                                            └─→ C6 Profile v2
                                                  │
                                                  └─→ Core 1.0 acceptance/release decision

G/O/I/E/CI не блокируют Core без явно документированной зависимости.
```

## Обязательные принципы нового Core-пути

### Desktop layout

- dashboard использует всю доступную ширину;
- глобальный узкий `max-width` запрещён;
- локальные ограничения применяются только к конкретному тексту, форме или dialog;
- дополнительная ширина превращается в колонки и рабочее пространство;
- 1920/1440/1280/1024 и zoom входят в UI verification.

### UI/content

- один общий `PageHeader` contract;
- одинаковые компоненты имеют одинаковую форму и motion;
- текст не повторяет title/route без новой информации;
- не создаются ни плоские полотна текста, ни бесконечные вложенные cards;
- route, предназначенный для удаления, не проходит дорогостоящий polish перед cleanup.

### Scope discipline

- C3 не перестраивает Today/Profile product model;
- C4 не смешивается с визуальным redesign;
- C5 и C6 используют foundation C3;
- Gamification остаётся отдельным треком;
- bulk actions и contextual additions не активируются автоматически.

## Завершённая история Core

Актуальные основные отчёты:

- [C1.5R.0 — восстановление](../reports/core/c1-5r-0-recovery-baseline.md);
- [C1.5R.1 — идентичность карточки](../reports/core/c1-5r-1-canonical-card-display-identity.md);
- [C1.5R.2 — formatter runtime](../reports/core/c1-5r-2-declarative-compact-formatter-runtime.md);
- [C1.5R.3 — preview semantics](../reports/core/c1-5r-3-front-back-preview-semantics.md);
- [C1.5R.4 — источники кандидатов](../reports/core/c1-5r-4-independent-triage-candidate-sources.md);
- [C1.5R.5 — attention inbox](../reports/core/c1-5r-5-cards-attention-inbox-redesign.md);
- [C1.5R.6 — guided Inspection Profiles](../reports/core/c1-5r-6-guided-inspection-profiles-ux.md);
- [C1.5R.7 — integrated acceptance](../reports/core/c1-5r-7-integrated-acceptance-closeout.md);
- [C1.6 — exact-card resolution loop](../reports/core/c1-6-canonical-single-card-resolution-loop.md);
- [C2 — Core 1.0 Hardening](../reports/core/c2-core-hardening-ui-remediation.md).

Исторические runs сохраняются как evidence соответствующего SHA и не переобъявляются задним числом.

## Сопоставление старой и новой структуры

| Прежнее расположение | Текущая структура |
| --- | --- |
| Stage 10 Cards v2 | C1 Core |
| Stage 10.5 Core 1.0 Hardening | C2 Core |
| Stage 11 Contextual Analytics | evidence-triggered backlog; не C3 |
| Stage 12 Extension Foundation | условный E1/E2 |
| Stage 13 Analytics Pack | условный E3 |
| Telemetry Admin Dashboard | O track |
| Identity continuity | I track |
| Gamification | G track |

Исторические пути сохраняются как compatibility pointers.

## Словарь статусов

- **Завершён** — обязательный результат существует и прошёл указанные gates.
- **Влит** — candidate интегрирован в целевую долгоживущую ветку.
- **Ручная приёмка открыта** — автоматические gates пройдены, но owner smoke выявил незакрытые проблемы.
- **Следующий этап** — рекомендуемая обязательная работа внутри трека.
- **Условный этап** — активируется только при наличии явного trigger.
- **Заблокирован** — обязательная зависимость или gate не выполнен.
- **Отложен** — намеренно находится вне текущего горизонта.
- **Только исследование** — не входит в production/package/CI.

## Границы каталогов

```text
docs/       актуальные контракты и handoff
roadmap/    треки, зависимости и критерии активации
reports/    исторические доказательства и итоговые отчёты
```

- [Индекс документации](../docs/README.md);
- [Исторические отчёты](../reports/README.md);
- [Журнал решений](../docs/decision-log.md);
- [Передача контекста ИИ](../docs/ai-handoff.md).

## Правила изменения roadmap

1. Production-код и тесты имеют приоритет.
2. Этап указывает цель, статус, зависимости, scope и критерии завершения.
3. Параллельный трек не блокирует Core без документированной зависимости.
4. Placeholder UI и неутверждённые функции не добавляются заранее.
5. Payload и публичное поведение меняются синхронно между слоями, тестами и docs.
6. Research candidates не являются production commitments.
7. Runtime artifacts, logs, screenshots, tokens, profile data и `.ankiaddon` не коммитятся.
8. Проверка следует `docs/test-matrix.md` и `docs/verification-run-policy.md`.
9. Успешный exact-SHA E2E не повторяется без нового риска или изменённого дерева.
10. Merge, release, deployment и publication — разные явно одобряемые действия.
11. Не создаётся новая лестница подпунктов вместо одной цельной задачи.
12. Site-wide UI review предшествует site-wide implementation, но не становится отдельным numbered stage.
13. Завершение `E2E-I1` не активирует автоматически `E2E-I2` или CI 7–12.

## Текущая точка Core

```text
C1 — завершён и принят
C2 — реализован, проверен и влит в core
C2 manual acceptance remediation — следующая работа
C3–C6 — обязательный путь к Core 1.0
C1.6B — условный
contextual additions — evidence-triggered backlog
release — не начат
```
