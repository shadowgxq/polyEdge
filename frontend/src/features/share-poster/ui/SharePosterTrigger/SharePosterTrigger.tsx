import * as Dialog from '@radix-ui/react-dialog';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Share2 } from '../../../../shared/icons';
import type { SharePosterContent } from '../../model/sharePoster.types';
import { SharePosterDialog } from '../SharePosterDialog';
import styles from './SharePosterTrigger.module.css';

export type SharePosterTriggerProps = {
  content: SharePosterContent;
  /** 分享入口无障碍名中的实体名（事件 / 榜单名），作不翻译变量插值注入。 */
  entityName: string;
  /** 分享链接；缺省用当前页 URL。 */
  shareUrl?: string;
};

/**
 * 分享入口（share-poster，PRD §4.5、AC-6/AC-7、design D7）。
 *
 * 键盘可达的只读入口，触发时打开分享弹窗并以当前展示数据出图 + 分发；无任何交易入口。
 * `aria-label` 经 i18n 插值呈现实体名（不字符串拼接）。出图 / 分发编排全部下沉弹窗，
 * 本组件只承担入口触发与弹窗开合态。
 */
export function SharePosterTrigger({ content, entityName }: SharePosterTriggerProps) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <button
          type="button"
          className={styles.trigger}
          aria-label={t('share.trigger.aria', { name: entityName })}
        >
          <Share2 className={styles.icon} aria-hidden="true" />
          {t('share.trigger.label')}
        </button>
      </Dialog.Trigger>
      <SharePosterDialog content={content} />
    </Dialog.Root>
  );
}
