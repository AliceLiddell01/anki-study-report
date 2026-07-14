import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import i18n from "../i18n";
import { dashboardToken } from "./actionsApi";
import type {
  AnswerMode,
  DashboardScope,
  DeckOption,
  PublicSettings,
  ReportDetailLevel,
  ReportPeriod,
  ReportScope,
  SettingsResponse,
  SettingsSectionName,
} from "../types/settings";

export const defaultPublicSettings: PublicSettings = {
  dashboard: { scope: "all", selectedDeckIds: [], selectedDeckNames: [], includeChildDecks: true },
  report: {
    defaultPeriod: "today",
    customStartDate: "",
    customEndDate: "",
    scope: "all",
    selectedDeckIds: [],
    includeChildDecks: true,
    detailLevel: "normal",
    answerMode: "auto",
  },
  data: {
    trackReviewerSessions: false,
    sessionIdleTimeoutSeconds: 600,
    sessionGapCapSeconds: 120,
    useStudyTimeStats: false,
    useStatsCacheForReport: false,
  },
  server: { autoStart: false, port: 8766, idleTimeoutSeconds: 1800 },
};

export async function loadPublicSettings(signal?: AbortSignal): Promise<SettingsResponse> {
  const response = await fetch(`/api/dashboard/settings?token=${encodeURIComponent(dashboardToken())}`, {
    cache: "no-store",
    signal,
  });
  return parseSettingsResponse(response);
}

export async function savePublicSettings(
  patch: Partial<PublicSettings>,
  signal?: AbortSignal,
): Promise<SettingsResponse> {
  const response = await fetch(`/api/dashboard/settings?token=${encodeURIComponent(dashboardToken())}`, {
    method: "POST",
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
    signal,
  });
  return parseSettingsResponse(response);
}

export function normalizePublicSettings(value: unknown): PublicSettings {
  const source = objectValue(value);
  const dashboard = objectValue(source.dashboard);
  const report = objectValue(source.report);
  const data = objectValue(source.data);
  const server = objectValue(source.server);
  return {
    dashboard: {
      scope: enumValue(dashboard.scope, ["all", "selected"], "all") as DashboardScope,
      selectedDeckIds: integerArray(dashboard.selectedDeckIds),
      selectedDeckNames: stringArray(dashboard.selectedDeckNames),
      includeChildDecks: booleanValue(dashboard.includeChildDecks, true),
    },
    report: {
      defaultPeriod: enumValue(
        report.defaultPeriod,
        ["today", "yesterday", "since_last_report", "last_7_days", "last_30_days", "custom", "all_time"],
        "today",
      ) as ReportPeriod,
      customStartDate: stringValue(report.customStartDate),
      customEndDate: stringValue(report.customEndDate),
      scope: enumValue(report.scope, ["all", "current", "selected"], "all") as ReportScope,
      selectedDeckIds: integerArray(report.selectedDeckIds),
      includeChildDecks: booleanValue(report.includeChildDecks, true),
      detailLevel: enumValue(report.detailLevel, ["compact", "normal", "full"], "normal") as ReportDetailLevel,
      answerMode: enumValue(report.answerMode, ["auto", "standard", "pass_fail"], "auto") as AnswerMode,
    },
    data: {
      trackReviewerSessions: booleanValue(data.trackReviewerSessions, false),
      sessionIdleTimeoutSeconds: integerValue(data.sessionIdleTimeoutSeconds, 600),
      sessionGapCapSeconds: integerValue(data.sessionGapCapSeconds, 120),
      useStudyTimeStats: booleanValue(data.useStudyTimeStats, false),
      useStatsCacheForReport: booleanValue(data.useStatsCacheForReport, false),
    },
    server: {
      autoStart: booleanValue(server.autoStart, false),
      port: integerValue(server.port, 8766),
      idleTimeoutSeconds: integerValue(server.idleTimeoutSeconds, 1800),
    },
  };
}

export function normalizeDeckOptions(value: unknown): DeckOption[] {
  if (!Array.isArray(value)) return [];
  const seen = new Set<number>();
  return value.flatMap((entry) => {
    const option = objectValue(entry);
    const id = integerValue(option.id, 0);
    const name = stringValue(option.name).trim();
    if (id <= 0 || !name || seen.has(id)) return [];
    seen.add(id);
    return [{ id, name }];
  });
}

export function settingsSectionsAreDirty(
  saved: PublicSettings,
  draft: PublicSettings,
  sections: SettingsSectionName[],
): boolean {
  return sections.some((section) => JSON.stringify(saved[section]) !== JSON.stringify(draft[section]));
}

export function settingsPatch(
  draft: PublicSettings,
  sections: SettingsSectionName[],
): Partial<PublicSettings> {
  return Object.fromEntries(sections.map((section) => [section, draft[section]])) as Partial<PublicSettings>;
}

