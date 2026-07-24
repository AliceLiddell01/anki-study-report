# Трек Extension Ecosystem

**Трек:** `E`  
**Роль:** условная first-party extension architecture  
**Текущий статус:** `E1` — conditional

Core должен оставаться полноценным и releasable без extension system. Трек начинается только с конкретного first-party reference pack.

## Карта

```mermaid
flowchart LR
    N{Есть named reference pack?}
    N -->|нет| D[Track deferred]
    N -->|да| E1[E1 Contract discovery]
    E1 --> G{Minimal contract justified?}
    G -->|нет| C[Оставить workflow в Core или отказаться]
    G -->|да| E2[E2 Pack foundation]
    E2 -. concrete analytics need .-> E3[E3 Analytics pack]
    E2 -. separate evidence .-> E4[E4 Additional packs]
```

## Этапы

| Этап | Статус | Цель | Completion |
| --- | --- | --- | --- |
| **E1 Contract discovery** | Conditional | Вывести минимальный contract из одного approved reference pack | proposal доказывает каждую capability и отклоняет speculative surface |
| **E2 Minimal foundation** | После E1 | Реализовать versioned fail-closed first-party extension points | install/update/uninstall/recovery проходят; Core работает без pack |
| **E3 Analytics pack** | Conditional | Вынести один optional/expensive analytical workflow | pack отдельно удаляем, metrics canonical, Core performance/data не затронуты |
| **E4 Additional packs** | Deferred | Добавлять один evidence-backed first-party pack за раз | у каждого pack есть owner, security review и maintenance case |

## Invariants

- никаких unsigned remote code, generic iframe/JavaScript plugins или arbitrary UI slots;
- frontend pack не получает прямой collection access;
- capability allowlist и compatibility versioned;
- package/tests/lifecycle отделены от Core;
- token, sanitizer, action и media boundaries сохраняются;
- marketplace и third-party ecosystem не подразумеваются.

## Activation criteria

E1 требует named workflow, ownership, maintenance plan и доказательство, что функция не должна оставаться bounded Core addition. E2–E4 не активируются заранее.
