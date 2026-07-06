import { render } from '@testing-library/react';
import type { ReactElement } from 'react';
import { I18nextProvider } from 'react-i18next';

import { i18n, type Locale } from '../i18n';

/**
 * 以真实 i18n 实例包裹待测 UI，供 shared/ui 基元与外壳组件测试复用。
 * 显式指定语言，避免测试间语言状态相互污染。
 */
export async function renderWithI18n(ui: ReactElement, locale: Locale = 'en') {
  await i18n.changeLanguage(locale);
  return render(<I18nextProvider i18n={i18n}>{ui}</I18nextProvider>);
}
