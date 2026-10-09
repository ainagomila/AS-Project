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

export function trackPaymentIfPresent(handle: UserCleanupHandle, accountIban: string, paymentId: string) {
    const formatted = ensurePaymentIdFormat(paymentId)
    if (!formatted) {
        return
    }
    handle.trackPayment({ accountIban, paymentId: formatted })
}

