import { beforeEach, describe, expect, it, vi } from 'vitest'
import apiClient from '@/api/apiClient'

const mocks = vi.hoisted(() => ({ getUser: vi.fn() }))

vi.mock('@/api/oidc', () => ({ userManager: { getUser: mocks.getUser } }))

const REMOTE_BASE_URL = 'https://localhost:8080/'
const EXPECTED_BASE_URL =
  import.meta?.env?.VITE_API_BASE_URL ??
  (import.meta?.env?.DEV ? '/api' : REMOTE_BASE_URL)

function getBaseUrlHandler() {
  return apiClient.interceptors.request.handlers[0].fulfilled
}

function getAuthHandler() {
  return apiClient.interceptors.request.handlers[1].fulfilled
}

describe('apiClient', () => {
  beforeEach(() => {
    mocks.getUser.mockReset()
  })

  it('keeps axios defaults lean but preserves content-type header', () => {
    expect(apiClient.defaults.baseURL).toBeUndefined()
    expect(apiClient.defaults.headers['Content-Type']).toBe('application/json')
  })

  it('prefixes relative URLs with the API base', () => {
    const handler = getBaseUrlHandler()
    const normalizedBase = (EXPECTED_BASE_URL || '').replace(/\/+$/, '')
    const config = handler({ url: '/users' })
    expect(config.url).toBe(`${normalizedBase}/users`)
  })

  it('keeps absolute URLs untouched', () => {
    const handler = getBaseUrlHandler()
    const absoluteUrl = 'https://example.com/foo'
    const config = handler({ url: absoluteUrl })
    expect(config.url).toBe(absoluteUrl)
  })

  it('injects the in-memory access token when the user is signed in', async () => {
    mocks.getUser.mockResolvedValue({ access_token: 'abc123', expired: false })
    const config = await getAuthHandler()({ headers: {} })
    expect(config.headers.Authorization).toBe('Bearer abc123')
  })

  it('does not add authorization header without a user', async () => {
    mocks.getUser.mockResolvedValue(null)
    const config = await getAuthHandler()({ headers: {} })
    expect(config.headers.Authorization).toBeUndefined()
  })

  it('does not send an expired token', async () => {
    mocks.getUser.mockResolvedValue({ access_token: 'old', expired: true })
    const config = await getAuthHandler()({ headers: {} })
    expect(config.headers.Authorization).toBeUndefined()
  })
})
