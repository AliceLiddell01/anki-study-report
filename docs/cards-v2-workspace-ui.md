# UI рабочего пространства Cards v2 — исторический контракт C1.5

## Статус

Этот документ сохранён только как историческое свидетельство отклонённого Design Gate C1.5 с нативной таблицей. Он не является актуальным implementation contract.

Текущий контракт представления `#/cards` описан в документах:

- [`cards-attention-inbox.md`](cards-attention-inbox.md) — C1.5R.5: semantic inbox с приоритетом идентичности, wide Inspector и non-modal drawer на 1024 px;
- [`card-preview-semantics.md`](card-preview-semantics.md) — лицевая сторона в Inspector и развёрнутый answer/back;
- [`triage-candidate-sources-v4.md`](triage-candidate-sources-v4.md) — независимые learning/current-content sources и ручное cursor continuation.

## Историческое решение

В C1.5 была выбрана компактная нативная таблица с persistent Inspector. Позднее owner review по screenshots и реальному профилю отозвал product acceptance.

C1.5R.5 полностью удаляет эту таблицу и не сохраняет её как responsive alias, скрытый режим, feature flag или fallback.

Исторические зелёные CI/E2E runs по-прежнему доказывают, что старая реализация выполнялась, но не подтверждают корректность текущего продукта.

## Текущая граница

C1.5R.5 остаётся read-only. В него не входят:

- selection и mutations;
- Safe Actions;
- manual resolution;
- recheck lifecycle;
- функциональность editor;
- ARIA grid или listbox;
- второй preview renderer.

Эти возможности находятся вне scope R5.