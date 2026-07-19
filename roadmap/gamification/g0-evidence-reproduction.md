# G0.7 — Canonical Windows evidence reproduction

## Status

`COMPLETE_CURRENT_EVIDENCE_REPRODUCED_WITH_OPEN_GAP`

## Canonical, execution and result refs

- canonical input: `9716b3f98bc4a975031a078f42e38a7d8fb109a6`;
- execution branch: `temp/g0-7-windows-execution`;
- successful execution commit: `eea4c24b178259bf611a317e115bf6d8f6ed9577`;
- clean result branch: `temp/g0-7-windows-result`.

The execution branch is temporary and is not merged into `gamification`.

## Windows runner and environment

- runner label: `windows-2025`;
- image: `windows-2025-vs2026` / `20260714.173.1`;
- OS: Microsoft Windows Server 2025, build 10.0.26100, AMD64;
- Python: CPython 3.11.9 x64;
- wheelhouse: 17 exact SHA-256 locked wheels;
- fresh offline venv replay: PASS;
- regular non-editable package install and `pip check`: PASS;
- Rust: `1.97.1-x86_64-pc-windows-msvc`;
- Cargo locked online/offline metadata: PASS.

The package was installed from a temporary copy, preserving the canonical source
tree byte-for-byte.

## Artifact

- workflow run: `29695312258`;
- job: `88214940938`;
- artifact ID: `8444920908`;
- artifact name: `g0-7-windows-evidence-eea4c24b178259bf611a317e115bf6d8f6ed9577`;
- API/ZIP digest: `sha256:0530a2d63d37cfc00c946b85b17edf05e38d6e1bcb4f13fa2825282b702687ae`;
- compressed size: 507574 bytes;
- payload: 138 files / 5893935 bytes;
- manifest digest: `33f3bfb145ba6dfe1252cb68612ffcb4f63dfae2a1f18553474da0e5246f5150`;
- effective expiry: `2026-08-02T16:40:11Z`;
- workflow conclusion: SUCCESS;
- independent audit: PASS.

Independent verification checked safe extraction, every manifest size/hash,
strict JSON and CSV parsing, required raw paths, input immutability, same-seed
byte equality, secondary-seed difference, security sanitization and an
independent cross-horizon recomputation.

## Sweep

- evaluated: 30;
- PASS: 30;
- Pareto states: 14;
- deterministic digest: `1a691b15c813088af0779eff4979e2052c9b86096484051131d9ea2a7d946db3`.

## Sensitivity

- 13 grids / 63 points;
- complete evidence: 63;
- invariant PASS: 63;
- quantitative PASS: 53;
- expected crossings: 10;
- deterministic digest: `f092ad834d4996f5d79f2cb1f30057b409c8df66821cedcdba653dc02a4d6639`.

## Population

| Mode | Persona-days | Digest |
|---|---:|---|
| development | 480 | `e533ee5d53093594982acdfddeac2522e6f5cf02ac4bedbce535addbe0afeddd` |
| standard | 584000 | `95cdfce9b84b46afd4e47849b6f52a62e7fae4211dabf116a217beb6cf611b92` |
| long smoke | 112 | `1d2d8c5a12c68232e1c53092bbabb3ced4f92d083c5989720c1232bd2956cd9d` |

Every canonical pair is identical. Secondary development produced
`c05f34296cc52d72210dce602a8182865fcd422aa1e7983a088e4b4a496c2a24`, which differs from the canonical seed.

## Longitudinal — 30 days

- candidates: 4;
- policies: 9;
- results: 36;
- reviews: 1484;
- trajectory: `472dbff99545a9881c7dff3538a1ff486959de838a1943e8df44c51ff033957c`;
- final cohort: `b6ef5f16de626f73a160f2c637e26a081db119343cde43f6844eab7685d26ed0`;
- report: `2c45fea0f6281dbcb3d90c3702478b0a0b56bc33990ace78b41256a87b137b72`.

## Longitudinal — 90 days

