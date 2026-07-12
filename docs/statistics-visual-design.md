# Визуальный контракт Statistics

Статус: реализован поверх Statistics v1 без изменения metric, cache и API
semantics.

## Baseline audit

Проверен artifact GitHub Actions `29171975230` для Stage 6, включая пять
маршрутов в light/dark и `stats-overview`/`stats-decks` при 125%.

Baseline был функционально корректным, но выглядел как scaffold:

- header, controls, KPI и charts лежали на одном плоском фоне без явной
  иерархии;
- KPI были голыми числами без surfaces и comparison context;
- Overview показывал `reviews + seconds`, `percent + seconds` и
  `introduced + reviews` одинаковыми grouped bars на общей шкале;
- Quality смешивал процент успешности с Pass/Fail counts;
- Load показывал будущую нагрузку прежде всего таблицей;
- Deck comparison открывался без выбранных строк и без primary chart;
- sparse fixture оставляла огромные пустые plot areas и один доминирующий
  последний bucket;
- пользователю были видны `STATISTICS V1`, `True Retention`, `Daily load`,
  `Mature`, `Learning`, `Review`, `Relearning` и формула daily load.

Baseline artifact не входит в Git.

## Цели и иерархия

Statistics — личный аналитический центр, а не debug page или settings form.
Каждый маршрут использует четыре уровня:

1. identity маршрута и secondary action для native Anki Statistics;
2. grouped query surface с coverage;
3. factual insight и KPI context;
4. analytical panels, затем supporting tables/definitions.

Важнейший вывод расположен выше KPI и графиков. Основной chart занимает больше
места, чем secondary small multiples. Whitespace разделяет смысловые группы,
но не создаёт пустые области вокруг микроскопических bars.

## Surface system

Statistics переиспользует общие radius, border, shadow, typography, form и
focus tokens. Внутри маршрута есть три уровня:

- page/query/insight surfaces;
- KPI и primary analytical panels;
- nested summaries, direct legends, definitions и table disclosures.

Light theme использует нейтральные бело-серые panels поверх общего голубого
canvas; dark theme отделяет panels borders и controlled elevation. Цветные
surfaces не используются как набор rainbow KPI tiles.

## Semantic palette

Palette централизована CSS variables и одинаково назначена во всех маршрутах:

| Семантика | Базовый цвет |
| --- | --- |
| Повторения | blue/cyan |
| Время учёбы | purple |
| Новые/введённые | green |
| Успешность | teal |
| Предыдущий период | muted neutral + dashed outline |
| Снова | red |
| Трудно | amber |
| Хорошо | teal |
| Легко | cyan |
| Изучение | purple |
| Повторение | blue |
| Переучивание | coral |
| Молодые / зрелые | blue / green |
| Приостановленные | muted neutral |
| Скрытые | patterned neutral |

Light/dark имеют отдельные значения с той же semantic identity. Alert colors
не назначаются обычной величине только ради декора.

## Chart selection и mixed units

Chart выбирается по аналитическому вопросу:

- trend — line;
- discrete amount — zero-origin bar;
- part-to-whole — stacked strip/columns;
- deck comparison — ranked bars с direct labels.

Count, seconds, percentage, cards и notes не делят одну простую числовую
шкалу. Overview и past Load используют separate panels/small multiples.
Quality разделяет success rate line и stacked Pass/Fail volume. Bar и stacked
axes начинаются с zero. Dual axes и normalization не используются.

Recharts уже входил в Stage 6 baseline через Home, поэтому новая chart library
не добавлена. Shared primitives находятся в
`web-dashboard/src/components/statistics/StatisticsCharts.tsx`; semantic
presentation helpers и palette mapping — в соседнем
`statisticsPresentation.ts`.

## Comparison

KPI comparison использует:

- relative percent для counts/time;
- percentage points для rates;
- explicit `Нет сопоставимых данных` вместо fake `0%`;
- muted dashed outline и текст, то есть различие не только цветом;
- neutral direction: рост нагрузки не объявляется автоматически good/bad.

Backend не публикует previous-period bucket series. Frontend не реконструирует
и не выдумывает такую линию: charts остаются current-only, а доступный
aggregate comparison показывается в KPI.

