import PlaceholderPage from "./PlaceholderPage";

function BrowsePage() {
  return (
    <PlaceholderPage
      title="Поиск"
      description="Здесь будет глобальный поиск по колодам, карточкам, тегам, словам, значениям и проблемам."
      available={["Фильтр по колодам уже доступен на странице Колоды.", "Anki Browser можно открыть из Действий.", "Поиск останется локальным и в режиме только чтения."]}
      actions={[
        { label: "Перейти в Действия", href: "#/actions", primary: true },
        { label: "Открыть Колоды", href: "#/decks" },
        { label: "На Главную", href: "#/home" },
      ]}
      features={[
        { title: "Глобальный поиск", text: "Единая строка поиска по локальным учебным данным.", status: "neutral" },
        { title: "Теги", text: "Навигация по тегам и связанным группам карточек.", status: "neutral" },
        { title: "Проблемы", text: "Поиск карточек и колод с конкретными проблемами.", status: "warning" },
        { title: "Только чтение", text: "Просмотр без изменения базы Anki.", status: "good" },
      ]}
    />
  );
}

export default BrowsePage;
