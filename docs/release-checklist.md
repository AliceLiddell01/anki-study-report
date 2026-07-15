# Release checklist

Снимок документации: 2026-07-14.

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

Проверить output bundle guard: Statistics/FSRS должны оставаться dynamic
entries, ни один JS chunk не должен превышать 500,000 bytes, large-chunk warning
не должен появляться.

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

В package output должны быть пустыми `Missing/Empty linked dashboard assets`,
`Unreferenced dashboard JS/CSS assets`, `Dashboard asset graph errors` и
`Unsafe dashboard asset references`.

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
старого flat dump; вся папка остаётся ignored. Settings Hub run содержит 20
page screenshots. Все indexed paths должны существовать, быть relative и
уникальными; canonical log — `diagnostics/anki_study_report.log`, а raw token
допустим только внутри ignored `runtime/dashboard-ready.json`.

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

## Version and gated publication

- `anki_study_report/version.py`, `release/changelog.json`, generated changelog outputs and `manifest.json.mod`
  describe the same release.
- `prepare_release.py --version <version> --check` passes.
- Release PR workflows pass without production secrets or mutations.
- After merge, dispatch `release.yml` from exact current `master` with explicit
  version/channel.
- Если предыдущий run оставил draft, проверить его через authenticated
  paginated `List releases`, а не считать `404` published-by-tag endpoint
  доказательством отсутствия release.
- Existing matching draft должен быть reused и retargeted на exact новый
  `master` SHA; не удалять его и не создавать второй вручную.
- Перед Environment approval проверить `github-draft-report-*`: release ID,
  target commitish, ровно три expected assets, `uploaded` state и verified
  SHA-256 для каждого asset.
- Approve `ankiweb-production` only after the exact-artifact `standard/full`
  gate and draft GitHub Release are green.
- После изменения workflow/publisher запускать новый dispatch с текущего
  `master`; не использовать `Re-run failed jobs` старого run.
- Для восстановления `v1.0.0` запустить `release.yml` с `branch=master`,
  `version=1.0.0`, `channel=stable`, проверить draft report и только затем
  одобрить `ankiweb-production`.
- В publisher report authoritative evidence — exact owner-form metadata и
  normalized description SHA-256; публичный description container является
  bounded eventual smoke. Уже актуальное состояние должно завершиться с
  `mutationCount: 0` и `idempotent: true`.
- Confirm final run evidence: commit SHA, artifact SHA-256, E2E-tested package
  SHA, GitHub assets, description hash, public AnkiWeb download hash.
- Do not manually create another AnkiWeb branch or upload a different archive.

Commands and recovery are in `docs/release-automation.md`.

## Do not publish

- If package validation fails.
- If archive contains runtime/generated files.
- If dashboard assets are stale.
- If token-bearing artifacts are staged.
- If Docker/live Anki failed for a runtime-risk change and the failure is not
  understood.
