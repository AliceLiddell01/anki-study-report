# CI Stage 12 — Scale and delivery operations

**Status:** Unscheduled

Stage 12 нужен только если проект заметно вырастет: несколько активных
contributors, высокий PR volume, частые releases или отдельная maintenance team.
Для текущего solo/small-project режима это не обязательный этап.

## Цель

Масштабировать CI/CD governance без превращения repository в сложную platform
систему раньше времени.

## Возможный scope

### Branch and merge governance

- required checks и rulesets для `master`;
- clear ownership для workflow/release changes;
- merge queue только после подтверждённой конкуренции PR и при доступности для
  текущего repository ownership/plan;
- `merge_group` support только вместе с реальным включением merge queue;
- rebase-equivalent merge policy и post-merge Fast CI proof.

Merge queue не добавляется ради моды: при низком PR volume она создаёт лишние
runs и усложняет exact-SHA evidence.

### Capacity and runner strategy

- usage/performance metrics по workflow/job/runner OS;
- monthly minute/storage budget;
- concurrency limits и cancellation superseded runs;
- comparison standard/larger runners только по measured economics;
- self-hosted runner только после отдельного security, maintenance и availability
  design.

Local developer machine не становится автоматическим CI fallback.

### Scheduled maintenance

Допустимы lightweight scheduled checks:

- deprecated Actions/runner warnings;
- dependency and toolchain drift report;
- GHCR environment lock/publication consistency;
- release metadata and documentation consistency;
- non-mutating publisher contract smoke, если DOM drift становится регулярной
  operational проблемой.

Scheduled full real-Anki E2E по умолчанию не нужен. Он вводится только при
доказанной пользе и отдельном quota budget.

### Operational dashboard

Можно собрать read-only CI operations summary:

- p50/p95 runtime и queue time;
- first-run pass и confirmed flake rate;
- top failing phases;
- artifact/storage footprint;
- environment/toolchain age;
- open maintenance exceptions и quarantine expiry.

Dashboard не хранит credentials, не запускает deployments и не заменяет GitHub
как source of truth.

### Delivery resilience

- documented response на GitHub/GHCR/AnkiWeb outage;
- release checkpoint/resume matrix;
- bounded eventual-consistency handling;
- operator decision points before external publication;
- evidence retention для failed/partial release;
- no automatic publication fallback through another service.

## Activation conditions

Stage 12 получает номер active work только при одном или нескольких фактах:

- concurrent PR регулярно конфликтуют на `master`;
- required checks становятся merge bottleneck;
- CI usage приближается к установленному budget;
- release operations требуют нескольких maintainers;
- infrastructure incidents повторяются и имеют measurable cost.

## Completion criteria

- governance соответствует фактическому масштабу проекта;
- дополнительная automation уменьшает operator work или merge risk;
- новые scheduled jobs имеют owner, budget и stop condition;
- branch/release protections покрыты tests или documented inspection;
- current exact-package, immutable-image и approval boundaries сохранены;
- нет обязательного third-party CI provider без отдельного решения.

## Out of scope

- Kubernetes или отдельная CI platform;
- permanent self-hosted fleet для небольшого проекта;
- automatic production publication;
- scheduled heavy tests без budget;
- replacement GitHub Actions без доказанного ограничения текущей системы.
