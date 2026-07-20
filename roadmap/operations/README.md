# Operations track

**Track:** `O`  
**Role:** protected operational tooling for remote services, separate from the local add-on  
**Decision snapshot:** **2026-07-20**  
**Current status:** `O1` is **Next**; `O2` is **Conditional**

Operations is a parallel track. It does not extend the primary study navigation, does not place administrative credentials in the add-on and does not block `C1`, `C2` or local gamification work.

The accepted direction separates four concerns:

```text
anonymous telemetry
account identity
cloud synchronization
paid-service entitlement
```

They may share operational tooling later, but they do not share identifiers, credentials, storage contracts or consent semantics by default.

## Cross-track independence

- `O1` starts from the telemetry contracts already merged to `master`.
- Core and Gamification branches are not merged or cherry-picked into Operations merely to begin this track.
- `O1` can run while `C1` and `G0+` continue independently.
- `O2` depends on an approved Identity/Cloud Sync product contract, not on completion of `O1` or local gamification.
- Remote gamification continuity may use the future cloud-sync service; local gamification remains independent.

---

# O1 — Telemetry Operations Foundation and Admin Console

**Status:** Next  
**Activation:** approved because automatic operational metrics and an early minimal admin surface are now required

## Goal

Provide the project owner with a protected, read-only operational surface for:

- usage aggregates;
- ingestion and quota health;
- Worker and D1 infrastructure metrics;
- aggregation and retention freshness;
- privacy, consent and deletion status;
- bounded incident diagnostics.

The first useful release is intentionally small. It prioritizes trustworthy automated collection and clear health signals over a broad dashboard.

## Architecture boundary

```text
Browser
→ Cloudflare Access
→ separate Admin UI / Admin Worker
   ├─ fixed read-only telemetry query API
   ├─ Cloudflare GraphQL Analytics adapter
   └─ bounded operational collector
→ TELEMETRY_DB + separate ADMIN_DB
```

### Authorization

Cloudflare Access is the outer identity-aware proxy. The Admin Worker must still validate the Access JWT on every request, including signature, issuer, expiry and expected audience. JWKS rotation must be supported.

No administrative secret, Access token, service credential or token-bearing URL may enter:

- the add-on;
- the bundled frontend;
- browser storage;
- repository files;
- logs, screenshots or CI artifacts.

### Query safety

Every endpoint is:

- read-only;
- typed;
- bounded;
- selected from a fixed query registry;
- restricted to allowlisted periods, intervals and filters;
- implemented with prepared statements and bound values.

The browser never supplies SQL, table names, column names or arbitrary grouping expressions.

## Data sources

### `TELEMETRY_DB`

Authoritative for application-level information:

- enrolled and active installations;
- accepted event counts;
- event, version, page, feature, action, result and bounded performance distributions;
- consent schema and privacy notice distributions;
- quota state;
- retention, expiry and deletion outcomes.

These are **installation metrics**, not proof of unique people. The UI must not label installations as users.

### Cloudflare GraphQL Analytics API

Authoritative for provider-level infrastructure information:

- D1 rows read and written;
- query volume and latency;
- database size;
- Worker requests, errors, status classes, CPU and execution duration where available;
- current provider quota pressure.

The API credential is server-side, least-privilege and read-only.

### `ADMIN_DB`

Stores only bounded operational state:

- hourly provider metric snapshots;
- source freshness;
- alert state and threshold crossings;
- collector run status;
- dashboard configuration that is not secret.

It does not store raw request logs, IP addresses, installation identifiers, access tokens or copied telemetry payloads.

## Metric and query contract

A versioned Metric Registry is required before UI implementation. Every metric definition states:

```text
metric_code
human meaning
source
aggregation formula
supported periods
supported interval
allowed filters
data retention
exact or estimated semantics
privacy threshold
empty / incomplete semantics
freshness source
```

The current `daily_aggregates` table does not preserve every raw-event dimension needed by the accepted dashboard. O1 must introduce a bounded long-term read model rather than building the UI directly on the current table.

Recommended logical families:

```text
daily_metric_totals
daily_metric_dimensions
daily_metric_pairs
maintenance_runs
provider_metric_snapshots
```

The exact schema is finalized during implementation, but these invariants are fixed:

1. no universal high-cardinality analytics cube;
2. no arbitrary combinations of dimensions;
3. only reviewed metric codes are materialized;
4. aggregation remains idempotent;
5. deleted installations cannot be reconstructed from aggregates;
6. migrations are forward-only and separately verified in staging.

## Privacy semantics

The dashboard uses terms such as:

