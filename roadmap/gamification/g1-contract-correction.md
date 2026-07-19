# G1.1 corrective checkpoint — Contract semantics

## Status

`G1.1 correction — Complete`

`G1 — In Progress`

`G1.2 — Next / Ready`

`production integration — PROHIBITED`

## Recorded refs

- canonical input: `f1485498b697c043a65c2d7ac6f6758da19b7e19`;
- correction branch: `temp/g1-1-contract-correction`;
- correction commit: this commit;
- execution run: `29701997981`;
- `master` and `core`: unchanged by this checkpoint.

## Trigger

The frozen machine-readable contract passed its schema while containing two
semantic metadata inconsistencies: attribution completeness was marked executable
before tracing existed, and boolean/status outputs were described as ratios.

## Confirmed inconsistencies

1. `diagnostic_attribution.status` said `REQUIRED_FOR_G1_2_NOT_IMPLEMENTED`, while
   `hard_gates.technical_completeness.attribution_fields` said `EXECUTABLE`.
2. `endpoint_pass`, `replica_grew`, `group_systematic_growth` and
   `overall_research_gate` used `fraction/ratio` metadata despite producing
   booleans or a status.

## Corrected attribution classification

The field requirements remain frozen and mandatory. Their current gate is
`NORMATIVE_NOT_YET_EXECUTABLE`; trace implementation remains absent and belongs
to G1.2.

## Corrected metric value kinds

- `endpoint_pass`: `boolean/boolean`, predicate-input tolerance `1e-9`;
- `replica_grew`: `boolean/boolean`, predicate threshold `> 1e-9`;
- `group_systematic_growth`: `boolean/boolean`, aggregate tolerance not applicable;
- `overall_research_gate`: `status/status`, aggregate tolerance not applicable.

## Unchanged frozen semantics

All six evidence cells, three group outcomes, `R-CURRENT`, overall `FAIL`, policy
pairs, horizons, replicas, formulas, endpoint cap `0.03`, comparison tolerance
`1e-9`, growth threshold, protected invariants and decision outcomes are unchanged.
The protocol remains v1 because no decision semantics changed.

## Files changed

Exactly seven tracked paths listed by the corrective checkpoint contract.

## JSON and schema validation

Draft 2020-12 self-check, strict parsing, duplicate-key rejection, finite-number
traversal, deterministic serialization, valid/invalid representation-unit pairing
samples and frozen attribution-status rejection were executed.

## Evidence/config reconciliation

The corrected contract reconciles 6/6 cells and 3/3 groups to the immutable G0.7
record. Seven policies, retention timelines, delay `[30,45)`, review limit `1000`,
90-day `24 x 2`, 365-day `20 x 2` and seed `20260716` remain exact.

## Git audit

The correction is prepared as one direct-descendant commit with exactly seven
allowed paths, no workflow/source/test/config/evidence changes and no generated
research outputs.

## Temporary branch and worktree cleanup

The GitHub Actions runner uses isolated ephemeral checkouts rather than a persistent
linked worktree. Remote `temp/g1-1-*` refs are deleted operationally only after
canonical fast-forward verification.

## Workflow definition audit

