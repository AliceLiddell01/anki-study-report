# Repository agent guidance

## Project entry points

Before non-trivial work, read the relevant parts of `README.md`,
`docs/ai-handoff.md`, `roadmap/core/README.md`, profile documentation and
reports, production code, tests, `docs/test-matrix.md`, and
`docs/verification-run-policy.md`.

## Source-of-truth priority

Use this order when sources disagree:

1. current production code and tests;
2. current README and profile documentation;
3. fresh reports and evidence;
4. old plans and historical reports;
5. assumptions.

Separate confirmed facts from assumptions and do not invent missing results.

## Architecture and security invariants

Without a separate, evidence-backed decision, do not:

- give the frontend direct access to the Anki collection;
- expose the local server beyond its intended boundary;
- weaken token validation or log dashboard tokens or token-bearing URLs;
- weaken sanitizer, media validation, or action allowlists;
- turn card preview into an unsafe iframe or JavaScript surface;
- hand-edit generated dashboard assets.

## Frontend / backend contract rule

A payload or public-behavior change must update every affected layer together:
backend implementation, frontend types and parsers, tests, and documentation.
Do not change only one side of a contract.

## Cards frozen boundary

Cards is `ACCEPTED / COMPLETE / FROZEN`. Without a newly demonstrated
regression, do not change Cards component composition, queue, rail, drawer,
expanded answer, native card preview, AV/audio/GIF/media paths, Shadow DOM, or
Cards-specific styling to support unrelated Settings work. After shared-shell
changes, run only a focused Cards regression smoke proportional to risk.

## Testing and verification policy

Choose checks by risk. Do not run heavy Docker or real-Anki E2E without a
measured need. Never report a test, build, or browser result without its actual
output. After the final mutation, run one consolidated verification. An
artifact is complete only after inventory, checksum, and CRC validation.

## Git and PR policy

Work on the current task branch. Without explicit owner approval, do not create
a branch or PR, rebase, merge, force-push, mark a PR ready for review, merge a
PR, or publish a release. Preserve unrelated user changes. Commit messages must
describe the actual result.

## Artifact hygiene

Do not commit logs, screenshots, evidence archives, runtime output, caches,
profile data, tokens, `.ankiaddon` files, or Playwright output unless the path
is intentionally a versioned fixture.

## Visual-review policy

Codex does not assign a numerical visual score or claim owner visual
acceptance. Produce objective screenshots, geometry measurements, diffs, and a
deviation report, then leave the visual verdict to the owner or external
reviewer. Tests and accessibility results do not substitute for visual parity.

## Workflow stop-loss

Use direct repository commands and existing tools. The allowed cycle is one
implementation pass, one full verification, at most one bounded visual
correction pass, and one final verification. If the browser harness fails
repeatedly, fix the root cause in the existing repository-owned harness; do not
create a ladder of one-off runner, repair, resume, or finalizer scripts.
