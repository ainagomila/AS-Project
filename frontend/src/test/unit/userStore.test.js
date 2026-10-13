import { beforeEach, describe, expect, it, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUserStore } from '@/stores/user'

const MOCK_TOKEN = '11111111-2222-3333-4444-555555555555'

describe('user store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('logs in and persists session data', () => {
    const store = useUserStore()
    const sessionPayload = { token: MOCK_TOKEN, user: { name: 'Ada' } }

    store.login('12345678A', sessionPayload)

    expect(store.dni).toBe('12345678A')
    expect(store.token).toBe(MOCK_TOKEN)
    expect(store.userData).toEqual({ name: 'Ada' })
    expect(store.isAuthenticated).toBe(true)
    expect(localStorage.getItem('userDni')).toBe('12345678A')
    expect(localStorage.getItem('isAuthenticated')).toBe('true')
    expect(localStorage.getItem('authToken')).toBe(MOCK_TOKEN)
    expect(JSON.parse(localStorage.getItem('userData'))).toEqual({ name: 'Ada' })
  })

    it('persists session payload when backend omits nested user info', () => {
      const store = useUserStore()
      const payload = { token: MOCK_TOKEN, permissions: ['dashboard'] }

      store.login('12345678A', payload)

      expect(store.userData).toEqual(payload)
      expect(JSON.parse(localStorage.getItem('userData'))).toEqual(payload)
    })

  it('logs out and clears storage', () => {
    const store = useUserStore()
    store.login('12345678A', { token: MOCK_TOKEN, user: { name: 'Ada' } })

    store.logout()

    expect(store.dni).toBeNull()
    expect(store.token).toBeNull()
    expect(store.userData).toBeNull()
    expect(store.isAuthenticated).toBe(false)
    expect(localStorage.getItem('userDni')).toBeNull()
    expect(localStorage.getItem('isAuthenticated')).toBeNull()
    expect(localStorage.getItem('userData')).toBeNull()
    expect(localStorage.getItem('authToken')).toBeNull()
  })

  it('hydrates state from storage', () => {
    localStorage.setItem('userDni', '321')
    localStorage.setItem('isAuthenticated', 'true')
    localStorage.setItem('authToken', MOCK_TOKEN)
    localStorage.setItem('userData', JSON.stringify({ theme: 'dark' }))

    const store = useUserStore()
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    store.initFromStorage()

    expect(store.dni).toBe('321')
    expect(store.token).toBe(MOCK_TOKEN)
    expect(store.isAuthenticated).toBe(true)
    expect(store.userData).toEqual({ theme: 'dark' })
    expect(consoleSpy).not.toHaveBeenCalled()
  })

  it('ignores malformed persisted payloads but keeps session token', () => {
    localStorage.setItem('userDni', '456')
    localStorage.setItem('isAuthenticated', 'true')
    localStorage.setItem('authToken', MOCK_TOKEN)
    localStorage.setItem('userData', '{bad json')

    const store = useUserStore()
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    store.initFromStorage()

    expect(store.dni).toBe('456')
    expect(store.token).toBe(MOCK_TOKEN)
    expect(store.isAuthenticated).toBe(true)
    expect(store.userData).toBeNull()
    expect(consoleSpy).toHaveBeenCalled()
  })

    it('exposes computed getters backed by userData', () => {
      const store = useUserStore()
      const profile = {
        name: 'Marina',
        email: 'marina@test.com',
        phone: '+34600000000',
        birthday: '1990-01-01',
        gender: 'female',
        pin: '222222',
      }

      store.login('123', { token: MOCK_TOKEN, user: profile })

      expect(store.name).toBe('Marina')
      expect(store.email).toBe('marina@test.com')
      expect(store.phone).toBe('+34600000000')
      expect(store.birthday).toBe('1990-01-01')
      expect(store.gender).toBe('female')
      expect(store.pin).toBe('222222')
    })
})
