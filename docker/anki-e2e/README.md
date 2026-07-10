# Anki Study Report Docker E2E

This directory contains the heavy Docker-based E2E environment for running the
add-on inside real Anki Desktop with an isolated Linux profile.

It is intentionally separate from the fast local test suite. The normal local
checks remain:

```bash
cd web-dashboard
pnpm run test:frontend
pnpm run build
cd ..
node scripts/run_python.mjs -m pytest
python scripts/package_addon.py --check-only
```

Run the full local check without Docker:

```powershell
scripts/run_full_check.ps1 -SkipDocker
```

Run the full local check with Docker E2E and a clean Docker volume first:

```powershell
scripts/run_full_check.ps1 -CleanDocker
```

Run only Docker E2E through the full-check wrapper:

```powershell
scripts/run_full_check.ps1 -DockerOnly
```

## When to Run Checks

- Fast checks: run Python tests, frontend tests, and frontend build before a
  normal commit that changes Python, TypeScript, or dashboard assets.
- Package check: run before building or handing off `anki_study_report.ankiaddon`.
- Docker E2E: run before merging renderer, dashboard runtime, or Anki desktop
  integration changes.
- Docker E2E with `KEEP_E2E_DATA=1`: use only for debugging an E2E failure where
  preserving the temporary profile helps diagnosis.
- Full check script: run before a large merge, checkpoint, or branch handoff.

## Release Package CSS Checks

Build the release add-on from the project root:

```powershell
.\build_ankiaddon.ps1
```

The script validates that it is running from the Anki Study Report checkout by
checking `web-dashboard/package.json`, `anki_study_report/manifest.json`, and
`scripts/package_addon.py`. The package validator also reads
`web_dashboard/index.html` inside the archive and checks that every linked
Vite JS/CSS asset exists in the `.ankiaddon`, is non-empty, and that dashboard
CSS markers such as theme rules, app shell styles, Cards table styles, and
Shadow DOM preview host styles are present.

For manual Anki checks, remove the old installed add-on folder from
`addons21` before installing a new `.ankiaddon`, or verify that Anki fully
replaced the previous install. Then restart Anki and reopen/restart the
dashboard server. This avoids judging a fresh archive through stale installed
`web_dashboard/assets` files. Runtime outputs such as `e2e-artifacts/`,
screenshots, logs, and old generated dashboard assets must stay out of the
release archive.

## Architecture

- Base image: `mcr.microsoft.com/playwright:v1.49.1-noble`
- Anki Desktop: official `anki-${ANKI_VERSION}-linux-x86_64.tar.zst` release
- Default Anki version: `26.05`
- Headless display: `Xvfb :99`
- Profile base: `/e2e/anki-data`
- Profile name: `E2E`
- Profile metadata DB: `/e2e/anki-data/prefs21.db`
- Add-on install path: `/e2e/anki-data/addons21/anki_study_report_e2e`
- Artifacts path: `/e2e/artifacts`

The project source is bind-mounted read-only at `/workspace`. The runner copies
it into `/e2e/workspace-build` before installing dependencies or building
dashboard assets, so the container writes only to its internal build directory
and `/e2e/artifacts`.

## Fixture Collection

`create-profile.sh` resets `/e2e/anki-data` by default and recreates the
base-level add-ons folder plus `/e2e/anki-data/E2E`. Set `KEEP_E2E_DATA=1` to
skip that reset while debugging.

`bootstrap-prefs.py` creates `/e2e/anki-data/prefs21.db` before Anki starts.
It writes the `profiles` table with pickled protocol 4 `_global` metadata and
the `E2E` profile row, matching Anki's profile manager storage format. The
metadata disables update prompts, sets English as the default language, records
`last_loaded_profile_name=E2E`, and disables update/add-on update checks. The
profile row disables sync/media sync and includes Anki's standard window,
import, backup, search, and legacy color/media keys.

`seed-collection.py` then creates a fresh `collection.anki2` in the E2E profile
for each run. It does not use or mount any personal Anki data.

The collection includes:

- Japanese vocabulary card with `[sound:要望.mp3]`, `要.gif`, `望.gif`, inline
  color, `.word-focus`, and night-mode CSS.
