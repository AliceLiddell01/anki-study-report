import PlaceholderPage from "./PlaceholderPage";

function StatsPage() {
  return (
    <PlaceholderPage
      title="Статистика"
      description="Здесь будет глубокая статистика по дням, неделям, retention, нагрузке и новым карточкам."
      available={["Короткие KPI и сравнение с нормой на Главной.", "Календарная история по дням.", "Таблица здоровья колод."]}
      actions={[
        { label: "На Главную", href: "#/home", primary: true },
        { label: "Открыть Календарь", href: "#/calendar" },
        { label: "Открыть Колоды", href: "#/decks" },
      ]}
      features={[
        { title: "Удержание", text: "Качество повторений по периодам и типам карточек.", status: "good" },
        { title: "Нагрузка", text: "Нагрузка, среднее время ответа и пики повторений.", status: "warning" },
        { title: "Новые карточки", text: "Баланс новых карточек и повторений без полного симулятора.", status: "neutral" },
        { title: "Тренды", text: "Сравнение дня, недели и месяца в одном месте.", status: "neutral" },
      ]}
    />
  );
}

export default StatsPage;
