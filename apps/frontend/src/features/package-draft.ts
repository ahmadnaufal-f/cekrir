import type { ScreenshotAnalysis } from '../types/api'

export interface PackageDraft {
  resiNumber: string
  courier: string
  sender: string
  products: string
}

export const indonesiaCouriers = [
  { code: 'spx', name: 'Shopee Express (SPX)' },
  { code: 'jne', name: 'JNE' },
  { code: 'jnt', name: 'J&T Express' },
  { code: 'sicepat', name: 'SiCepat Ekspres' },
  { code: 'pos', name: 'Pos Indonesia' },
  { code: 'anteraja', name: 'Anteraja' },
  { code: 'ninja', name: 'Ninja Xpress' },
  { code: 'lion', name: 'Lion Parcel' },
  { code: 'tiki', name: 'TIKI' },
  { code: 'ide', name: 'ID Express' },
  { code: 'wahana', name: 'Wahana' },
]

export function courierName(code: string) {
  return (
    indonesiaCouriers.find((courier) => courier.code === code)?.name ??
    code.toUpperCase()
  )
}

export function isShopeeExpress(name: string) {
  const normalized = name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
  return /^(spx|shopee e?xpress)( |$)/.test(normalized)
}

export function fillPackageDraft(
  draft: PackageDraft,
  result: ScreenshotAnalysis,
): PackageDraft {
  const fill = (current: string, extracted: string | null) =>
    current.trim() ? current : (extracted ?? '')

  return {
    resiNumber: fill(draft.resiNumber, result.resi_number),
    courier: fill(
      draft.courier,
      !result.courier_service || isShopeeExpress(result.courier_service)
        ? 'spx'
        : null,
    ),
    sender: fill(draft.sender, result.sender_name),
    products: fill(draft.products, result.product_names.join('\n')),
  }
}
