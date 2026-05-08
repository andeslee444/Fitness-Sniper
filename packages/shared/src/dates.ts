export const APP_TIME_ZONE = 'America/New_York';

interface DateParts {
  year: number;
  month: number;
  day: number;
}

interface ZonedDateTimeParts extends DateParts {
  hour: number;
  minute: number;
  second: number;
}

const formatterCache = new Map<string, Intl.DateTimeFormat>();

function getFormatter(timeZone: string): Intl.DateTimeFormat {
  const cached = formatterCache.get(timeZone);
  if (cached) return cached;

  const formatter = new Intl.DateTimeFormat('en-US', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hourCycle: 'h23',
  });
  formatterCache.set(timeZone, formatter);
  return formatter;
}

function parseDateString(dateStr: string): DateParts {
  const [year, month, day] = dateStr.split('-').map(Number);
  if (!year || !month || !day) {
    throw new Error(`Invalid date string: ${dateStr}`);
  }
  return { year, month, day };
}

function formatDateParts({ year, month, day }: DateParts): string {
  return [
    String(year).padStart(4, '0'),
    String(month).padStart(2, '0'),
    String(day).padStart(2, '0'),
  ].join('-');
}

function getZonedParts(date: Date, timeZone: string): ZonedDateTimeParts {
  const parts = getFormatter(timeZone).formatToParts(date);
  const values: Partial<Record<keyof ZonedDateTimeParts, number>> = {};

  for (const part of parts) {
    if (
      part.type === 'year' ||
      part.type === 'month' ||
      part.type === 'day' ||
      part.type === 'hour' ||
      part.type === 'minute' ||
      part.type === 'second'
    ) {
      values[part.type] = Number(part.value);
    }
  }

  if (
    values.year == null ||
    values.month == null ||
    values.day == null ||
    values.hour == null ||
    values.minute == null ||
    values.second == null
  ) {
    throw new Error(`Could not format date in ${timeZone}`);
  }

  return {
    year: values.year,
    month: values.month,
    day: values.day,
    hour: values.hour,
    minute: values.minute,
    second: values.second,
  };
}

function getTimeZoneOffsetMs(date: Date, timeZone: string): number {
  const parts = getZonedParts(date, timeZone);
  const localAsUtc = Date.UTC(
    parts.year,
    parts.month - 1,
    parts.day,
    parts.hour,
    parts.minute,
    parts.second,
  );
  return localAsUtc - date.getTime();
}

export function dateStringInTimeZone(
  date = new Date(),
  timeZone = APP_TIME_ZONE,
): string {
  return formatDateParts(getZonedParts(date, timeZone));
}

export function minutesSinceMidnightInTimeZone(
  date = new Date(),
  timeZone = APP_TIME_ZONE,
): number {
  const parts = getZonedParts(date, timeZone);
  return parts.hour * 60 + parts.minute;
}

export function dayOfWeekForDateString(dateStr: string): number {
  const { year, month, day } = parseDateString(dateStr);
  return new Date(Date.UTC(year, month - 1, day, 12, 0, 0)).getUTCDay();
}

export function addDaysToDateString(dateStr: string, daysToAdd: number): string {
  const { year, month, day } = parseDateString(dateStr);
  const date = new Date(Date.UTC(year, month - 1, day + daysToAdd, 12, 0, 0));
  return formatDateParts({
    year: date.getUTCFullYear(),
    month: date.getUTCMonth() + 1,
    day: date.getUTCDate(),
  });
}

export function zonedDateTimeToUtc(
  dateStr: string,
  hours: number,
  minutes: number,
  timeZone = APP_TIME_ZONE,
): Date {
  const { year, month, day } = parseDateString(dateStr);
  const localAsUtc = Date.UTC(year, month - 1, day, hours, minutes, 0, 0);

  let instant = new Date(localAsUtc);
  instant = new Date(localAsUtc - getTimeZoneOffsetMs(instant, timeZone));
  instant = new Date(localAsUtc - getTimeZoneOffsetMs(instant, timeZone));

  return instant;
}
