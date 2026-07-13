import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface CalibrationBin {
  label: string;
  predicted: number | null;
  actual: number | null;
  sampleSize: number;
  sufficiency: string;
}

interface DailyPoint {
  day: number;
  reviews: number;
  minutes: number;
}

export function CalibrationChart({ bins }: { bins: CalibrationBin[] }) {
  const points = bins.map((bin) => ({
    ...bin,
    ideal: bin.predicted,
    actualReliable: bin.sufficiency === "insufficient" ? null : bin.actual,
    actualSparse: bin.sufficiency === "insufficient" ? bin.actual : null,
  }));
  const maxSample = Math.max(1, ...bins.map((bin) => bin.sampleSize));
  return (
    <>
      <div className="statistics-rechart fsrs-calibration-chart" role="img" aria-label="Прогноз и фактическое удержание по интервалам">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points} margin={{ top: 12, right: 18, bottom: 8, left: 0 }}>
            <CartesianGrid vertical={false} className="statistics-chart-grid" />
            <XAxis dataKey="label" tickLine={false} axisLine={false} minTickGap={18} />
            <YAxis domain={[0, 1]} tickFormatter={(value) => `${Math.round(value * 100)}%`} tickLine={false} axisLine={false} width={42} />
            <Tooltip formatter={(value, name) => [formatPercent(Number(value)), chartLabel(String(name))]} contentStyle={tooltipStyle} />
            <Line type="linear" dataKey="ideal" stroke="var(--text-muted)" strokeDasharray="5 5" dot={false} strokeWidth={1.5} isAnimationActive={false} />
            <Line type="linear" dataKey="predicted" stroke="var(--stats-color-reviews)" dot={{ r: 3 }} strokeWidth={2.5} connectNulls={false} isAnimationActive={false} />
            <Line type="linear" dataKey="actualReliable" stroke="var(--stats-color-success)" dot={{ r: 4 }} strokeWidth={2.5} connectNulls={false} isAnimationActive={false} />
            <Line type="linear" dataKey="actualSparse" stroke="var(--stats-color-again)" strokeDasharray="3 4" dot={{ r: 4, strokeWidth: 2 }} strokeWidth={1.5} connectNulls={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="fsrs-sample-strip" aria-label="Размер выборки по интервалам">
        {bins.map((bin) => (
          <span key={bin.label} className={bin.sufficiency === "insufficient" ? "is-sparse" : ""}>
            <i style={{ height: `${Math.max(8, bin.sampleSize / maxSample * 100)}%` }} />
            <small>{bin.label}</small>
            <strong>{bin.sampleSize}</strong>
          </span>
        ))}
      </div>
      <div className="statistics-legend" aria-label="Обозначения графика">
        <span><i className="stats-color-reviews" />Прогноз FSRS</span>
        <span><i className="stats-color-success" />Фактически</span>
        <span><i className="fsrs-legend-ideal" />Идеальное совпадение</span>
        <span><i className="stats-color-again" />Малая выборка</span>
      </div>
    </>
  );
}

export function WorkloadComparisonChart({ current, hypothetical }: { current: DailyPoint[]; hypothetical: DailyPoint[] }) {
  const currentByDay = new Map(current.map((point) => [point.day, point]));
  const hypotheticalByDay = new Map(hypothetical.map((point) => [point.day, point]));
  const days = [...new Set([...currentByDay.keys(), ...hypotheticalByDay.keys()])].sort((a, b) => a - b);
  const points = days.map((day) => ({
    day,
    label: `День ${day}`,
    current: currentByDay.get(day)?.reviews ?? null,
    hypothetical: hypotheticalByDay.get(day)?.reviews ?? null,
  }));
  return (
    <>
      <div className="statistics-rechart fsrs-workload-comparison" role="img" aria-label="Сравнение текущей и гипотетической нагрузки">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points} margin={{ top: 12, right: 18, bottom: 8, left: 0 }}>
            <CartesianGrid vertical={false} className="statistics-chart-grid" />
            <XAxis dataKey="label" tickFormatter={(_, index) => index % Math.max(1, Math.ceil(points.length / 6)) === 0 ? `${points[index]?.day ?? ""}` : ""} tickLine={false} axisLine={false} />
            <YAxis domain={[0, "auto"]} tickLine={false} axisLine={false} width={42} />
            <Tooltip contentStyle={tooltipStyle} formatter={(value, name) => [`${Number(value).toLocaleString("ru-RU")} повт.`, name === "current" ? "Текущая цель" : "Сценарий"]} labelFormatter={(label) => String(label)} />
            <Line type="linear" dataKey="current" stroke="var(--text-muted)" strokeDasharray="5 5" dot={false} strokeWidth={2} connectNulls={false} isAnimationActive={false} />
            <Line type="linear" dataKey="hypothetical" stroke="var(--stats-color-reviews)" dot={false} strokeWidth={2.5} connectNulls={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="statistics-legend" aria-label="Обозначения графика">
        <span><i className="fsrs-legend-current" />Текущая цель</span>
        <span><i className="stats-color-reviews" />Гипотетический сценарий</span>
      </div>
    </>
  );
}

const tooltipStyle = {
  background: "var(--surface-2)",
  border: "1px solid var(--border-strong)",
  borderRadius: ".65rem",
  color: "var(--text-primary)",
  fontSize: ".75rem",
};

function formatPercent(value: number) {
  return `${new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 1 }).format(value * 100)}%`;
}

function chartLabel(value: string) {
  return ({ ideal: "Идеально", predicted: "Прогноз FSRS", actualReliable: "Фактически", actualSparse: "Фактически, малая выборка" } as Record<string, string>)[value] || value;
}
