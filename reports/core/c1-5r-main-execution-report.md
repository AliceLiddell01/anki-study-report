# C1.5R — основной отчёт о выполнении и репозиторном closeout

**Дата:** 2026-07-21
**Проект:** Anki Study Report
**Контур:** Core / C1.5R — Cards and Inspection Profiles UX remediation
**Итог:** C1.5R.0–R.7 Complete
**Owner product acceptance:** Accepted
**Следующий этап:** C1.6 — Next, not started
**PR:** #55
**Итоговый implementation candidate:** `df633563490f80346617871ec5640adf99154956`
**Closeout и merged `core`:** `813b0824d324adbe50b2bca0ca0fab294efb0ea0`

## 1. Краткий итог

C1.5R успешно завершён как полный corrective-контур для ранее отклонённого
пользовательского результата C1.5.

В рамках C1.5R были последовательно закрыты:

1. восстановление корректного baseline и статусов;
2. единая карточная display identity;
3. декларативный compact formatter runtime;
4. корректная front/back preview semantics;
5. независимые bounded candidate sources;
6. новый Cards attention inbox;
7. guided Inspection Profiles UX;
8. интегрированная проверка всего контура и отдельное owner acceptance.

Финальный кандидат прошёл focused regression, canonical non-Docker suite,
package build/validation и clean full real-Anki E2E с рестартом Anki. В ходе
acceptance были найдены и исправлены два рассогласования только в E2E harness.
Production behavior, публичные payload-контракты и security boundaries не
ослаблялись.

PR #55 закрыт как merged в `core`. В `master` ничего не переносилось. Release,
deployment, публикация `.ankiaddon`, AnkiWeb и C1.6 не выполнялись.

## 2. Исходная ситуация

До возобновления closeout существовал один сохранённый кандидат:

- branch: `c1-5r-7-integrated-acceptance-v2`;
- paused candidate: `dce5b3c4a4f16f213ca565e46f57ef4465415f20`;
- PR: #55;
- ранее зафиксированный `core`: `cc35dc626687948ba25c1e248faf39763fbfe523`;
- лучший retained GitHub Actions run: `29828336280`.

В retained run успешно прошли:

- canonical non-Docker;
- package/provenance;
- artifact round-trip;
- candidate hygiene;
- immutable GHCR;
- targeted Cards real-Anki E2E.

Full real-Anki E2E завершился ошибкой в Inspection Profiles. Артефакты показали,
что targeted `cards` scope успешно подготавливал профиль, а `full` scope оставлял
его ненастроенным. Это указывало не на product failure, а на рассогласование
между E2E scope setup и scope consumption.

## 3. Фактическая последовательность работ

### 3.1. Аудит сохранённого кандидата

Были повторно проверены:

- состояние PR #55;
- точные SHA `core` и candidate;
- состав diff;
- шаги run `29828336280`;
- package, provenance, targeted и full artifacts;
- `smoke-api.py`, `smoke-browser.mjs`, restart scripts;
- текущие tests и roadmap/handoff.

Подтвердилось, что кандидат содержал в основном удаление временной R7
инфраструктуры, а реальный blocker находился в E2E harness.

### 3.2. Синхронизация с актуальным `core`

За время паузы `core` сдвинулся до:

`4e71de18d7a370a1ebc182290894e0b5c4975502`

Изменения были документационными и относились к AI work modes. Они были
включены в closeout candidate через commit:

`cda2bae79fdbf9c553a885839eb7cc2c85abca73`
— `chore: synchronize the R7 closeout with core`

Единственный конфликт касался временного R7 workflow, который и должен был быть
удалён итоговым cleanup.

### 3.3. Первая правка E2E harness

В `docker/anki-e2e/smoke-api.py` Inspection Profiles contract запускался только
при точном `ANKI_E2E_SCOPE == "cards"`, хотя browser/full сценарий использовал
объединённую семантику `cards/full`.

Исправление:

`0e1f69f7dd80002973701d5256e64ba7069d89a2`
— `test: align Inspection Profiles fixtures across E2E scopes`

Изменения:

