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

export interface InspectionProfilesWorkspace {
  catalog: InspectionProfilesQueryResponse | null;
  items: InspectionProfileSummary[];
  loadState: LoadState;
  loadError: string | null;
  selectedNoteTypeId: string | null;
  selected: InspectionProfileSummary | null;
  draft: InspectionProfile | null;
  dirty: boolean;
  validation: InspectionValidateResponse | null;
  fieldErrors: Record<string, string>;
  busy: boolean;
  status: string | null;
  conflictRevision: number | null;
  reload: (preserveDraft?: boolean) => Promise<void>;
  select: (noteTypeId: string | null, discardDirty?: boolean) => boolean;
  setDraft: (draft: InspectionProfile | null) => void;
  useSuggestion: () => void;
  startEmpty: () => void;
  validate: () => Promise<boolean>;
  save: (targetState: "suggested" | "confirmed") => Promise<boolean>;
  disable: () => Promise<boolean>;
  remove: () => Promise<boolean>;
  resetToServer: () => void;
  clearStatus: () => void;
}

export function useInspectionProfilesWorkspace(): InspectionProfilesWorkspace {
  const [catalog, setCatalog] = useState<InspectionProfilesQueryResponse | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedNoteTypeId, setSelectedNoteTypeId] = useState<string | null>(null);
  const selectedIdRef = useRef<string | null>(null);
  const [draft, setDraftState] = useState<InspectionProfile | null>(null);
  const [baseline, setBaseline] = useState<InspectionProfile | null>(null);
  const [validation, setValidation] = useState<InspectionValidateResponse | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [conflictRevision, setConflictRevision] = useState<number | null>(null);
  const querySequence = useRef(0);
  const queryController = useRef<AbortController | null>(null);
  const validateController = useRef<AbortController | null>(null);

  const items = catalog?.items ?? [];
  const selected = items.find((item) => item.structure.noteTypeId === selectedNoteTypeId) ?? null;
  const dirty = useMemo(() => stableJson(draft) !== stableJson(baseline), [baseline, draft]);

  const reload = useCallback(async (preserveDraft = false) => {
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
      const currentSelectedId = selectedIdRef.current;
      if (currentSelectedId && !preserveDraft) {
        const current = response.items.find((item) => item.structure.noteTypeId === currentSelectedId) ?? null;
        const next = cloneProfile(current?.storedProfile ?? null);
        setBaseline(next);
        setDraftState(cloneProfile(next));
        setValidation(null);
        setFieldErrors({});
      }
    } catch (error) {
      if (controller.signal.aborted) return;
      setLoadState("error");
      setLoadError(error instanceof InspectionProfilesApiError ? error.code : "inspection_profiles_failed");
    }
  }, []);

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
    if (dirty && !discardDirty) return false;
    selectedIdRef.current = noteTypeId;
    setSelectedNoteTypeId(noteTypeId);
    const item = catalog?.items.find((candidate) => candidate.structure.noteTypeId === noteTypeId) ?? null;
    const next = cloneProfile(item?.storedProfile ?? null);
    setBaseline(next);
    setDraftState(cloneProfile(next));
    setValidation(null);
    setFieldErrors({});
    setConflictRevision(null);
    setStatus(null);
    return true;
  }, [catalog?.items, dirty]);

  const setDraft = useCallback((next: InspectionProfile | null) => {
    setDraftState(cloneProfile(next));
    setValidation(null);
    setFieldErrors({});
    setStatus(null);
  }, []);

  const makeDraft = useCallback((fromSuggestion: boolean) => {
    if (!selected) return;
    const now = new Date().toISOString();
    setDraft({
      profileId: `note-type-${selected.structure.noteTypeId}`,
      noteTypeId: selected.structure.noteTypeId,
      noteTypeName: selected.structure.name,
      storedState: "suggested",
      displayName: selected.structure.name,
      expectedFingerprint: selected.structure.fingerprint,
      appliesTo: { templateOrdinals: [] },
      fieldMappings: fromSuggestion
        ? selected.suggestion.fieldMappings.map(({ role, fields }) => ({ role, fields: fields.map((field) => ({ ...field })) }))
        : [],
      checks: fromSuggestion ? selected.suggestion.checks.map((check) => ({ ...check, roles: [...check.roles] })) : [],
      confirmedAt: null,
      updatedAt: now,
    });
  }, [selected, setDraft]);

  const preparedDraft = useCallback((targetState: "suggested" | "confirmed") => {
    if (!draft || !selected) return null;
    const now = new Date().toISOString();
    return {
      ...cloneProfile(draft)!,
      noteTypeName: selected.structure.name,
      storedState: targetState,
      expectedFingerprint: selected.structure.fingerprint,
      confirmedAt: targetState === "confirmed" ? now : null,
      updatedAt: now,
    };
  }, [draft, selected]);

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
    setBusy(true);
    setFieldErrors({});
    try {
      const result = await validateInspectionProfile({
        schemaVersion: 2,
        profile,
        preview: { mode: "sample", limit: 10 },
      }, controller.signal);
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
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }, []);

  const validate = useCallback(async () => {
    if (!draft) return false;
    return Boolean(await runValidation(draft));
  }, [draft, runValidation]);

  const mutate = useCallback(async (
    operation: () => ReturnType<typeof updateInspectionProfile>,
    successCode: string,
  ) => {
    if (busy) return false;
    setBusy(true);
    setStatus(null);
    setConflictRevision(null);
    try {
      await operation();
      setStatus(successCode);
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
    } finally {
      setBusy(false);
    }
  }, [busy, reload]);

  const save = useCallback(async (targetState: "suggested" | "confirmed") => {
    const profile = preparedDraft(targetState);
    if (!profile || !catalog) return false;
    const result = await runValidation(profile);
    if (!result?.valid) return false;
    return mutate(
      () => updateInspectionProfile({
        schemaVersion: 1,
        action: "save",
        expectedRevision: catalog.store.revision,
        targetState,
        profile,
      }),
      targetState === "confirmed" ? "profile_confirmed" : "draft_saved",
    );
  }, [catalog, mutate, preparedDraft, runValidation]);

  const disable = useCallback(async () => {
    if (!catalog || !selected) return false;
    return mutate(() => updateInspectionProfile({
      schemaVersion: 1,
      action: "disable",
      expectedRevision: catalog.store.revision,
      noteTypeId: selected.structure.noteTypeId,
    }), "profile_disabled");
  }, [catalog, mutate, selected]);

  const remove = useCallback(async () => {
    if (!catalog || !selected) return false;
    const removed = await mutate(() => updateInspectionProfile({
      schemaVersion: 1,
      action: "delete",
      expectedRevision: catalog.store.revision,
      noteTypeId: selected.structure.noteTypeId,
    }), "profile_deleted");
    if (removed) {
      setBaseline(null);
      setDraftState(null);
      setValidation(null);
    }
    return removed;
  }, [catalog, mutate, selected]);

  const resetToServer = useCallback(() => {
    const next = cloneProfile(selected?.storedProfile ?? null);
    setBaseline(next);
    setDraftState(cloneProfile(next));
    setValidation(null);
    setFieldErrors({});
    setConflictRevision(null);
    setStatus(null);
  }, [selected?.storedProfile]);

  return {
    catalog, items, loadState, loadError, selectedNoteTypeId, selected, draft, dirty,
    validation, fieldErrors, busy, status, conflictRevision, reload, select, setDraft,
    useSuggestion: () => makeDraft(true), startEmpty: () => makeDraft(false), validate,
    save, disable, remove, resetToServer, clearStatus: () => setStatus(null),
  };
}

function validateClientDraft(profile: InspectionProfile): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!profile.displayName.trim()) errors["profile.displayName"] = "required";
  const roles = profile.fieldMappings.map((mapping) => mapping.role);
  if (new Set(roles).size !== roles.length) errors["profile.fieldMappings"] = "duplicate_roles";
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
function cloneProfile(value: InspectionProfile | null): InspectionProfile | null {
  return value ? JSON.parse(JSON.stringify(value)) as InspectionProfile : null;
}
