import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import CardsSection from '@/components/dashboard/CardsSection.vue'

async function mountComponent(props) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: { template: '<div />' } },
      { path: '/card/:id', name: 'CardDetail', component: { template: '<div />' } },
    ],
  })
  await router.push('/')
  await router.isReady()

  const wrapper = mount(CardsSection, {
    props,
    global: {
      plugins: [router],
    },
  })

  return { wrapper, router }
}

describe('CardsSection', () => {
  const accounts = [
    { id: 'acc-1', name: 'Daily Account' },
    { id: 'acc-2', name: 'Savings' },
  ]
  const cards = [
    { id: 'card-1', type: 'DEBIT', last4: '9876', accountId: 'acc-1', bank: 'Test Bank' },
  ]

  it('renders card details including formatted number and account name', async () => {
    const { wrapper } = await mountComponent({ accounts, cards })
    const cardItem = wrapper.get('.card-item')
    expect(cardItem.text()).toContain('DEBIT')
    expect(cardItem.text()).toContain('Daily Account')
    expect(cardItem.text()).toContain('Test Bank')
    expect(cardItem.text()).toContain('••••')
    expect(cardItem.text()).toContain('9876')
  })

  it('emits add-card when button clicked', async () => {
    const { wrapper } = await mountComponent({ accounts, cards })
    await wrapper.find('button.add-card').trigger('click')
    expect(wrapper.emitted('add-card')).toBeTruthy()
  })

  it('pushes card detail route on click', async () => {
    const { wrapper, router } = await mountComponent({ accounts, cards })
    const pushSpy = vi.spyOn(router, 'push')
    await wrapper.get('.card-item').trigger('click')
    expect(pushSpy).toHaveBeenCalledWith({ name: 'CardDetail', params: { id: 'card-1' } })
  })
})
