import { APIRequestContext } from '@playwright/test'
import { API_BASE_URL } from './env'
import {
    ensurePaymentIdFormat,
    fetchAuthToken,
    type TestUserCredentials,
} from './testData'
import type { UserCleanupHandle } from './cleanup'

function normaliseIban(value: string) {
    return String(value ?? '')
        .replace(/\s+/g, '')
        .toUpperCase()
}

async function listTransfers(
    request: APIRequestContext,
    credentials: TestUserCredentials,
    accountIban: string,
    authToken?: string | null,
) {
    const token = authToken ?? (await fetchAuthToken(request, credentials.dni, credentials.password))
    if (!token) {
        return []
    }

    const response = await request.get(
        `${API_BASE_URL}/users/${encodeURIComponent(credentials.dni)}/accounts/${encodeURIComponent(normaliseIban(accountIban))}/transfers`,
        {
            headers: {
                Authorization: `Bearer ${token}`,
            },
            params: {
                sort: 'desc',
            },
        },
    )

    if (!response.ok()) {
        return []
    }

    const payload = await response.json()
    if (Array.isArray(payload)) {
        return payload
    }
    if (Array.isArray(payload?.transfers)) {
        return payload.transfers
    }
    if (Array.isArray(payload?.items)) {
        return payload.items
    }
    return []
}

export async function fetchLatestTransferPaymentId(
    request: APIRequestContext,
    credentials: TestUserCredentials,
    accountIban: string,
    authToken?: string | null,
) {
    const transfers = await listTransfers(request, credentials, accountIban, authToken)
    if (!transfers.length) {
        return ''
    }
    const head = transfers[0] ?? {}
    const paymentId = head.paymentId ?? head.id ?? ''
    return ensurePaymentIdFormat(paymentId)
}

// New accounts open at 0, so tests fund them from the user's registration account.
export async function fundAccountViaApi(
    request: APIRequestContext,
    credentials: TestUserCredentials,
    accountIban: string,
    amount: number,
) {
    const token = await fetchAuthToken(request, credentials.dni, credentials.password)
    const headers = { Authorization: `Bearer ${token}` }
    const userUrl = `${API_BASE_URL}/users/${encodeURIComponent(credentials.dni)}`
    const accounts = (await (await request.get(`${userUrl}/accounts`, { headers })).json()).accounts
    const source = accounts.find((a) => a.iban !== normaliseIban(accountIban))
    const response = await request.post(`${userUrl}/accounts/${source.iban}/transfers`, {
        headers,
        data: {
            beneficiary: 'E2E funding',
            destinationIban: normaliseIban(accountIban),
            amount,
            currency: 'EUR',
            concept: 'E2E funding',
            pin: credentials.pin,
        },
    })
    if (!response.ok()) {
        throw new Error(`Funding transfer failed: ${response.status()}`)
    }
}

export function trackPaymentIfPresent(handle: UserCleanupHandle, accountIban: string, paymentId: string) {
    const formatted = ensurePaymentIdFormat(paymentId)
    if (!formatted) {
        return
    }
    handle.trackPayment({ accountIban, paymentId: formatted })
}

