# Security Policy

## Supported Versions

Security fixes are developed for the latest source on the default branch and,
when applicable, the latest published Anki Study Report release. Older releases
and forks may not receive backports.

## Reporting a Vulnerability

Please do **not** open a public issue, pull request, discussion, or comment for a
suspected vulnerability.

Report it privately to
[leaf.fairy@proton.me](mailto:leaf.fairy@proton.me) with the subject
`[Anki Study Report security]`.

Include, when safely available:

- the affected version or commit;
- the affected operating system and Anki version;
- a concise description of the security impact;
- reproducible steps or a minimal proof of concept;
- the relevant route, API, file, or component;
- whether user interaction or a specially crafted collection/card is required;
- suggested mitigations or patches;
- your preferred name or handle for acknowledgment.

Remove dashboard tokens, token-bearing URLs, collection content, profile data,
credentials, private filesystem paths, and other personal information before
sending evidence. If sensitive data is essential to reproduction, describe it
first rather than attaching it immediately.

The maintainer will aim to acknowledge a complete report within seven days.
Investigation and remediation time depend on severity, reproducibility, and
release impact. Please allow a reasonable coordinated-disclosure period before
publishing details.

## Relevant Security Issues

Examples include:

- bypassing dashboard token validation or authorization;
- exposing the local server beyond the loopback interface;
- leaking dashboard tokens or token-bearing URLs;
- path traversal, arbitrary local file access, or unsafe media resolution;
- script execution or unsafe active content through card HTML, CSS, templates,
  or previews;
- bypassing sanitizer, media, request-body, or action allowlists;
- arbitrary command or RPC execution;
- exposing raw collection, card, note, revlog, profile, or filesystem data;
- unsafe archive/package contents or public CI/E2E artifacts containing secrets
  or personal data;
- dependency or workflow compromise that materially affects users or releases.

## Usually Not a Security Issue

The following should normally use a bug report instead:

- incorrect statistics without a confidentiality or integrity impact;
- layout, theme, translation, or accessibility defects;
- ordinary installation or startup failures;
- performance regressions without a denial-of-service or data-safety impact;
- unsupported Anki versions or modified forks;
- reports that only show that the dashboard is reachable from the same local
  user who launched it, with no boundary bypass.

When uncertain, report privately and let the maintainer classify it.

## Project Security Boundaries

Anki Study Report is local software, but it processes user-controlled card
HTML/CSS/media and serves a token-protected HTTP dashboard. Security-sensitive
changes must preserve the project's documented boundaries, including:

- loopback-only server binding;
- strict token validation;
- allowlisted API actions and request models;
- bounded aggregate payloads instead of raw collection access;
- validated trusted media resolution;
- parser/allowlist-based card HTML and style sanitization;
- isolated card preview rendering without iframe or JavaScript execution;
- redaction and exclusion of token-bearing runtime artifacts.

See [`docs/security-and-safety.md`](docs/security-and-safety.md) for the detailed
technical model and verification commands.

## Disclosure and Credit

After a fix is available, the maintainer may publish a security advisory or
release note describing the impact and mitigation without exposing user data.
Reporter credit will be given when requested and appropriate; anonymous reports
are also accepted.
