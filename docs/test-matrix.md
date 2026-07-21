# Матрица проверок

**Снимок документации:** 2026-07-22

Минимальная проверка — нижняя граница для небольшого изменения. Желательная проверка нужна перед merge/release либо когда diff затрагивает несколько layers.

Full real-Anki E2E — integration gate, а не обычный development loop.

## Общая матрица

| Изменение | Минимальная проверка | Желательная проверка | Docker/live Anki | Причина |
| --- | --- | --- | --- | --- |
| docs-only | `git diff --check` | вручную проверить links, code fences и paths | Нет | code/runtime не менялись |
| pure Python logic | focused pytest | `compileall` конкретных add-on modules | Обычно нет | pure modules тестируются без Anki |
| Anki hooks/startup/profile lifecycle | targeted pytest | live Anki smoke или real-Anki E2E | Да | `aqt`, hooks и restart не видны unit tests |
| dashboard payload/public schema | backend contract tests | frontend parser/types tests + build | Иногда | backend/frontend/docs должны меняться синхронно |
| frontend UI/types | focused Vitest + typecheck | `pnpm run build:addon` | Нет для pure UI | типы, state и normalization |
| card rendering/media/preview | frontend preview tests + sanitizer pytest | targeted Cards real-Anki smoke | Да для final | native render, media и Shadow DOM требуют runtime |
| dashboard server/token/actions | server/action pytest | frontend API tests + local smoke | Иногда | token, allowlist, HTTP errors и QueryOp |
| Search + Safe Actions | search/runtime/entity action tests + frontend | Fast CI + targeted `standard/global`; full при shared diff | Да | latest-wins reads, exact IDs, undoable mutations и Browser bridge |
| Triage query v4 | triage candidates/service/runtime/dashboard tests + parser/hook tests | Fast CI + targeted `standard/cards` | Да для final | independent sources, cursor coherence и live profiles |
| C1.6 exact-card resolution | recheck backend/API/parser/client/hook/page/focus tests | Fast CI + targeted `standard/cards` с restart + final `standard/full` при shared runtime diff | Да | exact-card detector reuse, fail-closed reconciliation, focus и E2E handoff |
| Inspection Profiles | store/service/runtime/schema/dashboard + frontend editor tests | Fast CI + targeted `standard/cards` с restart | Да | fingerprints, persistence, profile isolation и live note types |
| Settings/Profile API | config/profile/dashboard tests + frontend | package check; real-Anki при lifecycle change | Иногда | allowlists, atomic storage и reload |
| Statistics/FSRS | service/dashboard tests + frontend | Fast CI + targeted `standard/stats`; final full при shared diff | Да для final | native configuration/memory/simulator и screenshots |
| Signals/Notifications | detector/store/server + Bell/Center/Settings tests | targeted `standard/notifications` с restart + one final full | Да | App Shell, persistence и local API |
| telemetry/privacy client | telemetry contract/store/client/dashboard tests | `standard/settings` с fake loopback и restart | Да при queue/network/deletion | consent, bounded queue, retry и deletion |
| packaging/build scripts | `package_addon.py --check` | exact `.ankiaddon` build | Нет | forbidden files, assets и metadata |
| Docker E2E/runtime behavior | targeted local checks | risk-required exact-package cloud E2E | Да | real Anki Desktop/import/restart/browser |
| E2E artifacts/redaction | helper/exporter tests | one relevant E2E run | Да | manifest, token/path redaction и public-safe artifact |
| CI workflows/handoff | focused workflow/handoff tests + YAML/static scans | one exact-SHA manual observation после local PASS | По risk | checkout/package identity, hashes и failure semantics |
| release/publisher | release/package/publisher tests + `-SkipDocker` | exact release artifact + `standard/full` | Да | build/E2E/GitHub/AnkiWeb SHA parity |

## Команды

```powershell
git diff --check
node scripts/run_python.mjs -m pytest
cd web-dashboard
pnpm run test:frontend
pnpm run typecheck
pnpm run build:addon
```

```powershell
./build_ankiaddon.ps1
./scripts/run_full_check.ps1 -SkipDocker
./scripts/run_full_check.ps1 -CleanDocker
./scripts/run_full_check.ps1 -DockerOnly
```

В WSL `.ps1` entrypoints запускаются через установленный PowerShell Core согласно repository environment contract.

## Stop-loss

- после failure сначала анализируются artifacts/logs/root cause;
- rerun разрешён только после concrete fix или для отдельно подтверждённой infrastructure failure;
- второй одинаковый failure прекращает blind reruns;
- successful exact-SHA run не повторяется;
- local full Docker не дублирует successful exact-package cloud full gate;
- warm-cache repeats и performance workers не запускаются без отдельной задачи.

## Когда не запускать Docker E2E

Не запускать Docker E2E для:

- docs-only changes;
- небольших pure helpers;
- changes, не затрагивающих startup, rendering, media, server, package layout или live collection behavior.

## Cards C1.5R.5

Focused completion включает:

- Cards hook/page/component/helper Vitest;
- Triage/Search/dashboard pytest;
- typecheck;
- production build/bundle guard;
- package validation;
- isolated browser evidence;
- canonical non-Docker gate.

Browser matrix покрывает wide light/dark, 100 items, 1024 queue/drawer/modal, partial sources, needs-review profiles, continuation и empty state.

## Triage C1.5R.4

Проверяются:

- independent period learning и current-content sources;
- confirmed-profile boundary;
- 500-note keyset bound;
- explicit coherent cursor;
- deterministic representative card;
- отсутствие preview/media reads в candidate scan.

## Guided Inspection Profiles C1.5R.6

Required contour:

- page/hook/Basic/Advanced/validation/projection/API tests;
- store/service/runtime/dashboard/triage/package regressions;
- typecheck и production build;
- package validation;
- non-Docker gate;
- Chromium Japanese/Programming/lifecycle/light/dark/1024 evidence.

## C1.6 canonical single-card resolution loop

Focused contour:

```text
triage candidates/service/runtime/dashboard
Triage API parser/client
Cards hook/page/detail/inbox
race/latest-wins behavior
reason reconciliation
focus recovery
E2E helpers and smoke assertions
```

Final recorded evidence:

```text
focused backend/E2E helpers: 81 tests PASS
frontend: 324 tests PASS
Python compileall: PASS
production build/bundle guard: PASS — entry 429,516 bytes
package: PASS — 77 entries
canonical non-Docker: PASS — 324 frontend, 802 Python, 5 platform skips
Fast CI 29862254960: PASS
final-head Fast CI 29863609253: PASS
targeted standard/cards + restart 29862551442: PASS
final standard/full 29862800106: PASS
```

Local Docker не повторялся после successful exact-package cloud E2E. Проверка на private Anki profile владельца не выполнялась.

## Release delivery

Release/version/package/publisher/workflow changes требуют focused tests:

```text
test_release_automation.py
test_ankiweb_publisher.py
test_release_workflow.py
test_package_build.py
tests/publish_ankiweb.test.mjs
```

Final production gate — `standard/full` на exact release artifact SHA. Heavy release job запускается только manual dispatch из разрешённой branch после отдельного owner decision.

## Product notices и consent

Required:

- product notices/changelog/dashboard/package/release tests;
- coordinator/API frontend tests;
- RU/EN parity;
- targeted `standard/settings`;
- final `standard/full` только при shared App Shell/server/E2E/package diff.

Real-Anki smoke проверяет consent-first order, no preselection, decline persistence, What’s New no-repeat/manual reopen и Privacy route.