- candidates: 14 from the current Windows sweep Pareto output;
- policies: 9;
- results: 252;
- reviews: 31892;
- trajectory: `3f3d70e60a31ecef39da0db3803a9a7b0c5ac70a3f919bfe88fe901d3dda5997`;
- final cohort: `4ad6d255e3260767ad527a4038c79bcc6fef8cf454959abc502fc0f11c2c893d`;
- report: `b2ce8e805dbc9a5fc765dbc57c064ed076951238c5fad2f52294aa264823438c`.

## Longitudinal — 365 days

- candidate: `R-CURRENT`;
- policies: 7 exact required policies;
- results: 14;
- reviews: 2189;
- trajectory: `4b38ee3dc2922c2dea92d3b099d81274c173e36dec906ab98c725679ed5ac48a`;
- final cohort: `daedc0f96737836a6d575599d7f030cd00dff9817c5d831c32309914f54441c9`;
- report: `355f883d1fd183ca4cec6cba153731365d24332779b1d43aeb82a8f6b01ff64f`.

## Same-seed and secondary-seed checks

All required run1/run2 raw trees are byte-identical. The secondary population
development and longitudinal development trajectories are valid and different.

## Cross-horizon gate

| Comparison | Replica | 90-day | 365-day | Delta | 365 endpoint | Growth |
|---|---:|---:|---:|---:|---|---|
| `intentional-backlog` | 0 | -0.7877% | 0.0563% | 0.8441% | PASS | grew |
| `intentional-backlog` | 1 | -0.0443% | -1.5675% | -1.5231% | PASS | did not grow |
| `retention-high-cycle` | 0 | -0.3774% | 1.7402% | 2.1176% | PASS | grew |
| `retention-high-cycle` | 1 | -1.0045% | 0.1544% | 1.1588% | PASS | grew |
| `retention-low-cycle` | 0 | 1.0981% | 1.1624% | 0.0643% | PASS | grew |
| `retention-low-cycle` | 1 | 0.4017% | 1.3605% | 0.9588% | PASS | grew |

Both retention-cycle groups fail systematic growth while all 365-day endpoints
remain below 3%. Intentional backlog passes.

## Historical reconciliation

