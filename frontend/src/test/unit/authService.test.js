import { describe, expect, it, vi, beforeEach } from 'vitest'
import apiClient from '@/api/apiClient'
import { checkUserExists, signupUser } from '@/api/authService'

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}))

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

  it('signs up user mapping payload shape', async () => {
    mocks.post.mockResolvedValue({ data: { message: 'created' } })
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
    expect(response).toEqual({ message: 'created' })
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
})
