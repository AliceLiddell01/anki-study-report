# C2 / PR #130 — финальное закрытие Cards AV/audio/media evidence

**Дата:** 2026-07-27  
**Репозиторий:** `AliceLiddell01/anki-study-report`  
**Base branch:** `core`  
**Frozen base SHA:** `62cd4c1fc1dda6354f3e30cb3ae4aee5dfb4891f`  
**Working branch:** `c2-manual-acceptance-remediation`  
**Production package source SHA:** `ec0c2cc48c6f9b2a5aa06469223ec4f73e1eb2e7`  
**Final E2E harness SHA:** `67aafd55120f8761e158ba838936d46881209f93`  
**Pull request:** `#130` — OPEN / DRAFT / UNMERGED  
**Статус:** финальный exact-card AV/audio/media gate завершён; технических AV/media blockers не осталось; формальный owner verdict `ACCEPT CARDS 1:1` ещё не зафиксирован; Inspection Profiles не начата.

## 1. Итог

Финальный repository-owned real-Anki contour для карточки `1649481469689` (`影`) завершился `PASS`.

```text
exact package validation                         PASS
committed real-deck import                       PASS
exact scheduling scenario                        PASS
native Anki render_output provenance             PASS
exact API AV/media contract                      PASS
standard browser smoke                           19/19 PASS
standard screenshots                             18/18
exact browser scenarios                          6/6 PASS
exact browser screenshots                        30
first and second replay                          PASS
currentTime reset before second play             PASS
local MP3/GIF/PNG HTTP                           200
GIF intrinsic geometry                           160×120
live GIF cross-scenario frame difference         PASS
deterministic GIF decoder frame count            154
external requests                                0
Inspection Profiles requests                     0
page errors / console errors / failed requests   0 / 0 / 0
final evidence self-verification                 PASS
missing / unexpected / mismatches                0 / 0 / 0
```

Final artifact:

```text
name: cards-final-av-media-fidelity-evidence.zip
size: 56 313 355 bytes
SHA-256: 3d8c9da5bd80bb48a6ea543bdba407cdc8751c708d7f9f990221d120f3516d8f
```

## 2. Scope

### В scope

- exact real-Anki proof для карточки `1649481469689`;
- question/answer AV-tag provenance;
- safe replay markup и local audio;
- реальный первый и второй playback;
- local media HTTP ledger;
- exact media filename/hash checks;
- wide, 1024 drawer и expanded answer в light/dark;
- GIF intrinsic geometry, live frame difference и deterministic frame extraction;
- self-verifying final evidence;
- reusable repository-owned Cards-only E2E harness;
- bounded failure diagnostics;
- documentation closeout.

### Вне scope

- изменения production Cards после уже принятого AV/media repair;
- Inspection Profiles implementation;
- Settings shared regression sweep;
- ready-for-review;
- merge PR #130;
- release;
- C3.

## 3. Exact identities

### 3.1. Package identity

```text
tested package source SHA:
ec0c2cc48c6f9b2a5aa06469223ec4f73e1eb2e7

anki_study_report.ankiaddon SHA-256:
ce2d1a612e803c86b38ddb5da0de81884b4e24b7c622714b371a1bf032020f02
```

Harness-only reuse был принят fail closed: package bytes не пересобирались после изменений только в `docker/anki-e2e/` и его focused contracts.

### 3.2. Harness identity

```text
final harness SHA:
67aafd55120f8761e158ba838936d46881209f93

reuse mode:
harness-only

Docker image:
sha256:2e952fb095fb554b0d4567027a86f475f4d9734892bd10f091a44bdd24ac0c43
```

### 3.3. Real-deck identity

```text
Words APKG:
docker/anki-e2e/fixtures/real-decks/words-n1.apkg

SHA-256:
78dfab9424fcdb1f5da4005f7e5a2789a04c13414c5477bc647069a06ad10a9b

imported:
718 Words notes/cards
133 Grammar notes/cards
70 Java notes/cards
921 total cards
2153 media files
```

### 3.4. Exact card

```text
card ID: 1649481469689
word: 影
note type: Слова

front:
影.gif
影.mp3
one replay control
one local audio element

back:
影.gif
影.png
replay remains available
```

Exact media hashes:

```text
影.gif:
4a4d7f3ad02b029e00d96c28a7f1f4af245aab38858b2a00c9681fa0d2667bce

影.mp3:
f7ad06083e9911da13af81f52de3282166a666e452b690cebf4c4a0e45ea7dc7

影.png:
25cae7e94b0ba6fe12b7ecfea741aefbb2ea901d2b62c693c1cf015283a150e1
```

## 4. Repository-owned E2E contour

Вместо продолжения внешних one-off runner’ов добавлен bounded scope `cards-exact-av-media` внутри существующего `docker/anki-e2e/`.

Добавлены:

```text
docker/anki-e2e/cards-exact-av-media-scenario.py
docker/anki-e2e/cards-exact-av-media-api.py
docker/anki-e2e/cards-exact-av-media-browser.mjs
docker/anki-e2e/cards-exact-av-media-evidence.py
docker/anki-e2e/cards-exact-av-media-failure.py
docker/anki-e2e/cards-exact-av-media-entrypoint.sh
docker/anki-e2e/run-cards-exact-av-media-host.sh
docker/anki-e2e/test_cards_exact_av_media_contract.py
```

