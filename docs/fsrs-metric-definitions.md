# FSRS metric definitions

Calculation version: `fsrs-analytics-v1.0`.

| Metric | Definition / source | Included, scope, aggregation, unit | Sample / missing / limitation |
| --- | --- | --- | --- |
| Estimated remembered | Sum of current native retrievability | reviewed cards with valid state; scope/group sum; cards | ≥1; null/0 state becomes insufficient; expectation, not guaranteed list |
| Average retrievability | Mean current probability of recall | same cards; weighted by card; ratio | ≥1; snapshot only |
| Median stability | Median native Stability | valid states; days | ≥1; Stability is time from 100% to 90%; log buckets |
| Difficulty distribution | Counts of native Difficulty 1–10 | valid states; card counts/share | ≥1; model property, not material quality verdict |
| Actual retention | Successful qualifying answers / all qualifying | Again fail; Hard/Good/Easy pass; compatible group; ratio | 100 preliminary, 400 sufficient; monthly periods preferred |
| Target retention | Default plus per-deck override | each card/deck own target; ratio/range | config required; never fixed global 90% |
| Calibration bins | Mean predicted R vs observed recall per central R bucket | compatible parameters, bounded period; ratio/count | bin 30 preliminary/100 sufficient; sparse bin visible, not interpreted |
| Steps scenarios | first Again/Hard/Good, Again→Good, Good→Again, relearning | same preset, bounded event history; count/rate/delay seconds | per scenario 30/100; no pooled confidence |
| Recommended step range | Quartile envelope of observed successful delays | key scenarios in same preset; seconds | key scenarios ≥100; observational, no optimal-minute claim/no Apply |
| Simulated reviews/day | Mean native daily review counts | selected compatible group and inputs; reviews/day | valid native config/state; estimate |
| Simulated minutes/day | Mean native daily time cost / 60 | same; minutes/day | native response required; estimate |
| Simulated peak | Maximum native daily review count | horizon; reviews | native response required |
| Simulated backlog | Sum above supplied daily cap in returned series | horizon; reviews | bounded proxy; may be zero when native simulator already applies cap |

Memory availability depends on valid current states. Calibration and Steps have
separate central thresholds. Simulator sufficiency is configuration validity
and native model availability, not a statistical confidence interval.
