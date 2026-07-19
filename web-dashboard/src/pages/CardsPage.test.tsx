// @vitest-environment jsdom

import { act } from "react";
import { createRoot } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../i18n";
import type { CardsTriageWorkspace } from "../hooks/useCardsTriageWorkspace";
import type { SearchInspectResponse } from "../types/search";
import type { TriageItem, TriageQueryResponse, TriageReason } from "../types/triage";
import CardsPage from "./CardsPage";

const workspaceMock = vi.fn<() => CardsTriageWorkspace>();
vi.mock("../hooks/useCardsTriageWorkspace", () => ({ useCardsTriageWorkspace: () => workspaceMock() }));

const learningReason: TriageReason = {
  reasonId: "learning:1", code: "learning.repeated_again", family: "learning", scope: "card",
  priority: "high", sources: ["attention"], evidence: [{ kind: "review_counts", againCount: 4, periodStartMs: 1, periodEndMs: 2 }], detectedAtMs: 2,
};
const contentReason: TriageReason = {
  reasonId: "content:1", code: "content.audio_missing", family: "content", scope: "note",
  priority: "medium", sources: ["profile_checks"], evidence: [{ kind: "profile_check", profileId: "note-type-7", checkId: "audio", checkKind: "contains_audio", roles: ["audio"], fields: [{ ordinal: 2, name: "Audio" }], expectedCondition: "contains_audio", actualTextLength: null, expectedTextLength: null, marker: "audio", markerPresent: false, profileRevision: 2, fingerprint: "a".repeat(64), affectedSiblingCount: 2, templateOrdinals: [0] }], detectedAtMs: 2,
};
const items: TriageItem[] = [
  { itemId: "card:1001", availability: "available", cardId: "1001", noteId: "2001", deck: { deckId: "3", name: "Japanese::N5" }, noteType: { noteTypeId: "7", name: "Japanese Vocabulary" }, template: { ordinal: 0, name: "Recognition" }, displayText: "【に】（する）", displaySource: "reviewer_front", displayStatus: "available", displayTruncated: false, priority: "high", primaryReasonCode: learningReason.code, reasons: [learningReason, contentReason], sources: ["attention", "profile_checks"], cardState: { state: "review", suspended: false, buried: false, flag: 1 }, inspect: { mode: "cards", cardId: "1001" } },
  { itemId: "card:1002", availability: "available", cardId: "1002", noteId: "2002", deck: { deckId: "4", name: "Programming" }, noteType: { noteTypeId: "8", name: "Basic" }, template: { ordinal: 0, name: "Card 1" }, displayText: "", displaySource: "reviewer_front", displayStatus: "media_only", displayTruncated: false, priority: "medium", primaryReasonCode: contentReason.code, reasons: [contentReason], sources: ["profile_checks"], cardState: { state: "suspended", suspended: true, buried: false, flag: 0 }, inspect: { mode: "cards", cardId: "1002" } },
];
const response: TriageQueryResponse = {
  schemaVersion: 4, dataset: "automatic", status: "partial", generatedAtMs: 10, totalCount: 2, returnedCount: 2, limit: 100, truncated: false,
  sourceStatus: { learningCandidates: source("available", 1), contentCandidates: { ...source("available", 1), scannedNoteCount: 1, nextCursor: null }, signals: source("unavailable", 0), searchResolver: source("empty", 0), profileChecks: source("available", 1) },
  contentChecks: { status: "profiles_need_review", confirmedProfileCount: 1, needsReviewProfileCount: 2, disabledProfileCount: 0, suggestedProfileCount: 0, scannedNoteCount: 1, evaluatedNoteCount: 1, failedCheckCount: 1, skippedCount: 1, truncated: false, nextCursor: null, errorCode: null },
  items,
};
const inspectResponse: SearchInspectResponse<"cards"> = { schemaVersion: 2, mode: "cards", requestId: "cards-1", details: { cardId: "1001", noteId: "2001", deckId: "3", deckName: "Japanese::N5", noteTypeId: "7", noteTypeName: "Japanese Vocabulary", templateOrdinal: 0, templateName: "Recognition", displayText: "【に】（する）", displaySource: "reviewer_front", displayStatus: "available", displayTruncated: false, state: "review", due: 1, interval: 10, repetitions: 5, lapses: 1, flag: 1, tagSummary: ["n5"], deck: { deckId: "3", deckName: "Japanese::N5" }, noteType: { noteTypeId: "7", noteTypeName: "Japanese Vocabulary" }, template: { ordinal: 0, name: "Recognition" }, queue: 2, tags: ["n5"], renderedPreview: { renderStatus: "sanitized", frontHtml: "<b>覚える</b>", backHtml: "<b>remember</b>", frontPlainText: "覚える", css: "b{font-weight:700}", mediaRefs: [], cardOrd: 0, cardId: 1001, renderSource: "anki_native" } } };

