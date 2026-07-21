# Передача контекста ИИ — Anki Study Report

**Снимок:** 2026-07-22

## С чего начать

Читайте источники в таком порядке:

1. [`../README.md`](../README.md);
2. этот файл;
3. [`../roadmap/README.md`](../roadmap/README.md);
4. [`../roadmap/core/README.md`](../roadmap/core/README.md);
5. актуальные production-код и тесты в пределах задачи;
6. профильный контракт и последний отчёт соответствующего этапа.

При противоречиях используйте следующий приоритет:

```text
актуальные production-код и тесты
→ актуальные README и профильные документы
→ свежие отчёты и артефакты
→ старые планы и сообщения
→ предположения
```

Не утверждайте, что файл, артефакт или участок кода изучен, если он фактически не был открыт.

## Текущее состояние проекта

Anki Study Report — локальный add-on для Anki 26.05+ с Python runtime и React/TypeScript dashboard.

Dashboard:

- доступен только через loopback-интерфейс;
- защищён токеном;
- получает ограниченные JSON/API-проекции;
- не предоставляет frontend прямой доступ к collection.

Принятый продуктовый контур до Stage 9.5 завершён.

Текущий статус Core:

```text
ветка: core
C1.5R.0–R.7: завершено
продуктовая приёмка C1.5R владельцем: выполнена
C1.6: завершено; принято владельцем; влито в core
C1.6B: условный этап; не начат
Core C1: завершён
C2: следующий этап; не начат
```

Head ветки Core после C1.6:

```text
928e3fe749ce6aa4b9c414641c4ef66ac46a694b
```

PR C1.6:

```text
#125 — Add canonical single-card resolution loop
влит в core через rebase
```

## Актуальные отчёты

- [`../reports/core/c1-5r-0-recovery-baseline.md`](../reports/core/c1-5r-0-recovery-baseline.md);
- [`../reports/core/c1-5r-1-canonical-card-display-identity.md`](../reports/core/c1-5r-1-canonical-card-display-identity.md);
- [`../reports/core/c1-5r-2-declarative-compact-formatter-runtime.md`](../reports/core/c1-5r-2-declarative-compact-formatter-runtime.md);
- [`../reports/core/c1-5r-3-front-back-preview-semantics.md`](../reports/core/c1-5r-3-front-back-preview-semantics.md);
- [`../reports/core/c1-5r-4-independent-triage-candidate-sources.md`](../reports/core/c1-5r-4-independent-triage-candidate-sources.md);
- [`../reports/core/c1-5r-5-cards-attention-inbox-redesign.md`](../reports/core/c1-5r-5-cards-attention-inbox-redesign.md);
- [`../reports/core/c1-5r-6-guided-inspection-profiles-ux.md`](../reports/core/c1-5r-6-guided-inspection-profiles-ux.md);
- [`../reports/core/c1-5r-7-integrated-acceptance-closeout.md`](../reports/core/c1-5r-7-integrated-acceptance-closeout.md);
- [`../reports/core/c1-6-canonical-single-card-resolution-loop.md`](../reports/core/c1-6-canonical-single-card-resolution-loop.md).

## Исторический C1.5

Исторические запуски Fast CI и real-Anki для C1.5 подтверждают работоспособность прежней реализации, но не являются подтверждением приёмки текущего UX после отклонения владельцем.

C1.5R заменил отклонённые части:

```text
R1 каноническая идентичность отображения карточки
R2 декларативный компактный форматтер
R3 семантика предпросмотра лицевой и обратной стороны
R4 независимые источники кандидатов
R5 очередь Cards, построенная вокруг идентичности карточки
R6 пошаговая настройка Inspection Profiles
R7 комплексная приёмка
```

## Актуальные контракты Cards

Основные документы:

