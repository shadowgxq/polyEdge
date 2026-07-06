import type { BiasCategory } from './BiasLabel.types';

/** 分类 → i18n 标签 key（en/zh 两套文案见 shared/i18n/resources）。 */
export const BIAS_LABEL_KEY = {
  hot: 'bias.label.hot',
  cold: 'bias.label.cold',
  fair: 'bias.label.fair',
} as const satisfies Record<BiasCategory, string>;