- Generic non-Japanese front/back card.
- Custom CSS card.
- Unsafe sanitizer card with script/file/javascript examples for API-level
  sanitizer checks.

Synthetic media fixtures are written into
`/e2e/anki-data/E2E/collection.media`. The default GIF fixtures are large
enough for browser smoke tests to verify image loading and rendered dimensions.

For local visual checks against real Anki media, set a read-only media source
before running `scripts/run_anki_e2e_docker.ps1`:

```powershell
$env:ANKI_E2E_REAL_MEDIA_DIR="C:\Users\KykLa\AppData\Roaming\Anki2\1-й пользователь\collection.media"
$env:ANKI_E2E_REQUIRE_REAL_MEDIA="1"
.\scripts\run_anki_e2e_docker.ps1
Remove-Item Env:\ANKI_E2E_REAL_MEDIA_DIR
Remove-Item Env:\ANKI_E2E_REQUIRE_REAL_MEDIA
```

Only the allowlisted files `要.gif`, `望.gif`, and `要望.mp3` are copied into
the isolated E2E profile. The real `collection.anki2`, profile folder,
backups, add-on data, trash, and other personal files are not mounted or
copied. Without these environment variables, Docker E2E uses the synthetic
fixtures and remains CI-safe.

## APKG Fixture Mode

The default Docker E2E run always seeds the synthetic collection and then
imports the tracked APKG fixture when it is present in the checkout. If no APKG
fixture is present, the runner keeps using the synthetic collection and writes
`apkg-import-summary.json` with `enabled: false`.

APKG mode imports a sanitized test deck into the isolated E2E collection after
the synthetic fixture is seeded and before Anki starts. The APKG is fixture-only
regression data for card rendering and dashboard previews; do not use a real
personal collection or full Anki profile here. Imported cards are made
problematic programmatically with deterministic E2E-only `revlog` and card
stats, so they appear in Cards page / `attentionCards`.

Tracked fixture path, only for small sanitized test decks:

```text
docker/anki-e2e/fixtures/asr-e2e-render-fixtures.apkg
```

Local-only fixture mode is preferred while iterating. The PowerShell wrapper
copies the host file into ignored staging:

```text
docker/anki-e2e/local-input/asr-e2e-render-fixtures.apkg
```

Docker mounts that directory read-only at `/e2e/local-input/`. The staged
`local-input` folder, screenshots, logs, HTML dumps, and JSON runtime artifacts
are ignored and must not be committed.

Run the default synthetic E2E:

```powershell
.\scripts\run_anki_e2e_docker.ps1
```

Run strict APKG fixture E2E with the tracked fixture:

```powershell
.\scripts\run_full_check.ps1 -DockerOnly -RequireApkgFixture
```

Run APKG-derived Cards performance smoke with 100 problematic cards:

```powershell
.\scripts\run_full_check.ps1 -DockerOnly -RequireApkgFixture -Perf100
```

`-Perf100` sets `ANKI_E2E_PERF100=1`. The E2E setup keeps the tracked APKG as
the source fixture, clones its imported notes/cards inside the isolated Docker
collection until 100 cards are problematic, and writes
`browser-smoke-performance-100-<label>.json` with mode, viewport, host,
render-source, scroll, and layout counters.

Run strict APKG local fixture E2E while iterating on an ignored local file:

```powershell
$env:ANKI_E2E_APKG_FIXTURE="C:\path\to\asr-e2e-render-fixtures.apkg"
$env:ANKI_E2E_REQUIRE_APKG_FIXTURE="1"
docker compose -f docker\anki-e2e\docker-compose.yml down -v
.\scripts\run_anki_e2e_docker.ps1
Remove-Item Env:\ANKI_E2E_APKG_FIXTURE
Remove-Item Env:\ANKI_E2E_REQUIRE_APKG_FIXTURE
```

The APKG importer first uses Anki's package importer API
`anki.importing.apkg.AnkiPackageImporter`. If that API is not available in the
installed Anki package, the script tries the collection backend package import
method and otherwise fails with a clear diagnostic rather than manually
unpacking the APKG.

## Add-on E2E Mode

The add-on only enables E2E shortcuts when:

