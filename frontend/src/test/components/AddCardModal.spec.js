import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import AddCardModal from '@/components/modals/AddCardModal.vue'

describe('AddCardModal', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2025-01-15T12:00:00Z'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('normalises card number formatting as the user types', async () => {
    const wrapper = mount(AddCardModal)
    const input = wrapper.get('[data-testid="add-card-number-input"]')
    await input.setValue('1234567890123456')
    expect(wrapper.vm.form.cardNumber).toBe('1234 5678 9012 3456')
  })

  it('shows validation errors when fields are missing', async () => {
    const wrapper = mount(AddCardModal, {
      props: {
        accounts: [{ id: 'acc-1', name: 'Main', number: 'ES00' }],
      },
    })
    await wrapper.get('form').trigger('submit.prevent')
    expect(wrapper.emitted('submit')).toBeUndefined()
    expect(wrapper.findAll('.err').length).toBeGreaterThan(0)
  })

  it('emits submit with generated card data when valid', async () => {
    const wrapper = mount(AddCardModal, {
      props: {
        accounts: [{ iban: 'ES00', name: 'Main', bank: 'Test Bank' }],
      },
    })

    await wrapper.get('[data-testid="add-card-number-input"]').setValue('1234567890123456')
    await wrapper.get('[data-testid="add-card-pin-input"]').setValue('1234')
    await wrapper.get('[data-testid="add-card-cvv-input"]').setValue('410')
    await wrapper.get('[data-testid="add-card-expire-month-input"]').setValue('01')
    await wrapper.get('[data-testid="add-card-expire-year-input"]').setValue('30')
    await wrapper.get('[data-testid="add-card-type-select"]').setValue('DEBIT')
    await wrapper.get('[data-testid="add-card-account-select"]').setValue('ES00')

    await wrapper.get('form').trigger('submit.prevent')

    const emitted = wrapper.emitted('submit')
    expect(emitted).toBeTruthy()
    const payload = emitted[0][0]
    expect(payload).toMatchObject({
      iban: 'ES00',
      body: {
        pan: '1234567890123456',
        pin: '1234',
        cvv: '410',
        expireDate: '01/30',
        type: 'DEBIT',
        bank: 'Test Bank',
        alias: null,
      },
    })
  })
})
