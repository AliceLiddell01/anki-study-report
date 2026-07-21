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
let wideMode = true;
vi.mock("../hooks/useCardsTriageWorkspace", () => ({ useCardsTriageWorkspace: () => workspaceMock() }));
vi.mock("../hooks/useMediaQuery", () => ({ useMediaQuery: () => wideMode }));

const learningReason: TriageReason = {
  reasonId: "learning:1", code: "learning.repeated_again", family: "learning", scope: "card",
  priority: "high", sources: ["attention"], evidence: [{ kind: "review_counts", againCount: 4, periodStartMs: 1, periodEndMs: 7 * 86400000 + 1 }], detectedAtMs: 2,
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
  sourceStatus: { learningCandidates: source("available", 1), contentCandidates: { ...source("available", 1), scannedNoteCount: 500, truncated: true, nextCursor: "500" }, signals: source("unavailable", 0), searchResolver: source("empty", 0), profileChecks: source("available", 1) },
  contentChecks: { status: "profiles_need_review", confirmedProfileCount: 1, needsReviewProfileCount: 2, disabledProfileCount: 0, suggestedProfileCount: 0, scannedNoteCount: 500, evaluatedNoteCount: 1, failedCheckCount: 1, skippedCount: 1, truncated: true, nextCursor: "500", errorCode: null },
  items,
};
const inspectResponse: SearchInspectResponse<"cards"> = { schemaVersion: 2, mode: "cards", requestId: "cards-1", details: { cardId: "1001", noteId: "2001", deckId: "3", deckName: "Japanese::N5", noteTypeId: "7", noteTypeName: "Japanese Vocabulary", templateOrdinal: 0, templateName: "Recognition", displayText: "【に】（する）", displaySource: "reviewer_front", displayStatus: "available", displayTruncated: false, state: "review", due: 1, interval: 10, repetitions: 5, lapses: 1, flag: 1, tagSummary: ["n5"], deck: { deckId: "3", deckName: "Japanese::N5" }, noteType: { noteTypeId: "7", noteTypeName: "Japanese Vocabulary" }, template: { ordinal: 0, name: "Recognition" }, queue: 2, tags: ["n5"], renderedPreview: { renderStatus: "sanitized", frontHtml: "<b>覚える</b>", backHtml: "<b>remember</b>", frontPlainText: "覚える", backPlainText: "remember", css: "b{font-weight:700}", mediaRefs: [], cardOrd: 0, cardId: 1001, renderSource: "anki_native" } } };

beforeEach(async () => {
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  await i18n.changeLanguage("ru");
  wideMode = true;
  workspaceMock.mockReturnValue(readyWorkspace());
});
afterEach(() => { vi.restoreAllMocks(); document.body.innerHTML = ""; });

