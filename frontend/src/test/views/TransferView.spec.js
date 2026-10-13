import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import TransferView from '@/views/TransferView.vue'

const routeParams = { id: 'ES0099887766' }
const pushMock = vi.fn()

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: routeParams }),
  useRouter: () => ({ push: pushMock }),
  RouterLink: {
    name: 'RouterLinkStub',
    props: ['to'],
    template: '<a><slot /></a>',
  },
}))

const mockUserStore = {
  dni: '12345678A',
  isAuthenticated: true,
  initFromStorage: vi.fn(),
}

vi.mock('@/stores/user', () => ({
  useUserStore: () => mockUserStore,
}))

const getAccountMock = vi.fn()
const createTransferMock = vi.fn()

vi.mock('@/api/userService', () => ({
  getAccount: (...args) => getAccountMock(...args),
  createTransfer: (...args) => createTransferMock(...args),
}))

vi.mock('@/components/layout/HeaderLayout.vue', () => ({
  default: {
    name: 'HeaderLayoutStub',
    template: '<header><slot /></header>',
  },
}))

async function mountTransferView() {
  const wrapper = mount(TransferView)
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  pushMock.mockReset()
  mockUserStore.dni = '12345678A'
  mockUserStore.isAuthenticated = true
  mockUserStore.initFromStorage.mockClear()
  getAccountMock.mockReset()
  createTransferMock.mockReset()
  getAccountMock.mockResolvedValue({
    bank: 'Kofre',
    name: 'Main',
    iban: 'ES1111222233334444',
    balance: 250,
    currency: 'EUR',
  })
  createTransferMock.mockResolvedValue({ id: 'transfer-1' })
})

describe('TransferView', () => {
  it('normalises IBAN input and exposes validation status', async () => {
    const wrapper = await mountTransferView()

    const ibanInput = wrapper.get('#iban')
    await ibanInput.setValue('es12 34aa56')
    expect(wrapper.vm.form.destinationIban).toBe('ES12 34AA 56')
    expect(wrapper.vm.ibanStatus).toBe('invalid')

    await ibanInput.setValue('ES91 2100 0418 4502 0005 1332')
    expect(wrapper.vm.ibanStatus).toBe('valid')
  })

  it('prevents submitting transfers with invalid or excessive amounts', async () => {
    const wrapper = await mountTransferView()

    const amountInput = wrapper.get('#amount')
    await amountInput.setValue('9999,999')
    expect(wrapper.vm.form.amount).toBe('9999.99')
    expect(wrapper.vm.amountError).toBe('Amount exceeds available balance')

    const cta = wrapper.get('form button[type="submit"]')
    expect(cta.attributes('disabled')).toBeDefined()
  })

  it('sends sanitised payloads after confirming the PIN', async () => {
    const wrapper = await mountTransferView()

    await wrapper.get('#beneficiary').setValue('Lucia QA')
    await wrapper.get('#iban').setValue('ES91 2100 0418 4502 0005 1332')
    await wrapper.get('#amount').setValue('50.25')
    await wrapper.get('#concept').setValue('QA run')

    await wrapper.get('form').trigger('submit.prevent')
    expect(wrapper.vm.showVerify).toBe(true)

    const pinInputs = wrapper.findAll('.pin-box')
    expect(pinInputs).toHaveLength(6)
    for (let i = 0; i < pinInputs.length; i += 1) {
      await pinInputs[i].setValue(String(i + 1))
    }

    await wrapper.get('.pin-modal .btn-primary').trigger('click')
    await flushPromises()

    expect(createTransferMock).toHaveBeenCalledTimes(1)
    expect(createTransferMock).toHaveBeenCalledWith(
      '12345678A',
      routeParams.id,
      expect.objectContaining({
        beneficiary: 'Lucia QA',
        destinationIban: 'ES9121000418450200051332',
        amount: 50.25,
        currency: 'EUR',
        concept: 'QA run',
        pin: '123456',
      }),
    )

    expect(wrapper.vm.toast.open).toBe(true)
    expect(wrapper.vm.toast.text).toContain('Lucia QA')
    expect(wrapper.vm.showVerify).toBe(false)

    wrapper.vm.handleToastClose()
    expect(pushMock).toHaveBeenCalledWith(`/accounts/${routeParams.id}`)
  })
})
