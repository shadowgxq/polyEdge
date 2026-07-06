import i18next from 'i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import { initReactI18next } from 'react-i18next';

import { DEFAULT_LOCALE, isSupportedLocale, LOCALE_STORAGE_KEY, LOCALES } from './locale.constants';
import en from './resources/en.json';
import zh from './resources/zh.json';

/**
 * i18n 初始化（PRD §4.6 / §5.4、AC-8）。
 *
 * - English + 中文两套 resource，`fallbackLng: 'en'`、`supportedLngs: ['en','zh']`。
 * - 语言检测/持久化经 i18next-browser-languagedetector：`order:['localStorage','navigator']`、
 *   `caches:['localStorage']`，存储 key 统一为 LOCALE_STORAGE_KEY。
 * - 含市场内容的句子一律用带占位符插值 key（形如 `{{eventName}}`/`{{optionName}}`），
 *   事件名/选项名作为变量注入，禁止与译文字符串拼接（见 detail.topBias）。
 */
export const i18n = i18next.createInstance();

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      zh: { translation: zh },
    },
    fallbackLng: DEFAULT_LOCALE,
    supportedLngs: [...LOCALES],
    load: 'languageOnly',
    nonExplicitSupportedLngs: true,
    interpolation: {
      // 事件名/选项名为纯文本变量，无需 HTML 转义。
      escapeValue: false,
    },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
      lookupLocalStorage: LOCALE_STORAGE_KEY,
    },
    react: {
      // resource 已随包内联同步就绪，无需 Suspense 等待。
      useSuspense: false,
    },
    returnNull: false,
  });

/**
 * PRD AC-8：默认锁定 English，不因浏览器语言自动切中文。
 * 仅当 localStorage 存有既存偏好时沿用检测结果，否则回落默认 English。
 */
function readStoredLocale(): string | null {
  try {
    return globalThis.localStorage?.getItem(LOCALE_STORAGE_KEY) ?? null;
  } catch {
    return null;
  }
}

const storedLocale = readStoredLocale();
if (!isSupportedLocale(storedLocale) && i18n.language !== DEFAULT_LOCALE) {
  void i18n.changeLanguage(DEFAULT_LOCALE);
}

export default i18n;