- добавлен helper `should_run_inspection_profiles(scope)`;
- Inspection Profiles API smoke включён для `cards` и `full`;
- добавлен parametrized regression test;
- `global` и `notifications` scopes остались исключёнными.

### 3.4. Canonical non-Docker verification

После приведения окружения к поддерживаемой матрице прошли:

- TypeScript typecheck;
- frontend tests: 318;
- Python tests: 796;
- production bundle;
- package build;
- package validation;
- archive validation: 74 entries;
- repository hygiene.

### 3.5. Первый полноценный full real-Anki E2E

Первый фактически запущенный full E2E прошёл:

- clean Anki 26.05 startup;
- first API smoke;
- browser smoke;
- FSRS visual contract;
- первый lifecycle segment.

После restart повторный API smoke ожидал состояние `needs_review`, но fixture
осталась `confirmed`.

Анализ показал второе рассогласование scope:

- `smoke-api.py` теперь правильно проверял `full`;
- `restart-anki.sh` выполнял `mutate-inspection-profile-fixture.py` только при
  точном scope `cards`;
- full-run выполнял restart, но пропускал необходимую deterministic mutation.

### 3.6. Вторая правка E2E harness

Исправление:

`df633563490f80346617871ec5640adf99154956`
— `test: run Inspection Profiles restart mutation in full scope`

Изменения:

- restart mutation выполняется для `full|cards`;
- добавлен regression test;
- затронуты только:
  - `docker/anki-e2e/restart-anki.sh`;
  - `tests/test_docker_smoke_helpers.py`.

После правки focused helper suite прошёл 30 тестов.

### 3.7. Финальный clean full real-Anki E2E

Финальный прогон успешно подтвердил:

| Gate | Результат |
| --- | --- |
| Anki version | 26.05 |
| initial API smoke | PASS |
| browser smoke | PASS |
| FSRS visual contract | PASS |
| route/theme/profile matrix | PASS — 80 комбинаций |
| restart lifecycle | PASS |
| restart API smoke | PASS |
| structured artifact manifest | PASS |
| page screenshots | 50 |
| navigation screenshots | 2 |
| synthetic Cards screenshots | 4 |
| APKG Cards screenshots | 1 |
| repository worktree after run | clean |

Итоговый implementation candidate был запушен в PR branch.

### 3.8. Документационный closeout

Commit:

`813b0824d324adbe50b2bca0ca0fab294efb0ea0`
— `docs: close C1.5R integrated acceptance`

Обновлены:

- `README.md`;
- `docs/ai-handoff.md`;
- `roadmap/README.md`;
- `roadmap/core/README.md`;
- `reports/README.md`;
- `reports/core/c1-5r-cards-profiles-ux-remediation.md`;
- добавлен `reports/core/c1-5r-7-integrated-acceptance-closeout.md`.

Статусы были синхронизированы:

- C1.5R.0–R.7 — Complete;
- owner product acceptance — Accepted;
- C1.6 — Next, not started;
- C1.6B — Conditional;
- Core C1 — In progress.

### 3.9. Интеграция в `core`

PR #55 был:

- переименован в `C1.5R.7 integrated acceptance closeout`;
- обновлён полным verification summary;
- переведён из draft;
- интегрирован в `core`.

Rebase merge через GitHub был отклонён, поскольку история candidate содержала
синхронизационный merge commit. Так как `core` являлся прямым предком closeout
head, `core` был безопасно fast-forward обновлён на exact SHA `813b082...`
без force.

После операции GitHub отразил PR #55 как merged, а `core` и closeout head стали
идентичны.

## 4. Реестр проблем и решений

