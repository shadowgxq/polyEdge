import clsx from 'clsx';
import { useTranslation } from 'react-i18next';

import { BIAS_LABEL_KEY } from './BiasLabel.constants';
import type { BiasCategory } from './BiasLabel.types';
import styles from './BiasLabel.module.css';

const TONE_CLASS_BY_CATEGORY = {
  hot: styles.hot,
  cold: styles.cold,
  fair: styles.fair,
} as const satisfies Record<BiasCategory, string>;

export type BiasLabelProps = {
  category: BiasCategory;
  className?: string;
};

/**
 * 偏差三分类标签（PRD §4.3、bias-algorithm §4）。
 * 纯展示：分类由外部注入，不含偏差计算；文案随语言切换。
 */
export function BiasLabel({ category, className }: BiasLabelProps) {
  const { t } = useTranslation();

  return (
    <span className={clsx(styles.label, TONE_CLASS_BY_CATEGORY[category], className)}>
      {t(BIAS_LABEL_KEY[category])}
    </span>
  );
}
