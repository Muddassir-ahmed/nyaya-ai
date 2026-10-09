import { expect, test } from '@playwright/test';

test('shows the startup intro, supports skipping, and remembers completion', async ({ page }) => {
  await page.goto('/');

  await expect(
    page.getByLabel('NyayaAI introduction'),
  ).toBeVisible();
  await expect(
    page.getByRole('img', { name: 'State Emblem of India' }),
  ).toBeVisible();

  await page.getByRole('button', { name: 'Skip intro' }).click();

  await expect(
    page.getByLabel('NyayaAI introduction'),
  ).toHaveCount(0);
  await expect(
    page.getByRole('heading', { name: /Legal clarity/ }),
  ).toBeVisible();

  await page.reload();

  await expect(
    page.getByLabel('NyayaAI introduction'),
  ).toHaveCount(0);
});

test.describe('reduced motion', () => {
  test.use({ reducedMotion: 'reduce' });

  test('dismisses the startup intro quickly', async ({ page }) => {
    await page.goto('/');

    await expect(
      page.getByLabel('NyayaAI introduction'),
    ).toHaveCount(0, { timeout: 2000 });
    await expect(
      page.getByRole('heading', { name: /Legal clarity/ }),
    ).toBeVisible();
  });
});
