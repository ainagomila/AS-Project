import { APIRequestContext, request as playwrightRequest } from '@playwright/test'
import { createHash, createHmac, randomBytes } from 'node:crypto'
import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { API_BASE_URL, FRONTEND_BASE_URL } from './env'

const DNI_LETTERS = 'TRWAGMYFPDXBNJZSQVHLCKE'
const IBAN_COUNTRY_CODE = 'ES'
const SPANISH_BANK_WEIGHTS = [4, 8, 5, 10, 9, 7, 3, 6]
const SPANISH_ACCOUNT_WEIGHTS = [1, 2, 4, 8, 5, 10, 9, 7, 3, 6]

function uniqueSuffix() {
    return Math.floor(Date.now() % 1_000_000 + Math.random() * 1_000_000)
        .toString(36)
        .toUpperCase()
}

function randomDigits(length: number) {
    return Array.from({ length }, () => Math.floor(Math.random() * 10)).join('')
}

function computeSpainControlDigit(value: string, weights: number[]) {
    const sum = value
        .split('')
        .reduce((acc, digit, index) => acc + Number(digit) * weights[index], 0)
    const remainder = 11 - (sum % 11)
    if (remainder === 10) return 1
    if (remainder === 11) return 0
    return remainder
}

function computeIbanCheckDigits(countryCode: string, bban: string) {
    const rearranged = `${bban}${countryCode}00`
    const numeric = rearranged.replace(/[A-Z]/g, (char) => (char.charCodeAt(0) - 55).toString())
    let remainder = 0
    for (const digit of numeric) {
        remainder = (remainder * 10 + Number(digit)) % 97
    }
    const checkDigits = 98 - remainder
    return checkDigits.toString().padStart(2, '0')
}

function generateDniNumber() {
    const digits = Math.floor(Math.random() * 100_000_000)
        .toString()
        .padStart(8, '0')
    const letter = DNI_LETTERS[Number(digits) % 23]
    return `${digits}${letter}`
}

function formatBirthdate(date: Date) {
    const year = date.getFullYear()
    const month = `${date.getMonth() + 1}`.padStart(2, '0')
    const day = `${date.getDate()}`.padStart(2, '0')
    return {
        iso: `${year}-${month}-${day}`,
        display: `${day}/${month}/${year}`,
    }
}

function generatePhonePair() {
    const local = `6${randomDigits(8)}`
    return {
        local,
        e164: `+34${local}`,
    }
}

function generateIban() {
    const bank = (Math.floor(Math.random() * 9000) + 1000).toString()
    const branch = randomDigits(4)
    const account = randomDigits(10)
    const firstControl = computeSpainControlDigit(bank + branch, SPANISH_BANK_WEIGHTS)
    const secondControl = computeSpainControlDigit(account, SPANISH_ACCOUNT_WEIGHTS)
    const bban = `${bank}${branch}${firstControl}${secondControl}${account}`
    const checksum = computeIbanCheckDigits(IBAN_COUNTRY_CODE, bban)
    return `${IBAN_COUNTRY_CODE}${checksum}${bban}`
}

function luhnCheckDigit(payload: string) {
    // Double every second digit counting from the right of the payload, as Luhn does
    // once the check digit is appended.
    const sum = payload
        .split('')
        .reverse()
        .reduce((acc, char, index) => {
            const digit = Number(char)
            if (index % 2 === 1) return acc + digit
            const doubled = digit * 2
            return acc + (doubled > 9 ? doubled - 9 : doubled)
        }, 0)
    return String((10 - (sum % 10)) % 10)
}

/** A random 16-digit Visa-style PAN that passes the Luhn check. */
export function generatePan() {
    const payload = `4${randomDigits(14)}`
    return `${payload}${luhnCheckDigit(payload)}`
}

/**
 * The verifier's secret key: VERIFIER_SECRET_KEY from the environment, or from the
 * repository's .env that scripts/start-docker.* generates. Tests run from frontend/.
 */
