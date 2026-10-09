import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createPinia } from 'pinia'
import SignupView from '@/views/SignupView.vue'

const mocks = vi.hoisted(() => ({
  signupUser: vi.fn(),
  checkUserExists: vi.fn(),
  userStore: {
    login: vi.fn(),
  },
}))

const MOCK_TOKEN = '11111111-2222-3333-4444-555555555555'
vi.mock('@/api/authService', () => ({
  signupUser: mocks.signupUser,
  checkUserExists: mocks.checkUserExists,
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

async function mountSignupView() {
  const router = createTestRouter()
  await router.push('/')
  await router.isReady()

  const wrapper = mount(SignupView, {
    global: {
      plugins: [router, createPinia()],
      stubs: { RouterLink: RouterLinkStub },
    },
  })

  return { wrapper, router }
}

describe('SignupView', () => {
  beforeAll(() => {
    globalThis.alert = vi.fn()
  })

  beforeEach(() => {
    globalThis.alert.mockClear()
    mocks.signupUser.mockReset()
    mocks.checkUserExists.mockReset()
    mocks.userStore.login.mockReset()
  })

  it('warns when passwords do not match', async () => {
    const { wrapper } = await mountSignupView()
    await wrapper.get('#password').setValue('Secret12!')
    await wrapper.get('#confirmPassword').setValue('Other12!')

    await flushPromises()
    expect(wrapper.text()).toContain('Passwords do not match.')

    await wrapper.get('form').trigger('submit.prevent')

    expect(globalThis.alert).toHaveBeenCalledWith('Please fix the errors.')
    expect(mocks.signupUser).not.toHaveBeenCalled()
  })

  it('stops registration when the user already exists', async () => {
    mocks.checkUserExists.mockImplementation(async (value) => value === '12345678Z')
    vi.useFakeTimers()
    try {
      const { wrapper } = await mountSignupView()

      await wrapper.get('#name').setValue('Ada Lovelace')
      await wrapper.get('#dni').setValue('12345678Z')
      await wrapper.get('#email').setValue('ada@example.com')
      await wrapper.get('#phone').setValue('+34600111222')
      await wrapper.get('#password').setValue('Secret12!')
      await wrapper.get('#confirmPassword').setValue('Secret12!')
      await wrapper.get('#pin').setValue('123456')
      await wrapper.get('#birthday').setValue('01/02/1990')
      await wrapper.get('select').setValue('female')
      await wrapper.get('#terms').setValue(true)

      vi.runAllTimers()
      await flushPromises()

      await wrapper.get('form').trigger('submit.prevent')
      await flushPromises()

      expect(mocks.checkUserExists).toHaveBeenCalledWith('12345678Z')
      expect(wrapper.text()).toContain('This DNI is already registered.')
      expect(mocks.signupUser).not.toHaveBeenCalled()
      expect(globalThis.alert).toHaveBeenCalledWith('Please fix the errors.')
    } finally {
      vi.useRealTimers()
    }
  })

  it('registers new users and redirects to dashboard', async () => {
    mocks.checkUserExists.mockImplementation(async () => false)
    mocks.signupUser.mockResolvedValue({ token: MOCK_TOKEN })
    vi.useFakeTimers()
    try {
      const { wrapper, router } = await mountSignupView()
      const pushSpy = vi.spyOn(router, 'push')

      await wrapper.get('#name').setValue('Ada Lovelace')
      await wrapper.get('#dni').setValue('87654321X')
      await wrapper.get('#email').setValue('ada@example.com')
      await wrapper.get('#phone').setValue('+34999111222')
      await wrapper.get('#password').setValue('Secret12!')
      await wrapper.get('#confirmPassword').setValue('Secret12!')
      await wrapper.get('#pin').setValue('123456')
      await wrapper.get('#birthday').setValue('05/03/1994')
      await wrapper.get('select').setValue('female')
      await wrapper.get('#terms').setValue(true)

      vi.runAllTimers()
      await flushPromises()

      await wrapper.get('form').trigger('submit.prevent')
      await flushPromises()

      expect(mocks.signupUser).toHaveBeenCalledWith({
        name: 'Ada Lovelace',
        dni: '87654321X',
        email: 'ada@example.com',
        phone: '+34999111222',
        password: 'Secret12!',
        birthdate: '1994-03-05',
        gender: 'female',
        pin: '123456',
      })
      expect(mocks.userStore.login).toHaveBeenCalledWith('87654321X', { token: MOCK_TOKEN })
      expect(globalThis.alert).not.toHaveBeenCalled()
      expect(pushSpy).toHaveBeenCalledWith('/dashboard')
    } finally {
      vi.useRealTimers()
    }
  })
})
