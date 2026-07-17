# Extension ecosystem track

**Track:** `E`
**Role:** parallel/deferred first-party extension work
**Current status:** `E1` is Conditional

The core add-on is complete and releasable without an extension system. This track starts only from a concrete first-party need; it is not the automatic continuation of Statistics or Core 1.0.

## Sequence

```text
E1 Extension contract discovery with one reference pack
→ E2 Minimal Extension Pack Foundation
→ E3 First-party Analytics Pack (conditional)
→ E4 Additional first-party packs (evidence-based only)
```

## E1 — Contract discovery

**Status:** Conditional

### Goal

Use one approved first-party reference pack to discover the smallest required extension contract.

### Dependencies

C2 Core 1.0 contracts sufficiently stable; a concrete workflow cannot reasonably live in core.

### Scope

Capability inventory, data/query needs, lifecycle, compatibility, packaging, uninstall/recovery and threat model.

### Out of scope

Generic marketplace, hypothetical APIs, placeholders, remote code execution and arbitrary UI slots.

### Activation criteria

A named reference pack has a justified user workflow, ownership, maintenance plan and reason not to remain core.

### Completion criteria

A reviewed contract proposal proves each capability against the reference pack and rejects speculative surface.

## E2 — Minimal Extension Pack Foundation

**Status:** Planned only after E1

### Goal

Implement fail-closed, versioned first-party extension points required by the reference pack.

### Dependencies

E1 accepted; stable core migrations and package boundaries.

### Scope

Versioned manifest, capability allowlist, local lifecycle, compatibility negotiation, bounded Python-side data/query access, typed contribution slots, separate package/tests and uninstall/recovery.

### Out of scope

Unsigned remote code, generic iframe/JavaScript plugins, direct frontend collection access, arbitrary network privilege and account/sync.

### Activation criteria

E1 demonstrates that the foundation is necessary and minimal.

### Completion criteria

Reference pack passes install/update/uninstall/recovery; core works without it; token/sanitizer/action/media boundaries remain intact; artifacts stay separate.

## E3 — First-party Analytics Pack

**Status:** Conditional

### Goal

Host a specific optional/expensive analytical workflow that should not increase core startup/payload for everyone.

### Dependencies

E2 complete and a concrete unanswered analytical question with metric definitions and a performance budget.

### Scope

Only the approved workflow; local computation by default; typed extension contracts.

### Out of scope

Duplicating Statistics/FSRS, arbitrary dashboards, scheduler mutation or remote study-data telemetry.

### Activation criteria

A reference analytics workflow justifies E2 and cannot be delivered as a bounded contextual core addition.

### Completion criteria

Pack is separately installable/removable, metrics are canonical and tested, and core performance/data remain unaffected.

## E4 — Additional first-party packs

**Status:** Deferred

Each pack requires its own evidence, owner, security review and maintenance case. No marketplace or third-party ecosystem is implied.
