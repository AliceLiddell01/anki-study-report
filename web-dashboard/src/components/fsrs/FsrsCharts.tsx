import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";
import { localeForLanguage } from "../../i18n/language";

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
  const { t } = useTranslation("fsrs");
  const points = bins.map((bin) => ({
    ...bin,
    ideal: bin.predicted,
    actualReliable: bin.sufficiency === "insufficient" ? null : bin.actual,
    actualSparse: bin.sufficiency === "insufficient" ? bin.actual : null,
  }));
  const maxSample = Math.max(1, ...bins.map((bin) => bin.sampleSize));
  return (
    <>
      <div className="statistics-rechart fsrs-calibration-chart" role="img" aria-label={t("charts.calibrationAria")}>
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
      <div className="fsrs-sample-strip" aria-label={t("charts.sampleAria")}>
        {bins.map((bin) => (
          <span key={bin.label} className={bin.sufficiency === "insufficient" ? "is-sparse" : ""}>
            <i style={{ height: `${Math.max(8, bin.sampleSize / maxSample * 100)}%` }} />
            <small>{bin.label}</small>
            <strong>{bin.sampleSize}</strong>
          </span>
        ))}
      </div>
      <div className="statistics-legend" aria-label={t("charts.legend")}>
        <span><i className="stats-color-reviews" />{t("charts.predicted")}</span>
        <span><i className="stats-color-success" />{t("charts.actual")}</span>
        <span><i className="fsrs-legend-ideal" />{t("charts.ideal")}</span>
        <span><i className="stats-color-again" />{t("charts.sparse")}</span>
      </div>
    </>
  );
}

export function WorkloadComparisonChart({ current, hypothetical }: { current: DailyPoint[]; hypothetical: DailyPoint[] }) {
  const { t } = useTranslation("fsrs");
  const currentByDay = new Map(current.map((point) => [point.day, point]));
  const hypotheticalByDay = new Map(hypothetical.map((point) => [point.day, point]));
  const days = [...new Set([...currentByDay.keys(), ...hypotheticalByDay.keys()])].sort((a, b) => a - b);
  const points = days.map((day) => ({
    day,
    label: t("charts.day", { day }),
    current: currentByDay.get(day)?.reviews ?? null,
    hypothetical: hypotheticalByDay.get(day)?.reviews ?? null,
  }));
  return (
    <>
      <div className="statistics-rechart fsrs-workload-comparison" role="img" aria-label={t("charts.workloadAria")}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points} margin={{ top: 12, right: 18, bottom: 8, left: 0 }}>
            <CartesianGrid vertical={false} className="statistics-chart-grid" />
            <XAxis dataKey="label" tickFormatter={(_, index) => index % Math.max(1, Math.ceil(points.length / 6)) === 0 ? `${points[index]?.day ?? ""}` : ""} tickLine={false} axisLine={false} />
            <YAxis domain={[0, "auto"]} tickLine={false} axisLine={false} width={42} />
            <Tooltip contentStyle={tooltipStyle} formatter={(value, name) => [t("charts.reviews", { count: Number(value).toLocaleString(localeForLanguage(i18n.language)) }), name === "current" ? t("charts.current") : t("charts.hypothetical")]} labelFormatter={(label) => String(label)} />
            <Line type="linear" dataKey="current" stroke="var(--text-muted)" strokeDasharray="5 5" dot={false} strokeWidth={2} connectNulls={false} isAnimationActive={false} />
            <Line type="linear" dataKey="hypothetical" stroke="var(--stats-color-reviews)" dot={false} strokeWidth={2.5} connectNulls={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="statistics-legend" aria-label={t("charts.legend")}>
        <span><i className="fsrs-legend-current" />{t("charts.current")}</span>
        <span><i className="stats-color-reviews" />{t("simulator.hypothetical")}</span>
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
  return `${new Intl.NumberFormat(localeForLanguage(i18n.language), { maximumFractionDigits: 1 }).format(value * 100)}%`;
}

function chartLabel(value: string) {
  return ({ ideal: i18n.t("charts.ideal", { ns: "fsrs" }), predicted: i18n.t("charts.predicted", { ns: "fsrs" }), actualReliable: i18n.t("charts.actual", { ns: "fsrs" }), actualSparse: i18n.t("charts.actualSparse", { ns: "fsrs" }) } as Record<string, string>)[value] || value;
}