describe("Cards attention inbox", () => {
  it("removes the spreadsheet table and renders a semantic inbox with one detail surface", () => {
    const html = renderToStaticMarkup(<CardsPage report={null} loadState="ready" />);
    expect(html).toContain('data-testid="cards-inbox"');
    expect(html.match(/data-testid="cards-inbox-item"/g)).toHaveLength(2);
    expect(html).not.toContain("<table");
    expect(html).not.toContain('role="grid"');
    expect(html).not.toContain('role="listbox"');
    expect(html).toContain('data-testid="cards-inspector"');
    expect(html).not.toContain('data-testid="cards-detail-drawer"');
    expect(html.match(/data-shadow-preview="true"/g)).toHaveLength(1);
    expect(html).toContain("【に】（する）");
    expect(html).toContain("+1 причина");
    expect(html).toContain("Период обучения");
    expect(html).toContain("Проверить следующие заметки");
  });

  it("keeps filter clearing separate from the learning period", async () => {
    document.body.innerHTML = '<div id="root"></div>';
    const root = createRoot(document.getElementById("root")!);
    const workspace = readyWorkspace();
    workspaceMock.mockReturnValue(workspace);
    await act(async () => root.render(<CardsPage report={null} loadState="ready" />));
    const selects = Array.from(document.querySelectorAll("select"));
    const period = selects.find((select) => select.parentElement?.textContent?.includes("Период обучения"))!;
    await act(async () => { period.value = "30"; period.dispatchEvent(new Event("change", { bubbles: true })); });
    expect(workspace.setLearningPeriodDays).toHaveBeenCalledWith(30);
    const prioritySelect = selects.find((select) => select.parentElement?.textContent?.includes("Приоритет"))!;
    await act(async () => { prioritySelect.value = "high"; prioritySelect.dispatchEvent(new Event("change", { bubbles: true })); });
    const clear = Array.from(document.querySelectorAll("button")).find((button) => button.textContent?.includes("Очистить фильтры"));
    expect(clear).toBeTruthy();
    await act(async () => clear!.click());
    expect(workspace.setLearningPeriodDays).toHaveBeenCalledTimes(1);
    await act(async () => root.unmount());
  });

  it("uses a full-width queue and opens a non-modal drawer on activation", async () => {
    wideMode = false;
    document.body.innerHTML = '<div id="dashboard-app-shell"><div id="root"></div></div>';
    const root = createRoot(document.getElementById("root")!);
    const workspace = readyWorkspace();
    workspaceMock.mockReturnValue(workspace);
    await act(async () => root.render(<CardsPage report={null} loadState="ready" />));
    expect(document.querySelector('[data-testid="cards-detail-drawer"]')).toBeNull();
    const item = document.querySelector('button[data-card-id="1001"]') as HTMLButtonElement;
    item.focus();
    await act(async () => item.click());
    const drawer = document.querySelector('[data-testid="cards-detail-drawer"]')!;
    expect(drawer).toBeTruthy();
    expect(drawer.getAttribute("role")).toBe("region");
    expect(drawer.getAttribute("aria-modal")).toBeNull();
    expect(document.getElementById("dashboard-app-shell")!.hasAttribute("inert")).toBe(false);
    expect(workspace.activate).toHaveBeenCalledWith(items[0]);
    const close = drawer.querySelector('button[aria-label*="Закрыть подробности"]') as HTMLButtonElement;
    await act(async () => close.click());
    await act(async () => { await Promise.resolve(); });
    expect(document.querySelector('[data-testid="cards-detail-drawer"]')).toBeNull();
    expect(document.activeElement).toBe(item);
    await act(async () => root.unmount());
  });

  it("keeps the expanded answer as the existing true modal", async () => {
    document.body.innerHTML = '<div id="dashboard-app-shell"><div id="root"></div></div>';
    const root = createRoot(document.getElementById("root")!);
    await act(async () => root.render(<CardsPage report={null} loadState="ready" />));
    const expand = Array.from(document.querySelectorAll("button")).find((button) => button.textContent?.includes("Развернуть ответ"));
    expect(expand).toBeTruthy();
    await act(async () => expand!.click());
    const modal = document.querySelector('[data-testid="cards-preview-modal"]')!;
    expect(modal.getAttribute("role")).toBe("dialog");
    expect(modal.getAttribute("aria-modal")).toBe("true");
    expect(document.getElementById("dashboard-app-shell")!.inert).toBe(true);
    expect(modal.querySelector('[data-preview-side="back"]')?.innerHTML).toContain("remember");
    expect(modal.querySelector('[data-preview-side="back"]')?.innerHTML).not.toContain("覚える");
    await act(async () => root.unmount());
  });

  it("localizes unavailable compact identity in English", async () => {
    await i18n.changeLanguage("en");
    const unavailable: TriageItem = { ...items[1]!, displaySource: "none", displayStatus: "unavailable" };
    workspaceMock.mockReturnValue({ ...readyWorkspace(), activeId: "card:1002", activeItem: unavailable });
    const html = renderToStaticMarkup(<CardsPage report={null} loadState="ready" />);
    expect(html).toContain("Card text unavailable");
  });

  it("presents the reason-level resolution lifecycle without bulk or manual resolve controls", () => {
    const partial = {
      itemId: items[0]!.itemId,
      phase: "partially_resolved" as const,
      actionResult: { schemaVersion: 1 as const, entityType: "cards" as const, action: "suspend" as const, requestedCount: 1, affectedCount: 0, unchangedCount: 1, undoable: false, resultCode: "action.no_changes" as const, args: {} },
      actionError: null,
      recheckError: null,
      reconciliation: { removed: [learningReason], remaining: [contentReason], added: [] },
    };
    workspaceMock.mockReturnValue({ ...readyWorkspace(), resolution: partial, lastOutcome: partial });
    const html = renderToStaticMarkup(<CardsPage report={null} loadState="ready" />);
    expect(html).toContain("Устранено частично");
    expect(html).toContain("Anki не внёс изменений");
    expect(html).toContain("Частые ответы «Снова»");
    expect(html).toContain("Нет аудио");
    expect(html).toContain("Перепроверить карточку");
    expect(html).toContain("Успешное действие ещё не означает");
    expect(html).not.toContain('type="checkbox"');
    expect(html).not.toContain(">Готово<");
    expect(html).not.toContain(">Архивировать<");
  });

  it("announces a global pending mutation and disables conflicting inspector controls", () => {
    const awaiting = {
      itemId: items[0]!.itemId,
      phase: "awaiting_recheck" as const,
      actionResult: null,
      actionError: null,
      recheckError: null,
      reconciliation: null,
    };
    workspaceMock.mockReturnValue({
      ...readyWorkspace(),
      mutationPending: true,
      resolution: awaiting,
    });

    document.body.innerHTML = renderToStaticMarkup(<CardsPage report={null} loadState="ready" />);
    const pending = document.querySelector('[data-testid="cards-mutation-pending"]');
    expect(pending?.getAttribute("aria-busy")).toBe("true");
    expect(pending?.textContent).toContain("Действие выполняется");
    const controls = Array.from(document.querySelectorAll("button"));
    expect(controls.find((button) => button.textContent?.includes("Открыть в Anki"))?.disabled).toBe(true);
    expect(controls.find((button) => button.textContent?.includes("Перепроверить карточку"))?.disabled).toBe(true);
  });
});

function readyWorkspace(): CardsTriageWorkspace {
  return {
    queryStatus: "ready", queryError: null, response,
    learningPeriodDays: 7, setLearningPeriodDays: vi.fn(),
    activeId: items[0]!.itemId, activeItem: items[0]!,
    inspectStatus: "ready", inspectError: null, inspectResponse,
    openPending: false, openResult: null,
    resolution: null, lastOutcome: null, focusRequest: { itemId: null, version: 0 }, mutationPending: false,
    continuationStatus: "idle", continuationError: null, loadedContentPages: 0,
    scannedNoteCount: 500, hasMoreContent: true, lastContinuationAddedCount: null,
    activate: vi.fn(), clearActive: vi.fn(), refresh: vi.fn(), continueContentScan: vi.fn(async () => undefined), retryInspect: vi.fn(), openInAnki: vi.fn(async () => undefined), runSafeAction: vi.fn(async () => undefined), recheckActive: vi.fn(async () => undefined),
  };
}

function source(status: "available" | "empty" | "unavailable", itemCount: number) {
  return { status, itemCount, skippedCount: 0, truncated: false, errorCode: null } as const;
}
