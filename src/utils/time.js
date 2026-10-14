/** Database timestamps are UTC; the lab operates on Indian Standard Time. */
export function parseTimestamp(value) {
  const text = String(value ?? '')
  const normalized = /^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}/.test(text) && !/(?:Z|[+-]\d{2}:\d{2})$/i.test(text)
    ? text.replace(' ', 'T') + 'Z'
    : text
  return new Date(normalized)
}

export const LAB_TIME_ZONE = 'Asia/Kolkata'
