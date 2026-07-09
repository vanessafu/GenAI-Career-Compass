export const MONTH_LABELS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

/** Treat empty / placeholder dash values as blank. */
function cleanDate(value: string | undefined): string {
  const trimmed = value?.trim() ?? "";
  return trimmed && trimmed !== "\u2014" ? trimmed : "";
}

/** Render a `YYYY-MM` value as a friendly "Mar 2024" label, or the raw value. */
export function formatMonthLabel(value: string): string {
  const match = value.trim().match(/^(\d{4})-(\d{2})$/);
  if (!match) return value.trim();
  const monthIndex = Number(match[2]) - 1;
  const month = MONTH_LABELS[monthIndex] ?? match[2];
  return `${month} ${match[1]}`;
}

/** Join a start/end month range with a single dash, skipping empty parts. */
export function formatRange(start: string, end: string, endFallback = ""): string {
  const s = cleanDate(start);
  const e = cleanDate(end);
  const startLabel = s ? formatMonthLabel(s) : "";
  const endLabel = e ? formatMonthLabel(e) : endFallback;
  if (startLabel && endLabel) return `${startLabel} \u2013 ${endLabel}`;
  return startLabel || endLabel;
}

/** True when both dates are set and the start is after the end. */
export function isMonthRangeInvalid(start: string, end: string): boolean {
  const s = cleanDate(start);
  const e = cleanDate(end);
  return Boolean(s && e && s > e);
}
