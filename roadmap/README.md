# Roadmap Anki Study Report

**Снимок:** 2026-07-22

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
  ├─ C1.5R.0–R.7 — завершены и приняты
  ├─ C1.6 exact-card resolution loop — завершён, принят и влит в core
  └─ C1.6B limited bulk actions — условный этап
→ C2 Core 1.0 Hardening — завершён и exact-SHA проверен на candidate branch
  └─ PR #128 ожидает отдельного решения о merge в core
→ C3 Contextual Additions — только при доказанном пробеле
```

Финальный проверенный C2 head:

```text
9d5d7724aedac375fde3c9a6752baf1b4aee86ba
```

Полный отчёт:

- [C2 — усиление Core 1.0 и исправление UI после C1](../reports/core/c2-core-hardening-ui-remediation.md).

## Карта треков

| Трек | Роль | Текущий статус | Что не блокирует |
| --- | --- | --- | --- |
| [Core `C`](core/README.md) | единственный критический путь add-on | C1 завершён; C2 проверен; merge ожидает решения; C1.6B/C3 условны | — |
| [Геймификация `G`](gamification/README.md) | параллельное исследование и необязательный продукт | production не одобрен | Core |
| [Эксплуатация `O`](operations/README.md) | защищённые административные инструменты телеметрии | отдельный трек | Core |
| [Идентификация `I`](identity/README.md) | необязательный opt-in gate непрерывности | условный | Core и локальную геймификацию |
| [Расширения `E`](extensions/README.md) | first-party extension ecosystem | условный/отложенный | зрелость Core |
| [Платформа `CI`](platform/README.md) | CI/CD, exact artifacts и real-Anki E2E | независимый delivery track | продуктовый scope |

## Зависимости

```text
Stage 0–9.5 завершены
        │
        └─→ C1 завершён
              │
              └─→ C2 завершён и проверен на candidate branch
                    │
                    ├─ merge в core — отдельное решение
                    ├─ release — отдельное решение после проверки production tree
                    └─ C3 — только при доказанном пробеле

G/O/I/E не блокируют Core без явно документированной зависимости.
```

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

Исторические успешные или неуспешные runs сохраняются как evidence фактического состояния соответствующего SHA и не переобъявляются задним числом.

## Сопоставление старой и новой структуры

| Прежнее расположение | Текущая структура |
| --- | --- |
| Stage 10 Cards v2 | C1 Core |
| Stage 10.5 Core 1.0 Hardening | C2 Core |
| Stage 11 Contextual Analytics | условный C3 |
| Stage 12 Extension Foundation | условный E1/E2 |
| Stage 13 Analytics Pack | условный E3 |
| Telemetry Admin Dashboard | O track |
| Identity continuity | I track |
| Gamification | G track |

Исторические пути сохраняются как compatibility pointers.

## Словарь статусов

- **Завершён** — обязательный результат этапа существует и прошёл указанные gates.
- **Завершён на candidate branch** — реализация и проверка закончены, но merge в целевую долгоживущую ветку выполняется отдельным решением.
- **Следующий этап** — рекомендуемая работа внутри трека.
- **Условный этап** — активируется только при наличии явного trigger.
- **Заблокирован** — обязательная зависимость или gate не выполнены.
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

## Текущая точка Core

```text
C1 — завершён и принят
C2 — завершён и exact-SHA проверен на candidate branch
PR #128 — ожидает решения владельца о merge в core
C1.6B — условный
C3 — условный
release — не начат
```
