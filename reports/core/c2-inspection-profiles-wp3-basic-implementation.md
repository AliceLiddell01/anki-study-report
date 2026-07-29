# Inspection Profiles WP3 — Basic editor implementation

Дата: 2026-07-29  
Среда: Windows-native  
Repository: `C:\Users\KykLa\Documents\anki-study-report`  
Ветка: `c2-manual-acceptance-remediation`  
PR: `#130` — open, draft, unmerged

## Статус

```text
WP1 Settings shell:
STRUCTURAL FOUNDATION DELIVERED
OWNER VISUAL ASSESSMENT: 6/10 (historical owner assessment)
VISUAL LANGUAGE: PROVISIONAL

WP2 corrective candidate:
DELIVERED
EXTERNAL VISUAL REVIEW: 7.8/10 (historical external assessment)
OWNER ACCEPTANCE: NOT GRANTED
VISUAL DEBT: OPEN

Owner progression decision:
WP3 START AUTHORIZED WITHOUT WP2 ACCEPTANCE

WP3 Basic editor:
IMPLEMENTATION CANDIDATE DELIVERED
EXTERNAL VISUAL REVIEW: PENDING

WP4 Advanced:
NOT STARTED

Cards:
ACCEPTED / COMPLETE / FROZEN
```

Численная визуальная оценка WP3 не выполнялась. Visual verdict зарезервирован
за внешним reviewer и владельцем.

## Windows baseline

| Параметр | Значение |
| --- | --- |
| исходный implementation baseline | `5ee8ac07d1d9473cd09044d966252b2a5f6de499` |
| branch | `c2-manual-acceptance-remediation` |
| remote branch | `origin/c2-manual-acceptance-remediation` |
| PR base | `core` |
| frozen PR merge-base | `62cd4c1fc1dda6354f3e30cb3ae4aee5dfb4891f` |
| Windows | `10.0.22631` |
| PowerShell | `7.6.3` |
| Git | `2.52.0.windows.1` |
| Node | `v22.23.1` |
| pnpm | `9.15.9` |
| Playwright | `1.55.1` |
| Chromium | `140.0.7339.186` |
| axe-core | `4.12.1` |

WSL не использовался. До реализации branch была чистой и совпадала с remote.
PR уже имел конфликты с текущим `core`; их разрешение не входило в WP3.

## Решение владельца и границы

Текущая задача отдельно разрешила начать WP3, но не изменила verdict WP2.
Поэтому остаточный WP2 visual debt не закрывался и не переносился в статус
`CLOSED`.

WP3 ограничен внутренним Basic mode и его непосредственной интеграцией в
существующий editor frame. Не изменялись:

- backend, API schemas и strict Inspection Profile v1 contract;
- `useInspectionProfiles`, mutation lifecycle и action zone;
- Advanced internals;
- Settings header, catalog, identity rail и общий WP2 frame;
- Cards composition, behavior и styles;
- generated dashboard assets.

## Изученные источники

Перед изменениями прочитаны:

- `AGENTS.md`, `README.md`, `docs/ai-handoff.md`,
  `docs/chatgpt-work-mode.md`, `roadmap/README.md`,
  `roadmap/core/README.md`;
- `docs/inspection-profiles-v1.md`, `docs/inspection-profiles-ui.md`,
  `docs/guided-inspection-profiles.md`,
  `docs/security-and-safety.md`, `docs/test-matrix.md`,
  `docs/verification-run-policy.md`;
- WP2 screenshot audit, frame implementation, corrective-pass report и
  внешний corrective review;
- актуальные production components, projection helpers, tests, styles,
  localization и repository-owned visual harness;
- Prototype v3.2.3 README, checkpoint, state contract, accessibility report,
  interaction audit и authored `prototype.html`;
- переданные AI context и evidence sources.

При расхождениях приоритет отдавался current production code/tests, затем
актуальному contract и авторизующему owner task.

## Prototype integrity и target discovery

Источник:
`C:\Users\KykLa\Downloads\pr130_visual_prototype_v3_2_3.zip`.

