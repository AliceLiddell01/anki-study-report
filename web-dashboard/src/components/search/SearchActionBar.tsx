import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { SearchWorkspaceState } from "../../hooks/useSearchWorkspace";
import type { EntityActionResultCode } from "../../types/entityActions";

export default function SearchActionBar({ workspace }: { workspace: SearchWorkspaceState }) {
  const { t } = useTranslation("pages", { keyPrefix: "search.actions" });
  const [flag, setFlag] = useState(1);
  const [tagText, setTagText] = useState("");
  const tags = tagText.trim() ? [tagText.trim()] : [];
  const hasSelection = workspace.selectedIds.size > 0;
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
  if (code === "entity_action_stale") return "errors.stale";
  if (code === "invalid_entity_action") return "errors.invalid";
  if (code === "entity_action_timeout") return "errors.timeout";
  if (code === "invalid_entity_action_response") return "errors.malformed";
  if (code === "entity_action_unavailable") return "errors.unavailable";
  return "errors.failed";
}
