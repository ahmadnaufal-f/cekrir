import type { ScreenshotAnalysis } from '../types/api'

export interface PackageDraft {
  resiNumber: string
  courier: string
  sender: string
  products: string
}

export function fillPackageDraft(
  draft: PackageDraft,
  result: ScreenshotAnalysis,
): PackageDraft {
  const fill = (current: string, extracted: string | null) =>
    current.trim() ? current : (extracted ?? '')

  return {
    resiNumber: fill(draft.resiNumber, result.resi_number),
    courier: fill(draft.courier, result.courier_service),
    sender: fill(draft.sender, result.sender_name),
    products: fill(draft.products, result.product_names.join('\n')),
  }
}
