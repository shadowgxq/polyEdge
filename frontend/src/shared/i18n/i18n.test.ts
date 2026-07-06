import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { DEFAULT_LOCALE, i18n, LOCALE_STORAGE_KEY } from './index';

describe('i18n', () => {
  beforeEach(async () => {
    localStorage.clear();
    await i18n.changeLanguage(DEFAULT_LOCALE);
  });

  afterEach(async () => {
    await i18n.changeLanguage(DEFAULT_LOCALE);
    localStorage.clear();
  });

  it('defaults to English when there is no stored preference', () => {
    expect(i18n.language).toBe('en');
    expect(i18n.t('nav.eventList')).toBe('Events');
  });

  it('translates bias labels per language and interpolates market content', async () => {
    expect(i18n.t('bias.label.hot')).toBe('Crowded Attention Signal');

    await i18n.changeLanguage('zh');
    expect(i18n.t('bias.label.cold')).toBe('低关注·观察信号');
    expect(i18n.t('detail.topBias', { eventName: 'World Cup 2026', optionName: 'Brazil' })).toBe(
      'World Cup 2026 中 Brazil 偏差最高',
    );
  });

  it('persists the selected language to localStorage', async () => {
    await i18n.changeLanguage('zh');
    expect(localStorage.getItem(LOCALE_STORAGE_KEY)).toBe('zh');
  });
});
