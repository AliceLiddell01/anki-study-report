export interface CalibrationBinPresentation {
  predicted: number | null;
  actual: number | null;
  sampleSize: number;
  sufficiency: string;
}

export interface CalibrationVerdict {
  tone: "positive" | "warning" | "neutral";
  title: string;
  detail: string;
  weightedGap: number | null;
}

export function calibrationVerdict(
  sufficiency: string,
  bins: CalibrationBinPresentation[],
): CalibrationVerdict {
  if (sufficiency === "insufficient") {
    return {
      tone: "neutral",
      title: tf("calibration.earlyTitle"),
      detail: tf("calibration.earlyDetail"),
      weightedGap: null,
    };
  }
  const usable = bins.filter((bin) =>
    bin.sufficiency !== "insufficient"
    && bin.predicted != null
    && bin.actual != null
    && bin.sampleSize > 0,
  );
  const sampleSize = usable.reduce((sum, bin) => sum + bin.sampleSize, 0);
  if (!sampleSize) {
    return {
      tone: "neutral",
      title: tf("calibration.unavailableTitle"),
      detail: tf("calibration.unavailableDetail"),
      weightedGap: null,
    };
  }
  const weightedGap = usable.reduce(
    (sum, bin) => sum + ((bin.actual ?? 0) - (bin.predicted ?? 0)) * bin.sampleSize,
    0,
  ) / sampleSize;
  if (Math.abs(weightedGap) <= 0.02) {
    return {
      tone: "positive",
      title: tf("calibration.closeTitle"),
      detail: tf("calibration.closeDetail"),
      weightedGap,
    };
  }
  if (weightedGap < 0) {
    return {
      tone: "warning",
      title: tf("calibration.optimisticTitle"),
      detail: tf("calibration.optimisticDetail"),
      weightedGap,
    };
  }
  return {
    tone: "neutral",
    title: tf("calibration.conservativeTitle"),
    detail: tf("calibration.conservativeDetail"),
    weightedGap,
  };
}

export interface SimulatorValues {
  desiredRetention: number;
  horizonDays: number;
  additionalNewCards: number;
  newCardsPerDay: number;
  maximumReviewsPerDay: number;
}

export function simulatorFieldErrors(values: SimulatorValues): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!bounded(values.desiredRetention, 0.75, 0.99)) errors.desiredRetention = tf("validation.desiredRetention");
  if (![90, 180, 365].includes(values.horizonDays)) errors.horizonDays = tf("validation.horizonDays");
  if (!whole(values.additionalNewCards, 0, 100_000)) errors.additionalNewCards = tf("validation.additionalNewCards");
  if (!whole(values.newCardsPerDay, 0, 1_000)) errors.newCardsPerDay = tf("validation.newCardsPerDay");
  if (!whole(values.maximumReviewsPerDay, 1, 10_000)) errors.maximumReviewsPerDay = tf("validation.maximumReviewsPerDay");
  return errors;
}

export function targetGap(actual: number | null, target: { min: number; max: number } | null): number | null {
  if (actual == null || !target) return null;
  if (actual < target.min) return actual - target.min;
  if (actual > target.max) return actual - target.max;
  return 0;
}

function bounded(value: number, min: number, max: number): boolean {
  return Number.isFinite(value) && value >= min && value <= max;
}

function whole(value: number, min: number, max: number): boolean {
  return bounded(value, min, max) && Number.isInteger(value);
}
import i18n from "../i18n";

const tf = (key: string) => i18n.t(key, { ns: "fsrs" });
