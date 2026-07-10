import { Settings, UserRound } from "lucide-react";
import type { StudyReport } from "../types/report";

function ProfilePage({ report }: { report: StudyReport | null; onReportUpdated?: (report: StudyReport) => void }) {
  const selectedDecks = report?.metadata.selectedDecks.filter((deck) => deck.trim().length > 0) ?? [];
  const filteredDecks = selectedDecks.filter((deck) => deck.toLowerCase() !== "все колоды");
  const scope = filteredDecks.length === 0
    ? "Все колоды"
    : filteredDecks.length <= 3
      ? filteredDecks.join(", ")
      : `${filteredDecks.length} колод`;

  return (
    <div className="grid gap-5">
      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel sm:p-6">
        <div className="flex items-start gap-4">
          <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-report-blue/35 bg-report-blue/10 text-report-blue">
            <UserRound size={24} aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <span className="status-pill status-neutral">локальный профиль</span>
            <h1 className="mt-4 text-2xl font-semibold tracking-normal text-report-text sm:text-3xl">Профиль</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-report-muted">
              Это переходный read-only экран. Личные аккаунты, аватары, достижения и activity feed пока не реализованы.
            </p>
          </div>
        </div>
      </section>

      <section className="rounded-xl border border-ink-700 bg-ink-850 p-5 shadow-panel">
        <h2 className="text-lg font-semibold tracking-normal text-report-text">Текущая область dashboard</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <Detail label="Колоды" value={scope} />
          <Detail label="Дочерние колоды" value={report?.metadata.includeChildren ? "включены" : "не включены"} />
        </div>
        <p className="mt-4 text-sm leading-6 text-report-muted">
          Страница «Сегодня» всегда показывает текущий локальный день. Область колод и defaults отчёта настраиваются в Settings Hub.
        </p>
        <a className="mt-4 inline-flex items-center gap-2 rounded-lg border border-report-blue/45 bg-report-blue/15 px-4 py-2 text-sm font-semibold text-report-text transition hover:border-report-blue focus:outline-none focus:ring-2 focus:ring-report-blue/55" href="#/settings">
          <Settings size={16} aria-hidden="true" /> Открыть настройки
        </a>
      </section>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-ink-700 bg-ink-900/45 px-3 py-3">
      <p className="text-xs uppercase tracking-[0.04em] text-report-muted">{label}</p>
      <p className="mt-1 break-words text-sm font-semibold text-report-text">{value}</p>
    </div>
  );
}

export default ProfilePage;
