import { test, expect } from '@playwright/test'
import { autoAcceptDialogs, logInThroughUi } from './support/flows'
import { createCleanupManager } from './support/cleanup'
import { buildTestUser, registerUserViaApi } from './support/testData'

test.describe('Login experience', () => {
    let cleanup: ReturnType<typeof createCleanupManager>

    test.beforeEach(({ page, request }) => {
        autoAcceptDialogs(page)
        cleanup = createCleanupManager(request)
    })

    test.afterEach(async () => {
        await cleanup.cleanup()
    })

    test('logs in, shows the dashboard, and logs out cleanly', async ({ page, request }) => {
        const user = buildTestUser()
        await registerUserViaApi(request, user)
        cleanup.registerUser({ dni: user.dni, pin: user.pin, password: user.password })

        await logInThroughUi(page, { dni: user.dni, password: user.password })
        await expect(page.locator('.logout-btn')).toBeVisible()

        await page.locator('.logout-btn').click()
        await expect(page).toHaveURL(/\/$/)

        // The session is really gone: a protected page sends us back to the sign-in page.
        await page.goto('/dashboard')
        await expect(page).toHaveURL(/\/accounts\/login\//)
    })

    test('requires credentials before submitting the login form', async ({ page }) => {
        await page.goto('/login')
        await page.locator('.login-btn').click()
        await expect(page).toHaveURL(/\/accounts\/login\//)
        await expect(page.locator('.error')).toHaveCount(0)
    })

    test('rejects invalid passwords with an error message', async ({ page, request }) => {
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

    test('redirects unauthenticated dashboard visits to the sign-in page', async ({ page }) => {
        await page.goto('/dashboard')
        await expect(page).toHaveURL(/\/accounts\/login\//)
        await expect(page.getByRole('heading', { name: 'Log in' })).toBeVisible()
    })
})
