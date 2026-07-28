import { Download, Upload } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";
import { useTranslation } from "react-i18next";
import AccessibleModal from "../components/AccessibleModal";
import RefreshButton from "../components/RefreshButton";
import { SettingsRouteHeader } from "../layout/SettingsRouteHeader";
import AdvancedProfileDisclosure from "../components/inspection-profiles/AdvancedProfileDisclosure";
import BasicProfileEditor from "../components/inspection-profiles/BasicProfileEditor";
import EditorModeTabs, { type InspectionEditorMode } from "../components/inspection-profiles/EditorModeTabs";
import InspectionProfileEditorIdentity from "../components/inspection-profiles/InspectionProfileEditorIdentity";
import InspectionProfilesCatalog from "../components/inspection-profiles/InspectionProfilesCatalog";
import ProfileValidationResult from "../components/inspection-profiles/ProfileValidationResult";
import { useInspectionProfilesWorkspace } from "../hooks/useInspectionProfilesWorkspace";
import { profileLanguage } from "../lib/inspectionProfileBasicView";
import { parseInspectionProfileDocument } from "../lib/inspectionProfilesApi";
import type { InspectionProfile, InspectionProfileSummary } from "../types/inspectionProfiles";
import "../styles/inspectionProfiles.css";

type ConfirmAction = "save_draft" | "disable" | "delete" | "replace_suggestion" | "start_empty" | null;

