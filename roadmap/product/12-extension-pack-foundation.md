# Stage 12 — Extension Pack / DLC Foundation

**Status:** Planned

## Цель

Создать минимальные безопасные extension points для first-party optional functionality и снизить зависимость от сторонних add-ons, не превращая core в marketplace или хост произвольного загружаемого кода.

## Предпосылки

- Core 1.0 contracts и migrations зафиксированы.
- Cards/Signals/Statistics boundaries стабильны.
- Есть конкретный first-party reference pack, который доказывает необходимость API.

## Предлагаемый scope

- versioned pack manifest;
- explicit capability allowlist;
- local installation/discovery lifecycle;
- compatibility checks against core version;
- ограниченные data/query extension points через Python runtime;
- typed UI contribution slots только там, где есть reference workflow;
- separate packaging, tests и uninstall/recovery behavior;
- no direct frontend access to collection;
- no arbitrary network privilege.

## Обязательный reference pack

Foundation не принимается без одного first-party pack, реализующего реальную функцию и доказывающего минимальность extension API. Конкретный pack выбирается отдельным продуктовым решением; foundation не должна заранее поддерживать все гипотетические integrations.

## Out of scope

- marketplace;
- загрузка и выполнение неподписанного удалённого кода;
- unsigned third-party scripts;
- generic iframe/web plugin surface;
- account/cloud sync;
- автоматическая миграция функций сторонних add-ons без лицензирования и contract review.

## Completion criteria

- Один reference pack проходит install/update/uninstall/recovery.
- Core работает без pack.
- Pack не может обходить token/sanitizer/action/media boundaries.
- Version/capability negotiation fail-closed.
- Packaging и release артефакты core/pack разделены.
