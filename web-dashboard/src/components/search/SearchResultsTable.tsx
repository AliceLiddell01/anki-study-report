import { useTranslation } from "react-i18next";
import type { SearchWorkspaceState } from "../../hooks/useSearchWorkspace";
import { cardDisplayText } from "../../lib/cardDisplayText";
import type { SearchCardRow, SearchNoteRow } from "../../types/search";

export default function SearchResultsTable({ workspace }: { workspace: SearchWorkspaceState }) {
  const { t } = useTranslation("pages", { keyPrefix: "search" });
  const response = workspace.response;
  if (!response) return null;
  const rows = response.mode === "cards" ? response.items as SearchCardRow[] : response.items as SearchNoteRow[];
  const pageIds = rows.map((row) => response.mode === "cards" ? (row as SearchCardRow).cardId : (row as SearchNoteRow).noteId);
  const pageSelected = pageIds.length > 0 && pageIds.every((id) => workspace.selectedIds.has(id));

  return (
    <section className="search-results-panel" aria-label={t("results.label")}>
      <div className="search-results-summary">
        <span>{t("results.count", { count: response.boundedTotal })}</span>
        <span>{t("selection.count", { count: workspace.selectedIds.size })}</span>
      </div>
      {response.truncated ? <p className="search-notice" role="status">{t("states.truncated", { count: response.boundedTotal })}</p> : null}
      {workspace.selectionCapHit ? <p className="search-notice is-warning" role="status">{t("selection.limit", { count: 200 })}</p> : null}
      <div className="search-table-wrap">
        <table className="search-table">
          <thead><tr>
            <th className="search-checkbox-cell"><input type="checkbox" aria-label={t("selection.selectPage")} checked={pageSelected} onChange={(event) => workspace.togglePageSelection(event.target.checked)} /></th>
            <th>{t("columns.primary")}</th>
            {response.mode === "cards" ? <CardHeaders /> : <NoteHeaders />}
          </tr></thead>
          <tbody>{rows.map((row) => response.mode === "cards"
            ? <CardRow key={(row as SearchCardRow).cardId} row={row as SearchCardRow} workspace={workspace} />
            : <NoteRow key={(row as SearchNoteRow).noteId} row={row as SearchNoteRow} workspace={workspace} />)}</tbody>
        </table>
      </div>
      <div className="search-pagination" aria-label={t("pagination.label")}>
        <button type="button" className="secondary-button" disabled={response.page <= 1 || workspace.queryStatus === "loading"} onClick={() => workspace.goToPage(response.page - 1)}>{t("pagination.previous")}</button>
        <span>{response.pageCount ? t("pagination.page", { page: response.page, count: response.pageCount }) : t("pagination.empty")}</span>
        <label>{t("pagination.pageSize")}<select value={workspace.pageSize} onChange={(event) => workspace.setPageSize(Number(event.target.value) as 25 | 50 | 100)}>{[25, 50, 100].map((size) => <option key={size}>{size}</option>)}</select></label>
        <button type="button" className="secondary-button" disabled={!response.hasNext || workspace.queryStatus === "loading"} onClick={() => workspace.goToPage(response.page + 1)}>{t("pagination.next")}</button>
      </div>
    </section>
  );
}

function CardHeaders() { const { t } = useTranslation("pages", { keyPrefix: "search.columns" }); return <><th>{t("deck")}</th><th>{t("noteType")}</th><th>{t("template")}</th><th>{t("state")}</th><th>{t("due")}</th><th>{t("interval")}</th><th>{t("repetitions")}</th><th>{t("lapses")}</th><th>{t("flag")}</th></>; }
function NoteHeaders() { const { t } = useTranslation("pages", { keyPrefix: "search.columns" }); return <><th>{t("noteType")}</th><th>{t("tags")}</th><th>{t("cardCount")}</th><th>{t("decks")}</th></>; }

function CardRow({ row, workspace }: { row: SearchCardRow; workspace: SearchWorkspaceState }) {
  const { t } = useTranslation("pages", { keyPrefix: "search" });
  const active = workspace.activeId === row.cardId;
  const identity = cardDisplayText(row);
  return <tr className={`${active ? "is-active " : ""}${workspace.selectedIds.has(row.cardId) ? "is-selected" : ""}`} onClick={(event) => { if (!(event.target as HTMLElement).closest("input,button")) void workspace.inspect(row.cardId); }}>
    <td className="search-checkbox-cell"><input type="checkbox" aria-label={t("selection.selectCard", { id: row.cardId })} checked={workspace.selectedIds.has(row.cardId)} onChange={(event) => workspace.toggleSelection(row.cardId, event.target.checked)} /></td>
    <th scope="row"><button type="button" className="search-row-button" aria-pressed={active} onClick={() => workspace.inspect(row.cardId)} title={identity}>{identity}</button></th>
    <td title={row.deckName}>{row.deckName}</td><td>{row.noteTypeName}</td><td>{row.templateName}</td><td>{t(`states.${row.state}`)}</td><td>{row.due}</td><td>{row.interval}</td><td>{row.repetitions}</td><td>{row.lapses}</td><td>{t(`flags.${row.flag}`)}</td>
  </tr>;
}

function NoteRow({ row, workspace }: { row: SearchNoteRow; workspace: SearchWorkspaceState }) {
  const { t } = useTranslation("pages", { keyPrefix: "search" });
  const active = workspace.activeId === row.noteId;
  return <tr className={`${active ? "is-active " : ""}${workspace.selectedIds.has(row.noteId) ? "is-selected" : ""}`} onClick={(event) => { if (!(event.target as HTMLElement).closest("input,button")) void workspace.inspect(row.noteId); }}>
    <td className="search-checkbox-cell"><input type="checkbox" aria-label={t("selection.selectNote", { id: row.noteId })} checked={workspace.selectedIds.has(row.noteId)} onChange={(event) => workspace.toggleSelection(row.noteId, event.target.checked)} /></td>
    <th scope="row"><button type="button" className="search-row-button" aria-pressed={active} onClick={() => workspace.inspect(row.noteId)} title={row.primaryText}>{row.primaryText || t("results.blank")}</button></th>
    <td>{row.noteTypeName}</td><td>{row.tagSummary.join(" · ") || "—"}</td><td>{row.cardCount}</td><td>{row.deckSummary.map((deck) => deck.deckName).join(" · ") || "—"}</td>
  </tr>;
}
