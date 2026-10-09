import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    sessionStorage.setItem('nyaya-ai-startup-intro-complete', 'true');
  });
  await page.goto('/');
});

test('uses the supplied Ashoka emblem with the NyayaAI wordmark', async ({ page }) => {
  const emblem = page.getByRole('img', {
    name: 'Lion Capital of Ashoka, the national emblem of India',
  });

  await expect(emblem).toBeVisible();
  await expect(page.locator('.brand')).toContainText('NYAYAAI');
  await expect(page.locator('.brand-mark')).toHaveCount(0);
});

test('applies the supplied colour system to the interface', async ({ page }) => {
  const colours = await page.evaluate(() => {
    const root = getComputedStyle(document.documentElement);
    const value = (name: string) => root.getPropertyValue(name).trim();

    return {
      cream: value('--cream'),
      creamDeep: value('--cream-deep'),
      ink: value('--ink'),
      navy: value('--navy'),
      saffron: value('--saffron'),
      green: value('--green'),
      gold: value('--gold'),
      line: value('--line'),
      bodyBackground: getComputedStyle(document.body).backgroundColor,
      headingColour: getComputedStyle(document.querySelector('h1')!).color,
      buttonBackground: getComputedStyle(document.querySelector('.primary')!).backgroundColor,
    };
  });

  expect(colours).toEqual({
    cream: '#fcfaf5',
    creamDeep: '#f4f0e7',
    ink: '#1b2233',
    navy: '#18244a',
    saffron: '#bd6b2d',
    green: '#3c6b50',
    gold: '#ae8338',
    line: '#ded7c8',
    bodyBackground: 'rgb(252, 250, 245)',
    headingColour: 'rgb(24, 36, 74)',
    buttonBackground: 'rgb(24, 36, 74)',
  });
});

test('presents the editorial landing page without unsupported capability claims', async ({ page }) => {
  await expect(page.getByRole('heading', { name: /Legal clarity/ })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Ask NyayaAI', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: /Justice begins with/ })).toBeVisible();
  await expect(page.getByRole('heading', { name: /A focused legal corpus/ })).toBeVisible();
  await expect(page.getByText('Bharatiya Nyaya Sanhita, 2023')).toBeVisible();
  await expect(page.getByText('Constitution of India', { exact: true })).toBeVisible();
  await expect(page.getByText(/12 Indian languages/i)).toHaveCount(0);
  await expect(page.getByText(/every Indian/i)).toHaveCount(0);
});
