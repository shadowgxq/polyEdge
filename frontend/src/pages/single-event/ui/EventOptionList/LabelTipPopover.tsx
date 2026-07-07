import * as Popover from '@radix-ui/react-popover';
import { useTranslation } from 'react-i18next';

import { Info } from '../../../../shared/icons';
import styles from './LabelTipPopover.module.css';

const LABEL_KEYS = [
  'consensusFavorite',
  'lowAttentionFavorite',
  'overheatedFavorite',
  'overheatedContender',
  'quietLongshot',
  'hypedLongshot',
  'watchLongshot',
] as const;

export function LabelTipPopover() {
  const { t } = useTranslation();

  return (
    <Popover.Root>
      <Popover.Trigger asChild>
        <button type="button" className={styles.trigger} aria-label={t('detail.labelTip.trigger')}>
          <Info className={styles.icon} aria-hidden="true" />
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          className={styles.content}
          side="bottom"
          align="start"
          sideOffset={8}
          aria-labelledby="label-tip-title"
          aria-describedby="label-tip-description"
        >
          <div className={styles.header}>
            <h3 id="label-tip-title" className={styles.title}>
              {t('detail.labelTip.title')}
            </h3>
            <p id="label-tip-description" className={styles.description}>
              {t('detail.labelTip.description')}
            </p>
          </div>

          <dl className={styles.list}>
            {LABEL_KEYS.map((key) => (
              <div key={key} className={styles.item}>
                <dt className={styles.term}>{t(`detail.labelTip.items.${key}.term`)}</dt>
                <dd className={styles.definition}>
                  {t(`detail.labelTip.items.${key}.description`)}
                </dd>
              </div>
            ))}
          </dl>
          <Popover.Arrow className={styles.arrow} />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