| Проверка | Результат |
| --- | --- |
| ZIP SHA-256 | `48F3ACE56B11F0DD328709923A99BB7277B0747F2CBC489E00DEE7821F6BF8F9` |
| entries | 52 |
| uncompressed bytes | 9,384,879 |
| declared checksums | 51 |
| checksum missing/mismatch | 0 / 0 |
| full CRC read | PASS |

Authored target найден в состоянии Java / Basic. Он использует две внутренние
колонки: field mappings слева, validation rules и template scope справа.
Target был открыт и проверен в Chromium при 1440×900; same-state comparisons
используют именно этот authored state, а не выдуманную реконструкцию.

## Component map

| Слой | Ответственность в WP3 |
| --- | --- |
| `BasicProfileEditor.tsx` | guided summary, field mappings, шесть check kinds, template scope и focus ownership |
| `InspectionProfilesSettingsPage.tsx` | маршрутизация error-summary links к Basic-supported controls без изменения Advanced-only path |
| `inspectionProfiles.css` | bounded two-column composition, responsive collapse, readable density и QHD width |
| `BasicProfileEditor.test.tsx` | template scope, add/remove focus и Basic interaction contracts |
| validation/visual contract tests | empty required mapping, summary/control focus и structural selectors |
| `inspection-profiles-visual-evidence.mjs` | deterministic WP3 states, region crops, geometry, interaction and accessibility evidence |

## Реализация

Basic editor перекомпонован в одну guided surface:

- сводка оставляет понятное состояние, explanation и confidence category без
  дублированных counts и schema terminology;
- на широком editor field mappings занимают левую колонку, requirements и
  template scope — правую;
- при ширине editor до 760 px секции складываются в одну колонку, а field row
  складывается только до 480 px;
- QHD guided surface ограничена `78rem`, чтобы controls не растягивались на
  весь workspace;
- сохранены все шесть строгих check kinds и стабильные внутренние ID;
- при нескольких templates пользователь явно выбирает all либо конкретный
  набор; снять последний explicit template нельзя;
- добавление требования фокусирует новый row, удаление — следующий,
  предыдущий либо кнопку добавления;
- required controls получают `aria-invalid` и `aria-describedby`;
- explicit validation сначала фокусирует summary; Basic-supported link
  возвращает фокус на точный Basic control, Advanced-only path сохранён;
- очистка required mapping оставляет `[]`, а не stale controlled value.

## Сохранённые инварианты

- frontend не получил прямой доступ к Anki collection;
- loopback/token boundary, sanitizer, media validation и allowlists не
  ослаблялись;
- Basic и Advanced продолжают редактировать один browser draft;
- autosave и autoconfirm не добавлялись;
- strict payload contract не изменён;
- Advanced и action zone не перерабатывались;
- Cards остался frozen и не затронут.

## Автоматизированные проверки

| Команда | Результат |
| --- | --- |
| focused Vitest, 4 files / 16 tests | PASS |
| `.\node_modules\.bin\vitest.cmd run`, 75 files / 393 tests | PASS |
| `.\node_modules\.bin\tsc.cmd --noEmit` | PASS |
| Vite production build, 2285 modules | PASS |
| bundle guard, 21 JS chunks / entry 441,975 bytes / total 1,422,275 bytes / gzip 402,366 bytes | PASS |
| `node --check scripts/inspection-profiles-visual-evidence.mjs` | PASS |
| `python -m compileall -q anki_study_report` | PASS |
| `git diff --check` | PASS |

Docker и real-Anki E2E не запускались: они запрещены scope WP3 и не
соответствуют риску frontend-only изменения.

## Browser matrix

Финальный repository-owned harness выполнил production-preview matrix:

- 26 full-page captures;
- 354 region captures;
- 26 ARIA snapshots;
- 0 axe violations и 0 incomplete results для обязательных 1440 RU light Java
  и 1024 EN dark Java states;
- 0 unexpected requests, page errors, console errors, failed requests и
  expected aborts;
- обязательные EN/RU, light/dark, Java Basic, review/unresolved, zero
  requirements, custom role, multi-template, 1024 и QHD states;
