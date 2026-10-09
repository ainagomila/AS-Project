import { test, expect, type APIRequestContext, type Page } from '@playwright/test'
import { autoAcceptDialogs, createAccountViaUi, logInThroughUi } from '../support/flows'
import { createCleanupManager, type UserCleanupHandle } from '../support/cleanup'
import { buildTestAccount, buildTestUser, registerUserViaApi, deleteAccountViaApi } from '../support/testData'

async function openAccountDetail(
    page: Page,
    request: APIRequestContext,
    cleanupHandle: UserCleanupHandle,
) {
    const account = buildTestAccount()
    await createAccountViaUi(page, account)
    cleanupHandle.trackAccount(account.iban)

    const card = page.locator('.account-card', { hasText: account.name }).first()
    await expect(card).toBeVisible({ timeout: 15_000 })
    await card.click()
    await expect(page).toHaveURL(/\/accounts\//)
    return account
}

/**
 * Regression coverage for alias editing on the account detail page.
 */
test.describe('Account alias updates', () => {
    let cleanup: ReturnType<typeof createCleanupManager>

    test.beforeEach(({ request }) => {
        cleanup = createCleanupManager(request)
    })

    test.afterEach(async () => {
        await cleanup.cleanup()
    })

    async function bootstrap(page: Page, request: APIRequestContext) {
        autoAcceptDialogs(page)
        const user = buildTestUser()
        await registerUserViaApi(request, user)
        const handle = cleanup.registerUser({ dni: user.dni, pin: user.pin, password: user.password })
        await logInThroughUi(page, { dni: user.dni, password: user.password })
        return handle
    }

    test('persists the edited alias when the API succeeds', async ({ page, request }) => {
        const handle = await bootstrap(page, request)
        const account = await openAccountDetail(page, request, handle)

        const aliasTitle = page.locator('.title .name')
        await expect(aliasTitle).toContainText(account.name)

        await page.getByRole('button', { name: 'Edit alias' }).click()
        const newAlias = `${account.name} Â· QA`
        await page.locator('input.edit-input').fill(newAlias)
        await page.getByRole('button', { name: 'Save alias' }).click()

        await expect(aliasTitle).toContainText(newAlias)
    })

    test('does not call the backend when the alias is cleared', async ({ page, request }) => {
        const handle = await bootstrap(page, request)
        const account = await openAccountDetail(page, request, handle)

        const encoded = encodeURIComponent(account.iban)
        const patchCalls: string[] = []
        page.on('request', (req) => {
            if (req.method() === 'PATCH' && req.url().includes(`/accounts/${encoded}`)) {
                patchCalls.push(req.url())
            }
        })

        await page.getByRole('button', { name: 'Edit alias' }).click()
        await page.locator('input.edit-input').fill('   ')
        await page.getByRole('button', { name: 'Save alias' }).click()

        await expect(page.locator('.title .name')).toContainText(account.name)
        expect(patchCalls).toHaveLength(0)
    })

    test('shows the fallback toast when the alias update fails server-side', async ({ page, request }) => {
        const handle = await bootstrap(page, request)
        const account = await openAccountDetail(page, request, handle)

        await deleteAccountViaApi(request, handle.credentials, account.iban)

        await page.getByRole('button', { name: 'Edit alias' }).click()
        await page.locator('input.edit-input').fill('Should Fail Alias')
        await page.getByRole('button', { name: 'Save alias' }).click()

        await expect(page.locator('.toast')).toContainText('No se pudo actualizar el alias')
    })
})

