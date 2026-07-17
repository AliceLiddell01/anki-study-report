# CI Stage 1 — Gated delivery baseline

**Status:** Complete

## Результат

- Fast CI и PR-safe release validation разделены от production publication.
- Production release запускается только вручную с version/channel inputs.
- Exact artifact, approval Environment и AnkiWeb/GitHub publication gates.
- Merge/push сами по себе не публикуют release.
- Дублирующий Windows release build на PR устранён/ограничен manual delivery path.

## Canonical docs

- `docs/ci-cd.md`
- `docs/release-automation.md`
- `docs/packaging-release.md`
