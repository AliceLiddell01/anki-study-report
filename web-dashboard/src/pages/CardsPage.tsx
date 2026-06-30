import PlaceholderPage from "./PlaceholderPage";

function CardsPage() {
  return (
    <PlaceholderPage
      title="Cards"
      description="Поиск и анализ карточек: leech, failed, slow answer, missing audio, missing examples."
      features={[
        { title: "Risk Cards", text: "Карточки с повторными ошибками, leech-сигналами и долгими ответами.", status: "danger" },
        { title: "Content Gaps", text: "Поиск пропущенного аудио, примеров и слабых полей.", status: "warning" },
        { title: "Review Patterns", text: "История ответов по карточке и динамика сложности.", status: "neutral" },
        { title: "Safe Inspection", text: "Только просмотр и анализ, без редактирования карточек.", status: "good" },
      ]}
    />
  );
}

export default CardsPage;