| Claim | Historical | Canonical Windows | Linux support | Class | Decision impact |
|---|---|---|---|---|---|
| Corrected sweep semantic result | {"evaluated": 30, "paretoCount": 14, "pass": 30} | {"evaluated": 30, "paretoCount": 14, "pass": 30} | {"evaluated": 30, "paretoCount": 14, "pass": 30} | EXACT_MATCH | Confirms the current sweep selection used for calibration-90. |
| Corrected sweep historical digest | "16ce6388691f4645fd77ead50f548c3f0985224fa0813f2f1fd6ebee99eeeeb1" | "1a691b15c813088af0779eff4979e2052c9b86096484051131d9ea2a7d946db3" | "9327de27502e22198e9b876f950f233fba19d4f6b1635e040b8a7bf9017e785c" | NOT_COMPARABLE | No semantic drift inferred; historical digest identity is not claimed. |
| Sensitivity semantic result | {"complete": 63, "crossings": 10, "grids": 13, "invariantPass": 63, "points": 63, "quantitativePass": 53} | {"complete": 63, "crossings": 10, "grids": 13, "invariantPass": 63, "points": 63, "quantitativePass": 53} | {"complete": 63, "crossings": 10, "grids": 13, "invariantPass": 63, "points": 63, "quantitativePass": 53} | EXACT_MATCH | No sensitivity evidence gap was introduced by recovery. |
| Sensitivity historical digest | "2ebc1c182fb6075f441a473e842ad198d80977e6128c82ce9427d0a72c4dd682" | "f092ad834d4996f5d79f2cb1f30057b409c8df66821cedcdba653dc02a4d6639" | "78f4c31b69166c59eb49f4beaab67bde7bb684ac0686ba7cf30b115b887f49e0" | NOT_COMPARABLE | Current reproducibility is established without claiming historical digest equivalence. |
| Population counts | {"development": 480, "longSmoke": 112, "standard": 584000} | {"development": 480, "longSmoke": 112, "standard": 584000} | {"development": 480, "longSmoke": 112, "standard": 584000} | EXACT_MATCH | Population workload coverage is reproduced. |
| Population historical standard digest | "a7823e39eb85c5b39f37266ad4b7057d12febe54d4c7478e06d9c911425703c4" | "95cdfce9b84b46afd4e47849b6f52a62e7fae4211dabf116a217beb6cf611b92" | "95cdfce9b84b46afd4e47849b6f52a62e7fae4211dabf116a217beb6cf611b92" | NOT_COMPARABLE | Cross-platform current behavior agrees; historical digest identity is not claimed. |
| Longitudinal semantic counts | {"calibration365": [14, 2189], "calibration90": [252, 31892], "development": [36, 1484]} | {"calibration365": [14, 2189], "calibration90": [252, 31892], "development": [36, 1484]} | {"calibration365": [14, 2189], "calibration90": [252, 31892], "development": [36, 1484]} | EXACT_MATCH | The persistent-card evidence contour is reproduced. |
| Longitudinal historical digests | "Only truncated historical trajectory/final/report digests are available." | {"calibration365": {"candidateCount": 1, "finalCohortDigest": "daedc0f96737836a6d575599d7f030cd00dff9817c5d831c32309914f54441c9", "horizonDays": 365, "policyCount": 7, "repeat": "IDENTICAL", "reportDigest": "355f883d1fd183ca4cec6cba153731365d24332779b1d43aeb82a8f6b01ff64f", "resultCount": 14, "reviewCount": 2189, "trajectoryDigest": "4b38ee3dc2922c2dea92d3b099d81274c173e36dec906ab98c725679ed5ac48a"}, "calibration90": {"candidateCount": 14, "finalCohortDigest": "4ad6d255e3260767ad527a4038c79bcc6fef8cf454959abc502fc0f11c2c893d", "horizonDays": 90, "policyCount": 9, "repeat": "IDENTICAL", "reportDigest": "b2ce8e805dbc9a5fc765dbc57c064ed076951238c5fad2f52294aa264823438c", "resultCount": 252, "reviewCount": 31892, "trajectoryDigest": "3f3d70e60a31ecef39da0db3803a9a7b0c5ac70a3f919bfe88fe901d3dda5997"}, "development": {"candidateCount": 4, "finalCohortDigest": "b6ef5f16de626f73a160f2c637e26a081db119343cde43f6844eab7685d26ed0", "horizonDays": 30, "policyCount": 9, "repeat": "IDENTICAL", "reportDigest": "2c45fea0f6281dbcb3d90c3702478b0a0b56bc33990ace78b41256a87b137b72", "resultCount": 36, "reviewCount": 1484, "trajectoryDigest": "472dbff99545a9881c7dff3538a1ff486959de838a1943e8df44c51ff033957c"}} | "Linux trajectory/final/report digests differ from current Windows for persistent-card runs." | NOT_COMPARABLE | Semantic claims are compared separately from digest identity. |
| Same-seed replay | "Repeated fixed-config/seed digests identical." | "PASS for sweep, sensitivity, every population mode and every longitudinal mode; raw files are byte-identical within each required pair." | "PASS in the normalized supporting run." | EXACT_MATCH | Current deterministic evidence baseline established. |
| Secondary-seed behavior | "Different seed changes trajectory under the same contract." | {"longitudinalDevelopment": "DIFFERENT", "populationDevelopment": "DIFFERENT"} | {"longitudinalDevelopment": "DIFFERENT", "populationDevelopment": "DIFFERENT"} | EXACT_MATCH | The simulator is deterministic by seed rather than seed-insensitive. |
| Baseline preservation | "Baseline ratio 1.0 within floating tolerance; zero suppression events." | "PASS across all 302 policy-result rows; zero suppression events." | "PASS in supporting normalized evidence." | EXACT_MATCH | The open cycling result is not caused by honest baseline suppression. |
| Cross-horizon per-replica values and group gates | {"intentionalBacklog": {"endpoint": "PASS", "growth": "PASS"}, "retentionHigh": {"endpoint": "PASS", "growth": "FAIL"}, "retentionLow": {"endpoint": "PASS", "growth": "FAIL"}} | {"cells": [{"advantage365": 0.0005632323390294677, "advantage90": -0.00787729417762993, "comparison": "intentional-backlog", "delta365Minus90": 0.008440526516659398, "endpoint365Pass": true, "endpoint90Pass": true, "grew": true, "replica": 0}, {"advantage365": -0.015674928856293055, "advantage90": -0.00044346058049055326, "comparison": "intentional-backlog", "delta365Minus90": -0.015231468275802502, "endpoint365Pass": true, "endpoint90Pass": true, "grew": false, "replica": 1}, {"advantage365": 0.01740169409234382, "advantage90": -0.0037743285774081313, "comparison": "retention-high-cycle", "delta365Minus90": 0.02117602266975195, "endpoint365Pass": true, "endpoint90Pass": true, "grew": true, "replica": 0}, {"advantage365": 0.0015438826586415418, "advantage90": -0.010044592850379412, "comparison": "retention-high-cycle", "delta365Minus90": 0.011588475509020955, "endpoint365Pass": true, "endpoint90Pass": true, "grew": true, "replica": 1}, {"advantage365": 0.011623868729051332, "advantage90": 0.010980579297321715, "comparison": "retention-low-cycle", "delta365Minus90": 0.0006432894317296173, "endpoint365Pass": true, "endpoint90Pass": true, "grew": true, "replica": 0}, {"advantage365": 0.013604965651852367, "advantage90": 0.004017396619023545, "comparison": "retention-low-cycle", "delta365Minus90": 0.009587569032828822, "endpoint365Pass": true, "endpoint90Pass": true, "grew": true, "replica": 1}], "groups": [{"comparison": "intentional-backlog", "endpoint365Pass": true, "replicas": 2, "status": "PASS", "systematicGrowth": false}, {"comparison": "retention-high-cycle", "endpoint365Pass": true, "replicas": 2, "status": "FAIL", "systematicGrowth": true}, {"comparison": "retention-low-cycle", "endpoint365Pass": true, "replicas": 2, "status": "FAIL", "systematicGrowth": true}], "method": "365-day unexplained advantage must remain <=3%; retention cycling must not increase in every matched replica", "status": "FAIL"} | {"intentionalBacklog": {"endpoint": "PASS", "growth": "PASS"}, "retentionHigh": {"endpoint": "PASS", "growth": "FAIL"}, "retentionLow": {"endpoint": "PASS", "growth": "FAIL"}} | EXACT_MATCH | The open cycling gap is reproduced and handed to G1. |
| Candidate decision | "No recommended candidate; R-CURRENT remains a regression reference." | "No recommended candidate; R-CURRENT remains a regression reference." | "No recommended candidate; R-CURRENT remains a regression reference." | EXACT_MATCH | G1 starts from an open measured problem, not a production choice. |

