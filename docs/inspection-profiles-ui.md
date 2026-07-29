# UI настроек Inspection Profiles

## Текущий маршрут

```text
#/settings/inspection-profiles
```

Авторитетный контракт взаимодействия:

- [Пошаговая настройка Inspection Profiles](guided-inspection-profiles.md).

Строгий сохраняемый формат:

- [Inspection Profiles v1](inspection-profiles-v1.md).

## Контур страницы

Страница сохраняет:

- боковую панель Settings;
- компактную сводку состояний;
- каталог с поиском.

Сводка состояний является информационным списком, а не псевдо-tabs. Поиск занимает полную ширину каталога; на широком layout каталог ограничен 280–320 px, а при 1024 px складывается над editor без двух узких колонок.

Произвольный тип заметки автоматически не выбирается. Содержательные элементы каталога остаются нативными кнопками и показывают:

- название типа заметки;
- фактическое состояние;
- понятный обнаруженный вид;
- количество полей и шаблонов.

Выбор ненастроенного типа немедленно создаёт детерминированный черновик только в browser. Открытие или переключение чистого созданного черновика не считается несохранённой пользовательской работой.

В обычном пути отсутствует отдельное действие `Use suggestion`.

## Basic

Basic открыт по умолчанию и читается как одна guided surface с последовательными milestones, а не как schema editor:

1. понятную сводку предложенной настройки и категорию confidence;
2. точные сопоставления полей Anki, показанные через понятные роли;
3. понятные требования, проецируемые на каждый строгий вид проверки v1;
4. понятный scope шаблонов карточек;
5. ограниченный результат validation и выборки;
6. одно основное действие с учётом жизненного цикла.

Вехи обычного пути: состояние, suggestion, используемые поля, требования, scope карточек, validation и confirmation. Field и requirement rows остаются самостоятельными интерактивными объектами, но секции разделяются типографикой и интервалами, а не вложенными panel/card.

На широком editor Basic использует ограниченную двухколоночную композицию:
сопоставления полей находятся слева, а требования и scope карточек — справа.
При ширине editor не более 760 px секции складываются в одну колонку; строки
сопоставления сохраняют подпись и selector рядом до 480 px. На QHD ширина
guided surface ограничена, чтобы форма не растягивалась на весь workspace.

Basic никогда не показывает:

- slugs ролей;
- ordinal шаблонов;
- стабильные ID проверок.

Basic не создаёт вторую сохраняемую модель.

## Advanced и инструменты

Basic и Advanced — взаимоисключающие tabs одного editor: Basic выбран по умолчанию, а Advanced заменяет его в том же месте и показывает strict editors с машинными идентификаторами. Переключение режима сохраняет один browser draft и само по себе не выполняет autosave, validation или confirm. Ошибки и dirty-state видны на tab Advanced.

Инструменты профиля — отдельный disclosure, содержащий:

- import;
- export;
- детерминированный reset;
- start empty;
- disable;
- delete.

Эти инструменты не конкурируют визуально с подтверждением.

Обычные и destructive tools разделены. Revision conflict — блокирующее inline-состояние непосредственно над action zone и сохраняет локальный черновик.

Ошибки Advanced обозначаются на tab. После явной неудачной validation фокус переходит на сводку ошибок; ссылки переключают режим и фокусируют соответствующие строгие элементы управления.

Ошибки, для которых существует Basic control, остаются в Basic: ссылка из
сводки переводит фокус на точный selector или input и сохраняет
`aria-invalid`/`aria-describedby`. Только Advanced-only ошибка переключает
режим перед переводом фокуса.

## Хранение и авторитетность

- autosave отсутствует;
- autoconfirm отсутствует;
- перед подтверждённым update v1 выполняется validate v2;
- авторитетны только `confirmed` и структурно актуальные профили;
- `needs_review` и `disabled` работают по принципу fail closed;
- конфликты revision сохраняют локальный пользовательский черновик.

## Responsive-цель

Основная цель — desktop и laptop.

На широких размерах используется split-компоновка каталога и editor. При 1024 px компоновка складывается без горизонтального overflow. Внутренние 3→2→1-column grids реагируют container queries на фактическую ширину editor, а не только на viewport.

Validation остаётся persistent inline рядом с action region; необязательный toast статичен и не перекрывает форму. Добавление требования переводит фокус в новый row; удаление — в следующий или предыдущий row, а при отсутствии соседей — в кнопку добавления. Пустое состояние использует одну поверхность без иллюстрации и прямо объясняет, что generated draft не сохраняется и не включается автоматически.

## Граница проверки

C1.5R.6 покрывает:

- детерминированные тесты компонентов, hook и проекции;
- backend-регрессию;
- typecheck;
- production-сборку;
- проверку пакета;
- каноническую проверку без Docker;
- настоящую матрицу Chromium в светлой и тёмной темах.

Docker и real-Anki и приёмка на приватном профиле владельца выполнены в C1.5R.7.


## Delivery checkpoint — 2026-07-29

Corrected WP2 evidence remains the frame baseline, but WP2 owner acceptance was
not granted and its visual debt remains open. The owner separately authorized
WP3 to proceed without accepting WP2.

```text
WP2 frame: CORRECTIVE CANDIDATE DELIVERED
WP2 external review: 7.8/10 (historical external assessment)
WP2 owner acceptance: NOT GRANTED
WP3 Basic: IMPLEMENTATION CANDIDATE DELIVERED
WP3 external visual review: PENDING
WP4 Advanced: NOT STARTED
Profiles acceptance: NOT READY
```

See the [corrected screenshot-first audit](../reports/core/c2-inspection-profiles-screenshot-audit.md)
and [WP3 Basic implementation report](../reports/core/c2-inspection-profiles-wp3-basic-implementation.md).
