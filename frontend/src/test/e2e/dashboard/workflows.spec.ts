import { test, expect, request as playwrightRequest, type APIRequestContext } from '@playwright/test'
import { autoAcceptDialogs, logInThroughUi } from '../support/flows'
import { createCleanupManager, type UserCleanupHandle } from '../support/cleanup'
import { buildTestUser, computeCvv, generatePan, registerUserViaApi } from '../support/testData'

// Generar IBAN espaÃ±ol vÃ¡lido con dÃ­gitos de control correctos
function generateValidSpanishIban(): string {
    // Generar 20 dÃ­gitos aleatorios (cÃ³digo banco + sucursal + DC + cuenta)
    const randomPart = Array.from({ length: 20 }, () => Math.floor(Math.random() * 10)).join('')

    // Calcular dÃ­gitos de control segÃºn algoritmo IBAN
    // IBAN = ES + 2 dÃ­gitos de control + 20 dÃ­gitos
    const bban = randomPart
    const numericIban = bban + '142800' // ES = 1428, 00 es el DC temporal

    // Calcular mÃ³dulo 97
    let remainder = BigInt(numericIban) % 97n
    const checkDigits = (98n - remainder).toString().padStart(2, '0')

    return `ES${checkDigits}${bban}`
}

function requireAccountIban(value: string | undefined): string {
    if (!value) {
        throw new Error('IBAN not available for card creation test')
    }
    return value
}

function formatIbanForUi(value: string): string {
    return value.replace(/(.{4})/g, '$1 ').trim()
}

test.describe.serial('Dashboard workflows', () => {
    let user: { dni: string; password: string; pin: string }
    let accountName: string
    let iban: string
    let cleanup: ReturnType<typeof createCleanupManager>
    let apiContext: APIRequestContext
    let cleanupHandle: UserCleanupHandle | null = null

    test.beforeAll(async () => {
        apiContext = await playwrightRequest.newContext()
        cleanup = createCleanupManager(apiContext)
        const testUser = buildTestUser()
        user = { dni: testUser.dni, password: testUser.password, pin: testUser.pin }

        await registerUserViaApi(apiContext, testUser)
        cleanupHandle = cleanup.registerUser({ dni: user.dni, pin: user.pin, password: user.password })
    })

    test.afterAll(async () => {
        await cleanup.cleanup()
        await apiContext.dispose()
    })

    test('creates a new bank account from the dashboard', async ({ page }) => {
        autoAcceptDialogs(page)
        accountName = `Account ${Date.now()}`
        // Generar IBAN espaÃ±ol vÃ¡lido con dÃ­gitos de control
        iban = generateValidSpanishIban()
        const formattedIban = formatIbanForUi(iban)

        await logInThroughUi(page, user)

        await page.getByRole('button', { name: 'Add Account' }).click()
        const modal = page.locator('.modal')
        await expect(modal.getByText('Add Bank Account')).toBeVisible()

        await page.getByTestId('add-account-iban-input').fill(iban)
        await page.getByTestId('add-account-name-input').fill(accountName)
        await page.getByTestId('add-account-bank-input').fill('Kofre Test Bank')
        await page.getByTestId('add-account-currency-select').selectOption('EUR')

        await page.getByTestId('add-account-submit-btn').click()
        await expect(modal).toBeHidden({ timeout: 15_000 })

        cleanupHandle?.trackAccount(iban)

        const accountCard = page.locator('.account-card').filter({ hasText: formattedIban })
        await expect(accountCard).toBeVisible({ timeout: 20_000 })
        await page.locator('.logout-btn').click()
    })

    test('adds a card linked to the newly created account', async ({ page }) => {
        autoAcceptDialogs(page)
        await logInThroughUi(page, user)

        await page.getByRole('button', { name: 'Add Card' }).click()
        const modal = page.locator('.modal')
        await expect(modal.getByRole('heading', { name: 'Add Card' })).toBeVisible()

        const cardNumber = generatePan()
        const expireYear = `${(new Date().getFullYear() + 2) % 100}`
        await page.getByTestId('add-card-number-input').fill(cardNumber)
        await page.getByTestId('add-card-pin-input').fill('1234')
        await page.getByTestId('add-card-cvv-input').fill(computeCvv(cardNumber, `12/${expireYear}`))
        await page.getByTestId('add-card-expire-month-input').fill('12')
        await page.getByTestId('add-card-expire-year-input').fill(expireYear)
        await page.getByTestId('add-card-type-select').selectOption('DEBIT')
        await page.getByTestId('add-card-alias-input').fill('Test Card')
        const accountIban = requireAccountIban(iban)
        await page.getByTestId('add-card-account-select').selectOption(accountIban)

        await page.getByTestId('add-card-submit-btn').click()
        await expect(modal).toBeHidden({ timeout: 15_000 })

        const last4 = cardNumber.slice(-4)
        const cardRow = page.locator('.card-item').filter({ hasText: last4 })
        await expect(cardRow).toBeVisible({ timeout: 20_000 })

        cleanupHandle?.trackCard({ iban: requireAccountIban(iban), pan: cardNumber })

        await page.locator('.logout-btn').click()
    })

    test('opens the account detail view with transactions', async ({ page }) => {
        autoAcceptDialogs(page)
        await logInThroughUi(page, user)

        const formattedIban = formatIbanForUi(requireAccountIban(iban))
        const accountCard = page.locator('.account-card').filter({ hasText: formattedIban }).first()
        await expect(accountCard).toBeVisible({ timeout: 15_000 })
        await accountCard.click()

        await page.waitForURL('**/accounts/**', { timeout: 20_000 })
        await expect(page.getByText('Available Balance')).toBeVisible()
        const transactionsHeading = page.getByRole('heading', { name: 'Transactions' }).first()
        await expect(transactionsHeading).toBeVisible()

        await page.locator('button.back-btn').click()
        await page.waitForURL('**/dashboard', { timeout: 15_000 })
        await page.locator('.logout-btn').click()
    })
})

