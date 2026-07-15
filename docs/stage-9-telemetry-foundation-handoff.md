# Stage 9 telemetry foundation handoff

Снимок: 2026-07-15. Этот документ — канонический closure/handoff для Stage 9.
Он разделяет статистику двух репозиториев и не выдаёт сумму строк или файлов за
одну метрику без воспроизводимого метода.

## Статус

- Stage 9.0: COMPLETE.
- Stage 9.1: COMPLETE.
- Stage 9.2 code foundation: COMPLETE.
- Cloudflare deployment/operations acceptance: PENDING до появления прямых
  доказательств EU provisioning, staging/production deploy, deletion и
  backup/restore.

Production endpoint в add-on остаётся выключенным до завершения cloud
acceptance и финализации RU/EN уведомления о конфиденциальности. Новый
`.ankiaddon` release этим этапом не создаётся.

## Воспроизводимая статистика merged foundation PR

### Add-on PR #20

`AliceLiddell01/anki-study-report#20` — 81 changed files, 6 469 additions,
50 deletions.

- base ref: `master`;
- base SHA: `abf3b9a943e18c59c801088de7c757b154fe272e`;
- tested head SHA: `bed35056e8f1fa78f9a32863d8e77084af957ddd`;
- merge commit: `9cdce8f0475ef0fe81016c35e9d026c89249b832`;
- method: GitHub REST `GET /repos/AliceLiddell01/anki-study-report/pulls/20`,
  fields `changed_files`, `additions`, `deletions`, cross-checked with
  `gh pr view 20`;
- scope: только diff этого PR внутри add-on репозитория.

### Telemetry service PR #1

`AliceLiddell01/anki-study-report-telemetry#1` — 52 changed files,
4 427 additions, 0 deletions.

- base ref: `master`;
- base SHA: `3c8d652d95c7f9b1703edbce3e1a51866c257c48`;
- head SHA: `0ef27811e5efe78d9a8016691b5fe921c1fd3044`;
- merge commit: `4739a1fe29a9a6f7840e0d2ad8c48bc4f04b54bf`;
- method: GitHub REST
  `GET /repos/AliceLiddell01/anki-study-report-telemetry/pulls/1`, fields
  `changed_files`, `additions`, `deletions`, cross-checked with `gh pr view 1`;
- scope: только diff этого PR внутри private telemetry репозитория.

## Почему нет combined total

Числа `128 changed files`, `8 214 additions`, `388 deletions` удалены из
closure-контракта: они не воспроизводятся из merged PR. Простая сумма PR
метрик тоже не публикуется как «объём Stage 9»: пути принадлежат разным
репозиториям, одинаковые относительные имена могут дублироваться, а GitHub
считает changed files отдельно для каждого diff. Combined unique-path metric
не рассчитывалась.

## Стабилизационные PR

Корректирующие PR этого прохода будут перечислены отдельно после merge с их
собственными base/head SHA и GitHub PR statistics. Их значения нельзя
прибавлять к foundation PR без явного определения агрегата.

## Уже принято до cloud deployment

- add-on Fast CI и CodeQL;
- real-Anki `standard/settings` и `standard/full`;
- telemetry repository CI и contract parity;
- accepted `standard/full` run `29412736595`: 44/44 screenshots,
  restart queue 482/482, offline deletion PASS, confirmed deletion PASS,
  credentials destroyed PASS.

Этот run не повторяется для report-only или telemetry-repository-only правок.

## Cloud acceptance evidence

До завершения provisioning здесь намеренно нет выдуманных resource ID, URL,
workflow run ID или утверждений о jurisdiction. После успешной приёмки раздел
должен содержать только санитизированные имена/ID, доказанную EU jurisdiction,
точный Worker URL, repository SHA, deployment/backup run ID, migration names,
synthetic result codes, row counts и checksums — без secret values, токенов,
Authorization headers, IP/User-Agent или database export bytes.
