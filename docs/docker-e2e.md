# Docker E2E

Снимок документации: 2026-07-13.

Подробный технический README уже есть в `docker/anki-e2e/README.md`. Эта
страница фиксирует, как Docker E2E вписывается в общий проект и какие решения
нельзя случайно откатить.

Для диагностики падений см. `docs/troubleshooting.md`.

## Назначение

Docker E2E запускает add-on внутри реального Anki Desktop в изолированном Linux
профиле. Это тяжелая проверка для случаев, когда обычных pytest/Vitest
недостаточно:

- startup hooks Anki;
- dashboard server readiness;
- card preview rendering;
- Shadow DOM / Anki-like preview modes;
- media loading;
- package install layout;
- взаимодействие с реальным Anki profile manager.

## Основные команды

Полный прогон с очисткой Docker volume:

```powershell
.\scripts\run_full_check.ps1 -CleanDocker
```

Только Docker E2E:

```powershell
.\scripts\run_full_check.ps1 -DockerOnly
```

Прямой runner:

```powershell
.\scripts\run_anki_e2e_docker.ps1
```

## Ключевые пути внутри контейнера

```text
/workspace                                      bind-mounted source checkout
/e2e/workspace-build                            writable copied build tree
/e2e/anki-data                                  Anki base profile directory
/e2e/anki-data/prefs21.db                       base profile metadata DB
/e2e/anki-data/E2E                              E2E profile folder
/e2e/anki-data/addons21/anki_study_report_e2e   installed add-on
/e2e/artifacts                                  E2E artifacts
```

Важно: add-on устанавливается на base-level path:

```text
/e2e/anki-data/addons21/anki_study_report_e2e
```

Не переносить его в:

```text
/e2e/anki-data/E2E/addons21/...
```

Для Anki 26.05 также важен base-level `prefs21.db` с `_global` и `E2E` rows в
таблице `profiles`.

## E2E env vars add-on

Add-on включает E2E shortcuts только при:

```text
ANKI_STUDY_REPORT_E2E=1
```

Важные переменные:

```text
ANKI_STUDY_REPORT_E2E
ANKI_STUDY_REPORT_E2E_ARTIFACTS
ANKI_STUDY_REPORT_E2E_ARTIFACTS_DIR
ANKI_STUDY_REPORT_E2E_READY_FILE
```

## Readiness artifacts

Generated outputs разделены по назначению:

```text
e2e-artifacts/
├─ artifact-manifest.json
├─ runtime/
│  ├─ dashboard-ready.json
│  └─ addon-e2e-events.jsonl
├─ diagnostics/                startup trees, logs and tails
├─ reports/                    API/browser/APKG JSON summaries
├─ html/                       redacted DOM dumps
├─ package/                    Docker-built .ankiaddon
└─ screenshots/
   ├─ navigation/              avatar menu, light/dark
   ├─ pages/                   current non-Cards routes, light/dark
   └─ cards/
      ├─ synthetic/            table/tiles/anki-preview, light/dark
      └─ apkg/                 table/tiles/anki-preview, light/dark
```

Readiness readers и add-on E2E bootstrap используют `runtime/`. На
timeout/failure в первую очередь полезны:

```text
e2e-artifacts/runtime/dashboard-ready.json
e2e-artifacts/runtime/addon-e2e-events.jsonl
e2e-artifacts/diagnostics/anki-data-tree.txt
e2e-artifacts/diagnostics/addons-tree.txt
e2e-artifacts/diagnostics/anki-startup-tail.txt
e2e-artifacts/reports/browser-smoke-first.json
e2e-artifacts/html/failures/
e2e-artifacts/screenshots/failures/
```

Эти файлы помогают диагностировать, дошел ли Anki до import, hook, report build,
server start, publish и readiness write.

## Startup markers

`addon-e2e-events.jsonl` должен показывать цепочку вроде:

```text
import_start
addon_folder_present
e2e_env_detected
hook_registered
import_done
hook_fired
bootstrap_scheduled
collection_available
report_build_start
report_build_done
server_start_start
server_start_done
report_publish_start
report_publish_done
readiness_write_start
readiness_write_done
```

