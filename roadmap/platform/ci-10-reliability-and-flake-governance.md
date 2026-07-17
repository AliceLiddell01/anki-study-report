# CI Stage 10 — Reliability and flake governance

**Status:** Conditional

**Dependency:** CI Stage 7 должен показать повторяющиеся nondeterministic или
infrastructure failures. Один случайный сбой не запускает этот этап.

## Цель

Сделать причины красных runs классифицируемыми и воспроизводимыми, не превращая
retry в способ скрывать defects.

## Failure taxonomy

Каждый failed/cancelled run относится к одной категории:

```text
project regression
contract/test regression
confirmed flake
GitHub/registry/network infrastructure
runner provisioning
operator/input error
superseded cancellation
unknown
```

Категория подтверждается evidence. `unknown` не становится flake только потому,
что следующий run прошёл.

## Structured evidence

Fast CI и E2E summaries могут хранить bounded fields:

- failing phase/step;
- stable failure code;
- first failing test/task;
- runner image/version;
- retry/rerun relationship;
- whether tested SHA/package/image identity changed;
- artifact availability;
- classification и confidence.

Public reports сохраняют текущие redaction и privacy boundaries.

## Retry policy

Default остаётся `no automatic retry`.

Один bounded retry можно рассматривать только для заранее определённых
infrastructure classes, когда meaningful project execution ещё не началось либо
result доказанно не отражает project state. Первая attempt и retry сохраняются
как раздельное evidence и используют те же checkout/package/environment identity.

Test assertion, package mismatch, browser error, security validation или release
contract failure автоматически не повторяются.

## Flaky-test governance

Temporary quarantine допускается только когда:

- есть issue с owner и root-cause hypothesis;
- указан expiry/review date;
- тест продолжает запускаться как отдельный diagnostic;
- quarantine видна в summary;
- release/security/package critical checks остаются blocking.

Постоянный `skip`, broad exception catch и `continue-on-error` не считаются
исправлением flake.

## Determinism candidates

- stable random/time seeds;
- deterministic fixture reset;
- isolated temp/profile/database paths;
- explicit timezone/locale;
- bounded readiness and shutdown;
- no shared mutable files between workers;
- consistent screenshot/task ordering;
- simulated external services in automated tests.

Production behavior не меняется только ради нестабильного теста.

## Reliability budget

Отслеживаются failure rate, confirmed flake rate, infrastructure failure rate,
rerun rate, time to classification, runs без usable diagnostics и возраст
quarantined tests.

Stage 10 успешен, когда снижается unknown/flake rate и растёт first-run pass rate,
а не когда увеличивается число retries.

## Completion criteria

- taxonomy и stable codes покрыты tests;
- один failure не получает несовместимые категории;
- policy согласована с `verification-run-policy.md`;
- blind reruns и successful same-SHA repeats остаются запрещены;
- release path не ослаблен;
- quarantine имеет owner/expiry и не скрыта;
- trend report подтверждает улучшение reliability.

## Out of scope

- retry каждого failed job;
- автоматическое увеличение timeout;
- игнорирование browser/API/security errors;
- self-hosted runner как обход flaky hosted environment;
- снижение test coverage;
- product fallback, которого нет в production contract.
