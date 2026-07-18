// @vitest-environment jsdom

import { act } from "react";
import { createRoot } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { CardsTriageWorkspace } from "../hooks/useCardsTriageWorkspace";
import CardsPage from "./CardsPage";

const workspaceMock = vi.fn<() => CardsTriageWorkspace>();
vi.mock("../hooks/useCardsTriageWorkspace", () => ({ useCardsTriageWorkspace: () => workspaceMock() }));

const learningReason = {
  reasonId: "learning:1", code: "learning.repeated_again", family: "learning" as const, scope: "card" as const,
  priority: "high" as const, sources: ["attention" as const], evidence: [{ kind: "review_counts" as const, againCount: 4, periodStartMs: 1, periodEndMs: 2 }], detectedAtMs: 2,
};
const contentReason = {
  reasonId: "content:1", code: "content.audio_missing", family: "content" as const, scope: "note" as const,
  priority: "medium" as const, sources: ["profile_checks" as const], evidence: [{ kind: "profile_check" as const, profileId: "note-type-7", checkId: "audio", checkKind: "contains_audio" as const, roles: ["audio"], fields: [{ ordinal: 2, name: "Audio" }], expectedCondition: "contains_audio", actualTextLength: null, expectedTextLength: null, marker: "audio" as const, markerPresent: false as const, profileRevision: 2, fingerprint: "a".repeat(64), affectedSiblingCount: 2, templateOrdinals: [0] }], detectedAtMs: 2,
};
const items = [
  { itemId: "card:1001", availability: "available" as const, cardId: "1001", noteId: "2001", deck: { deckId: "3", name: "Japanese::N5" }, noteType: { noteTypeId: "7", name: "Japanese Vocabulary" }, template: { ordinal: 0, name: "Recognition" }, primaryText: "覚える", priority: "high" as const, primaryReasonCode: learningReason.code, reasons: [learningReason, contentReason], sources: ["attention" as const, "profile_checks" as const], cardState: { state: "review" as const, suspended: false, buried: false, flag: 1 }, inspect: { mode: "cards" as const, cardId: "1001" } },
  { itemId: "card:1002", availability: "available" as const, cardId: "1002", noteId: "2002", deck: { deckId: "4", name: "Programming" }, noteType: { noteTypeId: "8", name: "Basic" }, template: { ordinal: 0, name: "Card 1" }, primaryText: "Promise microtask ordering", priority: "medium" as const, primaryReasonCode: contentReason.code, reasons: [contentReason], sources: ["profile_checks" as const], cardState: { state: "suspended" as const, suspended: true, buried: false, flag: 0 }, inspect: { mode: "cards" as const, cardId: "1002" } },
];
const response = {
  schemaVersion: 2 as const, dataset: "automatic" as const, status: "partial" as const, generatedAtMs: 10, totalCount: 2, returnedCount: 2, limit: 100, truncated: false,
  sourceStatus: { attention: source("available", 1), signals: source("unavailable", 0), searchResolver: source("empty", 0), profileChecks: source("available", 1) },
  contentChecks: { status: "profiles_need_review" as const, confirmedProfileCount: 1, needsReviewProfileCount: 2, disabledProfileCount: 0, suggestedProfileCount: 0, evaluatedNoteCount: 1, failedCheckCount: 1, skippedCount: 1, truncated: false, errorCode: null },
  items,
};
const inspectResponse = { schemaVersion: 1 as const, mode: "cards" as const, requestId: "cards-1", details: { cardId: "1001", noteId: "2001", deckId: "3", deckName: "Japanese::N5", noteTypeId: "7", noteTypeName: "Japanese Vocabulary", templateOrdinal: 0, templateName: "Recognition", primaryText: "覚える", state: "review" as const, due: 1, interval: 10, repetitions: 5, lapses: 1, flag: 1, tagSummary: ["n5"], deck: { deckId: "3", deckName: "Japanese::N5" }, noteType: { noteTypeId: "7", noteTypeName: "Japanese Vocabulary" }, template: { ordinal: 0, name: "Recognition" }, queue: 2, tags: ["n5"], renderedPreview: { renderStatus: "sanitized" as const, frontHtml: "<b>覚える</b>", backHtml: "<b>remember</b>", frontPlainText: "覚える", css: "b{font-weight:700}", mediaRefs: [], cardOrd: 0, cardId: 1001, renderSource: "anki_native" } } };

beforeEach(() => { (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true; workspaceMock.mockReturnValue(readyWorkspace()); vi.stubGlobal("window", window); });
afterEach(() => { vi.restoreAllMocks(); document.body.innerHTML = ""; });

describe("Cards v2 queue and Inspector", () => {
  it("renders one semantic queue and active-only Inspector preview without legacy modes", () => {
    const html = renderToStaticMarkup(<CardsPage report={null} loadState="ready" />);
    expect(html).toContain('data-testid="cards-triage-table"');
    expect(html.match(/data-testid="cards-triage-row"/g)).toHaveLength(2);
    expect(html).toContain('data-testid="cards-inspector"');
    expect(html.match(/data-shadow-preview="true"/g)).toHaveLength(1);
    expect(html).toContain("+1 причина");
    expect(html).toContain("2 профиля проверки требуют внимания");
    expect(html).toContain("Некоторые источники");
    expect(html).not.toContain("riskScore");
    expect(html).not.toContain("Плитки");
    expect(html).not.toContain("Превью Anki");
    expect(html).not.toContain('type="checkbox"');
  });

  it("keeps preview failures separate from reasons and exact-ID actions", () => {
    workspaceMock.mockReturnValue({ ...readyWorkspace(), inspectStatus: "error", inspectResponse: null, inspectError: Object.assign(new Error("gone"), { code: "search_entity_not_found", status: 404, name: "SearchApiError" }) as never });
    const html = renderToStaticMarkup(<CardsPage report={null} loadState="ready" />);
    expect(html).toContain("Карточка недоступна или удалена");
    expect(html).toContain("Частые ответы «Снова»");
    expect(html).toContain("Нет аудио");
    expect(html).toContain("Открыть в Anki");
  });

  it("portals expanded preview outside the inert application shell", async () => {
    document.body.innerHTML = '<div id="dashboard-app-shell"><div id="root"></div></div>';
    const rootNode = document.getElementById("root")!;
    const root = createRoot(rootNode);
    await act(async () => root.render(<CardsPage report={null} loadState="ready" />));
    const expand = Array.from(document.querySelectorAll("button")).find((button) => button.textContent?.includes("Развернуть превью"));
    expect(expand).toBeTruthy();
    await act(async () => expand!.click());
    const modal = document.querySelector('[data-testid="cards-preview-modal"]');
    expect(modal).toBeTruthy();
    expect(document.getElementById("dashboard-app-shell")!.contains(modal)).toBe(false);
    expect(document.getElementById("dashboard-app-shell")!.inert).toBe(true);
    await act(async () => root.unmount());
  });
});

function readyWorkspace(): CardsTriageWorkspace {
  return { queryStatus: "ready", queryError: null, response, activeId: items[0]!.itemId, activeItem: items[0]!, inspectStatus: "ready", inspectError: null, inspectResponse, openPending: false, openResult: null, activate: vi.fn(), clearActive: vi.fn(), refresh: vi.fn(), retryInspect: vi.fn(), openInAnki: vi.fn(async () => undefined) };
}

function source(status: "available" | "empty" | "unavailable", itemCount: number) { return { status, itemCount, skippedCount: 0, truncated: false, errorCode: null }; }