Если есть `addon_folder_present`, но нет `import_start`, Anki не импортировал
add-on. Если есть import/hook, но нет server/readiness, смотреть report build
или dashboard server. Если нет профиля, сначала проверять `prefs21.db` и layout.

## Browser smoke modes

Statistics screenshot contract:

- pages light/dark: `stats-overview`, `stats-quality`, `stats-load`,
  `stats-progress`, `stats-decks`;
- states: overview `sparse|comparison`, quality `low-confidence`, load
  `future-due`, progress `current-state`, decks
  `default-selection|custom-selection`;
- zoom 125%: overview, quality, load, decks.

Browser assertions дополнительно проверяют grouped controls, visible panel
borders, no mixed-unit grouped chart, zero-origin bars, no chart/horizontal
clipping, no dock overlap, default deck comparison, Russian user labels,
console/page/request errors и token absence. После cloud run screenshots нужно
просмотреть содержательно; одного manifest/count недостаточно.

Cards preview smoke mode-specific:

- `table` и `tiles` проверяют Shadow DOM host
  `data-testid="anki-card-shadow-preview"` и остаются front-only. В этих
  режимах нет вложенного вертикального table scroll: страница скроллится
  обычным page scroll.
- `ankiPreview` проверяет единственную answer-only секцию
  `data-testid="anki-preview-answer"`, построенную из
  `renderedPreview.backHtml` и rendered через `AnkiCardShadowPreview` host
  `data-shadow-preview-mode="preview"` / `data-preview-side="answer"`.
  Отдельный front в этом режиме не дублируется; если `backHtml` отсутствует,
  ожидается диагностический fallback.
- Preview не использует iframe. Shadow DOM isolation обязателен для всех
  текущих rendered modes: `table`, `tiles` и `ankiPreview`; sanitizer не
  ослабляется, JS templates не исполняются.
- Browser smoke сохраняет screenshots для `table`, `tiles` и `ankiPreview` в
  light/dark темах отдельно для synthetic и APKG fixtures. Он также сохраняет
  light/dark пары десяти текущих non-Cards routes (включая пять Settings Hub
  pages) и открытого avatar menu. Profile smoke отдельно проверяет synthetic
  identity `E2E`, шесть KPI, activity/recent/decks, сохраняет дату и сортировку,
  перезагружает страницу и доказывает persistence через `/api/profile`.
  Browser report отдельно публикует `requestFailures` и `consoleErrors` и
  завершает smoke ошибкой, если они не пусты; `ERR_ABORTED` при намеренной
  навигации между screenshots остаётся только в raw `networkEvents`.
  Activity smoke сохраняет canonical `#/calendar`, проверяет heading/nav
  «Активность», default 90 days, metric/day selection, inactive detail,
  five-plus deck expansion, daily/weekly derived feed и explicit load-more.
  Decks smoke проверяет normalized payload, filtered exclusion, collapsed
  hierarchy, disclosure `aria-expanded`, nested search, status/sibling sort,
  direct/subtree detail, descendant issues и обе typed Anki Browser actions.
  `screenshots/pages/decks/light.png` и `dark.png` входят в manifest как обычная
  light/dark page pair.

  Stage 5.5 дополнительно проверяет persistent theme toggle на product/settings
  routes, light/dark persistence после reload/navigation, отсутствие duplicate
  dock и overlap с profile menu. State screenshots фиксируют expanded Activity
  history и Decks root/parent/leaf. Отдельные zoom screenshots используют
  изолированный Playwright context 1152×800 CSS px при deviceScaleFactor 1.25.

  Stage 6 добавляет пять Statistics routes и light/dark screenshots
  `stats-overview`, `stats-quality`, `stats-load`, `stats-progress`,
  `stats-decks`. Smoke проверяет primary order/active state, direct reload,
  90d default, finite/all-time/single-deck/direct controls, успешный typed
  statistics query, native Stats callback и отсутствие token в DOM. Zoom 125%
  дополнительно покрывает Overview и deck comparison.

