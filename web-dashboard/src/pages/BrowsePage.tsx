import PlaceholderPage from "./PlaceholderPage";

function BrowsePage() {
  return (
    <PlaceholderPage
      title="Browse"
      description="Глобальный поиск по колодам, карточкам, тегам, словам, значениям и проблемам."
      features={[
        { title: "Global Search", text: "Единая строка поиска по локальным учебным данным.", status: "neutral" },
        { title: "Tags", text: "Навигация по тегам и связанным группам карточек.", status: "neutral" },
        { title: "Problems", text: "Поиск карточек и колод с конкретными проблемами.", status: "warning" },
        { title: "Read-Only", text: "Просмотр без изменения базы Anki.", status: "good" },
      ]}
    />
  );
}

export default BrowsePage;
