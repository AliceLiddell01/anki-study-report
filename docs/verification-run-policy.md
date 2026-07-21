# Политика verification runs

**Статус:** обязательная политика с 2026-07-13

Full real-Anki E2E — финальный integration gate, а не development loop.

## Общая последовательность

Для product/runtime change:

```text
локальные targeted tests
→ commit + push
→ Fast CI exact SHA PASS
→ один targeted real-Anki scope
→ final standard/full только при эскалации planner/matrix
→ rebase merge проверенного patch/tree
→ Fast CI на итоговом master
```

Fast CI обязателен на `codex/**`, PR и `master`. До его PASS E2E не запускается.

Targeted gate выбирается по product scope.

Final `standard/full` выполняется только тогда, когда его требует actual diff по planner/matrix, а не автоматически после каждого targeted gate.

`strict-apkg` нужен только при изменении Cards/APKG contract. `perf100` — только для явной performance task.

## Search и Safe Actions

Targeted gate:

```text
standard/global
```

Он выполняется один раз на exact ready-head SHA после Fast CI и покрывает:

- route/navigation;
- query/inspect;
- Browser bridge;
- reversible mutations;
- fixture restore.

Изменения shared dashboard server, mutation runtime или E2E fixture эскалируют final gate до `standard/full`.

`strict-apkg` и `perf100` не требуются, если Cards rendering, APKG и performance contracts не менялись.

## Inspection Profiles и Triage

Targeted gate:

```text
standard/cards
verify_restart = true
```

Он использует exact package Fast CI и подтверждает:

- live structures Japanese и Programming;
- save/confirm через supported API;
- Japanese-only missing-audio reason;
- independent learning reason;
- profile-local revision после restart;
- fail-closed `needs_review` после изменения fixture template reference.

Это contract/runtime proof, а не screenshot acceptance.

Для C1.3 `full`, `strict-apkg` и `perf100` не требуются только из-за самого этапа.

Для C1.4 сохраняется тот же exact-package `standard/cards` с restart. Browser smoke дополнительно проверяет:

- route `#/settings/inspection-profiles`;
- lifecycle confirmed/needs-review;
- local dirty suggestion draft;
- validate-v2 bounded preview;
- protection от navigation с unsaved changes;
- отсутствие horizontal overflow;
- screenshots list/editor/dirty/preview.

Browser smoke не сохраняет и не подтверждает draft автоматически.

## Stage 9.3–9.5 — Notifications

Порядок:

```text
focused tests
→ -SkipDocker
→ exact-SHA Fast CI
→ один standard/notifications с restart
→ один final standard/full
```

Targeted повторяется только после relevant failure/change. Full run не повторяется без изменения contract.

Local Docker допускается только как явное owner exception и не заменяет Fast CI, CodeQL или cloud proof.

## Требование exact SHA

Ready PR-head SHA обязан иметь Fast CI PASS и требуемый real-Anki gate именно на этом SHA.

Разрешённый repository rebase merge создаёт новый commit SHA даже при неизменном patch/tree.

После merge сравниваются production tree/patch и проверенный PR head.

Повтор real-Anki gate требуется только тогда, когда rebase или conflict resolution изменили production tree.

Fast CI на итоговом `master` обязателен всегда. Новый SHA сам по себе не является причиной повторять успешный E2E.

## Stop-loss при failure

После failure сначала изучаются artifacts, logs и root cause.

Разрешён максимум один повтор соответствующего targeted/full gate после конкретного исправления.

Второй одинаковый failure останавливает blind reruns.

Successful exact-SHA run не повторяется.

Запрещены:

- warm-cache repeats;
- workers benchmark без отдельной задачи;
- resource telemetry benchmark без отдельной задачи;
- local full Docker после cloud PASS;
- full после каждого исправления;
- full после rebase-equivalent merge с неизменным production tree.

Docs-only change после gate требует только docs checks/Fast CI. Unit fixture без runtime impact требует Fast CI. Local FSRS UI/API требует targeted `stats`. Shared shell/server/package/E2E infrastructure требует `full`.

## Advisory verification planner

`scripts/plan_verification.py` принимает:

```text
--base
--head
--path — repeatable
```

Он записывает:

```text
verification-plan.json
verification-plan.md
GitHub Step Summary
```

Classifier:

- path/rule based;
- deterministic;
- покрыт tests;
- advisory only.

Planner не запускает E2E, не хранит status и не может понизить shared runtime/E2E/package change. Человек или agent может повысить gate.

Expected plan Stage 7:

```text
Fast CI required
one targeted stats
one final full
telemetry off
no warm-cache/local duplicate
```

Поскольку actual Stage 7 меняет dashboard server и E2E fixture/contract, planner корректно эскалирует final integration requirement, но не создаёт лишний ранний full run.

## Fast CI instrumentation baseline

Изменение только Fast CI timing contract сначала проходит:

- focused helper/workflow/summary/run_full_check tests;
- canonical local `run_full_check.ps1 -SkipDocker`.

После local PASS для Stage 5A разрешён ровно один `workflow_dispatch` на exact instrumentation branch.

Этот run — observational baseline. Не выполняются:

- before/after pair;
- warm-cache repeat;
- PR-trigger surrogate;
- Docker E2E;
- release.

Internal monotonic phase timings анализируются вместе с timestamps Jobs API action/step. Artifact upload и post-job cache work не приписываются internal phase timers.

После PR #37 canonical contour содержит ровно один TypeScript typecheck. Нельзя возвращать удалённый `frontend-typecheck-build` или второй `pnpm run typecheck`.

Runner, checkout и caches сохраняются без изменений.

Если authorized baseline падает, automatic rerun запрещён. Нужно скачать diagnostics, классифицировать failure как project/instrumentation/infrastructure и вернуть `FAIL` или `PARTIAL`.

Fix и новый run требуют отдельного решения владельца.

## Fast package producer

Successful Fast CI run публикует diagnostics artifact отдельно от short-lived exact package artifact.

Diagnostics загружается через `always()` и не содержит `.ankiaddon`.

Package artifact появляется только после успешных:

- canonical checks;
- planner;
- summary;
- package validation;
- diagnostics upload.

Producer metadata обязано различать:

- tested `github.sha`;
- source head SHA;
- source base SHA.

`packageSha256` относится к bytes внутреннего `.ankiaddon`. GitHub artifact digest относится к transport artifact и не записывается внутрь immutable metadata.

Один manual Fast CI `workflow_dispatch` на exact feature branch допустим для проверки producer contract после local PASS.

Stage 2 не меняет E2E contour: Docker E2E продолжает build from source и не скачивает Fast package. Cross-run handoff требует отдельного решения и не добавляется как побочный эффект producer stage.

## Fast package consumer

Docker E2E может явно получить successful exact Fast package через `fast_ci_run_id`.

Consumer обязан:

- проверить source run и artifact list через read-only API;
- скачать diagnostics/package по artifact IDs;
- получить tested SHA из validated diagnostics;
- checkout exact tested commit;
- связать metadata source head с исходным E2E workflow SHA.

Invalid run ID, fork, ambiguity, expiry или identity/hash mismatch завершаются ошибкой без source-build fallback.

Для Stage 3 разрешена одна пара cloud observations на exact branch:

```text
один manual Fast CI
один standard/settings с telemetry/restart off и полученным run ID
```

Не выполняются source-build comparison, warm repeat, full, strict APKG или Perf100.

Stage 3 доказывает handoff semantics. Performance A/B относится к Stage 4. Release exact-artifact flow остаётся отдельным current-run gate.

## Release policy

Release infrastructure, package version source, changelog, release workflow и AnkiWeb adapter всегда классифицируются как `full`.

Production workflow переиспользует `ci-e2e.yml` и устанавливает exact final archive через:

```text
ANKI_E2E_PREBUILT_ADDON_PATH
```

E2E evidence обязано иметь тот же SHA-256.

PR запускает `Validate release contract`. Heavy build и production jobs сохраняют прежние check identities, но получают `skipped` через job-level conditions.

Manual dispatch из `master` выполняет exact build и полную release chain. Это отдельное явное owner decision и не является автоматическим продолжением merge.

## Product notices и privacy

Targeted gate:

```text
standard/settings
```

Он запускается после Fast CI на exact ready-head SHA.

Изменение App Shell, dashboard server, E2E smoke, package validation или canonical release input эскалирует final gate до `standard/full`.

Повторный local full не заменяет cloud proof.

Для Stage 9.0.1 порядок:

```text
focused tests
→ -SkipDocker
→ exact-SHA Fast CI
→ один standard/settings с exact package artifact
```

Planner может потребовать один final `standard/full` из-за shared dashboard server/E2E smoke.

Cloud telemetry deployment выполняется только после service CI:

```text
staging migration/deploy
→ sanitized synthetic lifecycle
→ manual production deploy
→ такой же lifecycle
```

Automated tests не обращаются к production.

Реальный profile требует отдельного явного checkpoint владельца и не считается accepted по synthetic proof.