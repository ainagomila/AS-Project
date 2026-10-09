import { describe, expect, it, vi, beforeEach } from 'vitest'
import apiClient from '@/api/apiClient'
import {
  checkUserExists,
  loginUser,
  logoutSession,
  signupUser,
  validateSession,
} from '@/api/authService'

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}))

const MOCK_TOKEN = '11111111-2222-3333-4444-555555555555'

vi.mock('@/api/apiClient', () => ({
  default: {
    get: mocks.get,
    post: mocks.post,
  },
}))

describe('authService', () => {
  beforeEach(() => {
    mocks.get.mockReset()
    mocks.post.mockReset()
    localStorage.clear()
  })

  it('checks if user exists by dni', async () => {
    mocks.get.mockResolvedValue({ data: true })

    const result = await checkUserExists('12345678A')

    expect(apiClient.get).toHaveBeenCalledWith('/auth/exists/12345678A')
    expect(result).toBe(true)
  })

  it('returns false when user is missing', async () => {
    mocks.get.mockRejectedValue({ response: { status: 404 } })

    await expect(checkUserExists('not-found')).resolves.toBe(false)
  })

  it('rethrows unexpected errors when checking user existence', async () => {
    const error = { response: { status: 500 }, message: 'boom' }
    mocks.get.mockRejectedValue(error)

    await expect(checkUserExists('oops')).rejects.toBe(error)
  })

  it('logs in user, stores token and returns payload', async () => {
    mocks.post.mockResolvedValue({ data: { token: MOCK_TOKEN, user: { name: 'Ada' } } })

    const response = await loginUser('12345678A', 'secret')

    expect(apiClient.post).toHaveBeenCalledWith('/auth/login', {
      dni: '12345678A',
      password: 'secret',
    })
    expect(localStorage.getItem('authToken')).toBe(MOCK_TOKEN)
    expect(response).toEqual({ token: MOCK_TOKEN, user: { name: 'Ada' } })
  })

  it('propagates login failure', async () => {
    const error = new Error('boom')
    mocks.post.mockRejectedValue(error)

    await expect(loginUser('bad', 'creds')).rejects.toBe(error)
  })

  it('signs up user mapping payload shape and stores token', async () => {
    mocks.post.mockResolvedValue({ data: { message: 'created', token: MOCK_TOKEN } })
    const payload = {
      name: 'Ada',
      dni: '123',
      password: 'secret',
      email: 'user@test.com',
      phone: '600123123',
      pin: undefined,
      gender: undefined,
      birthdate: undefined,
    }

    const response = await signupUser(payload)

    expect(apiClient.post).toHaveBeenCalledWith('/auth/register', {
      dni: '123',
      password: 'secret',
      email: 'user@test.com',
      phone: '+34600123123',
      pin: undefined,
      gender: undefined,
      birthdate: undefined,
      name: 'Ada',
    })
    expect(localStorage.getItem('authToken')).toBe(MOCK_TOKEN)
    expect(response).toEqual({ message: 'created', token: MOCK_TOKEN })
  })

  it('rejects signup when phone cannot be normalized', async () => {
    await expect(
      signupUser({
        name: 'Ada',
        dni: '123',
        password: 'secret',
        email: 'user@test.com',
        phone: '+34999',
        pin: '123456',
        gender: 'female',
        birthdate: '1990-01-01',
      }),
    ).rejects.toThrow('INVALID_PHONE_FORMAT_FE')
    expect(apiClient.post).not.toHaveBeenCalled()
  })

  it('throws clean error message on signup failure', async () => {
    const error = {
      response: {
        data: {
          message: 'Already exists',
        },
      },
    }
    mocks.post.mockRejectedValue(error)

    await expect(
      signupUser({ name: 'Ada', dni: '1', password: '2', email: 'a', phone: '+34600123123' }),
    ).rejects.toThrow('Already exists')
  })

  it('logs out when token present and clears storage', async () => {
    localStorage.setItem('authToken', MOCK_TOKEN)
    mocks.post.mockResolvedValue({})

    await logoutSession('12345678A')

    expect(apiClient.post).toHaveBeenCalledWith('/auth/logout', {
      dni: '12345678A',
      token: MOCK_TOKEN,
    })
    expect(localStorage.getItem('authToken')).toBeNull()
  })

  it('skips logout call when token missing', async () => {
    await logoutSession('12345678A')
    expect(apiClient.post).not.toHaveBeenCalled()
  })

  it('allows overriding logout token argument even when storage empty', async () => {
    mocks.post.mockResolvedValue({})

    await logoutSession('321', 'OVERRIDE_TOKEN')

    expect(apiClient.post).toHaveBeenCalledWith('/auth/logout', {
      dni: '321',
      token: 'OVERRIDE_TOKEN',
    })
  })

  it('validates session using stored token', async () => {
    localStorage.setItem('authToken', MOCK_TOKEN)
    mocks.post.mockResolvedValue({})

    await expect(validateSession('12345678A')).resolves.toBe(true)

    expect(apiClient.post).toHaveBeenCalledWith('/auth/validate', {
      dni: '12345678A',
      token: MOCK_TOKEN,
    })
  })

  it('throws when trying to validate without token', async () => {
    await expect(validateSession('12345678A')).rejects.toThrow('Missing session token.')
  })

  it('validates session with explicit token argument', async () => {
    mocks.post.mockResolvedValue({})

    await expect(validateSession('42', 'TOKEN')).resolves.toBe(true)

    expect(apiClient.post).toHaveBeenCalledWith('/auth/validate', {
      dni: '42',
      token: 'TOKEN',
    })
  })

  it('propagates backend validation failures', async () => {
    const error = new Error('invalid')
    mocks.post.mockRejectedValue(error)

    await expect(validateSession('dni', 'bad-token')).rejects.toBe(error)
  })
})
