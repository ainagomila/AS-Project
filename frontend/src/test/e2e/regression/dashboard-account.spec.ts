import { test, expect } from '@playwright/test'
import type { APIRequestContext, Page } from '@playwright/test'
import { autoAcceptDialogs, createAccountViaUi, logInThroughUi } from '../support/flows'
import { createCleanupManager } from '../support/cleanup'
import { buildTestAccount, buildTestUser, registerUserViaApi } from '../support/testData'

/**
 * Regression coverage for dashboard account creation flows.
 */
test.describe('Dashboard account creation', () => {
    let cleanup: ReturnType<typeof createCleanupManager>

    test.beforeEach(({ request }) => {
        cleanup = createCleanupManager(request)
    })

    test.afterEach(async () => {
        await cleanup.cleanup()
    })

    async function bootstrapUser(page: Page, request: APIRequestContext) {
        autoAcceptDialogs(page)
        const user = buildTestUser()
        await registerUserViaApi(request, user)
        const handle = cleanup.registerUser({ dni: user.dni, pin: user.pin, password: user.password })
        await logInThroughUi(page, { dni: user.dni, password: user.password })
        return { user, handle }
    }

    test('adds a new account and refreshes the list on success', async ({ page, request }) => {
        const { handle } = await bootstrapUser(page, request)
        const account = buildTestAccount({ balance: 750 })

        const accountCards = page.locator('.accounts-grid .account-card')
        const accountsBefore = await accountCards.count()

        await createAccountViaUi(page, account)
        handle.trackAccount(account.iban)

        await expect(async () => {
            const currentCount = await accountCards.count()
            expect(currentCount).toBeGreaterThan(accountsBefore)
        }).toPass()
        await expect(page.locator('.account-card', { hasText: account.name })).toBeVisible()
    })

    test('keeps the modal open when the IBAN fails validation', async ({ page, request }) => {
        await bootstrapUser(page, request)

        await page.getByRole('button', { name: 'Add Account' }).click()
        const modal = page.locator('.modal').last()
        await expect(modal).toBeVisible()

        await page.getByTestId('add-account-iban-input').fill('ES12 34')
        await page.getByTestId('add-account-name-input').fill('Invalid IBAN account')
        await page.getByTestId('add-account-bank-input').fill('Bad Bank')
        await page.getByTestId('add-account-balance-input').fill('120')
        await page.getByTestId('add-account-currency-select').selectOption('EUR')

        const submitBtn = page.getByTestId('add-account-submit-btn')
        await expect(submitBtn).toBeDisabled()
        await expect(
            modal.locator('.err', { hasText: 'Invalid Spanish IBAN format (ES + 22 digits).' }),
        ).toBeVisible()
    })

    test('surfaces backend errors when the creation API fails', async ({ page, request }) => {
        const { handle } = await bootstrapUser(page, request)
        const account = buildTestAccount({ balance: 300 })

        await createAccountViaUi(page, account)
        handle.trackAccount(account.iban)
        await expect(page.locator('.account-card', { hasText: account.name })).toBeVisible()

        await page.getByRole('button', { name: 'Add Account' }).click()
        await page.getByTestId('add-account-iban-input').fill(account.iban)
        await page.getByTestId('add-account-name-input').fill(`Duplicate ${account.name}`)
        await page.getByTestId('add-account-bank-input').fill(account.bank)
        await page.getByTestId('add-account-balance-input').fill('250')
        await page.getByTestId('add-account-currency-select').selectOption('EUR')

        const dialogPromise = page.waitForEvent('dialog')
        await page.getByTestId('add-account-submit-btn').click()
        const dialog = await dialogPromise
        expect(dialog.message()).toMatch(/No se pudo crear la cuenta|account/i)
        await page.getByRole('button', { name: 'Cancel' }).click()
    })
})