export default function InspectionProfilesSettingsPage() {
  const { t, i18n } = useTranslation("pages");
  const workspace = useInspectionProfilesWorkspace();
  const [pendingSelection, setPendingSelection] = useState<string | null>(null);
  const [confirmAction, setConfirmAction] = useState<ConfirmAction>(null);
  const [importMessage, setImportMessage] = useState<string | null>(null);
  const [editorMode, setEditorMode] = useState<InspectionEditorMode>("basic");
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => setEditorMode("basic"), [workspace.selectedNoteTypeId]);

  const requestSelection = (noteTypeId: string) => {
    if (workspace.select(noteTypeId)) return;
    setPendingSelection(noteTypeId);
  };

  const executeConfirmAction = async () => {
    const action = confirmAction;
    setConfirmAction(null);
    if (action === "save_draft") await runSave("suggested");
    if (action === "disable") await workspace.disable();
    if (action === "delete") await workspace.remove();
    if (action === "replace_suggestion") workspace.replaceWithSuggestion();
    if (action === "start_empty") workspace.startEmpty();
  };

  const focusErrorSummary = () => {
    window.setTimeout(() => document.getElementById("inspection-errors-title")?.focus(), 0);
  };

  const runValidate = async () => {
    const valid = await workspace.validate();
    if (!valid) focusErrorSummary();
  };

  const runSave = async (targetState: "suggested" | "confirmed") => {
    const saved = await workspace.save(targetState);
    if (!saved) focusErrorSummary();
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
      workspace.setImportedDraft({
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
    <div className="inspection-workspace-page workspace-page">
      <SettingsRouteHeader>
        <header className="inspection-page-header">
          <div>
            <h1 className="workspace-page-title">{t("inspectionProfiles.title")}</h1>
            <p className="workspace-body">{t("inspectionProfiles.description")}</p>
          </div>
          <RefreshButton label={copyForLanguage(profileLanguage(i18n.resolvedLanguage)).refreshCatalog} pending={workspace.loadState === "loading"} onClick={() => void workspace.reload(true, true)} />
          {workspace.status === "catalog_refreshed" ? <p className="inspection-catalog-refresh-status" role="status">{statusLabel(t, workspace.status)}</p> : null}
        </header>
      </SettingsRouteHeader>

      {workspace.loadState === "error" ? (
        <section className="inspection-load-state workspace-state is-error" role="alert">
          <h2>{t("inspectionProfiles.load.failed")}</h2>
          <p>{statusLabel(t, workspace.loadError)}</p>
          <button type="button" className="secondary-button" onClick={() => void workspace.reload()}>{t("inspectionProfiles.actions.retry")}</button>
        </section>
      ) : null}

      {workspace.catalog && workspace.catalog.store.status !== "available" && workspace.catalog.store.status !== "empty" ? (
        <section className="inspection-store-warning workspace-state" role="alert">
          <strong>{t(`inspectionProfiles.store.${workspace.catalog.store.status}.title`)}</strong>
          <span>{t(`inspectionProfiles.store.${workspace.catalog.store.status}.description`)}</span>
        </section>
      ) : null}

      <div className="inspection-workspace">
        <InspectionProfilesCatalog
          catalog={workspace.catalog}
          items={workspace.items}
          loadState={workspace.loadState}
          selectedNoteTypeId={workspace.selectedNoteTypeId}
          onSelect={requestSelection}
        />

        <main className="inspection-editor workspace-region" aria-live="off" aria-busy={workspace.loadState === "loading"}>
          {!workspace.selected ? <section className="inspection-empty-editor"><h2>{t("inspectionProfiles.editor.selectTitle")}</h2><p>{t("inspectionProfiles.editor.selectDescription")}</p><small>{t("inspectionProfiles.editor.selectSafety")}</small></section> : workspace.draft ? (
            <ProfileWorkspace
              item={workspace.selected}
              draft={workspace.draft}
              workspace={workspace}
              editorMode={editorMode}
              onEditorModeChange={setEditorMode}
              operationMessage={importMessage ?? (workspace.status === "catalog_refreshed" ? "" : statusLabel(t, workspace.status))}
              operationError={Boolean(workspace.status?.includes("failed") || workspace.status?.includes("conflict"))}
              onValidate={() => void runValidate()}
              onConfirm={() => void runSave("confirmed")}
              onSaveDraft={() => workspace.selected?.effectiveState === "confirmed" ? setConfirmAction("save_draft") : void runSave("suggested")}
              onDisable={() => setConfirmAction("disable")}
              onDelete={() => setConfirmAction("delete")}
              onExport={exportProfile}
              onImport={() => fileInput.current?.click()}
              onReplaceSuggestion={() => workspace.dirty ? setConfirmAction("replace_suggestion") : workspace.replaceWithSuggestion()}
              onStartEmpty={() => workspace.dirty ? setConfirmAction("start_empty") : workspace.startEmpty()}
              onRevealAdvancedError={(path) => {
                const basicControlId = basicControlIdForError(path);
                flushSync(() => setEditorMode(basicControlId ? "basic" : "advanced"));
                document.getElementById(basicControlId ?? controlIdForError(path))?.focus();
              }}
            />
          ) : null}
        </main>
      </div>

      <input ref={fileInput} className="sr-only" type="file" accept="application/json,.json" aria-label={t("inspectionProfiles.import.fileLabel")} onChange={(event) => void importProfile(event.target.files?.[0])} />
      {pendingSelection ? <AccessibleModal portal testId="inspection-unsaved-dialog" title={t("inspectionProfiles.unsaved.title")} closeLabel={t("inspectionProfiles.actions.close")} onRequestClose={() => setPendingSelection(null)} footer={<div className="product-modal-actions"><button type="button" className="secondary-button" onClick={() => setPendingSelection(null)}>{t("inspectionProfiles.actions.keepEditing")}</button><button type="button" className="danger-button" onClick={() => { workspace.select(pendingSelection, true); setPendingSelection(null); }}>{t("inspectionProfiles.actions.discard")}</button></div>}><p className="product-modal-lead">{t("inspectionProfiles.unsaved.description")}</p></AccessibleModal> : null}
      {confirmAction ? <ActionConfirmation action={confirmAction} noteTypeName={workspace.selected?.structure.name ?? ""} onClose={() => setConfirmAction(null)} onConfirm={() => void executeConfirmAction()} /> : null}
    </div>
  );
}

function ProfileWorkspace({ item, draft, workspace, editorMode, onEditorModeChange, operationMessage, operationError, onValidate, onConfirm, onSaveDraft, onDisable, onDelete, onExport, onImport, onReplaceSuggestion, onStartEmpty, onRevealAdvancedError }: {
  item: InspectionProfileSummary;
  draft: InspectionProfile;
  workspace: ReturnType<typeof useInspectionProfilesWorkspace>;
  editorMode: InspectionEditorMode;
  onEditorModeChange: (mode: InspectionEditorMode) => void;
  operationMessage: string;
  operationError: boolean;
  onValidate: () => void;
  onConfirm: () => void;
  onSaveDraft: () => void;
  onDisable: () => void;
  onDelete: () => void;
  onExport: () => void;
  onImport: () => void;
  onReplaceSuggestion: () => void;
  onStartEmpty: () => void;
  onRevealAdvancedError: (path: string) => void;
}) {
  const { t, i18n } = useTranslation("pages");
  const language = profileLanguage(i18n.resolvedLanguage);
  const copy = pageCopy(language);
  const canMutate = workspace.catalog?.store.status === "available" || workspace.catalog?.store.status === "empty";
  const blocking = hasBlockingIssue(item, draft);
  const revisionBlocked = workspace.conflictRevision !== null;
  const confirmedUnchanged = item.effectiveState === "confirmed" && !workspace.dirty;
  const primaryLabel = item.effectiveState === "needs_review" ? copy.reviewConfirm
    : item.effectiveState === "disabled" ? copy.reviewEnable
      : item.effectiveState === "confirmed" ? copy.validateConfirmChanges
        : copy.confirmEnable;
  const guidance = lifecycleGuidance(item, language, workspace.generatedDraft);
  const advancedErrorCount = Object.keys(workspace.fieldErrors).filter(isAdvancedError).length;

  return (
    <div className="inspection-editor-stack">
      <InspectionProfileEditorIdentity
        item={item}
        draft={draft}
        generatedDraft={workspace.generatedDraft}
        dirty={workspace.dirty}
        guidance={guidance}
        reviewReason={item.effectiveState === "needs_review" ? reasonLabel(item.stateReason, language) : null}
      />

      <EditorModeTabs
        mode={editorMode}
        label={copy.editorModeLabel}
        basicLabel={copy.basicMode}
        advancedLabel={copy.advancedMode}
        advancedErrorCount={advancedErrorCount}
        changed={workspace.dirty}
        changedLabel={copy.changed}
        advancedErrorsLabel={copy.advancedErrors}
        onChange={onEditorModeChange}
      />

      {editorMode === "basic" ? (
        <section id="inspection-basic-mode-panel" role="tabpanel" aria-labelledby="inspection-mode-basic" tabIndex={0}>
          <BasicProfileEditor item={item} draft={draft} onChange={workspace.setDraftFromUser} errors={workspace.fieldErrors} />
        </section>
      ) : <AdvancedProfileDisclosure item={item} draft={draft} errors={workspace.fieldErrors} onChange={workspace.setDraftFromUser} />}

      {Object.keys(workspace.fieldErrors).length ? <ErrorSummary errors={workspace.fieldErrors} onNavigate={onRevealAdvancedError} /> : null}
      {workspace.validation ? <ProfileValidationResult item={item} draft={draft} validation={workspace.validation} /> : null}

      {workspace.conflictRevision !== null ? (
        <section className="inspection-conflict workspace-state" role="alert">
          <h3>{t("inspectionProfiles.conflict.title")}</h3>
          <p>{t("inspectionProfiles.conflict.description", { revision: workspace.conflictRevision })}</p>
          <div className="workspace-state-actions">
            <button type="button" className="secondary-button" onClick={() => void workspace.reload(true)}>{copy.reviewServer}</button>
            <button type="button" className="danger-button" onClick={workspace.resetToServer}>{t("inspectionProfiles.conflict.reloadDiscard")}</button>
          </div>
        </section>
      ) : null}

      <section className="inspection-primary-actions" aria-label={copy.actionsLabel}>
        <div className="inspection-action-copy">
          <strong><span className="inspection-milestone" aria-hidden="true">7</span>{confirmedUnchanged ? copy.enabled : primaryLabel}</strong>
          <p>{confirmedUnchanged ? copy.enabledHelp : copy.primaryHelp}</p>
        </div>
        <div className="inspection-action-row">
          {!confirmedUnchanged ? (
            <button type="button" className="primary-button" disabled={workspace.busy || !canMutate || blocking || revisionBlocked} onClick={onConfirm}>
              {workspace.busy ? copy.working : primaryLabel}
            </button>
          ) : <span className="inspection-enabled-status">{copy.enabled}</span>}
          <button type="button" className="secondary-button" disabled={workspace.busy} onClick={onValidate}>{copy.checkSetup}</button>
          {(workspace.generatedDraft || (item.effectiveState === "suggested" && workspace.dirty) || (item.effectiveState === "confirmed" && workspace.dirty)) ? (
            <button type="button" className="secondary-button" disabled={workspace.busy || !canMutate || revisionBlocked} onClick={onSaveDraft}>{item.effectiveState === "suggested" ? copy.saveChanges : copy.saveDraft}</button>
          ) : null}
        </div>
        {blocking ? <p className="inspection-inline-error">{copy.blockingHelp}</p> : null}
        {operationMessage ? <p className={`inspection-operation-status${operationError ? " is-error" : ""}`} role={operationError ? "alert" : "status"}>{operationMessage}</p> : null}
      </section>

      <details className="inspection-major-disclosure inspection-tools-disclosure">
        <summary>
          <span><strong>{copy.profileTools}</strong><small>{copy.profileToolsHelp}</small></span>
        </summary>
        <div className="inspection-profile-tools">
          <div className="inspection-profile-tool-group">
            {item.storedProfile ? <button type="button" className="secondary-button" onClick={onExport}><Download size={16} aria-hidden="true" />{t("inspectionProfiles.actions.export")}</button> : null}
            <button type="button" className="secondary-button" onClick={onImport}><Upload size={16} aria-hidden="true" />{t("inspectionProfiles.actions.import")}</button>
            <button type="button" className="tertiary-button" onClick={onReplaceSuggestion}>{copy.resetSuggestion}</button>
          </div>
          <div className="inspection-profile-tool-group is-destructive">
            <button type="button" className="tertiary-button" onClick={onStartEmpty}>{t("inspectionProfiles.actions.startEmpty")}</button>
            {item.storedProfile && item.effectiveState !== "disabled" ? <button type="button" className="secondary-button" disabled={workspace.busy || !canMutate || revisionBlocked} onClick={onDisable}>{t("inspectionProfiles.actions.disable")}</button> : null}
            {item.storedProfile ? <button type="button" className="danger-button" disabled={workspace.busy || !canMutate || revisionBlocked} onClick={onDelete}>{t("inspectionProfiles.actions.delete")}</button> : null}
          </div>
        </div>
      </details>
    </div>
  );
}

function ErrorSummary({ errors, onNavigate }: { errors: Record<string, string>; onNavigate: (path: string) => void }) {
  const { t } = useTranslation("pages");
  return <section className="inspection-error-summary" role="alert" aria-labelledby="inspection-errors-title"><h3 id="inspection-errors-title" tabIndex={-1}>{t("inspectionProfiles.errors.title")}</h3><p>{t("inspectionProfiles.errors.description")}</p><ul>{Object.entries(errors).map(([path, value]) => <li key={path}><button type="button" onClick={() => onNavigate(path)}>{fieldLabel(t, path)}: {t(`inspectionProfiles.errors.${value}`, { defaultValue: value })}</button></li>)}</ul></section>;
}

function isAdvancedError(path: string): boolean {
  return basicControlIdForError(path) === null;
}

function ActionConfirmation({ action, noteTypeName, onClose, onConfirm }: { action: Exclude<ConfirmAction, null>; noteTypeName: string; onClose: () => void; onConfirm: () => void }) {
  const { t, i18n } = useTranslation("pages");
  const language = profileLanguage(i18n.resolvedLanguage);
  const local = confirmationCopy(action, noteTypeName, language);
  return <AccessibleModal portal testId={`inspection-${action}-dialog`} title={local.title} closeLabel={t("inspectionProfiles.actions.close")} onRequestClose={onClose} footer={<div className="product-modal-actions"><button type="button" className="secondary-button" onClick={onClose}>{t("inspectionProfiles.actions.cancel")}</button><button type="button" className={action === "delete" || action === "start_empty" ? "danger-button" : "primary-button"} onClick={onConfirm}>{local.confirm}</button></div>}><p className="product-modal-lead">{local.description}</p></AccessibleModal>;
}

function hasBlockingIssue(item: InspectionProfileSummary, draft: InspectionProfile): boolean {
  const roles = new Set(draft.fieldMappings.map((mapping) => mapping.role));
  const missingField = draft.fieldMappings.some((mapping) => !mapping.fields.length);
  const duplicateFields = new Set(draft.fieldMappings.flatMap((mapping) => mapping.fields.map((field) => `${field.ordinal}:${field.name}`))).size
    !== draft.fieldMappings.flatMap((mapping) => mapping.fields).length;
  const invalidCheck = draft.checks.some((check) => !check.roles.length || check.roles.some((role) => !roles.has(role)));
  const missingTemplate = draft.appliesTo.templateOrdinals.some((ordinal) => !item.structure.templates.some((template) => template.ordinal === ordinal));
  const ambiguousSuggestion = item.effectiveState === "not_configured" && item.suggestion.confidence < 0.5 && item.suggestion.unresolvedFields.length > 0;
  return missingField || duplicateFields || invalidCheck || missingTemplate || ambiguousSuggestion;
}

function lifecycleGuidance(item: InspectionProfileSummary, language: "ru" | "en", generated: boolean) {
  const ru = language === "ru";
  if (item.effectiveState === "not_configured") return {
    title: ru ? "Безопасный вариант уже подготовлен" : "A safe setup is ready",
    description: ru
      ? "Он существует только в браузере, ещё не сохранён и не влияет на карточки."
      : "It exists only in this browser, is not saved, and does not affect cards.",
  };
  if (item.effectiveState === "suggested") return { title: ru ? "Черновик сохранён" : "Draft saved", description: ru ? "Проверки ещё не включены." : "Checks are not enabled yet." };
  if (item.effectiveState === "confirmed") return { title: ru ? "Профиль включён" : "Profile enabled", description: ru ? "Он используется для проверки этого точного типа записи." : "It is used to inspect this exact note type." };
  if (item.effectiveState === "needs_review") return { title: ru ? "Требуется повторная проверка" : "Review is required", description: ru ? "Проверки временно не применяются, пока профиль не будет подтверждён снова." : "Checks are temporarily fail-closed until the profile is confirmed again." };
  return { title: ru ? "Проверки отключены" : "Checks disabled", description: ru ? "Настройки сохранены, но не создают authoritative issues." : "The setup is preserved but creates no authoritative issues." };
}

function reasonLabel(reason: string | null, language: "ru" | "en"): string {
  const ru = language === "ru";
  const reasons: Record<string, [string, string]> = {
    field_added: ["Добавлено поле; проверьте назначение полей.", "A field was added; review field purposes."],
    field_removed: ["Сопоставленное поле удалено.", "A mapped field was removed."],
    field_changed: ["Имя или порядок поля изменились.", "A field name or order changed."],
    template_field_usage_changed: ["Изменились шаблоны или ссылки на поля.", "Templates or their field references changed."],
    fingerprint_mismatch: ["Структурный fingerprint больше не совпадает.", "The structure fingerprint no longer matches."],
  };
  return (reasons[reason ?? ""] ?? ["Структура изменилась неизвестным безопасным способом.", "The structure changed for an unknown safe reason."])[ru ? 0 : 1];
}

function pageCopy(language: "ru" | "en") {
  return language === "ru" ? {
    editorModeLabel: "Режим редактора профиля", basicMode: "Основное", advancedMode: "Расширенное", changed: "Изменено", advancedErrors: (count: number) => `Ошибок в расширенном режиме: ${count}`, actionsLabel: "Действия профиля", checkSetup: "Проверить настройку", confirmEnable: "Подтвердить и включить", reviewConfirm: "Проверить и подтвердить снова", reviewEnable: "Проверить и включить", validateConfirmChanges: "Проверить и подтвердить изменения", enabled: "Включено", enabledHelp: "Профиль уже authoritative; повторное подтверждение без изменений не требуется.", primaryHelp: "Backend сначала проверит структуру и ограниченный пример, затем сохранит профиль только при успехе.", saveDraft: "Сохранить как черновик", saveChanges: "Сохранить изменения", working: "Выполняется…", blockingHelp: "Разрешите неоднозначность или исправьте обязательные ссылки перед включением.", profileTools: "Инструменты профиля", profileToolsHelp: "Импорт, экспорт, сброс и destructive actions", resetSuggestion: "Восстановить предложенную настройку", reviewServer: "Обновить сведения о сервере",
  } : {
    editorModeLabel: "Profile editor mode", basicMode: "Basic", advancedMode: "Advanced", changed: "Changed", advancedErrors: (count: number) => `Advanced mode errors: ${count}`, actionsLabel: "Profile actions", checkSetup: "Check setup", confirmEnable: "Confirm and enable", reviewConfirm: "Review and confirm again", reviewEnable: "Review and enable", validateConfirmChanges: "Validate and confirm changes", enabled: "Enabled", enabledHelp: "The profile is already authoritative; unchanged profiles do not need reconfirmation.", primaryHelp: "The backend validates the structure and a bounded sample before saving only on success.", saveDraft: "Save as draft", saveChanges: "Save changes", working: "Working…", blockingHelp: "Resolve ambiguity or fix required references before enabling the profile.", profileTools: "Profile tools", profileToolsHelp: "Import, export, reset, and destructive actions", resetSuggestion: "Restore suggested setup", reviewServer: "Refresh server information",
  };
}

function copyForLanguage(language: "ru" | "en") {
  return { refreshCatalog: language === "ru" ? "Обновить список" : "Refresh list" };
}

function confirmationCopy(action: Exclude<ConfirmAction, null>, name: string, language: "ru" | "en") {
  const ru = language === "ru";
  if (action === "save_draft") return { title: ru ? "Сделать профиль неактивным?" : "Make this profile inactive?", description: ru ? `Сохранение «${name}» как черновика отключит authoritative проверки до повторного подтверждения.` : `Saving “${name}” as a draft disables authoritative checks until it is reconfirmed.`, confirm: ru ? "Сохранить как черновик" : "Save as draft" };
  if (action === "disable") return { title: ru ? "Отключить профиль?" : "Disable this profile?", description: ru ? `Настройки «${name}» сохранятся, но проверки перестанут применяться.` : `The “${name}” setup remains stored, but checks stop applying.`, confirm: ru ? "Отключить" : "Disable" };
  if (action === "delete") return { title: ru ? "Удалить локальный профиль?" : "Delete the local profile?", description: ru ? `Профиль «${name}» будет удалён. Карточки и тип записи Anki не изменятся.` : `The “${name}” profile will be deleted. Anki cards and the note type remain unchanged.`, confirm: ru ? "Удалить профиль" : "Delete profile" };
  if (action === "replace_suggestion") return { title: ru ? "Заменить текущие изменения?" : "Replace current changes?", description: ru ? "Детерминированная подсказка заменит пользовательский черновик, но ничего не сохранит и не включит." : "The deterministic suggestion replaces the user draft without saving or enabling it.", confirm: ru ? "Восстановить подсказку" : "Restore suggestion" };
  return { title: ru ? "Начать с пустого профиля?" : "Start with an empty profile?", description: ru ? "Текущие пользовательские изменения будут отброшены. Пустой профиль останется несохранённым." : "Current user changes will be discarded. The empty profile remains unsaved.", confirm: ru ? "Начать с пустого" : "Start empty" };
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
  const mapping = path.match(/fieldMappings\.(\d+)\.(role|fields)/);
  if (mapping) return mapping[2] === "role" ? `inspection-role-${mapping[1]}` : `inspection-mapping-${mapping[1]}`;
  const check = path.match(/checks\.(\d+)\.(checkId|kind|priority|mode|roles|minLength)/);
  if (check) {
    if (check[2] === "checkId") return `inspection-check-id-${check[1]}`;
    if (check[2] === "roles") return `inspection-check-roles-${check[1]}`;
    if (check[2] === "minLength") return `inspection-check-length-${check[1]}`;
    return `inspection-check-${check[2]}-${check[1]}`;
  }
  if (path.includes("appliesTo")) return "inspection-template-scope";
  return "inspection-profile-display-name";
}
function basicControlIdForError(path: string): string | null {
  if (path === "profile.fieldMappings") return "inspection-basic-fields";
  const mapping = path.match(/fieldMappings\.(\d+)\.fields/);
  if (mapping) return `inspection-basic-role-${mapping[1]}`;
  if (path === "profile.checks") return "inspection-basic-requirements";
  const check = path.match(/checks\.(\d+)\.(roles|minLength)/);
  if (check) return check[2] === "roles" ? `inspection-basic-check-role-${check[1]}` : `inspection-basic-min-length-${check[1]}`;
  if (path === "profile.appliesTo.templateOrdinals") return "inspection-basic-template-scope";
  return null;
}
function safeFileName(value: string): string { return value.normalize("NFKD").replace(/[^a-zA-Z0-9_-]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 80) || "profile"; }
