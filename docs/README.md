# Documentation index

`docs/` contains only current architecture, API, UX, security, configuration, testing and operational contracts.

## Folder boundaries

```text
docs/       current behavior and mandatory contracts
roadmap/    track placement, dependencies and activation/completion criteria
reports/    historical audits, measurements and closeout evidence
```

Future planning is multi-track. The compact map is [roadmap/README.md](../roadmap/README.md):

- [Core](../roadmap/core/README.md)
- [Gamification](../roadmap/gamification/README.md)
- [Telemetry operations](../roadmap/operations/README.md)
- [Identity continuity](../roadmap/identity/README.md)
- [Extension ecosystem](../roadmap/extensions/README.md)
- [Platform / CI](../roadmap/platform/README.md)

Gamification research, telemetry admin tooling, optional identity and extension packs are not current production contracts merely because they appear in roadmap.

## Main current-contract entries

- [Project overview](project-overview.md)
- [Architecture](architecture.md)
- [Dashboard API](dashboard-api.md)
- [Frontend map](frontend-map.md)
- [Navigation / IA](navigation-ia.md)
- [Cards v2 product contract](cards-v2-product-contract.md)
- [Cards v2 triage read API](cards-v2-triage-read-api.md)
- [Cards attention inbox](cards-attention-inbox.md)
- [Historical C1.5 workspace UI](cards-v2-workspace-ui.md)
- [Canonical card display identity](card-display-identity.md)
- [Declarative card display formatter v1](card-display-formatter-v1.md)
- [Inspection Profiles v1](inspection-profiles-v1.md)
- [Inspection Profiles settings UI](inspection-profiles-ui.md)
- [Settings Hub](settings-hub.md)
- [Statistics](statistics-v1.md)
- [FSRS analytics](fsrs-analytics.md)
- [Search and Safe Actions](search-v1-and-safe-actions.md)
- [Signals](signals-foundation.md)
- [Notification Center](notification-center.md)
- [Privacy / telemetry](privacy-telemetry.md)
- [Security and safety](security-and-safety.md)
- [Test matrix](test-matrix.md)
- [Verification policy](verification-run-policy.md)
- [CI/CD](ci-cd.md)
- [GHCR E2E consumer](ghcr-e2e-consumer.md)
- [Packaging / release](packaging-release.md)
- [Decision log](decision-log.md)
- [AI handoff](ai-handoff.md)

Historical evidence belongs in [reports/](../reports/README.md), not in `docs/`.

## C1.5R.3 preview semantics

See [`card-preview-semantics.md`](card-preview-semantics.md). Full preview uses reviewer/native front and answer; Inspector shows front, expanded dialog shows answer, and compact identity remains unchanged.

## C1.5R.4 independent candidate sources

See [`triage-candidate-sources-v4.md`](triage-candidate-sources-v4.md). Triage schema v4 separates bounded period learning candidates from bounded current-content candidates.

## C1.5R.5 Cards attention inbox

See [`cards-attention-inbox.md`](cards-attention-inbox.md). The rejected table is replaced by a semantic identity-led list, wide Inspector, 1024 px non-modal drawer, explicit learning period and bounded manual current-content continuation.
