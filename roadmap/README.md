# Roadmap Anki Study Report

**Снимок:** 2026-07-29

Roadmap разделён на один обязательный продуктовый путь **Core** и независимые либо условные треки. Больший номер не создаёт общей очереди между разными направлениями.

## Общая карта

```mermaid
flowchart TB
    S[Stage 0–9.5<br/>accepted product contour] --> C1[C1 Cards v2<br/>complete]
    C1 --> C2[C2 Core hardening<br/>complete and accepted]
    C2 --> C3[C3 UI & Shell<br/>next]
    C3 --> C4[C4 Data Independence]
    C4 --> C5[C5 Today v2]
    C5 --> C6[C6 Profile v2]
    C6 --> R{Core 1.0<br/>owner acceptance}
    R --> REL[Separate release decision]

    G[Gamification G<br/>research / conditional]
    O[Operations O<br/>independent]
    I[Identity I<br/>conditional]
    E[Extensions E<br/>conditional]
    P[Platform / CI<br/>I1–I6 complete]

    G -. no automatic block .-> C3
    O -. no automatic block .-> C3
    I -. no automatic block .-> C3
    E -. no automatic block .-> C3
    P -. no automatic block .-> C3
```

## Состояние треков

| Трек | Роль | Текущий статус | Следующая точка |
| --- | --- | --- | --- |
| [Core `C`](core/README.md) | единственный обязательный путь add-on | C1 и C2 завершены; C2 acceptance закрыта | C3 UI & Shell |
| [Gamification `G`](gamification/README.md) | research и необязательный продукт | развивается независимо; production не одобрен | определяется в профильной ветке и roadmap |
| [Operations `O`](operations/README.md) | защищённые admin-инструменты удалённых сервисов | O1 активирован; O2 условный | O1 в отдельном Operations-контуре |
| [Identity `I`](identity/README.md) | optional continuity/recovery gate | не запланирован | I1 только при конкретном cross-device workflow |
| [Extensions `E`](extensions/README.md) | first-party extension ecosystem | условный/отложенный | E1 только с reference pack |
| [Platform / CI](platform/README.md) | CI/CD, точные артефакты и E2E в реальном Anki | E2E-I1–I6 завершены | нет активного этапа; CI 7–12 только по отдельному trigger |

Operations остаётся независимым от локального add-on. Подробная принятая граница O1/O2, privacy, authorization и remote-service scope хранится в [профильном roadmap Operations](operations/README.md).

## Как читать roadmap

Каждый этап должен содержать:

- цель;
- статус;
- зависимости и activation criteria;
- scope и out of scope;
- completion criteria.

Roadmap не является production contract. Приоритет источников:

```text
production code и tests
→ docs/
→ roadmap/
→ reports/
```

## Границы

- `docs/` — текущее поведение и обязательные contracts;
- `roadmap/` — будущее развитие и зависимости;
- `reports/` — исторические audits, measurements и closeout evidence.

Завершённые run IDs, SHA и artifacts не дублируются в корневой roadmap. Они находятся в [reports](../reports/README.md).

## Общие правила

1. Параллельный трек не блокирует Core без документированной зависимости.
2. Placeholder UI и speculative APIs не добавляются заранее.
3. Payload/public behavior меняются синхронно между backend, frontend types, tests и docs.
4. Runtime artifacts, logs, screenshots, tokens, profile data и `.ankiaddon` не коммитятся.
5. Verification следует [test matrix](../docs/test-matrix.md) и [run policy](../docs/verification-run-policy.md).
6. Successful unchanged exact-SHA E2E не повторяется.
7. Merge, release и publication — разные решения.
8. Один крупный этап не дробится на бесконечную лестницу подпунктов.

## Словарь статусов

- **Complete** — обязательный результат существует и прошёл заявленные gates.
- **Merged** — candidate интегрирован в целевую долгоживущую ветку.
- **Owner accepted** — обязательные автоматические gates и требуемая ручная приёмка завершены.
- **Next** — следующая рекомендуемая работа внутри трека.
- **Conditional** — активируется только при явном trigger.
- **Deferred** — намеренно вне текущего горизонта.
- **Research only** — не входит в production/package/CI.
