import { expect, Locator, Page } from '@playwright/test'
import { TestUser } from './testData'

const floatingFieldSelector = ':is(.input-field, .form-field)'

const floatingField = (page: Page, labelText: string) =>
    page
        .locator(floatingFieldSelector, { has: page.locator('label', { hasText: labelText }) })
        .locator('input')
        .first()

export function getFloatingField(page: Page, labelText: string) {
    return floatingField(page, labelText)
}

export function autoAcceptDialogs(page: Page) {
    page.on('dialog', (dialog) => dialog.accept().catch(() => undefined))
}

export type SignupFormOptions = {
    acceptTerms?: boolean
    confirmPassword?: string
}

export async function completeSignupForm(
    page: Page,
    user: TestUser,
    options: SignupFormOptions = {},
) {
    const { acceptTerms = true, confirmPassword } = options

    await page.getByTestId('signup-name-input').fill(user.name)
    await page.getByTestId('signup-dni-input').fill(user.dni)
    await page.getByTestId('signup-email-input').fill(user.email)
    await page.getByTestId('signup-phone-input').fill(user.phoneLocal)
    await page.getByTestId('signup-password-input').fill(user.password)
    await page.getByTestId('signup-confirm-password-input').fill(confirmPassword ?? user.password)
    await page.getByTestId('signup-pin-input').fill(user.pin)
    await page.getByTestId('signup-birthday-input').fill(user.birthdateDisplay)
    await page.getByTestId('signup-gender-select').selectOption(user.gender)

    if (acceptTerms) {
        await page.getByTestId('signup-terms-checkbox').check()
    }
}

export async function logInThroughUi(page: Page, credentials: { dni: string; password: string }) {
    await page.goto('/login')
    await page.getByTestId('login-dni-input').fill(credentials.dni)
    await page.getByTestId('login-password-input').fill(credentials.password)
    const [response] = await Promise.all([
        page.waitForResponse((res) =>
            res.url().includes('/auth/login') && res.request().method() === 'POST',
        ),
        page.getByTestId('login-submit-btn').click(),
    ])

    if (!response.ok()) {
        const body = await response.text().catch(() => '')
        throw new Error(`Login request failed: ${response.status()} ${body}`)
    }

    await expect(page).toHaveURL(/\/dashboard$/)
}

export async function fillPinInputs(container: Locator, pin: string) {
    const digits = pin.split('')
    for (let i = 0; i < digits.length; i += 1) {
        const input = container.nth(i)
        await input.fill(digits[i])
    }
}

export type AccountFormData = {
    iban: string
    name: string
    bank: string
    balance: number
    currency: string
}

export async function createAccountViaUi(page: Page, account: AccountFormData) {
    await page.getByRole('button', { name: 'Add Account' }).click()
    await page.getByTestId('add-account-iban-input').fill(account.iban)
    await page.getByTestId('add-account-name-input').fill(account.name)
    await page.getByTestId('add-account-bank-input').fill(account.bank)
    await page.getByTestId('add-account-balance-input').fill(String(account.balance))
    await page.getByTestId('add-account-currency-select').selectOption(account.currency)
    await page.getByTestId('add-account-submit-btn').click()
    const newAccountCard = page.locator('.account-card', { hasText: account.name }).first()
    await expect(newAccountCard).toBeVisible({ timeout: 15_000 })
}

export type CardFormData = {
    pan: string
    cardPin: string
    cvv: string
    expireMonth: string
    expireYear: string
    alias: string
    type: string
    accountIban: string
}

export async function createCardViaUi(page: Page, card: CardFormData) {
    if (!card.accountIban) {
        throw new Error('createCardViaUi requires accountIban to be set')
    }

    await page.getByRole('button', { name: 'Add Card' }).click()
    await page.getByTestId('add-card-number-input').fill(card.pan)
    await page.getByTestId('add-card-pin-input').fill(card.cardPin)
    await page.getByTestId('add-card-cvv-input').fill(card.cvv)
    await page.getByTestId('add-card-expire-month-input').fill(card.expireMonth)
    await page.getByTestId('add-card-expire-year-input').fill(card.expireYear)
    await page.getByTestId('add-card-type-select').selectOption(card.type)
    if (card.alias) {
        await page.getByTestId('add-card-alias-input').fill(card.alias)
    }
    await page.getByTestId('add-card-account-select').selectOption(card.accountIban)
    await page.getByTestId('add-card-submit-btn').click()
    const lastFour = card.pan.slice(-4)
    const newCardNumber = page.locator('.card-number', { hasText: lastFour })
    await expect(newCardNumber).toBeVisible({ timeout: 15_000 })
}

