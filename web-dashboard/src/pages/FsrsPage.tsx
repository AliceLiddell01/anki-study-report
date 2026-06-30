import PlaceholderPage from "./PlaceholderPage";

function FsrsPage() {
  return (
    <PlaceholderPage
      title="FSRS Lab"
      description="Predicted recall, desired retention, workload forecast, hard misuse risk, what-if simulator."
      features={[
        { title: "Predicted Recall", text: "Прогноз удержания и зоны риска по FSRS-данным.", status: "good" },
        { title: "Workload Forecast", text: "Нагрузка ближайших дней без имитации полного Anki Simulator.", status: "warning" },
        { title: "Hard Misuse", text: "Сигналы неправильного использования Hard и Again.", status: "danger" },
        { title: "What-If", text: "Будущий отдельный режим для безопасных сценариев.", status: "neutral" },
      ]}
    />
  );
}

export default FsrsPage;
