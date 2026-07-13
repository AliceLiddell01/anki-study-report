# Verification run policy

Статус: обязательная политика с 2026-07-13.

Полный real-Anki E2E — финальный integration gate, а не development loop.
Последовательность product/runtime change:

```text
локальные targeted tests
→ commit + push
→ Fast CI exact SHA PASS
→ один targeted real-Anki scope
→ один final standard/full на готовом SHA
→ merge того же SHA без повторного E2E
```

Fast CI обязателен на `codex/**`, PR и `master`. До его PASS E2E не запускается.
Targeted gate выбирается по product scope. Для Stage 7 это `standard/stats`,
workers `3`, resource telemetry `false`. Final release integration gate — один
`standard/full`. `strict-apkg` нужен только Cards/APKG change; `perf100` только
явной performance-задаче.

После failure сначала изучаются artifact/log/root cause. Разрешён максимум один
повтор соответствующего targeted/full после исправления. Второй одинаковый
failure останавливает blind reruns. Успешный exact-SHA run не повторяется.

Запрещены warm-cache repeat, workers benchmark, resource telemetry benchmark,
локальный full Docker после cloud PASS, full после каждого исправления и full
после fast-forward merge того же SHA. Docs-only после gate требует только
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
