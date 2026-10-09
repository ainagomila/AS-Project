import { test, expect, type APIRequestContext, type Page } from '@playwright/test'
import { autoAcceptDialogs, createAccountViaUi, logInThroughUi } from './support/flows'
import { createCleanupManager } from './support/cleanup'
import { buildTestAccount, buildTestUser, registerUserViaApi } from './support/testData'

async function openAccountDetail(
    page: Page,
    request: APIRequestContext,
    cleanup: ReturnType<typeof createCleanupManager>,
) {
    const user = buildTestUser()
    await registerUserViaApi(request, user)
    const cleanupHandle = cleanup.registerUser({ dni: user.dni, pin: user.pin, password: user.password })

    await logInThroughUi(page, { dni: user.dni, password: user.password })

    const account = buildTestAccount()
    await createAccountViaUi(page, account)
    cleanupHandle.trackAccount(account.iban)

    const card = page.locator('.account-card', { hasText: account.name }).first()
    await expect(card).toBeVisible({ timeout: 15_000 })
    await card.click()
    await expect(page).toHaveURL(/\/accounts\//)

    return { user, account, cleanupHandle }
}

test.describe('Account detail view', () => {
    let cleanup: ReturnType<typeof createCleanupManager>

    test.beforeEach(({ request }) => {
        cleanup = createCleanupManager(request)
    })

    test.afterEach(async () => {
        await cleanup.cleanup()
    })

    test('updates the alias of an account and reflects the change immediately', async ({ page, request }) => {
        autoAcceptDialogs(page)

        const { user, account } = await openAccountDetail(page, request, cleanup)

        const aliasTitle = page.locator('.title .name')
        await expect(aliasTitle).toContainText(account.name)

        await page.getByRole('button', { name: 'Edit alias' }).click()

        const newAlias = `Weekend ${user.dni.slice(-3)}`
        await page.locator('input.edit-input').fill(newAlias)
        await page.getByRole('button', { name: 'Save alias' }).click()

        await expect(aliasTitle).toContainText(newAlias)
    })

    test('keeps the alias unchanged when submitting an empty value', async ({ page, request }) => {
        autoAcceptDialogs(page)

        const { account, cleanupHandle } = await openAccountDetail(page, request, cleanup)

        await page.getByRole('button', { name: 'Edit alias' }).click()
        const aliasInput = page.locator('input.edit-input')
        await aliasInput.fill('   ')
        await page.getByRole('button', { name: 'Save alias' }).click()

        const aliasTitle = page.locator('.title .name')
        await expect(aliasTitle).toHaveText(account.name)

        // ensure cleanup handles still registered entities
        cleanupHandle.trackAccount(account.iban)
    })
})

