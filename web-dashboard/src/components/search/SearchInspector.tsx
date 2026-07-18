import { useTranslation } from "react-i18next";
import type { SearchWorkspaceState } from "../../hooks/useSearchWorkspace";
import { cardDisplayText } from "../../lib/cardDisplayText";
import type { SearchCardDetails, SearchNoteDetails } from "../../types/search";

export default function SearchInspector({ workspace }: { workspace: SearchWorkspaceState }) {
  const { t } = useTranslation("pages", { keyPrefix: "search" });
  return <aside className="search-inspector" aria-label={t("inspector.label")}>
    <h2>{t("inspector.title")}</h2>
    {!workspace.activeId ? <p className="search-inspector-empty">{t("inspector.initial")}</p> : null}
    {workspace.inspectStatus === "loading" ? <p role="status">{t("inspector.loading")}</p> : null}
    {workspace.inspectStatus === "error" ? <div className="search-error" role="alert"><strong>{workspace.inspectError?.code === "search_entity_not_found" ? t("inspector.stale") : t("inspector.failed")}</strong><button className="secondary-button" type="button" onClick={() => workspace.activeId && workspace.inspect(workspace.activeId)}>{t("states.retry")}</button></div> : null}
    {workspace.inspectStatus === "ready" && workspace.inspectResponse ? workspace.inspectResponse.mode === "cards"
      ? <CardInspector details={workspace.inspectResponse.details as SearchCardDetails} />
      : <NoteInspector details={workspace.inspectResponse.details as SearchNoteDetails} /> : null}
  </aside>;
}

function CardInspector({ details }: { details: SearchCardDetails }) {
  const { t } = useTranslation("pages", { keyPrefix: "search" });
  return <div className="search-inspector-content"><h3>{cardDisplayText(details)}</h3><dl>
    <Entry label={t("columns.deck")} value={details.deckName} /><Entry label={t("columns.noteType")} value={details.noteTypeName} /><Entry label={t("columns.template")} value={details.templateName} /><Entry label={t("columns.state")} value={t(`states.${details.state}`)} /><Entry label={t("columns.queue")} value={String(details.queue)} /><Entry label={t("columns.due")} value={String(details.due)} /><Entry label={t("columns.interval")} value={String(details.interval)} /><Entry label={t("columns.repetitions")} value={String(details.repetitions)} /><Entry label={t("columns.lapses")} value={String(details.lapses)} /><Entry label={t("columns.flag")} value={t(`flags.${details.flag}`)} /><Entry label={t("columns.tags")} value={details.tags.join(" · ") || "—"} />
  </dl><div className="search-technical"><span>cardId {details.cardId}</span><span>noteId {details.noteId}</span></div></div>;
}

function NoteInspector({ details }: { details: SearchNoteDetails }) {
  const { t } = useTranslation("pages", { keyPrefix: "search" });
  return <div className="search-inspector-content"><h3>{details.primaryText || t("results.blank")}</h3><dl><Entry label={t("columns.noteType")} value={details.noteTypeName} /><Entry label={t("columns.tags")} value={details.tags.join(" · ") || "—"} /><Entry label={t("columns.cardCount")} value={String(details.cardCount)} /><Entry label={t("columns.decks")} value={details.deckSummaries.map((deck) => deck.deckName).join(" · ") || "—"} /></dl><section className="search-note-fields"><h4>{t("inspector.fields")}</h4>{details.fields.map((field, index) => <div key={`${field.name}-${index}`}><strong>{field.name}</strong><p>{field.value || "—"}</p></div>)}</section><div className="search-technical"><span>noteId {details.noteId}</span><span>{t("inspector.cardReferences", { count: details.cardReferences.length })}</span>{details.cardReferences.slice(0, 20).map((reference) => <span key={reference.cardId}>cardId {reference.cardId}</span>)}</div></div>;
}

function Entry({ label, value }: { label: string; value: string }) { return <div><dt>{label}</dt><dd>{value || "—"}</dd></div>; }
