import { describe, expect, it } from 'vitest'
import router from '@/router'

describe('app router', () => {
  it('registers expected named routes', () => {
    const names = router.getRoutes().map((route) => route.name)
    expect(names).toEqual(
      expect.arrayContaining([
        'Landing',
        'Login',
        'Dashboard',
        'Signup',
        'CardDetail',
        'AccountDetail',
        'AccountTransfer',
        'Profile',
        'Admin',
      ]),
    )
  })

  it('defines a fallback redirect to home', () => {
    const fallback = router
      .getRoutes()
      .find((route) => route.path === '/:pathMatch(.*)*')
    expect(fallback).toBeTruthy()
    expect(fallback?.redirect).toBe('/')
  })
})
