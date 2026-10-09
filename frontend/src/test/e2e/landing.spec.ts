import { test, expect } from '@playwright/test'
import { autoAcceptDialogs } from './support/flows'

test.describe('Landing page', () => {
  test.beforeEach(async ({ page }) => {
    autoAcceptDialogs(page)
  })

  test('hero CTA routes to auth flows without touching backend data', async ({ page }) => {
    await page.goto('/')

    await expect(page.getByRole('heading', { name: /Control your money/i })).toBeVisible()

    await page.getByRole('button', { name: 'Log In' }).click()
    await expect(page).toHaveURL(/\/login$/)

    await page.goto('/')
    await page.getByRole('button', { name: /Start Now/i }).click()
    await expect(page).toHaveURL(/\/signup$/)
  })

  test('exposes accessible header actions and content sections', async ({ page }) => {
    await page.goto('/')

    const nav = page.locator('.left-nav')
    await expect(nav.getByRole('link', { name: 'About Us' })).toBeVisible()
    await expect(nav.getByRole('link', { name: 'Security' })).toBeVisible()
    await expect(nav.getByRole('link', { name: 'Help' })).toBeVisible()
    await expect(nav.getByRole('link', { name: 'Terms & Conditions' })).toBeVisible()

    await nav.getByRole('link', { name: 'Terms & Conditions' }).click()
    await expect(page).toHaveURL(/\/terms$/)

    await page.goto('/')

    await nav.getByRole('link', { name: 'About Us' }).click()
    await page.waitForFunction(() => {
      const target = document.getElementById('about')
      return target ? target.getBoundingClientRect().top < window.innerHeight : false
    })

    await nav.getByRole('link', { name: 'Help' }).click()
    await expect(page.getByRole('heading', { name: 'Help & Support' })).toBeVisible()
  })
})