```json
{
  "gamification": [
    {
      "classification": "CANONICAL_REQUIRED",
      "path": ".github/workflows/ci-e2e.yml"
    },
    {
      "classification": "CANONICAL_REQUIRED",
      "path": ".github/workflows/ci-fast.yml"
    },
    {
      "classification": "CANONICAL_REQUIRED",
      "path": ".github/workflows/e2e-environment-image.yml"
    },
    {
      "classification": "CANONICAL_REQUIRED",
      "path": ".github/workflows/release.yml"
    },
    {
      "classification": "CANONICAL_REQUIRED",
      "path": ".github/workflows/telemetry-client-smoke.yml"
    }
  ],
  "temp/g1-1-contract-correction": [
    {
      "classification": "UNKNOWN",
      "path": ".github/workflows/ci-e2e.yml"
    },
    {
      "classification": "UNKNOWN",
      "path": ".github/workflows/ci-fast.yml"
    },
    {
      "classification": "UNKNOWN",
      "path": ".github/workflows/e2e-environment-image.yml"
    },
    {
      "classification": "UNKNOWN",
      "path": ".github/workflows/release.yml"
    },
    {
      "classification": "UNKNOWN",
      "path": ".github/workflows/telemetry-client-smoke.yml"
    }
  ],
  "temp/g1-1-contract-correction-execution": [
    {
      "classification": "UNKNOWN",
      "path": ".github/workflows/ci-e2e.yml"
    },
    {
      "classification": "UNKNOWN",
      "path": ".github/workflows/ci-fast.yml"
    },
    {
      "classification": "UNKNOWN",
      "path": ".github/workflows/e2e-environment-image.yml"
    },
    {
      "classification": "TEMPORARY_STAGE_ONLY",
      "path": ".github/workflows/g1-1-contract-correction-observer.yml"
    },
    {
      "classification": "TEMPORARY_STAGE_ONLY",
      "path": ".github/workflows/g1-1-contract-correction-retry.yml"
    },
    {
      "classification": "TEMPORARY_STAGE_ONLY",
      "path": ".github/workflows/g1-1-contract-correction-retry2.yml"
    },
    {
      "classification": "TEMPORARY_STAGE_ONLY",
      "path": ".github/workflows/g1-1-contract-correction.yml"
    },
    {
      "classification": "UNKNOWN",
      "path": ".github/workflows/release.yml"
    },
    {
      "classification": "UNKNOWN",
      "path": ".github/workflows/telemetry-client-smoke.yml"
    }
  ],
  "temp/g1-1-problem-gate-freeze": [
    {
      "classification": "UNKNOWN",
      "path": ".github/workflows/ci-e2e.yml"
    },
    {
      "classification": "UNKNOWN",
      "path": ".github/workflows/ci-fast.yml"
    },
    {
      "classification": "UNKNOWN",
      "path": ".github/workflows/e2e-environment-image.yml"
    },
    {
      "classification": "UNKNOWN",
      "path": ".github/workflows/release.yml"
    },
    {
      "classification": "UNKNOWN",
      "path": ".github/workflows/telemetry-client-smoke.yml"
    }
  ],
  "temp/g1-1-problem-gate-freeze-execution": [
    {
      "classification": "UNKNOWN",
      "path": ".github/workflows/ci-e2e.yml"
    },
    {
      "classification": "UNKNOWN",
      "path": ".github/workflows/ci-fast.yml"
    },
    {
      "classification": "UNKNOWN",
      "path": ".github/workflows/e2e-environment-image.yml"
    },
    {
      "classification": "TEMPORARY_STAGE_ONLY",
      "path": ".github/workflows/g1-1-observer.yml"
    },
    {
      "classification": "TEMPORARY_STAGE_ONLY",
      "path": ".github/workflows/g1-1-publication.yml"
    },
    {
      "classification": "UNKNOWN",
      "path": ".github/workflows/release.yml"
    },
    {
      "classification": "UNKNOWN",
      "path": ".github/workflows/telemetry-client-smoke.yml"
    }
  ]
}
```

No G1.1 stage-only workflow exists on canonical `gamification`.

## Workflow run and artifact cleanup

Runs classified `DELETE_AFTER_STAGE` before publication:

```json
[
  {
    "artifacts": [],
    "classification": "DELETE_AFTER_STAGE",
    "conclusion": "failure",
    "created_at": "2026-07-19T18:47:34Z",
    "event": "push",
    "head_branch": "temp/g1-1-problem-gate-freeze-execution",
    "head_sha": "d4d91d4db30de0f85dd002a01f367358c39d7acd",
    "id": 29699320076,
    "status": "completed",
    "updated_at": "2026-07-19T18:48:05Z",
    "workflow_name": "G1.1 problem and gate freeze publication",
    "workflow_path": ".github/workflows/g1-1-publication.yml"
  },
  {
    "artifacts": [],
    "classification": "DELETE_AFTER_STAGE",
    "conclusion": "failure",
    "created_at": "2026-07-19T18:55:19Z",
    "event": "push",
    "head_branch": "temp/g1-1-problem-gate-freeze-execution",
    "head_sha": "ec2440eeba1d54b85476db2cb0587c2e3005af29",
    "id": 29699552983,
    "status": "completed",
    "updated_at": "2026-07-19T18:57:02Z",
    "workflow_name": "G1.1 publication observer",
    "workflow_path": ".github/workflows/g1-1-observer.yml"
  },
  {
    "artifacts": [],
    "classification": "DELETE_AFTER_STAGE",
    "conclusion": "failure",
    "created_at": "2026-07-19T18:55:40Z",
    "event": "push",
    "head_branch": "temp/g1-1-problem-gate-freeze-execution",
    "head_sha": "92ec6eb72e720e9895a47c0c29a620a926f8ab07",
    "id": 29699572383,
    "status": "completed",
    "updated_at": "2026-07-19T18:57:04Z",
    "workflow_name": "G1.1 problem and gate freeze publication",
    "workflow_path": ".github/workflows/g1-1-publication.yml"
  },
  {
    "artifacts": [],
    "classification": "DELETE_AFTER_STAGE",
    "conclusion": "success",
    "created_at": "2026-07-19T18:56:15Z",
    "event": "push",
    "head_branch": "temp/g1-1-problem-gate-freeze-execution",
    "head_sha": "92ec6eb72e720e9895a47c0c29a620a926f8ab07",
    "id": 29699614321,
    "status": "completed",
    "updated_at": "2026-07-19T18:56:34Z",
    "workflow_name": "G1.1 publication observer",
    "workflow_path": ".github/workflows/g1-1-observer.yml"
  },
  {
    "artifacts": [],
    "classification": "DELETE_AFTER_STAGE",
    "conclusion": "failure",
    "created_at": "2026-07-19T18:56:15Z",
    "event": "push",
    "head_branch": "temp/g1-1-problem-gate-freeze-execution",
    "head_sha": "92ec6eb72e720e9895a47c0c29a620a926f8ab07",
    "id": 29699614398,
    "status": "completed",
    "updated_at": "2026-07-19T18:57:28Z",
    "workflow_name": "G1.1 problem and gate freeze publication",
    "workflow_path": ".github/workflows/g1-1-publication.yml"
  },
  {
    "artifacts": [],
    "classification": "DELETE_AFTER_STAGE",
    "conclusion": "failure",
    "created_at": "2026-07-19T20:01:24Z",
    "event": "push",
    "head_branch": "temp/g1-1-contract-correction-execution",
    "head_sha": "db6e4adae596339897579a20100b119d45449c6b",
    "id": 29701719714,
    "status": "completed",
    "updated_at": "2026-07-19T20:01:56Z",
    "workflow_name": "G1.1 contract correction publication",
    "workflow_path": ".github/workflows/g1-1-contract-correction.yml"
  },
  {
    "artifacts": [],
    "classification": "DELETE_AFTER_STAGE",
    "conclusion": "failure",
    "created_at": "2026-07-19T20:03:40Z",
    "event": "push",
    "head_branch": "temp/g1-1-contract-correction-execution",
    "head_sha": "e670425684bd6482231a32e091126b389dfdaab0",
    "id": 29701795489,
    "status": "completed",
    "updated_at": "2026-07-19T20:04:05Z",
    "workflow_name": "G1.1 contract correction publication",
    "workflow_path": ".github/workflows/g1-1-contract-correction.yml"
  },
  {
    "artifacts": [],
    "classification": "DELETE_AFTER_STAGE",
    "conclusion": "success",
    "created_at": "2026-07-19T20:04:34Z",
    "event": "push",
    "head_branch": "temp/g1-1-contract-correction-execution",
    "head_sha": "5880e7b7824628b8c82e8252818053df63b22664",
    "id": 29701825646,
    "status": "completed",
    "updated_at": "2026-07-19T20:04:47Z",
    "workflow_name": "G1.1 contract correction observer",
    "workflow_path": ".github/workflows/g1-1-contract-correction-observer.yml"
  },
  {
    "artifacts": [],
    "classification": "DELETE_AFTER_STAGE",
    "conclusion": "success",
    "created_at": "2026-07-19T20:06:12Z",
    "event": "push",
    "head_branch": "temp/g1-1-contract-correction-execution",
    "head_sha": "d70b923862a5aff047bafc01ba948ed4b50dacf3",
    "id": 29701879793,
    "status": "completed",
    "updated_at": "2026-07-19T20:06:24Z",
    "workflow_name": "G1.1 contract correction observer",
    "workflow_path": ".github/workflows/g1-1-contract-correction-observer.yml"
  },
  {
    "artifacts": [],
    "classification": "DELETE_AFTER_STAGE",
    "conclusion": "failure",
    "created_at": "2026-07-19T20:08:01Z",
    "event": "push",
    "head_branch": "temp/g1-1-contract-correction-execution",
    "head_sha": "f78c4d754224cbb36ed04c595250a2246e5f3387",
    "id": 29701934308,
    "status": "completed",
    "updated_at": "2026-07-19T20:08:31Z",
    "workflow_name": "G1.1 contract correction retry",
    "workflow_path": ".github/workflows/g1-1-contract-correction-retry.yml"
  },
  {
    "artifacts": [],
    "classification": "DELETE_AFTER_STAGE",
    "conclusion": "success",
    "created_at": "2026-07-19T20:09:01Z",
    "event": "push",
    "head_branch": "temp/g1-1-contract-correction-execution",
    "head_sha": "454ffdfdcca0683a61c541a453f39e278e50c1be",
    "id": 29701964340,
    "status": "completed",
    "updated_at": "2026-07-19T20:09:13Z",
    "workflow_name": "G1.1 contract correction observer",
    "workflow_path": ".github/workflows/g1-1-contract-correction-observer.yml"
  }
]
```

