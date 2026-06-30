type PlaceholderFeature = {
  title: string;
  text: string;
  status?: "good" | "neutral" | "warning" | "danger";
};

function PlaceholderPage({
  title,
  description,
  features,
}: {
  title: string;
  description: string;
  features: PlaceholderFeature[];
}) {
  return (
    <div className="grid gap-5">
      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel sm:p-6">
        <div className="max-w-3xl">
          <span className="status-pill status-neutral">planned page</span>
          <h1 className="mt-4 text-2xl font-semibold tracking-normal text-report-text sm:text-3xl">{title}</h1>
          <p className="mt-3 text-sm leading-6 text-report-muted sm:text-base">{description}</p>
        </div>
      </section>
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {features.map((feature) => (
          <article key={feature.title} className="deck-card">
            <span className={`status-pill status-${feature.status ?? "neutral"}`}>{feature.status ?? "info"}</span>
            <h2 className="mt-4 text-base font-semibold tracking-normal text-report-text">{feature.title}</h2>
            <p className="mt-2 text-sm leading-6 text-report-muted">{feature.text}</p>
          </article>
        ))}
      </section>
    </div>
  );
}

export default PlaceholderPage;
