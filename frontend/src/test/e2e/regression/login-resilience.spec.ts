import { test, expect } from '@playwright/test'
import { autoAcceptDialogs, logInThroughUi } from '../support/flows'
import { createCleanupManager } from '../support/cleanup'
import { buildTestUser, registerUserViaApi } from '../support/testData'

/**
 * Mirrors the original regression-matrix "Login resilience" scenarios but uses the live backend.
 */
test.describe('Login resilience', () => {
    let cleanup: ReturnType<typeof createCleanupManager>

    test.beforeEach(({ request }) => {
        cleanup = createCleanupManager(request)
    })

    test.afterEach(async () => {
        await cleanup.cleanup()
    })

    test('logs in successfully when API returns a valid session', async ({ page, request }) => {
        autoAcceptDialogs(page)
        const user = buildTestUser()
        await registerUserViaApi(request, user)
        cleanup.registerUser({ dni: user.dni, pin: user.pin, password: user.password })

        await logInThroughUi(page, { dni: user.dni, password: user.password })
        await expect(page).toHaveURL(/\/dashboard$/)
        await expect(page.locator('.account-card')).toBeVisible()
        await page.locator('.logout-btn').click()
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
        expect(dialog.message()).toMatch(/enter your credentials|credencials?.*incompletes?/i)
        await expect(page).toHaveURL(/\/login$/)
    })

    test('surfaces backend error messages for rejected logins', async ({ page, request }) => {
        autoAcceptDialogs(page)
        const user = buildTestUser()
        await registerUserViaApi(request, user)
        cleanup.registerUser({ dni: user.dni, pin: user.pin, password: user.password })

        await page.goto('/login')
        await page.getByTestId('login-dni-input').fill(user.dni)
        await page.getByTestId('login-password-input').fill(`${user.password}!`)

        const dialogPromise = page.waitForEvent('dialog')
        await page.getByTestId('login-submit-btn').click()
        const dialog = await dialogPromise
        expect(dialog.message()).toMatch(/invalid dni or password|credencials? inv/i)
        await expect(page).toHaveURL(/\/login$/)
    })
})

