# Telemetry operations track

**Track:** `O`
**Role:** parallel operational tooling, separate from the local add-on
**Current status:** `O1` is Planned

The current telemetry service is an opt-in ingestion Worker with EU D1 and a deliberately narrow public surface. It has no dashboard, generic query API or user account. Operations work does not add a route to the user dashboard and does not place admin credentials in the add-on.

## O1 — Telemetry Admin Analytics Dashboard

**Status:** Planned; activation is independent of Cards v2

### Goal

Provide the project owner with a protected read-only operational dashboard for usage aggregates, system health, privacy/retention/deletion status and bounded diagnostics.

### Dependencies

- telemetry ingestion/data/retention/deletion contracts are stable enough to query;
- separate staging and production resources;
- explicit aggregate/query definitions;
- a separate repository or clearly isolated subproject and deployment boundary.

### Architecture boundary

```text
Browser
→ Cloudflare Access
→ separate Admin UI / Admin Worker
→ fixed read-only prepared-query API
→ TELEMETRY_DB binding
```

Cloudflare Access is the outer identity-aware proxy, but the Worker must still validate the Access JWT/audience on each request. D1 access remains server-side; query parameters are allowlisted and bound through prepared statements.

Official references:

- https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/
- https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/
- https://developers.cloudflare.com/d1/worker-api/prepared-statements/

### Scope

- Overview, activity, versions/environment and bounded feature/event distributions;
- performance/error buckets and quota/rate-limit pressure;
- aggregation freshness and system-health notices;
- privacy notice/consent schema distribution;
- retention, expiry, deletion and consistency status;
- fixed period/interval/filter allowlists;
- synthetic-only staging verification and separate manual production deployment;
- deployment rollback and fail-closed authorization tests.

### Out of scope

- local dashboard route or hidden admin mode;
- arbitrary SQL/query endpoint;
- raw content-level study data;
- admin secrets in Python, bundled frontend, config or browser storage;
- write/mutation controls over installations/events;
- account, remote flags or generic analytics platform.

### Activation criteria

Activate when at least one is true:

- recurring operational questions require manual D1 inspection;
- ingestion/retention/deletion health needs regular observation;
- telemetry volume makes direct ad hoc inspection error-prone;
- production incidents require a bounded read-only diagnostic surface.

The stage may begin before Cards v2 and does not block Core 1.0.

### Completion criteria

- Access policy and Worker-side JWT/audience validation fail closed;
- every API endpoint is read-only, bounded, typed and uses prepared queries;
- staging uses synthetic data only;
- no admin secret or route enters the add-on;
- privacy/retention/deletion metrics cannot reconstruct deleted payloads;
- deployment, rollback and security verification are documented;
- production deployment remains separately approved.
