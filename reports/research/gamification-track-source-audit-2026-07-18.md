# Gamification track — source audit

**Дата аудита:** 2026-07-18  
**Scope:** историческая research-ветка и внешняя evidence base  
**Статус:** historical input для `roadmap/gamification/README.md`, не production contract

## Источник

Research branch:

```text
chatgpt/gamification-concept-foundation
```

На дату аудита относительно тогдашнего `master`:

```text
ahead: 48 commits
behind: 99 commits
merge base: 4d197c1037fd66401735e654c6697791364518a4
```

Ветка является research source, а не merge-ready production feature branch.

## Найденное состояние

- Progression и Anki XP foundations — `DRAFT v0.2`;
- Review taxonomy, rewards, abuse и day aggregation разработаны как drafts;
- Stage 5A и несколько simulator sub-stages документированы complete;
- Stage 5B.C и общий Review simulation — `PARTIAL`;
- open blocker — cross-horizon retention-cycling evidence;
- Learn XP и Create XP не начаты;
- global XP conversion, production ledger/API/migrations/UI не спроектированы.

Spot-check подтвердил наличие simulator implementation и tests; существовавшие tests заявляли 26 scenarios и 53 assertions. Это подтверждение наличия assets, а не замена повторному запуску на актуальной базе.

## Решение по ветке

- не merge/rebase historical branch целиком;
- создать актуальную research branch от current base;
- selectively reconcile documents, source, scenarios, schemas и tests;
- повторно выполнить documented checks;
- отделить reproducible current evidence от superseded reports;
- сохранить isolation от production package/Fast CI.

## Внешняя evidence base

Исследования поддерживают осторожный, theory-informed подход, но не обещают, что points автоматически улучшают обучение.

Основные выводы:

- поддерживать autonomy, competence и relatedness;
- персонализация может быть лучше one-size-fits-all;
- points, badges, competition и leaderboards могут приносить вред;
- long-term effects требуют longitudinal и matched-control evidence;
- engagement metrics необходимо отделять от learning outcomes;
- explainable progress и constructive feedback предпочтительнее escalating extrinsic rewards.

References:

- https://doi.org/10.1016/j.lmot.2024.102015
- https://doi.org/10.1007/s11423-023-10337-7
- https://doi.org/10.1016/j.lindif.2024.102470
- https://doi.org/10.1111/jcal.13077
- https://doi.org/10.1016/j.infsof.2022.107142
- https://doi.org/10.3390/educsci11010032

## Ограничения

Этот отчёт не подтверждает актуальную executable baseline, не принимает XP formula и не разрешает production integration. Текущие activation criteria находятся только в [Gamification roadmap](../../roadmap/gamification/README.md).
