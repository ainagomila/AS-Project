import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import BankAccounts from '@/components/dashboard/BankAccounts.vue'

async function mountComponent(props = {}) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: { template: '<div />' } },
      { path: '/accounts/:id', name: 'AccountDetail', component: { template: '<div />' } },
    ],
  })
  await router.push('/')
  await router.isReady()

  const wrapper = mount(BankAccounts, {
    props,
    global: {
      plugins: [router],
    },
  })

  return { wrapper, router }
}

describe('BankAccounts', () => {
  const accounts = [
    { id: 'acc-1', bank: 'Test Bank', name: 'Main', number: 'ES00', balance: 'Ôé¼1.23' },
    { id: 'acc-2', bank: 'Another Bank', name: 'Spare', number: 'ES01', balance: 'Ôé¼0.00' },
  ]

  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders each provided account', async () => {
    const { wrapper } = await mountComponent({ accounts })
    const cards = wrapper.findAll('.account-card')
    expect(cards).toHaveLength(2)
    expect(cards[0].text()).toContain('Test Bank')
  })

  it('emits add-account when the button is clicked', async () => {
    const { wrapper } = await mountComponent({ accounts })
    await wrapper.find('button.add-account').trigger('click')
    expect(wrapper.emitted('add-account')).toBeTruthy()
  })

  it('navigates to account detail when a card is clicked', async () => {
    const { wrapper, router } = await mountComponent({ accounts })
    const pushSpy = vi.spyOn(router, 'push')
    await wrapper.findAll('.account-card')[0].trigger('click')
    expect(pushSpy).toHaveBeenCalledWith({ name: 'AccountDetail', params: { id: 'acc-1' } })
  })
})
