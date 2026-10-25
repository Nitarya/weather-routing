import dayjs from "dayjs";

const formatter = (options) => new Intl.DateTimeFormat("en-US", options);

export function formatClock(iso) {
  return formatter({ hour: "numeric", minute: "2-digit" }).format(new Date(iso));
}

export function formatClockWithZone(iso) {
  return formatter({
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  }).format(new Date(iso));
}

export function formatDayClock(iso) {
  return formatter({
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(iso));
}

export function formatDay(iso) {
  return formatter({ weekday: "short", month: "short", day: "numeric" }).format(
    new Date(iso),
  );
}

export function formatDuration(minutes) {
  const rounded = Math.max(1, Math.round(minutes));
  const hours = Math.floor(rounded / 60);
  const mins = rounded % 60;
  if (hours === 0) return `${mins}m`;
  if (mins === 0) return `${hours}h`;
  return `${hours}h ${mins}m`;
}

export function formatMiles(value, digits = 0) {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
}

export function formatWeight(value) {
  return new Intl.NumberFormat("en-US").format(Math.round(value));
}

export function parseDateTime(value) {
  const date = dayjs(value);
  return date.isValid() ? date.toDate() : null;
}

export function toIso(departureLocal) {
  const date = parseDateTime(departureLocal);
  return date ? date.toISOString() : new Date().toISOString();
}

export function relativeHourLabel(hour) {
  if (hour === 0) return "Departure";
  return `+${hour}h`;
}
