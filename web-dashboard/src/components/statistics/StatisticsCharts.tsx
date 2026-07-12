import { useId, type ReactNode } from "react";
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
                  <YAxis domain={[0, "auto"]} allowDataOverflow={false} tickFormatter={(value) => axisValue(value, metrics[0]?.format)} width={42} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={tooltipStyle} formatter={(value, name) => [formatValue(Number(value), metrics.find((metric) => metric.key === name)?.format), metrics.find((metric) => metric.key === name)?.label || name]} labelFormatter={(label) => String(label)} />
                  {metrics.map((metric) => <Bar key={String(metric.key)} dataKey={String(metric.key)} name={String(metric.key)} stackId={kind === "stacked" ? metric.stackId || "whole" : undefined} fill={`var(--${statisticsColorClass[metric.color]})`} radius={kind === "stacked" ? 0 : [4, 4, 0, 0]} isAnimationActive={false} />)}
                </BarChart>
              )}
            </ResponsiveContainer>
          </div>
          {sparse ? <figcaption className="statistics-sparse-note">Мало точек: график показывает только доступные значения без интерполяции.</figcaption> : null}
        </figure>
      ) : allZero ? <p className="statistics-zero-state">За выбранный период значение равно нулю. Это покрытый период, а не пропуск данных.</p> : <StatisticsEmptyState text="Для выбранного периода данных нет. Пропуски не заменены нулями." />}
      <StatisticsLegend metrics={metrics} />
      <details className="statistics-data-disclosure">
        <summary aria-controls={tableId}>Таблица данных</summary>
        <div className="statistics-table-wrap" id={tableId}>
          <table className="statistics-table" aria-labelledby={titleId}>
            <thead><tr><th>Интервал</th>{metrics.map((metric) => <th key={String(metric.key)}>{metric.label}</th>)}</tr></thead>
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
  return <div className="statistics-legend" aria-label="Обозначения графика">{metrics.map((metric) => <span key={String(metric.key)}><i className={statisticsColorClass[metric.color]} aria-hidden="true" />{metric.label}</span>)}</div>;
}

export function StatisticsEmptyState({ text }: { text: string }) {
  return <p className="statistics-empty">{text}</p>;
}

export function seriesSummary(points: StatisticsSeriesPoint[], key: keyof StatisticsSeriesPoint, label: string) {
  const values = points.map((point) => typeof point[key] === "number" ? point[key] as number : null);
  const available = values.filter((value): value is number => value != null && Number.isFinite(value));
  if (!available.length) return `${label}: данных для выбранного периода нет.`;
  if (key === "successRate") {
    return `${label}: от ${formatValue(Math.min(...available), "percent")} до ${formatValue(Math.max(...available), "percent")} по ${available.length} интервалам.`;
  }
  if (key === "averageAnswerSeconds") {
    return `${label}: от ${formatValue(Math.min(...available), "seconds")} до ${formatValue(Math.max(...available), "seconds")} по ${available.length} интервалам.`;
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
  if (format === "seconds") return `${value} с`;
  if (format === "duration") return `${Math.round(value / 60)} мин`;
  return new Intl.NumberFormat("ru-RU", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

function formatValue(value: number, format?: StatisticsChartMetric["format"]): string {
  if (!Number.isFinite(value)) return "Нет данных";
  if (format === "percent") return `${new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 1 }).format(value * 100)}%`;
  if (format === "seconds") return `${new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 1 }).format(value)} с`;
  if (format === "duration") return `${new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 1 }).format(value / 60)} мин`;
  return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 1 }).format(value);
}

function formatUnknown(value: unknown, format?: StatisticsChartMetric["format"]): string {
  return typeof value === "number" && Number.isFinite(value) ? formatValue(value, format) : "Нет данных";
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