- [`cards-v2-product-contract.md`](cards-v2-product-contract.md);
- [`cards-v2-triage-read-api.md`](cards-v2-triage-read-api.md);
- [`cards-v2-resolution-loop.md`](cards-v2-resolution-loop.md);
- [`cards-attention-inbox.md`](cards-attention-inbox.md);
- [`card-display-identity.md`](card-display-identity.md);
- [`card-preview-semantics.md`](card-preview-semantics.md);
- [`inspection-profiles-v1.md`](inspection-profiles-v1.md);
- [`guided-inspection-profiles.md`](guided-inspection-profiles.md).

## Компактная идентичность карточки

Модуль `anki_study_report/card_display_identity.py` отвечает за компактную идентичность конкретной карточки.

Последовательность fallback:

```text
вопрос из Browser
→ лицевая сторона reviewer
→ media_only | unavailable
```

Поля wire-контракта:

```text
displayText
displaySource      browser_question | reviewer_front | none
displayStatus      available | media_only | unavailable
displayTruncated
```

Одну backend-проекцию используют строки и подробности Search, элементы Triage, очередь Cards и заголовок Inspector.

Поле `primaryText` у Card отсутствует. Search в режиме заметок сохраняет `primaryText` заметки.

## Семантика предпросмотра

- Inspector показывает санитизированную нативную лицевую сторону;
- расширенный модальный диалог показывает санитизированную нативную обратную сторону;
- полный предпросмотр загружается только для активной карточки;
- строки очереди не читают media и не рендерят полный HTML;
- sanitizer, проверка media и изоляция Shadow DOM обязательны.

## Источники кандидатов Triage v4

Запрос Triage v4 разделяет:

- кандидатов по учебной активности за ограниченный период;
- кандидатов по текущему содержимому с ограниченным объёмом;
- активные Signals;
- идентичность Search.

Проверка текущего содержимого:

- использует только подтверждённые и актуальные Inspection Profiles;
- имеет keyset-ограничение в 500 заметок на запрос;
- продолжение выполняется через явный cursor;
- автоматический цикл по cursor отсутствует;
- representative card выбирается детерминированно;
- предпросмотр и media не читаются.

## Очередь карточек, требующих внимания

Каноническая компоновка:

```text
>= 1200 px: плотная семантическая очередь + постоянный Inspector
< 1200 px: очередь на всю ширину + немодальная выдвижная панель
```

Очередь — упорядоченный семантический список с одной нативной кнопкой на элемент. Это не таблица, ARIA `grid`, `listbox` или составной элемент с roving tabindex.

Период обучения: 7, 30 или 90 дней. Продолжение проверки текущего содержимого запускается вручную и ограничено на клиенте: до 500 уникальных элементов и 10 дополнительных страниц.

## Пошаговая настройка Inspection Profiles

Обычный путь:

```text
конкретный тип заметки
→ немедленно создаваемый чистый черновик Basic
→ ограниченная проверка и выборка
→ явное подтверждение
```

Basic предоставляет понятную проекцию строгого документа v1. Advanced сохраняет точные ID, mappings, checks и область шаблонов. Автосохранение и автоподтверждение отсутствуют.

Причины по содержимому создают только подтверждённые и актуальные профили. Состояния `suggested`, `disabled` и `needs_review` работают по принципу fail closed.

## C1.6 — канонический цикл решения проблемы одной карточки

C1.6 завершён, принят владельцем и влит в `core`.

Кандидат реализации и runtime:

```text
edaf9030dbba355593e52cf8922d4c7985ce4b75
```

Финальный head PR:

```text
9e4b74b0bc3a0a34590217550a7e8be4263c7fd6
```

Коммит после вливания в Core:

```text
928e3fe749ce6aa4b9c414641c4ef66ac46a694b
```

Жизненный цикл:

```text
проблема
→ существующий Safe Action или Open in Anki
→ результат действия
→ Awaiting recheck
→ каноническая ограниченная перепроверка конкретной карточки
→ Still active | Partially resolved | Resolved | Recheck failed | Evidence stale
```

### API

```text
POST /api/triage/query    schema v4
POST /api/triage/recheck  schema v1
```