Current correction run (not deletable while in progress):

```json
[
  {
    "artifacts": [],
    "classification": "PRESERVE_UNKNOWN_CURRENT",
    "conclusion": null,
    "created_at": "2026-07-19T20:10:06Z",
    "event": "push",
    "head_branch": "temp/g1-1-contract-correction-execution",
    "head_sha": "296954aad317bf2229ef244ce10f23e75875afe8",
    "id": 29701997981,
    "status": "in_progress",
    "updated_at": "2026-07-19T20:10:10Z",
    "workflow_name": "G1.1 contract correction retry 2",
    "workflow_path": ".github/workflows/g1-1-contract-correction-retry2.yml"
  }
]
```

Deleting a completed run also deletes its attached artifacts. Operational deletion
occurs after canonical verification; the final GitHub closeout records results.

## Preserved canonical evidence

- Windows evidence run `29695312258`;
- Windows job `88214940938`;
- raw artifact `8444920908`;
- G0.7 publication run `29697258461`;
- Linux supporting run `29691295919`.

## What was not run

No sweep, sensitivity, population, longitudinal, full pytest, Rust, Fast CI,
Docker E2E, real-Anki E2E or production test was run. Executable research inputs
did not change.

## Limitations

This checkpoint corrects contract consistency only. It neither diagnoses nor
repairs the cycling behavior. The current workflow run can be deleted only after
completion and is therefore reported separately in the final closeout.

## G1.2 readiness

`READY`: G1.2 may implement synthetic attribution against the corrected v1
contract without changing frozen decision semantics.

## Next step

`G1.2 — Root-cause attribution`.
