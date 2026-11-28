import { describe, expect, it } from 'vitest'
import { fillPackageDraft, isShopeeExpress } from './package-draft'

describe('package draft', () => {
  it.each([
    'SPX',
    'SPX Express',
    'Shopee Express',
    'Shopee Xpress',
    'Shopee Express (SPX)',
  ])('recognizes %s as the supported courier', (name) =>
    expect(isShopeeExpress(name)).toBe(true),
  )

  it('defaults an unreadable courier to SPX and leaves an unsupported courier blank for review', () => {
    const draft = { resiNumber: '', courier: '', sender: '', products: '' }
    const details = {
      resi_number: '0001',
      sender_name: null,
      product_names: [],
    }
    expect(
      fillPackageDraft(draft, { ...details, courier_service: null }).courier,
    ).toBe('spx')
    expect(
      fillPackageDraft(draft, { ...details, courier_service: 'JNE' }).courier,
    ).toBe('')
  })
  it('fills only blank fields and preserves the exact resi and manual edits', () => {
    expect(
      fillPackageDraft(
        {
          resiNumber: '',
          courier: 'Manual courier',
          sender: '',
          products: 'Manual product',
        },
        {
          resi_number: '000xY-128',
          courier_service: 'SPX Express',
          sender_name: null,
          product_names: ['First product', 'Second product'],
        },
      ),
    ).toEqual({
      resiNumber: '000xY-128',
      courier: 'Manual courier',
      sender: '',
      products: 'Manual product',
    })
  })

  it('puts extracted products on separate lines when the field is blank', () => {
    expect(
      fillPackageDraft(
        { resiNumber: 'Manual resi', courier: '', sender: '', products: '' },
        {
          resi_number: null,
          courier_service: null,
          sender_name: null,
          product_names: ['A', 'B'],
        },
      ).products,
    ).toBe('A\nB')
  })
})