## Sparse и missing data

- `null` остаётся пропуском; Recharts `connectNulls=false`;
- отсутствующие значения не превращаются в zero;
- covered all-zero series получает explicit factual zero state вместо пустого
  plot;
- single-point series объясняется текстом и не интерполируется;
- каждый chart имеет visible summary и expandable table;
- rate/time summaries показывают диапазон, а не бессмысленную сумму;
- bar axes не обрезаются.

## Терминология

Primary UI использует русские пользовательские labels: `Ежедневная нагрузка`,
`Истинное удержание`, `Зрелые`, `Изучение`, `Повторение`, `Переучивание`,
`Снова`, `Трудно`, `Хорошо`, `Легко`. Точное определение daily load и true
retention доступно через `Как считается`, но формула и developer labels не
являются primary content. Имена колод и другие пользовательские данные не
переводятся.

## Composition по маршрутам

### Обзор

Factual insight, шесть KPI с comparison context, primary reviews trend,
отдельные time/success/answer-time trends и introduced bars. Никаких
mixed-unit grouped charts.

### Качество

Success rate line отделён от stacked answer volume. Кнопки ответа показаны как
100% part-to-whole strip с counts и percentages. Истинное удержание имеет
отдельный panel, young/mature split, sample и confidence.

### Нагрузка

KPI: overdue, 7/30-day due и active-day average. Past reviews/time/new cards
разделены. Future due — stacked columns по типам очереди; table остаётся
structured alternative. Assumptions показаны рядом.

### Прогресс

Cards и notes — отдельные KPI. Current collection states — part-to-whole
snapshot с direct legend. Introduced trend не притворяется historical
young/mature state series.

### Колоды

Frontend детерминированно выбирает до трёх достаточных/предварительных root
groups с наибольшим числом reviews. Ranked success bars видны при первом
открытии; reviews остаются secondary text, а не общей шкалой. Таблица сохраняет
выбор и полный набор фактов; selected rows имеют checkmark и inset marker, не
только цвет.

## Accessibility contract

- native links/controls и `aria-current`;
- route heading и panel headings;
- visible chart summary, legend/direct labels и associated data table;
- tooltip не является единственным источником значений;
- selected/previous/category states имеют non-color cues;
- focus styles используют общие product tokens;
- `prefers-reduced-motion` отключает существующие motion effects;
- meaningful chart strokes, bars и controls проверяются в light/dark;
- dock overlap и horizontal overflow являются E2E failures.

Contract следует рекомендациям
[Carbon dashboards](https://carbondesignsystem.com/data-visualization/dashboards/),
[Carbon chart types](https://carbondesignsystem.com/data-visualization/chart-types/),
[Carbon axes](https://carbondesignsystem.com/data-visualization/axes-and-labels/)
и [W3C complex images](https://www.w3.org/WAI/tutorials/images/complex/).

## Screenshot matrix

Cloud standard E2E публикует:

- light/dark: overview, quality, load, progress, decks;
- states: overview sparse/comparison, quality low-confidence, load future-due,
  progress current-state, decks default/custom selection;
- 125%: overview, quality, load, decks.

Artifact review проверяет hierarchy, clipping, legends, tooltip viewport,
sparse states, default deck chart, terminology, console/page errors, request
failures и token absence. Screenshot count сам по себе не является proof.

## Performance

Baseline Stage 6: JS `824 880`, CSS `68 463` bytes. Production build после
visual redesign: JS `855 510` (+`30 630`), CSS `80 626` (+`12 163`) bytes.
Новых dependencies/lazy chunks нет. Shared chart primitives: line, bar,
stacked columns, stacked strips и ranked bars. Query count и payload/API не
изменены; каждый query по-прежнему обновляет один shared result.

## Future FSRS compatibility

Stage 7 должен переиспользовать Statistics panel, palette, legend, summary,
tooltip и table contracts. FSRS не должен создавать второй chart system,
смешивать units или использовать color-only meaning.

## Non-goals

FSRS, calibration, forgetting curves, stability/difficulty/retrievability,
новые метрики, cache redesign, custom query builder, Cards, Decks health,
Activity/Profile/global redesign, i18n и mobile-first work не входят в этот
контракт.