export function usePublicSettingsForm(
  sections: SettingsSectionName[],
  onSaved?: (response: SettingsResponse) => void,
) {
  const { t } = useTranslation("pages");
  const sectionKey = sections.join(",");
  const [saved, setSaved] = useState<PublicSettings>(defaultPublicSettings);
  const [draft, setDraft] = useState<PublicSettings>(defaultPublicSettings);
  const [deckOptions, setDeckOptions] = useState<DeckOption[]>([]);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">("loading");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [restartRequired, setRestartRequired] = useState(false);

  const reload = useCallback(() => {
    const controller = new AbortController();
    setLoadState("loading");
    loadPublicSettings(controller.signal)
      .then((response) => {
        setSaved(response.settings);
        setDraft(response.settings);
        setDeckOptions(response.deckOptions);
        setFieldErrors({});
        setMessage("");
        setLoadState("ready");
      })
      .catch((error: Error) => {
        if (error.name !== "AbortError") {
          setMessage(error.message);
          setLoadState("error");
        }
      });
    return () => controller.abort();
  }, []);

  useEffect(() => reload(), [reload]);

  const dirty = useMemo(
    () => settingsSectionsAreDirty(saved, draft, sections),
    // sectionKey is the stable semantic dependency; callers pass inline arrays.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [draft, saved, sectionKey],
  );

  useEffect(() => {
    if (!dirty) return;
    const beforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    const interceptRoute = (event: MouseEvent) => {
      const anchor = (event.target as Element | null)?.closest?.('a[href^="#/"]') as HTMLAnchorElement | null;
      if (anchor && !window.confirm(t("settingsCommon.leaveConfirm"))) {
        event.preventDefault();
      }
    };
    window.addEventListener("beforeunload", beforeUnload);
    document.addEventListener("click", interceptRoute, true);
    return () => {
      window.removeEventListener("beforeunload", beforeUnload);
      document.removeEventListener("click", interceptRoute, true);
    };
  }, [dirty, t]);

  const save = async () => {
    setSaving(true);
    setMessage("");
    setFieldErrors({});
    const patch = settingsPatch(draft, sections);
    try {
      const response = await savePublicSettings(patch);
      setSaved(response.settings);
      setDraft(response.settings);
      setDeckOptions(response.deckOptions);
      setRestartRequired(Boolean(response.restartRequired));
      setMessage(response.reportRefreshError ? t("settingsCommon.savedRefreshFailed") : response.message || t("settingsCommon.savedSuccess"));
      onSaved?.(response);
    } catch (error) {
      const settingsError = error as SettingsApiError;
      setFieldErrors(settingsError.fieldErrors || {});
      setMessage(settingsError.message || t("settingsCommon.saveFailed"));
    } finally {
      setSaving(false);
    }
  };

  const cancel = () => {
    setDraft(saved);
    setFieldErrors({});
    setMessage(t("settingsCommon.cancelled"));
  };

  return {
    saved,
    draft,
    setDraft,
    deckOptions,
    loadState,
    saving,
    dirty,
    message,
    fieldErrors,
    restartRequired,
    save,
    cancel,
    reload,
  };
}

class SettingsApiError extends Error {
  fieldErrors?: Record<string, string>;
}

async function parseSettingsResponse(response: Response): Promise<SettingsResponse> {
  const data = (await response.json().catch(() => ({}))) as Record<string, unknown>;
  if (!response.ok || data.ok === false) {
    const error = new SettingsApiError(
      response.status === 403
        ? i18n.t("settingsCommon.invalidToken", { ns: "pages" })
        : stringValue(data.message) || i18n.t("settingsCommon.saveFailed", { ns: "pages" }),
    );
    const rawErrors = objectValue(data.fieldErrors);
    error.fieldErrors = Object.fromEntries(
      Object.entries(rawErrors).filter((entry): entry is [string, string] => typeof entry[1] === "string"),
    );
    throw error;
  }
  return {
    ...(data as Omit<SettingsResponse, "settings" | "deckOptions">),
    ok: true,
    settings: normalizePublicSettings(data.settings),
    deckOptions: normalizeDeckOptions(data.deckOptions),
  };
}

function objectValue(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function enumValue(value: unknown, allowed: string[], fallback: string): string {
  return typeof value === "string" && allowed.includes(value) ? value : fallback;
}

function integerArray(value: unknown): number[] {
  if (!Array.isArray(value)) return [];
  return [...new Set(value.filter((item): item is number => Number.isInteger(item) && item > 0))];
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string" && item.trim().length > 0) : [];
}

function integerValue(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isInteger(value) ? value : fallback;
}

function booleanValue(value: unknown, fallback: boolean): boolean {
  return typeof value === "boolean" ? value : fallback;
}

function stringValue(value: unknown): string {
  return typeof value === "string" ? value : "";
}
