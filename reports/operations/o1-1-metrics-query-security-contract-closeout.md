# O1.1 Metrics, Query and Security Contract closeout

- Date: `2026-07-26`
- Scope: contract-first telemetry Operations work
- Status: **O1.1 Complete; O1.2 Next; O1.3–O1.6 Planned**
- Canonical private commit:
  `7c9bd324034b97b84851f2d99a35234b9da74a89`
- Canonical private review:
  [anki-study-report-telemetry PR #19](https://github.com/AliceLiddell01/anki-study-report-telemetry/pull/19)

## Result

The private telemetry repository now holds the canonical versioned source
audit, Metric Registry, fixed Query Registry, typed response semantics,
privacy/backfill boundaries, Access/JWT/JWKS security contract, threat model,
focused machine-readable validation, and exact O1.2/O1.3 handoff.

The public repository intentionally records only stage state and non-private
boundaries. It does not duplicate the private registries, schema evidence,
provider identifiers, or operational values.

## Fixed decisions

- Operations is a separate protected admin product, never an add-on dashboard
  route.
- Installation metrics are not people/account metrics.
- Active installation means fixed-window accepted activity, not enrollment.
- Queries are read-only, typed, bounded, registry-backed, and allowlisted.
- The browser sends no SQL, database object names, arbitrary dimensions, or
  generic grouping.
- Small distribution cells below 5 use server-side primary and complementary
  suppression.
- Empty, suppressed, incomplete, stale, unavailable, and error are distinct
  response states.
- Historical gaps are explicit; deleted installations are not reconstructed.
- Access is outer protection, while the future Admin Worker must still validate
  signature, issuer, audience, expiry/not-before, and JWKS rotation.
- A D1 binding has no documented technical read-only mode; static query
  templates and absence of mutation endpoints remain application controls.

## Deliberately not implemented

- Admin Worker, API, or UI;
- D1 read-model or maintenance-ledger migrations;
- `ADMIN_DB` or provider collector;
- Access application, policy, credentials, secrets, or deployment;
- telemetry event, purpose, consent, notice, or retention changes;
- cloud workflows, add-on release, Docker, or real-Anki E2E.

## Next

O1.2 implements only the reviewed operational read model and bounded
maintenance evidence. O1.3 then implements the protected fixed read-only API.
Provider collection remains O1.4.
