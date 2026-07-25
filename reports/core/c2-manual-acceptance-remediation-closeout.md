# C2 — closeout post-merge manual acceptance remediation

**Дата технического закрытия:** 2026-07-26
**Репозиторий:** `AliceLiddell01/anki-study-report`
**Базовая ветка:** `core`
**Базовый SHA:** `62cd4c1fc1dda6354f3e30cb3ae4aee5dfb4891f`
**Рабочая ветка:** `c2-manual-acceptance-remediation`
**Проверенный production candidate:** `a746172f8746eac82ff628d36a7a6328d9332acf`
**Pull request:** `#130`
**Статус:** автоматизированная remediation и exact package/E2E campaign технически завершены; PR остаётся открытым draft, ручной owner acceptance на приватной коллекции и отдельное решение об интеграции не выполнены.

## 1. Итог этапа

Этот follow-up закрыл автоматизируемую часть post-merge owner acceptance remediation для C2 без создания нового numbered stage.

Работа состояла из четырёх связанных задач:

1. синхронизировать существующую ветку PR #130 с актуальным `core` обычным merge commit;
2. удалить отклонённый глобальный prototype overlay и не переносить его в production composition;
3. сохранить принятые Cards / native preview / Inspection Profiles изменения без возврата устаревшего runtime и E2E harness;
4. восстановить потерянный при разрешении конфликта bounded telemetry continuation и повторно доказать production package в Fast CI и real-Anki `standard/full`.

Финальный автоматизированный результат:

```text
latest Core synchronization      PASS
rejected global overlay cleanup  PASS
telemetry continuation repair    PASS
focused regression verification  PASS
canonical non-Docker gate        PASS
exact Fast CI package            PASS
standard/full real-Anki E2E      PASS
restart verification             PASS
artifact identity/redaction      PASS
```

Этап не выполнял merge PR #130 в `core`, release, deployment, публикацию или запуск C3.

## 2. Исходное состояние

Перед синхронизацией:

- актуальный `core`: `62cd4c1fc1dda6354f3e30cb3ae4aee5dfb4891f`;
- исходный head PR #130: `661b1175ab06b44062567bb408442eac297b0e9f`;
- ветка PR отставала от `core` на 241 commit и содержала 16 собственных commits;
- PR был открыт, draft и не смержен;
- предыдущие successful Fast CI/E2E proofs относились к старому head `0a85d565a3746bbba5b7f1268283147f206a513c` и не могли считаться current-head evidence после синхронизации.

Источниками истины при разрешении расхождений были current production code и tests из `core`, затем актуальные contracts и только после этого исторические отчёты PR.

## 3. Scope

### В scope

- ordinary two-parent merge актуального `core` в существующую PR-ветку;
- сохранение production remediation Cards и Inspection Profiles;
- сохранение current E2E-I1–E2E-I6 harness и test-matrix contracts;
- удаление rejected global CSS overlay;
- проверка отсутствия остаточных imports/markers overlay;
- focused и canonical non-Docker verification;
- exact Fast CI package;
- один risk-appropriate final `standard/full` real-Anki E2E с restart;
- синхронизация README, AI handoff, Core roadmap и reports index;
- подробный closeout report.

### Вне scope

- merge PR #130 в `core`;
- rebase или force-push;
- новый PR или новая рабочая ветка;
- C3 UI & Shell;
- C1.6B;
- release, deployment, AnkiWeb publication;
- доступ к приватной Anki collection владельца;
- повтор успешного same-SHA Fast CI или E2E;
- `strict-apkg`, `perf100`, warm repeat и локальный Docker после cloud PASS.

## 4. Git integration

### 4.1 Merge commit

Актуальный `core` был включён в существующую ветку обычным двухродительским merge commit:

```text
merge commit:
263ae939a0b8b71706f6c63e90df7b10075e288a

parents:
661b1175ab06b44062567bb408442eac297b0e9f
62cd4c1fc1dda6354f3e30cb3ae4aee5dfb4891f
```

Rebase и force-push не применялись. Существующий PR и branch identity сохранены.

### 4.2 Разрешение пересечений

Пересечение между старой базой PR, текущим `core` и remediation branch было локализовано в трёх путях:

| Путь | Решение | Причина |
| --- | --- | --- |
| `docker/anki-e2e/smoke-browser.mjs` | сохранить current `core` | компактный real-deck runner и E2E-I1–E2E-I6 contracts заменили старый монолитный runner PR |
| `docs/test-matrix.md` | сохранить current `core` | актуальная matrix отражает package/harness identity, targeted scopes и final full policy |
| `anki_study_report/telemetry_client.py` | сначала сохранить current `core`, затем точечно вернуть bounded continuation | новые threshold/race changes из `core` обязательны, но regression PR доказал потерю pending intent на восьмой итерации |

