import { test, expect, type Page } from '@playwright/test';
import { queryResponseSchema } from '../src/contract';
import { safeWebUrl } from '../src/Result';

// Synthetic UI fixtures only. They do not represent legal advice, an actual
// authority, an emergency contact, or approved legal source data.
function response(route: string, extra: Record<string, unknown> = {}) {
  return {
    route,
    analysis: { original_query: 'Test question', intent: 'legal_information', domain: 'unknown', jurisdiction: null },
    ...extra,
  };
}
const validation = { citation_valid: true, claim_grounding_valid: true, answer_integrity_valid: true };
const evidence = { chunk_id: 1, citation_id: 'E1', content: 'Synthetic evidence for the browser test.', document_title: 'Test document', source_url: 'https://example.com/source', is_verified: true };
const legal = response('legal', { legal_answer: { summary: 'Synthetic answer for the browser test.', legal_basis: ['Synthetic basis.'], citations: ['E1'] }, evidence: [evidence], validation });

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.sessionStorage.setItem('nyaya-ai-startup-intro-complete', 'true');
  });
});

async function mockResponse(page: Page, data: unknown, status = 200) {
  await page.route('**/query', async (route) => {
    await route.fulfill({ status, json: data, headers: { 'Access-Control-Allow-Origin': '*' } });
  });
}
async function submit(page: Page, question = 'Test question') {
  await page.goto('/');
  await page.getByLabel('Your question', { exact: true }).fill(question);
  await page.getByRole('button', { name: 'Get guidance' }).click();
}

test('validates the contract and rejects malformed responses', () => {
  expect(queryResponseSchema.safeParse(legal).success).toBe(true);
  expect(queryResponseSchema.safeParse(response('invented_route')).success).toBe(false);
  expect(queryResponseSchema.safeParse(response('legal', { answer_blocked: 'false' })).success).toBe(false);
  expect(queryResponseSchema.safeParse(response('legal', { validation: { citation_completeness: 2 } })).success).toBe(false);
  expect(queryResponseSchema.safeParse({ route: 'legal' }).success).toBe(false);
});

test('permits only absolute HTTP(S) source URLs without credentials', () => {
  for (const url of ['javascript:alert(1)', 'data:text/html,test', 'file:///test', '//example.com', 'https://user:password@example.com', 'bad']) {
    expect(safeWebUrl(url)).toBeNull();
  }
  expect(safeWebUrl('https://example.com/source')).toBe('https://example.com/source');
});

test('submits the exact API shape and displays a source-grounded response', async ({ page }) => {
  let body: unknown;
  await page.route('**/query', async (route) => {
    body = route.request().postDataJSON();
    await route.fulfill({ json: legal });
  });
  await page.goto('/');
  await page.getByLabel('Your question', { exact: true }).fill('  Test question  ');
  await page.getByLabel('State or jurisdiction').fill('  Assam  ');
  await page.getByRole('button', { name: 'Get guidance' }).click();
  await expect(page.getByText('Synthetic answer for the browser test.')).toBeVisible();
  expect(body).toEqual({ query: 'Test question', jurisdiction: 'Assam' });
  await page.getByText('View backend validation results').click();
  await expect(page.getByText('Passed', { exact: true })).toHaveCount(3);
  await page.getByText('Test document', { exact: false }).click();
  await expect(page.getByText('Synthetic evidence for the browser test.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Open source' })).toHaveAttribute('href', 'https://example.com/source');
});

test('never renders a blocked draft, even if all validation booleans say true', async ({ page }) => {
  await mockResponse(page, { ...legal, answer_blocked: true });
  await submit(page);
  await expect(page.getByRole('heading', { name: 'We couldn’t verify this answer' })).toBeVisible();
  await expect(page.getByText('Synthetic answer for the browser test.')).toHaveCount(0);
  await expect(page.getByText('Synthetic basis.')).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'Supporting sources' })).toHaveCount(0);
});

