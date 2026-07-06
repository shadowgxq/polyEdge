/**
 * 语言与本地化常量（PRD §4.6 / §5.4、AC-8）。
 * 支持 English + 中文两语言，默认 English；语言偏好持久化到 localStorage。
 */
export const LOCALES = ['en', 'zh'] as const;

export type Locale = (typeof LOCALES)[number];

/** PRD AC-8：无既存偏好时默认 English。 */
export const DEFAULT_LOCALE: Locale = 'en';

/** 语言偏好在 localStorage 的存储 key（供 languagedetector 缓存与读取）。 */
export const LOCALE_STORAGE_KEY = 'polyedge.locale';

export function isSupportedLocale(value: unknown): value is Locale {
  return typeof value === 'string' && (LOCALES as readonly string[]).includes(value);
}
