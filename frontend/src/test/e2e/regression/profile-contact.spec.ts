import { test, expect } from '@playwright/test'
import type { APIRequestContext, Page } from '@playwright/test'
import { autoAcceptDialogs, fillPinInputs, getFloatingField, logInThroughUi } from '../support/flows'
import { createCleanupManager } from '../support/cleanup'
import { buildTestUser, registerUserViaApi } from '../support/testData'

async function openProfile(
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
 * Regression coverage for profile contact edits.
 */
test.describe('Profile contact updates', () => {
    let cleanup: ReturnType<typeof createCleanupManager>

    test.beforeEach(({ request }) => {
        cleanup = createCleanupManager(request)
    })

    test.afterEach(async () => {
        await cleanup.cleanup()
    })

    test('saves the email and phone after verifying the PIN', async ({ page, request }) => {
        const { user } = await openProfile(page, request, cleanup)
        const emailField = getFloatingField(page, 'Email')
        const phoneField = getFloatingField(page, 'Phone Number')

        const updatedEmail = `qa.${user.dni}@kofre.app`
        const updatedPhone = buildTestUser().phoneE164
        await emailField.fill(updatedEmail)
        await phoneField.fill(updatedPhone)

        const saveButton = page.getByRole('button', { name: 'Save changes' })
        await expect(saveButton).toBeEnabled({ timeout: 10_000 })
        await saveButton.click()
        const pinModal = page.locator('.pin-modal', { hasText: 'Confirm changes' })
        await expect(pinModal).toBeVisible()
        await fillPinInputs(pinModal.locator('.pin-box'), user.pin)
        const updateResponse = page.waitForResponse((res) =>
            res.url().includes(`/users/${encodeURIComponent(user.dni)}`) && res.request().method() === 'PATCH',
        )
        await pinModal.getByRole('button', { name: /^Save$/ }).click()
        await updateResponse
        await expect(pinModal).toBeHidden()

        await expect(emailField).toHaveValue(updatedEmail.toLowerCase(), { timeout: 15_000 })
        await expect(phoneField).toHaveValue(updatedPhone, { timeout: 15_000 })
    })

    test('requires a 6-digit PIN before contacting the backend', async ({ page, request }) => {
        const { user } = await openProfile(page, request, cleanup)
        const emailField = getFloatingField(page, 'Email')
        const phoneField = getFloatingField(page, 'Phone Number')
        await emailField.fill(`guardrails+${user.dni}@kofre.app`)
        await phoneField.fill(buildTestUser().phoneE164)

        const verifyCalls: string[] = []
        page.on('request', (req) => {
            if (req.method() === 'POST' && req.url().includes('/security/verify-pin')) {
                verifyCalls.push(req.url())
            }
        })

        const saveButton = page.getByRole('button', { name: 'Save changes' })
        await expect(saveButton).toBeEnabled({ timeout: 10_000 })
        await saveButton.click()
        const pinModal = page.locator('.pin-modal', { hasText: 'Confirm changes' })
        await expect(pinModal).toBeVisible()
        const pinBoxes = pinModal.locator('.pin-box')
        await pinBoxes.nth(0).fill('1')
        await pinBoxes.nth(1).fill('2')
        await pinBoxes.nth(2).fill('3')
        await pinModal.getByRole('button', { name: /^Save$/ }).click()

        await expect(pinModal.locator('.modal-error')).toHaveText('Enter your 6-digit PIN.')
        expect(verifyCalls).toHaveLength(0)
    })

    test('shows the modal error when the backend update fails', async ({ page, request }) => {
        const { user } = await openProfile(page, request, cleanup)
        const emailField = getFloatingField(page, 'Email')
        await emailField.fill(`error+${user.dni}@kofre.app`)

        await page.evaluate(() => window.localStorage.setItem('authToken', 'invalid-token'))

        await page.getByRole('button', { name: 'Save changes' }).click()
        const pinModal = page.locator('.pin-modal', { hasText: 'Confirm changes' })
        await expect(pinModal).toBeVisible()
        await fillPinInputs(pinModal.locator('.pin-box'), user.pin)
        await pinModal.getByRole('button', { name: /^Save$/ }).click()

        await expect(pinModal.locator('.modal-error')).toHaveText(
            /(Request failed with status code 401|Error al guardar los cambios\.|No changes have been made\.)/,
        )
        await pinModal.getByRole('button', { name: 'Cancel' }).click()
        await expect(pinModal).toBeHidden()
    })
})

