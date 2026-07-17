# CI Stage 11 — Release reproducibility

**Status:** Conditional

Stage 11 рассматривается после стабилизации core/release contracts. Текущий
manual exact-artifact release path сохраняется.

## Цель

Добиться воспроизводимой сборки `.ankiaddon` и усилить проверяемость release
inputs без второй постоянной pipeline.

## Возможный scope

- canonical ZIP entry ordering;
- deterministic timestamps и permissions;
- explicit UTF-8 filenames;
- controlled line-ending handling для text assets;
- stable generated dashboard asset graph;
- clean rebuild comparison по exact SHA-256;
- deterministic Python development dependency lock;
- frozen pnpm/toolchain validation;
- review dependency changes отдельно от обычного code diff;
- SBOM для shipped add-on assets, если его польза подтверждена;
- проверка существующего provenance evidence перед final release closeout;
- bounded policy обновления pinned Actions и GHCR environment revisions;
- machine-readable release evidence index и operator checklist.

## Правила принятия

- temporary dual-build experiment не становится постоянным duplicate job;
- одинаковые inputs должны давать одинаковые bytes либо documented
  platform-bound result;
- exact package SHA остаётся единым для E2E, GitHub Release и AnkiWeb;
- release по-прежнему запускается вручную с exact current `master`;
- real-Anki `standard/full` и approval gate сохраняются;
- опубликованные SemVer bytes не перезаписываются;
- recovery выполняется новым run текущего workflow.

## Completion criteria

- reproducibility contract покрыт tests;
- clean paired build evidence сохранено в `reports/ci/`;
- dependency/toolchain changes reviewable и pinned;
- provenance/SBOM verification документирована, если SBOM принят;
- package/release docs и recovery runbook синхронизированы.

## Out of scope

- automatic publication after merge;
- mutable package identity;
- removal of exact-artifact or real-Anki gates;
- permanent duplicate release builders.
