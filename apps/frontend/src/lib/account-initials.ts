export function accountInitials(name?: string | null): string {
  return (
    name
      ?.trim()
      .split(/\s+/)
      .map((part) => part.match(/\p{L}\p{M}*/u)?.[0])
      .filter(Boolean)
      .slice(0, 2)
      .join('')
      .toUpperCase() ?? ''
  )
}