- priority, min length, multi-role, explicit template scope, template
  check/uncheck, add/remove focus, empty required mapping, client-side
  validation, summary focus и exact-control focus.

QHD geometry: editor width `1882.75`, Basic panel width `1170`, internal
columns `700.234 / 451.766`, horizontal overflow отсутствует.

## Evidence identity

Внешний artifact:

```text
C:\Users\KykLa\Documents\Anki Study Report Evidence\
  pr130-wp3-basic-evidence.zip
```

Implementation source:

```text
commit: ddbd7ec7fcb166ffcd7dfbef8ee9da0838326076
tree: cf7d886b5d14daa4a313bbf2a27ceea380c3a2a2
```

Expanded harness source:

```text
commit: 1f60e9d3fa6989e4c01fd03033a0f3d35f12668a
tree: bbd3a2409df479557460d991494de8526143367f
```

Artifact содержит manifest, SHA256SUMS, source identities, Prototype
references, production captures, comparisons, overlays, pixel diffs, metrics,
accessibility, interactions, diagnostics, report и exact harness source. Он
пересобран после документационного delivery head, поэтому `finalDocsHead`
записан отдельно от screenshot implementation source. Финальные ZIP
size/SHA-256/CRC опубликованы в body PR #130 и итоговом отчёте.

## Findings ledger

| ID | Статус | Результат |
| --- | --- | --- |
| BASIC-01 | CLOSED | exact authored Java/Basic target найден и целостность Prototype подтверждена |
| BASIC-02 | PARTIAL | Basic editor перекомпонован и bounded; наследуемые WP2 frame differences и более строгие production controls остаются видимыми |
| BASIC-03 | CLOSED | summary hierarchy упрощена без schema jargon и alert-on-load |
| BASIC-04 | CLOSED | field mappings собраны в читаемую левую колонку |
| BASIC-05 | CLOSED | все шесть check kinds доступны через понятные controls |
| BASIC-06 | CLOSED | explicit template scope не может неявно стать all |
| BASIC-07 | CLOSED | add/remove requirement сохраняет предсказуемый focus |
| BASIC-08 | CLOSED | required mapping очистка не оставляет stale value |
| BASIC-09 | CLOSED | error summary возвращает к точному Basic control |
| BASIC-10 | CLOSED | 1024 и QHD не имеют горизонтального overflow |
| BASIC-11 | CLOSED | обязательные axe/ARIA/keyboard checks пройдены |
| BASIC-12 | CLOSED | backend, strict contract, Advanced, action zone и Cards не изменены |

## Открытые отклонения

`BASIC-02` остаётся `PARTIAL`: WP3 не исправляет весь WP2 frame и не копирует
Prototype за счёт ослабления production validation. Это сознательная граница,
а не скрытое закрытие visual debt.

Внешний reviewer должен отдельно оценить visual parity. WP2 owner acceptance,
Profiles owner acceptance, ready-for-review и merge не заявляются.

## Git delivery

| Commit | Результат |
| --- | --- |
| `ddbd7ec7fcb166ffcd7dfbef8ee9da0838326076` | `feat: recompose guided profile editor` |
| `1f60e9d3fa6989e4c01fd03033a0f3d35f12668a` | `test: expand guided editor browser evidence` |
| `70e0b89b2152245b7b458d8fdbe7d8d12aff3519` | `docs: document guided editor candidate` |

Implementation, harness и основная документационная синхронизация отправлены
в `origin/c2-manual-acceptance-remediation`. Финальный delivery head совпадает
с remote; его точный SHA записан в external evidence provenance.

## Docs и PR

Синхронизированы:

- `docs/ai-handoff.md`;
- `roadmap/core/README.md`;
- `docs/inspection-profiles-ui.md`;
- `docs/guided-inspection-profiles.md`;
- этот implementation report.

Body существующего PR #130 обновлён после push документации и содержит
фактические проверки, evidence identity и явные границы acceptance. PR остаётся
draft и unmerged. WP4 Advanced не начат.
