# Release checklist

Снимок документации: 2026-07-06.

Чеклист перед публикацией или передачей `anki_study_report.ankiaddon`.

## Source state

- `git status --short --branch` чистый или pending changes понятны.
- Поведение, API и contract изменения отражены в docs.
- `manifest.json` проверен.
- `config.json` проверен.
- Нет staged/generated/runtime мусора.

## Local checks

- Frontend tests:

```powershell
cd web-dashboard
pnpm run test:frontend
```

- Dashboard build into add-on:

```powershell
pnpm run build:addon
```

- Python tests:

```powershell
cd ..
node scripts/run_python.mjs -m pytest
```

- Package validation:

```powershell
node scripts/run_python.mjs scripts/package_addon.py --check
node scripts/run_python.mjs scripts/package_addon.py --check-only
```

## Preferred release build

```powershell
.\build_ankiaddon.ps1
```

Record final artifact:

```text
anki_study_report.ankiaddon
```

Record final size manually from filesystem when preparing release notes.

## Optional but required for runtime-risk changes

Run Docker E2E for startup/rendering/server/media/package-layout changes:

```powershell
.\scripts\run_full_check.ps1 -CleanDocker
```

For final Cards preview release handoff, use the strict APKG Perf100 profile:

```powershell
.\scripts\run_full_check.ps1 -CleanDocker -RequireApkgFixture -Perf100
```

This imports `docker/anki-e2e/fixtures/asr-e2e-render-fixtures.apkg`, verifies
the APKG import path, clones imported cards/notes inside the Docker collection
for the 100-card smoke, and leaves timings as diagnostics rather than release
thresholds.

После strict APKG run проверить `e2e-artifacts/artifact-manifest.json`, наличие
light/dark page/navigation pairs и обе Cards matrices под
`screenshots/cards/synthetic` и `screenshots/cards/apkg`. В root не должно быть
старого flat dump; вся папка остаётся ignored.

Do not run heavy Docker E2E for docs-only changes.

## Manual local Anki smoke

- Install fresh `.ankiaddon`.
- Ensure old installed add-on folder/assets are not reused accidentally.
- Restart Anki.
- Open Anki Study Report from Tools menu.
- Build/open report.
- Open dashboard.
- Check Cards page preview mode.
  - `table`/`tiles`: front-only Shadow DOM preview, normal page scroll.
  - `ankiPreview`: answer-only `AnkiCardShadowPreview` host from
    `renderedPreview.backHtml`, no separate front duplication.
- Check one media preview if rendering/media changed.
- Check Actions page only with non-destructive actions unless explicitly needed.

## AnkiWeb/manual publication

There is no project automation for AnkiWeb publication in this checkout.
Before publishing manually:

- Check description.
- Check tags.
- Check changelog.
- Check compatibility with `min_point_version`.
- Keep final artifact path and size in release notes.
- Create release commit/tag if that workflow is being used.

## Do not publish

- If package validation fails.
- If archive contains runtime/generated files.
- If dashboard assets are stale.
- If token-bearing artifacts are staged.
- If Docker/live Anki failed for a runtime-risk change and the failure is not
  understood.
