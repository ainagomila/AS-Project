import { test, expect, type APIRequestContext, type Page } from '@playwright/test'
import {
    autoAcceptDialogs,
    createAccountViaUi,
    createCardViaUi,
    fillPinInputs,
    logInThroughUi,
} from './support/flows'
import { createCleanupManager } from './support/cleanup'
import { buildTestAccount, buildTestCard, buildTestUser, registerUserViaApi } from './support/testData'

async function bootstrapCardDetail(
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

    const card = buildTestCard({ accountIban: account.iban, bank: account.bank })
    await createCardViaUi(page, card)
    cleanupHandle.trackCard({ iban: account.iban, pan: card.pan })

    const lastFour = card.pan.slice(-4)
    const cardTile = page.locator('.card-item', { hasText: lastFour }).first()
    await expect(cardTile).toBeVisible({ timeout: 15_000 })
    await cardTile.click()

    await expect(page).toHaveURL(new RegExp(`/card/${card.pan}$`))
    await expect(page.locator('.title .bank')).toContainText(card.bank)

    return { user, account, card }
}

test.describe('Card detail experience', () => {
    let cleanup: ReturnType<typeof createCleanupManager>

    test.beforeEach(({ request }) => {
        cleanup = createCleanupManager(request)
    })

    test.afterEach(async () => {
        await cleanup.cleanup()
    })

    test('locks sensitive data until the correct PIN is provided', async ({ page, request }) => {
        autoAcceptDialogs(page)
        const { user } = await bootstrapCardDetail(page, request, cleanup)

        const lockedCard = page.locator('.virtual-card.locked').first()
        await expect(lockedCard).toBeVisible()
        await lockedCard.click()

        const pinModal = page.getByTestId('unlock-card-pin-modal')
        await expect(pinModal).toBeVisible()

        const pinInputs = pinModal.locator('.pin-input .pin-box')
        await fillPinInputs(pinInputs, '000000')
        await pinModal.getByRole('button', { name: 'Unlock' }).click()
        await expect(pinModal.getByText('Incorrect PIN. Unable to unlock the card.')).toBeVisible()

        for (let i = 0; i < 6; i += 1) {
            await pinInputs.nth(i).fill('')
        }

        await fillPinInputs(pinInputs, user.pin)
        await pinModal.getByRole('button', { name: 'Unlock' }).click()

        await expect(pinModal).toBeHidden()
        await expect(page.locator('.virtual-card.locked')).toHaveCount(0)

        const sensitiveInfo = page.locator('.sensitive-info .value').first()
        await expect(sensitiveInfo).toBeVisible()
        await expect(sensitiveInfo).not.toHaveText('***')
        await expect(sensitiveInfo).toHaveText(/.{3,}/)
    })

    test('allows editing the card alias and validates delete PIN guardrails', async ({ page, request }) => {
        autoAcceptDialogs(page)
        const { user, card } = await bootstrapCardDetail(page, request, cleanup)

        const aliasDisplay = page.locator('.title .name:not(.edit)').first()
        const aliasEditor = page.locator('.title .name.edit')
        await expect(aliasDisplay).toContainText(card.alias)

        await page.locator('button.edit-inline').first().click()
        const newAlias = `QA Alias ${Date.now().toString(36)}`
        await page.locator('input.edit-input').fill(newAlias)
        const encodedDni = encodeURIComponent(user.dni)
        const encodedPan = encodeURIComponent(card.pan)
        const aliasUpdate = page.waitForResponse(
            (response) =>
                response.url().includes(`/users/${encodedDni}/accounts/`) &&
                response.url().includes(`/cards/${encodedPan}`) &&
                response.request().method() === 'PATCH',
        )
        await page.locator('button.edit-accept').click()
        await aliasUpdate
        await expect(aliasEditor).toBeHidden()
        await expect(aliasDisplay).toContainText(newAlias)

        await page.locator('.header-actions .pill.delete').click()
        const confirmDeleteModal = page.locator('.modal-card', { hasText: 'Delete card' }).first()
        await expect(confirmDeleteModal).toBeVisible()
        await confirmDeleteModal.getByRole('button', { name: /Delete permanently/i }).click()

        const deleteModal = page.getByTestId('delete-card-pin-modal')
        await expect(deleteModal).toBeVisible()

        await deleteModal.getByRole('button', { name: /Delete permanently/i }).click()
        await expect(deleteModal.getByText('Please enter your 6-digit PIN.')).toBeVisible()

        await deleteModal.getByRole('button', { name: 'Cancel' }).click()
        await expect(deleteModal).toBeHidden()
    })
})

