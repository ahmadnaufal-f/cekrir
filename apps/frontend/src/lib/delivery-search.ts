/** Normalize user search input and delivery fields before literal matching. */
export function normalizeDeliverySearch(query: string): string {
  return query
    .normalize('NFKC')
    .trim()
    .toLocaleLowerCase('en-US')
    .split(/\s+/u)
    .filter(Boolean)
    .join(' ')
}
