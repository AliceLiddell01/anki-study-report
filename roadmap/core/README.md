# Продуктовая ветка Core

**Трек:** `C`  
**Роль:** единственный обязательный последовательный путь основного add-on  
**Текущий статус:** `C1 завершён`; `C2 завершён, проверен и включён в core`; post-merge manual acceptance remediation ведётся как ограниченный follow-up без нового этапа; `C1.6B` и `C3` условны

Core не зависит от геймификации, аккаунтов, административного UI телеметрии или пакетов расширений. Параллельные треки не меняют критерии завершения Core.

## Модель поставки

Core разрабатывается в долгоживущей ветке `core`.

- C1 и C2 выполняются последовательно;
- merge в `core`, синхронизация с `master`, release и публикация — разные решения;
- merge в `master`, release tag, GitHub Release, `.ankiaddon`, deployment и AnkiWeb требуют отдельного одобрения владельца;
- несвязанные изменения не переносятся автоматически;
- force-push запрещён без явного одобрения;
- сообщения коммитов описывают фактические изменения.

## Последовательность

```text
C1 Cards v2 / Problem Triage — завершён
→ C2 Core 1.0 Hardening — завершён, проверен и включён в core
→ C3 Contextual Additions — только при доказанном пробеле
```

# C1 — Cards v2 / Problem Triage

**Статус:** завершён, принят владельцем

## Завершённые части

| Часть | Статус | Основной источник |
| --- | --- | --- |
| C1.0 — исходное состояние | завершено | [`reports/core/c1-0-baseline.md`](../../reports/core/c1-0-baseline.md) |
| C1.1 — продуктовый контракт | завершено | [`docs/cards-v2-product-contract.md`](../../docs/cards-v2-product-contract.md) |
| C1.2 — Triage и API чтения | завершено | [`docs/cards-v2-triage-read-api.md`](../../docs/cards-v2-triage-read-api.md) |
| C1.3 — Inspection Profiles runtime | завершено | [`docs/inspection-profiles-v1.md`](../../docs/inspection-profiles-v1.md) |
| C1.4 — Inspection Profiles UI | завершено | [`docs/inspection-profiles-ui.md`](../../docs/inspection-profiles-ui.md) |
| C1.5 — исторический Cards workspace | техническое подтверждение сохранено; продуктовая приёмка отозвана | [`reports/core/c1-5-cards-workspace.md`](../../reports/core/c1-5-cards-workspace.md) |
| C1.5R — UX recovery | R0–R7 завершены и приняты | отчёты C1.5R |
| C1.6 — exact-card resolution loop | завершено, принято и влито в `core` | [`docs/cards-v2-resolution-loop.md`](../../docs/cards-v2-resolution-loop.md) |
| C1.6B — ограниченные массовые действия | условный этап, не начат | отдельное решение владельца |

C1.5R заменил отклонённые части C1.5: идентичность карточки, formatter runtime, preview semantics, независимые источники кандидатов, attention inbox, guided Inspection Profiles и integrated acceptance.

C1.6 закрепил канонический lifecycle одной карточки:

```text
проблема
→ Safe Action или Open in Anki
→ результат действия
→ Awaiting recheck
→ exact-card recheck
→ Still active | Partially resolved | Resolved | Recheck failed | Evidence stale
```

C1.6B не требуется для завершения C1 и не активируется автоматически.

# C2 — Core 1.0 Hardening

**Статус:** реализация завершена; exact-SHA Fast CI, targeted `standard/cards` с restart и final `standard/full` завершились успешно; изменения включены в `core`

**Candidate branch:** `c2-core-hardening-ui-remediation`  
**Финальный проверенный head:** `9d5d7724aedac375fde3c9a6752baf1b4aee86ba`

## Цель

Стабилизировать существующий продукт как поддерживаемый Core 1.0 без новой системы поставки и без расширения функций.

## Выполнено

- parser-backed политика CSS карточек и browser defense in depth;
- локальная exact-card authority без влияния unrelated profiles;
- generation-safe query, inspect, cache и mutations;
- bounded add-on Search work и concurrency gate;
- минимальный public status и корректный idle lifecycle;
- extraction только доказанных policy seams;
- behavior-based E2E helpers;
- общий visual role system;
- targeted remediation Cards и Inspection Profiles;
- исправление Fast CI → E2E handoff для advisory PR associations;
- CSP-safe Vite theme bootstrap;
- закрывающая exact-SHA verification campaign.

Полный ledger, тесты, решения и residual risks:

- [`reports/core/c2-core-hardening-ui-remediation.md`](../../reports/core/c2-core-hardening-ui-remediation.md).

## Критерии завершения C2

Выполнены:

- known technical/security findings закрыты либо документированно смягчены;
- known UI findings закрыты либо документированно смягчены;
- payload/schema parity сохранён;
- security boundaries не ослаблены;
- Fast CI успешно проверил текущий exact SHA;
- targeted real-Anki `standard/cards` с restart прошёл;
- final real-Anki `standard/full` прошёл;
- residual risks явно зафиксированы;
- release и publication не выполнялись неявно.

Post-merge исправления замечаний ручной приёмки Cards и Inspection Profiles не открывают C2.x и не меняют критерии этапа. Они документируются append-only в итоговом отчёте C2 и проходят собственные exact-SHA gates.

## Вне scope C2

- новые функции;
- C1.6B;
- C3;
- геймификация, аккаунты и extension ecosystem;
- перестройка delivery infrastructure;
- release, deployment и публикация;
- broad legacy rewrite без доказанного риска.

# C3 — Contextual Additions

**Статус:** условный этап

C3 активируется только для конкретного доказанного пробела, на который текущие Statistics, FSRS, Search, Cards и Triage не дают ответа. Каждое дополнение обязано определить пользовательское решение, доступность данных, ограниченный запрос, место в интерфейсе, правила интерпретации и scope проверки.

При отсутствии доказанного пробела C3 закрывается без расширения функций.

## Следующее действие Core

```text
закрытие ограниченного post-merge manual acceptance follow-up
→ отдельная ручная приёмка владельцем
→ отдельное решение о дальнейшем этапе или release
```

Не начинать C1.6B, C3, release или merge в `master` автоматически.
