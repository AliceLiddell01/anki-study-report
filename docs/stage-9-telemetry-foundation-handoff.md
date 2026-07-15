# Stage 9 telemetry foundation handoff

Снимок: 2026-07-15. Этот документ — канонический closure/handoff для Stage 9.
Он разделяет статистику двух репозиториев и не выдаёт сумму строк или файлов за
одну метрику без воспроизводимого метода.

## Статус

- Stage 9.0: COMPLETE.
- Stage 9.1: COMPLETE.
- Stage 9.2 code foundation: COMPLETE.
- Cloudflare deployment/operations acceptance: COMPLETE для EU D1,
  staging/production deploy, synthetic deletion и временного D1 export/import
  recovery drill.
- Add-on endpoint и RU/EN production notice: COMPLETE в текущем checkout.

R2 не активирован и не входит в active contract. 30-дневные независимые
бэкапы перенесены в future infrastructure work. Новый `.ankiaddon` release
этим этапом не создаётся.

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

### Add-on PR #21

`AliceLiddell01/anki-study-report#21` — 20 changed files, 424 additions,
52 deletions.

- base SHA: `9cdce8f0475ef0fe81016c35e9d026c89249b832`;
- tested head SHA: `e964249d7ec870103f5fff0c8835757943cf0e1f`;
- final master SHA after rebase merge: `7e02badd94872c47d1e72d2b3ffe9bca530494f0`;
- method: GitHub REST PR metadata fields `changed_files`, `additions`,
  `deletions` and base/head/merge SHA;
- scope: consent/What’s New polish, localized timestamps, screenshot contract
  and reproducible telemetry handoff.

### Add-on PR #23

`AliceLiddell01/anki-study-report#23` — 17 changed files, 276 additions,
52 deletions.

- base SHA: `7e02badd94872c47d1e72d2b3ffe9bca530494f0`;
- tested head SHA: `811baaf0f9e00f055d2d7018690cce57f98a4194`;
- final master SHA after rebase merge: `694d16c0ff0dc6a02d177e97ba147de000fbd575`;
- method: GitHub REST PR metadata fields `changed_files`, `additions`,
  `deletions` and base/head/merge SHA;
- scope: accepted production endpoint, fresh production re-consent, full RU/EN
  notice, lazy notice chunk, tests and cloud-acceptance documentation.

Эти PR statistics остаются отдельными compare ranges и не прибавляются к
foundation PR без заранее определённого агрегата.

## Уже принято до cloud deployment

- add-on Fast CI и CodeQL;
- real-Anki `standard/settings` и `standard/full`;
- telemetry repository CI и contract parity;
- accepted `standard/full` run `29412736595`: 44/44 screenshots,
  restart queue 482/482, offline deletion PASS, confirmed deletion PASS,
  credentials destroyed PASS.

Этот run не повторяется для report-only или telemetry-repository-only правок.

## Cloud acceptance evidence

Staging:

- Worker: `https://anki-study-report-telemetry-staging.anki-study-report.workers.dev`;
- D1: `anki-study-report-telemetry-staging`,
  `a3e06e45-26f0-4bf9-a0f2-dfc762a292dc`, jurisdiction `eu`;
- final notice-version deployment: SHA
  `79627fe0f861447ee5a3af7aa0a6026285737201`, run `29427911018`, PASS;
- recovery drill: run `29425019956`, export SHA-256
  `fff84bf0b91be46d6e5bfb4d4e10aa8130cae9d0c7a7819aadae9a6669ff6ffb`,
  5,527 bytes, source/restored row counts matched, temporary D1 destroyed,
  SQL artifact absent.

Production:

- Worker: `https://anki-study-report-telemetry.anki-study-report.workers.dev`;
- D1: `anki-study-report-telemetry-prod`,
  `00dcea29-9a7e-48b4-a845-d585e8d6f0f2`, jurisdiction `eu`;
- final notice-version deployment: SHA
  `79627fe0f861447ee5a3af7aa0a6026285737201`, run `29427988405`, PASS;
- recovery drill: run `29426752402`, export SHA-256
  `ec462a229dcc63e76c07f2af0b19b24182a217eba28ae2f627d78c4d0b09c153`,
  4,805 bytes, source/restored row counts matched, temporary D1 destroyed,
  SQL artifact absent.

Обе среды доказали provider-managed D1 Time Travel за 7 дней. Synthetic smoke
проверил health/schema, enrollment, valid/duplicate/invalid/unauthorized paths,
confirmed deletion, invalidated token и нулевой residue. Первый staging run
`29427549104` честно завершился FAIL из-за edge propagation старой notice
version; после добавления exact-schema wait тот же acceptance прошёл.

GitHub Environments `cloudflare-staging` и `cloudflare-production` содержат
только names `CLOUDFLARE_ACCOUNT_ID` и `CLOUDFLARE_API_TOKEN`; Worker secrets:
`TOKEN_HASH_SECRET`, `ABUSE_HMAC_SECRET`, `ADMIN_MAINTENANCE_TOKEN`. Secret
values, Authorization headers, IP/User-Agent и SQL bytes в evidence не входят.
