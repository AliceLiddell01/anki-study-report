import PlaceholderPage from "./PlaceholderPage";

function StatsPage() {
  return (
    <PlaceholderPage
      title="Stats"
      description="Глубокая аналитика по дням, неделям, месяцам, retention, нагрузке и новым карточкам."
      features={[
        { title: "Retention", text: "Качество повторений по периодам и типам карточек.", status: "good" },
        { title: "Workload", text: "Нагрузка, среднее время ответа и пики повторений.", status: "warning" },
        { title: "New Cards", text: "Баланс новых карточек и повторений без полного симулятора.", status: "neutral" },
        { title: "Trends", text: "Сравнение дня, недели и месяца в одном месте.", status: "neutral" },
      ]}
    />
  );
}

export default StatsPage;
