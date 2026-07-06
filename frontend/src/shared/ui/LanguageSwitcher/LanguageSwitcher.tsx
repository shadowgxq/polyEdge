import type { ChangeEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { isSupportedLocale, type Locale, LOCALES } from '../../i18n';
import styles from './LanguageSwitcher.module.css';

/**
 * 语言切换入口（PRD §4.6 / §5.4、AC-8）。
 * 切换即时生效并经 languagedetector 持久化到 localStorage（刷新保持）。
 */
export function LanguageSwitcher() {
  const { t, i18n } = useTranslation();
  const currentLocale: Locale = isSupportedLocale(i18n.language) ? i18n.language : 'en';

  function handleChange(event: ChangeEvent<HTMLSelectElement>) {
    const nextLocale = event.target.value;
    if (isSupportedLocale(nextLocale) && nextLocale !== currentLocale) {
      void i18n.changeLanguage(nextLocale);
    }
  }

  return (
    <select
      className={styles.select}
      value={currentLocale}
      onChange={handleChange}
      aria-label={t('language.label')}
    >
      {LOCALES.map((locale) => (
        <option key={locale} value={locale}>
          {t(`language.${locale}`)}
        </option>
      ))}
    </select>
  );
}
