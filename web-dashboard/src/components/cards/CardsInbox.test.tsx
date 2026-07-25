// @vitest-environment jsdom

import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import type { TriageItem, TriageReason } from "../../types/triage";
import { CardsInbox } from "./CardsInbox";

const learning: TriageReason = {
  reasonId: "learning:1",
  code: "learning.repeated_again",
  family: "learning",
  scope: "card",
  priority: "high",
  sources: ["attention"],
  evidence: [{ kind: "review_counts", againCount: 4, periodStartMs: 0, periodEndMs: 7 * 86400000 }],
  detectedAtMs: 10,
};
const content: TriageReason = {
  reasonId: "content:1",
  code: "content.audio_missing",
  family: "content",
  scope: "note",
  priority: "medium",
  sources: ["profile_checks"],
  evidence: [{ kind: "profile_check", profileId: "p", checkId: "c", checkKind: "contains_audio", roles: ["audio"], fields: [], expectedCondition: "contains_audio", actualTextLength: null, expectedTextLength: null, marker: "audio", markerPresent: false, profileRevision: 1, fingerprint: "a".repeat(64), affectedSiblingCount: 3, templateOrdinals: [] }],
  detectedAtMs: null,
};
const items: TriageItem[] = [
  {
    itemId: "card:1001", availability: "available", cardId: "1001", noteId: "2001",
    deck: { deckId: "3", name: "Japanese::Vocabulary::A very long deck name" },
    noteType: { noteTypeId: "7", name: "Japanese Vocabulary" },
    template: { ordinal: 0, name: "Recognition" },
    displayText: "とても長い日本語のカード本文がここに入り改行なしでも安全に制限されます",
    displaySource: "reviewer_front", displayStatus: "available", displayTruncated: false,
    priority: "high", primaryReasonCode: learning.code, reasons: [learning, content], sources: ["attention", "profile_checks"],
    cardState: { state: "review", suspended: false, buried: false, flag: 1 }, inspect: { mode: "cards", cardId: "1001" },
  },
  {
    itemId: "card:1002", availability: "available", cardId: "1002", noteId: "2002",
    deck: { deckId: "4", name: "Programming" }, noteType: { noteTypeId: "8", name: "Basic" }, template: { ordinal: 0, name: "Card 1" },
    displayText: "", displaySource: "reviewer_front", displayStatus: "media_only", displayTruncated: false,
    priority: "medium", primaryReasonCode: content.code, reasons: [content], sources: ["profile_checks"],
    cardState: { state: "suspended", suspended: true, buried: false, flag: 0 }, inspect: { mode: "cards", cardId: "1002" },
  },
];

beforeEach(async () => i18n.changeLanguage("ru"));

describe("CardsInbox", () => {
  it("uses an ordered list with exactly one native button per item and no widget roles", () => {
    const html = renderToStaticMarkup(<CardsInbox items={items} activeId="card:1001" detailRegionId="cards-detail" drawerMode={false} drawerOpen={false} onActivate={vi.fn()} />);
    expect(html).toContain("<ol");
    expect(html.match(/data-testid="cards-inbox-item"/g)).toHaveLength(2);
    expect(html.match(/<button/g)).toHaveLength(2);
    expect(html).not.toContain("<table");
    expect(html).not.toContain('role="grid"');
    expect(html).not.toContain('role="listbox"');
    expect(html).not.toContain('role="option"');
    expect(html).not.toContain('type="checkbox"');
  });

  it("exposes identity as the accessible name and problem context as descriptions", () => {
    const html = renderToStaticMarkup(<CardsInbox items={items} activeId="card:1001" detailRegionId="cards-detail" drawerMode drawerOpen onActivate={vi.fn()} />);
    expect(html).toContain('aria-current="true"');
    expect(html).toContain('aria-expanded="true"');
    expect(html).toContain('aria-labelledby="cards-inbox-card-1001-identity"');
    expect(html).toContain("Частые ответы «Снова»");
    expect(html).toContain("+1 причина");
    expect(html).toContain("уровень записи");
    expect(html).toContain("Карточка только с медиа");
    expect(html).toContain("cards-inbox-item-identity");
  });
});
