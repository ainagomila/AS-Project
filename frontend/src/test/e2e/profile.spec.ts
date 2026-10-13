import { test, expect } from '@playwright/test'
import { autoAcceptDialogs, fillPinInputs, getFloatingField, logInThroughUi } from './support/flows'
import { createCleanupManager } from './support/cleanup'
import { buildTestUser, registerUserViaApi } from './support/testData'

test.describe('Profile management', () => {
  let cleanup: ReturnType<typeof createCleanupManager>

  test.beforeEach(({ page, request }) => {
    autoAcceptDialogs(page)
    cleanup = createCleanupManager(request)
  })

  test.afterEach(async () => {
    await cleanup.cleanup()
  })

  test('updates contact info after confirming the security PIN', async ({ page, request }) => {

    const user = buildTestUser()
    await registerUserViaApi(request, user)
    cleanup.registerUser({ dni: user.dni, pin: user.pin, password: user.password })

    await logInThroughUi(page, { dni: user.dni, password: user.password })

    await page.getByRole('button', { name: 'Open settings' }).click()
    await expect(page).toHaveURL(/\/profile$/)

    const newEmail = `updated+${user.dni}@kofre.app`
    const newPhone = '+34666123456'
    const emailField = getFloatingField(page, 'Email')
    const phoneField = getFloatingField(page, 'Phone Number')

    await expect(emailField).toHaveValue(user.email.toLowerCase())
    await expect(phoneField).toHaveValue(user.phoneE164)

    await emailField.fill(newEmail)
    await phoneField.fill(newPhone)

    await page.getByRole('button', { name: 'Save changes' }).click()
    const saveModal = page.locator('.pin-modal', { hasText: 'Confirm changes' })
    await expect(saveModal).toBeVisible()
    await fillPinInputs(saveModal.locator('.pin-box'), user.pin)
    await saveModal.getByRole('button', { name: /^Save$/ }).click()

    await expect(emailField).toHaveValue(newEmail)
    await expect(phoneField).toHaveValue(newPhone)
  })

  test('demands the correct PIN before revealing sensitive fields', async ({ page, request }) => {

    const user = buildTestUser()
    await registerUserViaApi(request, user)
    cleanup.registerUser({ dni: user.dni, pin: user.pin, password: user.password })

    await logInThroughUi(page, { dni: user.dni, password: user.password })

    await page.getByRole('button', { name: 'Open settings' }).click()
    await expect(page).toHaveURL(/\/profile$/)

    const currentPasswordField = page.locator('.form-field', { hasText: 'Current Password' })
    // Match the eye button that triggers the PIN modal for the masked current password value
    const revealToggle = currentPasswordField.locator('button.eye-btn').first()
    await revealToggle.click()

    const pinModal = page.locator('.pin-modal', { hasText: 'Enter 6-digit PIN' })
    await expect(pinModal).toBeVisible()
    const pinDigits = pinModal.locator('.pin-box')
    await fillPinInputs(pinDigits, '000000')
    const revealButton = pinModal.getByRole('button', { name: /^Reveal$/ })
    await revealButton.click()
    const errorBanner = pinModal.locator('.modal-error')
    await expect(errorBanner).toBeVisible()
    await expect(errorBanner).not.toHaveText('')
    await expect(pinModal).toBeVisible()
  })

  test('resets pending edits when clicking cancel', async ({ page, request }) => {

    const user = buildTestUser()
    await registerUserViaApi(request, user)
    cleanup.registerUser({ dni: user.dni, pin: user.pin, password: user.password })

    await logInThroughUi(page, { dni: user.dni, password: user.password })

    await page.getByRole('button', { name: 'Open settings' }).click()
    await expect(page).toHaveURL(/\/profile$/)

    const emailField = getFloatingField(page, 'Email')
    const phoneField = getFloatingField(page, 'Phone Number')

    await expect(emailField).not.toHaveValue('')
    await expect(phoneField).not.toHaveValue('')

    const originalEmail = await emailField.inputValue()
    const originalPhone = await phoneField.inputValue()

    await emailField.fill(`edited+${user.dni}@example.com`)
    await phoneField.fill('+34999000123')

    await page.getByRole('button', { name: 'Cancel' }).click()
    await expect(emailField).toHaveValue(originalEmail)
    await expect(phoneField).toHaveValue(originalPhone)
  })

  test('enforces password/PIN confirmation rules before saving', async ({ page, request }) => {

    const user = buildTestUser()
    await registerUserViaApi(request, user)
    cleanup.registerUser({ dni: user.dni, pin: user.pin, password: user.password })

    await logInThroughUi(page, { dni: user.dni, password: user.password })

    await page.getByRole('button', { name: 'Open settings' }).click()
    await expect(page).toHaveURL(/\/profile$/)

    const saveButton = page.getByRole('button', { name: 'Save changes' })
    const newPasswordField = getFloatingField(page, 'New Password')
    const confirmPasswordField = getFloatingField(page, 'Confirm New Password')
    const newPinField = getFloatingField(page, 'New PIN (6 digits)')
    const confirmPinField = getFloatingField(page, 'Confirm New PIN')

    await newPasswordField.fill('StrongPass1!')
    await confirmPasswordField.fill('Mismatch1!')
    await expect(saveButton).toBeDisabled()

    await confirmPasswordField.fill('StrongPass1!')
    await newPinField.fill('654321')
    await confirmPinField.fill('123456')
    await expect(saveButton).toBeDisabled()

    await confirmPinField.fill('654321')
    const emailField = getFloatingField(page, 'Email')
    const guardedEmail = `guard+${user.dni}@kofre.app`
    await emailField.fill(guardedEmail)
    await expect(saveButton).toBeEnabled()

    await saveButton.click()
    const pinModal = page.locator('.pin-modal', { hasText: 'Confirm changes' })
    await expect(pinModal).toBeVisible()

    await pinModal.getByRole('button', { name: /^Save$/ }).click()
    await expect(pinModal.getByText('Enter your 6-digit PIN.')).toBeVisible()

    await pinModal.getByRole('button', { name: 'Cancel' }).click()
    await expect(pinModal).toBeHidden()

    await page.getByRole('button', { name: 'Cancel' }).click()
  })
})

