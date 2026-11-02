import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useUserStore } from '@/stores/user'
import router from '@/router'

describe('admin access', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('exposes the admin flag from the login payload', () => {
    const store = useUserStore()
    store.login('12345678Z', { token: 't', user: { dni: '12345678Z', admin: true } })
    expect(store.isAdmin).toBe(true)

    store.login('12345678Z', { token: 't', user: { dni: '12345678Z', admin: false } })
    expect(store.isAdmin).toBe(false)
  })

  it('derives the role from the login payload', () => {
    const store = useUserStore()
    store.login('12345678Z', { token: 't', user: { dni: '12345678Z', role: 'ADMIN' } })
    expect(store.isAdmin).toBe(true)
    expect(store.isStaff).toBe(true)

    store.login('12345678Z', { token: 't', user: { dni: '12345678Z', role: 'AUDITOR' } })
    expect(store.isAdmin).toBe(false)
    expect(store.isStaff).toBe(true)

    store.login('12345678Z', { token: 't', user: { dni: '12345678Z', role: 'USER' } })
    expect(store.isAdmin).toBe(false)
    expect(store.isStaff).toBe(false)
  })

  it('marks the admin route as staff-only', () => {
    const admin = router.getRoutes().find((route) => route.name === 'Admin')
    expect(admin?.meta).toMatchObject({ requiresAuth: true, requiresStaff: true })
  })
})
