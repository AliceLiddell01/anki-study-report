## Summary

<!-- What problem does this pull request solve, and what changed? -->

## Scope

<!-- State the intended scope and any explicitly out-of-scope work. -->

## Related issue

<!-- Use "Closes #123" when applicable. -->

## Affected areas

- [ ] Python add-on runtime
- [ ] Dashboard API or payload
- [ ] React/TypeScript frontend
- [ ] Persistence or configuration
- [ ] Card rendering, HTML, CSS, or media
- [ ] Packaging or release
- [ ] GitHub Actions, CI, or Docker E2E
- [ ] Documentation only

## Contract and security impact

- [ ] No public API, payload, route, persistence, or configuration contract changed.
- [ ] Backend, frontend types, tests, and documentation were updated together where a contract changed.
- [ ] Token validation, localhost binding, sanitizers, media validation, action allowlists, and artifact redaction remain intact.
- [ ] The change does not introduce iframe/JavaScript card execution or direct frontend access to the Anki collection.

<!-- Explain any checked item that needs qualification. -->

## Verification

<!-- List the exact commands actually run and their results. Do not list planned checks as completed. -->

```text
command: result
```

### Docker / real-Anki verification

<!-- State the exact mode/scope and run when used. If not run, explain why it was not required by the verification policy. -->

## UI evidence

<!-- Add before/after screenshots for visible changes. Review all images for tokens, token-bearing URLs, collection/profile data, credentials, and private paths. -->

## Documentation

- [ ] Relevant documentation was updated.
- [ ] No documentation change was needed because public behavior and contracts are unchanged.

## Final checklist

- [ ] I inspected the current code and tests that define the affected contract.
- [ ] I did not overwrite or revert unrelated changes.
- [ ] Commit messages describe the actual completed changes.
- [ ] No generated/runtime artifacts, logs, screenshots, caches, profiles, tokens, `.ankiaddon`, or E2E outputs were committed.
- [ ] No secrets, personal information, collection content, or private paths were added to code, history, logs, or artifacts.
- [ ] The pull request is focused and remaining limitations or follow-up work are disclosed below.

## Remaining risks or follow-up work

<!-- Write "None known" only after considering unverified behavior and deferred work. -->