`docker/anki-e2e/run-e2e.sh` получил только интеграцию нового targeted contour. Общий real-deck import, Anki startup, API/browser smoke, manifest и cleanup lifecycle сохранены.

## 5. Последовательность commits

| Commit | Назначение |
| --- | --- |
| `629ea8f84b2b804e256ee9f3f3b7a7da62594caa` | repository-owned exact Cards AV/media gate |
| `79a66ab095de795b6939731b46c931ce8187fc54` | exact replay class counting и root-safe cleanup |
| `cc302321f5e21b9360a7cb354a7ce293cf41a718` | exact-word geometry вместо чужого `(する)` oracle |
| `9d0260bc9eb00556c8613050b3c78c64233c10a2` | explicit `config.word` serialization в page context |
| `2286ab8705f8ec0db5c3965cf16f28aceef51b29` | type-aware media geometry, replay/GIF proof hardening |
| `07184f1ab801309d7f4acbb2662cb3602746a34c` | natural playback вместо artificial forward seek |
| `fbc20fa9e1ae60ea8a55335af6d628895d68d94d` | page-level GIF screenshot proof |
| `67aafd55120f8761e158ba838936d46881209f93` | cross-scenario GIF proof и robust failure arguments |

Production AV/media repair до E2E campaign уже находился в commits:

```text
78dbcb031673f5504b22a7e57a14ed00570c7a3b
3d4d0cca64d6f7ea7778d2684cea1287f3d7730a
```

## 6. Встретившиеся проблемы и решения

### 6.1. Historical artifacts ошибочно считались обязательными inputs

**Симптом:** preflight блокировал работу из-за отсутствия ZIP с historical именем, хотя canonical cache уже содержал извлечённый эквивалент и exact package.

**Причина:** поиск классифицировал только filename, а не состояние `ZIP / extracted directory / equivalent manifest`.

**Решение:** state-aware inventory:
- отдельно фиксировать ZIP;
- отдельно extracted tree;
- читать manifest/README/provenance без повторной распаковки;
- historical optional evidence не превращать в blocker final production gate.

### 6.2. Short bind syntax создавала каталог вместо отсутствующего файла

**Симптом:** container ожидал script file, но получал directory либо `No such file or directory`.

**Причина:** `-v`/short bind syntax может создать отсутствующий source как directory.

**Решение:** только explicit `--mount type=bind` после `require_file`/`require_dir`; отсутствующий source становится понятным pre-run error.

### 6.3. Regex считал prefix-классы как exact replay wrapper

**Симптом:** `wrapper=3, button=1, audio=1`.

**Причина:** regex для `asr-card-replay` также совпадал с `asr-card-replay-button` и `asr-card-replay-audio`.

**Решение:** разбор class attributes через `HTMLParser` и подсчёт exact class tokens.

### 6.4. Root-owned bind-mounted temporary files ломали cleanup

**Симптом:** host trap получал `Permission denied`.

**Причина:** основной container создавал временные files как root.

**Решение:** scoped cleanup только exact `mktemp` directory через pinned Docker image; без `sudo rm -rf`, без широкой очистки `/tmp`.

### 6.5. Harness унаследовал oracle `(する)` от другой карточки

**Симптом:** geometry failure на Words card `影`.

**Причина:** hard-coded grammar text не относился к exact card.

**Решение:** exact `.word-focus` с текстом `config.word`; example geometry требуется только на back side.

### 6.6. `config.word` не был передан в `page.evaluate()`

**Симптом:** корректный `.word-focus` существовал в DOM, но browser probe возвращал count `0`.

**Причина:** Node closure и browser page context изолированы; serialized argument содержал media names, но не `word`.

**Решение:** явно включить `word` в object argument и добавить source-contract regression.

### 6.7. GIF geometry ошибочно применялась к PNG

**Симптом:** back-side PNG отклонялся из-за отсутствия intrinsic `160×120`.

**Причина:** общий image helper использовал GIF oracle для всех images.

**Решение:** type-aware geometry:
- GIF: exact natural/computed `160×120`;
- PNG: положительная intrinsic/rendered geometry и сохранённый aspect ratio.

### 6.8. Artificial audio seek не работал в headless environment

**Симптом:** assignment `currentTime=0.3056` завершался `currentTime=0`.

**Причина:** forward seek зависел от фактического `seekable` range и media decoder state, хотя продукту нужен только reset к нулю.

**Решение:** дать первому playback естественно уйти от нуля, pause, затем доказать второй click через `play` event с `currentTime≈0`; `seekable`/`played` сохраняются только как diagnostics.

### 6.9. Canvas и повторные screenshots одного page context не давали разные GIF frames

**Симптом:** 60 samples, один hash, несмотря на animated resource.

**Причина:** browser screenshot/canvas sampling не гарантирует новый GIF frame на каждый вызов; выбранный observation method был хрупким.

