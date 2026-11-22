/** Format a Date as its calendar day in an IANA time zone (YYYY-MM-DD). */
export function getCalendarDate(date: Date, timeZone: string): string {
  if (!Number.isFinite(date.getTime())) {
    throw new RangeError('Cannot format an invalid date.')
  }

  const parts = new Intl.DateTimeFormat('en-US-u-ca-iso8601-nu-latn', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(date)
  const values = Object.fromEntries(
    parts.map(({ type, value }) => [type, value]),
  )

  return `${values.year}-${values.month}-${values.day}`
}
