type PlaceholderFeature = {
  title: string;
  text: string;
  status?: "good" | "neutral" | "warning" | "danger";
};

function PlaceholderPage({
  title,
  description,
  available,
  actions,
  features,
}: {
  title: string;
  description: string;
  available: string[];
  actions: Array<{ label: string; href: string; primary?: boolean }>;
  features: PlaceholderFeature[];
}) {
  return (
    <div className="grid gap-5">
      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel sm:p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <span className="status-pill status-neutral">в разработке</span>
            <h1 className="mt-4 text-2xl font-semibold tracking-normal text-report-text sm:text-3xl">{title}</h1>
            <p className="mt-3 text-sm leading-6 text-report-muted sm:text-base">{description}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {actions.map((action) => (
                <a
                  key={action.href}
                  href={action.href}
                  className={[
                    "inline-flex min-h-10 items-center justify-center rounded-lg border px-3 py-2 text-sm font-medium transition",
                    action.primary
                      ? "border-report-blue/55 bg-report-blue/15 text-report-text hover:border-report-blue"
                      : "border-ink-700 bg-ink-900/45 text-report-secondary hover:border-report-blue/55 hover:text-report-text",
                  ].join(" ")}
                >
                  {action.label}
                </a>
              ))}
            </div>
          </div>
          <div className="nested-surface min-w-[260px] rounded-lg border border-ink-700 p-4 lg:max-w-sm">
            <h2 className="text-base font-semibold text-report-text">Уже доступно</h2>
            <ul className="mt-3 grid gap-2 text-sm leading-6 text-report-muted">
              {available.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        </div>
      </section>
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {features.map((feature) => (
          <article key={feature.title} className="deck-card flex min-h-[174px] flex-col">
            <span className={`status-pill status-${feature.status ?? "neutral"}`}>{statusText(feature.status ?? "neutral")}</span>
            <h2 className="mt-4 text-base font-semibold tracking-normal text-report-text">{feature.title}</h2>
            <p className="mt-2 text-sm leading-6 text-report-muted">{feature.text}</p>
          </article>
        ))}
      </section>
    </div>
  );
}

function statusText(status: "good" | "neutral" | "warning" | "danger") {
  return {
    good: "хорошо",
    neutral: "инфо",
    warning: "внимание",
    danger: "опасно",
  }[status];
}

export default PlaceholderPage;
