# C2 — closeout post-merge manual acceptance remediation

**Дата технического закрытия:** 2026-07-26
**Репозиторий:** `AliceLiddell01/anki-study-report`
**Базовая ветка:** `core`
**Базовый SHA:** `62cd4c1fc1dda6354f3e30cb3ae4aee5dfb4891f`
**Рабочая ветка:** `c2-manual-acceptance-remediation`
**Проверенный production candidate:** `a746172f8746eac82ff628d36a7a6328d9332acf`
**Pull request:** `#130`
**Статус historical Stage 1:** автоматизированная remediation и exact package/E2E campaign технически завершены; этот report не является closeout новой Cards v3.2.3 composition. Stage 2 описан отдельно в [Cards Prototype v3.2.3 production integration](c2-cards-v323-production-integration.md). PR остаётся открытым draft.

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
documentation closeout           PASS
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

Актуальный `core` был включён в существующую ветку обычным двухродительским merge commit:

```text
merge commit:
263ae939a0b8b71706f6c63e90df7b10075e288a

parents:
661b1175ab06b44062567bb408442eac297b0e9f
62cd4c1fc1dda6354f3e30cb3ae4aee5dfb4891f
```

Rebase и force-push не применялись. Существующий PR и branch identity сохранены.

Пересечение было локализовано в трёх путях:

| Путь | Решение | Причина |
| --- | --- | --- |
| `docker/anki-e2e/smoke-browser.mjs` | сохранить current `core` | компактный real-deck runner и E2E-I1–E2E-I6 contracts заменили старый монолитный runner PR |
| `docs/test-matrix.md` | сохранить current `core` | актуальная matrix отражает package/harness identity, targeted scopes и final full policy |
| `anki_study_report/telemetry_client.py` | сохранить новые изменения `core`, затем точечно вернуть bounded continuation | regression PR доказал потерю pending intent на восьмой итерации |

После production campaign ветка была ahead 19 / behind 0 относительно `core`. Последующие commits меняют только Markdown/report tree и не меняют проверенные package bytes.

## 5. Удаление rejected prototype overlay

Commit `ea431acee24901c69460f6a6d1dc0393912eeab3` удалил:

- `web-dashboard/src/styles/prototypeV323.css`;
- import этого файла из `web-dashboard/src/main.tsx`.

Дополнительно проверено отсутствие `prototypeV323`, `prototype-v323` и marker `Accepted Prototype v3.2.3 presentation contract.`

Cleanup не откатывал production components, hooks, Cards/Profiles contracts или pinned `highlight.js`.

## 6. Telemetry continuation regression

Focused Python suite выявил regression `test_background_worker_preserves_continuation_at_iteration_limit`: pending continuation терялся после восьмой итерации bounded loop.

Commit `a746172f8746eac82ff628d36a7a6328d9332acf` восстановил pending intent на последней итерации, сохранив новые threshold/race protections из `core`.

| Проверка | Результат |
| --- | --- |
| exact continuation regression | PASS — 1 test |
| полный `tests/test_telemetry_client.py` | PASS — 22 tests |
| focused Python remediation suite | PASS — 101 tests |
| focused frontend remediation suite | PASS — 10 files / 47 tests |
| `git diff --check` | PASS |

## 7. Canonical local non-Docker verification

Выполнен `scripts/run_full_check.ps1 -SkipDocker`.

| Контур | Результат |
| --- | --- |
| TypeScript typecheck | PASS |
| frontend Vitest | PASS — 73 files / 352 tests |
| Vite production build | PASS — 2279 modules |
| bundle guard | PASS — 21 JS chunks |
| Python full | PASS — 1113 tests |
| package build/verification | PASS — 97 entries |
| generated-output hygiene | PASS |

## 8. Exact Fast CI package

```text
Fast CI run: 30173712679
head SHA: a746172f8746eac82ff628d36a7a6328d9332acf
status: success
package artifact: ci-package-a746172f8746eac82ff628d36a7a6328d9332acf-30173712679-1
package artifact ID: 8623655600
package transport digest: sha256:6e090bf9e60a6e0f95335bfebf4309c597114afe7abb44d02d51577b186c7110
internal .ankiaddon SHA-256: 3f554a2db42d482edc852c0db8ff88173f02246c86b244e8d53c05fab106aa45
internal package size: 764821 bytes
diagnostics artifact ID: 8623655386
```

Metadata подтвердили одинаковые `testedCommitSha` и `sourceHeadSha`.

## 9. Final real-Anki integration gate

Выполнен один final gate вместо двух тяжёлых последовательных запусков:

