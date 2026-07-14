# Gated release delivery

Снимок документации: 2026-07-14.

Проект использует каноническую SemVer-версию из
`anki_study_report/version.py`, пользовательский changelog из `CHANGELOG.md`
и ручной workflow `.github/workflows/release.yml`. Merge сам по себе ничего не
публикует. Production release начинается только явным `workflow_dispatch` с
`master` на точном текущем commit.

## Подготовка версии

Политика версий:

- `MAJOR` — несовместимое изменение пользовательского или интеграционного контракта;
- `MINOR` — новая обратно совместимая пользовательская возможность или законченный workflow;
- `PATCH` — исправление, security/performance/package/localization polish без нового самостоятельного workflow;
- prerelease использует обычный SemVer, например `1.1.0-rc.1`.

Подготовить и проверить версию:

```powershell
node scripts/run_python.mjs scripts/prepare_release.py --version 1.0.0 --dry-run
node scripts/run_python.mjs scripts/prepare_release.py --version 1.0.0
node scripts/run_python.mjs scripts/prepare_release.py --version 1.0.0 --check
node scripts/run_python.mjs scripts/validate_release.py --version 1.0.0 --channel stable
```

Preparation обновляет version source, намеренный `manifest.json.mod` и
версионированный раздел changelog, сохраняя свежий `[Unreleased]`. Release PR
должен включать эти изменения. PR-запуск `Gated Release Delivery` выполняет
валидацию, полный non-Docker pipeline и строит внутренний артефакт, но не
получает production secrets, write permissions и не публикует ничего.

## Production flow

После merge и зелёного PR CI maintainer запускает:

```powershell
gh workflow run release.yml --ref master -f version=1.0.0 -f channel=stable
```

Workflow выполняет цепочку:

```text
validate → build exact .ankiaddon → standard/full real-Anki E2E
→ provenance attestation + verified draft GitHub Release
→ approved AnkiWeb Environment + one Save on existing Branch 1
→ public byte/hash verification → finalize GitHub Release
```

Между job передаётся один `anki_study_report.ankiaddon`; его SHA-256 проверяется
после каждого скачивания и совпадает с пакетом в E2E evidence, GitHub Release и
публичным AnkiWeb download. Stable release обновляет существующий add-on
`373100400`, только `Branch 1`, с min/max `26.05.0`. Кнопка `Add New Branch` не
автоматизируется. Prerelease пропускает AnkiWeb и публикуется в GitHub как
prerelease, не как latest.

## GitHub Environment

Одноразовая настройка:

1. Создать Environment `ankiweb-production`.
2. Ограничить deployment веткой `master` и добавить required reviewer.
3. Создать environment secrets `ANKIWEB_EMAIL` и `ANKIWEB_PASSWORD`.

Значения вводятся через stdin и не должны попадать в shell history или аргументы:

```powershell
gh secret set --env ankiweb-production ANKIWEB_EMAIL
gh secret set --env ankiweb-production ANKIWEB_PASSWORD
gh secret list --env ankiweb-production
```

Только job `ankiweb-publish` с этим Environment читает credentials. Publisher
использует временный Playwright context и не сохраняет cookies, storage state,
trace, screenshots или HTML авторизованной страницы.

## Безопасный dry-run

`scripts/publish_ankiweb.mjs --dry-run` входит в live owner form, проверяет
идентичность страницы, единственность `Branch 1`, поля и кнопку Save, но не
выбирает файл, не меняет поля и не нажимает Save. Отчёт содержит только
санитизированные boolean/hash evidence.

## Восстановление

- До финализации GitHub Release остаётся draft; исправьте причину и повторите
  тот же dispatch. Draft assets могут быть обновлены только до публикации.
- Challenge/2FA, изменение DOM, лишняя branch или hash mismatch останавливают
  workflow до Save либо до финализации GitHub Release.
- После успешного AnkiWeb Save, но до финализации, повторный запуск идемпотентно
  сверяет metadata, description и публичный artifact hash и не делает второй Save.
- Опубликованный SemVer release и его assets не перезаписываются. Любое изменение
  bytes требует новой версии.
- Никогда не объявляйте local PASS заменой упавшему cloud release run.

Текущий этап добавляет только delivery infrastructure. Search UI, route и
navigation entry не входят в release automation.