**Решение:** сравнивать exact GIF crops, уже снятые в разных real production scenarios:
- одна theme;
- одинаковая округлённая rendered geometry;
- разные timestamps;
- минимум два разных SHA.

Light и dark groups независимо дали по два разных frames. `ImageDecoder` отдельно подтвердил `frameCount=154`.

### 6.10. String-based focused test блокировал правильный runtime refactor

**Симптом:** runtime использовал локальный alias `proof`, test искал старый literal `window.__asrReplayProof?.playCalls >= 2`.

**Причина:** test проверял incidental implementation string.

**Решение:** обновить structural contract на фактические markers, не возвращая старую запись.

### 6.11. Atomic file replacement снял executable bit

**Симптом:** `cards-exact-av-media-browser.mjs` менялся `100755 → 100644`.

**Причина:** temporary file получил default mode перед `os.replace()`.

**Решение:** patcher явно восстанавливает mode; focused test проверяет `os.X_OK`.

### 6.12. Failure packager передавал пустой optional `--token`

**Симптом:** после browser failure диагностический ZIP не создавался из-за argparse error.

**Причина:** host runner всегда добавлял `--token "$token"`.

**Решение:** собирать argument array и добавлять `--token` только при непустом значении; отдельный empty-token smoke подтверждает ZIP creation.

## 7. Финальные browser proofs

### 7.1. Scenarios

```text
wide-light
drawer-1024-light
expanded-light
wide-dark
drawer-1024-dark
expanded-dark
```

### 7.2. Replay

```text
first playback:
play event PASS
playing event PASS
play() Promise PASS

second playback:
natural currentTime before click > 0
play event currentTime = 0
playing event PASS
resetObserved = true

rejected play() Promise:
handled without page error
```

### 7.3. GIF

```text
source hash: exact
HTTP: 200
intrinsic geometry: 160×120
ImageDecoder frameCount: 154
deterministic frame 0: saved
```

Cross-scenario proof:

```text
light:160x120
drawer-1024-light vs expanded-light
elapsed: 2516 ms
unique hashes: 2

dark:160x120
drawer-1024-dark vs expanded-dark
elapsed: 2552 ms
unique hashes: 2
```

### 7.4. Security/network

```text
external requests: 0
Inspection Profiles requests: 0
page errors: 0
console errors: 0
failed requests: 0
```

## 8. Verification

### Focused

```text
Python:
48 passed

Node:
16 passed

bash syntax:
PASS

Node syntax:
PASS

Python compile:
PASS

git diff --check:
PASS

failure bundle empty-token smoke:
PASS
ZIP CRC:
PASS
```

### Real Anki

```text
Anki: 26.05
mode: standard
scope: cards-exact-av-media
restart: skipped by targeted-scope policy
standard browser plan: 19/19 PASS
standard screenshots: 18/18
exact browser: PASS
exact scenarios: 6
exact screenshots: 30
final artifact self-verification: PASS
```

## 9. Что не запускалось

| Проверка/действие | Причина |
| --- | --- |
| новый Fast CI | изменения после package commit были harness-only и прошли fail-closed reuse validation |
| `standard/full` | риск был ограничен targeted Cards exact AV/media contour; общий production/startup/restart lifecycle не изменялся |
| restart | targeted scope не проверял persistent state |
| Inspection Profiles | отдельный owner checkpoint; автоматический переход запрещён |
| ready-for-review | не запрошено |
| merge | отдельное решение владельца |
| release/C3 | вне scope |

## 10. Stop-loss и reusable lessons

Следующие правила становятся обязательными для похожих задач:

1. Один repository-owned contour вместо цепочки one-off runners.
2. Preflight собирает все blockers и различает missing/ZIP/extracted/wrong-type.
3. Heavy gate запускается только после focused tests.
4. После failure сначала изучаются report/artifact/source, а не делается blind rerun.
5. Browser oracle должен соответствовать exact entity и exact side.
6. Browser-context dependencies передаются явно.
7. Geometry assertions являются media-type-aware.
8. Playback доказывается observable events, а не искусственным seek.
9. Dynamic image proof отделяется от deterministic frame proof.
10. Failure diagnostics тестируются отдельно, включая отсутствие optional values.
11. File mode входит в contract для executable harness files.
12. После PASS неизменную package/harness pair не повторять.

Актуальный reusable contract: [`../../docs/cards-exact-av-media-e2e.md`](../../docs/cards-exact-av-media-e2e.md).

## 11. Итоговая граница

```text
Cards native template CSS fidelity: PASS
Cards AV/audio/media production repair: PASS
Cards exact real-Anki evidence: PASS
Cards exact evidence artifact: SELF-VERIFIED
Cards technical AV/media blockers: NONE

Cards formal owner verdict: PENDING
Inspection Profiles implementation: NOT STARTED
Settings regression sweep: NOT STARTED
PR #130: OPEN / DRAFT / UNMERGED
merge/release/C3: NOT PERFORMED
```

Технических оснований для `REVISE CARDS` по AV/audio/media больше нет. Формальный следующий owner action остаётся отдельным:

```text
ACCEPT CARDS 1:1
```
