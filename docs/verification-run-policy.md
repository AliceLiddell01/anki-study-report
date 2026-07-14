# Verification run policy

Статус: обязательная политика с 2026-07-13.

Полный real-Anki E2E — финальный integration gate, а не development loop.
Последовательность product/runtime change:

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
Targeted gate выбирается по product scope. Для Stage 7 это `standard/stats`,
workers `3`, resource telemetry `false`. Final `standard/full` выполняется,
когда его требует actual diff по planner/matrix, а не автоматически после
каждого targeted gate. `strict-apkg` нужен только Cards/APKG change; `perf100`
только явной performance-задаче.

Для Search v1/Safe Actions targeted gate — один `standard/global` на exact
ready-head SHA после Fast CI: scope содержит route/navigation, query/inspect,
Browser bridge, reversible mutations и fixture restore. Изменения shared
dashboard server, mutation runtime и E2E fixture эскалируют final gate до
`standard/full`; strict APKG и Perf100 не нужны, если Cards rendering/APKG/
performance contracts не менялись.

Готовый PR-head SHA должен иметь Fast CI PASS и требуемый real-Anki gate именно
на этом SHA. Разрешённый repository rebase merge создаёт новые commit SHA даже
при неизменном patch/tree. После merge сравниваются production tree/patch с
проверенным PR-head: повтор real-Anki gate нужен только если rebase/conflict
resolution изменил production tree. Fast CI на итоговом `master` обязателен в
любом случае; новый SHA сам по себе не является причиной повторять успешный E2E.

После failure сначала изучаются artifact/log/root cause. Разрешён максимум один
повтор соответствующего targeted/full после исправления. Второй одинаковый
failure останавливает blind reruns. Успешный exact-SHA run не повторяется.

Запрещены warm-cache repeat, workers benchmark, resource telemetry benchmark,
локальный full Docker после cloud PASS, full после каждого исправления и full
после rebase-equivalent merge с неизменным production tree. Docs-only после gate требует только
docs/Fast CI; unit fixture без runtime impact — Fast CI; local FSRS UI/API —
`stats`; shared shell/server/package/E2E infrastructure — `full`.

## Advisory planner

`scripts/plan_verification.py` принимает `--base`, `--head` или repeatable
`--path`, пишет `verification-plan.json`/`.md` и GitHub Step Summary. Classifier
path/rule based, deterministic, tested и только advisory: он не запускает E2E,
не хранит status и не может понизить shared runtime/E2E/package change. Человек
или агент может повысить gate.

Stage 7 expected plan: Fast CI required; targeted `stats` once; final `full`
once; telemetry off; no warm-cache/local duplicate. Поскольку actual Stage 7
также меняет dashboard server и E2E fixture/contract, planner корректно
эскалирует final integration requirement, но не создаёт лишний ранний full run.

## Release policy

Release infrastructure, package version source, changelog, release workflow и
AnkiWeb adapter всегда классифицируются как `full`. Production workflow
переиспользует `ci-e2e.yml` и устанавливает exact final archive через
`ANKI_E2E_PREBUILT_ADDON_PATH`; E2E evidence обязано иметь тот же SHA-256.
PR запускает только validation/build. Manual dispatch с `master` — отдельное
явное решение владельца и не является автоматическим продолжением merge.