function verifierSecretKey() {
    if (process.env.VERIFIER_SECRET_KEY) return process.env.VERIFIER_SECRET_KEY
    for (const file of [resolve(process.cwd(), '../.env'), resolve(process.cwd(), '.env')]) {
        if (!existsSync(file)) continue
        const match = /^VERIFIER_SECRET_KEY=(.*)$/m.exec(readFileSync(file, 'utf8'))
        if (match?.[1]) return match[1].trim().replace(/^(['"])(.*)\1$/, '$2')
    }
    throw new Error(
        'VERIFIER_SECRET_KEY not found: set it or run the tests from frontend/ next to the generated ../.env',
    )
}

/**
 * The CVV the verifier service accepts for this PAN and expiry date (MM/YY), derived
 * like the issuing bank would: HMAC-SHA256 of "<PAN>E<MM/YY>" with the verifier's key,
 * modulo 1000. Mirrors verifier-backend/app/main.py.
 */
export function computeCvv(pan: string, expiry: string) {
    const tag = createHmac('sha256', verifierSecretKey()).update(`${pan}E${expiry}`).digest()
    const cvv = BigInt(`0x${tag.toString('hex')}`) % 1000n
    return cvv.toString().padStart(3, '0')
}

export type TestUser = {
    name: string
    dni: string
    email: string
    phoneLocal: string
    phoneE164: string
    password: string
    pin: string
    gender: 'female' | 'male' | 'other'
    birthdateIso: string
    birthdateDisplay: string
}

export function buildTestUser(overrides: Partial<TestUser> = {}): TestUser {
    const birthdate = formatBirthdate(new Date(1990, 0, 15))
    const phone = generatePhonePair()
    const pin = overrides.pin ?? randomDigits(6)
    return {
        name: overrides.name ?? `Playwright User ${uniqueSuffix()}`,
        dni: overrides.dni ?? generateDniNumber(),
        email: overrides.email ?? `qa+${uniqueSuffix()}@kofre.app`,
        phoneLocal: overrides.phoneLocal ?? phone.local,
        phoneE164: overrides.phoneE164 ?? phone.e164,
        password: overrides.password ?? `Pw1_${uniqueSuffix()}!`,
        pin,
        gender: overrides.gender ?? 'female',
        birthdateIso: overrides.birthdateIso ?? birthdate.iso,
        birthdateDisplay: overrides.birthdateDisplay ?? birthdate.display,
    }
}

export type TestAccount = {
    iban: string
    name: string
    bank: string
    currency: string
}

export function buildTestAccount(overrides: Partial<TestAccount> = {}): TestAccount {
    return {
        iban: overrides.iban ?? generateIban(),
        name: overrides.name ?? `Savings ${uniqueSuffix()}`,
        bank: overrides.bank ?? 'Kofre Test Bank',
        currency: overrides.currency ?? 'EUR',
    }
}

export type TestCard = {
    pan: string
    cvv: string
    cardPin: string
    alias: string
    type: 'DEBIT' | 'CREDIT'
    bank: string
    expireMonth: string
    expireYear: string
    accountIban: string
}

export function buildTestCard(overrides: Partial<TestCard> = {}): TestCard {
    const expireYear = overrides.expireYear ?? `${(new Date().getFullYear() + 2).toString().slice(-2)}`
    const expireMonth = overrides.expireMonth ?? '12'
    const pan = overrides.pan ?? generatePan()
    return {
        pan,
        cvv: overrides.cvv ?? computeCvv(pan, `${expireMonth}/${expireYear}`),
        cardPin: overrides.cardPin ?? randomDigits(4),
        alias: overrides.alias ?? `Travel ${uniqueSuffix()}`,
        type: overrides.type ?? 'DEBIT',
        bank: overrides.bank ?? 'Kofre Test Bank',
        expireMonth,
        expireYear,
        accountIban: overrides.accountIban ?? '',
    }
}

export type TestUserCredentials = Pick<TestUser, 'dni' | 'pin' | 'password'>

export async function registerUserViaApi(request: APIRequestContext, user: TestUser) {
    const response = await request.post(`${API_BASE_URL}/auth/register`, {
        data: {
            name: user.name,
            dni: user.dni,
            email: user.email,
            phone: user.phoneE164,
            password: user.password,
            birthdate: user.birthdateIso,
            gender: user.gender,
            pin: user.pin,
        },
    })

    if (!response.ok()) {
        throw new Error(
            `Failed to register user ${user.dni}: ${response.status()} ${await response.text()}`,
        )
    }
}

function normalizeIban(iban: string) {
    return String(iban ?? '')
        .replace(/\s+/g, '')
        .toUpperCase()
}

function normalizePan(pan: string) {
    return String(pan ?? '').replace(/\s+/g, '')
}

export function ensurePaymentIdFormat(rawId: string) {
    const trimmed = String(rawId ?? '').trim()
    if (!trimmed) {
        return ''
    }
    return trimmed.startsWith('PAY-') ? trimmed : `PAY-${trimmed.replace(/^PAY[-_]?/i, '')}`
}

const OAUTH_CLIENT_ID = 'kofre-web'

/**
 * Signs in through the real OAuth2 flow (Authorization Code + PKCE, like the app) and
 * returns an access token. It uses its own request context so the Django login cookie
 * of one user never leaks into the next call. The redirect URI must be the one registered
 * for the client, so run the tests with E2E_BASE_URL pointing at the frontend origin.
 */
export async function fetchAuthToken(_request: APIRequestContext, dni: string, password: string) {
    const api = await playwrightRequest.newContext({ ignoreHTTPSErrors: true })
    try {
        const verifier = randomBytes(32).toString('base64url')
        const challenge = createHash('sha256').update(verifier).digest('base64url')
        const redirectUri = `${FRONTEND_BASE_URL}/callback`
        const query = new URLSearchParams({
            response_type: 'code',
            client_id: OAUTH_CLIENT_ID,
            redirect_uri: redirectUri,
            scope: 'openid banking',
            code_challenge: challenge,
            code_challenge_method: 'S256',
            state: randomBytes(8).toString('hex'),
        })

        // 1. Not signed in yet: the authorize endpoint sends us to the login page.
        const toLogin = await api.get(`${API_BASE_URL}/o/authorize/?${query}`, { maxRedirects: 0 })
        const loginUrl = new URL(toLogin.headers()['location'] ?? '', API_BASE_URL)

        // 2. Load the login form (CSRF cookie + token) and submit the credentials.
        const loginPage = await api.get(loginUrl.toString())
        const csrf = /name="csrfmiddlewaretoken" value="([^"]+)"/.exec(await loginPage.text())?.[1]
        if (!csrf) {
            console.warn(`CSRF token not found on the login page for ${dni}`)
            return null
        }
        const submitted = await api.post(loginUrl.toString(), {
            form: {
                username: dni,
                password,
                csrfmiddlewaretoken: csrf,
                next: loginUrl.searchParams.get('next') ?? '',
            },
            headers: { Referer: loginUrl.toString() },
            maxRedirects: 0,
        })
        if (submitted.status() !== 302) {
            console.warn(`Failed to login for auth token ${dni}: ${submitted.status()}`)
            return null
        }

        // 3. Signed in: authorize now answers with the redirect that carries the code.
        const authorized = await api.get(
            new URL(submitted.headers()['location'] ?? '', API_BASE_URL).toString(),
            { maxRedirects: 0 },
        )
        const code = new URL(authorized.headers()['location'] ?? '', API_BASE_URL).searchParams.get('code')
        if (!code) {
            console.warn(`Authorization code missing for ${dni}`)
            return null
        }

        // 4. Exchange the code (and the PKCE verifier) for the tokens.
        const tokenResponse = await api.post(`${API_BASE_URL}/o/token/`, {
            form: {
                grant_type: 'authorization_code',
                code,
                redirect_uri: redirectUri,
                client_id: OAUTH_CLIENT_ID,
                code_verifier: verifier,
            },
        })
        if (!tokenResponse.ok()) {
            console.warn(`Token request failed for ${dni}: ${tokenResponse.status()}`)
            return null
        }
        const payload = await tokenResponse.json()
        return (payload?.access_token as string | undefined) ?? null
    } catch (error) {
        console.warn(`Error obtaining auth token for ${dni}:`, error)
        return null
    } finally {
        await api.dispose()
    }
}

export async function deleteAccountViaApi(
    request: APIRequestContext,
    credentials: TestUserCredentials,
    rawIban: string,
    authToken?: string,
) {
    const iban = normalizeIban(rawIban)
    if (!iban) {
        return
    }

    try {
        const token = authToken ?? (await fetchAuthToken(request, credentials.dni, credentials.password))
        if (!token) {
            return
        }

        const response = await request.delete(
            `${API_BASE_URL}/users/${encodeURIComponent(credentials.dni)}/accounts/${encodeURIComponent(iban)}`,
            {
                headers: {
                    Authorization: `Bearer ${token}`,
                },
                data: {
                    pin: credentials.pin,
                },
            },
        )

        if (!response.ok() && response.status() !== 404) {
            console.warn(
                `Failed to delete account ${iban} for ${credentials.dni}: ${response.status()} ${await response.text()}`,
            )
        }
    } catch (error) {
        console.warn(`Error during account deletion ${iban} for ${credentials.dni}:`, error)
    }
}

export type UserAccountSummary = {
    iban?: string
    [key: string]: unknown
}

export async function listAccountsViaApi(
    request: APIRequestContext,
    credentials: TestUserCredentials,
    authToken?: string,
): Promise<UserAccountSummary[]> {
    try {
        const token = authToken ?? (await fetchAuthToken(request, credentials.dni, credentials.password))
        if (!token) {
            return []
        }

        const response = await request.get(
            `${API_BASE_URL}/users/${encodeURIComponent(credentials.dni)}/accounts`,
            {
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            },
        )

        if (!response.ok()) {
            if (response.status() !== 404) {
                console.warn(
                    `Failed to list accounts for ${credentials.dni}: ${response.status()} ${await response.text()}`,
                )
            }
            return []
        }

        const payload = await response.json()
        if (Array.isArray(payload)) {
            return payload as UserAccountSummary[]
        }
        if (Array.isArray(payload?.accounts)) {
            return payload.accounts as UserAccountSummary[]
        }
        if (Array.isArray(payload?.items)) {
            return payload.items as UserAccountSummary[]
        }
        return []
    } catch (error) {
        console.warn(`Error listing accounts for cleanup ${credentials.dni}:`, error)
        return []
    }
}

export async function deleteCardViaApi(
    request: APIRequestContext,
    credentials: TestUserCredentials,
    rawIban: string,
    rawPan: string,
    authToken?: string,
) {
    const iban = normalizeIban(rawIban)
    const pan = normalizePan(rawPan)
    if (!iban || !pan) {
        return
    }

    try {
        const token = authToken ?? (await fetchAuthToken(request, credentials.dni, credentials.password))
        if (!token) {
            return
        }

        const response = await request.delete(
            `${API_BASE_URL}/users/${encodeURIComponent(credentials.dni)}/accounts/${encodeURIComponent(iban)}/cards/${encodeURIComponent(pan)}`,
            {
                headers: {
                    Authorization: `Bearer ${token}`,
                },
                data: {
                    pin: credentials.pin,
                },
            },
        )

        if (!response.ok() && response.status() !== 404) {
            console.warn(
                `Failed to delete card ${pan} (${iban}) for ${credentials.dni}: ${response.status()} ${await response.text()}`,
            )
        }
    } catch (error) {
        console.warn(`Error during card deletion ${pan} for ${credentials.dni}:`, error)
    }
}

export async function deletePaymentViaApi(
    request: APIRequestContext,
    credentials: TestUserCredentials,
    rawIban: string,
    rawPaymentId: string,
    authToken?: string,
) {
    const iban = normalizeIban(rawIban)
    const paymentId = ensurePaymentIdFormat(rawPaymentId)
    if (!iban || !paymentId) {
        return
    }

    try {
        const token = authToken ?? (await fetchAuthToken(request, credentials.dni, credentials.password))
        if (!token) {
            return
        }

        const encodedUser = encodeURIComponent(credentials.dni)
        const encodedIban = encodeURIComponent(iban)
        const encodedPayment = encodeURIComponent(paymentId)
        const endpoints = [
            `${API_BASE_URL}/users/${encodedUser}/accounts/${encodedIban}/transfers/${encodedPayment}`,
            `${API_BASE_URL}/users/${encodedUser}/accounts/${encodedIban}/payments/${encodedPayment}`,
        ]

        for (const endpoint of endpoints) {
            const response = await request.delete(endpoint, {
                headers: {
                    Authorization: `Bearer ${token}`,
                },
                data: {
                    pin: credentials.pin,
                },
            })

            if (response.ok()) {
                return
            }

            if (response.status() === 404) {
                continue
            }

            console.warn(
                `Failed to delete payment ${paymentId} for ${credentials.dni}: ${response.status()} ${await response.text()}`,
            )
            return
        }
    } catch (error) {
        console.warn(`Error during payment deletion ${paymentId} for ${credentials.dni}:`, error)
    }
}

export async function deleteUserViaApi(
    request: APIRequestContext,
    dni: string,
    pin: string,
    password: string,
    authToken?: string,
) {
    try {
        const token = authToken ?? (await fetchAuthToken(request, dni, password))
        if (!token) {
            return
        }

        const response = await request.delete(`${API_BASE_URL}/users/${dni}`, {
            headers: {
                Authorization: `Bearer ${token}`,
            },
            data: {
                dni: dni.slice(-4),
                pin,
            },
        })

        if (!response.ok() && response.status() !== 404) {
            console.warn(
                `Failed to delete user ${dni}: ${response.status()} ${await response.text()}`,
            )
        }
    } catch (error) {
        console.warn(`Error during user deletion ${dni}:`, error)
    }
}

