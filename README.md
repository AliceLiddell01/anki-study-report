# Anki Study Report

Документация описывает текущий проект на **2026-07-22**.

Anki Study Report — add-on для Anki 26.05+ с Python runtime и React/TypeScript dashboard. Он собирает локальную статистику обучения, строит Markdown/HTML-отчёт и предоставляет token-protected dashboard на `127.0.0.1` с Statistics/FSRS, Activity, Decks, native Cards/Notes Search, Safe Actions, Cards и локальными Signals/Notifications.

Settings также содержит локальный Inspection Profiles workspace для явной настройки декларативных проверок exact note types; он не изменяет коллекцию.

Signals, evidence, entity references и notification preferences остаются per-profile/local и не отправляются в remote telemetry. Отдельный private telemetry service принимает только opt-in bounded technical events.

## Быстрый вход

```text
anki_study_report/       Python add-on/runtime/API
web-dashboard/           Vite + React + TypeScript
tests/                   Python tests
scripts/                 build/package/verification
docker/anki-e2e/         real-Anki Desktop E2E
docs/                    current contracts
roadmap/                 tracks, dependencies and activation criteria
reports/                 historical evidence
```

Главный release artifact — flat `anki_study_report.ankiaddon`.

Current primary navigation:

```text
Сегодня → Активность → Статистика → Колоды → Поиск → Карточки
```

Profile, Tools, Settings and Support live outside the primary study navigation. Server, Sources and Logs remain current diagnostic/settings surfaces until the corresponding roadmap cleanup is implemented.

## Roadmap

The accepted product contour is complete through **Stage 9.5**. Future work is organized by independent tracks rather than one global Stage 10–13 queue.

- [Roadmap map](roadmap/README.md)
- [Core critical path](roadmap/core/README.md): `C2 owner acceptance closure → C3 UI & Shell → C4 Data Independence → C5 Today v2 → C6 Profile v2 → Core 1.0`
- [Gamification](roadmap/gamification/README.md): parallel research/product track; production not approved
- [Telemetry operations](roadmap/operations/README.md): separate protected admin tooling
- [Identity continuity](roadmap/identity/README.md): conditional opt-in gate
- [Extension ecosystem](roadmap/extensions/README.md): conditional/deferred
- [Platform / CI](roadmap/platform/README.md): independent delivery/E2E track

Only the Core sequence is mandatory for Core 1.0. Gamification, accounts, telemetry admin UI, extension packs, `C1.6B` and contextual additions do not block it unless a documented dependency is introduced.

Current Core status:

```text
C1 — complete and accepted
C2 — implemented, exact-SHA verified and merged into core
core merge commit — edb140b1197910aae31500a40e4a8287cc46b760
post-merge owner acceptance — reopened after manual Cards/Inspection Profiles review
next action — bounded C2 manual acceptance remediation
C3–C6 — mandatory future Core path
Core 1.0 release — not started
```

The revised Core path explicitly requires:

- a full-width desktop shell instead of one global narrow centered container;
- a site-wide UI/content system with shared headers, surfaces, shapes, spacing and motion;
- removal of obsolete Tools/Report surfaces;
- first-party replacement of useful external data-source functionality before Sources is deleted;
- a focused daily `Today v2`;
- a full-width editable `Profile v2 Foundation` without fake gamification placeholders.

Current platform state:

```text
CI Stage 6B: Complete
cloud real-Anki E2E: immutable GHCR digest only
manual E2E package: exact Fast CI artifact
release E2E package: exact release artifact
local Docker build: development/diagnostic fallback
future CI 7+: conditional on new measurements
```

## Important commands

Canonical non-Docker check:

```powershell
.\scripts\run_full_check.ps1 -SkipDocker
```

Release build:

```powershell
.\build_ankiaddon.ps1
```

Package validation:

```powershell
node scripts/run_python.mjs scripts/package_addon.py --check
node scripts/run_python.mjs scripts/package_addon.py --check-only
```

Full local Docker E2E, only when risk/policy requires it:

```powershell
.\scripts\run_full_check.ps1 -CleanDocker
```

Manual gated release after merge:

```powershell
node scripts/run_python.mjs scripts/prepare_release.py --version 1.0.0 --check
gh workflow run release.yml --ref master -f version=1.0.0 -f channel=stable
```

Merge or push does not publish automatically.

## Documentation

Start with:

- [Documentation index](docs/README.md)
- [Project overview](docs/project-overview.md)
- [Architecture](docs/architecture.md)
- [Dashboard API](docs/dashboard-api.md)
- [Navigation / IA](docs/navigation-ia.md)
- [Security and safety](docs/security-and-safety.md)
- [Test matrix](docs/test-matrix.md)
- [Verification policy](docs/verification-run-policy.md)
- [CI/CD](docs/ci-cd.md)
- [GHCR E2E consumer](docs/ghcr-e2e-consumer.md)
- [Decision log](docs/decision-log.md)
- [AI handoff](docs/ai-handoff.md)
- [Historical reports](reports/README.md)

## Contract rules

1. Payload/public behavior changes require synchronized backend, frontend types/validators, tests and docs.
2. Frontend never reads the Anki collection directly.
3. The dashboard remains loopback-only and token-protected.
4. Sanitizer, media validation, action allowlists and preview isolation are security contracts.
5. Generated assets, logs, screenshots, profile data, tokens, `.ankiaddon` and E2E outputs are not committed.
6. Production code is not changed to satisfy an outdated test when current behavior is correct.
7. Research code/evidence is not silently added to Fast CI or package contents.
8. Release remains manual, approval-gated and exact-artifact based.
9. Desktop working pages must not be constrained by one global narrow `max-width`; width limits are local component decisions.
10. New pages must reuse shared layout/content primitives instead of introducing another local visual grammar.

## Participation and safety

- [Contributing](CONTRIBUTING.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Security policy](SECURITY.md)
- [GPL-3.0-only license](LICENSE)

Potential vulnerabilities must use the private channel documented in `SECURITY.md`, not public Issues.
