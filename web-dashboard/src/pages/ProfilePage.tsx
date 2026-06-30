import PlaceholderPage from "./PlaceholderPage";

function ProfilePage() {
  return (
    <PlaceholderPage
      title="Study Profile"
      description="Общий профиль обучения: streak, active days, total reviews, mature cards, current focus."
      features={[
        { title: "Learning Identity", text: "Сводка привычек, темпа и текущего учебного фокуса.", status: "good" },
        { title: "Streaks", text: "Активные дни, пропуски и восстановление ритма.", status: "neutral" },
        { title: "Long-Term Progress", text: "Рост зрелых карточек и накопленная история повторений.", status: "neutral" },
        { title: "Focus Areas", text: "Темы и колоды, которые сейчас важнее всего.", status: "warning" },
      ]}
    />
  );
}

export default ProfilePage;
