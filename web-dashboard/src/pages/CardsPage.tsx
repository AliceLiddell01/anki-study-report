import PlaceholderPage from "./PlaceholderPage";

function CardsPage() {
  return (
    <PlaceholderPage
      title="Карточки"
      description="Здесь будет карточный уровень анализа: leech, повторные ошибки, долгие ответы, пропущенное аудио и слабые поля."
      available={["Сводка по проблемным колодам на Главной.", "Открытие проблемных карточек через Anki Browser.", "Безопасный режим только чтения."]}
      actions={[
        { label: "На Главную", href: "#/home", primary: true },
        { label: "Открыть проблемные колоды", href: "#/decks" },
        { label: "Перейти в Действия", href: "#/actions" },
      ]}
      features={[
        { title: "Рискованные карточки", text: "Карточки с повторными ошибками, leech-сигналами и долгими ответами.", status: "danger" },
        { title: "Пробелы в данных", text: "Поиск пропущенного аудио, примеров и слабых полей.", status: "warning" },
        { title: "Паттерны ответов", text: "История ответов по карточке и динамика сложности.", status: "neutral" },
        { title: "Безопасный просмотр", text: "Только просмотр и анализ, без редактирования карточек.", status: "good" },
      ]}
    />
  );
}

export default CardsPage;
