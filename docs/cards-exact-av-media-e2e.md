# Cards exact AV/audio/media E2E

**Статус:** актуальный специализированный runbook
**Снимок:** 2026-07-27
**Scope:** `docker/anki-e2e/`, exact production Cards AV/media evidence

Этот документ описывает reusable contract для exact-card AV/audio/media proof. Историческая последовательность конкретного закрытия хранится в [`../reports/core/c2-cards-final-av-media-evidence-closeout.md`](../reports/core/c2-cards-final-av-media-evidence-closeout.md).

## 1. Когда использовать

Использовать этот contour, когда нужно доказать на real Anki:

- native question/answer render;
- safe replay markup;
- local audio playback;
- local GIF/PNG delivery;
- exact media identity;
- preview/drawer/expanded geometry;
- live GIF animation;
- отсутствие external requests и security regressions.

Он не является обычным debugger и не заменяет focused tests.

## 2. Три независимые identities

Всегда фиксируются отдельно:

```text
package identity
→ tested source SHA
→ .ankiaddon SHA-256/size

harness identity
→ current checkout SHA
→ changed harness paths/hashes
→ reuse mode

evidence identity
→ output path
→ artifact SHA-256/size
→ self-verification result
```

Разные package/harness SHA допустимы только после fail-closed harness-only reuse validation.
Для локального `source-build` package SHA вычисляется из фактически собранного
архива внутри contour, а provenance явно помечается `source-build`; Fast CI
metadata в этом режиме не подделывается.

## 3. State-aware preflight

Preflight не должен останавливаться на первой бытовой ошибке. За один read-only проход он классифицирует:

```text
repository missing
wrong repository
wrong branch
wrong HEAD
dirty/staged paths
tool missing
Docker daemon unavailable
file missing
path exists as directory instead of file
ZIP only
already extracted directory
multiple candidates
SHA mismatch
insufficient disk
```

Historical evidence не является обязательным input только из-за совпадения старого filename. Проверяется фактическое содержимое, manifest и provenance.

ZIP inventory сначала выполняется без extraction. Повторная распаковка существующего canonical tree запрещена без необходимости.

## 4. Repository-owned contour

Exact gate должен быть частью существующего `docker/anki-e2e/`, сохраняя:

- committed APKG manifest/checksums;
- real importer;
- collection inventory;
- deterministic anchors/scenarios;
- Anki startup;
- standard API smoke;
- standard browser smoke;
- artifact manifest;
- scoped cleanup.

Нельзя создавать параллельную E2E-систему или продолжать лестницу внешних runner’ов.

## 5. Strict host paths и mounts

До Docker:

```text
require_file
require_dir
exact SHA checks
output empty/nonexistent guard
```

Для bind mounts использовать explicit:

```text
--mount type=bind,source=<host>,target=<container>
```

Short `-v`/volume syntax не используется для exact file inputs: отсутствующий source может превратиться в directory и скрыть реальную ошибку.

Container-created root-owned temp data удаляется только scoped cleanup для exact `mktemp` directory. Запрещены широкие `sudo rm -rf`, cleanup всего `/tmp` и удаление непроверенного symlink path.

## 6. Exact HTML и side-aware contract

Class counts выполняются по exact tokens, а не по regex prefix.

```text
asr-card-replay
asr-card-replay-button
asr-card-replay-audio
replay-button
```

Для каждого side задаётся отдельный contract:

```text
front:
replay + audio + GIF + exact word focus
answer-only PNG отсутствует

back:
replay + audio + GIF + PNG + exact word focus
example geometry присутствует, если она относится к шаблону
```

Нельзя переносить text oracle от другой карточки или note type.

## 7. Browser context serialization

Код внутри `page.evaluate()` исполняется в page context. Любое внешнее значение передаётся явно через serializable argument.

Проверять source contracts на наличие необходимых keys:

```text
word
gif filename
mp3 filename
png filename
mode/side
```

Нельзя рассчитывать, что Node closure автоматически доступна в browser context.

## 8. Media geometry

Geometry assertions являются type-aware.

### GIF

Для exact template разрешён жёсткий oracle, если он доказан source evidence:

```text
naturalWidth
naturalHeight
computed width/height
rendered rect
```

### PNG

Без отдельного exact oracle проверяются:

```text
complete=true
positive intrinsic dimensions
positive computed dimensions
positive rendered rect
preserved aspect ratio
```

GIF dimensions нельзя автоматически применять к PNG.

## 9. Replay proof

Replay доказывается observable behavior:

1. первый click;
2. `play()` вызван;
3. Promise fulfilled;
4. `play` event;
5. `playing` event;
6. playback естественно ушёл от нуля;
7. pause;
8. второй click;
9. второй `play` event наблюдается около `currentTime=0`;
10. rejected `play()` Promise обработан без page error.

Artificial forward seek не является обязательной precondition. `seekable` и `played` ranges сохраняются как diagnostics, но отсутствие forward-seek capability не является product defect.

## 10. GIF proof