No unexplained material semantic drift remains. Historical digest equality is not
claimed when the historical raw bundle is unavailable.

## Linux supporting evidence

- branch head: `6ba7e431544795649335db00658526331e2fd975`;
- summary blob: `156f0d370f1a44c28246eb1fae2246b695e12887`;
- workflow run/job: `29691295919` / `88204419057`;
- semantic result: MATCH;
- open gap: REPRODUCED;
- raw artifact: UNAVAILABLE;
- canonical equivalence: NOT CLAIMED.

## Current candidate decision

- recommended candidate: none;
- `R-CURRENT`: regression reference;
- production integration: prohibited;
- learning effectiveness: not proven.

## Files and commits

Only the seven allowlisted evidence/documentation paths belong to the clean result
commit. No workflow, tool, monitor or raw artifact file is transferred from the
execution branch.

## Isolation and immutability

All source, tests, fixtures, scenarios, personas, configs, contracts, schemas,
declarations, environment/functional records, Cargo files and historical reports
have identical before/after digests.

## What was not executed

Fast CI, Docker E2E, real-Anki E2E, production runtime/frontend tests, full
population long mode, real Anki history replay, human learning evaluation and
production integration tests were intentionally not run. The full G0.6 functional
suite was not repeated because executable inputs were unchanged.

## Limitations

The evidence is synthetic. The 365-day run is bounded to one candidate, 20 cards
and two replicas. Historical digest equivalence cannot be proven without the
historical raw bundle. The current artifact expires at
`2026-08-02T16:40:11Z`.

## G0 closure

G0 closes because environment, functional behavior and current evidence are now
truthfully reproducible; the open cycling result is precisely measured and handed
to G1.

## Next

`G1 — Close Review XP cross-horizon cycling gap`
