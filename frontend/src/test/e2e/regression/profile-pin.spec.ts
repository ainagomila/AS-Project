import { test, expect } from '@playwright/test'
import type { APIRequestContext, Page } from '@playwright/test'
import { autoAcceptDialogs, fillPinInputs, getFloatingField, logInThroughUi, useInvalidAccessToken } from '../support/flows'
import { createCleanupManager } from '../support/cleanup'
import { buildTestUser, registerUserViaApi } from '../support/testData'

function computeNextPin(currentPin: string): string {
    return currentPin === '654321' ? '123450' : '654321'
}

async function bootstrapProfile(
    page: Page,
    request: APIRequestContext,
    cleanup: ReturnType<typeof createCleanupManager>,
) {
    autoAcceptDialogs(page)
    const user = buildTestUser()
    await registerUserViaApi(request, user)
    const handle = cleanup.registerUser({ dni: user.dni, pin: user.pin, password: user.password })
    await logInThroughUi(page, { dni: user.dni, password: user.password })
    await page.getByRole('button', { name: 'Open settings' }).click()
    await expect(page).toHaveURL(/\/profile$/)
    const emailField = getFloatingField(page, 'Email')
    const normalizedEmail = user.email.toLowerCase()
    await expect(emailField).toHaveValue(normalizedEmail, { timeout: 15_000 })
    return { user, handle }
}

/**
 * Regression coverage for PIN changes in the profile view.
 */
test.describe('Profile PIN changes', () => {
    let cleanup: ReturnType<typeof createCleanupManager>

    test.beforeEach(({ request }) => {
        cleanup = createCleanupManager(request)
    })

    test.afterEach(async () => {
        await cleanup.cleanup()
    })

    test('updates the PIN when both entries match and the API succeeds', async ({ page, request }) => {
        const { user, handle } = await bootstrapProfile(page, request, cleanup)
        const newPinField = getFloatingField(page, 'New PIN (6 digits)')
        const confirmPinField = getFloatingField(page, 'Confirm New PIN')

        const nextPin = computeNextPin(user.pin)
        await newPinField.fill(nextPin)
        await confirmPinField.fill(nextPin)

        await page.getByRole('button', { name: 'Save changes' }).click()
        const pinModal = page.locator('.pin-modal', { hasText: 'Confirm changes' })
        await expect(pinModal).toBeVisible()
        await fillPinInputs(pinModal.locator('.pin-box'), user.pin)
        const dialogPromise = page.waitForEvent('dialog')
        await pinModal.getByRole('button', { name: /^Save$/ }).click()
        const dialog = await dialogPromise
        expect(dialog.message()).toMatch(/CHANGES SAVED/i)
        handle.credentials.pin = nextPin
    })

    test('keeps the save button disabled when the PIN confirmation does not match', async ({ page, request }) => {
        await bootstrapProfile(page, request, cleanup)
        const newPinField = getFloatingField(page, 'New PIN (6 digits)')
        const confirmPinField = getFloatingField(page, 'Confirm New PIN')

        await newPinField.fill('123456')
        await confirmPinField.fill('654321')
        await expect(page.getByText('PINs must match.')).toBeVisible()
        await expect(page.getByRole('button', { name: 'Save changes' })).toBeDisabled()
    })

    test('displays the modal error when the backend rejects the new PIN', async ({ page, request }) => {
        const { user } = await bootstrapProfile(page, request, cleanup)
        const newPinField = getFloatingField(page, 'New PIN (6 digits)')
        const confirmPinField = getFloatingField(page, 'Confirm New PIN')

        await newPinField.fill('987654')
        await confirmPinField.fill('987654')
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

