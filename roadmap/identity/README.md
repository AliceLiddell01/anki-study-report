# Identity continuity track

**Track:** `I`
**Role:** conditional cloud/recovery gate
**Current status:** `I1` is Conditional, not scheduled

Identity continuity is not a prerequisite for telemetry, Cards v2 or Core 1.0. It must not silently become an account system.

## I1 — Identity continuity and optional linking

**Status:** Conditional

### Goal

Provide continuity only when a validated cross-installation workflow cannot be solved by local export/import or the existing anonymous `installation_id`.

### Trigger conditions

At least one concrete requirement must exist:

- cross-device state;
- recovery after reinstall/OS loss;
- continuity of an approved production gamification ledger;
- entitlement or sync that cannot be represented locally.

A vague desire to “have accounts later” is not a trigger.

### Identity model

```text
installation_id — random identity of one installation/profile
person_id       — absent by default; explicit opt-in linkage only
```

One person may have multiple installations and one installation may be shared. `installation_id` is not upgraded into a person identifier.

### Dependencies

- explicit product workflow and data-purpose definition;
- separate threat model and privacy migration;
- stable state/ledger contract for the feature requiring continuity;
- export/delete/revoke semantics before implementation.

### Scope

- compare recovery code/file, passkey/OAuth/account and OS credential-store options;
- link/unlink/revoke/rotate/export/delete lifecycle;
- bounded replay/rate-limit/recovery controls;
- separate identity, telemetry, entitlement and sync data;
- migration, rollback and recovery verification.

### Out of scope

- default account creation;
- retroactive linking of existing installations;
- IP, MAC, machine GUID, hardware or browser fingerprinting;
- hidden identifiers or automatic person inference;
- social features or monetization without separate stages.

### Activation criteria

A documented trigger condition is approved and local export/import is insufficient. Production gamification can remain local without `I1`; remote continuity may depend on it later.

### Completion criteria

- `person_id` remains absent by default;
- explicit informed opt-in;
- no fingerprint-derived identity;
- unlink, revoke, export and delete work end to end;
- privacy notice/consent migration and threat model are approved;
- secrets and identifiers are excluded from logs, screenshots, reports and CI artifacts.