Live animation и deterministic decoding — разные доказательства.

### Deterministic

```text
exact source SHA
ImageDecoder frameCount > 1
decode(frameIndex=0)
saved fixed frame
```

### Live production

Сохраняется exact GIF crop из каждого real production scenario. Сравниваются только captures с:

```text
same theme
same rounded rendered dimensions
different timestamps
```

PASS требует минимум два разных SHA в одной comparison group.

Повторные screenshots одного page context или canvas sampling не считаются надёжным единственным proof: browser capture API не обещает новый GIF frame на каждый вызов.

## 11. Responsive UX screenshot matrix

Тот же exact real-card contour является canonical owner-facing источником Cards
screenshots. Отдельный mock/dev capture не заменяет эту матрицу.

Основная матрица сохраняется в
`screenshots/cards/exact-av-media/responsive-matrix/`:

```text
cards-page-full-hd-1920x1080-light.png
cards-page-qhd-2560x1440-light.png
cards-page-4k-uhd-3840x2160-light.png
```

Контракт каждого кадра:

- реальная рабочая карточка из committed APKG;
- `deviceScaleFactor=1`;
- viewport-only capture (`fullPage=false`) без browser zoom и post-capture resize;
- точный viewport из имени файла;
- закрыты уведомления, filters, coverage и modal;
- document не превышает viewport по ширине или высоте;
- Cards workspace bounded, queue и inspector имеют одинаковую высоту;
- template-owned Anki background заполняет native preview frame по ширине и высоте.

Дополнительные состояния сохраняются только для primary `1920x1080` в
`interaction-gallery/1920x1080/`:

```text
01-dismissible-warnings-1920x1080-light.png
02-filters-open-1920x1080-light.png
03-coverage-open-1920x1080-light.png
04-expanded-answer-close-up-1920x1080-light.png
05-refresh-notification-close-up-1920x1080-light.png
06-native-card-fill-1920x1080-dark.png
```

Последний dark capture и light matrix дополнительно закрепляют отсутствие
dashboard-colored боковых полей внутри native card frame.

## 12. Failure diagnostics

Failure packager обязан работать даже когда token не был восстановлен.

Optional arguments формируются как array и добавляются только при непустом значении.

Failure ZIP содержит:

- safe README;
- first exact problem;
- process/container logs;
- exact reports;
- screenshot/trace при наличии;
- inventory;
- redacted paths/tokens;
- CRC-valid archive.

Отдельный focused smoke должен вызвать packager без token и проверить `unzip -t`.

## 13. Focused minimum

Перед каждым real-Anki run:

```text
bash -n changed shell files
python -m py_compile changed Python files
node --check changed MJS files
focused exact AV/media pytest
browser progress/report Node tests
harness reuse tests
screenshot contract tests
git diff --check
executable mode checks
failure packager smoke
```

String tests должны проверять contract markers, а не incidental formatting или локальное имя переменной.

## 14. Heavy-run policy

```text
focused checks
→ commit/push
→ exact package/harness reuse validation
→ один targeted cards-exact-av-media run
→ artifact self-verification
→ stop
```

После failure:

```text
first failed assertion
→ exact report
→ screenshots/media ledger
→ current source
→ one concrete fix
```

Blind rerun запрещён. После успешной неизменной package/harness pair повтор не нужен.

## 15. Acceptance checklist

```text
[ ] exact repository/branch/local+remote HEAD
[ ] clean tree or exact expected dirty set
[ ] exact package SHA
[ ] committed APKG checksums
[ ] exact card ID/note type/word
[ ] question/answer AV tags
[ ] exact class-token counts
[ ] local media HTTP 200
[ ] media SHA-256
[ ] side-aware geometry
[ ] first replay play/playing
[ ] second replay reset proof
[ ] rejected play Promise handled
[ ] six light/dark scenarios
[ ] live GIF comparison group with >=2 hashes
[ ] deterministic GIF frameCount > 1
[ ] zero external/profile/error requests
[ ] final ZIP self-verification
[ ] no unrelated dirty paths
```

## 16. External references

- Playwright `page.screenshot()` — clip и animation behavior: <https://playwright.dev/docs/api/class-page#page-screenshot>
- Playwright evaluation contexts: <https://playwright.dev/docs/evaluating>
- Docker bind mounts: <https://docs.docker.com/engine/storage/bind-mounts/>
- `HTMLMediaElement.currentTime`: <https://developer.mozilla.org/en-US/docs/Web/API/HTMLMediaElement/currentTime>
- `HTMLMediaElement.seekable`: <https://developer.mozilla.org/en-US/docs/Web/API/HTMLMediaElement/seekable>
- `seeked` event: <https://developer.mozilla.org/en-US/docs/Web/API/HTMLMediaElement/seeked_event>
- `ImageTrack.frameCount`: <https://developer.mozilla.org/en-US/docs/Web/API/ImageTrack/frameCount>
- Python `zipfile`: <https://docs.python.org/3/library/zipfile.html>
