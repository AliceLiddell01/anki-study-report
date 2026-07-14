import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import type { SearchFiltersState, SearchWorkspaceState } from "../../hooks/useSearchWorkspace";
import type { StudyReport } from "../../types/report";
import type { DeckOption } from "../../types/settings";

export default function SearchQueryBar({ workspace, report, deckOptions }: { workspace: SearchWorkspaceState; report: StudyReport | null; deckOptions: DeckOption[] }) {
  const { t } = useTranslation("pages", { keyPrefix: "search" });
  const noteTypes = (report?.noteTypeCatalog ?? []).map((item) => ({ id: String(item.noteTypeId), name: item.name }));
  const updateFilter = <K extends keyof SearchFiltersState>(key: K, value: SearchFiltersState[K]) => {
    workspace.setFilters((current) => ({ ...current, [key]: value }));
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    workspace.submit();
  };

  return (
    <form className="search-command" onSubmit={submit} aria-label={t("query.formLabel")}>
      <div className="search-command-main">
        <label className="search-query-field">
          <span>{t("query.label")}</span>
          <input
            value={workspace.query}
            onChange={(event) => workspace.setQuery(event.target.value)}
            maxLength={4096}
            placeholder={t("query.placeholder")}
            autoComplete="off"
          />
        </label>
        <button className="search-primary-button" type="submit" disabled={workspace.queryStatus === "loading"}>
          {workspace.queryStatus === "loading" ? t("query.searching") : t("query.submit")}
        </button>
        <button className="secondary-button" type="button" onClick={workspace.clear}>{t("query.clear")}</button>
      </div>

      <div className="search-controls-row">
        <fieldset className="search-segmented">
          <legend>{t("mode.label")}</legend>
          {(["cards", "notes"] as const).map((mode) => (
            <label key={mode}>
              <input type="radio" name="search-mode" value={mode} checked={workspace.mode === mode} onChange={() => workspace.setMode(mode)} />
              <span>{t(`mode.${mode}`)}</span>
            </label>
          ))}
        </fieldset>
        <label><span>{t("filters.deck")}</span><select value={workspace.filters.deckId} onChange={(event) => updateFilter("deckId", event.target.value)}><option value="">{t("filters.allDecks")}</option>{deckOptions.map((item) => <option key={item.id} value={String(item.id)}>{item.name}</option>)}</select></label>
        <label><span>{t("filters.noteType")}</span><select value={workspace.filters.noteTypeId} onChange={(event) => updateFilter("noteTypeId", event.target.value)}><option value="">{t("filters.allNoteTypes")}</option>{noteTypes.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <label><span>{t("filters.tag")}</span><input value={workspace.filters.tag} maxLength={100} onChange={(event) => updateFilter("tag", event.target.value)} placeholder={t("filters.tagPlaceholder")} /></label>
        {workspace.mode === "cards" ? <>
          <label><span>{t("filters.state")}</span><select value={workspace.filters.state} onChange={(event) => updateFilter("state", event.target.value as SearchFiltersState["state"])}><option value="">{t("filters.anyState")}</option>{["new", "learning", "review", "due", "suspended", "buried"].map((value) => <option key={value} value={value}>{t(`states.${value}`)}</option>)}</select></label>
          <label><span>{t("filters.flag")}</span><select value={workspace.filters.flag} onChange={(event) => updateFilter("flag", event.target.value as SearchFiltersState["flag"])}><option value="">{t("filters.anyFlag")}</option>{[0, 1, 2, 3, 4, 5, 6, 7].map((value) => <option key={value} value={String(value)}>{t(`flags.${value}`)}</option>)}</select></label>
        </> : null}
        <label><span>{t("sort.label")}</span><select value={workspace.sortDirection} onChange={(event) => workspace.setSortDirection(event.target.value as "asc" | "desc")}><option value="asc">{t("sort.idAsc")}</option><option value="desc">{t("sort.idDesc")}</option></select></label>
      </div>
      <p className="search-syntax-hint">{t("query.help")}</p>
    </form>
  );
}