Все остальные необходимые remediation paths были перенесены без подмены current production architecture.

### 4.3 Финальное отношение к `core`

После production commit campaign ветка находилась:

```text
ahead:  19
behind: 0
merge base: 62cd4c1fc1dda6354f3e30cb3ae4aee5dfb4891f
```

Последующий documentation-only closeout commit меняет только Markdown/report tree и не меняет проверенные package bytes.

## 5. Удаление rejected prototype overlay

В merge tree присутствовал глобальный prototype overlay, который был признан неподходящим для production composition.

Отдельным commit:

```text
ea431acee24901c69460f6a6d1dc0393912eeab3
Remove the rejected global prototype overlay
```

были удалены:

- `web-dashboard/src/styles/prototypeV323.css`;
- import этого файла из `web-dashboard/src/main.tsx`.

Дополнительно проверено отсутствие:

- `prototypeV323`;
- `prototype-v323`;
- marker `Accepted Prototype v3.2.3 presentation contract.`

Cleanup не откатывал production components, hooks, Cards/Profiles contracts или pinned `highlight.js`.

## 6. Telemetry continuation regression

### 6.1 Обнаружение

Focused Python suite выявил один реальный failure:

```text
tests/test_telemetry_client.py::
test_background_worker_preserves_continuation_at_iteration_limit
```

Причина:

1. worker обрабатывал pending request;
2. `_send_again` / `_deletion_requested` очищались внутри bounded loop;
3. на восьмой итерации выполнялся `continue`;
4. цикл завершался;
5. `finally` больше не видел pending intent;
6. continuation worker не создавался.

### 6.2 Исправление

Commit:

```text
a746172f8746eac82ff628d36a7a6328d9332acf
Preserve telemetry continuation at the iteration limit
```

точечно восстановил bounded behavior:

- loop использует `attempt`;
- на последней разрешённой итерации pending intent возвращается во внутренние flags;
- текущий worker завершает цикл;
- `finally` создаёт continuation worker;
- новые threshold/race protections из `core` сохранены.

Изменено только:

```text
anki_study_report/telemetry_client.py
```

### 6.3 Focused proof

| Проверка | Результат |
| --- | --- |
| exact continuation regression | PASS — 1 test |
| полный `tests/test_telemetry_client.py` | PASS — 22 tests |
| focused Python remediation suite | PASS — 101 tests |
| focused frontend remediation suite | PASS — 10 files / 47 tests |
| `git diff --check` | PASS |

## 7. Canonical local non-Docker verification

Выполнен canonical gate:

```text
scripts/run_full_check.ps1 -SkipDocker
```

Результаты:

| Контур | Результат |
| --- | --- |
| repository hygiene | PASS |
| structured changelog outputs | PASS |
| TypeScript typecheck | PASS |
| frontend Vitest | PASS — 73 files / 352 tests |
| Vite production build | PASS — 2279 modules |
| bundle guard | PASS — 21 JS chunks |
| bundle total | 1 406 617 bytes |
| bundle gzip total | 397 647 bytes |
| Python full | PASS — 1113 tests |
| package build | PASS |
| package verification | PASS |
| archive entries | 97 |
| linked dashboard asset graph | PASS |
| forbidden/missing entries | none |

Проверка не оставила generated assets или другие tracked changes.

## 8. Exact Fast CI package

### 8.1 Run identity

```text
workflow: Fast CI
run ID: 30173712679
event: workflow_dispatch
branch: c2-manual-acceptance-remediation
head SHA: a746172f8746eac82ff628d36a7a6328d9332acf
status: completed
conclusion: success
```

Job `Frontend, Python and package` завершился успешно. Canonical fast pipeline, verification planner, package preparation и оба artifact uploads прошли.

### 8.2 Package identity

```text
artifact:
ci-package-a746172f8746eac82ff628d36a7a6328d9332acf-30173712679-1

artifact ID:
8623655600

artifact archive size:
759768 bytes

artifact transport digest:
sha256:6e090bf9e60a6e0f95335bfebf4309c597114afe7abb44d02d51577b186c7110

internal package:
anki_study_report.ankiaddon

internal package size:
764821 bytes

internal package SHA-256:
3f554a2db42d482edc852c0db8ff88173f02246c86b244e8d53c05fab106aa45
```

Diagnostics artifact:

```text
ci-fast-30173712679-1
artifact ID: 8623655386
transport digest:
sha256:89c13009095cc4a32d9ae3b53e836a05420b01a8efdf2d40bb6838b69eacaaf1
```

Metadata подтвердили одинаковые `testedCommitSha` и `sourceHeadSha`.

## 9. Final real-Anki integration gate

### 9.1 Выбор gate

PR затрагивает одновременно:

- Cards и native preview;
- Inspection Profiles;
- shared frontend presentation;
- telemetry/restart lifecycle;
- package/runtime contour.

Поэтому вместо двух последовательных тяжёлых запусков был выполнен один final:

```text
mode: standard
scope: full
verify_restart: true
run_purpose: acceptance
fast_ci_run_id: 30173712679
```

Это соответствует [verification run policy](../../docs/verification-run-policy.md): несколько product scopes и telemetry/restart требуют final `standard/full`.

### 9.2 Run identity

```text
workflow: Full Docker / Anki E2E
run ID: 30174041436
event: workflow_dispatch
branch: c2-manual-acceptance-remediation
head SHA: a746172f8746eac82ff628d36a7a6328d9332acf
status: completed
conclusion: success
job: Real Anki Desktop (standard / full)
```

Exact Fast CI package был разрешён по artifact ID, скачан, проверен и повторно проверен после E2E. Source-build fallback не использовался.

### 9.3 E2E artifacts

Main artifact:

```text
ci-e2e-standard-30174041436-1
artifact ID: 8623737960
size: 7045989 bytes
digest:
sha256:0685125c2c893a1e2d9e7fa3698236734dd83262c13ab8417b90ee99e292bc15
```

Bounded history:

```text
ci-e2e-history-30174041436-1
artifact ID: 8623738676
size: 7228 bytes
digest:
sha256:2af33d14d279acc650b2b442d145929b3fcf3747c3a04fd5f7066f668369a925
```

### 9.4 Canonical result

| Evidence | Результат |
| --- | --- |
| final summary | `success` |
| failure category | `none` |
| browser plan | 23/23 PASS |
| screenshots | 18/18 captured |
| browser console events | 0 |
| page errors | 0 |
| failed requests | 0 |
| unexpected external requests | 0 |
| first-start API smoke | PASS |
| restart API smoke | PASS |
| telemetry restart persistence | PASS |
| offline deletion-pending state | PASS |
| final deletion confirmation | PASS |
| credential destruction | PASS |
| artifact validation/redaction | PASS |
| final Docker cleanup | PASS |

Текущий compact runner создаёт 18 contract-oriented screenshots. Он не обязан воспроизводить старый исторический 125-screenshot artifact: авторитетными являются current workflow, manifest, browser plan и canonical final summary.

## 10. Real-deck foundation

Gate использовал только три committed APKG:

```text
docker/anki-e2e/fixtures/real-decks/words-n1.apkg
docker/anki-e2e/fixtures/real-decks/grammar-n5.apkg
docker/anki-e2e/fixtures/real-decks/java-core.apkg
```

Подтверждены:

- manifest/checksum contract;
- импорт всех трёх колод;
- inventory;
- 11 обязательных anchors;
- native light/dark previews;
- Cards real-deck inbox states;
- отсутствие synthetic fallback и external APKG override.

## 11. Security и архитектурные инварианты

Remediation не изменила фундаментальные границы:

- frontend не получил прямой доступ к Anki collection;
- dashboard остался loopback-only и token-protected;
- CSP не ослаблена;
- sanitizer и parser-backed CSS policy сохранены;
- preview не стал iframe или JavaScript execution surface;
- внешние preview requests не разрешены;
- media остаются за validated local boundary;
- action allowlists не расширялись неограниченно;
- raw note values, profile data и tokens не публиковались в artifacts;
- telemetry deletion lifecycle остался fail closed.

Актуальные contracts:

- [Cards v2 product contract](../../docs/cards-v2-product-contract.md)
- [Cards resolution loop](../../docs/cards-v2-resolution-loop.md)
- [Card preview semantics](../../docs/card-preview-semantics.md)
- [Inspection Profiles UI](../../docs/inspection-profiles-ui.md)
- [Guided Inspection Profiles](../../docs/guided-inspection-profiles.md)
- [Verification run policy](../../docs/verification-run-policy.md)
- [Fast CI package / E2E reuse](../../docs/e2e-package-harness-reuse.md)
- [Canonical E2E summary/history](../../docs/e2e-final-summary-history.md)

## 12. Операционные инциденты и исправления процесса

Во время ручного ChatGPT-mode closeout были выявлены четыре orchestration defect. Они не скрыты и не считаются успешными checkpoint:

### 12.1 Ложная финальная строка первого focused block

Первый блок содержал `set -u` и `pipefail`, но не `set -e`. Python suite вернул failure, однако shell продолжил выполнение до строки `CHECKPOINT 2 PASS`.

Исправление:

- checkpoint был классифицирован как FAIL;
- последующие блоки использовали `set -euo pipefail`;
- failing telemetry regression был локализован и исправлен;
- ложный PASS не использовался как evidence.

### 12.2 Недоступный `powershell.exe`

WSL session не имел Windows executable interoperability в `PATH`.

Исправление:

- путь к Downloads определялся через `/mnt/c/Users/...`;
- WSL configuration не изменялась ради одной операции;
- repository mutation до failure не происходила.

### 12.3 Значимый leading space в porcelain

Первый Python repair runner применил mutation, но затем ошибочно использовал `.strip()` для `git status --porcelain`, уничтожив значимый leading space в статусе `" M path"`.

Исправление:

- исходный runner повторно не запускался;
- создан state-aware continuation runner;
- проверялся exact dirty set и exact repaired source anchor.

### 12.4 Dirty patch оказался в checkout `core`

Новый terminal открылся на `core`, поэтому рабочая копия изменения временно находилась при `core` HEAD.

Исправление:

- никакой commit в `core` не создавался;
- доказано, что исходный blob `telemetry_client.py` одинаков в `core` и PR branch;
- доказано, что dirty set содержит только целевой patch;
- обычный `git switch` безопасно перенёс working-tree patch на PR branch;
- затем tests, commit и fast-forward push выполнены на правильной ветке.

Итог: данные не потеряны, `core` history не изменена, force/reset/stash не применялись.

## 13. Документационный closeout

После успешных package/E2E gates обновляются только:

- `README.md`;
- `docs/ai-handoff.md`;
- `roadmap/core/README.md`;
- `reports/README.md`;
- этот report.

Это docs-only изменение. Оно не меняет `.ankiaddon` bytes или production behavior. В соответствии с [verification run policy](../../docs/verification-run-policy.md) для него нужны `git diff --check` и проверка links/paths/code fences; этот closeout не dispatch'ит новый manual Fast CI или Docker E2E.

Поэтому identities разделяются:

```text
verified production candidate:
a746172f8746eac82ff628d36a7a6328d9332acf

subsequent PR head:
documentation-only closeout commit
```

Fast CI и E2E остаются evidence именно для проверенного production candidate.

## 14. Что не проверено автоматически

Не выполнялся автоматический доступ к приватной Anki collection владельца.

Остаются ручные проверки:

### Cards

- native compact/expanded backgrounds на representative real cards;
- media и code highlighting на реальных шаблонах;
- wheel behavior queue / Inspector / preview / drawer;
- `Suspend`, `Bury`, `Open in Anki`;
- pending/success/error feedback;
- authoritative Recheck outcomes;
- refresh и reduced-motion appearance.

### Inspection Profiles

- Basic/Advanced никогда не отображаются одновременно;
- unsaved draft сохраняется при mode switch;
- meaningful real field names предлагаются корректно;
- ambiguous fields требуют явного выбора;
- длинные RU/EN labels читаемы на обычных desktop widths;
- validation feedback остаётся inline.

## 15. Остаточные риски

- browser raster и scrollbar details остаются platform-dependent;
- low-confidence field inference намеренно не угадывает роль автоматически;
- safe CSS fidelity ограничена parser allowlist;
- ручной owner acceptance может выявить collection-specific UI issue;
- docs-only PR head не является новым package-tested SHA, хотя production tree относительно `a746172f8746eac82ff628d36a7a6328d9332acf` не меняется.

## 16. Решение и следующий шаг

Автоматизированная bounded C2 remediation технически готова.

Следующий шаг:

```text
owner acceptance на приватной collection
→ отдельное решение об интеграции PR #130
→ только после этого возможна активация C3
```

C3, C1.6B, release и другие треки не запускаются автоматически.

## 17. Финальная классификация

```text
C1: завершён и принят
C2 implementation/integration: завершены и влиты в core
C2 automated post-merge remediation: PASS
verified production candidate: a746172f8746eac82ff628d36a7a6328d9332acf
canonical local non-Docker: PASS
Fast CI exact package: 30173712679 / PASS
standard/full + restart: 30174041436 / PASS
artifact validation/redaction: PASS
PR #130: OPEN / DRAFT / UNMERGED
private-profile owner acceptance: PENDING
C3: NOT STARTED
release/deployment/publication: NOT PERFORMED
```
