import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  fetchInspectionProfiles,
  InspectionProfilesApiError,
  updateInspectionProfile,
  validateInspectionProfile,
} from "../lib/inspectionProfilesApi";
import type {
  InspectionProfile,
  InspectionProfileSummary,
  InspectionProfilesQueryResponse,
  InspectionValidateResponse,
} from "../types/inspectionProfiles";

type LoadState = "loading" | "ready" | "error";
export type InspectionDraftOrigin = "none" | "generated" | "stored" | "imported" | "empty";

export interface InspectionProfilesWorkspace {
  catalog: InspectionProfilesQueryResponse | null;
  items: InspectionProfileSummary[];
  loadState: LoadState;
  loadError: string | null;
  selectedNoteTypeId: string | null;
  selected: InspectionProfileSummary | null;
  draft: InspectionProfile | null;
  draftOrigin: InspectionDraftOrigin;
  generatedDraft: boolean;
  hasUserEdits: boolean;
  dirty: boolean;
  validation: InspectionValidateResponse | null;
  fieldErrors: Record<string, string>;
  busy: boolean;
  status: string | null;
  conflictRevision: number | null;
  reload: (preserveDraft?: boolean, announce?: boolean) => Promise<void>;
  select: (noteTypeId: string | null, discardDirty?: boolean) => boolean;
  setDraftFromUser: (draft: InspectionProfile | null) => void;
  setImportedDraft: (draft: InspectionProfile) => void;
  replaceWithSuggestion: () => void;
  startEmpty: () => void;
  validate: () => Promise<boolean>;
  save: (targetState: "suggested" | "confirmed") => Promise<boolean>;
  disable: () => Promise<boolean>;
  remove: () => Promise<boolean>;
  resetToServer: () => void;
  clearStatus: () => void;
}

interface DraftSnapshot {
  profile: InspectionProfile | null;
  baseline: InspectionProfile | null;
  origin: InspectionDraftOrigin;
  userEdited: boolean;
}

