# Public repository readiness

Дата аудита: 2026-07-11.

## Scope

Проверены `origin/master`, локальные `master` и
`codex/github-actions-ci-foundation`, remote branches, tag
`checkpoint/anki-e2e-card-preview` и вся reachable history. На момент аудита это
81 commit, одна remote branch и один tag. Репозиторий оставался private.

Проверены tracked tree и history blobs, типовые secret/credential markers,
локальные пути и персональные маркеры, binary/media inventory, существующие
GitHub Actions runs/artifacts, workflow permissions и будущий Fast CI artifact
contract.

## Tools and commands

Использовались `git fetch --all --tags --prune`, `git branch -a`,
`git tag --list`, `git rev-list --all`, `git rev-list --objects --all`,
`git grep`, `git cat-file`, `git count-objects`, `gh run list`, GitHub Actions
API metadata и read-only inspection APKG/ZIP containers. Внешний secret scanner
в окружении отсутствовал; случайный бинарник не устанавливался.

## Findings

### Critical / high

Не обнаружены. Сильные сигнатуры PAT/API keys/private keys в reachable history
не найдены. Полные значения потенциальных credentials в отчёт не выводились.

### Resolved — owner-authored and owner-authorized APKG fixture

`docker/anki-e2e/fixtures/asr-e2e-render-fixtures.apkg` содержит 10 реальных
учебных notes/cards, 4 note types и 13 bundled media entries. Владелец создал,
курировал и многократно переработал cards, fields, templates и deck structure с
AI assistance. Все media нарисованы, записаны либо сгенерированы владельцем под
его управлением; сторонних скачанных assets с неясными правами нет.

Владелец разрешил публичное размещение и распространение этой конкретной
fixture, включая notes/cards/templates/CSS/media, как части repository, tests,
Docker E2E и CI artifacts. Это узкое разрешение не задаёт лицензию для остального
репозитория.

Read-only inspection подтвердил целостность APKG и ожидаемые counts. Сигнатуры
credentials/private keys, абсолютные локальные пути, embedded attribution или
copyright notice, противоречащие owner attestation, не обнаружены. Fixture не
является экспортом чужой приватной collection и не содержит конфиденциальных
данных. Synthetic replacement и history rewrite не требуются и не выполнялись.

### Low / acceptable development metadata

В текущей Docker E2E документации был локальный абсолютный путь с username и
именем Anki profile. Текущая версия заменена placeholders; старые commits всё
ещё содержат эту безcredentialную development metadata. Тестовые unsafe-path
строки в sanitizer tests являются намеренными synthetic inputs.

Исторический `anki_study_report/anki_study_report.zip` содержит только старый
плоский набор исходного кода/config add-on; credentials, collection или media в
нём не обнаружены.

## GitHub Actions history

До gate найдено три успешных run на `master`: один workflow `Tests` и два
dependency-graph update run. У них отсутствуют сохранённые artifacts. Наличие
сильных secret signatures, локального username/profile или collection markers
в inspected logs и metadata не установлено.

## Future Fast CI artifact assessment

Workflow имеет только `permissions: contents: read`, checkout credentials не
сохраняются, repository secrets/OIDC/self-hosted runner не используются.
Artifact contract ограничен `ci-summary.md`, `ci-summary.json`,
`environment.txt`, `logs/fast-check.log` и non-release CI `.ankiaddon`.
Summary/environment формируются из repository/run/runtime metadata и не должны
включать secrets, PII, Anki profile или приватные файлы вне checkout. Package
содержит собираемый код проекта. Tracked APKG не входит в release package;
владелец отдельно разрешил её использование в repository tests и CI artifacts.

## License decision

Планируется public repository без `LICENSE`. Открытая лицензия не объявлена;
`LICENSE`, `COPYING`, `NOTICE`, SPDX identifier, license badge и декларация
открытой лицензии не добавлялись.

## Gate decision

`GO FOR PUBLIC`.

Owner review завершён, единственный fixture/media finding закрыт. Unresolved
critical/high findings и существенные owner-review items отсутствуют.
