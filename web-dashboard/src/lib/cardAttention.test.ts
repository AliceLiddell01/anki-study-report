import { describe, expect, it } from "vitest";
import {
  buildCardAttentionRows,
  buildCardBrowserSearch,
  cardAttentionState,
  cardIssueLabels,
  DEFAULT_CARD_FILTERS,
  explainCardAttentionEmptyState,
  filterCardAttentionRows,
  hasCardAttentionSource,
  summarizeCardAttentionRows,
} from "./cardAttention";
import type { StudyReport } from "../types/report";

const baseReport = {
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
} satisfies StudyReport;

function aliasRow(label: string, overrides: Record<string, unknown> = {}) {
  return {
    id: `alias-${label}`,
    cardId: "456",
    noteId: "789",
    deckName: "Legacy::Deck",
    frontPreview: `front from ${label}`,
    preview: {
      primary: `preview primary ${label}`,
      secondary: `preview secondary ${label}`,
      tertiary: "legacy meta",
      mediaBadges: ["audio"],
    },
    issues: ["missing audio"],
    riskScore: 77,
    againCount: 1,
    lapses: 0,
    averageAnswerSeconds: 8,
    passRate: 0.9,
    lastReviewedAt: "2026-07-01",
    search_query: "nid:789",
    ...overrides,
  };
}