- enrolled installations;
- active installations over a fixed window;
- installations by add-on version;
- installations by consent schema or privacy notice;
- deletion requests completed;
- raw rows expired;
- aggregate freshness.

It must not claim:

- unique people;
- person retention;
- user-level journeys;
- identity across installations;
- reconstructed deleted installations.

Initial privacy guardrails:

- global totals may be exact;
- small distribution cells below `5` are displayed as `<5`;
- one-dimensional breakdowns are the default;
- two-dimensional breakdowns require an explicit registry entry;
- installation IDs are never searchable or displayed;
- there is no raw-event explorer;
- arbitrary multi-filter segmentation is forbidden.

Changing these guardrails requires a privacy review, not a frontend-only change.

## Freshness and maintenance evidence

Freshness must be explicit rather than inferred only from the newest aggregate date.

`maintenance_runs` records bounded state for each scheduled execution:

```text
run_id
scheduled_for
started_at
completed_at
status_code
aggregate_rows_changed
raw_rows_deleted
aggregate_rows_deleted
operational_rows_deleted
duration_bucket
```

Allowed status codes are bounded, for example:

```text
running
success
partial_failure
storage_unavailable
unexpected_failure
```

No SQL, exception messages, stack traces, tokens or request bodies are stored.

The UI reports freshness separately for:

1. telemetry aggregation;
2. retention/deletion maintenance;
3. Cloudflare provider metric collection.

Initial operational targets:

```text
Daily telemetry maintenance
- healthy:   last success < 30 hours
- warning:   30–54 hours
- critical:  > 54 hours

Hourly provider collector
- healthy:   last success < 2 hours
- warning:   2–4 hours
- critical:  > 4 hours
```

These are deployment-contract defaults, not arbitrary user-editable settings.

## Minimal admin information architecture

The first admin UI contains only four top-level surfaces:

### Overview

- active installations;
- accepted events;
- current error rate;
- source freshness;
- critical operational notices.

### Usage

- add-on and Anki versions;
- bounded page, feature and action distributions;
- search/action result and duration buckets;
- exact source and retention labels.

### Reliability

- D1 rows read/written and database size;
- Worker request/error state;
- quota pressure;
- collector and maintenance history;
- fail-closed runtime switch state where safely observable.

### Privacy

- consent schema and privacy notice distributions;
- retention and expiry state;
- deletion completion counts;
- explicit explanation that anonymized aggregates may outlive raw installation data.

There is no generic dashboard builder, customizable SQL editor or mutation console.

## Delivery phases

```text
O1.0  Activation evidence and source/schema audit
O1.1  Metric Registry and query contract
O1.2  Aggregate read model and maintenance ledger
O1.3  Access threat model and authorization contract
O1.4  Read-only Admin Worker API
O1.5  Cloudflare provider collector and ADMIN_DB snapshots
O1.6  Minimal Overview / Usage / Reliability / Privacy UI
O1.7  Synthetic staging verification and separately approved production deployment
```

## Dependencies

- stable telemetry ingestion, consent, retention and deletion contracts;
- separate staging and production resources;
- a separate Admin Worker and deployment boundary;
- explicit Metric Registry definitions;
- least-privilege Cloudflare analytics credential;
- synthetic-only staging data;
- reviewed migrations and rollback procedure.

## Scope

- automatic telemetry aggregation;
- fixed operational queries;
- provider metric collection;
- system-health notices;
- quota and capacity visibility;
- aggregation, retention and deletion freshness;
- Access authorization and fail-closed tests;
- deployment and rollback documentation;
- bounded administrative audit events.

## Out of scope

- local dashboard route or hidden admin mode;
- arbitrary SQL/query endpoint;
- raw study content or raw event browsing;
- account registration;
- cloud synchronization;
- payment processing;
- remote feature flags;
- installation-level tracking;
- write/mutation controls over telemetry installations or events;
- Analytics Engine as the authoritative telemetry store;
- unrelated Core, Gamification or Extension work.

## Completion criteria

- Access policy and Worker-side JWT/audience validation fail closed;
- every API endpoint is read-only, bounded, typed and registry-backed;
- prepared statements are used for all D1 parameters;
- long-term aggregates preserve only reviewed dimensions;
- source-specific freshness is visible and tested;
- small-cell privacy suppression is enforced server-side;
- Cloudflare credentials remain server-only;
- staging uses synthetic data only;
- no admin secret or route enters the add-on;
- privacy, retention and deletion metrics cannot reconstruct deleted payloads;
- deployment, rollback and security verification are documented;
- production deployment remains separately approved.

---

