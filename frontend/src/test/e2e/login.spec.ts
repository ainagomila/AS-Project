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

        const token = await page.evaluate(() => window.localStorage.getItem('authToken'))
        expect(token).toBeTruthy()

        await page.locator('.logout-btn').click()
        await expect(page).toHaveURL(/\/login$/)

        const tokenAfterLogout = await page.evaluate(() => window.localStorage.getItem('authToken'))
        expect(tokenAfterLogout).toBeNull()
    })

    test('requires credentials before attempting login', async ({ page }) => {
        const loginRequests: string[] = []
        page.on('request', (request) => {
            if (request.url().includes('/auth/login')) {
                loginRequests.push(request.url())
            }
        })

        await page.goto('/login')
        await page.getByTestId('login-submit-btn').click()
        await expect(page).toHaveURL(/\/login$/)
        expect(loginRequests).toHaveLength(0)
    })

    test('rejects invalid passwords with a descriptive alert', async ({ page, request }) => {
        const user = buildTestUser()
        await registerUserViaApi(request, user)
        cleanup.registerUser({ dni: user.dni, pin: user.pin, password: user.password })

        await page.goto('/login')
        await page.getByTestId('login-dni-input').fill(user.dni)
        await page.getByTestId('login-password-input').fill(`${user.password}!`)

        const dialogPromise = page.waitForEvent('dialog')
        await page.getByTestId('login-submit-btn').click()
        const dialog = await dialogPromise
        expect(dialog.message()).toMatch(/invalid dni or password|credencials inv/i)
        await expect(page).toHaveURL(/\/login$/)
    })

    test('redirects unauthenticated dashboard visits back to the login page', async ({ page }) => {
        await page.goto('/dashboard')
        await expect(page).toHaveURL(/\/login(\?.*)?$/)
        await expect(page.getByRole('heading', { name: 'Log in' })).toBeVisible()
    })
})

