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

    test('logs in successfully with valid credentials', async ({ page, request }) => {
        autoAcceptDialogs(page)
        const user = buildTestUser()
        await registerUserViaApi(request, user)
        cleanup.registerUser({ dni: user.dni, pin: user.pin, password: user.password })

        await logInThroughUi(page, { dni: user.dni, password: user.password })
        await expect(page).toHaveURL(/\/dashboard$/)
        await expect(page.locator('.account-card')).toBeVisible()
        await page.locator('.logout-btn').click()
        await expect(page).toHaveURL(/\/$/)
    })

    test('does not submit an empty login form', async ({ page }) => {
        await page.goto('/login')
        await page.locator('.login-btn').click()
        await expect(page).toHaveURL(/\/accounts\/login\//)
    })

    test('shows the backend error for rejected logins', async ({ page, request }) => {
        const user = buildTestUser()
        await registerUserViaApi(request, user)
        cleanup.registerUser({ dni: user.dni, pin: user.pin, password: user.password })

        await page.goto('/login')
        await page.locator('#id_username').fill(user.dni)
        await page.locator('#id_password').fill(`${user.password}!`)
        await page.locator('.login-btn').click()

        await expect(page.locator('.error')).toHaveText('Incorrect DNI or password.')
        await expect(page).toHaveURL(/\/accounts\/login\//)
    })
})
