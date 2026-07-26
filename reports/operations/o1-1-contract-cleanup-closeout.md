# O1.1 — исправление Operations topology и contract review

- Дата: `2026-07-26`
- Статус: **Complete / reviewable contract**
- Public base: `operations` от `core@62cd4c1fc1dda6354f3e30cb3ae4aee5dfb4891f`
- Canonical telemetry review:
  [PR #19](https://github.com/AliceLiddell01/anki-study-report-telemetry/pull/19)

## Результат

O1.1 зафиксировал versioned Metric Registry, fixed Query Registry, source
boundary, suppression semantics и будущую Admin security boundary в private
telemetry repository. Public repository хранит только безопасный status,
архитектурные границы и ссылки; private registry contents не копируются.

Telemetry PR #19:

- направлен в `operations`, а не `master`;
- остаётся draft, auto-merge выключен;
- имеет русский Markdown body с реальными переносами;
- содержит отдельный dependency cleanup для двух OSV findings;
- не заявляет deployment или merge.

## Исправление ошибочной попытки

Public PR #147 оставлен закрытым и unmerged. Он не переоткрывался и не
retargeted, потому что был основан на `master`, имел literal `\n` в body и не
отражал Operations integration boundary.

Полезные public-safe решения перенесены вручную на clean branch от exact
`core`; commits или merge history из неправильной `master`-ветки не
переносились.

После публикации replacement PR #148 remote branch
`agent/o1-1-operations-roadmap` удалена как obsolete. Открытых PR на неё не
было; исходные commits остаются восстановимыми по закрытому PR #147 и SHA
`991f53d3e43829f1b1c0dad77e8946d28a2cc8e6`.

## OSV blocker

Фактический CI log run `30178730833` показал:

- `GHSA-mh99-v99m-4gvg`: `brace-expansion 5.0.7`, fixed `5.0.8`;
- `GHSA-f88m-g3jw-g9cj`: `sharp 0.34.5`, fixed `0.35.0+`.

Исправление обновляет совместимые direct parent dependencies и lockfile:
`brace-expansion 5.0.8`, `sharp 0.35.2`. Scanner, severity policy и workflow не
ослаблялись.

## Не выполнялось

- merge в telemetry `operations`, `master` или main `core`;
- staging/production migration или deployment;
- Admin API/UI/Access;
- provider collector;
- Docker/real-Anki E2E;
- release.