```text
run ID: 30174041436
mode: standard
scope: full
verify_restart: true
run_purpose: acceptance
fast_ci_run_id: 30173712679
status: success
```

Artifacts:

```text
ci-e2e-standard-30174041436-1
ID: 8623737960
digest: sha256:0685125c2c893a1e2d9e7fa3698236734dd83262c13ab8417b90ee99e292bc15

ci-e2e-history-30174041436-1
ID: 8623738676
digest: sha256:2af33d14d279acc650b2b442d145929b3fcf3747c3a04fd5f7066f668369a925
```

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
| first-start и restart API smoke | PASS |
| telemetry restart/deletion lifecycle | PASS |
| artifact validation/redaction | PASS |
| final Docker cleanup | PASS |

## 10. Real-deck foundation

Gate использовал только committed APKG:

```text
docker/anki-e2e/fixtures/real-decks/words-n1.apkg
docker/anki-e2e/fixtures/real-decks/grammar-n5.apkg
docker/anki-e2e/fixtures/real-decks/java-core.apkg
```

Подтверждены manifest/checksum contract, импорт трёх колод, inventory, 11 anchors, native light/dark previews и Cards real-deck inbox states. Synthetic fallback и external APKG override не использовались.

## 11. Security и архитектурные инварианты

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

Зафиксированы и не скрыты:

1. первый focused block не имел `set -e`, поэтому ложная финальная строка PASS была отвергнута;
2. `powershell.exe` был недоступен в WSL, поэтому использовался `/mnt/c`;
3. `.strip()` уничтожил значимый leading space porcelain status, после чего использовался state-aware continuation;
4. dirty patch временно оказался при `core` HEAD, но не был закоммичен и был безопасно перенесён на PR branch;
5. docs runner attempts остановились до commit/push из-за слишком строгих guards и parser ошибки diagnostics; после stop-loss документация была опубликована напрямую через GitHub connector.

## 13. Документационный closeout

Обновлены только:

- `README.md`;
- `docs/ai-handoff.md`;
- `roadmap/core/README.md`;
- `reports/README.md`;
- этот report.

Это docs-only изменение. Оно не меняет `.ankiaddon` bytes или production behavior. Новый manual Fast CI или Docker E2E не запускались.

Идентичности разделяются:

```text
verified production candidate:
a746172f8746eac82ff628d36a7a6328d9332acf

current documentation head:
смотрите актуальный head PR #130; он содержит только docs-only commits после production candidate
```

## 14. Что не проверено автоматически

Не выполнялся автоматический доступ к приватной Anki collection владельца.

Остаются ручные проверки Cards и Inspection Profiles на реальных note types, media, scroll/action/recheck behavior, Basic/Advanced draft preservation и длинных RU/EN labels.

## 15. Остаточные риски

- browser raster и scrollbar details platform-dependent;
- low-confidence field inference намеренно не угадывает роль автоматически;
- safe CSS fidelity ограничена parser allowlist;
- private-profile owner acceptance может выявить collection-specific UI issue;
- docs-only PR head не является новым package-tested SHA.

## 16. Решение и следующий шаг

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

## Post-closeout correction — Prototype v3.2.3 production integration sequence

**Добавлено:** 2026-07-26. Этот addendum исправляет только устаревший следующий шаг; historical SHA, package/E2E evidence и технические результаты выше не переписываются.

Последовательность `owner acceptance → merge decision → C3` оказалась преждевременной: Stage 1 удалил отклонённый global overlay, но не выполнил настоящую 1:1 recomposition утверждённых Cards и Inspection Profiles. Актуальная последовательность:

```text
Stage 1: latest-Core sync + rejected-overlay cleanup — COMPLETE
→ Stage 2: Cards 1:1 production integration
→ owner checkpoint: ACCEPT / REVISE CARDS
→ Stage 3: Inspection Profiles 1:1
→ owner checkpoint: ACCEPT / REVISE PROFILES
→ final verification
→ отдельное решение о merge PR #130
```

Текущий статус после Stage 2:

```text
Cards 1:1 implementation/evidence: COMPLETE / awaiting owner decision
Inspection Profiles 1:1: NOT STARTED
PR #130: OPEN / DRAFT / UNMERGED
Fast CI / Docker E2E in Stage 2: NOT RUN
merge / release / C3: NOT PERFORMED
```

Предыдущий exact Fast CI и real-Anki E2E остаются baseline evidence Stage 1 и не выдаются за доказательство новой Cards composition. Полный Stage 2 implementation/evidence ledger: [C2 Cards Prototype v3.2.3 production integration](c2-cards-v323-production-integration.md).
