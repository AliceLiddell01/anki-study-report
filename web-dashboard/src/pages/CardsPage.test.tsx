import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import CardsPage from "./CardsPage";
import type { StudyReport } from "../types/report";

const baseReport: StudyReport = {
  metadata: {
    title: "Report",
    period: "today",
    selectedDecks: [],
    includeChildren: true,
    answerMode: "pass_fail",
    createdAt: "2026-07-03",
    detailMode: "normal",
    deletedCardReviews: 0,
    unavailableTrackerNotes: [],
  },
  summary: {
    verdict: "",
    riskLevel: "neutral",
    mainAction: "",
    warning: "",
    newCardsAdvice: "",
  },
  kpis: [],
  answerDistribution: [],
  activity: {
    available: false,
    activeDays: 0,
    missedDays: 0,
    currentStreak: 0,
    bestStreak: 0,
    bestDay: "",
    weekdayAverage: [],
    days: [],
  },
  decks: [],
  attentionCards: [
    {
      cardId: 123,
      noteId: 456,
      deckName: "Japanese",
      frontPreview: "legacy front",
      preview: {
        frontText: "表だけ",
        backText: "back-side meaning",
        primary: "表だけ",
        secondary: "translation must stay hidden",
        tertiary: "cid:999 / template meta",
        mediaBadges: ["audio", "image", "gif"],
        noteTypeName: "Japanese vocab",
        cardTemplateName: "Recognition",
        detectedKind: "japanese_vocab",
      },
      renderedPreview: {
        renderStatus: "sanitized",
        frontHtml: '<span class="word">表だけ</span><img src="/api/media?name=front.gif">',
        backHtml: "<b>back-side meaning</b>",
        frontPlainText: "表だけ",
        backPlainText: "back-side meaning",
        css: ".word { color: red; }",
        mediaRefs: [
          { name: "front.gif", type: "image", url: "/api/media?name=front.gif" },
          { name: "voice.mp3", type: "audio", url: "/api/media?name=voice.mp3" },
        ],
      },
      issues: ["missing pitch", "AUDIO", "missing_audio"],
      riskScore: 80,
      againCount: 2,
      lapses: 1,
      averageAnswerSeconds: 12,
      passRate: 0.5,
      lastReviewedAt: "2026-07-03",
      searchQuery: "cid:123",
    },
  ],
  attentionCardsStatus: {
    status: "available",
    scannedCards: 1,
    returnedCards: 1,
    source: "fresh",
    noteTypeProfilesCount: 1,
  },
  noteTypeCatalog: [
    {
      noteTypeId: 1,
      name: "Japanese vocab",
      noteCount: 120,
      cardTemplateCount: 2,
      fields: ["Word", "Meaning", "Audio"],
      templates: [{ ord: 0, name: "Recognition" }, { ord: 1, name: "Production" }],
      cssAvailable: true,
      usedInCurrentCards: true,
    },
    {
      noteTypeId: 2,
      name: "Basic",
      noteCount: 50,
      cardTemplateCount: 1,
      fields: ["Front", "Back"],
      templates: [{ ord: 0, name: "Card 1" }],
      cssAvailable: false,
      usedInCurrentCards: false,
    },
  ],
  forecast: {
    available: false,
    tomorrow: 0,
    next7Days: 0,
    next30Days: 0,
    activeDayBaseline: 0,
    overloadRisk: "neutral",
    daily: [],
    recommendation: "",
  },
  fsrs: {
    predictedRecall: null,
    cardsBelowTarget: 0,
    highForgettingRisk: 0,
    averageDifficulty: null,
    futureLoad30Days: 0,
    settings: {
      enabled: false,
      desiredRetention: null,
      helperDetected: false,
      helperConfigAvailable: false,
      rescheduleEnabled: false,
      autoDisperse: false,
    },
  },
  recommendations: {
    mainAction: "",
    why: "",
    avoid: "",
    checklist: [],
  },
};

afterEach(() => {
  vi.unstubAllGlobals();
});

function renderCards(displayMode: "table" | "tiles" | "ankiPreview" = "table") {
  vi.stubGlobal("window", {
    location: {
      search: "?token=test-token",
    },
    localStorage: {
      getItem: () => displayMode,
      setItem: () => undefined,
    },
  });
  return renderToStaticMarkup(<CardsPage report={baseReport} loadState="ready" />);
}

describe("CardsPage v4 UX corrections", () => {
  it("renders table preview from frontText without secondary, tertiary, cid, or raw media words", () => {
    const html = renderCards("table");

    expect(html).toContain("表だけ");
    expect(html).toContain("asr-front-preview-table");
    expect(html).toContain("/api/media?name=front.gif&token=test-token");
    expect(html).not.toContain("translation must stay hidden");
    expect(html).not.toContain("cid:999");
    expect(html).not.toContain("AUDIO");
    expect(html).not.toContain("IMAGE");
    expect(html).not.toContain("GIF");
    expect(html).not.toContain("нет ударения");
    expect(html).not.toContain("Медиа:");
    expect(html).toContain("нет аудио");
  });

  it("renders tiles main preview from frontText only", () => {
    const html = renderCards("tiles");

    expect(html).toContain("表だけ");
    expect(html).toContain("asr-front-preview-tile");
    expect(html).toContain("/api/media?name=front.gif&token=test-token");
    expect(html).not.toContain("translation must stay hidden");
    expect(html).not.toContain("cid:123");
  });

  it("renders simplified Anki preview from the front template only", () => {
    const html = renderCards("ankiPreview");

    expect(html).toContain("Front");
    expect(html).toContain("表だけ");
    expect(html).toContain(".asr-card-rendered .word");
    expect(html).toContain("/api/media?name=front.gif&token=test-token");
    expect(html).not.toContain(">Back</h3>");
    expect(html).not.toContain("back-side meaning");
    expect(html).not.toContain("/api/media?name=voice.mp3");
    expect(html).not.toContain("Both");
    expect(html).not.toContain("Anki-like preview fallback");
    expect(html).not.toContain("Упрощённый preview");
  });

  it("keeps display settings compact and hides raw debug wording", () => {
    const html = renderCards("table");

    expect(html).toContain("Настройки отображения");
    expect(html).toContain("Всего типов записей в коллекции");
    expect(html).toContain("Типы записей коллекции");
    expect(html).toContain("Japanese vocab");
    expect(html).not.toContain("localStorage");
    expect(html).not.toContain("Config contract");
    expect(html).not.toContain("strategy auto/structured");
  });
});
