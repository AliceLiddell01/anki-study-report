# Индекс исторической product-roadmap

`roadmap/product/` сохраняет принятую историческую последовательность Stage 0–9.5. Будущая работа организована по независимым трекам и больше не использует одну глобальную очередь Stage 10–13.

## Завершённый продуктовый контур

```text
Stage 0   Foundation / Legacy Cleanup
Stage 1   Navigation / IA
Stage 2   Settings Hub
Stage 3   Profile MVP
Stage 4   Activity / Calendar v2
Stage 5   Decks v2
Stage 5.5 UI Polish & Global Controls
Stage 6   Statistics v1
Stage 7   FSRS Analytics & Localization Closure
Stage 8   Search Query / Search v1 / Safe Actions
Stage 9   Notices / Telemetry / Signals / Notifications
```

## Актуальные треки

- [Core](../core/README.md): `C1 → C2 → manual acceptance closure → C3 UI & Shell → C4 Data Independence → C5 Today v2 → C6 Profile v2 → Core 1.0`.
- [Gamification](../gamification/README.md): параллельный research/product track `G0–G8`; production не одобрен.
- [Telemetry operations](../operations/README.md): защищённый внутренний трек `O`.
- [Identity continuity](../identity/README.md): условный `I1`.
- [Extension ecosystem](../extensions/README.md): условный/отложенный `E1–E4`.
- [Platform / CI](../platform/README.md): независимый CI/CD/E2E track.

`C1.6B` не входит в обязательную очередь. Прежний Stage 11/`C3 Contextual Additions` больше не является зарезервированным этапом: contextual additions допускаются только как отдельные доказанные предложения.

## Compatibility paths

Прежние файлы Stage 10–13 и `unscheduled-*` остаются по существующим путям как короткие указатели. Это сохраняет исторические ссылки и не создаёт вторую конкурирующую roadmap.

Каноническое текущее поведение находится в `docs/`; исторические доказательства — в `reports/`; обязательный будущий путь — в `roadmap/core/README.md`.
