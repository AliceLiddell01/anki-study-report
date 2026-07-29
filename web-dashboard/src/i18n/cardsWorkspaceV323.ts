export const cardsWorkspaceV323 = {
  en: {
    eyebrow: "Attention queue",
    title: "Cards",
    description: "Review the reason, open the exact card in Anki, and recheck the outcome.",
    refreshing: "Refreshing the queue…",
    dismissNotice: "Dismiss notification",
    filters: {
      searchPlaceholder: "Find a card or deck",
      open: "Filters",
      clearShort: "Reset",
    },
    queue: { resolved: "Resolved" },
    inspector: {
      reasons: "Why",
      next: "What to do",
      result: "Result",
      execution: "Execution / after action",
      recommendUnsuspend: "Return this suspended card to active study, then recheck the current reasons.",
      recommendUnbury: "Return this buried card to the active queue, then recheck the current reasons.",
      resolutionRail: "Reasons, recommendation, and execution",
    },
    resolution: {
      noActiveReasons: "No active reasons were detected. The card remains temporarily as confirmation of the result.",
      resolvedNext: "Move to the next card. This row is no longer included in the active queue count.",
      nextCard: "Next card",
      states: {
        resolved: {
          title: "Problem resolved",
          description: "The authoritative recheck found no active reasons. Confirmation remains until you move to the next card.",
        },
      },
    },
    drawer: { closeShort: "Close" },
    coverage: { action: "Coverage and details" },
  },
  ru: {
    eyebrow: "Очередь внимания",
    title: "Карточки",
    description: "Разберите причину, откройте точную карточку в Anki и перепроверьте результат.",
    refreshing: "Обновляем очередь…",
    dismissNotice: "Закрыть уведомление",
    filters: {
      searchPlaceholder: "Найти карточку или колоду",
      open: "Фильтры",
      clearShort: "Сбросить",
    },
    queue: { resolved: "Устранено" },
    inspector: {
      reasons: "Почему",
      next: "Что сделать",
      result: "Результат",
      execution: "Выполнение / после действия",
      recommendUnsuspend: "Верните приостановленную карточку в обучение, затем перепроверьте текущие причины.",
      recommendUnbury: "Верните отложенную карточку в активную очередь, затем перепроверьте текущие причины.",
      resolutionRail: "Причины, рекомендация и выполнение",
    },
    resolution: {
      noActiveReasons: "Активные причины не обнаружены. Карточка временно остаётся в очереди как подтверждение результата.",
      resolvedNext: "Перейдите к следующей карточке. Эта строка больше не входит в счётчик активной очереди.",
      nextCard: "К следующей карточке",
      states: {
        resolved: {
          title: "Проблема устранена",
          description: "Авторитетная перепроверка не нашла активных причин. Подтверждение остаётся до перехода к следующей карточке.",
        },
      },
    },
    drawer: { closeShort: "Закрыть" },
    coverage: { action: "Покрытие и детали" },
  },
} as const;
