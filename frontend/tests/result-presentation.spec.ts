import { expect, test } from '@playwright/test';

import {
  displayJurisdiction,
  shouldShowAuthorityFallback,
} from '../src/Result';


test.describe('result presentation helpers', () => {
  test('displays the national jurisdiction code as India', () => {
    expect(displayJurisdiction('IN')).toBe('India');
    expect(displayJurisdiction(' in ')).toBe('India');
  });

  test('preserves non-national jurisdiction values', () => {
    expect(displayJurisdiction('Assam')).toBe('Assam');
    expect(displayJurisdiction('IN-AS')).toBe('IN-AS');
  });

  test('does not duplicate a backend authority note', () => {
    expect(
      shouldShowAuthorityFallback(
        'No verified active authority record is available.',
        0,
      ),
    ).toBe(false);
  });

  test('uses the frontend fallback only when no note exists', () => {
    expect(shouldShowAuthorityFallback(null, 0)).toBe(true);
    expect(shouldShowAuthorityFallback(undefined, 1)).toBe(false);
  });
});
