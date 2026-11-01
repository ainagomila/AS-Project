import { beforeEach, describe, expect, it } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUserStore } from '@/stores/user'

describe('user store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('logs in with the profile and keeps nothing in storage', () => {
    const store = useUserStore()

    store.login('12345678A', { name: 'Ada' })

    expect(store.dni).toBe('12345678A')
    expect(store.userData).toEqual({ name: 'Ada' })
    expect(store.isAuthenticated).toBe(true)
    expect(localStorage.length).toBe(0)
    expect(sessionStorage.length).toBe(0)
  })

  it('logs out and clears the in-memory session', () => {
    const store = useUserStore()
    store.login('12345678A', { name: 'Ada' })

    store.logout()

    expect(store.dni).toBeNull()
    expect(store.userData).toBeNull()
    expect(store.isAuthenticated).toBe(false)
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

    store.login('123', profile)

    expect(store.name).toBe('Marina')
    expect(store.email).toBe('marina@test.com')
    expect(store.phone).toBe('+34600000000')
    expect(store.birthday).toBe('1990-01-01')
    expect(store.gender).toBe('female')
    expect(store.pin).toBe('222222')
  })
})
