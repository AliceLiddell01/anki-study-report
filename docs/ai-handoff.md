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
C2 base implementation/integration — завершены и влиты в core
PR #130 Stage 1: latest-Core sync + rejected-overlay cleanup — COMPLETE
PR #130 Stage 2: Cards 1:1 composition + bounded visual revision + native Anki night-mode correction — COMPLETE, owner decision PENDING
PR #130 Stage 3: Inspection Profiles 1:1 — NOT STARTED
final verification / merge decision / C3 — NOT PERFORMED
release — не начат
```

Точный scope: [`../roadmap/core/README.md`](../roadmap/core/README.md).

Current C2 remediation evidence:

```text
PR: #130 — OPEN / DRAFT / UNMERGED
base core: 62cd4c1fc1dda6354f3e30cb3ae4aee5dfb4891f
verified production candidate: a746172f8746eac82ff628d36a7a6328d9332acf
Stage 1 Fast CI baseline: 30173712679 — PASS (pre-revision package)
Stage 1 standard/full + restart baseline: 30174041436 — PASS (pre-revision package)
package SHA-256: 3f554a2db42d482edc852c0db8ff88173f02246c86b244e8d53c05fab106aa45
Stage 1 synchronization/overlay cleanup: complete
Cards 1:1 initial production commit: 1f78b69574794c67149796343dde8cbdd4948fb4
Cards bounded visual revision: 34a7680392ee7e17dc3ee826dad5bdf9808bc3d1
Cards native Anki night-mode correction: f288595499904eadeb81c4ceab3da232581c30f5
Cards final visual production commit: c2c2b65b399907010ff7e2d40307b1ded02a1bc3
Cards final visual evidence: cards-v323-production-final-visual-closure-evidence.zip
Cards final visual evidence SHA-256: 6feef7766f9283316199430da3dc934b8ab91c5808bf6fe4ae7c589c8dd2599b
Cards repaired micro-evidence: cards-v323-production-final-evidence-repair.zip
Cards repaired micro-evidence SHA-256: ab2db7135ee3993e0e31668252b814694ae34d8adb1688398d5b3d13747e55d8
Cards composition/revision/night-mode/final visual closure/repaired evidence: COMPLETE / owner decision PENDING
Inspection Profiles screenshot-first visual audit: NOT STARTED
Inspection Profiles 1:1 implementation: NOT STARTED
Settings shared regression sweep: NOT STARTED
PR merge/final verification/C3: NOT PERFORMED
```

Актуальный Cards contract: [Cards workspace по Prototype v3.2.3](cards-v323-production-workspace.md).

### Visual coverage checkpoint

`ACCEPT CARDS 1:1` принимает только route `#/cards`; это не означает принятие PR #130, Inspection Profiles, ready-for-review или merge.

| Route / area | Prototype references | Current production captures | Reviewed | Owner verdict / next action |
| --- | --- | --- | --- | --- |
| `#/cards` wide | есть | есть, включая repaired Words media | да | owner decision PENDING |
| `#/cards` drawer/modal | есть | есть | да | входит только в Cards checkpoint |
| `#/cards` lifecycle | есть | repaired `still_active` отличается от `recheck_pending` | да | owner decision PENDING |
| `#/settings/inspection-profiles` | есть | актуального полного production-пакета нет | нет | NOT REVIEWED; после `ACCEPT CARDS 1:1` отдельный screenshot-first audit без production changes на первом проходе |
| Settings shared shell | частично | только старые CI captures | нет | NOT REVIEWED |
| Other Settings routes | redesign не входит в текущий scope | нужен только regression sweep | нет | OUT OF SCOPE / REGRESSION ONLY |


Reports:

- [Stage 1 — C2 manual acceptance remediation](../reports/core/c2-manual-acceptance-remediation-closeout.md);
- [Stage 2 — Cards Prototype v3.2.3 production integration](../reports/core/c2-cards-v323-production-integration.md).

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