beforeEach(async () => { (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true; await i18n.changeLanguage("ru"); workspaceMock.mockReturnValue(readyWorkspace()); vi.stubGlobal("window", window); });
afterEach(() => { vi.restoreAllMocks(); document.body.innerHTML = ""; });

describe("Cards v2 queue and Inspector", () => {
  it("uses the same canonical identity in queue and Inspector without redesigning the workspace", () => {
    const html = renderToStaticMarkup(<CardsPage report={null} loadState="ready" />);
    expect(html).toContain('data-testid="cards-triage-table"');
    expect(html.match(/data-testid="cards-triage-row"/g)).toHaveLength(2);
    expect(html).toContain('data-testid="cards-inspector"');
    expect(html.match(/【に】（する）/g)?.length).toBeGreaterThanOrEqual(2);
    expect(html).toContain("Карточка только с медиа");
    expect(html.match(/data-shadow-preview="true"/g)).toHaveLength(1);
    expect(html).toContain("+1 причина");
    expect(html).not.toContain("primaryText");
    expect(html).not.toContain('type="checkbox"');
  });

  it("localizes unavailable fallback in English", async () => {
    await i18n.changeLanguage("en");
    const unavailable: TriageItem = { ...items[1]!, displaySource: "none", displayStatus: "unavailable" };
    workspaceMock.mockReturnValue({ ...readyWorkspace(), activeId: "card:1002", activeItem: unavailable });
    const html = renderToStaticMarkup(<CardsPage report={null} loadState="ready" />);
    expect(html).toContain("Card text unavailable");
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
    const expand = Array.from(document.querySelectorAll("button")).find((button) => button.textContent?.includes("Развернуть ответ"));
    expect(expand).toBeTruthy();
    await act(async () => expand!.click());
    const modal = document.querySelector('[data-testid="cards-preview-modal"]');
    expect(modal).toBeTruthy();
    expect(document.getElementById("dashboard-app-shell")!.contains(modal)).toBe(false);
    expect(document.getElementById("dashboard-app-shell")!.inert).toBe(true);
    expect(modal?.textContent).toContain("Развёрнутое превью ответа");
    const modalPreview = modal?.querySelector('[data-preview-side="back"]');
    expect(modalPreview).toBeTruthy();
    expect(modalPreview?.getAttribute("data-preview-mode")).toBe("expanded");
    expect(modalPreview?.innerHTML).toContain("remember");
    expect(modalPreview?.innerHTML).not.toContain("覚える");
    await act(async () => root.unmount());
  });
});

function readyWorkspace(): CardsTriageWorkspace {
  return { queryStatus: "ready", queryError: null, response, activeId: items[0]!.itemId, activeItem: items[0]!, inspectStatus: "ready", inspectError: null, inspectResponse, openPending: false, openResult: null, activate: vi.fn(), clearActive: vi.fn(), refresh: vi.fn(), retryInspect: vi.fn(), openInAnki: vi.fn(async () => undefined) };
}

function source(status: "available" | "empty" | "unavailable", itemCount: number) { return { status, itemCount, skippedCount: 0, truncated: false, errorCode: null }; }

describe("Cards preview side availability", () => {
  it("renders front in Inspector without answer-only content", () => {
    const html = renderToStaticMarkup(<CardsPage report={null} loadState="ready" />);
    expect(html).toContain("Лицевая сторона");
    expect(html).toContain('data-preview-side="front"');
    expect(html).toContain("覚える");
    expect(html).not.toContain("remember");
  });

  it("keeps reasons and actions when front is unavailable", () => {
    const missingFront = { ...inspectResponse, details: { ...inspectResponse.details, renderedPreview: { ...inspectResponse.details.renderedPreview, frontHtml: "", frontPlainText: "" } } };
    workspaceMock.mockReturnValue({ ...readyWorkspace(), inspectResponse: missingFront });
    const html = renderToStaticMarkup(<CardsPage report={null} loadState="ready" />);
    expect(html).toContain("Лицевая сторона недоступна");
    expect(html).toContain("Частые ответы «Снова»");
    expect(html).toContain("Открыть в Anki");
  });

  it("does not present front as answer when back is unavailable", () => {
    const missingBack = { ...inspectResponse, details: { ...inspectResponse.details, renderedPreview: { ...inspectResponse.details.renderedPreview, backHtml: "", backPlainText: "" } } };
    workspaceMock.mockReturnValue({ ...readyWorkspace(), inspectResponse: missingBack });
    const html = renderToStaticMarkup(<CardsPage report={null} loadState="ready" />);
    expect(html).toContain("Превью ответа недоступно");
    expect(html).toContain("覚える");
    expect(html).not.toContain('data-preview-side="back"');
    expect(html).toContain('disabled=""');
  });
});
