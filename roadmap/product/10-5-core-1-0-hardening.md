# Указатель совместимости — прежний Stage 10.5

Этот путь сохранён, чтобы исторические ссылки не ломались.

Core 1.0 Hardening является этапом **C2** в авторитетном [треке Core](../core/README.md).

C2:

- реализован;
- прошёл exact-SHA Fast CI, targeted `standard/cards` с restart и final `standard/full`;
- влит в `core` merge commit `edb140b1197910aae31500a40e4a8287cc46b760`.

После merge ручная проверка владельца выявила незакрытые Cards/Inspection Profiles/motion regressions. Их исправление является append-only границей приёмки C2, а не новым `C2.x` этапом.

C2 больше не является последним обязательным этапом перед Core 1.0. Актуальный путь продолжается через C3–C6, определённые в authoritative Core roadmap.

Этот этап не перестраивает CI/CD. За инфраструктуру поставки отвечает независимый [трек Platform / CI](../platform/README.md).
