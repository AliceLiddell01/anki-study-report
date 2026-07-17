# CI Stage 2 — Exact Fast package producer

**Status:** Complete

Fast CI производит проверенный `.ankiaddon`, metadata и diagnostics как раздельные artifacts. Package identity связывается с tested/head/base SHA, ZIP integrity и package validation. PR-safe workflow не публикует release.

## Dependency

Этот этап сделал возможным Stage 3: real-Anki E2E может тестировать не повторную source build, а exact package из Fast CI.