for (const checks of [{ ...validation, claim_grounding_valid: false }, null]) {
  test(`fails closed for generated evidence with ${checks ? 'failed' : 'missing'} validation`, async ({ page }) => {
    await mockResponse(page, { ...legal, validation: checks });
    await submit(page);
    await expect(page.getByRole('heading', { name: 'We couldn’t verify this answer' })).toBeVisible();
    await expect(page.getByText('Synthetic answer for the browser test.')).toHaveCount(0);
  });
}

test('shows the backend no-evidence message without claiming validation passed', async ({ page }) => {
  await mockResponse(page, response('legal', { legal_answer: { summary: 'No evidence available for this test.' } }));
  await submit(page);
  await expect(page.getByText('No evidence available for this test.')).toBeVisible();
  await expect(page.getByText('Answer-validation results were not returned.')).toBeVisible();
  await expect(page.getByText('Passed', { exact: true })).toHaveCount(0);
});

test('follow-up keeps the original question and submits the supplied jurisdiction', async ({ page }) => {
  const requests: unknown[] = [];
  await page.route('**/query', async (route) => {
    requests.push(route.request().postDataJSON());
    await route.fulfill({ json: requests.length === 1
      ? response('follow_up', { follow_up_question: 'Which state?', analysis: { original_query: 'Where can I report this?', intent: 'authority_lookup', domain: 'criminal', requires_follow_up: true, missing_information: ['jurisdiction'] } })
      : response('authority', { authority_response: { service_key: 'test', jurisdiction: 'Assam', authorities: [] } }) });
  });
  await submit(page, 'Where can I report this?');
  await expect(page.getByText('Which state?')).toBeVisible();
  await page.getByRole('button', { name: 'Add details', exact: true }).click();
  await expect(page.getByLabel('State or jurisdiction')).toBeFocused();
  await page.getByLabel('State or jurisdiction').fill('Assam');
  await page.getByRole('button', { name: 'Submit with details' }).click();
  await expect(page.getByRole('heading', { name: 'Where to turn' })).toBeVisible();
  expect(requests).toEqual([{ query: 'Where can I report this?', jurisdiction: null }, { query: 'Where can I report this?', jurisdiction: 'Assam' }]);
});

test('authority directory displays only active verified records and safe links', async ({ page }) => {
  const authority = { id: 1, name: 'Synthetic authority', authority_type: 'other', domain: 'test', service_key: 'test', service_name: 'Test service', jurisdiction_id: 1, jurisdiction_name: 'Test jurisdiction', jurisdiction_code: 'TEST', primary_source_name: 'Test source', primary_source_url: 'https://example.com/source', official_portal_url: 'javascript:alert(1)', is_verified: true, is_active: true };
  await mockResponse(page, response('authority', { authority_response: { service_key: 'test', authorities: [authority, { ...authority, id: 2, name: 'Hidden unverified', is_verified: false }, { ...authority, id: 3, name: 'Hidden inactive', is_active: false }] } }));
  await submit(page);
  await expect(page.getByRole('heading', { name: 'Synthetic authority' })).toBeVisible();
  await expect(page.getByText('Hidden unverified')).toHaveCount(0);
  await expect(page.getByText('Hidden inactive')).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Official portal' })).toHaveCount(0);
});

test('emergency directory uses returned verified contacts and actions', async ({ page }) => {
  const contact = { name: 'Synthetic emergency contact', emergency_type: 'other', phone_number: 'TEST CONTACT ONLY', jurisdiction: 'Test jurisdiction', primary_source_name: 'Test source', primary_source_url: 'https://example.com', is_verified: true, is_active: true };
  await mockResponse(page, response('emergency', { emergency_response: { is_emergency: true, immediate_actions: ['Synthetic action for UI testing.'], contacts: [contact, { ...contact, name: 'Hidden emergency contact', is_verified: false }] } }));
  await submit(page);
  await expect(page.getByText('Synthetic action for UI testing.')).toBeVisible();
  await expect(page.getByText('TEST CONTACT ONLY')).toBeVisible();
  await expect(page.getByText('Hidden emergency contact')).toHaveCount(0);
});

