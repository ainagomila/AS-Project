import { test, expect } from '@playwright/test'
import type { APIRequestContext, Page } from '@playwright/test'
import { autoAcceptDialogs, createAccountViaUi, createCardViaUi, logInThroughUi } from '../support/flows'
import { createCleanupManager } from '../support/cleanup'
import { buildTestAccount, buildTestCard, buildTestUser, registerUserViaApi } from '../support/testData'

/**
 * Regression coverage for dashboard card creation scenarios.
 */
test.describe('Dashboard card creation', () => {
    let cleanup: ReturnType<typeof createCleanupManager>

    test.beforeEach(({ request }) => {
        cleanup = createCleanupManager(request)
    })

    test.afterEach(async () => {
        await cleanup.cleanup()
    })

    async function bootstrapAccount(page: Page, request: APIRequestContext) {
        autoAcceptDialogs(page)
        const user = buildTestUser()
        await registerUserViaApi(request, user)
        const handle = cleanup.registerUser({ dni: user.dni, pin: user.pin, password: user.password })
        await logInThroughUi(page, { dni: user.dni, password: user.password })

        const account = buildTestAccount()
        await createAccountViaUi(page, account)
        handle.trackAccount(account.iban)
        return { account, handle }
    }

    test('creates a card tied to the selected account when the API accepts it', async ({ page, request }) => {
        const { account, handle } = await bootstrapAccount(page, request)
        const card = buildTestCard({ accountIban: account.iban, bank: account.bank })

        await createCardViaUi(page, card)
        handle.trackCard({ iban: account.iban, pan: card.pan })

        const last4 = card.pan.slice(-4)
        await expect(page.locator('.card-number', { hasText: last4 })).toBeVisible()
    })

    test('validates the CVV length and keeps the modal open when it is invalid', async ({ page, request }) => {
        await bootstrapAccount(page, request)

        await page.getByRole('button', { name: 'Add Card' }).click()
        const modal = page.locator('.modal', { has: page.locator('h3', { hasText: 'Add Card' }) })
        await expect(modal).toBeVisible()

        await page.getByTestId('add-card-number-input').fill('4111111111111111')
        await page.getByTestId('add-card-pin-input').fill('1234')
        await page.getByTestId('add-card-cvv-input').fill('12')
        await page.getByTestId('add-card-expire-month-input').fill('12')
        await page.getByTestId('add-card-expire-year-input').fill('30')
        await page.getByTestId('add-card-type-select').selectOption('DEBIT')
        await page.getByTestId('add-card-account-select').selectOption({ index: 1 })

        const submitBtn = page.getByTestId('add-card-submit-btn')
        await expect(submitBtn).toBeDisabled()
        await expect(modal.locator('.err', { hasText: 'CVV must be 3 digits.' })).toBeVisible()
    })

    test('detects expired cards before sending the request', async ({ page, request }) => {
        await bootstrapAccount(page, request)

        await page.getByRole('button', { name: 'Add Card' }).click()
        const modal = page.locator('.modal', { has: page.locator('h3', { hasText: 'Add Card' }) })
        await expect(modal).toBeVisible()

        await page.getByTestId('add-card-number-input').fill('4111111111111111')
        await page.getByTestId('add-card-pin-input').fill('1234')
        await page.getByTestId('add-card-cvv-input').fill('123')
        await page.getByTestId('add-card-expire-month-input').fill('01')
        await page.getByTestId('add-card-expire-year-input').fill('20')
        await page.getByTestId('add-card-type-select').selectOption('DEBIT')
        await page.getByTestId('add-card-account-select').selectOption({ index: 1 })

        await expect(modal.locator('.err', { hasText: 'Card is expired.' })).toBeVisible()
        await expect(page.getByTestId('add-card-submit-btn')).toBeDisabled()
    })

    test('shows an alert when the backend rejects the card creation', async ({ page, request }) => {
        const { account, handle } = await bootstrapAccount(page, request)
        const card = buildTestCard({ accountIban: account.iban, bank: account.bank })

        await createCardViaUi(page, card)
        handle.trackCard({ iban: account.iban, pan: card.pan })
        await expect(page.locator('.card-number', { hasText: card.pan.slice(-4) })).toBeVisible()

        await page.getByRole('button', { name: 'Add Card' }).click()
        await page.getByTestId('add-card-number-input').fill(card.pan)
        await page.getByTestId('add-card-pin-input').fill(card.cardPin)
        await page.getByTestId('add-card-cvv-input').fill(card.cvv)
        await page.getByTestId('add-card-expire-month-input').fill(card.expireMonth)
        await page.getByTestId('add-card-expire-year-input').fill(card.expireYear)
        await page.getByTestId('add-card-type-select').selectOption(card.type)
        await page.getByTestId('add-card-account-select').selectOption(account.iban)

        const dialogPromise = page.waitForEvent('dialog')
        await page.getByTestId('add-card-submit-btn').click()
        const dialog = await dialogPromise
        expect(dialog.message()).toMatch(/No se pudo crear la tarjeta|card|Ja existeix una targeta/i)
        await page.getByRole('button', { name: 'Cancel' }).click()
    })
})

