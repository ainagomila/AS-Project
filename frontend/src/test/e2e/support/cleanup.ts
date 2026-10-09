import { APIRequestContext } from '@playwright/test'
import {
    deleteAccountViaApi,
    deleteCardViaApi,
    deletePaymentViaApi,
    deleteUserViaApi,
    ensurePaymentIdFormat,
    fetchAuthToken,
    listAccountsViaApi,
    type TestUserCredentials,
} from './testData'

type RegisteredCard = { iban: string; pan: string }
type RegisteredPayment = { accountIban: string; paymentId: string }

type CleanupRecord = {
    credentials: TestUserCredentials
    accounts: Set<string>
    cards: RegisteredCard[]
    payments: RegisteredPayment[]
}

export type UserCleanupHandle = {
    credentials: TestUserCredentials
    trackAccount: (iban: string) => void
    trackCard: (card: RegisteredCard) => void
    trackPayment: (payment: RegisteredPayment) => void
}

function normaliseIban(value: string) {
    return String(value ?? '')
        .replace(/\s+/g, '')
        .toUpperCase()
}

function ensureRecord(records: Map<string, CleanupRecord>, credentials: TestUserCredentials) {
    const key = credentials.dni
    if (!records.has(key)) {
        records.set(key, {
            credentials,
            accounts: new Set<string>(),
            cards: [],
            payments: [],
        })
    }
    return records.get(key) as CleanupRecord
}

export function createCleanupManager(request: APIRequestContext) {
    const records = new Map<string, CleanupRecord>()

    return {
        registerUser(credentials: TestUserCredentials): UserCleanupHandle {
            const record = ensureRecord(records, credentials)

            return {
                credentials,
                trackAccount(iban: string) {
                    const normalised = normaliseIban(iban)
                    if (normalised) {
                        record.accounts.add(normalised)
                    }
                },
                trackCard(card: RegisteredCard) {
                    const iban = normaliseIban(card.iban)
                    const pan = String(card.pan ?? '').replace(/\s+/g, '')
                    if (iban && pan) {
                        record.cards.push({ iban, pan })
                    }
                },
                trackPayment(payment: RegisteredPayment) {
                    const iban = normaliseIban(payment.accountIban)
                    const paymentId = ensurePaymentIdFormat(payment.paymentId)
                    if (iban && paymentId) {
                        record.payments.push({ accountIban: iban, paymentId })
                    }
                },
            }
        },
        async cleanup() {
            for (const record of records.values()) {
                await cleanupRecord(request, record)
            }
            records.clear()
        },
    }
}

async function cleanupRecord(request: APIRequestContext, record: CleanupRecord) {
    const authToken = await fetchAuthToken(request, record.credentials.dni, record.credentials.password)
    const deletedIbans = new Set<string>()

    for (const payment of [...record.payments].reverse()) {
        await deletePaymentViaApi(
            request,
            record.credentials,
            payment.accountIban,
            payment.paymentId,
            authToken ?? undefined,
        )
    }

    for (const card of [...record.cards].reverse()) {
        await deleteCardViaApi(
            request,
            record.credentials,
            card.iban,
            card.pan,
            authToken ?? undefined,
        )
    }

    for (const iban of [...record.accounts].reverse()) {
        const normalised = normaliseIban(iban)
        await deleteAccountViaApi(request, record.credentials, iban, authToken ?? undefined)
        if (normalised) {
            deletedIbans.add(normalised)
        }
    }

    const residualAccounts = await listAccountsViaApi(request, record.credentials, authToken ?? undefined)
    for (const account of residualAccounts) {
        const iban = normaliseIban(String(account.iban ?? ''))
        if (!iban || deletedIbans.has(iban)) {
            continue
        }
        await deleteAccountViaApi(request, record.credentials, iban, authToken ?? undefined)
        deletedIbans.add(iban)
    }

    await deleteUserViaApi(
        request,
        record.credentials.dni,
        record.credentials.pin,
        record.credentials.password,
        authToken ?? undefined,
    )
}
