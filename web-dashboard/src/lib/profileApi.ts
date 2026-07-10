import type { ProfileDeckSort, ProfileModel } from "../types/report";

export interface ProfileApiResponse {
  ok: boolean;
  profile?: ProfileModel;
  message?: string;
  error?: string;
  fieldErrors?: Record<string, string>;
}

export type ProfilePreferencesPatch = {
  customStudyStartedOn?: string | null;
  deckOverviewSort?: ProfileDeckSort;
};

export async function saveProfilePreferences(patch: ProfilePreferencesPatch): Promise<ProfileApiResponse> {
  const token = new URLSearchParams(window.location.search).get("token") || "";
  const response = await fetch(`/api/profile?token=${encodeURIComponent(token)}`, {
    method: "POST",
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  const payload = await readJson(response);
  if (!response.ok && !payload) {
    return { ok: false, error: response.status === 403 ? "invalid_dashboard_token" : "profile_update_failed" };
  }
  return normalizeResponse(payload);
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function normalizeResponse(value: unknown): ProfileApiResponse {
  const source = value && typeof value === "object" ? value as Record<string, unknown> : {};
  return {
    ok: source.ok === true,
    profile: source.profile && typeof source.profile === "object" ? source.profile as ProfileModel : undefined,
    message: typeof source.message === "string" ? source.message : undefined,
    error: typeof source.error === "string" ? source.error : undefined,
    fieldErrors: source.fieldErrors && typeof source.fieldErrors === "object"
      ? Object.fromEntries(Object.entries(source.fieldErrors as Record<string, unknown>).filter((entry): entry is [string, string] => typeof entry[1] === "string"))
      : undefined,
  };
}
