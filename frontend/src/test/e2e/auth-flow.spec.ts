import { test, expect } from '@playwright/test'
import { autoAcceptDialogs, logInThroughUi } from './support/flows'
import { createCleanupManager } from './support/cleanup'
import { buildTestUser, registerUserViaApi } from './support/testData'

test.describe('Authentication flow', () => {
    let cleanup: ReturnType<typeof createCleanupManager>

    test.beforeEach(({ request }) => {
        cleanup = createCleanupManager(request)
    })

    test.afterEach(async () => {
        await cleanup.cleanup()
    })

    test('allows login with valid credentials', async ({ page, request }) => {
        autoAcceptDialogs(page)
        const user = buildTestUser()
        await registerUserViaApi(request, user)
        cleanup.registerUser({ dni: user.dni, pin: user.pin, password: user.password })

        await logInThroughUi(page, { dni: user.dni, password: user.password })
        await expect(page.getByText('Your Cards')).toBeVisible()
        await page.locator('.logout-btn').click()
    })

    test('rejects login with invalid password', async ({ page, request }) => {
        autoAcceptDialogs(page)
        const user = buildTestUser()
        await registerUserViaApi(request, user)
        cleanup.registerUser({ dni: user.dni, pin: user.pin, password: user.password })

        await page.goto('/login')
        await page.getByTestId('login-dni-input').fill(user.dni)
        await page.getByTestId('login-password-input').fill(`${user.password}x`)

        const dialogPromise = page.waitForEvent('dialog')
        await page.getByTestId('login-submit-btn').click()
        const dialog = await dialogPromise
        expect(dialog.message()).toMatch(/invalid dni or password|credencials?\s+inv(?:a|\u00E0)lides?/i)
        await expect(page).toHaveURL(/\/login$/)
    })

    test('shows an alert when trying to submit empty credentials', async ({ page }) => {
        autoAcceptDialogs(page)
        await page.goto('/login')
        await page.getByTestId('login-dni-input').fill('   ')
        await page.getByTestId('login-password-input').fill('Secret123')

        const dialogPromise = page.waitForEvent('dialog')
        await page.getByTestId('login-submit-btn').click()
        const dialog = await dialogPromise
        expect(dialog.message()).toMatch(/enter your credentials|credencials?.*(incompletes?|inv(?:a|\u00E0)lides?)/i)
        await expect(page).toHaveURL(/\/login$/)
    })

    test('redirects unauthenticated dashboard access to login', async ({ page }) => {
        await page.goto('/dashboard')
        await expect(page).toHaveURL(/\/login(\?.*)?$/)
    })
})

