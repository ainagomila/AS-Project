import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AddAccountModal from '@/components/modals/AddAccountModal.vue'

describe('AddAccountModal', () => {
  it('formats IBAN as the user types', async () => {
    const wrapper = mount(AddAccountModal)
    const input = wrapper.get('[data-testid="add-account-iban-input"]')
    await input.setValue('es7921000418450200051332')
    expect(wrapper.vm.form.number).toBe('ES79 2100 0418 4502 0005 1332')
  })

  it('validates fields and prevents submission on errors', async () => {
    const wrapper = mount(AddAccountModal)
    await wrapper.get('form').trigger('submit.prevent')
    expect(wrapper.emitted('submit')).toBeUndefined()
    expect(wrapper.findAll('.err').length).toBeGreaterThan(0)
  })

  it('emits submit with cleaned payload when valid', async () => {
    const wrapper = mount(AddAccountModal)
    await wrapper.get('[data-testid="add-account-iban-input"]').setValue('ES9121000418450200051332')
    await wrapper.get('[data-testid="add-account-name-input"]').setValue('Savings')
    await wrapper.get('[data-testid="add-account-bank-input"]').setValue('Santander')
    await wrapper.get('[data-testid="add-account-currency-select"]').setValue('EUR')

    await wrapper.get('form').trigger('submit.prevent')

    const [payload] = wrapper.emitted('submit')[0]
    expect(payload).toMatchObject({
      iban: 'ES9121000418450200051332',
      name: 'Savings',
      bank: 'Santander',
      currency: 'EUR',
    })
    expect(payload).not.toHaveProperty('balance')
  })
})
