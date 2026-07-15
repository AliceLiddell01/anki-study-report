export type TelemetryPurpose = "reliabilityDiagnostics" | "featureUsage";

export type PrivacyState = {
  schemaVersion: number;
  requiresConsent: boolean;
  telemetry: {
    status: "undecided" | "accepted" | "declined";
    consentSchemaVersion: number;
    privacyNoticeVersion: string;
    purposes: Record<TelemetryPurpose, boolean>;
    effectivePurposes: Record<TelemetryPurpose, boolean>;
    decidedAt: string | null;
    deletionPending: boolean;
    requiresConsent: boolean;
  };
};

export type ChangelogItem = {
  id: string;
  text: { ru: string; en: string };
};

export type ChangelogRelease = {
  version: string;
  date: string;
  sections: Array<{
    type: "added" | "changed" | "fixed" | "safety" | "removed";
    items: ChangelogItem[];
  }>;
};

export type ProductNoticesResponse = {
  ok: boolean;
  currentVersion: string;
  notice: {
    schemaVersion: number;
    firstObservedVersion: string | null;
    lastStartedVersion: string | null;
    lastSeenReleaseVersion: string | null;
  };
  privacy: PrivacyState;
  requiresConsent: boolean;
  showWhatsNew: boolean;
  unseenReleaseVersions: string[];
  changelog: {
    schemaVersion: number;
    unreleased: { sections: ChangelogRelease["sections"] };
    releases: ChangelogRelease[];
  };
  error?: string;
};

export type PrivacyResponse = {
  ok: boolean;
  privacy?: PrivacyState;
  allowedDataCategories?: string[];
  neverCollected?: string[];
  privacyNotice?: {
    version: string;
    consentSchemaVersion: number;
    legalReviewStatus: "technical_draft_not_legal_advice";
  };
  message?: string;
  error?: string;
  fieldErrors?: Record<string, string>;
};

function dashboardToken(): string {
  return new URLSearchParams(window.location.search).get("token") || "";
}

async function request(path: string, init?: RequestInit): Promise<unknown> {
  const separator = path.includes("?") ? "&" : "?";
  const response = await fetch(`${path}${separator}token=${encodeURIComponent(dashboardToken())}`, {
    cache: "no-store",
    ...init,
  });
  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  if (!response.ok && (!payload || typeof payload !== "object")) {
    return { ok: false, error: response.status === 403 ? "invalid_dashboard_token" : "request_failed" };
  }
  return payload;
}

export async function fetchProductNotices(): Promise<ProductNoticesResponse> {
  try {
    const result = await request("/api/product-notices") as ProductNoticesResponse;
    if (result?.ok) return result;
  } catch {
    // The offline bundled history remains usable when runtime state is unavailable.
  }
  return productNoticesFallback();
}

export async function markCurrentReleaseSeen(): Promise<ProductNoticesResponse> {
  return request("/api/product-notices/seen", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  }) as Promise<ProductNoticesResponse>;
}

export async function fetchPrivacy(): Promise<PrivacyResponse> {
  return request("/api/privacy") as Promise<PrivacyResponse>;
}

export async function savePrivacyChoices(purposes: Record<TelemetryPurpose, boolean>): Promise<PrivacyResponse> {
  return request("/api/privacy", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ purposes }),
  }) as Promise<PrivacyResponse>;
}

function productNoticesFallback(): ProductNoticesResponse {
  const currentVersion = bundledChangelog.releases[0]?.version ?? "0.0.0";
  const disabledPurposes = { reliabilityDiagnostics: false, featureUsage: false };
  return {
    ok: true,
    currentVersion,
    notice: {
      schemaVersion: 1,
      firstObservedVersion: null,
      lastStartedVersion: null,
      lastSeenReleaseVersion: null,
    },
    privacy: {
      schemaVersion: 1,
      requiresConsent: true,
      telemetry: {
        status: "undecided",
        consentSchemaVersion: 1,
        privacyNoticeVersion: "2026-07-15",
        purposes: disabledPurposes,
        effectivePurposes: disabledPurposes,
        decidedAt: null,
        deletionPending: false,
        requiresConsent: true,
      },
    },
    requiresConsent: false,
    showWhatsNew: true,
    unseenReleaseVersions: bundledChangelog.releases.map((release) => release.version),
    changelog: bundledChangelog as unknown as ProductNoticesResponse["changelog"],
    error: "product_notices_state_unavailable",
  };
}
import { bundledChangelog } from "../data/changelog.generated";
