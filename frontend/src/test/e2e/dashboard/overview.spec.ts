import { test, expect } from '@playwright/test'
import {
    autoAcceptDialogs,
    createAccountViaUi,
    createCardViaUi,
    logInThroughUi,
} from '../support/flows'
import { createCleanupManager } from '../support/cleanup'
import { buildTestAccount, buildTestCard, buildTestUser, registerUserViaApi } from '../support/testData'

test.describe('Dashboard experience', () => {
    let cleanup: ReturnType<typeof createCleanupManager>

    test.beforeEach(({ request }) => {
        cleanup = createCleanupManager(request)
    })

    test.afterEach(async () => {
        await cleanup.cleanup()
    })

    test('lists balances and lets the user add new accounts and cards safely', async ({ page, request }) => {
        autoAcceptDialogs(page)

        const user = buildTestUser()
        await registerUserViaApi(request, user)
        const userHandle = cleanup.registerUser({ dni: user.dni, pin: user.pin, password: user.password })

        await logInThroughUi(page, { dni: user.dni, password: user.password })

        await expect(page.getByRole('heading', { name: 'Your Bank Accounts' })).toBeVisible()
        await expect(page.getByRole('heading', { name: 'Your Cards' })).toBeVisible()

        const newAccount = buildTestAccount()
        await createAccountViaUi(page, newAccount)
        userHandle.trackAccount(newAccount.iban)

        const cardsList = page.locator('.cards-row .card-item')
        const initialCards = await cardsList.count()

        const card = buildTestCard({ accountIban: newAccount.iban, bank: newAccount.bank })
        await createCardViaUi(page, card)
        userHandle.trackCard({ iban: newAccount.iban, pan: card.pan })

        await expect(cardsList).toHaveCount(initialCards + 1)
        await expect(page.locator('.card-number', { hasText: card.pan.slice(-4) })).toBeVisible()
    })

    test('prevents submitting malformed IBANs when adding an account', async ({ page, request }) => {
        autoAcceptDialogs(page)

        const user = buildTestUser()
        await registerUserViaApi(request, user)
        cleanup.registerUser({ dni: user.dni, pin: user.pin, password: user.password })

        await logInThroughUi(page, { dni: user.dni, password: user.password })

        await page.getByRole('button', { name: 'Add Account' }).click()
        const modal = page.locator('.modal').last()

        await page.getByTestId('add-account-iban-input').fill('ES12 34')
        await page.getByTestId('add-account-name-input').fill('Emergency fund')
        await page.getByTestId('add-account-bank-input').fill('Invalid Bank')
        await page.getByTestId('add-account-currency-select').selectOption('EUR')

        const submitBtn = page.getByTestId('add-account-submit-btn')
        await expect(submitBtn).toBeDisabled()
        await expect(
            modal.locator('.err', { hasText: 'Invalid Spanish IBAN format (ES + 22 digits).' }),
        ).toBeVisible()
        await expect(modal).toBeVisible()
    })

    test('keeps the add-card modal open until the data passes client validations', async ({ page, request }) => {
        autoAcceptDialogs(page)

        const user = buildTestUser()
        await registerUserViaApi(request, user)
        const userHandle = cleanup.registerUser({ dni: user.dni, pin: user.pin, password: user.password })

        await logInThroughUi(page, { dni: user.dni, password: user.password })

        const account = buildTestAccount()
        await createAccountViaUi(page, account)
        userHandle.trackAccount(account.iban)

        const cardsBefore = await page.locator('.cards-row .card-item').count()
        let cardPostRequests = 0
        page.on('request', (req) => {
            if (req.method() === 'POST' && req.url().includes('/cards')) {
                cardPostRequests += 1
            }
        })

        await page.getByRole('button', { name: 'Add Card' }).click()
        const modal = page.locator('.modal', {
            has: page.locator('h3', { hasText: 'Add Card' }),
        })
        await expect(modal).toBeVisible()

        await page.getByTestId('add-card-number-input').fill('4111 11')
        await page.getByTestId('add-card-pin-input').fill('12')
        await page.getByTestId('add-card-type-select').selectOption('DEBIT')
        await page.getByTestId('add-card-account-select').selectOption({ index: 1 })

        const submitBtn = page.getByTestId('add-card-submit-btn')
        await expect(submitBtn).toBeDisabled()

        await expect(modal).toBeVisible()
        await expect(modal.locator('.err')).toContainText(['Card number must be 16 digits.', 'PIN must be 4 digits.'])
        expect(cardPostRequests).toBe(0)
        await expect(page.locator('.cards-row .card-item')).toHaveCount(cardsBefore)
    })

    test('header buttons open profile and support logout navigation', async ({ page, request }) => {
        autoAcceptDialogs(page)

        const user = buildTestUser()
        await registerUserViaApi(request, user)
        cleanup.registerUser({ dni: user.dni, pin: user.pin, password: user.password })

        await logInThroughUi(page, { dni: user.dni, password: user.password })

        const loginUrlPattern = /\/accounts\/login\//
        const dashboardUrlPattern = /\/dashboard(\?.*)?$/

        await page.getByRole('button', { name: 'Open settings' }).click()
        await expect(page).toHaveURL(/\/profile$/)

        await page.getByRole('button', { name: 'Cancel' }).click()
        await expect(page).toHaveURL(dashboardUrlPattern)

        await page.locator('button.logout-btn').click()
        await expect(page).toHaveURL(/\/$/)

        await page.goto('/dashboard')
        await expect(page).toHaveURL(loginUrlPattern)
    })

    test('dashboard sections expose hash anchors for scrolling', async ({ page, request }) => {
        autoAcceptDialogs(page)

        const user = buildTestUser()
        await registerUserViaApi(request, user)
        cleanup.registerUser({ dni: user.dni, pin: user.pin, password: user.password })

        await logInThroughUi(page, { dni: user.dni, password: user.password })

        const sections: Array<{ label: string; hash: `#${string}` }> = [
            { label: 'Accounts', hash: '#accounts' },
            { label: 'Cards', hash: '#cards' },
        ]

        for (const { label, hash } of sections) {
            const targetSection = page.locator(hash)
            await expect(targetSection, `${label} section should exist`).toBeVisible()

            await page.evaluate((sectionHash) => {
                const el = document.querySelector(sectionHash)
                if (!el) {
                    return
                }
                el.scrollIntoView({ behavior: 'auto', block: 'start' })
                window.location.hash = sectionHash
            }, hash)

            await expect.poll(async () => page.evaluate(() => window.location.hash)).toBe(hash)
            await expect(targetSection).toBeInViewport()
        }
    })
})

