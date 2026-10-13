import { beforeEach, describe, expect, it } from 'vitest'
import apiClient from '@/api/apiClient'

const REMOTE_BASE_URL = 'http://localhost:8080/'
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
    localStorage.clear()
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

  it('injects bearer token when present', () => {
    localStorage.setItem('authToken', 'abc123')
    const handler = getAuthHandler()
    const config = handler({ headers: {} })
    expect(config.headers.Authorization).toBe('Bearer abc123')
  })

  it('does not add authorization header when token missing', () => {
    localStorage.removeItem('authToken')
    const handler = getAuthHandler()
    const config = handler({ headers: {} })
    expect(config.headers.Authorization).toBeUndefined()
  })
})
