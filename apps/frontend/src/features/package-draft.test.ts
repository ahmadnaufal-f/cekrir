import { describe, expect, it } from 'vitest'
import { fillPackageDraft } from './package-draft'

describe('package draft', () => {
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
