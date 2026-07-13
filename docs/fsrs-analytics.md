# FSRS analytics

Stage 7 помещает read-only FSRS center внутрь Statistics. Canonical routes:
`#/stats/fsrs`, `/memory`, `/calibration`, `/steps`, `/simulator`. Отдельного
`#/fsrs` нет. Primary Statistics и sidebar FSRS остаются active; локальная nav
использует `aria-current`.

Initial `statisticsHub.fsrs` содержит только capability, configuration groups,
counts и limitations. Heavy operations идут через token-protected strict
`POST /api/statistics/fsrs/query` с union `overview|memory|calibration|steps|simulate`.
Frontend не передаёт search, SQL, params, protobuf или backend command.

Configuration identity включает preset ID, FSRS parameter fingerprint и
relevant scheduler fingerprint. Per-deck desired-retention overrides остаются
отдельными. Filtered deck не становится group. Memory сравнивает каждую карту
с её own target; calibration/simulator требуют compatible group. Выбор deck в
Steps расширяется до всех normal decks того же preset и явно объясняется.

Sources: Anki 26.05 `get_config('fsrs')`, deck config manager, stored native
memory states and native `simulate_fsrs_review`. Current memory distributions —
snapshot, не historical reconstruction. Calibration использует prior native
memory state in review data and bounded compatible-group events. Steps reports
observed scenarios; no automatic config editing.

Simulator inputs: retention 0.75–0.99, 90/180/365 days, additional new cards,
new/day, max reviews/day. Он запускается только кнопкой, memoized в SPA,
отбрасывает stale response и никогда не показывает Apply. Native deck options
action принимает только revalidated normal deck ID.

Security: loopback/token, body ceiling server, strict fields/ranges, bounded
responses, no raw revlog/card/note content, IDs/path/token/search not exposed,
no generic RPC and no mutation. Helper is not imported or required.

Visual contract reuses Statistics surfaces, KPI, semantic colors, visible
summary and data tables; light/dark and 125% are in stats E2E. Expensive
calibration/simulator are explicit. Response ceilings: 100/200/150/150/300 KB.

Non-goals: parameters/retention/steps editing, optimize/reschedule, per-card
D/S/R, Target R Browser column, forgetting curves, SxR, Time Machine and all
Helper scheduling tools.

## Measured Stage 7 fixture profile

Anki 26.05 synthetic fixture, 2026-07-13, compact JSON / wall time:

| Slice | Bytes | Time |
| --- | ---: | ---: |
| Initial capability (`/api/report` additive delta) | 1,906 | 2.44 ms |
| Overview | 1,541 | 2.37 ms |
| Memory | 1,926 | 2.09 ms |
| Calibration | 1,906 | 3.60 ms |
| Steps | 2,218 | 2.48 ms |
| Simulator, 90 days/current+hypothetical | 7,938 | 4.94 ms |

Capability performs two grouped collection queries. Memory adds one bounded
state query; Overview also adds one 30-day retention aggregate; Calibration
uses one bounded card-ID query plus native `card_stats` for eligible cards;
Steps adds one bounded event query; Simulator adds one deck count and two
native simulations. No route repeats a full raw revlog export.

Stage 6.5 production baseline was JS 855,510 / CSS 80,626 bytes. Stage 7 build
is JS 877,967 (+22,457) / CSS 82,311 (+1,685). No dependency or lazy chunk was
added. Times are diagnostics, not hard gates.
