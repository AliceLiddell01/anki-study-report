# UI настроек Inspection Profiles

## Текущий маршрут

```text
#/settings/inspection-profiles
```

Авторитетный interaction contract:

- [Guided Inspection Profiles](guided-inspection-profiles.md).

Строгий persisted format:

- [Inspection Profiles v1](inspection-profiles-v1.md).

## Контур страницы

Страница сохраняет:

- Settings sidebar;
- compact summary состояний;
- searchable catalog.

Произвольный note type автоматически не выбирается. Содержательные catalog entries остаются native buttons и показывают:

- название note type;
- effective state;
- понятный detected kind;
- количество fields/templates.

Выбор unconfigured type немедленно создаёт детерминированный browser-only generated draft. Открытие или переключение clean generated draft не считается несохранённой пользовательской работой.

В normal path отсутствует отдельное действие `Use suggestion`.

## Basic

Basic открыт по умолчанию и содержит:

1. понятную сводку suggested setup и категорию confidence;
2. exact Anki field mappings, показанные через понятные roles;
3. понятные requirements, проецируемые на каждый strict check kind v1;
4. понятный scope card templates;
5. bounded validation/sample result;
6. одно lifecycle-aware primary action.

Basic никогда не показывает:

- role slugs;
- template ordinals;
- stable check IDs.

Basic не создаёт вторую persisted model.

## Advanced и tools

Advanced — native disclosure со strict editors и machine-level identifiers.

Profile tools — отдельный disclosure, содержащий:

- import;
- export;
- deterministic reset;
- start empty;
- disable;
- delete.

Эти tools не конкурируют визуально с confirmation.

Hidden Advanced errors обозначаются снаружи collapsed panel. После явного failed validation focus переходит на error summary; links раскрывают и фокусируют соответствующие strict controls.

## Persistence и authority

- autosave отсутствует;
- autoconfirm отсутствует;
- перед confirmed update v1 выполняется validate v2;
- авторитетны только `confirmed` и structurally current profiles;
- `needs_review` и `disabled` работают fail closed;
- revision conflicts сохраняют локальный пользовательский draft.

## Responsive target

Основная цель — desktop/laptop.

На широких размерах используется split catalog/editor. На 1024 px layout складывается без horizontal overflow. Advanced остаётся collapsed, чтобы normal path не был подчинён strict editor.

## Граница проверки

C1.5R.6 покрывает:

- deterministic component/hook/projection tests;
- backend regression;
- typecheck;
- production build;
- package validation;
- canonical non-Docker verification;
- real Chromium light/dark matrix.

Docker/real-Anki и acceptance на приватном профиле владельца были выполнены в C1.5R.7.