# Передача актуального контекста ИИ

**Снимок:** 2026-07-25

Этот файл — короткая точка входа для нового рабочего чата. Он не заменяет production code, профильные contracts, roadmap или closeout reports.

## Порядок чтения

1. [`../README.md`](../README.md)
2. этот файл;
3. профильный roadmap;
4. профильный contract в `docs/`;
5. актуальные production code и tests;
6. свежий closeout или artifact только когда это необходимо задаче.

При противоречиях:

```text
production code и tests
→ актуальные contracts в docs/
→ roadmap/
→ свежие reports/artifacts
→ старые планы и сообщения
→ предположения
```

Не утверждайте, что файл, код, run или artifact изучен, если он фактически не был открыт.

## Проект

Anki Study Report — локальный add-on для Anki 26.05+ с Python runtime и React/TypeScript dashboard.

Ключевые границы:

- dashboard доступен только через loopback и защищён token;
- frontend получает bounded JSON/API projections и не читает collection напрямую;
- preview использует sanitizer и Shadow DOM без JavaScript execution surface;
- profile/study data остаются локальными, кроме явно opt-in bounded technical telemetry;
- payload/public behavior меняются синхронно между слоями, tests и docs.

Подробности: [architecture.md](architecture.md), [dashboard-api.md](dashboard-api.md), [security-and-safety.md](security-and-safety.md).

## Текущее состояние Core

```text
C1 — завершён и принят
C2 implementation/integration — завершены и влиты в core
C2 owner acceptance — повторно открыта после ручной UI-проверки
следующая работа — bounded post-C2 manual acceptance remediation
C3 → C4 → C5 → C6 — обязательный путь к Core 1.0
release — не начат
```

Параллельные Platform, Gamification, Operations, Identity и Extensions не блокируют Core без явно документированной зависимости.

Точный scope: [`../roadmap/core/README.md`](../roadmap/core/README.md).

## Текущее состояние Platform / CI

```text
real-deck E2E foundation — COMPLETE / merged
E2E-I1 — COMPLETE / merged через PR #134
E2E-I2 — COMPLETE / merged через PR #135
E2E-I3 — COMPLETE / merged через PR #136
E2E-I4 — COMPLETE / merged через PR #137
E2E-I5 — COMPLETE / cloud acceptance PASS в PR #141
E2E-I6 — следующий planned stage, не начат
```

E2E-I4 merge:

```text
PR: #137
feature implementation: 5e52faee5cd97af8e7760e2c5041c782ce4273fa
docs head: 37b0a569b3a11de6af84e2cdb675f98e97dcd30b
core merge commit: 8924987de31da64203855f5b15019b5075945650
```

E2E-I5 accepted candidate:

```text
PR: #141
candidate HEAD: 92354870970956ed5d2e9216efca5058aa8addf3
Fast CI: 30149481485 — PASS
standard/full: 30150971581 — PASS
artifact ID: 8617629796
identity digest: sha256:d85608e71b0bb927fbd7f400c9b65d436395ff359f467dec6a12f0c63028cbad
```

E2E-I6 не начинается автоматически: merge E2E-I5 и старт следующего stage остаются отдельными решениями владельца.

Актуальные Platform contracts:

- [run-event-protocol.md](run-event-protocol.md)
- [failure-diagnostics.md](failure-diagnostics.md)
- [e2e-preflight-cancellation.md](e2e-preflight-cancellation.md)
- [e2e-package-harness-reuse.md](e2e-package-harness-reuse.md)
- [non-release-build-identity.md](non-release-build-identity.md)
- [docker-e2e.md](docker-e2e.md)

Исторические run IDs, package hashes и artifact digests находятся в [`../reports/README.md`](../reports/README.md).

## Текущие рабочие решения

- Desktop/laptop — основной target dashboard; mobile не является приоритетом без отдельной задачи.
- Не добавлять placeholder routes, future DLC surfaces или вымышленные integrations.
- Не возвращать legacy aliases и routes без доказанной compatibility необходимости.
- Real-Anki Docker E2E выбирать по [test matrix](test-matrix.md) и [verification policy](verification-run-policy.md).
- Successful unchanged exact-SHA gates не повторять.
- Не создавать вложенную лестницу этапов вместо одной цельной задачи.
- Docs-only post-merge sync не требует повторного Fast CI или Docker E2E.

## Режим работы

Выбор между ChatGPT и Codex определяется фактической средой, а не названием модели:

- [ai-work-modes.md](ai-work-modes.md)
- [chatgpt-work-mode.md](chatgpt-work-mode.md)
- [codex-agent-rules.md](codex-agent-rules.md)

Для текущей задачи сначала определите трек и точный scope. Не начинайте следующий roadmap stage автоматически только потому, что предыдущий завершён.
