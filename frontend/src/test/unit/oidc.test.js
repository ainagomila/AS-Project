import { describe, it, expect } from 'vitest'
import { userManager } from '@/api/oidc'

describe('oidc config', () => {
  it('uses the public PKCE client and does not renew silently', () => {
    const s = userManager.settings
    expect(s.client_id).toBe('kofre-web')
    expect(s.response_type).toBe('code')
    expect(s.scope).toBe('openid banking')
    expect(s.redirect_uri).toMatch(/\/callback$/)
    expect(s.automaticSilentRenew).toBe(false)
  })
})