// Backend timestamps without an offset are UTC; format only at the UI boundary.
export function parseTimestamp(value: string | Date): Date {
  if (value instanceof Date) return value;
  const normalized = /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}/.test(value) &&
    !/(Z|[+-]\d{2}:?\d{2})$/i.test(value) ? value.replace(" ", "T") + "Z" : value;
  return new Date(normalized);
}

export function formatAge(value: string | null | undefined): string {
  if (!value) return "-";
  return /^\d{4}-\d{2}-\d{2}[T ]/.test(value) ? formatDateTime(value) : value;
}

export function formatDateTime(
  value: string | Date | null | undefined,
): string {
  if (!value) {
    return "-";
  }

  const date =
    value instanceof Date
      ? value
      : parseTimestamp(value);

  if (
    Number.isNaN(
      date.getTime(),
    )
  ) {
    return "-";
  }

  return new Intl.DateTimeFormat(
    "en-IN",
    {
      timeZone: "Asia/Kolkata",
      dateStyle: "medium",
      timeStyle: "medium",
      hour12: true,
    },
  ).format(date) + " IST";
}


export function formatDate(
  value: string | Date | null | undefined,
): string {
  if (!value) {
    return "-";
  }

  const date =
    value instanceof Date
      ? value
      : parseTimestamp(value);

  if (
    Number.isNaN(
      date.getTime(),
    )
  ) {
    return "-";
  }

  return new Intl.DateTimeFormat(
    "en-IN",
    {
      timeZone: "Asia/Kolkata",
      dateStyle: "medium",
    },
  ).format(date) + " IST";
}


export function formatTime(
  value: string | Date | null | undefined,
): string {
  if (!value) {
    return "-";
  }

  const date =
    value instanceof Date
      ? value
      : parseTimestamp(value);

  if (
    Number.isNaN(
      date.getTime(),
    )
  ) {
    return "-";
  }

  return new Intl.DateTimeFormat(
    "en-IN",
    {
      timeZone: "Asia/Kolkata",
      timeStyle: "medium",
      hour12: true,
    },
  ).format(date) + " IST";
}