import { test, expect } from '@playwright/test'
import { autoAcceptDialogs, createAccountViaUi, fillPinInputs, logInThroughUi } from './support/flows'
import { createCleanupManager } from './support/cleanup'
import { buildTestAccount, buildTestUser, registerUserViaApi } from './support/testData'

function buildWrongPin(pin) {
    if (!pin) {
        return '000000'
    }
    const lastDigit = pin.at(-1)
    const replacement = lastDigit === '0' ? '1' : '0'
    return `${pin.slice(0, -1)}${replacement}`
}

test.describe('Account transfers', () => {
    let cleanup: ReturnType<typeof createCleanupManager>

    test.beforeEach(({ page, request }) => {
        autoAcceptDialogs(page)
        cleanup = createCleanupManager(request)
    })

    test.afterEach(async () => {
        await cleanup.cleanup()
    })

    test('surfaces backend errors when the PIN confirmation is invalid', async ({ page, request }) => {
        const user = buildTestUser()
        await registerUserViaApi(request, user)
        const userHandle = cleanup.registerUser({ dni: user.dni, pin: user.pin, password: user.password })

        await logInThroughUi(page, { dni: user.dni, password: user.password })

        const account = buildTestAccount({ balance: 500 })
        await createAccountViaUi(page, account)
        userHandle.trackAccount(account.iban)

        const accountCard = page.locator('.account-card', { hasText: account.name }).first()
        await expect(accountCard).toBeVisible({ timeout: 15_000 })
        await accountCard.click()
        await expect(page).toHaveURL(/\/accounts\//)

        await page.getByRole('button', { name: 'New Transfer' }).click()
        await expect(page).toHaveURL(/\/accounts\/.*\/transfer$/)

        const validIban = 'ES91 2100 0418 4502 0005 1332'
        await page.getByTestId('transfer-beneficiary-input').fill('Lucia QA')
        await page.getByTestId('transfer-iban-input').fill(validIban)
        await page.getByTestId('transfer-amount-input').fill('50.25')
        await page.getByTestId('transfer-concept-input').fill('QA run')

        await page.getByTestId('transfer-submit-btn').click()

        const pinModal = page.locator('.modal-card.pin-modal').last()
        await expect(pinModal).toBeVisible({ timeout: 10_000 })
        const wrongPin = buildWrongPin(user.pin)
        await fillPinInputs(pinModal.getByTestId('transfer-pin-input'), wrongPin)
        await pinModal.getByTestId('transfer-pin-confirm-btn').click()

        const toast = page.locator('.toast')
        await expect(toast).toBeVisible({ timeout: 10_000 })
        await expect(toast.locator('.toast-title')).toHaveText('Error')
        await expect(toast.locator('.toast-message')).toHaveText(/invalid pin/i)
        await pinModal.getByRole('button', { name: 'Cancel' }).click()
        await expect(pinModal).toBeHidden()
    })

    test('blocks submission when IBAN or amount inputs are invalid', async ({ page, request }) => {
        const user = buildTestUser()
        await registerUserViaApi(request, user)
        const userHandle = cleanup.registerUser({ dni: user.dni, pin: user.pin, password: user.password })

        await logInThroughUi(page, { dni: user.dni, password: user.password })

        const account = buildTestAccount({ balance: 150 })
        await createAccountViaUi(page, account)
        userHandle.trackAccount(account.iban)

        const accountCard = page.locator('.account-card', { hasText: account.name }).first()
        await expect(accountCard).toBeVisible({ timeout: 15_000 })
        await accountCard.click()
        await expect(page).toHaveURL(/\/accounts\//)

        await page.getByRole('button', { name: 'New Transfer' }).click()
        await expect(page).toHaveURL(/\/accounts\/.*\/transfer$/)

        await page.getByTestId('transfer-beneficiary-input').fill('Test Recipient')
        await page.getByTestId('transfer-iban-input').fill('ES12 34')

        const ibanStatus = page.getByTestId('transfer-iban-status')
        await expect(ibanStatus).toBeVisible()
        await expect(ibanStatus).toContainText('Invalid IBAN')
        await expect(page.getByTestId('transfer-submit-btn')).toBeDisabled()

        const validIban = 'ES91 2100 0418 4502 0005 1332'
        await page.getByTestId('transfer-iban-input').fill(validIban)
        await expect(page.getByTestId('transfer-iban-status')).toContainText('IBAN format OK')

        await page.getByTestId('transfer-amount-input').fill(String(account.balance + 50))
        const amountError = page.getByTestId('transfer-amount-error')
        await expect(amountError).toBeVisible()
        await expect(amountError).toHaveText('Amount exceeds available balance')
        await expect(page.getByTestId('transfer-submit-btn')).toBeDisabled()
    })
})

