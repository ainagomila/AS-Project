import { beforeEach, describe, expect, it, vi } from 'vitest'
import apiClient from '@/api/apiClient'
import {
  getUser,
  updateUser,
  verifyPin,
  verifyPassword,
  changePassword,
  changePin,
  getAccounts,
  getAccount,
  addAccount,
  getAccountCards,
  getCard,
  getCardByPan,
  updateAccount,
  deleteAccount,
  getCards,
  addCard,
  updateCard,
  deleteCard,
  verifyCard,
  getTransfers,
} from '@/api/userService'

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
}))

vi.mock('@/api/apiClient', () => ({
  default: {
    get: mocks.get,
    post: mocks.post,
    patch: mocks.patch,
    delete: mocks.delete,
  },
}))

describe('userService', () => {
  beforeEach(() => {
    mocks.get.mockReset()
    mocks.post.mockReset()
    mocks.patch.mockReset()
    mocks.delete.mockReset()
  })

  it('reads user profile by dni', async () => {
    mocks.get.mockResolvedValue({ data: { name: 'Ana' } })
    const result = await getUser('123 456')
    expect(apiClient.get).toHaveBeenCalledWith('/users/123%20456')
    expect(result).toEqual({ name: 'Ana' })
  })

  it('updates user profile with patch', async () => {
    mocks.patch.mockResolvedValue({ data: { email: 'new@test.com' } })
    const payload = { email: 'new@test.com' }
    const result = await updateUser('ABC', payload)
    expect(apiClient.patch).toHaveBeenCalledWith('/users/ABC', payload)
    expect(result).toEqual(payload)
  })

  it('verifies pin and returns true', async () => {
    mocks.post.mockResolvedValue({ data: { pin: '1234' } })
    const response = await verifyPin('1', '1234')
    expect(apiClient.post).toHaveBeenCalledWith('/users/1/security/verify-pin', { pin: '1234' })
    expect(response).toEqual({ pin: '1234' })
  })

  it('verifies password returning payload', async () => {
    mocks.post.mockResolvedValue({ data: { password: 'secret' } })
    const response = await verifyPassword('dni', '555555')
    expect(apiClient.post).toHaveBeenCalledWith('/users/dni/security/verify-password', {
      pin: '555555',
    })
    expect(response).toEqual({ password: 'secret' })
  })

  it('changes password by posting payload', async () => {
    mocks.patch.mockResolvedValue({})
    const payload = { pin: '1234', newPassword: 'pass' }
    const response = await changePassword('1', payload)
    expect(apiClient.patch).toHaveBeenCalledWith('/users/1', { pin: '1234', password: 'pass' })
    expect(response).toBe(true)
  })

  it('changes pin', async () => {
    mocks.patch.mockResolvedValue({})
    const payload = { pin: '1111', newPin: '2222' }
    const response = await changePin('id', payload)
    expect(apiClient.patch).toHaveBeenCalledWith('/users/id', payload)
    expect(response).toBe(true)
  })

  it('lists accounts', async () => {
    mocks.get.mockResolvedValue({ data: [] })
    await getAccounts('dni')
    expect(apiClient.get).toHaveBeenCalledWith('/users/dni/accounts')
  })

  it('extracts nested accounts array when backend wraps response', async () => {
    mocks.get.mockResolvedValue({ data: { accounts: [{ id: 'acc-1' }] } })
    const accounts = await getAccounts('dni')
    expect(accounts).toEqual([{ id: 'acc-1' }])
  })

  it('returns empty list and warns when accounts payload malformed', async () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
    mocks.get.mockResolvedValue({ data: { unexpected: true } })
    const accounts = await getAccounts('dni')
    expect(accounts).toEqual([])
    expect(warnSpy).toHaveBeenCalled()
    warnSpy.mockRestore()
  })

  it('gets account details', async () => {
    mocks.get.mockResolvedValue({ data: { id: 'acc' } })
    await getAccount('dni', 'ES 00')
    expect(apiClient.get).toHaveBeenCalledWith('/users/dni/accounts/ES%2000')
  })

  it('creates account', async () => {
    mocks.post.mockResolvedValue({ data: { id: '1' } })
    const account = { iban: 'ES00' }
    await addAccount('dni', account)
    expect(apiClient.post).toHaveBeenCalledWith('/users/dni/accounts', account)
  })

  it('reads account cards for a specific IBAN', async () => {
    mocks.get.mockResolvedValue({ data: [{ id: 'card-1' }] })
    const cards = await getAccountCards('dni', 'ES00')
    expect(apiClient.get).toHaveBeenCalledWith('/users/dni/accounts/ES00/cards')
    expect(cards).toEqual([{ id: 'card-1' }])
  })

  it('reads card by id', async () => {
    mocks.get.mockResolvedValue({ data: { id: 'card' } })
    await getCard('dni', 'ES00', 'CARD 1')
    expect(apiClient.get).toHaveBeenCalledWith('/users/dni/accounts/ES00/cards/CARD1')
  })

  it('reads card by normalized pan using helper', async () => {
    mocks.get.mockResolvedValue({ data: [{ pan: '4111111111111111', alias: 'Primary' }] })
    const card = await getCardByPan('dni', '4111 1111 1111 1111')
    expect(apiClient.get).toHaveBeenCalledWith('/users/dni/cards')
    expect(card).toEqual({ pan: '4111111111111111', alias: 'Primary' })
  })

  it('returns null when card helper cannot find a match', async () => {
    mocks.get.mockResolvedValue({ data: [{ pan: '9999' }] })
    const card = await getCardByPan('dni', '0000')
    expect(card).toBeNull()
  })

  it('reads account by id (using getAccount)', async () => {
    mocks.get.mockResolvedValue({ data: { id: 'acc' } })
    await getAccount('dni', 'ACC#1')
    expect(apiClient.get).toHaveBeenCalledWith('/users/dni/accounts/ACC%231')
  })

  it('updates account', async () => {
    mocks.patch.mockResolvedValue({ data: { ok: true } })
    const payload = { alias: 'Main' }
    await updateAccount('dni', 'acc id', payload)
    expect(apiClient.patch).toHaveBeenCalledWith('/users/dni/accounts/acc%20id', payload)
  })

  it('deletes account', async () => {
    mocks.delete.mockResolvedValue({})
    const response = await deleteAccount('dni', 'acc', '1234')
    expect(apiClient.delete).toHaveBeenCalledWith('/users/dni/accounts/acc', { data: { pin: '1234' } })
    expect(response).toBe(true)
  })

  it('lists cards', async () => {
    mocks.get.mockResolvedValue({ data: [] })
    await getCards('dni')
    expect(apiClient.get).toHaveBeenCalledWith('/users/dni/cards')
  })

  it('extracts nested cards array when backend wraps response', async () => {
    mocks.get.mockResolvedValue({ data: { cards: [{ pan: '1' }] } })
    const cards = await getCards('dni')
    expect(cards).toEqual([{ pan: '1' }])
  })

  it('adds card', async () => {
    mocks.post.mockResolvedValue({ data: { id: '1' } })
    const payload = { pan: '1234', expireDate: '12/25', alias: null, cvv: '123', pin: '1234', type: 'DEBIT', bank: 'Test' }
    await addCard('dni', 'ES00', payload)
    expect(apiClient.post).toHaveBeenCalledWith('/users/dni/accounts/ES00/cards', {
      pan: '1234',
      expireDate: '12/25',
      alias: null,
      cvv: '123',
      pin: '1234',
      type: 'DEBIT',
      bank: 'Test'
    })
  })

  it('strips spaces when creating card payloads', async () => {
    mocks.post.mockResolvedValue({ data: { id: '1' } })
    const payload = {
      pan: '1234 5678',
      expireDate: '01/30',
      alias: 'Travel',
      cvv: '321',
      pin: '4321',
      type: 'CREDIT',
      bank: 'Kofre',
    }
    await addCard('dni', 'ES00', payload)
    expect(apiClient.post).toHaveBeenLastCalledWith('/users/dni/accounts/ES00/cards', expect.objectContaining({
      pan: '12345678',
    }))
  })

  it('updates card', async () => {
    mocks.patch.mockResolvedValue({ data: { ok: true } })
    const payload = { nick: 'Daily' }
    await updateCard('dni', 'iban123', 'card', payload)
    expect(apiClient.patch).toHaveBeenCalledWith('/users/dni/accounts/iban123/cards/card', payload)
  })

  it('deletes card', async () => {
    mocks.delete.mockResolvedValue({})
    const response = await deleteCard('dni', 'ES00', 'card id', '1234')
    expect(apiClient.delete).toHaveBeenCalledWith('/users/dni/accounts/ES00/cards/cardid', { data: { pin: '1234' } })
    expect(response).toBeTruthy()
  })

  it('verifies card sensitive data with endpoint guard', async () => {
    mocks.post.mockResolvedValue({ data: { cvv: '111' } })
    const response = await verifyCard('dni', 'ES00', 'CARD 1', '654321')
    expect(apiClient.post).toHaveBeenCalledWith(
      '/users/dni/accounts/ES00/cards/CARD%201/security/verify-card',
      { pin: '654321' },
    )
    expect(response).toEqual({ cvv: '111' })
  })

  it('fetches transfers cleaning IBAN and normalising query params', async () => {
    mocks.get.mockResolvedValue({ data: { items: [{ title: 'Rent' }] } })

    const transfers = await getTransfers('12345678A', 'ES12 3456 7890', {
      q: 'Rent',
      onlyExpenses: true,
    })

    expect(apiClient.get).toHaveBeenCalledWith(
      '/users/12345678A/accounts/ES1234567890/transfers',
      {
        params: {
          q: 'Rent',
          onlyExpenses: true,
        },
      },
    )
    expect(transfers).toEqual([{ title: 'Rent' }])
  })

  it('accepts alternate payload shapes when listing transfers', async () => {
    mocks.get.mockResolvedValueOnce({ data: [{ title: 'raw array' }] })
    const direct = await getTransfers('dni', 'ES00', {})
    expect(direct).toEqual([{ title: 'raw array' }])

    mocks.get.mockResolvedValueOnce({ data: { transfers: [{ title: 'wrapped' }] } })
    const wrapped = await getTransfers('dni', 'ES00', {})
    expect(wrapped).toEqual([{ title: 'wrapped' }])
  })

  it('warns and falls back to empty list when transfers payload is malformed', async () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
    mocks.get.mockResolvedValue({ data: { unexpected: true } })

    const items = await getTransfers('dni', 'ES00', {})
    expect(items).toEqual([])
    expect(warnSpy).toHaveBeenCalled()
    warnSpy.mockRestore()
  })
})
