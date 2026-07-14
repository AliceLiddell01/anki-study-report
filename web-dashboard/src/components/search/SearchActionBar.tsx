import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { SearchWorkspaceState } from "../../hooks/useSearchWorkspace";
import type { EntityActionResultCode } from "../../types/entityActions";
import type { SearchCardRow } from "../../types/search";
import type { DeckOption } from "../../types/settings";

export default function SearchActionBar({ workspace, deckOptions }: { workspace: SearchWorkspaceState; deckOptions: DeckOption[] }) {
  const { t } = useTranslation("pages", { keyPrefix: "search.actions" });
  const [flag, setFlag] = useState(1);
  const [tagText, setTagText] = useState("");
  const [deckId, setDeckId] = useState("");
  const tags = tagText.trim() ? [tagText.trim()] : [];
  const hasSelection = workspace.selectedIds.size > 0;
  const cardRows = workspace.response?.mode === "cards" ? workspace.response.items as SearchCardRow[] : [];
  const selectedRows = cardRows.filter((row) => workspace.selectedIds.has(row.cardId));
  const allSelectedVisible = selectedRows.length === workspace.selectedIds.size;
  const currentDecks = [...new Set(selectedRows.map((row) => row.deckName))];
  const currentDeckLabel = !allSelectedVisible
    ? t("multipleDecks")
    : currentDecks.length === 1
      ? currentDecks[0]
      : currentDecks.length > 1
        ? t("multipleDecks")
        : t("deckUnknown");
  const sameDestination = Boolean(deckId) && allSelectedVisible && selectedRows.every((row) => row.deckId === deckId);
  if (!hasSelection && !workspace.actionResponse && !workspace.actionError) return null;

  return <section className="search-action-surface" aria-label={t("label")}>
    {hasSelection ? <div className="search-action-bar">
      <strong>{t("selected", { count: workspace.selectedIds.size })}</strong>
      {workspace.mode === "cards" ? <>
        <button type="button" disabled={workspace.actionPending} onClick={() => workspace.runEntityAction("suspend")}>{t("suspend")}</button>
        <button type="button" disabled={workspace.actionPending} onClick={() => workspace.runEntityAction("unsuspend")}>{t("unsuspend")}</button>
        <label><span>{t("flag")}</span><select value={flag} disabled={workspace.actionPending} onChange={(event) => setFlag(Number(event.target.value))}>{[1, 2, 3, 4, 5, 6, 7].map((value) => <option key={value} value={value}>{t(`flagNames.${value}`)}</option>)}</select></label>
        <button type="button" disabled={workspace.actionPending} onClick={() => workspace.runEntityAction("set_flag", { flag })}>{t("setFlag")}</button>
        <button type="button" disabled={workspace.actionPending} onClick={() => workspace.runEntityAction("clear_flag")}>{t("clearFlag")}</button>
        <button type="button" disabled={workspace.actionPending} onClick={() => workspace.runEntityAction("bury")}>{t("bury")}</button>
        <button type="button" disabled={workspace.actionPending} onClick={() => workspace.runEntityAction("unbury")}>{t("unbury")}</button>
        <span className="search-action-help">{t("buryHelp")}</span>
        <label><span>{t("currentDeck")}</span><span className="search-current-deck">{currentDeckLabel}</span></label>
        <label><span>{t("destination")}</span><select value={deckId} disabled={workspace.actionPending || deckOptions.length === 0} onChange={(event) => setDeckId(event.target.value)}><option value="">{t("chooseDeck")}</option>{deckOptions.map((deck) => <option key={deck.id} value={String(deck.id)}>{deck.name}</option>)}</select></label>
        <button type="button" disabled={workspace.actionPending || !deckId || sameDestination} onClick={() => workspace.runEntityAction("move_to_deck", { deckId })}>{t("move")}</button>
        {sameDestination ? <span className="search-action-help">{t("sameDeck")}</span> : null}
      </> : <>
        <label className="search-tag-action"><span>{t("tags")}</span><input value={tagText} disabled={workspace.actionPending} maxLength={1000} onChange={(event) => setTagText(event.target.value)} placeholder={t("tagsPlaceholder")} /></label>
        <button type="button" disabled={workspace.actionPending || tags.length === 0} onClick={() => workspace.runEntityAction("add_tags", { tags })}>{t("addTags")}</button>
        <button type="button" disabled={workspace.actionPending || tags.length === 0} onClick={() => workspace.runEntityAction("remove_tags", { tags })}>{t("removeTags")}</button>
        <span className="search-action-help">{t("tagsHelp")}</span>
      </>}
      {workspace.actionPending ? <span role="status">{t("running")}</span> : null}
    </div> : null}
    {workspace.actionResponse ? <p className="search-action-feedback is-success" role="status">
      {t(resultKey(workspace.actionResponse.resultCode), {
        count: workspace.actionResponse.affectedCount,
        unchanged: workspace.actionResponse.unchangedCount,
        flag: workspace.actionResponse.args.flag,
      })} {workspace.actionResponse.undoable ? t("undoable") : ""}
    </p> : null}
    {workspace.actionError ? <p className="search-action-feedback is-error" role="alert">{t(errorKey(workspace.actionError.code))}</p> : null}
  </section>;
}

function resultKey(code: EntityActionResultCode): string {
  return `results.${code.replace(/\./g, "_")}`;
}

function errorKey(code: string): string {
  if (code === "cards.filtered_source_unsupported") return "errors.filteredSource";
  if (code === "cards.destination_filtered") return "errors.filteredDestination";
  if (code === "cards.destination_not_found") return "errors.destinationMissing";
  if (code === "entity_action_stale") return "errors.stale";
  if (code === "invalid_entity_action") return "errors.invalid";
  if (code === "entity_action_timeout") return "errors.timeout";
  if (code === "invalid_entity_action_response") return "errors.malformed";
  if (code === "entity_action_unavailable") return "errors.unavailable";
  return "errors.failed";
}
