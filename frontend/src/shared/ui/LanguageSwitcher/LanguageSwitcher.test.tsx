import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { DEFAULT_LOCALE, i18n, LOCALE_STORAGE_KEY } from '../../i18n';
import { renderWithI18n } from '../../testing/renderWithI18n';
import { LanguageSwitcher } from './LanguageSwitcher';

describe('LanguageSwitcher', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(async () => {
    await i18n.changeLanguage(DEFAULT_LOCALE);
    localStorage.clear();
  });

  it('switches the active language and persists it to localStorage', async () => {
    const user = userEvent.setup();
    await renderWithI18n(<LanguageSwitcher />, 'en');

    const select = screen.getByRole('combobox', { name: 'Language' });
    expect(select).toHaveValue('en');

    await user.selectOptions(select, 'zh');

    expect(i18n.language).toBe('zh');
    expect(localStorage.getItem(LOCALE_STORAGE_KEY)).toBe('zh');
  });
});
