import { test, expect } from '@playwright/test'
import { autoAcceptDialogs, completeSignupForm, submitLoginForm } from '../support/flows'
import { createCleanupManager } from '../support/cleanup'
import { buildTestUser, registerUserViaApi } from '../support/testData'

/**
 * Backend-backed version of the former "Signup guardrails" regression block.
 */
test.describe('Signup guardrails', () => {
    let cleanup: ReturnType<typeof createCleanupManager>

    test.beforeEach(({ request }) => {
        cleanup = createCleanupManager(request)
    })

    test.afterEach(async () => {
        await cleanup.cleanup()
    })

    test('registers a new user when every upstream dependency succeeds', async ({ page }) => {
        autoAcceptDialogs(page)
        const user = buildTestUser()
        cleanup.registerUser({ dni: user.dni, pin: user.pin, password: user.password })

        await page.goto('/signup')
        await completeSignupForm(page, user)
        await page.getByTestId('signup-submit-btn').click()

        await expect(page).toHaveURL(/\/accounts\/login\//)
        await submitLoginForm(page, { dni: user.dni, password: user.password })
        await expect(page).toHaveURL(/\/dashboard$/)
        await expect(page.getByRole('heading', { name: 'Your Bank Accounts' })).toBeVisible()
    })

    test('rejects malformed phone numbers before reaching the backend', async ({ page }) => {
        await page.goto('/signup')
        const user = buildTestUser()
        await completeSignupForm(page, user)
        await page.getByTestId('signup-phone-input').fill('123')

        const submitBtn = page.getByTestId('signup-submit-btn')
        await expect(submitBtn).toBeDisabled()
        await expect(
            page.getByText('Phone must be a Spanish number (+34, 9 digits).', { exact: false }),
        ).toBeVisible()
    })

    test('answers a taken DNI exactly like a new sign-up, without an error', async ({ page, request }) => {
        const dialogs: string[] = []
        page.on('dialog', (dialog) => {
            dialogs.push(dialog.message())
            void dialog.accept()
        })
        const existing = buildTestUser()
        await registerUserViaApi(request, existing)
        cleanup.registerUser({ dni: existing.dni, pin: existing.pin, password: existing.password })

        await page.goto('/signup')
        await completeSignupForm(page, buildTestUser({ dni: existing.dni }))
        await page.getByTestId('signup-submit-btn').click()

        await expect(page).toHaveURL(/\/accounts\/login\//)
        expect(dialogs).toEqual([])
    })

    test('blocks password mismatches without contacting the API', async ({ page }) => {
        await page.goto('/signup')
        const user = buildTestUser()
        await completeSignupForm(page, user, { confirmPassword: `${user.password}!` })

        const submitBtn = page.getByTestId('signup-submit-btn')
        await expect(page.getByText('Passwords do not match')).toBeVisible()
        await expect(submitBtn).toBeDisabled()
    })
})

