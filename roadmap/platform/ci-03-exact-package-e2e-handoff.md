# CI Stage 3 — Exact-package E2E handoff

**Status:** Complete

- Manual/reusable Docker E2E принимает `fast_ci_run_id`.
- Проверяет repository/run/SHA/result/artifact metadata fail-closed.
- Скачивает exact package и использует его как tested input.
- Diagnostics и package artifacts остаются раздельными.
- Release artifact path сохраняет тот же принцип exact identity.

Повторный source build допустим только как явно обозначенный diagnostic mode, но не заменяет final exact-package evidence.