export function useInspectionProfilesWorkspace(): InspectionProfilesWorkspace {
  const [catalog, setCatalog] = useState<InspectionProfilesQueryResponse | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedNoteTypeId, setSelectedNoteTypeId] = useState<string | null>(null);
  const [snapshot, setSnapshot] = useState<DraftSnapshot>({ profile: null, baseline: null, origin: "none", userEdited: false });
  const [validation, setValidation] = useState<InspectionValidateResponse | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [conflictRevision, setConflictRevision] = useState<number | null>(null);

  const selectedIdRef = useRef<string | null>(null);
  const snapshotRef = useRef(snapshot);
  const busyRef = useRef(false);
  const querySequence = useRef(0);
  const queryController = useRef<AbortController | null>(null);
  const validateController = useRef<AbortController | null>(null);

  const items = catalog?.items ?? [];
  const selected = items.find((item) => item.structure.noteTypeId === selectedNoteTypeId) ?? null;
  const dirty = useMemo(
    () => snapshot.userEdited && stableJson(snapshot.profile) !== stableJson(snapshot.baseline),
    [snapshot],
  );

  const commitSnapshot = useCallback((next: DraftSnapshot) => {
    const cloned = cloneSnapshot(next);
    snapshotRef.current = cloned;
    setSnapshot(cloned);
  }, []);

  const clearEditorFeedback = useCallback(() => {
    setValidation(null);
    setFieldErrors({});
    setStatus(null);
  }, []);

  const materializeItem = useCallback((item: InspectionProfileSummary | null) => {
    if (!item) {
      commitSnapshot({ profile: null, baseline: null, origin: "none", userEdited: false });
      return;
    }
    if (item.storedProfile) {
      const stored = cloneProfile(item.storedProfile);
      commitSnapshot({ profile: stored, baseline: cloneProfile(stored), origin: "stored", userEdited: false });
      return;
    }
    const generated = createDraft(item, true);
    commitSnapshot({ profile: generated, baseline: cloneProfile(generated), origin: "generated", userEdited: false });
  }, [commitSnapshot]);

  const reload = useCallback(async (preserveDraft = false, announce = false) => {
    const sequence = ++querySequence.current;
    queryController.current?.abort();
    const controller = new AbortController();
    queryController.current = controller;
    if (!preserveDraft) setLoadState("loading");
    setLoadError(null);
    try {
      const response = await fetchInspectionProfiles({ schemaVersion: 1, noteTypeIds: [], limit: 500 }, controller.signal);
      if (sequence !== querySequence.current) return;
      setCatalog(response);
      setLoadState("ready");
      if (announce) setStatus("catalog_refreshed");
      const currentSelectedId = selectedIdRef.current;
      if (!currentSelectedId) return;
      const current = response.items.find((item) => item.structure.noteTypeId === currentSelectedId) ?? null;
      if (!current) {
        selectedIdRef.current = null;
        setSelectedNoteTypeId(null);
        materializeItem(null);
        clearEditorFeedback();
        return;
      }
      const protectedUserDraft = snapshotRef.current.userEdited
        && stableJson(snapshotRef.current.profile) !== stableJson(snapshotRef.current.baseline);
      if (preserveDraft || protectedUserDraft) return;
      materializeItem(current);
      setValidation(null);
      setFieldErrors({});
    } catch (error) {
      if (controller.signal.aborted) return;
      setLoadState("error");
      setLoadError(error instanceof InspectionProfilesApiError ? error.code : "inspection_profiles_failed");
    }
  }, [clearEditorFeedback, materializeItem]);

  useEffect(() => {
    void reload();
    return () => {
      queryController.current?.abort();
      validateController.current?.abort();
    };
  }, [reload]);

  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  const select = useCallback((noteTypeId: string | null, discardDirty = false) => {
    const current = snapshotRef.current;
    const currentDirty = current.userEdited && stableJson(current.profile) !== stableJson(current.baseline);
    if (currentDirty && !discardDirty) return false;
    selectedIdRef.current = noteTypeId;
    setSelectedNoteTypeId(noteTypeId);
    const item = catalog?.items.find((candidate) => candidate.structure.noteTypeId === noteTypeId) ?? null;
    materializeItem(item);
    setValidation(null);
    setFieldErrors({});
    setConflictRevision(null);
    setStatus(null);
    return true;
  }, [catalog?.items, materializeItem]);

  const setDraftFromUser = useCallback((next: InspectionProfile | null) => {
    commitSnapshot({ ...snapshotRef.current, profile: cloneProfile(next), userEdited: true });
    clearEditorFeedback();
  }, [clearEditorFeedback, commitSnapshot]);

  const setImportedDraft = useCallback((next: InspectionProfile) => {
    commitSnapshot({ profile: cloneProfile(next), baseline: null, origin: "imported", userEdited: true });
    clearEditorFeedback();
  }, [clearEditorFeedback, commitSnapshot]);

  const replaceWithSuggestion = useCallback(() => {
    const item = catalog?.items.find((candidate) => candidate.structure.noteTypeId === selectedIdRef.current) ?? null;
    if (!item) return;
    const current = snapshotRef.current;
    const generated = createDraft(item, true);
    const cleanGenerated = current.origin === "generated" && !current.userEdited;
    commitSnapshot({
      profile: generated,
      baseline: cleanGenerated ? cloneProfile(generated) : cloneProfile(current.baseline),
      origin: "generated",
      userEdited: !cleanGenerated,
    });
    clearEditorFeedback();
    setConflictRevision(null);
  }, [catalog?.items, clearEditorFeedback, commitSnapshot]);

  const startEmpty = useCallback(() => {
    const item = catalog?.items.find((candidate) => candidate.structure.noteTypeId === selectedIdRef.current) ?? null;
    if (!item) return;
    commitSnapshot({ profile: createDraft(item, false), baseline: null, origin: "empty", userEdited: true });
    clearEditorFeedback();
  }, [catalog?.items, clearEditorFeedback, commitSnapshot]);

  const preparedDraft = useCallback((targetState: "suggested" | "confirmed") => {
    const draft = snapshotRef.current.profile;
    const item = catalog?.items.find((candidate) => candidate.structure.noteTypeId === selectedIdRef.current) ?? null;
    if (!draft || !item) return null;
    const now = new Date().toISOString();
    return {
      ...cloneProfile(draft)!,
      noteTypeName: item.structure.name,
      storedState: targetState,
      expectedFingerprint: { ...item.structure.fingerprint },
      confirmedAt: targetState === "confirmed" ? now : null,
      updatedAt: now,
    };
  }, [catalog?.items]);

  const beginAction = useCallback(() => {
    if (busyRef.current) return false;
    busyRef.current = true;
    setBusy(true);
    return true;
  }, []);

  const endAction = useCallback(() => {
    busyRef.current = false;
    setBusy(false);
  }, []);

  const runValidation = useCallback(async (profile: InspectionProfile): Promise<InspectionValidateResponse | null> => {
    const clientErrors = validateClientDraft(profile);
    if (Object.keys(clientErrors).length) {
      setFieldErrors(clientErrors);
      setValidation(null);
      setStatus("client_validation_failed");
      return null;
    }
    validateController.current?.abort();
    const controller = new AbortController();
    validateController.current = controller;
    setFieldErrors({});
    try {
      const result = await validateInspectionProfile({
        schemaVersion: 2,
        profile,
        preview: { mode: "sample", limit: 10 },
      }, controller.signal);
      if (controller.signal.aborted) return null;
      setValidation(result);
      setFieldErrors(result.fieldErrors);
      setStatus(result.valid ? "validation_succeeded" : "server_validation_failed");
      return result;
    } catch (error) {
      if (controller.signal.aborted) return null;
      const apiError = error instanceof InspectionProfilesApiError ? error : null;
      setFieldErrors(apiError?.fieldErrors ?? {});
      setStatus(apiError?.code ?? "inspection_profiles_failed");
      return null;
    }
  }, []);

  const validate = useCallback(async () => {
    const draft = snapshotRef.current.profile;
    if (!draft || !beginAction()) return false;
    try {
      return Boolean(await runValidation(draft));
    } finally {
      endAction();
    }
  }, [beginAction, endAction, runValidation]);

  const mutate = useCallback(async (
    operation: () => ReturnType<typeof updateInspectionProfile>,
    successCode: string,
  ) => {
    setStatus(null);
    setConflictRevision(null);
    try {
      await operation();
      setStatus(successCode);
      const current = snapshotRef.current;
      commitSnapshot({ ...current, origin: "stored", userEdited: false, baseline: cloneProfile(current.profile) });
      await reload(false);
      return true;
    } catch (error) {
      const apiError = error instanceof InspectionProfilesApiError ? error : null;
      setFieldErrors(apiError?.fieldErrors ?? {});
      if (apiError?.currentRevision !== undefined) {
        setConflictRevision(apiError.currentRevision);
        setStatus("inspection_profile_revision_conflict");
        await reload(true);
      } else {
        setStatus(apiError?.code ?? "inspection_profiles_failed");
      }
      return false;
    }
  }, [commitSnapshot, reload]);

  const save = useCallback(async (targetState: "suggested" | "confirmed") => {
    const profile = preparedDraft(targetState);
    if (!profile || !catalog || !beginAction()) return false;
    try {
      const result = await runValidation(profile);
      if (!result?.valid) return false;
      return await mutate(
        () => updateInspectionProfile({
          schemaVersion: 1,
          action: "save",
          expectedRevision: catalog.store.revision,
          targetState,
          profile,
        }),
        targetState === "confirmed" ? "profile_confirmed" : "draft_saved",
      );
    } finally {
      endAction();
    }
  }, [beginAction, catalog, endAction, mutate, preparedDraft, runValidation]);

  const disable = useCallback(async () => {
    const item = catalog?.items.find((candidate) => candidate.structure.noteTypeId === selectedIdRef.current) ?? null;
    if (!catalog || !item || !beginAction()) return false;
    try {
      return await mutate(() => updateInspectionProfile({
        schemaVersion: 1,
        action: "disable",
        expectedRevision: catalog.store.revision,
        noteTypeId: item.structure.noteTypeId,
      }), "profile_disabled");
    } finally {
      endAction();
    }
  }, [beginAction, catalog, endAction, mutate]);

  const remove = useCallback(async () => {
    const item = catalog?.items.find((candidate) => candidate.structure.noteTypeId === selectedIdRef.current) ?? null;
    if (!catalog || !item || !beginAction()) return false;
    try {
      const removed = await mutate(() => updateInspectionProfile({
        schemaVersion: 1,
        action: "delete",
        expectedRevision: catalog.store.revision,
        noteTypeId: item.structure.noteTypeId,
      }), "profile_deleted");
      if (removed) materializeItem({ ...item, storedProfile: null, effectiveState: "not_configured", authoritative: false });
      return removed;
    } finally {
      endAction();
    }
  }, [beginAction, catalog, endAction, materializeItem, mutate]);

  const resetToServer = useCallback(() => {
    const item = catalog?.items.find((candidate) => candidate.structure.noteTypeId === selectedIdRef.current) ?? null;
    materializeItem(item);
    clearEditorFeedback();
    setConflictRevision(null);
  }, [catalog?.items, clearEditorFeedback, materializeItem]);

  return {
    catalog,
    items,
    loadState,
    loadError,
    selectedNoteTypeId,
    selected,
    draft: snapshot.profile,
    draftOrigin: snapshot.origin,
    generatedDraft: snapshot.origin === "generated",
    hasUserEdits: snapshot.userEdited,
    dirty,
    validation,
    fieldErrors,
    busy,
    status,
    conflictRevision,
    reload,
    select,
    setDraftFromUser,
    setImportedDraft,
    replaceWithSuggestion,
    startEmpty,
    validate,
    save,
    disable,
    remove,
    resetToServer,
    clearStatus: () => setStatus(null),
  };
}