```bash
ANKI_STUDY_REPORT_E2E=1
```

In that mode it starts the dashboard server, publishes the default dashboard
report, and writes:

```text
/e2e/artifacts/runtime/dashboard-ready.json
/e2e/artifacts/runtime/addon-e2e-events.jsonl
```

The readiness file includes `port`, `baseUrl`, `token`, `startedAt`,
`addonVersion`, `profile`, and `reportAvailable`. The dashboard token is not
written into report payload artifacts.

The JSONL event file records the add-on startup/readiness pipeline:
`import_start`, `addon_folder_present`, `e2e_env_detected`, `hook_registered`,
`import_done`, `hook_fired`, `bootstrap_scheduled`, `collection_available`,
`report_build_start`, `report_build_done`, `server_start_start`,
`server_start_done`, `report_publish_start`, `report_publish_done`,
`report_published`, `readiness_write_start`, and `readiness_write_done`.
If the collection is missing it records `collection_unavailable` with main
window/profile details. On failure it records an `error` stage with traceback
details when the add-on can catch the exception.

`start-anki.sh` also writes the initial `addon_folder_present` marker before
launching Anki. If that is the last stage and no `import_start` appears, Anki
did not import the add-on.

Before launching Anki, `start-anki.sh` prints whether `prefs21.db`,
`collection.anki2`, and the installed add-on `__init__.py` exist. It also
queries the `profiles` table with Python `sqlite3` and prints the profile names
and blob sizes.

The health check is token-protected:

```text
GET /api/health?token=...
```

## Commands

Build the image:

```bash
docker compose -f docker/anki-e2e/docker-compose.yml build
```

For local development, `ANKI_SHA256` is optional. The downloaded Anki archive is
verified when the hash is provided, but the Docker E2E flow remains runnable
without a checksum for quick local iteration.

For CI or strict reproducibility, require the hash explicitly:

```bash
docker compose -f docker/anki-e2e/docker-compose.yml build --build-arg ANKI_REQUIRE_SHA256=1 --build-arg ANKI_SHA256=<sha256>
```

The equivalent environment-variable form is:

```bash
ANKI_REQUIRE_SHA256=1 ANKI_SHA256=<sha256> docker compose -f docker/anki-e2e/docker-compose.yml build
```

If `apt-get update` or `apt-get install` fails while fetching Ubuntu packages
from `archive.ubuntu.com` or `security.ubuntu.com`, retry the build first. The
Dockerfile configures apt with 5 retries and 30 second HTTP/HTTPS timeouts.

If the same mirror/CDN failure repeats, build with another Ubuntu mirror:

```bash
docker compose -f docker/anki-e2e/docker-compose.yml build --build-arg UBUNTU_MIRROR=http://mirror.math.princeton.edu/pub/ubuntu
```

Run E2E:

```bash
docker compose -f docker/anki-e2e/docker-compose.yml run --rm anki-e2e
```

Run from PowerShell:

```powershell
scripts/run_anki_e2e_docker.ps1
```

Run and keep artifacts in a specific folder:

```powershell
docker compose -f docker/anki-e2e/docker-compose.yml run --rm -v "${PWD}/e2e-artifacts:/e2e/artifacts" anki-e2e
```

Debug shell:

```bash
docker compose -f docker/anki-e2e/docker-compose.yml run --rm anki-e2e bash
```

The Dockerfile defaults to official Ubuntu packages over HTTPS to avoid
transient plain-HTTP CDN failures. Override the mirror when needed:

```bash
docker compose -f docker/anki-e2e/docker-compose.yml build --build-arg UBUNTU_MIRROR=https://mirror.example.org/ubuntu
```

If Anki fails with a Qt `xcb` platform plugin error, inspect:

```text
e2e-artifacts/diagnostics/qt-xcb-diagnostics-first.log
e2e-artifacts/diagnostics/anki-stdout-first.log
e2e-artifacts/diagnostics/anki-stderr-first.log
```

The startup script records `xdpyinfo`, the discovered `libqxcb.so` path, and
`ldd` output for that plugin. To make Qt print verbose plugin loading details
for the next run, set:

