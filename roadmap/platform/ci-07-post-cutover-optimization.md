# CI Stage 7 — Post-cutover optimization

**Status:** Conditional

Этап выполняется только после CI Stage 6 и новых измерений.

Возможный scope:

- E2E startup/runtime bottlenecks после исключения environment build;
- scope/worker scheduling;
- artifact compression/size;
- flake classification и retry policy;
- Fast CI setup/cache phases по structured timing;
- quota/minute budget.

Нельзя заранее менять caches, runner, test coverage или verification gates без baseline и expected saving. Успешный gate не повторяется «для уверенности».