for (const [route, heading] of [['civic', 'Service not yet available'], ['out_of_scope', 'Outside the current scope'], ['non_rag', 'More information needed'], ['legal', 'Your guidance'], ['emergency', 'Immediate assistance'], ['authority', 'Where to turn']]) {
  test(`${route} route handles empty payloads without invented guidance`, async ({ page }) => {
    await mockResponse(page, response(route));
    await submit(page);
    await expect(page.getByRole('heading', { name: heading, exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Supporting sources' })).toHaveCount(0);
  });
}

test('network failure preserves inputs and supports an explicit retry', async ({ page }) => {
  let calls = 0;
  await page.route('**/query', async (route) => {
    calls++;
    if (calls === 1) await route.abort('failed');
    else await route.fulfill({ json: response('non_rag') });
  });
  await submit(page);
  await expect(page.getByRole('alert')).toContainText('Could not reach NyayaAI');
  await expect(page.getByLabel('Your question', { exact: true })).toHaveValue('Test question');
  expect(calls).toBe(1);
  await page.getByRole('button', { name: 'Try again', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'More information needed' })).toBeVisible();
  expect(calls).toBe(2);
});

for (const [status, text] of [[422, 'could not accept the question'], [429, 'Too many requests'], [500, 'HTTP 500']] as const) {
  test(`handles HTTP ${status} without displaying server internals`, async ({ page }) => {
    await mockResponse(page, { detail: 'INTERNAL DATA MUST NOT BE SHOWN' }, status);
    await submit(page);
    await expect(page.getByRole('alert')).toContainText(text);
    await expect(page.getByText('INTERNAL DATA MUST NOT BE SHOWN')).toHaveCount(0);
  });
}

test('rejects malformed successful JSON', async ({ page }) => {
  await mockResponse(page, { route: 'legal', legal_answer: { summary: 'UNVALIDATED DRAFT' } });
  await submit(page);
  await expect(page.getByRole('alert')).toContainText('did not match the expected format');
  await expect(page.getByText('UNVALIDATED DRAFT')).toHaveCount(0);
});

test('stopping a request ignores a late response and allows a fresh request', async ({ page }) => {
  let release: (() => void) | undefined;
  let calls = 0;
  await page.route('**/query', async (route) => {
    calls++;
    if (calls === 1) {
      await new Promise<void>((resolve) => { release = resolve; });
      await route.fulfill({ json: legal }).catch(() => {});
    } else await route.fulfill({ json: response('non_rag') });
  });
  await submit(page);
  await expect.poll(() => calls).toBe(1);
  await page.getByRole('button', { name: 'Stop waiting' }).click();
  release?.();
  await expect(page.getByRole('status')).toContainText('Stopped waiting');
  await page.getByRole('button', { name: 'Get guidance' }).click();
  await expect(page.getByRole('heading', { name: 'More information needed' })).toBeVisible();
  await expect(page.getByText('Synthetic answer for the browser test.')).toHaveCount(0);
});

test('timeout preserves the question without an automatic retry', async ({ page }) => {
  let release: (() => void) | undefined;
  let calls = 0;
  await page.clock.install();
  await page.route('**/query', async (route) => {
    calls++;
    await new Promise<void>((resolve) => { release = resolve; });
    await route.fulfill({ json: legal }).catch(() => {});
  });
  await submit(page);
  await expect.poll(() => calls).toBe(1);
  await page.clock.fastForward(12 * 60 * 1000 + 1000);
  await expect(page.getByRole('alert')).toContainText('took too long');
  release?.();
  expect(calls).toBe(1);
  await expect(page.getByLabel('Your question', { exact: true })).toHaveValue('Test question');
});

test('user and API content render as text, never executable HTML', async ({ page }) => {
  const content = '<img src=x onerror="window.__injected=true">';
  await mockResponse(page, response('legal', { legal_answer: { summary: content } }));
  await submit(page, content);
  await expect(page.locator('.answer-summary')).toHaveText(content);
  await expect(page.locator('.result-card img')).toHaveCount(0);
});

test('mobile layout fits the viewport and retains form controls', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockResponse(page, legal);
  await submit(page);
  await expect(page.getByText('Synthetic answer for the browser test.')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await expect(page.getByLabel('State or jurisdiction')).toBeVisible();
});
