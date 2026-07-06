import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { EmptyState } from '../../../../shared/ui/EmptyState';
import { ErrorState } from '../../../../shared/ui/ErrorState';
import type { EventSearchCandidate, EventSearchScope } from '../../events.types';
import styles from './EventSearchResults.module.css';

export type EventSearchResultsProps = {
  status: 'pending' | 'error' | 'success';
  candidates: EventSearchCandidate[];
  searchScope?: EventSearchScope;
  onRetry: () => void;
};

/**
 * 名称搜索候选列表（PRD §4.2、AC-2/AC-5、design D4）。
 * 候选可点击定位到明细；`local_cache` 回退标注搜索范围；空候选给明确空态。
 */
export function EventSearchResults({
  status,
  candidates,
  searchScope,
  onRetry,
}: EventSearchResultsProps) {
  const { t } = useTranslation();

  if (status === 'pending') {
    return (
      <p className={styles.loading} role="status">
        {t('events.search.loading')}
      </p>
    );
  }

  if (status === 'error') {
    return <ErrorState onRetry={onRetry} />;
  }

  const isLocalScope = searchScope === 'local_cache';

  return (
    <div className={styles.results}>
      {isLocalScope ? (
        <p className={styles.scopeNote} role="note">
          {t('events.search.localScope')}
        </p>
      ) : null}

      {candidates.length === 0 ? (
        <EmptyState title={t('events.search.empty')} description={t('events.search.emptyHint')} />
      ) : (
        <ul className={styles.list}>
          {candidates.map((candidate) => (
            <li key={candidate.slug} className={styles.item}>
              <Link to={`/events/${candidate.slug}`} className={styles.link}>
                {candidate.title}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
