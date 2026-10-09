import { test, expect } from '@playwright/test'
import { autoAcceptDialogs, createAccountViaUi, fillPinInputs, logInThroughUi } from '../support/flows'
import { createCleanupManager } from '../support/cleanup'
import {
    buildTestAccount,
    buildTestUser,
    fetchAuthToken,
    registerUserViaApi,
} from '../support/testData'
import { API_BASE_URL } from '../support/env'
import { fetchLatestTransferPaymentId, trackPaymentIfPresent } from '../support/transfers'

function buildWrongPin(pin) {
    if (!pin) {
        return '000000'
    }
    const lastDigit = pin.at(-1)
    const replacement = lastDigit === '0' ? '1' : '0'
    return `${pin.slice(0, -1)}${replacement}`
}

async function fetchExistingAccountIban(request, credentials) {
    const token = await fetchAuthToken(request, credentials.dni, credentials.password)
    if (!token) {
        return ''
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
        return ''
    }
    const payload = await response.json()
    const list = Array.isArray(payload)
        ? payload
        : Array.isArray(payload?.accounts)
            ? payload.accounts
            : Array.isArray(payload?.items)
                ? payload.items
                : []
    const entry = list[0]
    return typeof entry?.iban === 'string' ? entry.iban : ''
}

async function createSourceAccount(page, account) {
    await createAccountViaUi(page, account)
    const card = page.locator('.account-card', { hasText: account.name }).first()
    await expect(card).toBeVisible({ timeout: 15_000 })
    await card.click()
    await expect(page).toHaveURL(/\/accounts\//)
}

/**
 * Backend-backed regression coverage for account transfers.
 */
test.describe('Account transfers', () => {
    let cleanup: ReturnType<typeof createCleanupManager>

    test.beforeEach(({ request }) => {
        cleanup = createCleanupManager(request)
    })

    test.afterEach(async () => {
        await cleanup.cleanup()
    })

    async function bootstrap(page, request) {
        autoAcceptDialogs(page)
        const user = buildTestUser()
        await registerUserViaApi(request, user)
        const handle = cleanup.registerUser({ dni: user.dni, pin: user.pin, password: user.password })
        await logInThroughUi(page, { dni: user.dni, password: user.password })
        const destinationIban = await fetchExistingAccountIban(request, handle.credentials)
        return { user, handle, destinationIban }
    }

    test('sends a transfer when the beneficiary data and PIN are valid', async ({ page, request }) => {
        const { user, handle, destinationIban } = await bootstrap(page, request)
        const account = buildTestAccount({ balance: 900 })
        await createSourceAccount(page, account)
        handle.trackAccount(account.iban)

        await page.getByRole('button', { name: 'New Transfer' }).click()
        await expect(page).toHaveURL(/\/accounts\/.*\/transfer$/)

        await page.getByTestId('transfer-beneficiary-input').fill('Backend QA Contact')
        await page.getByTestId('transfer-iban-input').fill(destinationIban || account.iban)
        await page.getByTestId('transfer-amount-input').fill('45.50')
        await page.getByTestId('transfer-concept-input').fill('Regression transfer')
        await page.getByTestId('transfer-submit-btn').click()

        const pinModal = page.locator('.pin-modal').last()
        await expect(pinModal).toBeVisible({ timeout: 10_000 })
        await fillPinInputs(pinModal.getByTestId('transfer-pin-input'), user.pin)
        await pinModal.getByTestId('transfer-pin-confirm-btn').click()

        const toast = page.locator('.toast')
        await expect(toast).toBeVisible({ timeout: 20_000 })
        await expect(toast.locator('.toast-title')).toHaveText('Transfer sent')
        await toast.locator('.toast-close').click()

        const paymentId = await fetchLatestTransferPaymentId(request, handle.credentials, account.iban)
        trackPaymentIfPresent(handle, account.iban, paymentId)
    })

    test('blocks submission when the amount exceeds the available balance', async ({ page, request }) => {
        const { handle } = await bootstrap(page, request)
        const account = buildTestAccount({ balance: 120 })
        await createSourceAccount(page, account)
        handle.trackAccount(account.iban)

        await page.getByRole('button', { name: 'New Transfer' }).click()
        await expect(page).toHaveURL(/\/accounts\/.*\/transfer$/)

        await page.getByTestId('transfer-beneficiary-input').fill('Test Recipient')
        await page.getByTestId('transfer-iban-input').fill('ES9121000418450200051332')
        await page.getByTestId('transfer-amount-input').fill('5000')

        const error = page.getByTestId('transfer-amount-error')
        await expect(error).toHaveText('Amount exceeds available balance')
        await expect(page.getByTestId('transfer-submit-btn')).toBeDisabled()
    })

    test('shows the IBAN helper error when the format is wrong', async ({ page, request }) => {
        const { handle } = await bootstrap(page, request)
        const account = buildTestAccount({ balance: 400 })
        await createSourceAccount(page, account)
        handle.trackAccount(account.iban)

        await page.getByRole('button', { name: 'New Transfer' }).click()
        await expect(page).toHaveURL(/\/accounts\/.*\/transfer$/)

        await page.getByTestId('transfer-iban-input').fill('ES12 34')
        const ibanStatus = page.getByTestId('transfer-iban-status')
        await expect(ibanStatus).toBeVisible()
        await expect(ibanStatus).toContainText('Invalid IBAN')
        await expect(page.getByTestId('transfer-submit-btn')).toBeDisabled()
    })

    test('highlights the PIN hint when the backend rejects the confirmation', async ({ page, request }) => {
        const { user, handle } = await bootstrap(page, request)
        const account = buildTestAccount({ balance: 500 })
        await createSourceAccount(page, account)
        handle.trackAccount(account.iban)

        await page.getByRole('button', { name: 'New Transfer' }).click()
        await expect(page).toHaveURL(/\/accounts\/.*\/transfer$/)

        await page.getByTestId('transfer-beneficiary-input').fill('Invalid PIN Contact')
        await page.getByTestId('transfer-iban-input').fill('ES9121000418450200051332')
        await page.getByTestId('transfer-amount-input').fill('25')
        await page.getByTestId('transfer-concept-input').fill('Invalid PIN try')
        await page.getByTestId('transfer-submit-btn').click()

        const pinModal = page.locator('.pin-modal').last()
        await expect(pinModal).toBeVisible({ timeout: 10_000 })
        const wrongPin = buildWrongPin(user.pin)
        await fillPinInputs(pinModal.getByTestId('transfer-pin-input'), wrongPin)
        await pinModal.getByTestId('transfer-pin-confirm-btn').click()

        const toast = page.locator('.toast')
        await expect(toast).toBeVisible({ timeout: 10_000 })
        await expect(toast.locator('.toast-title')).toHaveText('Error')
        await expect(toast.locator('.toast-message')).toHaveText(/invalid pin/i)
        await expect(pinModal).toBeVisible()
    })
})

