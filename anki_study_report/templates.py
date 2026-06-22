"""Russian report text templates for Anki Study Report."""

from __future__ import annotations


PASS_RATE_GOOD = 0.90
PASS_RATE_OK = 0.80
DUE_TOMORROW_LOAD_RATIO = 1.25
PROBLEM_DECK_PASS_RATE = 0.80
PROBLEM_DECK_MIN_REVIEWS = 5
BEST_DECK_PASS_RATE = 0.90
BEST_DECK_MIN_REVIEWS = 5


QUALITY_GOOD = "Хороший день: большинство ответов прошли без повторного провала."
QUALITY_OK = "Нормальный день, но ошибки были заметны."
QUALITY_HEAVY = "Тяжёлый день: лучше не брать много новых карточек, пока материал не стабилизируется."
QUALITY_EMPTY = "За выбранный период повторений не найдено."


DUE_TOMORROW_LIGHT = "На завтра заметной дополнительной нагрузки не видно."
DUE_TOMORROW_NONE = "На завтра в выбранной области ничего не запланировано."
DUE_TOMORROW_HIGH = (
    "На завтра ожидается высокая нагрузка относительно сегодняшних повторений."
)


SHORT_TEMPLATE = (
    "{summary}\n"
    "{quality}\n"
    "{time_summary}\n"
    "{tomorrow}"
)


DETAILED_TEMPLATE = (
    "Короткий вывод\n"
    "{short_conclusion}\n\n"
    "Итоги\n"
    "{summary}\n"
    "{time_summary}\n\n"
    "Качество\n"
    "{quality}\n\n"
    "Проблемные колоды\n"
    "{problem_decks}\n\n"
    "Завтра\n"
    "{tomorrow}\n\n"
    "Следующее действие\n"
    "{next_actions}"
)


MARKDOWN_TEMPLATE = (
    "# Anki Study Report\n\n"
    "## Итоги\n"
    "- Повторений: {total_reviews}\n"
    "- Новых карточек: {new_cards}\n"
    "- Again: {again_count}\n"
    "- Время: {estimated_minutes} мин\n\n"
    "## Качество\n"
    "- Процент успешных ответов: {pass_rate_percent}%\n"
    "- Вывод: {quality}\n\n"
    "## Проблемные колоды\n"
    "{problem_decks_markdown}\n\n"
    "## Завтра\n"
    "- К повторению: {due_tomorrow}\n"
    "- Вывод: {tomorrow}\n"
)