```bash
ANKI_STUDY_REPORT_E2E_DEBUG_QT=1 docker compose -f docker/anki-e2e/docker-compose.yml run --rm anki-e2e
```

## E2E Flow

`run-e2e.sh` performs:

1. Copy `/workspace` to `/e2e/workspace-build`.
2. Run `pnpm install --frozen-lockfile`.
3. Run `pnpm run build:addon`.
4. Build and validate `/e2e/artifacts/package/anki_study_report.ankiaddon`.
5. Create the isolated `E2E` Anki profile.
6. Bootstrap `/e2e/anki-data/prefs21.db` with `_global` and `E2E`.
7. Seed the fixture collection and media.
8. Copy the unpacked add-on into `addons21/anki_study_report_e2e`.
9. Start Anki in Xvfb with `-b /e2e/anki-data -p E2E`.
10. Wait for `runtime/dashboard-ready.json` and `/api/health`.
11. Run `smoke-api.py`.
12. Run `smoke-browser.mjs`, verify Cards preview modes, all existing page
    routes, avatar menu, and save deterministic light/dark screenshots.
    `table` and `tiles` stay front-only; `ankiPreview` checks one answer-only
    `AnkiCardShadowPreview` host rendered from `backHtml`.
13. Stop Anki.
14. Start Anki again with the same profile.
15. Wait for readiness and rerun API smoke.

## Artifacts

The default host artifact folder is:

```text
e2e-artifacts/
```

The root contains a redacted `artifact-manifest.json` plus category folders:

```text
e2e-artifacts/
├─ artifact-manifest.json
├─ runtime/                    dashboard-ready.json, events and PIDs
├─ diagnostics/                Anki/Xvfb logs, env, startup trees and tails
├─ reports/                    API, browser, APKG and fixture JSON
├─ html/                       redacted Cards/failure DOM dumps
├─ package/                    anki_study_report.ankiaddon
└─ screenshots/
   ├─ navigation/              avatar-menu-light.png, avatar-menu-dark.png
   ├─ pages/
   │  ├─ today|calendar|decks|profile|tools/
   │  └─ settings/report|data|server|sources|logs/
   └─ cards/
      ├─ synthetic/table|tiles|anki-preview/
      └─ apkg/table|tiles|anki-preview/
```

Each page and Cards leaf contains deterministic `light.png` and `dark.png`
files. A strict APKG run produces 20 page screenshots, 2 navigation screenshots,
6 synthetic Cards screenshots and 6 APKG Cards screenshots. Browser failures
write a screenshot under `screenshots/failures/`, HTML under `html/failures/`,
machine-readable summaries under `reports/`, and console logs under
`diagnostics/`.

The `calendar` page leaf is the Stage 4 Activity surface at canonical
`#/calendar`. Browser smoke exercises the default 90-day period, metric/day
selection, inactive details, five-plus deck expansion, derived daily/weekly
feed and explicit load-more before the light/dark page capture.

The manifest stores only existing relative paths and route/theme/mode/fixture
metadata. Validation rejects missing required files, absolute paths, traversal
and duplicates; missing optional files are omitted. The canonical add-on log is
`diagnostics/anki_study_report.log` (no hyphen alias). The readiness JSON may
contain the runtime token, but the manifest indexes only its path and never its
contents or a full token-bearing URL. Runtime PID files are intentionally not
required manifest entries.

## Safety

- The host `%APPDATA%/Anki2` folder is never mounted.
- The source mount is read-only in Compose.
- The fixture collection is generated from scratch.
- Media fixtures are tiny synthetic files.
- API response samples are sanitized and checked for token leakage.
- Docker E2E is a heavy command and requires Docker Desktop/WSL2 on Windows.

## Security Notes

- This container is test-only infrastructure for Docker E2E.
- Host Anki data is not mounted into the container.
- The project source mount is read-only; the runner copies it to a writable
  container-local build directory.
- Fixture data is synthetic and recreated for normal runs.
- The container may run as `root` to keep the Qt, Anki, and Xvfb setup simple in
  this test harness.
- `QTWEBENGINE_DISABLE_SANDBOX=1` is used only inside this test-only Docker E2E
  environment.
- The root container setup and Qt WebEngine sandbox override are not production
  or runtime recommendations.
