/**
 * Presentation helpers shared by the weather page and the dashboard summary.
 * Missing readings stay "—"; nothing is imputed.
 */

export function formatTemperature(value: number | null): string {
  return value === null ? "—" : `${Math.round(value)}°C`;
}

export function formatNumber(value: number | null, unit: string): string {
  if (value === null) {
    return "—";
  }
  const rounded = Math.round(value * 10) / 10;
  return `${rounded}${unit}`;
}

export function weekday(isoDate: string): string {
  const date = new Date(`${isoDate}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) {
    return isoDate;
  }
  return new Intl.DateTimeFormat("en-GB", {
    weekday: "short",
    timeZone: "UTC",
  }).format(date);
}

export function shortDate(isoDate: string): string {
  const date = new Date(`${isoDate}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) {
    return isoDate;
  }
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  }).format(date);
}

export function localTime(isoDateTime: string): string {
  // Open-Meteo returns the location's local wall-clock time without an offset
  // ("2026-11-06T14:15"). Show it as-is rather than shifting to the browser zone.
  const match = /T(\d{2}:\d{2})/.exec(isoDateTime);
  return match?.[1] ?? "unknown time";
}