`artifact-manifest.json` индексирует только существующие relative paths, status,
Anki version, timestamp, route/theme/mode/fixture metadata. Canonical add-on log
— `diagnostics/anki_study_report.log`; alias с дефисами не создаётся. Validator
отклоняет missing required, absolute, traversal и duplicate paths. Missing
optional artifacts не индексируются. Token и полный dashboard URL туда не
записываются; readiness file может содержать token, но manifest хранит только
его путь. Runtime PID files намеренно не являются required manifest entries.

Tracked APKG fixture находится здесь:

```text
docker/anki-e2e/fixtures/asr-e2e-render-fixtures.apkg
```

Strict APKG прогон:

```powershell
.\scripts\run_full_check.ps1 -DockerOnly -RequireApkgFixture
```

APKG-derived performance smoke на 100 карточек:

```powershell
.\scripts\run_full_check.ps1 -DockerOnly -RequireApkgFixture -Perf100
```

Этот режим не создает новую APKG fixture. После импорта tracked fixture Docker
E2E клонирует импортированные notes/cards внутри изолированной коллекции до
100 problematic cards и проверяет Cards page через тот же native render path.
Perf100 не включает virtualization; timing values в JSON artifacts нужны для
диагностики, а не как жесткие release thresholds. Цель проверки - подтвердить
desktop/laptop dashboard layout и отсутствие clipping/raw HTML/console errors на
100 APKG-derived карточках.

Если smoke падает на Cards page, сначала проверить активный mode и текущую DOM
форму. Не менять production component, пока не доказано, что проблема не в
ожиданиях smoke script.

## Runtime artifacts не коммитить

`e2e-artifacts/`, screenshots, DOM dumps, logs, local APKG input и token-bearing
outputs нужны для диагностики, но должны оставаться вне git.

## Scopes, parallel capture и telemetry

`mode` (`standard` / `strict-apkg` / `perf100`) задаёт fixture semantics, а
независимый `scope` — продуктовую область: `full`, `global`, `stats`, `decks`,
`activity`, `cards`, `settings`. Targeted scope сохраняет startup/readiness/API,
token, browser-error, redaction и manifest core, но не заменяет final `full`.
Restart при `auto` выполняется только для `full`.

Manual workflow также принимает `screenshot_workers` (`auto` = 3, max 4),
`resource_telemetry` и `verify_restart`. Read-only page captures выполняются
одним Chromium через bounded BrowserContext pool; mutating/Profile/settings/
Cards/APKG/restart операции остаются serial.

Новые deterministic reports:

```text
reports/screenshot-performance.json|md
reports/e2e-phase-timings.json|md
reports/resource-samples.jsonl
reports/resource-summary.json|md
reports/e2e-performance-summary.json|md
```

Manifest schema v2 индексирует их и записывает mode/scope/workers. Resource
files обязательны только при включённом sampler. Полный architecture,
baseline и формулы описаны в `docs/e2e-performance.md`.

## GitHub-hosted Ubuntu compatibility

Cloud E2E использует ту же цепочку `run_full_check.ps1` →
`run_anki_e2e_docker.ps1` → Compose → `run-e2e.sh`. PowerShell wrapper вызывает
вложенный `.ps1` через текущий PowerShell host, поэтому не зависит от Windows
`powershell.exe`; executable lookup и paths остаются cross-platform.

Artifacts mount нормализуется до абсолютного host path. Compose сохраняет
read-only `/workspace`, writable `/e2e/workspace-build`, named profile volume и
`shm_size: 2gb`; nested VM не требуется. Xvfb и software Qt/OpenGL работают
внутри обычного Linux container. Local real-media mount включается только через
явные локальные env vars и не активируется в cloud workflow.

Root `.dockerignore` исключает Git metadata, caches, node_modules, generated
dashboard/package/runtime и CI downloads, но сохраняет source и tracked
owner-authorized APKG fixture. Cloud build требует официальный SHA-256 Anki
26.05; Perf100 остаётся diagnostic smoke без performance threshold.

Public Actions artifact создаётся отдельно в `ci-e2e/`. Raw readiness JSON с
token остаётся локальным; exporter публикует только redacted readiness и
проверенные manifest-relative evidence files.
