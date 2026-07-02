import PlaceholderPage from "./PlaceholderPage";

function FsrsPage() {
  return (
    <PlaceholderPage
      title="FSRS Lab"
      description="Здесь будет отдельная зона FSRS: predicted recall, desired retention, workload forecast, hard misuse risk и безопасные what-if сценарии."
      available={["FSRS-сводка уже есть на Главной, если данные доступны.", "Прогноз нагрузки показывается без изменения расписания.", "Hard/Again остаются терминами Anki."]}
      actions={[
        { label: "На Главную", href: "#/home", primary: true },
        { label: "Открыть Статистику", href: "#/stats" },
        { label: "Перейти в Действия", href: "#/actions" },
      ]}
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
