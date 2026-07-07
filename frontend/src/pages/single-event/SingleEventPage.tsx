import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { SharePosterTrigger, type SharePosterContent } from '../../features/share-poster';
import { EmptyState } from '../../shared/ui/EmptyState';
import { ErrorState } from '../../shared/ui/ErrorState';
import { useEventDetailQuery } from './single-event.queries';
import type { EventDetail, OptionAnalysis } from './single-event.types';
import { EventDetailNotice } from './ui/EventDetailNotice';
import { EventEngagement } from './ui/EventEngagement';
import {
  DEFAULT_BIAS_SORT_DIRECTION,
  EventOptionList,
  sortOptionsByBias,
  type BiasSortDirection,
} from './ui/EventOptionList';
import styles from './SingleEventPage.module.css';

/**
 * 组装单事件海报内容（复用明细展示数据，不重算偏差）。
 * 偏差信号沿用既有兜底：契约 `label{zh,en}` 无 category 枚举，用中性本地化文案呈现。
 */
function buildEventPosterContent(
  detail: EventDetail,
  coreOption: OptionAnalysis,
  locale: string,
): SharePosterContent {
  const labelText = coreOption.label
    ? locale.startsWith('zh')
      ? coreOption.label.zh
      : coreOption.label.en
    : null;

  return {
    eyebrowKey: 'share.poster.eyebrow',
    headline: detail.title,
    coreOptionName: coreOption.name,
    impliedProbability: coreOption.impliedProbability,
    biasScore: coreOption.biasScore,
    signal: labelText ? { kind: 'text', text: labelText } : { kind: 'none' },
    dataSnapshotAt: detail.dataSnapshotAt,
  };
}

/**
 * 单事件明细 route entry（single-event-detail，PRD §4.0/§4.3、design D1）。
 *
 * 只承担：读路由参数 `eventId`（即 slug）、调用明细 query、按 加载/空/错误/成功 分派、
 * 组织面包屑与选项列表等区块的 composition。全页只读，无任何交易 / 下单 / 钱包入口。
 * 独立 UI 区块下沉为同模块命名组件。
 */
export function SingleEventPage() {
  const { t, i18n } = useTranslation();
  const { eventId } = useParams<{ eventId: string }>();
  const navigate = useNavigate();

  const detailQuery = useEventDetailQuery(eventId);
  const detail = detailQuery.data;
  const [sortDirection, setSortDirection] = useState<BiasSortDirection>(
    DEFAULT_BIAS_SORT_DIRECTION,
  );

  const visibleOptions = detail?.options.filter((option) => !option.excluded) ?? [];
  const isBiasApplicable = detail?.applicable ?? false;
  // 列表与分享共用同一排序结果：分享的核心选项恒为当前排序的第一行。
  const orderedOptions = sortOptionsByBias(visibleOptions, sortDirection, isBiasApplicable);

  function handleBack() {
    navigate(-1);
  }

  const currentCrumb = detail?.title ?? eventId ?? '';
  const coreOption = isBiasApplicable ? orderedOptions[0] : undefined;
  const posterContent =
    detail && coreOption ? buildEventPosterContent(detail, coreOption, i18n.language) : null;

  return (
    <section className={styles.page}>
      <nav className={styles.breadcrumb} aria-label={t('detail.breadcrumbEvents')}>
        <Link className={styles.breadcrumbLink} to="/events">
          {t('detail.breadcrumbEvents')}
        </Link>
        <span className={styles.separator} aria-hidden="true">
          /
        </span>
        <span className={styles.current}>{currentCrumb}</span>
      </nav>

      <button type="button" className={styles.back} onClick={handleBack}>
        {t('detail.back')}
      </button>

      {!eventId ? (
        <EmptyState
          title={t('detail.empty')}
          description={t('detail.emptyHint')}
          action={
            <Link className={styles.emptyAction} to="/events">
              {t('detail.backToList')}
            </Link>
          }
        />
      ) : detailQuery.isPending ? (
        <p className={styles.loading} role="status">
          {t('detail.loading')}
        </p>
      ) : detailQuery.isError ? (
        <ErrorState onRetry={() => void detailQuery.refetch()} />
      ) : !detail || visibleOptions.length === 0 ? (
        <EmptyState
          title={t('detail.empty')}
          description={t('detail.emptyHint')}
          action={
            <Link className={styles.emptyAction} to="/events">
              {t('detail.backToList')}
            </Link>
          }
        />
      ) : (
        <div className={styles.body}>
          <div className={styles.resultHeader}>
            <h1 className={styles.title}>{detail.title}</h1>
            {posterContent ? (
              <SharePosterTrigger content={posterContent} entityName={detail.title} />
            ) : null}
          </div>

          {!detail.applicable ? (
            <EventDetailNotice
              title={t('detail.notApplicable')}
              description={t('detail.notApplicableHint')}
            />
          ) : null}

          <EventEngagement commentCount={detail.commentCount} snapshotAt={detail.dataSnapshotAt} />

          <EventOptionList
            options={orderedOptions}
            applicable={detail.applicable}
            sortDirection={sortDirection}
            onSortChange={setSortDirection}
          />
        </div>
      )}
    </section>
  );
}
