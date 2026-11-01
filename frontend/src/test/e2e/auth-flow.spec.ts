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
        const user = buildTestUser()
        await registerUserViaApi(request, user)
        cleanup.registerUser({ dni: user.dni, pin: user.pin, password: user.password })

        await page.goto('/login')
        await page.locator('#id_username').fill(user.dni)
        await page.locator('#id_password').fill(`${user.password}x`)
        await page.locator('.login-btn').click()

        await expect(page.locator('.error')).toHaveText('Incorrect DNI or password.')
        await expect(page).toHaveURL(/\/accounts\/login\//)
    })

    test('rejects login for an unknown DNI', async ({ page }) => {
        await page.goto('/login')
        await page.locator('#id_username').fill('00000000T')
        await page.locator('#id_password').fill('Secret123')
        await page.locator('.login-btn').click()

        await expect(page.locator('.error')).toHaveText('Incorrect DNI or password.')
    })

    test('redirects unauthenticated dashboard access to login', async ({ page }) => {
        await page.goto('/dashboard')
        await expect(page).toHaveURL(/\/accounts\/login\//)
    })
})
