# Contributing to Anki Study Report

Thank you for helping improve Anki Study Report. Contributions in English or
Russian are welcome.

This repository contains an Anki add-on runtime written in Python and a local
React/TypeScript dashboard. Changes can cross runtime, API, frontend, packaging,
and real-Anki verification boundaries, so please read the relevant contracts
before editing code.

## Start Here

Read these files before making a non-trivial change:

1. [`README.md`](README.md) for the project map and canonical commands.
2. [`docs/ai-handoff.md`](docs/ai-handoff.md) for the current project state.
3. The task-specific document under [`docs/`](docs/).
4. [`docs/codex-agent-rules.md`](docs/codex-agent-rules.md) for repository safety
   and Git workflow rules.
5. [`docs/test-matrix.md`](docs/test-matrix.md) and
   [`docs/verification-run-policy.md`](docs/verification-run-policy.md) before
   choosing verification.
6. [`docs/security-and-safety.md`](docs/security-and-safety.md) for server,
   token, media, HTML, action, and artifact boundaries.

Production code and tests take precedence over stale plans or old reports.
Never claim that a file, test, or runtime behavior was inspected when it was not.

## Before You Begin

Search existing issues and pull requests first. For larger behavior or
architecture changes, open a feature request before investing substantial work.
Security vulnerabilities must follow [`SECURITY.md`](SECURITY.md), not a public
issue.

At the start of local work, inspect the checkout:

```powershell
git status --short --branch
git diff --stat
git ls-files --others --exclude-standard
```

Do not overwrite, reformat, or revert unrelated changes.

## Development Setup

The repository expects a working Node.js/pnpm environment and a Python runtime
compatible with the project scripts. Follow [`docs/development.md`](docs/development.md)
for current setup details rather than duplicating version requirements here.

Install frontend dependencies when needed:

```powershell
cd web-dashboard
pnpm install
```

Use the repository's Python launcher so local and CI behavior stay aligned:

```powershell
node scripts/run_python.mjs -m pytest
```

## Branches and Commits

Create a focused branch from the current default branch. Keep each pull request
to one coherent concern.

Write commit messages that describe the actual result, for example:

```text
docs: clarify contributor verification rules
fix(server): reject encoded traversal paths
```

Do not use a stage name, copy the task prompt, or describe work that was not
actually completed.

## Architecture and Safety Rules

Unless a reviewed design explicitly requires otherwise:

- do not change the dashboard payload on only one side;
- update backend builders, frontend types, tests, and documentation together
  when public payload or behavior changes;
- do not give the frontend direct access to the Anki collection or profile
  filesystem;
- keep the dashboard server bound to localhost;
- do not weaken token validation, sanitizers, media validation, or action
  allowlists;
- do not log the dashboard token or a full token-bearing URL;
- do not turn card rendering into an iframe or JavaScript execution surface;
- do not edit generated dashboard assets manually;
- do not change correct production behavior only to satisfy a stale test;
- do not reintroduce removed routes, aliases, placeholders, or legacy layers
  without evidence that compatibility requires them.

The dashboard targets local desktop and laptop use. Mobile-first redesigns are
outside the normal scope unless explicitly agreed.

## Files That Must Not Be Committed

Do not commit runtime, user, generated, or local environment artifacts,
including:

```text
e2e-artifacts/
web-dashboard/dist/
web-dashboard/screenshots/
anki_study_report/web_dashboard/
anki_study_report/user_files/
*.ankiaddon
*.zip
__pycache__/
.pytest_cache/
node_modules/
```

Never include collection data, profile data, tokens, token-bearing URLs,
credentials, private paths, or personally identifying information in commits,
issues, logs, screenshots, Actions summaries, or uploaded artifacts.

## Verification

Choose verification according to the affected risk, not by habit.

For the canonical non-Docker aggregate:

```powershell
.\scripts\run_full_check.ps1 -SkipDocker
```

For focused frontend work:

```powershell
cd web-dashboard
pnpm run test:frontend
pnpm run build:addon
```

For focused Python work:

```powershell
node scripts/run_python.mjs -m pytest <relevant-tests>
```

For packaging changes:

```powershell
node scripts/run_python.mjs scripts/package_addon.py --check
```

Real-Anki Docker E2E is an integration gate, not the default edit loop. Run it
only when the change affects runtime startup, installed assets, card rendering,
media, lifecycle, or another risk identified by the current verification policy.
Do not repeat successful exact-SHA gates without a documented reason.

Documentation-only changes normally require syntax/content review and diff
checks, not Docker E2E.

## Pull Requests

A pull request should:

- explain the user or maintenance problem being solved;
- describe the actual implementation and its scope;
- identify API, payload, persistence, security, or migration implications;
- link related issues when applicable;
- list every verification command actually run and its result;
- explain why a normally relevant check was skipped;
- include screenshots for visible UI changes;
- disclose remaining limitations, risks, or follow-up work;
- contain no unrelated changes or generated/runtime artifacts.

A local pass does not override a failing GitHub check. Address review feedback
without silently expanding scope.

## Documentation

Update documentation when public behavior, architecture, routes, contracts,
configuration, verification policy, or release behavior changes. Keep durable
facts in the appropriate source-of-truth document instead of copying large
blocks into multiple files.

## Licensing Contributions

By submitting a contribution, you agree that it may be distributed under the
repository's [GNU General Public License v3.0](LICENSE). Only contribute material
you have the right to license. Clearly identify third-party code, data, media, or
other assets and their applicable terms.

## Community Conduct

Participation in this project is governed by
[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).
