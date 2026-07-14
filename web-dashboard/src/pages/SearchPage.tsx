import { useTranslation } from "react-i18next";
import SearchInspector from "../components/search/SearchInspector";
import SearchActionBar from "../components/search/SearchActionBar";
import SearchQueryBar from "../components/search/SearchQueryBar";
import SearchResultsTable from "../components/search/SearchResultsTable";
import { useSearchDeckOptions } from "../hooks/useSearchDeckOptions";
import { useSearchWorkspace } from "../hooks/useSearchWorkspace";
import type { LoadState } from "./HomePage";
import type { StudyReport } from "../types/report";

export default function SearchPage({ report, loadState }: { report: StudyReport | null; loadState: LoadState }) {
  const { t } = useTranslation("pages", { keyPrefix: "search" });
  const workspace = useSearchWorkspace();
  const readyReport = loadState === "ready" ? report : null;
  const deckOptions = useSearchDeckOptions(readyReport);
  return <div className="search-page" data-testid="search-page">
    <header className="search-page-header"><div><span>{t("eyebrow")}</span><h1>{t("title")}</h1><p>{t("description")}</p></div><p className="search-privacy-note">{t("privacy")}</p></header>
    <SearchQueryBar workspace={workspace} report={readyReport} deckOptions={deckOptions} />
    {workspace.selectedIds.size ? <div className="search-batch-bar"><span>{t("selection.count", { count: workspace.selectedIds.size })}</span><button className="search-primary-button" type="button" disabled={workspace.browserPending} onClick={workspace.openInBrowser}>{workspace.browserPending ? t("browser.opening") : t("browser.open")}</button>{workspace.browserStatus ? <span role="status" className={workspace.browserStatus.ok ? "is-success" : "is-error"}>{workspace.browserStatus.ok ? t("browser.opened", { count: workspace.browserStatus.requestedCount ?? workspace.selectedIds.size }) : t("browser.failed")}</span> : null}</div> : null}
    <SearchActionBar workspace={workspace} deckOptions={deckOptions} />
    {workspace.queryStatus === "initial" ? <StatePanel title={t("states.initialTitle")} detail={t("states.initialDetail")} /> : null}
    {workspace.queryStatus === "loading" ? <StatePanel title={t("states.loadingTitle")} detail={t("states.loadingDetail")} live /> : null}
    {workspace.queryStatus === "error" ? <div className="search-state-panel search-error" role="alert"><strong>{errorTitle(workspace.queryError?.code, t)}</strong><p>{t("states.errorDetail")}</p><button className="secondary-button" type="button" onClick={workspace.retry}>{t("states.retry")}</button></div> : null}
    {workspace.queryStatus === "ready" && workspace.response?.items.length === 0 ? <StatePanel title={t("states.emptyTitle")} detail={t("states.emptyDetail")} /> : null}
    {workspace.response && workspace.queryStatus !== "initial" ? <div className={`search-workspace ${workspace.queryStatus === "loading" ? "is-loading" : ""}`}><SearchResultsTable workspace={workspace} /><SearchInspector workspace={workspace} /></div> : null}
  </div>;
}

function StatePanel({ title, detail, live = false }: { title: string; detail: string; live?: boolean }) { return <section className="search-state-panel" role={live ? "status" : undefined}><strong>{title}</strong><p>{detail}</p></section>; }

function errorTitle(code: string | undefined, t: (key: string) => string): string {
  const key = ({ invalid_search_request: "invalid", search_timeout: "timeout", search_unavailable: "unavailable", invalid_search_response: "malformed" } as Record<string, string>)[code ?? ""] ?? "failed";
  return t(`states.${key}`);
}
