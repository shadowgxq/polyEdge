import { useTranslation } from 'react-i18next';

import { BiasLabel } from '../../../../shared/ui/BiasLabel';
import { SnapshotTime } from '../../../../shared/ui/SnapshotTime';
import { buildImageProxyUrl } from '../../model/imageProxy.utils';
import type { SharePosterContent } from '../../model/sharePoster.types';
import styles from './SharePosterCard.module.css';

export type SharePosterCardProps = {
  content: SharePosterContent;
  /** 海报生成时间（出图触发时刻），与数据快照时间独立标注（design D4）。 */
  generatedAt: Date;
};

/**
 * 受控离屏海报卡片（share-poster，PRD §4.5、design D2/D4/D6）。
 *
 * 只含受控元素与内联字体，规避背景图 / CSS 滤镜 / icon-font，作为出图目标节点。
 * 内容：眉标 + 事件/榜单标题 + 核心选项与偏差信号 + 偏差评分 + 来源标注，
 * 并「区分展示」数据快照时间（`SnapshotTime`）与海报生成时间。
 * 偏差信号两种呈现：榜别 `category` 走 `BiasLabel`；单事件走已本地化中性文案（不重算分类）。
 * 市场内容（标题 / 选项名）保持英文源文本不翻译。样式仅用 `tokens.css` token。
 */
export function SharePosterCard({ content, generatedAt }: SharePosterCardProps) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language;

  const biasScoreText = new Intl.NumberFormat(locale, {
    signDisplay: 'exceptZero',
    maximumFractionDigits: 2,
  }).format(content.biasScore);

  const generatedTimeText = new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(generatedAt);

  const proxiedImageUrl = content.imageUrl ? buildImageProxyUrl(content.imageUrl) : null;

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <span className={styles.eyebrow}>{t(content.eyebrowKey)}</span>
        {proxiedImageUrl ? (
          <img className={styles.image} src={proxiedImageUrl} alt="" />
        ) : null}
        <h2 className={styles.headline}>{content.headline}</h2>
      </div>

      <div className={styles.core}>
        <span className={styles.coreLabel}>{t('share.poster.coreOption')}</span>
        <span className={styles.coreName}>{content.coreOptionName}</span>

        <div className={styles.scoreRow}>
          <span className={styles.scoreMeta}>
            <span className={styles.scoreCaption}>{t('share.poster.biasScore')}</span>
            <span className={styles.scoreValue}>{biasScoreText}</span>
          </span>
          {content.signal.kind === 'category' ? (
            <BiasLabel category={content.signal.category} />
          ) : content.signal.kind === 'text' ? (
            <span className={styles.neutralSignal}>{content.signal.text}</span>
          ) : null}
        </div>
      </div>

      <div className={styles.footer}>
        <span className={styles.source}>{t('share.poster.source')}</span>
        {content.dataSnapshotAt ? <SnapshotTime snapshotAt={content.dataSnapshotAt} /> : null}
        <span className={styles.time}>
          {t('share.poster.generatedTime', { time: generatedTimeText })}
        </span>
      </div>
    </div>
  );
}
