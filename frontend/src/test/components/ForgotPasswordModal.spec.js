import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ForgotPasswordModal from '@/components/modals/ForgotPasswordModal.vue'

describe('ForgotPasswordModal', () => {
  function mountModal() {
    return mount(ForgotPasswordModal, {
      props: {
        saving: false,
      },
    })
  }

  it('keeps the submit button disabled until the form is valid', async () => {
    const wrapper = mountModal()

    const submit = wrapper.get('button[type="submit"]')
    expect(submit.attributes('disabled')).toBeDefined()

    await wrapper.get('input[placeholder="12345678A"]').setValue('12345678A')
    await wrapper.findAll('input[placeholder="••••••••"]')[0].setValue('Aa1!aa')
    await wrapper.findAll('input[placeholder="••••••••"]')[1].setValue('Aa1!aa')
    await wrapper.get('input[placeholder="••••••"]').setValue('123456')

    expect(submit.attributes('disabled')).toBeUndefined()
  })

  it('shows validation messages for invalid fields as the user types', async () => {
    const wrapper = mountModal()

    await wrapper.get('input[placeholder="12345678A"]').setValue('INVALID')
    await wrapper.findAll('input[placeholder="••••••••"]')[0].setValue('short')
    await wrapper.findAll('input[placeholder="••••••••"]')[1].setValue('differs')
    await wrapper.get('input[placeholder="••••••"]').setValue('123')

    expect(wrapper.text()).toContain('Invalid DNI format')
    expect(wrapper.text()).toContain('At least 8 characters.')
    expect(wrapper.text()).toContain('Passwords do not match')
    expect(wrapper.text()).toContain('PIN must be 6 digits')
  })

  it('emits submit with sanitized payload when the form is valid', async () => {
    const wrapper = mountModal()

    await wrapper.get('input[placeholder="12345678A"]').setValue('12345678A')
    await wrapper.findAll('input[placeholder="••••••••"]')[0].setValue('Aa1!aa!')
    await wrapper.findAll('input[placeholder="••••••••"]')[1].setValue('Aa1!aa!')
    await wrapper.get('input[placeholder="••••••"]').setValue('654321')

    await wrapper.get('form').trigger('submit.prevent')

    expect(wrapper.emitted('submit')[0][0]).toEqual({
      dni: '12345678A',
      newPassword: 'Aa1!aa!',
      pin: '654321',
    })
  })
})
