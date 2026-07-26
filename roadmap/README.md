# Roadmap Anki Study Report

**Снимок:** 2026-07-26

Roadmap разделён на один обязательный продуктовый путь **Core** и независимые либо условные треки. Больший номер не создаёт общей очереди между разными направлениями.

## Общая карта

```mermaid
flowchart TB
    S[Stage 0–9.5<br/>accepted product contour] --> C1[C1 Cards v2<br/>complete]
    C1 --> C2[C2 Core hardening<br/>implemented and merged]
    C2 --> A[C2 owner acceptance<br/>remediation]
    A --> C3[C3 UI & Shell]
    C3 --> C4[C4 Data Independence]
    C4 --> C5[C5 Today v2]
    C5 --> C6[C6 Profile v2]
    C6 --> R{Core 1.0<br/>owner acceptance}
    R --> REL[Separate release decision]

    G[Gamification G<br/>G1 complete / DEFER<br/>G2.2 complete]
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
| [Core `C`](core/README.md) | единственный обязательный путь add-on | C2 влит; owner acceptance открыта | bounded C2 remediation, затем C3 |
| [Gamification `G`](gamification/README.md) | research и необязательный продукт | G0/G1 complete; G2 in progress; G2.1/G2.2 complete; lifecycle frozen; production не одобрен | G2.3 `NEXT / NOT STARTED`; отдельная активация |
| [Operations `O`](operations/README.md) | защищённые admin-инструменты telemetry | независимый условный трек | O1 только при operational trigger |
| [Identity `I`](identity/README.md) | optional continuity/recovery gate | не запланирован | I1 только при конкретном cross-device workflow |
| [Extensions `E`](extensions/README.md) | first-party extension ecosystem | условный/отложенный | E1 только с reference pack |
| [Platform / CI](platform/README.md) | CI/CD, точные артефакты и E2E в реальном Anki | E2E-I1–I6 и bounded corrective fix завершены | нет активного этапа; CI 7–12 только по отдельному trigger |

Профильный [`roadmap/gamification/README.md`](gamification/README.md) является источником актуального статуса Gamification внутри ветки `gamification`. Core mirror не переопределяет завершённые G0–G2.2.

## Как читать roadmap

Каждый этап должен содержать:

- цель;
- статус;
- зависимости и activation criteria;
- scope и out of scope;
- completion criteria.

Roadmap не является production contract. Приоритет источников:

```text
production/research code и tests
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
9. Research candidate не называется production-ready до отдельного решения.

## Словарь статусов

- **Complete** — обязательный результат существует и прошёл заявленные gates.
- **Merged** — candidate интегрирован в целевую долгоживущую ветку.
- **Owner acceptance open** — автоматические gates пройдены, но ручная проверка выявила незакрытый gap.
- **Next** — следующая рекомендуемая работа внутри трека.
- **Conditional** — активируется только при явном trigger.
- **Deferred** — намеренно вне текущего горизонта.
- **Research only** — не входит в production/package/CI.
