# Stage 3 — Profile MVP

**Status:** Complete

## Первоначальный план

Сделать заметный локальный профиль без аккаунтов и social-функций: nickname/description/avatar, дата начала обучения, сортировка колод, профильные KPI и support link.

## Фактически выполнено

- `#/profile` стал отдельной all-collection surface, независимой от dashboard scope.
- Lifetime KPI, activity summary и deck overview.
- Per-profile persistence для пользовательской даты начала и сортировки.
- Profile identity остаётся локальной; remote account/sync отсутствуют.
- Support ведёт на безопасную внешнюю ссылку через profile menu.

## Изменение плана

Профиль не превратился в общую таблицу статистики или вторую Settings page. Scope/report controls окончательно остались в Settings Hub.

## Canonical docs

- `docs/profile-mvp.md`
- `docs/navigation-ia.md`
- `docs/settings-hub.md`
