import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createPinia } from 'pinia'
import LoginView from '@/views/LoginView.vue'

const mocks = vi.hoisted(() => ({
  loginUser: vi.fn(),
  userStore: {
    login: vi.fn(),
  },
}))

const MOCK_TOKEN = '11111111-2222-3333-4444-555555555555'
vi.mock('@/api/authService', () => ({
  loginUser: mocks.loginUser,
}))

vi.mock('@/stores/user', () => ({
  useUserStore: () => mocks.userStore,
}))

function createTestRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: { template: '<div />' } },
      { path: '/dashboard', name: 'Dashboard', component: { template: '<div />' } },
    ],
  })
}

describe('LoginView', () => {
  beforeEach(() => {
    mocks.loginUser.mockReset()
    mocks.userStore.login.mockReset()
  })

  it('requires credentials before attempting login', async () => {
    const router = createTestRouter()
    await router.push('/')
    await router.isReady()

    const wrapper = mount(LoginView, {
      global: {
        plugins: [router, createPinia()],
        stubs: { RouterLink: RouterLinkStub },
      },
    })

    await wrapper.get('form').trigger('submit.prevent')

    expect(mocks.loginUser).not.toHaveBeenCalled()
    expect(globalThis.alert).toHaveBeenCalledWith('Please enter your credentials')
  })

  it('logs in and redirects on success', async () => {
    const router = createTestRouter()
    await router.push('/')
    await router.isReady()
    const pushSpy = vi.spyOn(router, 'push')

    mocks.loginUser.mockResolvedValue({ token: MOCK_TOKEN })

    const wrapper = mount(LoginView, {
      global: {
        plugins: [router, createPinia()],
        stubs: { RouterLink: RouterLinkStub },
      },
    })

    await wrapper.findAll('input')[0].setValue(' 12345678A ')
    await wrapper.findAll('input')[1].setValue('secret')

    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    expect(mocks.loginUser).toHaveBeenCalledWith('12345678A', 'secret')
    expect(mocks.userStore.login).toHaveBeenCalledWith('12345678A', { token: MOCK_TOKEN })
    expect(pushSpy).toHaveBeenCalledWith('/dashboard')
    expect(globalThis.alert).not.toHaveBeenCalled()
  })

  it('shows backend error messages when login fails', async () => {
    const router = createTestRouter()
    await router.push('/')
    await router.isReady()

    mocks.loginUser.mockRejectedValue({ response: { data: { message: 'Invalid credentials' } } })

    const wrapper = mount(LoginView, {
      global: {
        plugins: [router, createPinia()],
        stubs: { RouterLink: RouterLinkStub },
      },
    })

    await wrapper.findAll('input')[0].setValue('12345678A')
    await wrapper.findAll('input')[1].setValue('secret')

    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    expect(globalThis.alert).toHaveBeenCalledWith('Invalid credentials')
  })
})
