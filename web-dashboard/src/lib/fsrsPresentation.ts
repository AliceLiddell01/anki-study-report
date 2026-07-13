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
      title: "Пока рано оценивать точность модели",
      detail: "Достаточных интервалов мало, поэтому расхождение не превращается в сильный вывод.",
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
      title: "Вывод по калибровке недоступен",
      detail: "В ответе нет интервалов с достаточной выборкой и парой прогноз/факт.",
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
      title: "Прогноз близок к фактическому удержанию",
      detail: "Среднее взвешенное расхождение достаточных интервалов не превышает 2 процентных пунктов.",
      weightedGap,
    };
  }
  if (weightedGap < 0) {
    return {
      tone: "warning",
      title: "Модель выглядит оптимистичной",
      detail: "В достаточных интервалах фактическое удержание в среднем ниже прогноза FSRS.",
      weightedGap,
    };
  }
  return {
    tone: "neutral",
    title: "Модель выглядит консервативной",
    detail: "В достаточных интервалах фактическое удержание в среднем выше прогноза FSRS.",
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
  if (!bounded(values.desiredRetention, 0.75, 0.99)) errors.desiredRetention = "От 75% до 99%.";
  if (![90, 180, 365].includes(values.horizonDays)) errors.horizonDays = "Выберите 90, 180 или 365 дней.";
  if (!whole(values.additionalNewCards, 0, 100_000)) errors.additionalNewCards = "От 0 до 100 000 карточек.";
  if (!whole(values.newCardsPerDay, 0, 1_000)) errors.newCardsPerDay = "От 0 до 1 000 карточек в день.";
  if (!whole(values.maximumReviewsPerDay, 1, 10_000)) errors.maximumReviewsPerDay = "От 1 до 10 000 повторений.";
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
