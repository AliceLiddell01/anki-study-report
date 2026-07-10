import { describe, expect, it } from "vitest";
import {
  defaultPublicSettings,
  normalizeDeckOptions,
  normalizePublicSettings,
  settingsPatch,
  settingsSectionsAreDirty,
} from "./settingsApi";

describe("public settings model", () => {
  it("normalizes incomplete and invalid API values", () => {
    const settings = normalizePublicSettings({
      dashboard: { scope: "selected", selectedDeckIds: [2, 2, -1, "3"], includeChildDecks: false },
      report: { defaultPeriod: "invalid", scope: "current", detailLevel: "full", answerMode: "pass_fail" },
      data: { trackReviewerSessions: true, sessionIdleTimeoutSeconds: 900 },
      server: { port: 9000 },
    });

    expect(settings.dashboard).toEqual({
      scope: "selected",
      selectedDeckIds: [2],
      selectedDeckNames: [],
      includeChildDecks: false,
    });
    expect(settings.report.defaultPeriod).toBe("today");
    expect(settings.report.scope).toBe("current");
    expect(settings.data.sessionGapCapSeconds).toBe(120);
    expect(settings.server).toEqual({ autoStart: false, port: 9000, idleTimeoutSeconds: 1800 });
  });

  it("deduplicates and filters deck catalog entries", () => {
    expect(normalizeDeckOptions([
      { id: 2, name: "B" },
      { id: 2, name: "duplicate" },
      { id: 0, name: "invalid" },
      { id: 3, name: "" },
    ])).toEqual([{ id: 2, name: "B" }]);
  });

  it("tracks dirty state and sends only page-owned sections", () => {
    const saved = structuredClone(defaultPublicSettings);
    const draft = structuredClone(saved);
    expect(settingsSectionsAreDirty(saved, draft, ["data"])).toBe(false);

    draft.data.useStatsCacheForReport = true;
    expect(settingsSectionsAreDirty(saved, draft, ["data"])).toBe(true);
    expect(settingsSectionsAreDirty(saved, draft, ["server"])).toBe(false);
    expect(settingsPatch(draft, ["data"])).toEqual({ data: draft.data });
  });
});
