import { useId, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { StatisticsSeriesPoint } from "../../types/report";
import i18n from "../../i18n";
import { localeForLanguage } from "../../i18n/language";
import { describeSeries, statisticsColorClass, type StatisticsSemanticColor } from "./statisticsPresentation";

export interface StatisticsChartMetric {
  key: keyof StatisticsSeriesPoint | string;
  label: string;
  color: StatisticsSemanticColor;
  format?: "number" | "percent" | "seconds" | "duration";
  stackId?: string;
}

interface StatisticsChartPanelProps {
  title: string;
  description: string;
  summary: string;
  points: Array<StatisticsSeriesPoint | Record<string, unknown>>;
  metrics: StatisticsChartMetric[];
  kind: "line" | "bar" | "stacked";
  compact?: boolean;
  aside?: ReactNode;
  testId?: string;
}

export function StatisticsChartPanel({
  title,
  description,
  summary,
  points,
  metrics,
  kind,
  compact = false,
  aside,
  testId,
}: StatisticsChartPanelProps) {
  const { t } = useTranslation("statistics");
  const id = useId().replace(/:/g, "");
  const titleId = `statistics-chart-title-${id}`;
  const summaryId = `statistics-chart-summary-${id}`;
  const tableId = `statistics-chart-table-${id}`;
  const availableValues = points.flatMap((point) => metrics.map((metric) => (point as Record<string, unknown>)[String(metric.key)]).filter((value): value is number => numeric(value)));
  const hasData = availableValues.length > 0;
  const allZero = hasData && availableValues.every((value) => value === 0);
  const sparse = points.length <= 1;

  return (
    <section className={`statistics-panel statistics-chart-panel${compact ? " is-compact" : ""}`} data-testid={testId} data-chart-kind={kind}>
      <header className="statistics-panel-header">
        <div>
          <h2 id={titleId}>{title}</h2>
          <p>{description}</p>
        </div>
        {aside}
      </header>
      <p id={summaryId} className="statistics-chart-summary">{summary}</p>
      {hasData && !allZero ? (
        <figure aria-labelledby={titleId} aria-describedby={summaryId}>
          <div className="statistics-rechart" data-axis-origin={kind === "bar" || kind === "stacked" ? "zero" : "bounded"}>
            <ResponsiveContainer width="100%" height="100%">
              {kind === "line" ? (
                <LineChart data={points} margin={{ top: 12, right: 12, bottom: 8, left: 0 }}>
                  <CartesianGrid vertical={false} className="statistics-chart-grid" />
                  <XAxis dataKey="label" tickFormatter={shortLabel} minTickGap={24} tickLine={false} axisLine={false} />
                  <YAxis domain={axisDomain(metrics)} tickFormatter={(value) => axisValue(value, metrics[0]?.format)} width={42} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={tooltipStyle} formatter={(value, name) => [formatValue(Number(value), metrics.find((metric) => metric.key === name)?.format), metrics.find((metric) => metric.key === name)?.label || name]} labelFormatter={(label) => String(label)} />
                  {metrics.map((metric) => <Line key={String(metric.key)} type="linear" dataKey={String(metric.key)} name={String(metric.key)} stroke={`var(--${statisticsColorClass[metric.color]})`} strokeWidth={2.5} dot={{ r: 3, strokeWidth: 2 }} activeDot={{ r: 5 }} connectNulls={false} isAnimationActive={false} />)}
                </LineChart>
              ) : (
                <BarChart data={points} margin={{ top: 12, right: 12, bottom: 8, left: 0 }}>
                  <CartesianGrid vertical={false} className="statistics-chart-grid" />
                  <XAxis dataKey="label" tickFormatter={shortLabel} minTickGap={20} tickLine={false} axisLine={false} />
                  <YAxis
                    domain={[0, "auto"]}
                    allowDataOverflow={false}
                    allowDecimals={metrics.some((metric) => metric.format === "percent")}
                    tickFormatter={(value) => axisValue(value, metrics[0]?.format)}
                    width={42}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip contentStyle={tooltipStyle} formatter={(value, name) => [formatValue(Number(value), metrics.find((metric) => metric.key === name)?.format), metrics.find((metric) => metric.key === name)?.label || name]} labelFormatter={(label) => String(label)} />
                  {metrics.map((metric) => <Bar key={String(metric.key)} dataKey={String(metric.key)} name={String(metric.key)} stackId={kind === "stacked" ? metric.stackId || "whole" : undefined} fill={`var(--${statisticsColorClass[metric.color]})`} radius={kind === "stacked" ? 0 : [4, 4, 0, 0]} isAnimationActive={false} />)}
                </BarChart>
              )}
            </ResponsiveContainer>
          </div>
          {sparse ? <figcaption className="statistics-sparse-note">{t("chart.sparse")}</figcaption> : null}
        </figure>
      ) : allZero ? <p className="statistics-zero-state">{t("chart.zero")}</p> : <StatisticsEmptyState text={t("chart.empty")} />}
      <StatisticsLegend metrics={metrics} />
      <details className="statistics-data-disclosure">
        <summary aria-controls={tableId}>{t("chart.dataTable")}</summary>
        <div className="statistics-table-wrap" id={tableId}>
          <table className="statistics-table" aria-labelledby={titleId}>
            <thead><tr><th>{t("chart.interval")}</th>{metrics.map((metric) => <th key={String(metric.key)}>{metric.label}</th>)}</tr></thead>
            <tbody>{points.map((point, index) => {
              const record = point as Record<string, unknown>;
              return <tr key={String(record.key ?? index)}><th>{String(record.label ?? "—")}</th>{metrics.map((metric) => <td key={String(metric.key)}>{formatUnknown(record[String(metric.key)], metric.format)}</td>)}</tr>;
            })}</tbody>
          </table>
        </div>
      </details>
    </section>
  );
}

export function StatisticsLegend({ metrics }: { metrics: StatisticsChartMetric[] }) {
  const { t } = useTranslation("statistics");
  return <div className="statistics-legend" aria-label={t("chart.legend")}>{metrics.map((metric) => <span key={String(metric.key)}><i className={statisticsColorClass[metric.color]} aria-hidden="true" />{metric.label}</span>)}</div>;
}

export function StatisticsEmptyState({ text }: { text: string }) {
  return <p className="statistics-empty">{text}</p>;
}

export function seriesSummary(points: StatisticsSeriesPoint[], key: keyof StatisticsSeriesPoint, label: string) {
  const values = points.map((point) => typeof point[key] === "number" ? point[key] as number : null);
  const available = values.filter((value): value is number => value != null && Number.isFinite(value));
  if (!available.length) return i18n.t("series.noData", { ns: "statistics", label });
  if (key === "successRate") {
    return i18n.t("series.range", { ns: "statistics", label, min: formatValue(Math.min(...available), "percent"), max: formatValue(Math.max(...available), "percent"), count: available.length });
  }
  if (key === "averageAnswerSeconds") {
    return i18n.t("series.range", { ns: "statistics", label, min: formatValue(Math.min(...available), "seconds"), max: formatValue(Math.max(...available), "seconds"), count: available.length });
  }
  return describeSeries(values, label);
}

function numeric(value: unknown): boolean {
  return typeof value === "number" && Number.isFinite(value);
}

function axisDomain(metrics: StatisticsChartMetric[]): [number | "auto", number | "auto"] {
  return metrics.some((metric) => metric.format === "percent") ? [0, 1] : [0, "auto"];
}

function axisValue(value: number, format?: StatisticsChartMetric["format"]): string {
  if (format === "percent") return `${Math.round(value * 100)}%`;
  if (format === "seconds") return i18n.t("units.secondsShort", { ns: "common", value });
  if (format === "duration") return i18n.t("units.minutesShort", { ns: "common", value: Math.round(value / 60) });
  return new Intl.NumberFormat(localeForLanguage(i18n.resolvedLanguage || i18n.language), { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

function formatValue(value: number, format?: StatisticsChartMetric["format"]): string {
  if (!Number.isFinite(value)) return i18n.t("state.noData", { ns: "common" });
  const locale = localeForLanguage(i18n.resolvedLanguage || i18n.language);
  if (format === "percent") return new Intl.NumberFormat(locale, { style: "percent", maximumFractionDigits: 1 }).format(value);
  const formatted = new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(format === "duration" ? value / 60 : value);
  if (format === "seconds") return i18n.t("units.secondsShort", { ns: "common", value: formatted });
  if (format === "duration") return i18n.t("units.minutesShort", { ns: "common", value: formatted });
  return formatted;
}

function formatUnknown(value: unknown, format?: StatisticsChartMetric["format"]): string {
  return typeof value === "number" && Number.isFinite(value) ? formatValue(value, format) : i18n.t("state.noData", { ns: "common" });
}

function shortLabel(value: unknown): string {
  const label = String(value ?? "");
  return label.length > 12 ? label.slice(-10) : label;
}

const tooltipStyle = {
  border: "1px solid var(--border-strong)",
  borderRadius: "10px",
  background: "var(--surface-2)",
  color: "var(--text-primary)",
  fontSize: "12px",
};
