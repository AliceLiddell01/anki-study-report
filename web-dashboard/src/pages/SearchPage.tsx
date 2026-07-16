import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import SearchInspector from "../components/search/SearchInspector";
import SearchActionBar from "../components/search/SearchActionBar";
import SearchQueryBar from "../components/search/SearchQueryBar";
import SearchResultsTable from "../components/search/SearchResultsTable";
import { useSearchMetadata } from "../hooks/useSearchMetadata";
import { useSearchWorkspace } from "../hooks/useSearchWorkspace";
import type { StudyReport } from "../types/report";
import type { DeckOption } from "../types/settings";
import type { LoadState } from "./HomePage";
import { consumeNotificationHandoff } from "../lib/notificationHandoff";

export default function SearchPage({ report, loadState }: { report: StudyReport | null; loadState: LoadState }) {
  const { t } = useTranslation("pages", { keyPrefix: "search" });
  const workspace = useSearchWorkspace();
  const metadata = useSearchMetadata();
  const [notificationHandoff] = useState(() => consumeNotificationHandoff("card_problems"));
  const readyReport = loadState === "ready" ? report : null;
  const fallbackDeckOptions = useMemo(() => deckOptionsFromReport(readyReport), [readyReport]);
  return <div className="search-page" data-testid="search-page">
    <header className="search-page-header"><div><span>{t("eyebrow")}</span><h1>{t("title")}</h1><p>{t("description")}</p></div><p className="search-privacy-note">{t("privacy")}</p></header>
    {notificationHandoff ? <p role="status" className="rounded-lg border border-report-blue/45 bg-report-blue/10 px-4 py-3 text-sm text-report-secondary">{t("notificationHandoff")}</p> : null}
    <SearchQueryBar workspace={workspace} report={readyReport} metadata={metadata} fallbackDeckOptions={fallbackDeckOptions} />
    {workspace.selectedIds.size ? <div className="search-batch-bar"><span>{t("selection.count", { count: workspace.selectedIds.size })}</span><button className="search-primary-button" type="button" disabled={workspace.browserPending} onClick={workspace.openInBrowser}>{workspace.browserPending ? t("browser.opening") : t("browser.open")}</button>{workspace.browserStatus ? <span role="status" className={workspace.browserStatus.ok ? "is-success" : "is-error"}>{workspace.browserStatus.ok ? t("browser.opened", { count: workspace.browserStatus.requestedCount ?? workspace.selectedIds.size }) : t("browser.failed")}</span> : null}</div> : null}
    <SearchActionBar workspace={workspace} metadata={metadata} fallbackDeckOptions={fallbackDeckOptions} />
    {workspace.queryStatus === "initial" ? <StatePanel title={t("states.initialTitle")} detail={t("states.initialDetail")} /> : null}
    {workspace.queryStatus === "loading" ? <StatePanel title={t("states.loadingTitle")} detail={t("states.loadingDetail")} live /> : null}
    {workspace.queryStatus === "error" ? <div className="search-state-panel search-error" role="alert"><strong>{errorTitle(workspace.queryError?.code, t)}</strong><p>{t("states.errorDetail")}</p><button className="secondary-button" type="button" onClick={workspace.retry}>{t("states.retry")}</button></div> : null}
    {workspace.queryStatus === "ready" && workspace.response?.items.length === 0 ? <StatePanel title={t("states.emptyTitle")} detail={t("states.emptyDetail")} /> : null}
    {workspace.response && workspace.queryStatus !== "initial" ? <div className={`search-workspace ${workspace.queryStatus === "loading" ? "is-loading" : ""}`}><SearchResultsTable workspace={workspace} /><SearchInspector workspace={workspace} /></div> : null}
  </div>;
}

function deckOptionsFromReport(report: StudyReport | null): DeckOption[] {
  const options = new Map<number, string>();
  if (report?.deckHub) {
    Object.values(report.deckHub.nodes).forEach((node) => options.set(Number(node.deckId), node.fullName));
  }
  (report?.decks ?? []).forEach((deck) => options.set(Number(deck.id), deck.name));
  return [...options.entries()]
    .filter(([id, name]) => Number.isInteger(id) && id > 0 && name.trim().length > 0)
    .map(([id, name]) => ({ id, name }))
    .sort((left, right) => left.name.localeCompare(right.name));
}

function StatePanel({ title, detail, live = false }: { title: string; detail: string; live?: boolean }) { return <section className="search-state-panel" role={live ? "status" : undefined}><strong>{title}</strong><p>{detail}</p></section>; }

function errorTitle(code: string | undefined, t: (key: string) => string): string {
  const key = ({ invalid_search_request: "invalid", search_timeout: "timeout", search_unavailable: "unavailable", invalid_search_response: "malformed" } as Record<string, string>)[code ?? ""] ?? "failed";
  return t(`states.${key}`);
}
