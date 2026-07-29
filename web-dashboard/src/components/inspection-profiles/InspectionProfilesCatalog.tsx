import { Search, X } from "lucide-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { friendlyDetectedKind, profileLanguage } from "../../lib/inspectionProfileBasicView";
import type {
  InspectionProfileState,
  InspectionProfileSummary,
  InspectionProfilesQueryResponse,
} from "../../types/inspectionProfiles";

const PROFILE_STATES: InspectionProfileState[] = [
  "needs_review",
  "confirmed",
  "suggested",
  "not_configured",
  "disabled",
];

export const INSPECTION_PROFILE_STATE_PRIORITY: Readonly<Record<InspectionProfileState, number>> = Object.freeze({
  needs_review: 0,
  confirmed: 1,
  suggested: 2,
  not_configured: 3,
  disabled: 4,
});

export function filterAndSortInspectionProfileItems(
  items: readonly InspectionProfileSummary[],
  stateFilter: InspectionProfileState | "all",
  search: string,
  language: string,
): InspectionProfileSummary[] {
  const normalizedSearch = search.trim().toLocaleLowerCase(language);
  return items
    .map((item, sourceIndex) => ({ item, sourceIndex }))
    .filter(({ item }) => stateFilter === "all" || item.effectiveState === stateFilter)
    .filter(({ item }) => item.structure.name.toLocaleLowerCase(language).includes(normalizedSearch))
    .sort((left, right) => (
      INSPECTION_PROFILE_STATE_PRIORITY[left.item.effectiveState]
      - INSPECTION_PROFILE_STATE_PRIORITY[right.item.effectiveState]
      || left.item.structure.name.localeCompare(right.item.structure.name, language, {
        sensitivity: "base",
        numeric: true,
      })
      || left.sourceIndex - right.sourceIndex
    ))
    .map(({ item }) => item);
}

interface InspectionProfilesCatalogProps {
  catalog: InspectionProfilesQueryResponse | null;
  items: readonly InspectionProfileSummary[];
  loadState: "loading" | "ready" | "error";
  selectedNoteTypeId: string | null;
  onSelect: (noteTypeId: string) => void;
}

export default function InspectionProfilesCatalog({
  catalog,
  items,
  loadState,
  selectedNoteTypeId,
  onSelect,
}: InspectionProfilesCatalogProps) {
  const { t, i18n } = useTranslation("pages");
  const [search, setSearch] = useState("");
  const [stateFilter, setStateFilter] = useState<InspectionProfileState | "all">("all");
  const language = i18n.resolvedLanguage || i18n.language || "en";
  const filteredItems = useMemo(
    () => filterAndSortInspectionProfileItems(items, stateFilter, search, language),
    [items, language, search, stateFilter],
  );
  const hasFilters = Boolean(search || stateFilter !== "all");

  return (
    <aside className="inspection-catalog workspace-region" aria-labelledby="inspection-catalog-title">
      <div className="inspection-catalog-header">
        <h2 id="inspection-catalog-title" className="workspace-section-title">{t("inspectionProfiles.catalog.title")}</h2>
        <span>
          <span className="sr-only">{t("inspectionProfiles.catalog.count", { returned: catalog?.returnedCount ?? 0, total: catalog?.totalCount ?? 0 })}</span>
          <span aria-hidden="true">{catalog?.returnedCount ?? 0}/{catalog?.totalCount ?? 0}</span>
        </span>
      </div>
      <div className="inspection-catalog-controls">
        <label className="inspection-search" htmlFor="inspection-profile-search">
          <span className="sr-only">{t("inspectionProfiles.catalog.search")}</span>
          <Search size={15} aria-hidden="true" />
          <input
            id="inspection-profile-search"
            type="search"
            placeholder={t("inspectionProfiles.catalog.search")}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
        <label className="inspection-filter" htmlFor="inspection-profile-state-filter">
          <span className="sr-only">{t("inspectionProfiles.catalog.stateFilter")}</span>
          <select
            id="inspection-profile-state-filter"
            aria-label={t("inspectionProfiles.catalog.stateFilter")}
            value={stateFilter}
            onChange={(event) => setStateFilter(event.target.value as InspectionProfileState | "all")}
          >
            <option value="all">{t("inspectionProfiles.catalog.allStates")}</option>
            {PROFILE_STATES.map((state) => <option key={state} value={state}>{t(`inspectionProfiles.states.${state}`)}</option>)}
          </select>
        </label>
        {hasFilters ? (
          <button
            type="button"
            className="inspection-clear-filters"
            aria-label={t("inspectionProfiles.catalog.clearFilters")}
            title={t("inspectionProfiles.catalog.clearFilters")}
            onClick={() => {
              setSearch("");
              setStateFilter("all");
            }}
          >
            <X size={15} aria-hidden="true" />
          </button>
        ) : null}
      </div>
      {loadState === "loading" ? <p className="inspection-catalog-empty" role="status">{t("inspectionProfiles.load.loading")}</p> : null}
      {loadState === "ready" && !items.length ? <p className="inspection-catalog-empty">{t("inspectionProfiles.catalog.empty")}</p> : null}
      {loadState === "ready" && items.length > 0 && !filteredItems.length ? <p className="inspection-catalog-empty">{t("inspectionProfiles.catalog.noMatches")}</p> : null}
      <div className="inspection-note-list">
        {filteredItems.map((item) => (
          <NoteTypeButton
            key={item.structure.noteTypeId}
            item={item}
            selected={item.structure.noteTypeId === selectedNoteTypeId}
            onClick={() => onSelect(item.structure.noteTypeId)}
          />
        ))}
      </div>
      {catalog?.truncated ? <p className="inspection-truncated" role="status">{t("inspectionProfiles.catalog.truncated", { count: catalog.returnedCount, total: catalog.totalCount })}</p> : null}
    </aside>
  );
}

function NoteTypeButton({
  item,
  selected,
  onClick,
}: {
  item: InspectionProfileSummary;
  selected: boolean;
  onClick: () => void;
}) {
  const { t, i18n } = useTranslation("pages");
  const language = profileLanguage(i18n.resolvedLanguage);
  const kind = friendlyDetectedKind(item.suggestion.detectedKind, language).label;
  return (
    <button
      type="button"
      className={`inspection-note-button workspace-interactive${selected ? " is-selected workspace-selected" : ""}`}
      aria-pressed={selected}
      title={item.structure.name}
      onClick={onClick}
    >
      <span className="inspection-note-name">{item.structure.name}</span>
      <span className={`inspection-state-badge is-${item.effectiveState}`}>{t(`inspectionProfiles.states.${item.effectiveState}`)}</span>
      <small>{kind} · {t(`inspectionProfiles.stateHints.${item.effectiveState}`)}</small>
    </button>
  );
}
