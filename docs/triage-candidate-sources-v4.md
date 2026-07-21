# Источники кандидатов Triage v4

Triage v4 разделяет зависящую от периода историю обучения и текущее содержимое коллекции, не зависящее от выбранного периода.

## Семантика источников

- `learningCandidates` читает ограниченную историю повторений за запрошенный период.
- `contentCandidates` независимо от периода сканирует текущие notes/cards.
- `signals` остаётся существующим независимым источником.
- `search_workset` остаётся режимом точного набора карточек и не запускает автоматические loaders.

## Граница авторитетного профиля

Автоматический content scan разрешён только для профилей, у которых:

- сохранённое состояние равно `confirmed`;
- fingerprint совпадает с текущей структурой note type;
- присутствует хотя бы одна проверка.

Профили в состояниях `suggested`, `disabled` и `needs_review` учитываются в status, но не читают значения полей заметок.

## Ограничения и continuation

Loader текущего содержимого сканирует не более 500 note IDs за один запрос:

```text
note.id > contentCursor
order by note.id asc
limit 501
```

Затем выполняется одно пакетное чтение cards/notes. Offset pagination, автоматического continuation loop и глобального запроса общего количества нет. `nextCursor` присутствует только тогда, когда источник усечён.

## Scope и representative card

Пустой список `deckIds` означает все колоды. Выбранная родительская колода включает потомков через существующую семантику расширения deck scope. Suspended и buried cards остаются допустимыми, поскольку качество содержимого не зависит от scheduling state.

Каждая note проверяется один раз и привязывается к минимальному подходящему card ID внутри scope. Sibling count охватывает все текущие карточки этой note.

## Объединение и payload

Learning, signal и content reasons объединяются по card. Через каноническую Search display identity разрешаются только карточки, у которых есть reasons.

Наружу не передаются raw fields, HTML, названия медиафайлов, SQL, пути и текст исключений.

## Граница R5

R4 типизирует и проверяет continuation state, но не добавляет видимый control загрузки следующей страницы и не перестраивает Cards inbox. Эта продуктовая работа относится к C1.5R.5.

## Завершение проверки

Точный implementation commit:

```text
31b3b795e055f6be963c129b3edc1afdfc9dcd57
```

Изолированный run `29701478622` успешно прошёл:

- focused backend и frontend tests;
- typecheck;
- production build;
- package build/validation;
- API smoke;
- canonical non-Docker gate;
- Git hygiene.

Post-transfer run `29701642665` повторил затронутые focused checks на точном commit ветки `core` и также прошёл успешно.

Fast CI и Docker/real-Anki E2E для R4 не требовались. C1.5R.5 оставался отдельной продуктовой работой и не запускался этим closeout.