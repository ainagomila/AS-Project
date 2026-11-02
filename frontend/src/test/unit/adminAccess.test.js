import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useUserStore } from '@/stores/user'
import router from '@/router'

describe('admin access', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('exposes the role from the profile', () => {
    const store = useUserStore()
    store.login('12345678Z', { dni: '12345678Z', role: 'admin', admin: true })
    expect([store.isAdmin, store.isAuditor, store.isStaff]).toEqual([true, false, true])

    store.login('12345678Z', { dni: '12345678Z', role: 'auditor', admin: false })
    expect([store.isAdmin, store.isAuditor, store.isStaff]).toEqual([false, true, true])

    store.login('12345678Z', { dni: '12345678Z', role: 'customer', admin: false })
    expect([store.isAdmin, store.isAuditor, store.isStaff]).toEqual([false, false, false])
  })

  it('marks the back office route as staff-only', () => {
    const admin = router.getRoutes().find((route) => route.name === 'Admin')
    expect(admin?.meta).toMatchObject({ requiresAuth: true, requiresStaff: true })
  })
})
