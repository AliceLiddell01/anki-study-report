# Передача актуального контекста ИИ

**Снимок:** 2026-07-26

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
E2E-I5 — COMPLETE / merged через PR #141
E2E-I6 — COMPLETE / cloud acceptance пройдена в PR #142
следующий Platform/CI stage — не активирован
```

Принятый кандидат E2E-I6:

```text
PR: #142
HEAD принятого кандидата: 00e1e98f91b454a1fa0c5fef5b3530884f01ec32
Fast CI: 30166328801 — ПРОЙДЕНО
standard/full: 30166561184 — ПРОЙДЕНО
main artifact ID: 8621761591
main artifact digest: sha256:11dc6f3963dbd6b91059cdab27260bb7c1b41237d11d0adb8df4a36ca662fe05
history artifact ID: 8621762124
history artifact digest: sha256:0e545d0e46f87adaac8e1f73ef8ae864fc2df3234a05f9825340dc4ff6cb9c5c
canonical summary: success / complete / run/pass
history continuity: bootstrap, entries: 1
repository artifact/log retention для новых artifacts: 90 дней
```

Канонический E2E-I6 contract:

- [e2e-final-summary-history.md](e2e-final-summary-history.md)

Предыдущие Platform contracts:

- [run-event-protocol.md](run-event-protocol.md)
- [failure-diagnostics.md](failure-diagnostics.md)
- [e2e-preflight-cancellation.md](e2e-preflight-cancellation.md)
- [e2e-package-harness-reuse.md](e2e-package-harness-reuse.md)
- [non-release-build-identity.md](non-release-build-identity.md)
- [docker-e2e.md](docker-e2e.md)

Подробный E2E-I6 closeout находится в [`../reports/ci/e2e-i6-final-summary-history-closeout.md`](../reports/ci/e2e-i6-final-summary-history-closeout.md).

Ни E2E-I6, ни его успешное слияние не активируют CI 7–12 автоматически. Любая оптимизация требует отдельного измеренного trigger и решения владельца.

## Текущие рабочие решения

- Desktop/laptop — основной target dashboard; mobile не является приоритетом без отдельной задачи.
- Не добавлять placeholder routes, future DLC surfaces или вымышленные integrations.
- Не возвращать legacy aliases и routes без доказанной compatibility необходимости.
- Real-Anki Docker E2E выбирать по [test matrix](test-matrix.md) и [verification policy](verification-run-policy.md).
- Successful unchanged exact-SHA gates не повторять.
- PR, closeout-отчёты и handoff-документы, подготовленные на русском языке, должны использовать русский во всём человекочитаемом тексте; на английском сохраняются только точные идентификаторы, пути, команды, имена полей схемы, названия workflow/job и устоявшиеся непереводимые термины.
- Не создавать вложенную лестницу этапов вместо одной цельной задачи.
- Docs-only post-merge sync не требует повторного Fast CI или Docker E2E.

## Режим работы

Выбор между ChatGPT и Codex определяется фактической средой, а не названием модели:

- [ai-work-modes.md](ai-work-modes.md)
- [chatgpt-work-mode.md](chatgpt-work-mode.md)
- [codex-agent-rules.md](codex-agent-rules.md)

Для текущей задачи сначала определите трек и точный scope. Не начинайте следующий roadmap stage автоматически только потому, что предыдущий завершён.
