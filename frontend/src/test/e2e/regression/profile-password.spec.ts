import { test, expect } from '@playwright/test'
import type { APIRequestContext, Page } from '@playwright/test'
import { autoAcceptDialogs, fillPinInputs, getFloatingField, logInThroughUi, useInvalidAccessToken } from '../support/flows'
import { createCleanupManager } from '../support/cleanup'
import { buildTestUser, registerUserViaApi } from '../support/testData'

async function bootstrapProfile(
    page: Page,
    request: APIRequestContext,
    cleanup: ReturnType<typeof createCleanupManager>,
) {
    autoAcceptDialogs(page)
    const user = buildTestUser()
    await registerUserViaApi(request, user)
    cleanup.registerUser({ dni: user.dni, pin: user.pin, password: user.password })
    await logInThroughUi(page, { dni: user.dni, password: user.password })
    await page.getByRole('button', { name: 'Open settings' }).click()
    await expect(page).toHaveURL(/\/profile$/)
    const emailField = getFloatingField(page, 'Email')
    const normalizedEmail = user.email.toLowerCase()
    await expect(emailField).toHaveValue(normalizedEmail, { timeout: 15_000 })
    return { user }
}

/**
 * Regression coverage for password changes in the profile view.
 */
test.describe('Profile password changes', () => {
    let cleanup: ReturnType<typeof createCleanupManager>

    test.beforeEach(({ request }) => {
        cleanup = createCleanupManager(request)
    })

    test.afterEach(async () => {
        await cleanup.cleanup()
    })

    test('changes the password after a successful PIN verification', async ({ page, request }) => {
        const { user } = await bootstrapProfile(page, request, cleanup)
        const newPasswordField = getFloatingField(page, 'New Password')
        const confirmPasswordField = getFloatingField(page, 'Confirm New Password')

        const newPassword = `Pw_${user.dni.slice(-4)}!`
        await newPasswordField.fill(newPassword)
        await confirmPasswordField.fill(newPassword)

        const saveButton = page.getByRole('button', { name: 'Save changes' })
        await expect(saveButton).toBeEnabled()
        await saveButton.click()

        const pinModal = page.locator('.pin-modal', { hasText: 'Confirm changes' })
        await expect(pinModal).toBeVisible()
        await fillPinInputs(pinModal.locator('.pin-box'), user.pin)
        const dialogPromise = page.waitForEvent('dialog')
        await pinModal.getByRole('button', { name: /^Save$/ }).click()
        const dialog = await dialogPromise
        expect(dialog.message()).toMatch(/CHANGES SAVED/i)
    })

    test('keeps the save button disabled when passwords do not match', async ({ page, request }) => {
        await bootstrapProfile(page, request, cleanup)
        const newPasswordField = getFloatingField(page, 'New Password')
        const confirmPasswordField = getFloatingField(page, 'Confirm New Password')

        await newPasswordField.fill('ValidPass123!')
        await confirmPasswordField.fill('OtherPass123!')
        await expect(page.getByText('Passwords must match.')).toBeVisible()
        await expect(page.getByRole('button', { name: 'Save changes' })).toBeDisabled()
    })

    test('shows an inline error when the password update call fails', async ({ page, request }) => {
        const { user } = await bootstrapProfile(page, request, cleanup)
        const newPasswordField = getFloatingField(page, 'New Password')
        const confirmPasswordField = getFloatingField(page, 'Confirm New Password')

        await newPasswordField.fill('AnotherPw9!')
        await confirmPasswordField.fill('AnotherPw9!')

        await useInvalidAccessToken(page)

        await page.getByRole('button', { name: 'Save changes' }).click()
        const pinModal = page.locator('.pin-modal', { hasText: 'Confirm changes' })
        await expect(pinModal).toBeVisible()
        await fillPinInputs(pinModal.locator('.pin-box'), user.pin)
        await pinModal.getByRole('button', { name: /^Save$/ }).click()

        await expect(pinModal.locator('.modal-error')).toHaveText(
            /(Request failed with status code 401|No changes have been made\.)/,
        )
        await pinModal.getByRole('button', { name: 'Cancel' }).click()
    })
})