describe("cardAttention", () => {
  it("keeps the Cards reset-filter target on all time and all decks", () => {
    expect(DEFAULT_CARD_FILTERS).toEqual({
      period: "all",
      deck: "all",
      issue: "all",
      query: "",
      sortKey: "risk",
    });
  });

  it("normalizes explicit and inferred issue chips", () => {
    const rows = buildCardAttentionRows({
      ...baseReport,
      attentionCards: [
        {
          id: "one",
          cardId: 123,
          deckName: "Words",
          front: "front",
          issues: ["missing audio"],
          againCount: 3,
          lapses: 8,
          averageAnswerSeconds: 18,
          passRate: 0.64,
          lastReviewed: "2026-07-03",
          riskScore: 0,
        } as never,
      ],
    });

    expect(rows).toHaveLength(1);
    expect(rows[0].issues).toEqual(["missing_audio", "leech", "repeated_again", "slow_answer", "low_pass_rate"]);
    expect(rows[0].browserSearch).toBe("cid:123");
  });

  it("distinguishes missing, unavailable, and empty available card-level states", () => {
    expect(hasCardAttentionSource(baseReport)).toBe(false);
    expect(cardAttentionState(baseReport).status).toBe("absent");
    expect(hasCardAttentionSource({ ...baseReport, cards: [] } as unknown as StudyReport)).toBe(false);
    expect(cardAttentionState({ ...baseReport, cards: [] } as unknown as StudyReport).status).toBe("absent");
    expect(hasCardAttentionSource({ ...baseReport, attentionCards: [], attentionCardsStatus: { status: "available", scannedCards: 10, returnedCards: 0 } })).toBe(true);
    expect(
      cardAttentionState({
        ...baseReport,
        attentionCards: [],
        attentionCardsStatus: {
          status: "available",
          scannedCards: 10,
          returnedCards: 0,
          collectorRan: true,
          collectionAvailable: true,
          revlogRows: 12,
          candidateCards: 10,
          notesLoaded: 8,
          fieldScanCards: 10,
          cardsTotal: 100,
          notesTotal: 90,
          source: "fresh",
          issueCounts: {
            repeatedAgain: 2,
          },
          thresholds: {
            repeatedAgainThreshold: 2,
            slowAnswerSeconds: 10,
            lowPassRateThreshold: 0.6,
            leechLapsesFallback: 8,
            maxResults: 100,
          },
        },
      }),
    ).toMatchObject({
      status: "available",
      collectorRan: true,
      collectionAvailable: true,
      revlogRows: 12,
      candidateCards: 10,
      notesLoaded: 8,
      fieldScanCards: 10,
      cardsTotal: 100,
      notesTotal: 90,
      source: "fresh",
      issueCounts: expect.objectContaining({ repeatedAgain: 2 }),
      thresholds: expect.objectContaining({ slowAnswerSeconds: 10 }),
    });
    expect(buildCardAttentionRows({ ...baseReport, attentionCards: [] })).toEqual([]);
  });

  it("treats explicit collector errors as unavailable card-level data", () => {
    const state = cardAttentionState({
      ...baseReport,
      attentionCards: [],
      attentionCardsStatus: {
        status: "error",
        scannedCards: 0,
        returnedCards: 0,
        reason: "Card-level collector failed.",
      },
    });

    expect(state).toMatchObject({
      status: "error",
      scannedCards: 0,
      returnedCards: 0,
      reason: "Card-level collector failed.",
      hasExplicitStatus: true,
      hasRowsKey: true,
    });
    expect(hasCardAttentionSource({ ...baseReport, attentionCards: [], attentionCardsStatus: { status: "error" } })).toBe(false);
  });

  it("keeps cache unavailable status as fallback-only card-level state", () => {
    const state = cardAttentionState({
      ...baseReport,
      attentionCards: [],
      attentionCardsStatus: {
        status: "unavailable",
        scannedCards: 0,
        returnedCards: 0,
        collectorRan: false,
        collectionAvailable: false,
        reason: "cache snapshot has no card-level payload; fresh overlay not applied",
        source: "cache",
      },
    });

    expect(state).toMatchObject({
      status: "unavailable",
      scannedCards: 0,
      returnedCards: 0,
      collectorRan: false,
      collectionAvailable: false,
      source: "cache",
      hasExplicitStatus: true,
      hasRowsKey: true,
    });
    expect(hasCardAttentionSource({ ...baseReport, attentionCards: [], attentionCardsStatus: { status: "unavailable", source: "cache" } })).toBe(false);
  });

  it("explains available empty scans with no revlog rows", () => {
    const state = cardAttentionState({
      ...baseReport,
      attentionCards: [],
      attentionCardsStatus: {
        status: "available",
        source: "fresh",
        revlogRows: 0,
        candidateCards: 0,
        scannedCards: 0,
        returnedCards: 0,
      },
    });

    expect(explainCardAttentionEmptyState(state)).toMatchObject({
      title: "Нет проблемных карточек",
      text: "В выбранном периоде нет повторений для выбранной колоды.",
      sourceText: "Данные уровня карточек собраны из текущей коллекции Anki.",
    });
  });

  it("explains period mismatch when revlog exists outside selected period", () => {
    const state = cardAttentionState({
      ...baseReport,
      attentionCards: [],
      attentionCardsStatus: {
        status: "available",
        source: "fresh",
        revlogTotalRows: 100,
        revlogRowsInPeriod: 0,
        candidateCards: 0,
        scannedCards: 0,
        returnedCards: 0,
        periodStartRaw: 0,
        periodEndRaw: 1_783_100_000,
        periodStartMs: 0,
        periodEndMs: 1_783_100_000_000,
        timeUnitNormalized: true,
      },
    });

    expect(state).toMatchObject({
      revlogTotalRows: 100,
      revlogRowsInPeriod: 0,
      periodEndMs: 1_783_100_000_000,
      timeUnitNormalized: true,
    });
    expect(explainCardAttentionEmptyState(state).text).toBe("Повторы в revlog есть, но выбранный период не совпал с timestamp range.");
  });

  it("explains when deck filter removes period revlog rows", () => {
    const state = cardAttentionState({
      ...baseReport,
      attentionCards: [],
      attentionCardsStatus: {
        status: "available",
        source: "fresh",
        revlogTotalRows: 100,
        revlogRowsInPeriod: 20,
        revlogRowsAfterDeckFilter: 0,
        deckFilterApplied: true,
        selectedDeckIdsCount: 1,
        candidateCards: 0,
        scannedCards: 0,
        returnedCards: 0,
      },
    });

    expect(state).toMatchObject({
      deckFilterApplied: true,
      selectedDeckIdsCount: 1,
      revlogRowsAfterDeckFilter: 0,
    });
    expect(explainCardAttentionEmptyState(state).text).toBe("Фильтр колоды отсеял все revlog-записи.");
  });

  it("explains available empty scans with scanned cards and no issues", () => {
    const state = cardAttentionState({
      ...baseReport,
      attentionCards: [],
      attentionCardsStatus: {
        status: "available",
        source: "fresh",
        revlogRows: 12,
        candidateCards: 4,
        scannedCards: 4,
        returnedCards: 0,
      },
    });

    expect(explainCardAttentionEmptyState(state).text).toBe(
      "Карточки были просканированы, но leech, repeated Again, slow answer, low pass rate и missing-field issues не найдены.",
    );
  });

  it("marks fresh available rows as a real card-level source", () => {
    const report = {
      ...baseReport,
      attentionCards: [
        {
          cardId: 10,
          deckName: "Words",
          frontPreview: "front",
          issues: ["leech"],
        },
      ],
      attentionCardsStatus: {
        status: "available",
        scannedCards: 1,
        returnedCards: 1,
        source: "fresh",
      },
    } as StudyReport;

    expect(cardAttentionState(report)).toMatchObject({
      status: "available",
      source: "fresh",
      returnedCards: 1,
    });
    expect(buildCardAttentionRows(report)).toHaveLength(1);
  });

  it("filters by period, deck, issue, query and sort order", () => {
    const rows = buildCardAttentionRows({
      ...baseReport,
      attentionCards: [
        {
          id: "slow",
          cardId: 2,
          deckName: "Grammar",
          front: "particle",
          issues: ["slow_answer"],
          againCount: 1,
          lapses: 0,
          averageAnswerSeconds: 20,
          passRate: 0.9,
          lastReviewed: "2026-07-02",
          riskScore: 50,
        },
        {
          id: "again",
          cardId: 1,
          deckName: "Words",
          front: "abstract verb",
          issues: ["repeated_again"],
          againCount: 5,
          lapses: 1,
          averageAnswerSeconds: 9,
          passRate: 0.7,
          lastReviewed: "2026-07-03",
          riskScore: 80,
        },
      ],
    } as unknown as StudyReport);

    expect(
      filterCardAttentionRows(rows, {
        period: "today",
        deck: "Words",
        issue: "repeated_again",
        query: "abstract",
        sortKey: "again",
      }, { today: "2026-07-03" }).map((row) => row.id),
    ).toEqual(["again"]);
  });

  it("filters card rows locally by last reviewed date and updates KPI inputs", () => {
    const rows = buildCardAttentionRows({
      ...baseReport,
      attentionCards: [
        {
          id: "old",
          cardId: 1,
          deckName: "Words",
          front: "old",
          issues: ["leech"],
          againCount: 0,
          lapses: 0,
          averageAnswerSeconds: null,
          passRate: null,
          lastReviewed: "2026-05-01",
          riskScore: 90,
        },
        {
          id: "recent",
          cardId: 2,
          deckName: "Words",
          front: "recent",
          issues: ["missing_example"],
          againCount: 0,
          lapses: 0,
          averageAnswerSeconds: null,
          passRate: null,
          lastReviewed: "2026-07-02",
          riskScore: 40,
        },
      ],
    } as unknown as StudyReport);

    const filtered = filterCardAttentionRows(rows, { period: "7d", deck: "all", issue: "all", query: "", sortKey: "risk" }, { today: "2026-07-03" });

    expect(filtered.map((row) => row.id)).toEqual(["recent"]);
    expect(summarizeCardAttentionRows(filtered)).toMatchObject({
      problemCards: 1,
      leech: 0,
      dataGaps: 1,
    });
  });

  it("normalizes structured preview with badges", () => {
    const rows = buildCardAttentionRows({
      ...baseReport,
      attentionCards: [
        {
          cardId: 9,
          deckName: "Japanese",
          frontPreview: "fallback",
          preview: {
            primary: "鑑みる",
            secondary: "かんがみる",
            tertiary: "учитывать / глагол",
            mediaBadges: ["audio", "pitch", "gif"],
            noteTypeName: "Japanese vocab",
            cardTemplateName: "Recognition",
            detectedKind: "japanese_vocab",
          },
          issues: ["leech"],
        },
      ],
    } as unknown as StudyReport);

    expect(rows[0].front).toBe("鑑みる");
    expect(rows[0].preview).toMatchObject({
      frontText: "鑑みる",
      primary: "鑑みる",
      secondary: "かんがみる",
      mediaBadges: ["audio", "pitch", "gif"],
      noteTypeName: "Japanese vocab",
      cardTemplateName: "Recognition",
      detectedKind: "japanese_vocab",
    });
  });

  it("uses frontText as the row front and keeps bare media words out of issues", () => {
    const rows = buildCardAttentionRows({
      ...baseReport,
      attentionCards: [
        {
          cardId: 9,
          deckName: "Japanese",
          frontPreview: "legacy fallback",
          preview: {
            frontText: "表だけ",
            backText: "back-side meaning",
            primary: "表だけ",
            secondary: "translation should not be the front",
            tertiary: "cid-like meta",
            mediaBadges: ["AUDIO", "IMAGE", "GIF"],
          },
          issues: ["AUDIO", "IMAGE", "GIF", "missing pitch", "missing audio"],
        },
      ],
    } as StudyReport);

    expect(rows).toHaveLength(1);
    expect(rows[0].front).toBe("表だけ");
    expect(rows[0].issues).toEqual(["missing_audio"]);
    expect(rows[0].preview?.mediaBadges).toEqual(["audio", "image", "gif"]);
  });

  it("exposes the Russian localized issue-label contract", () => {
    expect(cardIssueLabels).toMatchObject({
      leech: "Leech",
      repeated_again: "Частые ответы «Снова»",
      slow_answer: "Долгий ответ",
      low_pass_rate: "Низкая успешность",
      missing_audio: "Нет аудио",
      missing_image: "Нет изображения",
    });
  });

  it("sorts normalized rows by risk score by default", () => {
    const rows = buildCardAttentionRows({
      ...baseReport,
      attentionCards: [
        {
          cardId: "1",
          deckName: "Words",
          frontPreview: "low",
          issues: ["slow answer"],
          riskScore: 20,
        },
        {
          cardId: "2",
          deckName: "Words",
          frontPreview: "high",
          issues: ["leech"],
          riskScore: 90,
        },
      ],
    } as StudyReport);

    expect(rows.map((row) => row.front)).toEqual(["high", "low"]);
  });

  it("summarizes KPI counts only from real card-level rows", () => {
    const rows = buildCardAttentionRows({
      ...baseReport,
      attentionCards: [
        {
          cardId: 1,
          deckName: "Words",
          frontPreview: "one",
          issues: ["leech", "missing audio"],
        },
        {
          cardId: 2,
          deckName: "Words",
          frontPreview: "two",
          issues: ["repeated again", "slow answer"],
        },
      ],
    } as StudyReport);

    expect(summarizeCardAttentionRows(rows)).toEqual({
      problemCards: 2,
      leech: 1,
      repeatedAgain: 1,
      slowAnswer: 1,
      dataGaps: 1,
    });
    expect(summarizeCardAttentionRows([])).toEqual({
      problemCards: 0,
      leech: 0,
      repeatedAgain: 0,
      slowAnswer: 0,
      dataGaps: 0,
    });
  });

  it("builds a deck search fallback when card id is unavailable", () => {
    expect(buildCardBrowserSearch({ deckName: 'Words::"N1"' })).toBe('deck:"Words::\\"N1\\""');
    expect(buildCardBrowserSearch({ deckName: "Words", noteId: 456 })).toBe("nid:456");
    expect(buildCardBrowserSearch({ deckName: "Words", front: 'quoted "term"' })).toBe('deck:"Words" quoted term');
  });

  it("normalizes rendered preview fallback safely", () => {
    const rows = buildCardAttentionRows({
      ...baseReport,
      attentionCards: [
        {
          cardId: 1,
          deckName: "Words",
          frontPreview: "front",
          renderedPreview: {
            renderStatus: "unavailable",
            renderSource: "anki_like_fallback",
            fallbackReason: "native_unavailable_no_card_id",
            reason: "structured preview is used",
          },
          issues: ["leech"],
        },
      ],
    } as StudyReport);

    expect(rows[0].renderedPreview).toMatchObject({
      renderStatus: "unavailable",
      renderSource: "anki_like_fallback",
      fallbackReason: "native_unavailable_no_card_id",
      reason: "structured preview is used",
    });
  });

  it("characterizes canonical raw card-level payload attentionCards", () => {
    const key = "attentionCards";
    const rows = buildCardAttentionRows({
      ...baseReport,
      [key]: [aliasRow(key)],
    } as unknown as StudyReport);

    expect(rows).toHaveLength(1);
    expect(rows[0]).toMatchObject({
      id: `alias-${key}`,
      cardId: 456,
      noteId: 789,
      deckName: "Legacy::Deck",
      front: `preview primary ${key}`,
      lastReviewed: "2026-07-01",
      browserSearch: "nid:789",
      issues: ["missing_audio"],
      riskScore: 77,
      averageAnswerSeconds: 8,
      passRate: 0.9,
    } as unknown as StudyReport);
    expect(rows[0].preview).toMatchObject({
      frontText: `preview primary ${key}`,
      primary: `preview primary ${key}`,
      secondary: `preview secondary ${key}`,
      mediaBadges: ["audio"],
    } as unknown as StudyReport);
  });

  it("keeps canonical attentionCards when removed legacy aliases are also present", () => {
    const canonical = aliasRow("attentionCards", { cardId: 100, frontPreview: "canonical", riskScore: 10 });
    const cards = aliasRow("cards", { cardId: 200, frontPreview: "cards alias", riskScore: 20 });

    expect(buildCardAttentionRows({ ...baseReport, attentionCards: [canonical], cards: [cards] } as unknown as StudyReport).map((row) => row.cardId)).toEqual([100]);
  });

  it("ignores removed top-level cards payload alias", () => {
    const cards = aliasRow("cards", { cardId: 200, riskScore: 20 });

    expect(buildCardAttentionRows({ ...baseReport, cards: [cards] } as unknown as StudyReport)).toEqual([]);
    expect(cardAttentionState({ ...baseReport, cards: [cards] } as unknown as StudyReport)).toMatchObject({
      status: "absent",
      hasRowsKey: false,
    } as unknown as StudyReport);
  });

  it("ignores removed top-level problemCards payload alias", () => {
    const problemCards = aliasRow("problemCards", { cardId: 400, riskScore: 40 });

    expect(buildCardAttentionRows({ ...baseReport, problemCards: [problemCards] } as unknown as StudyReport)).toEqual([]);
    expect(cardAttentionState({ ...baseReport, problemCards: [problemCards] } as unknown as StudyReport)).toMatchObject({
      status: "absent",
      hasRowsKey: false,
    } as unknown as StudyReport);
  });

  it("ignores removed top-level cardIssues payload alias", () => {
    const cardIssues = aliasRow("cardIssues", { cardId: 300, riskScore: 30 });

    expect(buildCardAttentionRows({ ...baseReport, cardIssues: [cardIssues] } as unknown as StudyReport)).toEqual([]);
    expect(cardAttentionState({ ...baseReport, cardIssues: [cardIssues] } as unknown as StudyReport)).toMatchObject({
      status: "absent",
      hasRowsKey: false,
    });
  });

  it("does not fall back to removed legacy aliases when canonical attentionCards is an empty array", () => {
    const cards = aliasRow("cards", { cardId: 200, riskScore: 20 });

    expect(buildCardAttentionRows({ ...baseReport, attentionCards: [], cards: [cards] } as unknown as StudyReport)).toEqual([]);
    expect(cardAttentionState({ ...baseReport, attentionCards: [], cards: [cards] } as unknown as StudyReport)).toMatchObject({
      status: "unavailable",
      hasRowsKey: true,
    });
  });

  it("accepts snake_case legacy row fields without changing the normalized card contract", () => {
    const rows = buildCardAttentionRows({
      ...baseReport,
      attentionCards: [
        {
          cardId: "456",
          noteId: "789",
          deckName: "Listening",
          frontPreview: "audio prompt",
          issues: [],
          missingFields: ["missing_audio"],
          lastReviewedAt: "2026-07-01",
          searchQuery: "cid:456",
        },
      ],
    } as StudyReport);

    expect(rows).toHaveLength(1);
    expect(rows[0]).toMatchObject({
      cardId: 456,
      noteId: 789,
      front: "audio prompt",
      lastReviewed: "2026-07-01",
      browserSearch: "cid:456",
      issues: ["missing_audio"],
    });
  });
});
