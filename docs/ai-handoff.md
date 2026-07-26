# Передача актуального контекста ИИ

**Снимок:** 2026-07-26

Этот файл — короткая точка входа. Он не заменяет production code, профильные contracts, roadmap или closeout reports.

## Порядок чтения

1. [`../README.md`](../README.md)
2. этот файл;
3. профильный roadmap;
4. профильный contract в `docs/`;
5. production code и tests;
6. свежий closeout только когда он нужен задаче.

При противоречиях:

```text
production code и tests
→ docs/
→ roadmap/
→ reports/artifacts
→ старые планы и сообщения
→ предположения
```

## Проект и границы

Anki Study Report — локальный add-on для Anki 26.05+ с Python runtime и React/TypeScript dashboard.

- dashboard работает только через loopback и защищён access token;
- frontend получает bounded API projections и не читает collection напрямую;
- preview использует sanitizer и Shadow DOM без JavaScript execution surface;
- учебные и профильные данные остаются локальными;
- payload/public behavior меняются синхронно между слоями, tests и docs.

Подробности: [architecture.md](architecture.md), [dashboard-api.md](dashboard-api.md), [security-and-safety.md](security-and-safety.md).

## Core

```text
C1 — завершён и принят
C2 implementation/integration — завершены и влиты в core
C2 owner acceptance — открыта bounded remediation
C3 → C4 → C5 → C6 — обязательный путь к Core 1.0
release — не начат
```

Точный scope: [`../roadmap/core/README.md`](../roadmap/core/README.md).

## Platform / CI

```text
real-deck E2E foundation — COMPLETE / merged
E2E-I1 — COMPLETE / PR #134
E2E-I2 — COMPLETE / PR #135
E2E-I3 — COMPLETE / PR #136
E2E-I4 — COMPLETE / PR #137
E2E-I5 — COMPLETE / PR #141
E2E-I6 — COMPLETE / merged через PR #142
E2E-I6 bounded corrective fix — cloud acceptance PASS / PR #144 открыт, не влит
следующий Platform/CI stage — не активирован
```

Принятый E2E-I6 candidate:

```text
implementation HEAD: 00e1e98f91b454a1fa0c5fef5b3530884f01ec32
docs/report head: 34498a03e2ce7b8aa2fe2ccef13a92ae2da42bf5
core merge SHA: 52731abb2fae682c97c3d0d9a542c250c6f25ea8
Fast CI: 30166328801 — PASS
standard/full: 30166561184 — PASS
main artifact: 8621761591
history artifact: 8621762124
canonical result: success / complete / run/pass
history: bootstrap / 1 entry
repository artifact/log retention: 90 дней для новых artifacts
```

Corrective candidate после E2E-I6:

```text
PR: #144 — OPEN / unmerged
base core: a49c4b301084e5ffd3915b4cfcacf7bb8c95a3cb
implementation HEAD: afe650adbf3ba55cb6b59068a1127022b651fbf3
Fast CI: 30169763775 — PASS
standard/full: 30169890912 — PASS
main artifact: 8622647178
history artifact: 8622648096
canonical result: success / complete / run/pass
history: append / 2 entries
corrected footprint: meaningful categories restored; other=6 service files
producer observations: current=55 / 4711, status=insufficient-history
```

Актуальный contract:

- [e2e-final-summary-history.md](e2e-final-summary-history.md)

Исторические отчёты:

- [E2E-I6 closeout](../reports/ci/e2e-i6-final-summary-history-closeout.md)
- [E2E-I6 post-merge sync](../reports/ci/e2e-i6-post-merge-documentation-sync.md)
- [E2E-I6 corrective closeout](../reports/ci/e2e-i6-corrective-fix-closeout.md)

E2E-I6 corrective fix не является новым этапом и не активирует CI 7–12. Любая оптимизация требует отдельного измеренного trigger и решения владельца.

## Operations

```text
O1.1 — Complete / integrated
O1.2 — Complete / integrated; not deployed
O1.3 — Complete / corrected / integrated; not deployed
O1.4 — Complete / integrated; not deployed
O1.5 — Next
O1.6 — Planned
```

Operations long-lived branch основана на
`core@62cd4c1fc1dda6354f3e30cb3ae4aee5dfb4891f`. Public PR #147 закрыт и не
используется из-за неправильной base `master` и literal-`\n` body.

Canonical private reviews:

- O1.1: [telemetry PR #19](https://github.com/AliceLiddell01/anki-study-report-telemetry/pull/19);
- O1.2: [telemetry PR #20](https://github.com/AliceLiddell01/anki-study-report-telemetry/pull/20);
- O1.3: [telemetry PR #21](https://github.com/AliceLiddell01/anki-study-report-telemetry/pull/21);
- O1.4 и corrective fix O1.3:
  [telemetry PR #22](https://github.com/AliceLiddell01/anki-study-report-telemetry/pull/22).

Telemetry integration:

```text
O1.1 merge: 8ef613d61c7b8672d9143b0c3b710c2d81b2fa6b
O1.2 final head: 86dcdae38c0044dee7e839ee2ff190d539b7cf57
O1.2 final CI: 30193694403 — PASS / OSV green
O1.2 merge: bb1ae3c7e42da22f917128b9becde04ba7b0b4d8
O1.3 final head: 755511ce20ffc65046503b2504d9edf6d7564e4f
O1.3 final CI: 30196888155 — PASS / OSV green
O1.3 merge: 1acb7abc6d9f2347ce59e3f2b52da3a0728140bb
O1.4 final head: 03ad15c15917c192878a6fa4900430772964c95c
O1.4 final CI: 30200494159 — PASS / OSV green
O1.4 merge: ebae6f71ec0dcf2ba044faf9dff2a58cde474263
```

Corrective fix O1.3 закрывает registry-wide differencing paths, сохраняет
различие exact zero и empty и уточняет source coverage. O1.4 добавляет отдельный
неразвёрнутый Provider Metrics Collector с least-privilege token boundary,
изолированным `ADMIN_DB`, fixed GraphQL templates, bounded retry/backfill,
90-day retention и source-specific freshness. Admin API не получает provider
token и читает только materialized provider snapshots.

20,000 accepted events остаётся abuse cap, не Free-plan capacity guarantee.
Remote D1 migration, Cloudflare Access resource/policy, Admin route,
staging/production deployment, live provider query, Cron activation и UI не
выполнялись. Следующий отдельный scope — `O1.5 — Minimal Admin Console`.

## Рабочие правила

- Desktop/laptop — основной target; mobile не является приоритетом без отдельной задачи.
- Не добавлять placeholder routes, speculative APIs или future extension surfaces заранее.
- Не возвращать legacy aliases без доказанной compatibility необходимости.
- Real-Anki Docker E2E выбирать по [test matrix](test-matrix.md) и [verification policy](verification-run-policy.md).
- Successful unchanged exact-SHA gates не повторять.
- Не создавать вложенную лестницу этапов вместо одной цельной задачи.
- Docs-only post-merge sync не требует повторного Fast CI или Docker E2E.

## Режим работы

- [Режимы ChatGPT и Codex](ai-work-modes.md)
- [ChatGPT work mode](chatgpt-work-mode.md)
- [Codex agent rules](codex-agent-rules.md)

Сначала определите трек и точный scope. Не начинайте следующий roadmap stage автоматически только потому, что предыдущий завершён.