| Проблема | Категория | Корневая причина | Решение | Итог |
| --- | --- | --- | --- | --- |
| Expected `core` SHA изменился | Repository drift | В `core` появились актуальные AI work-mode docs | Повторный аудит и синхронизация exact SHA | PASS |
| Git не создавал merge commit | Local Git config | В WSL checkout не была задана commit identity | Repository-local `user.name` и `user.email` | PASS |
| `pytest` отсутствовал | Local environment | В Arch WSL не было dev Python environment | Отдельный venv и `requirements-dev.txt` | PASS |
| PowerShell запускал Windows `git.exe` | WSL PATH | Windows paths добавлялись раньше Linux tooling | Sanitized PATH для verification process | PASS |
| Не найден `tsc` | Frontend environment | `web-dashboard/node_modules` отсутствовал | `pnpm install --frozen-lockfile` | PASS |
| Один timestamp test падал на Python 3.14 | Version mismatch | Python 3.14 принял ISO `24:00`, проект закрепляет Python 3.11 | Verification на repository-pinned Python 3.11 | PASS |
| `__pycache__` ломал hygiene gate | Generated output | Targeted pytest создавал bytecode/cache | `PYTHONDONTWRITEBYTECODE=1`, cacheprovider disabled, cleanup | PASS |
| Full API smoke не создавал Inspection Profiles | E2E harness | `smoke-api.py` ограничивал setup scope только `cards` | Scope helper для `cards/full` + regression | PASS |
| Restart smoke не получал `needs_review` | E2E harness | Fixture mutation выполнялась только для `cards` | Restart mutation для `full|cards` + regression | PASS |
| Предварительная гипотеза искала gate в browser smoke | Диагностика | Предположение оказалось слишком узким | Скрипт остановился до изменений; выполнен поиск по всему harness | Без ущерба |
| `docker compose` отсутствовал | Docker tooling | В Arch был Docker CLI без Compose plugin | Установлен официальный `docker-compose` package | PASS |
| Build warning о Buildx | Docker tooling | Buildx plugin отсутствовал | Установлен `docker-buildx` | PASS |
| Docker build не имел сети через bridge | WSL/Docker network | Docker bridge/NAT не мог стабильно подключиться к apt repositories | BuildKit build с `--network host`; runtime E2E оставлен canonical | PASS |
| Первый docs script не видел новый report | Script defect | `git diff --name-only` не включает untracked paths | Отдельная проверка tracked/untracked union | PASS |
| Trailing whitespace в Markdown | Documentation hygiene | Два пробела для Markdown line break | Удаление trailing spaces и `git diff --check` | PASS |
| Документы уже были staged | Git index state | Предыдущий скрипт частично подготовил index | Точная union-проверка staged/unstaged/untracked и refresh index | PASS |
| GitHub rebase merge отказал | Merge method | Candidate содержал merge commit | Exact non-force fast-forward `core` | PASS |

## 5. Что изменено в репозитории

### 5.1. Production code

Production behavior и публичные API/payload schemas в R7 closeout не менялись.

Не изменялись:

- loopback-only server boundary;
- token validation;
- sanitizer;
- media validation;
- action allowlists;
- collection access boundary;
- Inspection Profile v1 public contract;
- Search v2;
- Triage v4.

### 5.2. E2E harness

Изменены только bounded scope contracts:

- `docker/anki-e2e/smoke-api.py`;
- `docker/anki-e2e/restart-anki.sh`;
- `tests/test_docker_smoke_helpers.py`.

### 5.3. Временная инфраструктура

Из итогового diff удалены временные R7-файлы:

- `.github/workflows/r7-css-sentinel-control-v2.yml`;
- `.github/workflows/r7-docs-control.yml`;
- `.github/workflows/r7-integrated-acceptance-v4.yml`;
- `.github/workflows/r7-profile-smoke-schema-control.yml`;
- `scripts/r7_acceptance_scope.ps1`;
- `scripts/r7_prepare_package.py`.

Это убирает служебную acceptance-инфраструктуру из постоянного репозитория.

## 6. Итоговая Git-цепочка

| SHA | Назначение |
| --- | --- |
| `dce5b3c4a4f16f213ca565e46f57ef4465415f20` | paused best-known candidate |
| `4e71de18d7a370a1ebc182290894e0b5c4975502` | актуальный `core`, включённый в closeout |
| `cda2bae79fdbf9c553a885839eb7cc2c85abca73` | синхронизация candidate с `core` |
| `0e1f69f7dd80002973701d5256e64ba7069d89a2` | API smoke scope fix |
| `df633563490f80346617871ec5640adf99154956` | restart scope fix и accepted implementation candidate |
| `813b0824d324adbe50b2bca0ca0fab294efb0ea0` | docs closeout и merged `core` |

