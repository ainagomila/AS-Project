import { mount, flushPromises } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '@/App.vue'

const mocks = vi.hoisted(() => ({
  handlers: {},
  signinSilent: vi.fn(),
  signoutRedirect: vi.fn(),
}))

vi.mock('@/api/oidc', () => ({
  userManager: {
    signinSilent: mocks.signinSilent,
    signoutRedirect: mocks.signoutRedirect,
    events: {
      addAccessTokenExpiring: (cb) => {
        mocks.handlers.expiring = cb
      },
      addAccessTokenExpired: (cb) => {
        mocks.handlers.expired = cb
      },
      removeAccessTokenExpiring: vi.fn(),
      removeAccessTokenExpired: vi.fn(),
    },
  },
}))

const mountApp = () => mount(App, { global: { stubs: { RouterView: true } } })
const button = (wrapper, label) => wrapper.findAll('button').find((b) => b.text() === label)

describe('session expiry warning', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    mocks.signinSilent.mockReset()
    mocks.signoutRedirect.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('warns with a 60 second countdown when the token is about to expire', async () => {
    const wrapper = mountApp()
    expect(wrapper.text()).not.toContain('about to expire')

    mocks.handlers.expiring()
    await flushPromises()

    expect(wrapper.text()).toContain('about to expire')
    expect(wrapper.text()).toContain('60 seconds')
  })

  it('renews the tokens and closes the warning when the user extends', async () => {
    mocks.signinSilent.mockResolvedValue({})
    const wrapper = mountApp()
    mocks.handlers.expiring()
    await flushPromises()

    await button(wrapper, 'Extend session').trigger('click')
    await flushPromises()

    expect(mocks.signinSilent).toHaveBeenCalledTimes(1)
    expect(mocks.signoutRedirect).not.toHaveBeenCalled()
    expect(wrapper.text()).not.toContain('about to expire')
  })

  it('signs out when the user declines', async () => {
    const wrapper = mountApp()
    mocks.handlers.expiring()
    await flushPromises()

    await button(wrapper, 'Log out').trigger('click')

    expect(mocks.signoutRedirect).toHaveBeenCalledTimes(1)
    expect(mocks.signinSilent).not.toHaveBeenCalled()
  })

  it('signs out once when nobody answers within the minute', async () => {
    mountApp()
    mocks.handlers.expiring()
    await flushPromises()

    vi.advanceTimersByTime(60_000)
    mocks.handlers.expired()

    expect(mocks.signoutRedirect).toHaveBeenCalledTimes(1)
  })

  it('signs out when the renewal fails', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    mocks.signinSilent.mockRejectedValue(new Error('refresh token expired'))
    const wrapper = mountApp()
    mocks.handlers.expiring()
    await flushPromises()

    await button(wrapper, 'Extend session').trigger('click')
    await flushPromises()

    expect(mocks.signoutRedirect).toHaveBeenCalledTimes(1)
  })
})
