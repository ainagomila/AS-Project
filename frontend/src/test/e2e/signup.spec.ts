import { test, expect } from '@playwright/test'
import { autoAcceptDialogs, completeSignupForm, submitLoginForm } from './support/flows'
import { createCleanupManager } from './support/cleanup'
import { buildTestUser, registerUserViaApi } from './support/testData'

test.describe('Sign-up flow', () => {
  let cleanup: ReturnType<typeof createCleanupManager>

  test.beforeEach(({ page, request }) => {
    autoAcceptDialogs(page)
    cleanup = createCleanupManager(request)
  })

  test.afterEach(async () => {
    await cleanup.cleanup()
  })

  test('completes registration, signs in and lands on the dashboard', async ({ page }) => {
    const user = buildTestUser()
    cleanup.registerUser({ dni: user.dni, pin: user.pin, password: user.password })

    await page.goto('/signup')
    await completeSignupForm(page, user)

    await page.getByTestId('signup-submit-btn').click()
    await expect(page).toHaveURL(/\/accounts\/login\//)
    await submitLoginForm(page, { dni: user.dni, password: user.password })
    await expect(page).toHaveURL(/\/dashboard$/)

    await expect(page.getByRole('heading', { name: 'Your Bank Accounts' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Your Cards' })).toBeVisible()
  })

  test('blocks users under 18 before submitting the form', async ({ page }) => {
    const underage = buildTestUser({
      birthdateDisplay: '01/01/2010',
      birthdateIso: '2010-01-01',
    })

    await page.goto('/signup')
    await completeSignupForm(page, underage)

    const submitCta = page.getByTestId('signup-submit-btn')
    await expect(page.getByText('You must be 18 or older.')).toBeVisible()
    await expect(submitCta).toBeDisabled()
    await expect(page).toHaveURL(/\/signup$/)

    // No user created, no cleanup needed
  })

  test('rejects malformed phone numbers before reaching the backend', async ({ page }) => {
    const user = buildTestUser()

    await page.goto('/signup')
    await completeSignupForm(page, user)
    await page.getByTestId('signup-phone-input').fill('123')

    const submitBtn = page.getByTestId('signup-submit-btn')
    await expect(submitBtn).toBeDisabled()
    await expect(
      page.getByText('Phone must be a Spanish number (+34, 9 digits).', { exact: false }),
    ).toBeVisible()

    // No user created, no cleanup needed
  })

  test('disallows registering an already existing DNI', async ({ page, request }) => {
    const existing = buildTestUser()
    await registerUserViaApi(request, existing)
    cleanup.registerUser({ dni: existing.dni, pin: existing.pin, password: existing.password })

    await page.goto('/signup')
    await completeSignupForm(page, existing)

    const submitBtn = page.getByTestId('signup-submit-btn')
    await expect(page.getByText('This DNI is already registered.', { exact: false })).toBeVisible()
    await expect(submitBtn).toBeDisabled()
    await expect(page).toHaveURL(/\/signup$/)
  })

  test('requires matching passwords and accepted terms before enabling the CTA', async ({ page }) => {
    const user = buildTestUser()

    await page.goto('/signup')
    await completeSignupForm(page, user, { acceptTerms: false, confirmPassword: `${user.password}!` })

    const submit = page.getByTestId('signup-submit-btn')
    await expect(page.getByText('Passwords do not match')).toBeVisible()
    await expect(submit).toBeDisabled()

    await page.getByTestId('signup-confirm-password-input').fill(user.password)
    await expect(submit).toBeDisabled()

    await page.getByTestId('signup-terms-checkbox').check()
    await expect(submit).toBeEnabled()

    // No user created, no cleanup needed
  })
})