export function createDraft(item: InspectionProfileSummary, fromSuggestion: boolean): InspectionProfile {
  const now = new Date().toISOString();
  return {
    profileId: `note-type-${item.structure.noteTypeId}`,
    noteTypeId: item.structure.noteTypeId,
    noteTypeName: item.structure.name,
    storedState: "suggested",
    displayName: item.structure.name,
    expectedFingerprint: { ...item.structure.fingerprint },
    appliesTo: { templateOrdinals: [] },
    fieldMappings: fromSuggestion
      ? item.suggestion.fieldMappings.map(({ role, fields }) => ({ role, fields: fields.map((field) => ({ ...field })) }))
      : [],
    checks: fromSuggestion ? item.suggestion.checks.map(cloneCheck) : [],
    confirmedAt: null,
    updatedAt: now,
  };
}

export function validateClientDraft(profile: InspectionProfile): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!profile.displayName.trim()) errors["profile.displayName"] = "required";
  const roles = profile.fieldMappings.map((mapping) => mapping.role);
  if (new Set(roles).size !== roles.length) errors["profile.fieldMappings"] = "duplicate_roles";
  const fieldClaims = profile.fieldMappings.flatMap((mapping) => mapping.fields.map((field) => `${field.ordinal}:${field.name}`));
  if (new Set(fieldClaims).size !== fieldClaims.length) errors["profile.fieldMappings"] = "duplicate_fields";
  profile.fieldMappings.forEach((mapping, index) => {
    if (!/^[a-z][a-z0-9_]{0,39}$/.test(mapping.role)) errors[`profile.fieldMappings.${index}.role`] = "invalid_role";
    if (!mapping.fields.length) errors[`profile.fieldMappings.${index}.fields`] = "select_field";
  });
  const checkIds = profile.checks.map((check) => check.checkId);
  if (new Set(checkIds).size !== checkIds.length) errors["profile.checks"] = "duplicate_check_ids";
  profile.checks.forEach((check, index) => {
    if (!check.roles.length || check.roles.some((role) => !roles.includes(role))) {
      errors[`profile.checks.${index}.roles`] = "select_role";
    }
    if (check.kind === "min_text_length" && (!Number.isInteger(check.minLength) || check.minLength < 1 || check.minLength > 10_000)) {
      errors[`profile.checks.${index}.minLength`] = "invalid_min_length";
    }
  });
  return errors;
}

function stableJson(value: unknown): string { return JSON.stringify(value); }
function cloneCheck<T extends InspectionProfile["checks"][number]>(check: T): T {
  return { ...check, roles: [...check.roles] };
}
function cloneProfile(value: InspectionProfile | null): InspectionProfile | null {
  return value ? JSON.parse(JSON.stringify(value)) as InspectionProfile : null;
}
function cloneSnapshot(value: DraftSnapshot): DraftSnapshot {
  return {
    profile: cloneProfile(value.profile),
    baseline: cloneProfile(value.baseline),
    origin: value.origin,
    userEdited: value.userEdited,
  };
}