## 7. Сохранённые evidence

Исторический cloud-run:

- run: `29828336280`;
- package artifact: `8494243010`;
- provenance artifact: `8494242618`;
- targeted Cards artifact: `8494293447`;
- full artifact: `8494328398`.

Он остаётся полезным диагностическим evidence, но не является финальным
acceptance proof, поскольку full scope завершился ошибкой.

Финальный acceptance proof:

- implementation candidate: `df633563490f80346617871ec5640adf99154956`;
- local canonical non-Docker: PASS;
- local clean full real-Anki E2E: PASS;
- owner product decision: Accepted;
- merged core closeout: `813b0824d324adbe50b2bca0ca0fab294efb0ea0`.

## 8. Оценка успешности

### Подтверждено успешно

- C1.5R.0–R.7 завершены;
- owner product acceptance получен;
- весь required verification contour зелёный;
- package проверен;
- full lifecycle с рестартом Anki проверен;
- production contracts не ослаблены;
- temporary R7 workflows/helpers удалены из `core`;
- документация синхронизирована;
- PR #55 merged;
- `core` содержит exact closeout tree;
- C1.6 не начат преждевременно.

### Не выполнялось намеренно

- merge в `master`;
- release/tag;
- deployment;
- AnkiWeb publication;
- C1.6 implementation;
- C1.6B activation;
- повторный E2E после docs-only commit.

### Отдельный operational cleanup

Был подготовлен exact SHA-checked скрипт удаления disposable remote
`c1-5r-7-*` refs. В доступных логах этого отчёта нет подтверждённого
`R7 CLEANUP RESULT`, поэтому удаление remote branches здесь не объявляется
выполненным. Это не меняет статус C1.5R, но остаётся репозиторной hygiene-проверкой:

```bash
git ls-remote --heads origin 'refs/heads/c1-5r-7-*'
```

Ожидаемый итог после cleanup — пустой вывод.

## 9. Выводы по процессу

Основная техническая часть была успешно завершена, но путь оказался заметно
длиннее необходимого из-за смеси:

- старой временной GitHub Actions инфраструктуры;
- неполного WSL tooling;
- различий Windows/Linux PATH;
- неподдерживаемой Python version;
- Docker bridge networking;
- нескольких защитных ошибок в closeout scripts.

Положительный результат состоит в том, что защитные проверки почти всегда
останавливались до опасных действий. Ни одна из промежуточных ошибок не привела к:

- force-push;
- потере unrelated history;
- изменению `master`;
- ослаблению production contracts;
- коммиту generated artifacts;
- ложному объявлению failed harness как product failure.

Для следующих этапов следует применять закреплённые repository work-mode rules:

1. один stage — одна рабочая ветка и один основной PR;
2. сначала environment preflight;
3. Python строго по `.python-version`;
4. native Linux tooling в WSL без Windows command shadowing;
5. Docker Compose и Buildx проверять до E2E;
6. full real-Anki E2E использовать как integration gate, а не debugger;
7. не создавать временные controller/trigger workflows для routine Git operations;
8. после одного подтверждённого PASS не повторять same-SHA gate без новой причины.

## 10. Текущая точка продолжения

```text
C1.5R.0–R.7 — Complete
Owner product acceptance — Accepted
C1.6 — Next, not started
C1.6B — Conditional
Core C1 — In progress
```

Следующая отдельная задача — C1.6 Canonical single-card resolution loop.
Она должна начинаться новым bounded scope и не должна повторно открывать C1.5R
без подтверждённой production regression, security risk, data-loss risk или
явного owner rejection.

## 11. Связанные документы

- [`c1-5r-cards-profiles-ux-remediation.md`](c1-5r-cards-profiles-ux-remediation.md)
- [`c1-5r-7-integrated-acceptance-closeout.md`](c1-5r-7-integrated-acceptance-closeout.md)
- [`../../docs/ai-handoff.md`](../../docs/ai-handoff.md)
- [`../../roadmap/core/README.md`](../../roadmap/core/README.md)
- [`../../docs/test-matrix.md`](../../docs/test-matrix.md)
- [`../../docs/verification-run-policy.md`](../../docs/verification-run-policy.md)
