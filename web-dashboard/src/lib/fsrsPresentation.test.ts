import { describe, expect, it } from "vitest";
import { calibrationVerdict, simulatorFieldErrors, targetGap } from "./fsrsPresentation";

describe("FSRS presentation models", () => {
  it("does not turn sparse calibration bins into a strong verdict", () => {
    expect(calibrationVerdict("insufficient", [
      { predicted: .9, actual: 1, sampleSize: 1, sufficiency: "insufficient" },
    ])).toMatchObject({ tone: "neutral", weightedGap: null });
  });

  it("distinguishes close, optimistic, and conservative calibration", () => {
    expect(calibrationVerdict("sufficient", [
      { predicted: .9, actual: .89, sampleSize: 200, sufficiency: "sufficient" },
    ]).title).toContain("близок");
    expect(calibrationVerdict("sufficient", [
      { predicted: .9, actual: .84, sampleSize: 200, sufficiency: "sufficient" },
    ]).title).toContain("оптимистичной");
    expect(calibrationVerdict("sufficient", [
      { predicted: .84, actual: .9, sampleSize: 200, sufficiency: "sufficient" },
    ]).title).toContain("консервативной");
  });

  it("validates simulator bounds before a request", () => {
    expect(simulatorFieldErrors({ desiredRetention: 1, horizonDays: 30, additionalNewCards: -1, newCardsPerDay: 20.5, maximumReviewsPerDay: 0 })).toEqual({
      desiredRetention: "От 75% до 99%.",
      horizonDays: "Выберите 90, 180 или 365 дней.",
      additionalNewCards: "От 0 до 100 000 карточек.",
      newCardsPerDay: "От 0 до 1 000 карточек в день.",
      maximumReviewsPerDay: "От 1 до 10 000 повторений.",
    });
  });

  it("measures actual retention against the nearest target boundary", () => {
    expect(targetGap(.87, { min: .9, max: .93 })).toBeCloseTo(-.03);
    expect(targetGap(.91, { min: .9, max: .93 })).toBe(0);
    expect(targetGap(.95, { min: .9, max: .93 })).toBeCloseTo(.02);
  });
});