Запрос перепроверки содержит одну конкретную карточку, ожидаемый ID заметки, от одного до четырёх стабильных ID причин и текущую область проверки.

Backend переиспользует канонические детекторы Triage v4 через сериализованный `QueryOp`. Второй стек детекторов отсутствует.

### Правила определения результата

- успешное действие и `action.no_changes` не доказывают устранение проблемы;
- Open in Anki является передачей управления, а не доказательством изменения;
- оставшиеся причины обновляют элемент на месте;
- сочетание удалённых и оставшихся причин даёт состояние Partially resolved;
- новые причины показываются явно;
- отсутствие причин удаляет элемент только при полностью авторитетном результате;
- частичный, недоступный, ошибочный, устаревший, отсутствующий или изменившийся результат работает по принципу fail closed;
- после удаления элемента фокус восстанавливается детерминированно.

### Вне scope

- массовый выбор;
- ручные resolve, archive и snooze;
- постоянное состояние завершения;
- вторая система действий или детекторов;
- неограниченная повторная оценка;
- C1.6B.

### Проверка

```text
профильные backend- и E2E-вспомогательные тесты: 81 тест, PASS
frontend: 324 теста, PASS
Python compileall: PASS
production-сборка и ограничение bundle: PASS — 429 516 байт
пакет: PASS — 77 записей
каноническая проверка без Docker: PASS — 324 frontend-теста, 802 Python-теста, 5 пропусков платформенных тестов
Fast CI 29862254960: PASS
Fast CI для финального head 29863609253: PASS
целевой standard/cards с перезапуском 29862551442: PASS
финальный standard/full 29862800106: PASS
```

Отдельная проверка C1.6 на приватном профиле Anki владельца не выполнялась. Локальный Docker не повторял успешные cloud E2E-запуски с точным пакетом.

## Следующее точное действие

Следующий обязательный этап Core:

```text
C2 — Core 1.0 Hardening
```

Перед реализацией C2 требуется отдельная задача на продуктовую и техническую проработку. Не начинать C1.6B без отдельного подтверждения необходимости и решения владельца.

Не выполнять как неявное продолжение:

- merge в `master`;
- выпуск;
- deployment;
- публикацию `.ankiaddon` или на AnkiWeb;
- расширение функций C3.

## Границы проверки

Используйте:

- [`test-matrix.md`](test-matrix.md);
- [`verification-run-policy.md`](verification-run-policy.md).

Тяжёлый real-Anki E2E остаётся интеграционным gate. Не повторяйте успешные запуски для того же SHA без конкретной причины.

## Технические инварианты

Запрещено:

- односторонне менять публичный payload или schema;
- предоставлять frontend прямой доступ к collection;
- привязывать сервер к интерфейсу, отличному от `127.0.0.1`;
- ослаблять проверку токена, sanitizer, проверку media или allowlist действий;
- логировать токен или полный URL с токеном;
- создавать поверхность выполнения JavaScript через iframe или шаблоны;
- вручную редактировать сгенерированные assets dashboard;
- коммитить логи, скриншоты, cache, данные профиля, токены, `.ankiaddon` или результаты E2E;
- менять корректное production-поведение ради устаревшего теста;
- создавать второй стек запросов, действий, сигналов или детекторов;
- определять устранение проблемы на клиенте только по успеху действия или исчезновению элемента из очереди;
- начинать C1.6B, C2 или C3 без отдельной границы задачи.

## Другие треки

Геймификация, эксплуатация телеметрии, непрерывность идентификации, расширения и платформенные работы независимы. Они не блокируют C2 без явно зафиксированной зависимости.

## Границы работы с Git

Работайте в целевой ветке, указанной владельцем или задачей. Для Core по умолчанию используется `core`.

Не выполнять автоматически:

- merge или rebase в `master`;
- выпуск, deployment или публикацию;
- force-push;
- разрушительные reset, clean или удаление stash;
- перезапись несвязанных изменений.

Сообщения коммитов должны описывать фактически выполненное изменение.
