import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import CallbackView from '@/views/CallbackView.vue'

const mocks = vi.hoisted(() => ({
  signinCallback: vi.fn(),
  getUser: vi.fn(),
  userStore: { login: vi.fn() },
}))

vi.mock('@/api/oidc', () => ({ userManager: { signinCallback: mocks.signinCallback } }))
vi.mock('@/api/userService', () => ({ getUser: mocks.getUser }))
vi.mock('@/stores/user', () => ({ useUserStore: () => mocks.userStore }))

function createTestRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/dashboard', component: { template: '<div />' } },
      { path: '/profile', component: { template: '<div />' } },
      { path: '/callback', component: CallbackView },
    ],
  })
}

describe('CallbackView', () => {
  beforeEach(() => {
    mocks.signinCallback.mockReset()
    mocks.getUser.mockReset()
    mocks.userStore.login.mockReset()
  })

  it('stores the profile and returns to the page that started the login', async () => {
    mocks.signinCallback.mockResolvedValue({
      profile: { dni: '12345678Z' },
      state: { redirect: '/profile' },
    })
    mocks.getUser.mockResolvedValue({ dni: '12345678Z', name: 'Ana' })

    const router = createTestRouter()
    await router.push('/callback')
    await router.isReady()
    mount(CallbackView, { global: { plugins: [router] } })
    await flushPromises()

    expect(mocks.userStore.login).toHaveBeenCalledWith('12345678Z', {
      dni: '12345678Z',
      name: 'Ana',
    })
    expect(router.currentRoute.value.path).toBe('/profile')
  })

  it('goes home when the sign-in fails', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    mocks.signinCallback.mockRejectedValue(new Error('bad code'))

    const router = createTestRouter()
    await router.push('/callback')
    await router.isReady()
    mount(CallbackView, { global: { plugins: [router] } })
    await flushPromises()

    expect(mocks.userStore.login).not.toHaveBeenCalled()
    expect(router.currentRoute.value.path).toBe('/')
  })
})