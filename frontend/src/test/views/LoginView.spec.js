import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createPinia } from 'pinia'
import LoginView from '@/views/LoginView.vue'
import ForgotPasswordModal from '@/components/modals/ForgotPasswordModal.vue'

const mocks = vi.hoisted(() => ({
  signinRedirect: vi.fn(),
}))

vi.mock('@/api/oidc', () => ({ userManager: { signinRedirect: mocks.signinRedirect } }))
vi.mock('@/api/authService', () => ({ resetPassword: vi.fn() }))
vi.mock('@/stores/user', () => ({ useUserStore: () => ({ logout: vi.fn() }) }))

async function mountAt(path) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: { template: '<div />' } },
      { path: '/login', name: 'Login', component: LoginView },
    ],
  })
  await router.push(path)
  await router.isReady()

  const wrapper = mount(LoginView, {
    global: {
      plugins: [router, createPinia()],
      stubs: { RouterLink: RouterLinkStub },
    },
  })
  await flushPromises()
  return wrapper
}

describe('LoginView', () => {
  beforeEach(() => {
    mocks.signinRedirect.mockReset()
    mocks.signinRedirect.mockResolvedValue()
  })

  it('starts the OAuth sign-in as soon as it opens', async () => {
    await mountAt('/login')

    expect(mocks.signinRedirect).toHaveBeenCalledWith({ state: { redirect: '/dashboard' } })
  })

  it('returns to the requested page after the sign-in', async () => {
    await mountAt('/login?redirect=/profile')

    expect(mocks.signinRedirect).toHaveBeenCalledWith({ state: { redirect: '/profile' } })
  })

  it('ignores redirects that leave the site', async () => {
    await mountAt('/login?redirect=//evil.example')

    expect(mocks.signinRedirect).toHaveBeenCalledWith({ state: { redirect: '/dashboard' } })
  })

  it('opens the reset modal instead of redirecting when forgot=1', async () => {
    const wrapper = await mountAt('/login?forgot=1')

    expect(mocks.signinRedirect).not.toHaveBeenCalled()
    expect(wrapper.findComponent(ForgotPasswordModal).exists()).toBe(true)
  })

  it('alerts when the sign-in cannot start', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    mocks.signinRedirect.mockRejectedValue(new Error('offline'))

    await mountAt('/login')

    expect(globalThis.alert).toHaveBeenCalledWith('Could not start the sign-in. Please try again.')
  })
})
