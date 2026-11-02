// @vitest-environment node
import { describe, it, expect, beforeAll, afterAll, vi } from 'vitest'
import { signupUser } from '@/api/authService'
import { computeCvv, fetchAuthToken, generatePan } from '../e2e/support/testData'
import {
  addAccount,
  addCard,
  deleteAccount,
  deleteCard,
  deleteUser,
  getAccounts,
  getCards,
  getUser,
} from '@/api/userService'

vi.setConfig({ testTimeout: 60_000 })

// Tokens live in the UserManager (memory only), which does not exist in node.
// The access token comes from the real OAuth flow and is served through this stand-in.
const auth = vi.hoisted(() => ({ token: null }))
vi.mock('@/api/oidc', () => ({
  userManager: {
    getUser: async () => (auth.token ? { access_token: auth.token, expired: false } : null),
  },
}))

const DNI_LETTERS = 'TRWAGMYFPDXBNJZSQVHLCKE'

function randomDigits(length) {
  return Array.from({ length }, () => Math.floor(Math.random() * 10)).join('')
}

function uniqueSuffix() {
  return Math.floor(Math.random() * 10_000_000 + Date.now() % 1_000_000)
    .toString(36)
    .toUpperCase()
}

function buildTestUser() {
  const digits = Math.floor(Math.random() * 100_000_000)
    .toString()
    .padStart(8, '0')
  const letter = DNI_LETTERS[Number(digits) % DNI_LETTERS.length]
  return {
    name: `Backend QA ${uniqueSuffix()}`,
    dni: `${digits}${letter}`,
    email: `qa+${uniqueSuffix()}@kofre.app`,
    phone: `+34${6}${randomDigits(8)}`,
    password: `Pw1_${uniqueSuffix()}!`,
    pin: randomDigits(6),
    birthdate: '1994-02-15',
    gender: 'female',
  }
}

function computeSpainControlDigit(value, weights) {
  const sum = value
    .split('')
    .reduce((acc, digit, index) => acc + Number(digit) * weights[index], 0)
  const remainder = 11 - (sum % 11)
  if (remainder === 10) return 1
  if (remainder === 11) return 0
  return remainder
}

function computeIbanCheckDigits(countryCode, bban) {
  const rearranged = `${bban}${countryCode}00`
  const numeric = rearranged.replace(/[A-Z]/g, (char) => (char.charCodeAt(0) - 55).toString())
  let remainder = 0
  for (const digit of numeric) {
    remainder = (remainder * 10 + Number(digit)) % 97
  }
  const checkDigits = 98 - remainder
  return checkDigits.toString().padStart(2, '0')
}

function generateIban() {
  const bank = (Math.floor(Math.random() * 9000) + 1000).toString()
  const branch = randomDigits(4)
  const account = randomDigits(10)
  const bankWeights = [4, 8, 5, 10, 9, 7, 3, 6]
  const accountWeights = [1, 2, 4, 8, 5, 10, 9, 7, 3, 6]
  const firstControl = computeSpainControlDigit(bank + branch, bankWeights)
  const secondControl = computeSpainControlDigit(account, accountWeights)
  const bban = `${bank}${branch}${firstControl}${secondControl}${account}`
  const checksum = computeIbanCheckDigits('ES', bban)
  return `ES${checksum}${bban}`
}

function normaliseIban(iban) {
  return String(iban ?? '')
    .replace(/\s+/g, '')
    .toUpperCase()
}

function buildTestAccount() {
  return {
    iban: generateIban(),
    name: `QA Account ${uniqueSuffix()}`,
    bank: 'Kofre QA Bank',
    balance: Number((Math.random() * 500 + 100).toFixed(2)),
    currency: 'EUR',
  }
}

function buildTestCard(accountIban) {
  const pan = generatePan()
  const expireDate = '12/29'
  return {
    pan,
    expireDate,
    alias: `QA Card ${uniqueSuffix()}`,
    cvv: computeCvv(pan, expireDate),
    pin: randomDigits(4),
    type: 'DEBIT',
    bank: 'Kofre QA Bank',
    accountIban,
  }
}

function normalisePan(pan) {
  return String(pan ?? '').replace(/\s+/g, '')
}

// The tests build on each other (user, then account, then card), so they must not run concurrently.
describe('Real backend flows', { concurrent: false }, () => {
  const cleanup = {
    cards: [],
    accounts: [],
  }
  let testUser

  beforeAll(async () => {
    testUser = buildTestUser()
    await signupUser({
      name: testUser.name,
      dni: testUser.dni,
      email: testUser.email,
      phone: testUser.phone,
      password: testUser.password,
      birthdate: testUser.birthdate,
      gender: testUser.gender,
      pin: testUser.pin,
    })

    auth.token = await fetchAuthToken(null, testUser.dni, testUser.password)
    expect(auth.token).toBeTruthy()
  })

  afterAll(async () => {
    for (const card of [...cleanup.cards].reverse()) {
      try {
        await deleteCard(testUser.dni, card.iban, card.pan, testUser.pin)
      } catch (error) {
        console.warn('Failed to delete card during cleanup', error.message)
      }
    }

    for (const account of [...cleanup.accounts].reverse()) {
      try {
        await deleteAccount(testUser.dni, account.iban, testUser.pin)
      } catch (error) {
        console.warn('Failed to delete account during cleanup', error.message)
      }
    }

    try {
      await deleteUser(testUser.dni, { pin: testUser.pin })
    } catch (error) {
      console.warn('Failed to delete test user during cleanup', error.message)
    }

    auth.token = null
  })

  it('retrieves the profile of a freshly registered user', async () => {
    const profile = await getUser(testUser.dni)
    expect(profile).toBeDefined()
    expect(profile.dni).toBe(testUser.dni)
    expect(String(profile.email).toLowerCase()).toBe(testUser.email.toLowerCase())
  })

  it('creates accounts against the live backend and exposes them via the API', async () => {
    const payload = buildTestAccount()
    const created = await addAccount(testUser.dni, payload)
    cleanup.accounts.push({ iban: payload.iban })

    expect(normaliseIban(created.iban)).toBe(normaliseIban(payload.iban))

    const accounts = await getAccounts(testUser.dni)
    const match = accounts.find((account) => normaliseIban(account.iban) === normaliseIban(payload.iban))
    expect(match).toBeTruthy()
    expect(match.name ?? '').toContain(payload.name.split(' ')[0])
  })

  it('attaches cards to the previously created account', async () => {
    const targetAccount = cleanup.accounts[0]
    expect(targetAccount).toBeTruthy()

    const cardPayload = buildTestCard(targetAccount.iban)
    const card = await addCard(testUser.dni, targetAccount.iban, cardPayload)
    cleanup.cards.push({ iban: targetAccount.iban, pan: normalisePan(cardPayload.pan) })

    expect(card).toBeDefined()

    const cards = await getCards(testUser.dni)
    const found = cards.find((entry) => normalisePan(entry.pan) === normalisePan(cardPayload.pan))
    expect(found).toBeTruthy()
    expect(found.bank ?? card.bank).toBe(cardPayload.bank)
  })
})