# O2 — Paid Cloud Sync Operations

**Status:** Conditional  
**Role:** operational support for a future optional account and cloud-sync product  
**Activation:** only after the Identity/Cloud Sync product contract is separately approved and scheduled

O2 does not implement accounts or synchronization inside the Operations track. It defines how an approved remote service is entitled, observed, backed up, recovered and safely retired.

## Product boundary

The local add-on remains fully usable without an account or subscription.

```text
Free / local-first
- local dashboard and statistics
- local profile, avatar and banner
- local settings and gamification
- manual export/import
- optional anonymous telemetry

Paid / optional cloud service
- account continuity
- multi-device synchronization
- remote restore after reinstall or device loss
- cloud profile media
- bounded revision history and export
- future remote gamification continuity
```

The subscription pays for ongoing remote infrastructure and operations. It does not unlock or disable the local Core product.

## Identity separation

Three identifiers remain distinct:

```text
telemetry_installation_id
- anonymous telemetry identity for one installation/profile
- absent when telemetry is not enabled
- never promoted into a person identifier

account_id
- immutable, random, opaque account identity
- created only after voluntary registration
- survives email, nickname and authentication-method changes

sync_device_id
- one linked Anki profile/device under an account
- revocable and replaceable
```

One account may own several devices. One person may create several accounts. No hardware, IP, MAC, machine GUID or browser fingerprint is used to infer identity.

Telemetry is not automatically linked to `account_id` or `sync_device_id`.

## Preferred initial service contour

The current preferred candidate for the future cloud service is:

```text
Supabase Auth
Supabase PostgreSQL
Supabase Storage
EU-region resources
```

Cloudflare remains the existing telemetry and telemetry-operations platform.

This provider choice is not embedded into public identifiers or sync semantics. `account_id`, `sync_device_id`, entity revisions, export format and entitlement contracts remain provider-neutral so the service can later migrate to another PostgreSQL/object-storage platform.

Before implementation, current pricing, limits, regional guarantees, backup behavior and auth capabilities must be reverified against official provider documentation.

## Synchronization contract

Cloud synchronization is entity-based and incremental. It never uploads a complete local SQLite file as the protocol.

Each synchronized entity has stable identity and revision semantics, for example:

```text
entity_id
account_id
schema_version
revision
created_at
updated_at
deleted_at
payload
```

Required properties:

- optimistic concurrency;
- idempotency keys;
- incremental changes since `last_revision`;
- tombstones for deletions;
- explicit conflict state;
- offline/local-first operation;
- bounded history retention;
- export independent of the provider.

Different data classes may use different merge strategies. A future gamification ledger must be append-only/server-authoritative rather than a blindly overwritten XP total.

The first cloud contract does not include Anki collection files, card/note text, deck content or Anki media. Any such expansion requires a separate product, privacy and security stage.

## Manual Boosty entitlement MVP

Boosty is treated as proof of an active subscription, not as the source of application identity.

Because no approved public webhook/API contract is relied on, the initial flow is manual:

```text
1. User registers an Anki Study Report account.
2. User purchases the approved Boosty subscription level.
3. Account UI generates a one-time activation code.
4. User sends the code to the author in a private Boosty message.
5. Author verifies the active subscription in Boosty.
6. Author redeems the code in the protected admin console.
7. Server creates or extends the cloud_sync entitlement.
```

The claim code is:

- random;
- short-lived;
- single-use;
- bound to the authenticated account;
- stored only as a hash;
- incapable of authenticating a session or exposing account data.

The user does not send an internal account UUID, access token, JWT, device token or email as the activation secret.

### Entitlement source of truth

A server-side `entitlements` record is authoritative. Client flags and editable metadata are not.

Recommended logical records:

```text
entitlement_claims
provider_links
subscriptions
entitlements
entitlement_audit
```

The provider link stores only the minimum Boosty reference required for manual renewal checks. Private messages, payment details and screenshots are not copied into application storage.

Initial lifecycle target:

```text
active paid period
→ 7-day grace with full sync
→ 30-day read-only/export window
→ 30-day soft-delete recovery window
→ permanent purge
```

Exact production periods require final product/privacy review, but local data is never deleted or disabled when the remote entitlement ends.

Unofficial Boosty scraping or reverse-engineered payment automation is explicitly out of scope. A future provider with documented webhooks may be added through a provider adapter without changing the entitlement model.

## Capacity and admission control

Free-provider capacity is acceptable only for development, controlled Early Access and measured validation. It is not a permanent availability promise for a paid service.

Initial planning guardrails, to be revalidated before launch:

```text
maximum linked devices per account: 3
synchronized extension state:       2 MB/account
profile media target:               5 MB/account
early-access admission cap:         100 paid accounts
```

Operational thresholds are set below provider hard limits:

- warning before sustained resource use reaches `70%`;
- critical before sustained resource use reaches `85%`;
- new admissions may be paused before service degradation;
- paid-provider migration is triggered by measured capacity, reliability or revenue coverage rather than by emergency exhaustion.

Synchronization must minimize egress through incremental changes, pagination, conditional requests, compressed JSON and local media caching.

## Backup and recovery

Provider backups are not the only recovery mechanism.

The initial low-cost backup contour is:

```text
remote production service
→ automated encrypted export
→ primary local HDD archive
→ second physically separate/offline HDD copy
→ recurring restore drill
```

A complete backup includes, as applicable:

- PostgreSQL roles/schema/data and migration history;
- Auth identities and required authentication state;
- Storage objects, not only storage metadata;
- redacted project configuration and deployment manifests;
- checksums and a bounded backup manifest.

Secrets are not written into backup manifests or repository files.

Required controls:

- encryption at rest;
- backup key stored separately;
- versioned retention rather than one overwritten `latest` file;
- bounded backup retention aligned with account deletion promises;
- restore into a disposable environment;
- recurring integrity and restore verification;
- bounded reports that contain no user content or credentials.

A single HDD is not sufficient evidence of recoverability. At least one additional physically separate copy is required before production paid sync.

## O2 operational surface

When activated, the protected console may add:

- account-service health totals without browsing private user content;
- active/grace/read-only entitlement counts;
- claims awaiting manual verification;
- renewals approaching expiry;
- sync success/error/conflict rates;
- database, storage and egress pressure;
- accounts approaching fixed quotas;
- backup freshness and restore-drill state;
- deletion/export completion state.

Administrative mutations are limited to reviewed entitlement and lifecycle operations. They are not added to the anonymous telemetry console by default.

## Dependencies

- separately approved Identity and Cloud Sync stage;
- explicit account, device, sync and export contracts;
- privacy notice and consent model for remote account data;
- provider-region and data-processing review;
- server-side entitlement checks;
- account unlink/revoke/export/delete semantics;
- backup and restore implementation before paid production use;
- controlled Early Access admission policy.

## Scope

- service capacity and health monitoring;
- manual entitlement claims and renewals;
- bounded account/device quota enforcement;
- backup/export/restore operations;
- subscription grace and deletion lifecycle;
- sync reliability and conflict metrics;
- provider migration readiness;
- incident controls and operational runbooks.

## Out of scope

- mandatory registration;
- account or sync implementation inside the telemetry Worker;
- automatic identity inference;
- hardware fingerprinting;
- unofficial Boosty API automation;
- storing payment-card details;
- syncing Anki collections or study content in the first cloud contract;
- blocking local features after subscription expiry;
- social features, public profiles or marketplace behavior without separate stages;
- implementation work on Core or Gamification branches.

## Activation criteria

O2 begins only when all are true:

1. the Identity/Cloud Sync product stage is approved;
2. exact data classes to synchronize are documented;
3. local export/import is insufficient for the accepted workflow;
4. provider and region are selected with current limits verified;
5. entitlement and deletion semantics are approved;
6. a controlled Early Access cohort exists;
7. backup and restore design has an executable verification plan.

## Completion criteria

- local mode remains fully functional without account or subscription;
- `account_id`, `sync_device_id` and telemetry identity remain separated;
- entitlement is enforced server-side;
- claim codes are hashed, expiring and single-use;
- service-role credentials remain server-only;
- every user-data table has reviewed authorization/RLS behavior;
- sync is incremental, idempotent and conflict-aware;
- export, unlink, revoke and account deletion work end to end;
- database, Auth, Storage and configuration backups are complete and encrypted;
- a separate offline backup copy exists;
- restore drills are repeatable and documented;
- provider capacity and admission thresholds are observable;
- subscription expiry never deletes or blocks local data;
- no unofficial payment integration is a production dependency.

---

## Branch and delivery policy

Operations work is developed from current `master` on a dedicated branch. It must not silently absorb unrelated Core or Gamification commits.

Documentation-only roadmap changes do not justify Docker or real-Anki E2E. Implementation stages choose verification according to `docs/test-matrix.md` and `docs/verification-run-policy.md`.

Each production activation remains separately approved:

- telemetry Admin Worker deployment;
- provider analytics credential creation;
- account/cloud provider provisioning;
- paid-sync Early Access;
- backup destination and restore procedure;
- payment-provider automation.
