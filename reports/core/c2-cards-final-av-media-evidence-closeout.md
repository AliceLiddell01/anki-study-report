# C2 / PR #130 — Cards 1:1 owner acceptance closeout

**Дата:** 2026-07-28
**Репозиторий:** `AliceLiddell01/anki-study-report`
**Base branch:** `core`
**Frozen PR base / merge-base:** `62cd4c1fc1dda6354f3e30cb3ae4aee5dfb4891f`
**Working branch:** `c2-manual-acceptance-remediation`
**Pull request:** `#130` — OPEN / DRAFT / UNMERGED
**Owner verdict:** `ACCEPT CARDS 1:1`
**Cards status:** ACCEPTED / COMPLETE / FROZEN

## 1. Итог

Route `#/cards` принят владельцем после независимой проверки production state и финального self-verified evidence artifact.

```text
Cards composition:                         PASS
Native template CSS / Night Mode:          PASS
AV tags and local media:                   PASS
Replay lifecycle and reset:                PASS
GIF live/deterministic proof:              PASS
Visible keyboard focus light/dark:         PASS
Focus screenshot evidence:                 PASS
Accessible-name localization:              PASS
Artifact self-verification:                PASS
Security/network isolation:                PASS

Cards technical blockers:                  NONE
Cards accessibility blockers:              NONE
Cards owner verdict:                       ACCEPTED
```

Финальная оценка принятого состояния:

```text
average:                    ≈9.3/10
minimum mandatory aspect:  8.7/10
```

## 2. Финальные принятые identities

```text
Cards production package source:
a162dde223b1bc40b6b0f566ae1fb5d665089359

Cards final evidence harness:
5487bb32d43b11bbe618ec45e1b0e1e365fabb39

Cards final artifact:
cards-final-av-media-fidelity-evidence.zip

artifact size:
56 358 736 bytes

artifact SHA-256:
539cf5f08c5f804fa6de3b87c87f0792e6d60777f0b40a9c413a0b912516dfc3

exact screenshots:
32

self-verification:
PASS

missing / unexpected / mismatches:
0 / 0 / 0
```

Exact package:

```text
anki_study_report.ankiaddon
size: 767 233 bytes
SHA-256: e01b9dd3e3277d9ff0cafb9ac3a298a1459118056f07834a171662c91ae79357
```

## 3. Exact card и media

```text
card ID: 1649481469689
word: 影
note type: Слова
```

```text
影.gif:
4a4d7f3ad02b029e00d96c28a7f1f4af245aab38858b2a00c9681fa0d2667bce

影.mp3:
f7ad06083e9911da13af81f52de3282166a666e452b690cebf4c4a0e45ea7dc7

影.png:
25cae7e94b0ba6fe12b7ecfea741aefbb2ea901d2b62c693c1cf015283a150e1
```

Exact browser result:

```text
status:                       PASS
scenarios:                    6
screenshots:                  32
external requests:            0
Inspection Profiles requests: 0
page errors:                  0
console errors:               0
failed requests:              0
```

## 4. Принятые browser/media proofs

Scenarios:

```text
wide-light
drawer-1024-light
expanded-light
wide-dark
drawer-1024-dark
expanded-dark
```

Replay/audio:

```text
first playback:                  PASS
second replay:                   PASS
second play event currentTime:   0
resetObserved:                   true
MP3 HTTP:                        200
rejected Promise handled:        true
```

GIF/image:

```text
source hash:                     PASS
HTTP:                            200
intrinsic geometry:              160×120
ImageDecoder frameCount:         154
live light frame difference:     PASS
live dark frame difference:      PASS
```

Focus/accessibility:

```text
visible keyboard focus light:    PASS
visible keyboard focus dark:     PASS
focus ring clipping:             none
localized aria-label:            Воспроизвести аудио
filename exposed in label:       no
```

## 5. Историческая evidence lineage

Промежуточный exact AV/media contour остаётся частью истории и не удаляется из commit/report lineage. Он был корректным для своего момента, но больше не является финальной accepted identity.

| Состояние | Package source | Harness | Artifact | Screenshots | Статус |
| --- | --- | --- | --- | ---: | --- |
| pre-accessibility evidence | `ec0c2cc48c6f9b2a5aa06469223ec4f73e1eb2e7` | `67aafd55120f8761e158ba838936d46881209f93` | `56 313 355` bytes / `3d8c9da5bd80bb48a6ea543bdba407cdc8751c708d7f9f990221d120f3516d8f` | 30 | historical / superseded |
| final owner-accepted evidence | `a162dde223b1bc40b6b0f566ae1fb5d665089359` | `5487bb32d43b11bbe618ec45e1b0e1e365fabb39` | `56 358 736` bytes / `539cf5f08c5f804fa6de3b87c87f0792e6d60777f0b40a9c413a0b912516dfc3` | 32 | ACCEPTED / CURRENT |

Основные production/evidence milestones:

```text
78dbcb031673f5504b22a7e57a14ed00570c7a3b  Cards AV/media production repair
3d4d0cca64d6f7ea7778d2684cea1287f3d7730a  AV/media regression coverage
67aafd55120f8761e158ba838936d46881209f93  historical exact E2E harness closure
a162dde223b1bc40b6b0f566ae1fb5d665089359  replay focus accessibility/localization production micro-pass
5487bb32d43b11bbe618ec45e1b0e1e365fabb39  final accepted evidence harness
```

## 6. Scope и frozen boundary

Owner verdict относится только к route `#/cards`. Он не означает принятие Inspection Profiles, всего PR #130, ready-for-review или merge.

Cards production заморожен. Без новой доказанной регрессии запрещено:

- менять Cards component composition;
- менять queue, rail, drawer или expanded answer;
- менять native card preview;
- менять AV/audio/GIF path;
- менять Shadow DOM;
- менять Cards styles ради Settings;
- отзывать owner acceptance;
- повторно запускать тяжёлый Cards real-Anki Docker E2E.

После shared Settings changes допустим только короткий Cards regression smoke, если изменение действительно затрагивает shared shell/styles.

## 7. Проверки acceptance evidence

Независимый owner review подтвердил:

```text
transport ZIP CRC:               PASS
final artifact ZIP CRC:          PASS
manifest declared/actual:        60 / 60
manifest missing:                0
manifest unexpected:             0
manifest size/hash mismatches:   0
SHA256SUMS mismatches:            0
exact browser scenarios:         6 / PASS
exact screenshots:               32
```

Текущий docs-only sync не меняет production, harness или artifact и не требует повторного Fast CI, frontend tests либо Docker E2E.

Актуальный reusable contract: [`../../docs/cards-exact-av-media-e2e.md`](../../docs/cards-exact-av-media-e2e.md).

## 8. Итоговая граница

```text
Cards: ACCEPTED / COMPLETE / FROZEN
Cards technical blockers: NONE
Cards accessibility blockers: NONE

Inspection Profiles implementation: NOT STARTED
Settings regression sweep: NOT STARTED
final verification for the full PR: NOT PERFORMED
PR #130: OPEN / DRAFT / UNMERGED
ready-for-review / merge / release / C3: NOT PERFORMED
```

Следующий implementation focus — отдельный этап Inspection Profiles. Его visual acceptance threshold:

```text
minimum acceptable result: 8.5/10
preferred target: 9.0/10 or higher
```
