import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  ANKI_PREVIEW_MODE_CONFIG,
  AnkiCardShadowPreview,
  buildShadowPreviewDocument,
  calculateAdaptivePreviewLayout,
} from "../components/AnkiCardShadowPreview";
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
        frontHtml:
          '<span class="asr-card-replay"><button class="asr-card-replay-button" type="button" aria-label="Play audio voice.mp3" data-audio-name="voice.mp3"><span class="asr-card-replay-icon" aria-hidden="true">&#9658;</span></button><audio class="asr-card-audio" preload="none" src="/api/media?name=voice.mp3"></audio></span><span class="word">表だけ</span><img src="/api/media?name=front.gif">',
        backHtml:
          '<span class="asr-card-replay"><button class="asr-card-replay-button" type="button" aria-label="Play audio answer.mp3" data-audio-name="answer.mp3"><span class="asr-card-replay-icon" aria-hidden="true">&#9658;</span></button><audio class="asr-card-audio" preload="none" src="/api/media?name=answer.mp3"></audio></span><b>back-side meaning</b>',
        frontPlainText: "表だけ",
        backPlainText: "back-side meaning",
        css: ".word { color: red; }",
        cardOrd: 0,
        mediaRefs: [
          { name: "front.gif", type: "image", url: "/api/media?name=front.gif" },
          { name: "voice.mp3", type: "audio", url: "/api/media?name=voice.mp3" },
          { name: "answer.mp3", type: "audio", url: "/api/media?name=answer.mp3" },
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

function renderCards(displayMode: "table" | "tiles" | "ankiPreview" = "table", report: StudyReport = baseReport) {
  vi.stubGlobal("window", {
    location: {
      search: "?token=test-token",
    },
    localStorage: {
      getItem: () => displayMode,
      setItem: () => undefined,
    },
  });
  return renderToStaticMarkup(<CardsPage report={report} loadState="ready" />);
}

describe("CardsPage v5 adaptive card previews", () => {
  it("renders table preview from frontText without secondary, tertiary, cid, or raw media words", () => {
    const html = renderCards("table");

    expect(html).toContain("表だけ");
    expect(html).toContain("cards-risk-table");
    expect(html).toContain('data-testid="cards-table-wrap"');
    expect(html).toContain('data-testid="cards-risk-table"');
    expect(html).toContain('data-testid="cards-table-row"');
    expect(html).toContain('data-testid="cards-table-preview-cell"');
    expect(html).toContain('data-testid="cards-table-issues"');
    expect(html).toContain('data-testid="cards-table-actions"');
    expect(html).toContain("cards-risk-badge");
    expect(html).toContain("Высокий ·");
    expect(html).toContain("cards-row-open");
    expect(html).toContain("Открыть в Anki");
    expect(html).toContain("cards-row-copy");
    expect(html).toContain("anki-card-shadow-preview");
    expect(html).toContain('data-shadow-preview="true"');
    expect(html).toContain('data-preview-mode="table"');
    expect(html).toContain("asr-front-preview-table");
    expect(html).toContain("/api/media?name=front.gif&token=test-token");
    expect(html).not.toContain("translation must stay hidden");
    expect(html).not.toContain("back-side meaning");
    expect(html).not.toContain("/api/media?name=answer.mp3");
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
    const tileIndex = html.indexOf('data-testid="cards-tile"');
    const previewSlotIndex = html.indexOf('data-testid="cards-tile-preview-slot"');
    const metricsIndex = html.indexOf('data-testid="cards-tile-metrics"');
    const issuesIndex = html.indexOf('data-testid="cards-tile-issues"');
    const actionsIndex = html.indexOf('data-testid="cards-tile-actions"');

    expect(html).toContain("表だけ");
    expect(tileIndex).toBeGreaterThanOrEqual(0);
    expect(previewSlotIndex).toBeGreaterThan(tileIndex);
    expect(metricsIndex).toBeGreaterThan(previewSlotIndex);
    expect(issuesIndex).toBeGreaterThan(metricsIndex);
    expect(actionsIndex).toBeGreaterThan(issuesIndex);
    expect(html).toContain("anki-card-shadow-preview");
    expect(html).toContain('data-preview-mode="tile"');
    expect(html).toContain('data-preview-side="front"');
    expect(html).toContain('data-testid="cards-tile-meta"');
    expect(html).toContain("asr-front-preview-tile");
    expect(html).toContain("/api/media?name=front.gif&token=test-token");
    expect(html).not.toContain("translation must stay hidden");
    expect(html).not.toContain("back-side meaning");
    expect(html).not.toContain("/api/media?name=answer.mp3");
    expect(html).not.toContain("cid:123");
  });

  it("renders Anki preview as answer-only from the back template", () => {
    const html = renderCards("ankiPreview");

    expect(html).toContain("Вид после ответа");
    expect(html).toContain('data-testid="anki-preview-answer"');
    expect(html).toContain('data-shadow-preview-mode="preview"');
    expect(html).toContain('data-preview-mode="preview"');
    expect(html).toContain('data-preview-side="answer"');
    expect(html).not.toContain('data-testid="anki-preview-front"');
    expect(html).not.toContain('data-testid="anki-preview-back"');
    expect(html).not.toContain(".asr-card-rendered .word");
    expect(html).toContain("back-side meaning");
    expect(html).toContain("/api/media?name=answer.mp3&token=test-token");
    expect(html).not.toContain("/api/media?name=front.gif&token=test-token");
    expect(html).not.toContain("/api/media?name=voice.mp3&token=test-token");
    expect(html).toContain("asr-card-replay-button");
    expect(html).toContain("asr-card-audio");
    expect(html).not.toContain(" controls");
    expect(html).not.toContain(">Back</h3>");
    expect(html).not.toContain("Both");
    expect(html).not.toContain("Anki-like preview fallback");
    expect(html).not.toContain("Упрощённое превью");
  });

  it("falls back to the front preview when the rendered answer is unavailable", () => {
    const report = JSON.parse(JSON.stringify(baseReport)) as StudyReport;
    const rendered = report.attentionCards?.[0]?.renderedPreview;
    if (rendered) {
      rendered.backHtml = "";
      rendered.reason = "answer render skipped";
    }
    const html = renderCards("ankiPreview", report);

    expect(html).toContain("Вид после ответа");
    expect(html).toContain('data-testid="anki-preview-answer"');
    expect(html).toContain("表だけ");
    expect(html).toContain("/api/media?name=front.gif&token=test-token");
    expect(html).toContain("Ответ недоступен, показана лицевая сторона: answer render skipped");
    expect(html).not.toContain("back-side meaning");
  });

  it("keeps template diagnostics closed and hides raw debug wording", () => {
    const html = renderCards("table");

    expect(html).toContain("Настройки отображения");
    expect(html).toContain("Диагностика шаблонов");
    expect(html).toContain("Типов записей в коллекции");
    expect(html).toContain("Japanese vocab");
    expect(html).not.toContain("localStorage");
    expect(html).not.toContain("Config contract");
    expect(html).not.toContain("strategy auto/structured");
  });

  it("builds a shadow preview document with card classes, note CSS, and safe HTML", () => {
    const renderedHost = renderToStaticMarkup(
      <AnkiCardShadowPreview
        mode="table"
        html='<span class="asr-card-replay"><button class="asr-card-replay-button" type="button" aria-label="Play audio voice.mp3" data-audio-name="voice.mp3"><span class="asr-card-replay-icon" aria-hidden="true">&#9658;</span></button><audio class="asr-card-audio" preload="none" src="/api/media?name=voice.mp3"></audio></span><span class="word-focus" style="color: rgb(255, 165, 0)">要望する</span>'
        css=".word-focus { font-weight: 700; }"
        title="要望する"
        cardOrd={1}
        renderSource="anki_native"
        nightMode
      />,
    );
    const document = buildShadowPreviewDocument({
      mode: "table",
      html: '<span class="asr-card-replay"><button class="asr-card-replay-button" type="button" aria-label="Play audio voice.mp3" data-audio-name="voice.mp3"><span class="asr-card-replay-icon" aria-hidden="true">&#9658;</span></button><audio class="asr-card-audio" preload="none" src="/api/media?name=voice.mp3"></audio></span><span class="word-focus">要望する</span>',
      css: ".word-focus { font-weight: 700; }",
      cardOrd: 1,
      nightMode: true,
    });

    expect(renderedHost).toContain('data-shadow-preview="true"');
    expect(renderedHost).toContain('data-preview-side="front"');
    expect(renderedHost).toContain('data-render-source="anki_native"');
    expect(renderedHost).toContain('data-preview-measured="false"');
    expect(renderedHost).toContain('data-preview-overflow="false"');
    expect(renderedHost).toContain('data-preview-scale="0.500"');
    expect(renderedHost).toContain("data-shadow-preview-template");
    expect(renderedHost).toContain("asr-card-replay-button");
    expect(renderedHost).toContain("asr-card-audio");
    expect(renderedHost).not.toContain(" controls");
    expect(renderedHost).toContain("word-focus");
    expect(document.cardClassName).toBe("card card2 nightMode");
    expect(document.shellClassName).toBe("asr-shadow-card-shell asr-shadow-card-shell--table asr-shadow-card-shell--front nightMode");
    expect(document.viewportClassName).toBe("asr-shadow-card-viewport asr-shadow-card-viewport--table");
    expect(document.styleText).toContain(".word-focus { font-weight: 700; }");
    expect(document.styleText).toContain(".nightMode .card");
    expect(document.styleText).toContain(".asr-card-replay-button");
    expect(document.styleText).toContain(".asr-card-audio");
    expect(document.styleText).toContain("display: none");
    expect(document.styleText).toContain("transform: scale(var(--asr-preview-scale))");
    expect(document.styleText).toContain("overflow: visible");
    expect(ANKI_PREVIEW_MODE_CONFIG.table.scale).toBeGreaterThan(0.36);
    expect(ANKI_PREVIEW_MODE_CONFIG.table.minScale).toBeLessThan(ANKI_PREVIEW_MODE_CONFIG.table.maxScale);
    expect(ANKI_PREVIEW_MODE_CONFIG.tile.targetWidth).toBeGreaterThan(ANKI_PREVIEW_MODE_CONFIG.table.targetWidth);
    expect(ANKI_PREVIEW_MODE_CONFIG.preview.targetHeight).toBeGreaterThan(ANKI_PREVIEW_MODE_CONFIG.tile.targetHeight);
    expect(document.html).toContain("asr-card-replay-button");
    expect(document.html).toContain("asr-card-audio");
    expect(document.html).toContain("要望する");
  });

  it("calculates adaptive height for answer preview without clipping normal long cards", () => {
    const previewLayout = calculateAdaptivePreviewLayout({
      mode: "preview",
      availableWidth: 720,
      contentWidth: 720,
      contentHeight: 900,
    });
    const tableLayout = calculateAdaptivePreviewLayout({
      mode: "table",
      availableWidth: 336,
      contentWidth: 640,
      contentHeight: 900,
    });
    const tileLayout = calculateAdaptivePreviewLayout({
      mode: "tile",
      availableWidth: 500,
      contentWidth: 640,
      contentHeight: 260,
    });

    expect(previewLayout.overflow).toBe(false);
    expect(previewLayout.hostHeight).toBeGreaterThan(ANKI_PREVIEW_MODE_CONFIG.preview.targetHeight);
    expect(previewLayout.scale).toBeGreaterThanOrEqual(ANKI_PREVIEW_MODE_CONFIG.preview.minScale);
    expect(previewLayout.scale).toBeLessThanOrEqual(ANKI_PREVIEW_MODE_CONFIG.preview.maxScale);
    expect(tableLayout.hostHeight).toBeLessThanOrEqual(ANKI_PREVIEW_MODE_CONFIG.table.maxHeight ?? Infinity);
    expect(tableLayout.overflow).toBe(true);
    expect(tableLayout.scale).toBeLessThanOrEqual(ANKI_PREVIEW_MODE_CONFIG.table.maxScale);
    expect(tileLayout.overflow).toBe(false);
    expect(tileLayout.hostHeight).toBeLessThan(ANKI_PREVIEW_MODE_CONFIG.tile.maxHeight ?? Infinity);
  });
});
