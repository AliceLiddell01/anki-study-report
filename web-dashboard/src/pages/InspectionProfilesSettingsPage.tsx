import { Download, FileCheck2, Search, ShieldCheck, Upload } from "lucide-react";
import { useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import AccessibleModal from "../components/AccessibleModal";
import {
  ChecksEditor,
  FieldMappingsEditor,
  InspectionPreview,
  SuggestionPanel,
  TemplateScopeEditor,
} from "../components/inspection-profiles/ProfileEditors";
import { useInspectionProfilesWorkspace } from "../hooks/useInspectionProfilesWorkspace";
import { parseInspectionProfileDocument } from "../lib/inspectionProfilesApi";
import type { InspectionProfile, InspectionProfileState, InspectionProfileSummary } from "../types/inspectionProfiles";

const STATE_ORDER: Record<InspectionProfileState, number> = {
  needs_review: 0, confirmed: 1, suggested: 2, not_configured: 3, disabled: 4,
};
type ConfirmAction = "apply_suggestion" | "save_draft" | "disable" | "delete" | null;

export default function InspectionProfilesSettingsPage() {
  const { t, i18n } = useTranslation("pages");
  const workspace = useInspectionProfilesWorkspace();
  const [search, setSearch] = useState("");
  const [stateFilter, setStateFilter] = useState<InspectionProfileState | "all">("all");
  const [pendingSelection, setPendingSelection] = useState<string | null>(null);
  const [confirmAction, setConfirmAction] = useState<ConfirmAction>(null);
  const [importMessage, setImportMessage] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const filteredItems = useMemo(() => workspace.items
    .filter((item) => stateFilter === "all" || item.effectiveState === stateFilter)
    .filter((item) => item.structure.name.toLocaleLowerCase(i18n.resolvedLanguage).includes(search.trim().toLocaleLowerCase(i18n.resolvedLanguage)))
    .sort((left, right) => STATE_ORDER[left.effectiveState] - STATE_ORDER[right.effectiveState]
      || left.structure.name.localeCompare(right.structure.name, i18n.resolvedLanguage)), [i18n.resolvedLanguage, search, stateFilter, workspace.items]);

  const summary = useMemo(() => ({
    total: workspace.items.length,
    confirmed: workspace.items.filter((item) => item.effectiveState === "confirmed").length,
    needs_review: workspace.items.filter((item) => item.effectiveState === "needs_review").length,
    not_configured: workspace.items.filter((item) => item.effectiveState === "not_configured").length,
    disabled: workspace.items.filter((item) => item.effectiveState === "disabled").length,
  }), [workspace.items]);

  const requestSelection = (noteTypeId: string) => {
    if (workspace.select(noteTypeId)) return;
    setPendingSelection(noteTypeId);
  };

  const applySuggestion = () => {
    if (workspace.dirty) setConfirmAction("apply_suggestion");
    else workspace.useSuggestion();
  };

  const executeConfirmAction = async () => {
    const action = confirmAction;
    setConfirmAction(null);
    if (action === "apply_suggestion") workspace.useSuggestion();
    if (action === "save_draft") await workspace.save("suggested");
    if (action === "disable") await workspace.disable();
    if (action === "delete") await workspace.remove();
  };

  const importProfile = async (file: File | undefined) => {
    if (!file) return;
    if (file.size > 1024 * 1024) {
      setImportMessage(t("inspectionProfiles.import.tooLarge"));
      return;
    }
    try {
      const document = parseInspectionProfileDocument(JSON.parse(await file.text()) as unknown);
      const imported = document.profiles[0];
      const target = workspace.items.find((item) => item.structure.noteTypeId === imported.noteTypeId);
      if (!target) throw new Error("missing_note_type");
      if (workspace.dirty) throw new Error("unsaved_changes");
      const structureFields = new Set(target.structure.fields.map((field) => `${field.ordinal}:${field.name}`));
      const templateOrdinals = new Set(target.structure.templates.map((template) => template.ordinal));
      const referencesCurrent = imported.fieldMappings.every((mapping) => mapping.fields.every((field) => structureFields.has(`${field.ordinal}:${field.name}`)))
        && imported.appliesTo.templateOrdinals.every((ordinal) => templateOrdinals.has(ordinal));
      if (!referencesCurrent || imported.expectedFingerprint.value !== target.structure.fingerprint.value) throw new Error("structure_mismatch");
      workspace.select(imported.noteTypeId, true);
      workspace.setDraft({
        ...imported,
        noteTypeName: target.structure.name,
        storedState: "suggested",
        confirmedAt: null,
        updatedAt: new Date().toISOString(),
      });
      setImportMessage(t("inspectionProfiles.import.loaded"));
    } catch (error) {
      const code = error instanceof Error ? error.message : "invalid";
      setImportMessage(t(`inspectionProfiles.import.${code}`, { defaultValue: t("inspectionProfiles.import.invalid") }));
    } finally {
      if (fileInput.current) fileInput.current.value = "";
    }
  };

  const exportProfile = () => {
    const profile = workspace.selected?.storedProfile;
    if (!profile) return;
    const payload = JSON.stringify({ schemaVersion: 1, revision: 0, profiles: [profile] }, null, 2);
    const url = URL.createObjectURL(new Blob([`${payload}\n`], { type: "application/json" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${safeFileName(profile.displayName || profile.noteTypeName)}-inspection-profile.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="inspection-workspace-page">
      <header className="inspection-page-header">
        <span className="brand-icon-badge"><ShieldCheck size={21} aria-hidden="true" /></span>
        <div>
          <p className="inspection-eyebrow">{t("inspectionProfiles.eyebrow")}</p>
          <h1>{t("inspectionProfiles.title")}</h1>
          <p>{t("inspectionProfiles.description")}</p>
          <p className="inspection-safety-note">{t("inspectionProfiles.safety")}</p>
        </div>
      </header>

      {workspace.loadState === "error" ? (
        <section className="inspection-load-state is-error" role="alert">
          <h2>{t("inspectionProfiles.load.failed")}</h2>
          <p>{statusLabel(t, workspace.loadError)}</p>
          <button type="button" className="secondary-button" onClick={() => void workspace.reload()}>{t("inspectionProfiles.actions.retry")}</button>
        </section>
      ) : null}

      {workspace.catalog && workspace.catalog.store.status !== "available" && workspace.catalog.store.status !== "empty" ? (
        <section className="inspection-store-warning" role="alert">
          <strong>{t(`inspectionProfiles.store.${workspace.catalog.store.status}.title`)}</strong>
          <span>{t(`inspectionProfiles.store.${workspace.catalog.store.status}.description`)}</span>
        </section>
      ) : null}

      <section className="inspection-summary" aria-label={t("inspectionProfiles.summary.label")}>
        <SummaryButton label={t("inspectionProfiles.summary.total")} value={summary.total} active={stateFilter === "all"} onClick={() => setStateFilter("all")} />
        <SummaryButton label={t("inspectionProfiles.states.confirmed")} value={summary.confirmed} active={stateFilter === "confirmed"} onClick={() => setStateFilter("confirmed")} />
        <SummaryButton label={t("inspectionProfiles.states.needs_review")} value={summary.needs_review} active={stateFilter === "needs_review"} onClick={() => setStateFilter("needs_review")} />
        <SummaryButton label={t("inspectionProfiles.states.not_configured")} value={summary.not_configured} active={stateFilter === "not_configured"} onClick={() => setStateFilter("not_configured")} />
        {summary.disabled ? <SummaryButton label={t("inspectionProfiles.states.disabled")} value={summary.disabled} active={stateFilter === "disabled"} onClick={() => setStateFilter("disabled")} /> : null}
      </section>

      <div className="inspection-workspace">
        <aside className="inspection-catalog" aria-labelledby="inspection-catalog-title">
          <div className="inspection-catalog-header">
            <h2 id="inspection-catalog-title">{t("inspectionProfiles.catalog.title")}</h2>
            <span>{workspace.catalog?.returnedCount ?? 0}/{workspace.catalog?.totalCount ?? 0}</span>
          </div>
          <label className="inspection-search" htmlFor="inspection-profile-search"><Search size={16} aria-hidden="true" /><span>{t("inspectionProfiles.catalog.search")}</span><input id="inspection-profile-search" type="search" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
          <label className="inspection-filter" htmlFor="inspection-profile-state-filter">{t("inspectionProfiles.catalog.stateFilter")}<select id="inspection-profile-state-filter" value={stateFilter} onChange={(event) => setStateFilter(event.target.value as InspectionProfileState | "all")}><option value="all">{t("inspectionProfiles.catalog.allStates")}</option>{Object.keys(STATE_ORDER).map((state) => <option key={state} value={state}>{t(`inspectionProfiles.states.${state}`)}</option>)}</select></label>
          {(search || stateFilter !== "all") ? <button type="button" className="inspection-clear-filters" onClick={() => { setSearch(""); setStateFilter("all"); }}>{t("inspectionProfiles.catalog.clearFilters")}</button> : null}
          {workspace.loadState === "loading" ? <p className="inspection-catalog-empty" role="status">{t("inspectionProfiles.load.loading")}</p> : null}
          {workspace.loadState === "ready" && !workspace.items.length ? <p className="inspection-catalog-empty">{t("inspectionProfiles.catalog.empty")}</p> : null}
          {workspace.loadState === "ready" && workspace.items.length && !filteredItems.length ? <p className="inspection-catalog-empty">{t("inspectionProfiles.catalog.noMatches")}</p> : null}
          <div className="inspection-note-list">
            {filteredItems.map((item) => <NoteTypeButton key={item.structure.noteTypeId} item={item} selected={item.structure.noteTypeId === workspace.selectedNoteTypeId} onClick={() => requestSelection(item.structure.noteTypeId)} />)}
          </div>
          {workspace.catalog?.truncated ? <p className="inspection-truncated" role="status">{t("inspectionProfiles.catalog.truncated", { count: workspace.catalog.returnedCount, total: workspace.catalog.totalCount })}</p> : null}
        </aside>

        <main className="inspection-editor" aria-live="off">
          {!workspace.selected ? <section className="inspection-empty-editor"><FileCheck2 size={34} aria-hidden="true" /><h2>{t("inspectionProfiles.editor.selectTitle")}</h2><p>{t("inspectionProfiles.editor.selectDescription")}</p></section> : (
            <ProfileEditor
              item={workspace.selected}
              workspace={workspace}
              onUseSuggestion={applySuggestion}
              onSaveDraft={() => workspace.selected?.effectiveState === "confirmed" ? setConfirmAction("save_draft") : void workspace.save("suggested")}
              onDisable={() => setConfirmAction("disable")}
              onDelete={() => setConfirmAction("delete")}
              onExport={exportProfile}
              onImport={() => fileInput.current?.click()}
            />
          )}
        </main>
      </div>

      <input ref={fileInput} className="sr-only" type="file" accept="application/json,.json" aria-label={t("inspectionProfiles.import.fileLabel")} onChange={(event) => void importProfile(event.target.files?.[0])} />
      {(workspace.status || importMessage) ? <p className={workspace.status?.includes("failed") || workspace.status?.includes("conflict") ? "inspection-global-status is-error" : "inspection-global-status"} role={workspace.status?.includes("failed") ? "alert" : "status"}>{importMessage ?? statusLabel(t, workspace.status)}</p> : null}

      {pendingSelection ? <AccessibleModal testId="inspection-unsaved-dialog" title={t("inspectionProfiles.unsaved.title")} closeLabel={t("inspectionProfiles.actions.close")} onRequestClose={() => setPendingSelection(null)} footer={<div className="product-modal-actions"><button type="button" className="secondary-button" onClick={() => setPendingSelection(null)}>{t("inspectionProfiles.actions.keepEditing")}</button><button type="button" className="danger-button" onClick={() => { workspace.select(pendingSelection, true); setPendingSelection(null); }}>{t("inspectionProfiles.actions.discard")}</button></div>}><p className="product-modal-lead">{t("inspectionProfiles.unsaved.description")}</p></AccessibleModal> : null}
      {confirmAction ? <ActionConfirmation action={confirmAction} noteTypeName={workspace.selected?.structure.name ?? ""} onClose={() => setConfirmAction(null)} onConfirm={() => void executeConfirmAction()} /> : null}
    </div>
  );
}

function ProfileEditor({ item, workspace, onUseSuggestion, onSaveDraft, onDisable, onDelete, onExport, onImport }: {
  item: InspectionProfileSummary;
  workspace: ReturnType<typeof useInspectionProfilesWorkspace>;
  onUseSuggestion: () => void;
  onSaveDraft: () => void;
  onDisable: () => void;
  onDelete: () => void;
  onExport: () => void;
  onImport: () => void;
}) {
  const { t } = useTranslation("pages");
  const draft = workspace.draft;
  const canMutate = workspace.catalog?.store.status === "available" || workspace.catalog?.store.status === "empty";
  return (
    <div className="inspection-editor-stack">
      <section className="inspection-editor-header">
        <div><p>{t("inspectionProfiles.editor.noteType")}</p><h2>{item.structure.name}</h2><span className={`inspection-state-badge is-${item.effectiveState}`}>{t(`inspectionProfiles.states.${item.effectiveState}`)}</span>{workspace.dirty ? <span className="inspection-dirty-badge">{t("inspectionProfiles.editor.unsaved")}</span> : null}</div>
        <dl><div><dt>{t("inspectionProfiles.editor.kind")}</dt><dd>{t(`inspectionProfiles.kinds.${item.structure.kind}`)}</dd></div><div><dt>{t("inspectionProfiles.editor.fields")}</dt><dd>{item.structure.fields.length}</dd></div><div><dt>{t("inspectionProfiles.editor.templates")}</dt><dd>{item.structure.templates.length}</dd></div></dl>
      </section>

      {item.effectiveState === "needs_review" ? <section className="inspection-review-warning" role="alert"><strong>{t("inspectionProfiles.review.title")}</strong><span>{t(`inspectionProfiles.reasons.${item.stateReason ?? "unknown"}`, { defaultValue: t("inspectionProfiles.review.description") })}</span><span>{t("inspectionProfiles.review.failClosed")}</span></section> : null}
      {item.effectiveState === "disabled" ? <section className="inspection-info-banner"><strong>{t("inspectionProfiles.disabled.title")}</strong><span>{t("inspectionProfiles.disabled.description")}</span></section> : null}
      {workspace.conflictRevision !== null ? <section className="inspection-conflict" role="alert"><h3>{t("inspectionProfiles.conflict.title")}</h3><p>{t("inspectionProfiles.conflict.description", { revision: workspace.conflictRevision })}</p><div><button type="button" className="secondary-button" onClick={() => void workspace.reload(true)}>{t("inspectionProfiles.conflict.reviewServer")}</button><button type="button" className="danger-button" onClick={workspace.resetToServer}>{t("inspectionProfiles.conflict.reloadDiscard")}</button></div></section> : null}

      <SuggestionPanel item={item} onUse={onUseSuggestion} />

      {!draft ? (
        <section className="inspection-panel inspection-start-panel"><h2>{t("inspectionProfiles.editor.notConfiguredTitle")}</h2><p>{t("inspectionProfiles.editor.notConfiguredDescription")}</p><div className="inspection-action-row"><button type="button" className="primary-button" onClick={onUseSuggestion}>{t("inspectionProfiles.actions.useSuggestion")}</button><button type="button" className="secondary-button" onClick={workspace.startEmpty}>{t("inspectionProfiles.actions.startEmpty")}</button><button type="button" className="secondary-button" onClick={onImport}><Upload size={16} aria-hidden="true" />{t("inspectionProfiles.actions.import")}</button></div></section>
      ) : (
        <>
          <section className="inspection-panel">
            <label className="inspection-display-name" htmlFor="inspection-profile-display-name">{t("inspectionProfiles.editor.displayName")}<input id="inspection-profile-display-name" className="form-control" value={draft.displayName} aria-describedby={workspace.fieldErrors["profile.displayName"] ? "inspection-profile-display-name-error" : "inspection-profile-display-name-help"} onChange={(event) => workspace.setDraft({ ...draft, displayName: event.target.value })} /></label>
            <p id="inspection-profile-display-name-help" className="inspection-help">{t("inspectionProfiles.editor.displayNameHelp")}</p>
            {workspace.fieldErrors["profile.displayName"] ? <p id="inspection-profile-display-name-error" className="inspection-inline-error">{t("inspectionProfiles.errors.required")}</p> : null}
          </section>
          <TemplateScopeEditor item={item} draft={draft} onChange={workspace.setDraft} errors={workspace.fieldErrors} />
          <FieldMappingsEditor item={item} draft={draft} onChange={workspace.setDraft} errors={workspace.fieldErrors} />
          <ChecksEditor draft={draft} onChange={workspace.setDraft} errors={workspace.fieldErrors} />
          {Object.keys(workspace.fieldErrors).length ? <ErrorSummary errors={workspace.fieldErrors} /> : null}
          {workspace.validation ? <InspectionPreview validation={workspace.validation} /> : null}
          <section className="inspection-actions-panel">
            <div className="inspection-action-row">
              <button type="button" className="secondary-button" disabled={workspace.busy} onClick={() => void workspace.validate()}>{t("inspectionProfiles.actions.validate")}</button>
              <button type="button" className="secondary-button" disabled={workspace.busy || (!workspace.dirty && item.effectiveState !== "confirmed") || !canMutate} onClick={onSaveDraft}>{t("inspectionProfiles.actions.saveDraft")}</button>
              <button type="button" className="primary-button" disabled={workspace.busy || !canMutate} onClick={() => void workspace.save("confirmed")}>{item.effectiveState === "confirmed" ? t("inspectionProfiles.actions.reconfirm") : item.effectiveState === "disabled" ? t("inspectionProfiles.actions.enable") : t("inspectionProfiles.actions.confirm")}</button>
            </div>
            <div className="inspection-action-row inspection-secondary-actions">
              {item.storedProfile ? <button type="button" className="secondary-button" onClick={onExport}><Download size={16} aria-hidden="true" />{t("inspectionProfiles.actions.export")}</button> : null}
              <button type="button" className="secondary-button" onClick={onImport}><Upload size={16} aria-hidden="true" />{t("inspectionProfiles.actions.import")}</button>
              {item.storedProfile && item.effectiveState !== "disabled" ? <button type="button" className="secondary-button" disabled={workspace.busy || !canMutate} onClick={onDisable}>{t("inspectionProfiles.actions.disable")}</button> : null}
              {item.storedProfile ? <button type="button" className="danger-button" disabled={workspace.busy || !canMutate} onClick={onDelete}>{t("inspectionProfiles.actions.delete")}</button> : null}
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function NoteTypeButton({ item, selected, onClick }: { item: InspectionProfileSummary; selected: boolean; onClick: () => void }) {
  const { t } = useTranslation("pages");
  return <button type="button" className={`inspection-note-button${selected ? " is-selected" : ""}`} aria-pressed={selected} title={item.structure.name} onClick={onClick}><span className="inspection-note-name">{item.structure.name}</span><span className={`inspection-state-badge is-${item.effectiveState}`}>{t(`inspectionProfiles.states.${item.effectiveState}`)}</span><small>{t(`inspectionProfiles.stateHints.${item.effectiveState}`)}</small><span className="inspection-note-meta">{t("inspectionProfiles.catalog.structure", { fields: item.structure.fields.length, templates: item.structure.templates.length })}</span></button>;
}

function SummaryButton({ label, value, active, onClick }: { label: string; value: number; active: boolean; onClick: () => void }) {
  return <button type="button" className={active ? "is-active" : undefined} aria-pressed={active} onClick={onClick}><span>{label}</span><strong>{value}</strong></button>;
}

function ErrorSummary({ errors }: { errors: Record<string, string> }) {
  const { t } = useTranslation("pages");
  const focus = (path: string) => document.getElementById(controlIdForError(path))?.focus();
  return <section className="inspection-error-summary" role="alert" aria-labelledby="inspection-errors-title"><h2 id="inspection-errors-title">{t("inspectionProfiles.errors.title")}</h2><p>{t("inspectionProfiles.errors.description")}</p><ul>{Object.entries(errors).map(([path, value]) => <li key={path}><button type="button" onClick={() => focus(path)}>{fieldLabel(t, path)}: {t(`inspectionProfiles.errors.${value}`, { defaultValue: value })}</button></li>)}</ul></section>;
}

function ActionConfirmation({ action, noteTypeName, onClose, onConfirm }: { action: Exclude<ConfirmAction, null>; noteTypeName: string; onClose: () => void; onConfirm: () => void }) {
  const { t } = useTranslation("pages");
  return <AccessibleModal testId={`inspection-${action}-dialog`} title={t(`inspectionProfiles.confirmations.${action}.title`)} closeLabel={t("inspectionProfiles.actions.close")} onRequestClose={onClose} footer={<div className="product-modal-actions"><button type="button" className="secondary-button" onClick={onClose}>{t("inspectionProfiles.actions.cancel")}</button><button type="button" className={action === "delete" ? "danger-button" : "primary-button"} onClick={onConfirm}>{t(`inspectionProfiles.confirmations.${action}.confirm`)}</button></div>}><p className="product-modal-lead">{t(`inspectionProfiles.confirmations.${action}.description`, { name: noteTypeName })}</p></AccessibleModal>;
}

type Translate = (key: string, options?: Record<string, unknown>) => string;
function statusLabel(t: Translate, code: string | null): string { return code ? t(`inspectionProfiles.status.${code}`, { defaultValue: t("inspectionProfiles.status.failed") }) : ""; }
function fieldLabel(t: Translate, path: string): string {
  if (path.includes("fieldMappings")) return t("inspectionProfiles.mappings.title");
  if (path.includes("checks")) return t("inspectionProfiles.checks.title");
  if (path.includes("appliesTo")) return t("inspectionProfiles.templates.title");
  return t("inspectionProfiles.editor.displayName");
}
function controlIdForError(path: string): string {
  const mapping = path.match(/fieldMappings\.(\d+)/);
  if (mapping) return `inspection-role-${mapping[1]}`;
  const check = path.match(/checks\.(\d+)\.(roles|minLength)/);
  if (check) return check[2] === "roles" ? `inspection-check-kind-${check[1]}` : `inspection-check-length-${check[1]}`;
  return "inspection-profile-display-name";
}
function safeFileName(value: string): string { return value.normalize("NFKD").replace(/[^a-zA-Z0-9_-]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 80) || "profile"; }
