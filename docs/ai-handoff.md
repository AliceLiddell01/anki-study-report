# Передача актуального контекста ИИ

**Снимок:** 2026-07-27

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
PR #130 Stage 2: Cards 1:1 composition + native CSS + AV/media repair — COMPLETE
Cards final exact-card real-Anki evidence — PASS
Cards formal owner verdict — PENDING
Inspection Profiles corrected screenshot-first audit — COMPLETE / owner target decision PENDING
PR #130 Stage 3: Inspection Profiles 1:1 implementation — NOT STARTED
Settings shared regression sweep — NOT STARTED
final verification / merge decision / C3 — NOT PERFORMED
release — не начат
```

Точный scope: [`../roadmap/core/README.md`](../roadmap/core/README.md).

Current C2 remediation evidence:

```text
PR: #130 — OPEN / DRAFT / UNMERGED
base core: 62cd4c1fc1dda6354f3e30cb3ae4aee5dfb4891f

Stage 1 verified production candidate:
a746172f8746eac82ff628d36a7a6328d9332acf

Cards production AV/media repair:
78dbcb031673f5504b22a7e57a14ed00570c7a3b

Cards AV/media regression coverage:
3d4d0cca64d6f7ea7778d2684cea1287f3d7730a

final package source SHA:
ec0c2cc48c6f9b2a5aa06469223ec4f73e1eb2e7

final E2E harness SHA:
67aafd55120f8761e158ba838936d46881209f93

exact package SHA-256:
ce2d1a612e803c86b38ddb5da0de81884b4e24b7c622714b371a1bf032020f02

final evidence:
cards-final-av-media-fidelity-evidence.zip

final evidence size:
56 313 355 bytes

final evidence SHA-256:
3d8c9da5bd80bb48a6ea543bdba407cdc8751c708d7f9f990221d120f3516d8f

exact card:
1649481469689 / 影

standard browser smoke:
19/19 PASS / 18 screenshots

exact browser:
6/6 scenarios PASS / 30 screenshots

replay reset:
PASS

live GIF:
cross-scenario frame difference PASS

deterministic GIF:
frameCount=154

network/security:
external=0 / Inspection Profiles requests=0 / page errors=0 / console errors=0 / failed requests=0

evidence self-verification:
PASS / missing=0 / unexpected=0 / mismatches=0
```

Актуальные Cards contracts:

- [Cards workspace по Prototype v3.2.3](cards-v323-production-workspace.md);
- [Cards exact AV/audio/media E2E](cards-exact-av-media-e2e.md).

### Visual coverage checkpoint

`ACCEPT CARDS 1:1` принимает только route `#/cards`; это не означает принятие PR #130, Inspection Profiles, ready-for-review или merge.

| Route / area | Текущее подтверждение | Статус |
| --- | --- | --- |
| `#/cards` wide | exact same-card production captures + native CSS + AV/media evidence | technical PASS / owner verdict PENDING |
| `#/cards` drawer | exact 1024 light/dark capture и GIF crop | technical PASS / owner verdict PENDING |
| `#/cards` expanded | exact answer light/dark, GIF+PNG и geometry | technical PASS / owner verdict PENDING |
| replay/audio | два playback, reset к нулю, local MP3 HTTP 200 | PASS |
| animated GIF | exact SHA, 160×120, live light/dark frame difference, decoder 154 frames | PASS |
| `#/settings/inspection-profiles` | corrected screenshot-first audit | AUDIT COMPLETE / OWNER TARGET DECISION PENDING |
| Settings shared shell | только старые CI captures | NOT REVIEWED |
| Other Settings routes | redesign не входит в текущий scope | OUT OF SCOPE / REGRESSION ONLY |

Reports:

- [Stage 1 — C2 manual acceptance remediation](../reports/core/c2-manual-acceptance-remediation-closeout.md);
- [Stage 2 — Cards Prototype v3.2.3 production integration](../reports/core/c2-cards-v323-production-integration.md);
- [Cards final AV/audio/media evidence closeout](../reports/core/c2-cards-final-av-media-evidence-closeout.md);
- [Inspection Profiles — corrected screenshot-first audit](../reports/core/c2-inspection-profiles-screenshot-audit.md).

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
- Для exact Cards AV/media использовать [специализированный runbook](cards-exact-av-media-e2e.md).
- Successful unchanged exact-SHA gates не повторять.
- Не создавать вложенную лестницу этапов вместо одной цельной задачи.
- Docs-only closeout не требует повторного Fast CI или Docker E2E.

## Режим работы

- [Режимы ChatGPT и Codex](ai-work-modes.md)
- [ChatGPT work mode](chatgpt-work-mode.md)
- [ChatGPT manual operations](chatgpt-manual-operations.md)
- [Codex agent rules](codex-agent-rules.md)

Сначала определите трек и точный scope. Не начинайте следующий roadmap stage автоматически только потому, что предыдущий завершён.
