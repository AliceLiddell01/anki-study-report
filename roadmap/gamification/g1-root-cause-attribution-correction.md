# G1.2a — Attribution contract and evidence correction

## Status

`G1.2a correction — Complete`

`G1.3 — Next / Ready`

`candidate selected — NO`

`reward formula changed — NO`

`scheduler semantics changed — NO`

`production integration — PROHIBITED`

## Canonical input and artifact

- canonical input: `c83ab1ad015d6a013b0d8d1c2da659df507a2771`;
- preserved artifact: `8447755442`, run `29705334586`, job `88241257488`;
- rerun artifact SHA-256: `965700e8f78ff59581d4fa849c551abfe229bc37f6fcc9f72ec892a5143ce550`;
- manifest SHA-256: `60011077cc4301ef479ffe8f268926d02deece592159c1bf2e1fc398f91fe8b4`;
- manifest payload: 43 files / 28248999 bytes.

## Reproduced audit findings

1. The previous scheduler identity test compared the same object with itself.
2. Policy summaries and root-answer evidence were not strict enough.
3. Shares used absolute values after signed aggregation, allowing cancellation.
4. Several answers described fields without stating the supported conclusion.

## Corrections

- independent plain, direct-observer and attribution scheduler identities;
- mutation detection and pure fixed-trajectory counterfactual checks;
- strict Draft 2020-12 policy and tagged root-answer schemas;
- cell-level absolute contribution shares;
- direct conclusions plus explicit uncertainty boundaries in all fourteen answers.

## Corrected contribution semantics

```text
component share = sum(abs(component per retention cell)) / sum(abs(all components per retention cell))
window share = sum(abs(window per retention cell)) / sum(abs(all windows per retention cell))
```

- `memory_main`: 0.455223085523808;
- `post_transition`: 0.856512132319511;
- Challenge direction-consistent across all retention cells: `false`.

## Unchanged scientific and decision state

- six canonical cells unchanged;
- three group outcomes unchanged;
- overall gate remains `FAIL`;
- classification remains `ROOT_CAUSE_PARTIALLY_LOCALIZED` / `MEDIUM`;
- candidate selected: `false`;
- production approved: `false`;
- reward and scheduler semantics unchanged.

## Verification

- focused tests: 117 passed;
- full research package: 846 passed;
- artifact hash/manifest/strict JSON audit: PASS;
- schema self-check and corrected evidence validation: PASS;
- frozen blob audit: PASS;
- exact seven-path diff and security/whitespace audit: PASS.

## Files changed

- `research/gamification-sim/src/gamification_sim/diagnostic_attribution.py`
- `research/gamification-sim/tests/test_diagnostic_attribution.py`
- `research/gamification-sim/schemas/review-cycling-attribution-v1.schema.json`
- `research/gamification-sim/evidence/g1.2-root-cause-attribution-v1.json`
- `roadmap/gamification/g1-root-cause-attribution.md`
- `roadmap/gamification/g1-root-cause-attribution-correction.md`
- `roadmap/gamification/README.md`

## What was not run

Docker E2E, real-Anki E2E, dashboard/frontend tests, packaging, release and standalone Rust tests were omitted because this checkpoint changes isolated research Python, tests, schema, evidence and roadmap records only.

## Limitations

The trace is synthetic and post-hoc. It does not prove human behavior, learning effectiveness or one unique corrective formula. No coefficient or candidate was tested.

## Readiness

G1.3 may define bounded hypotheses prospectively. G1.3 was not started.
