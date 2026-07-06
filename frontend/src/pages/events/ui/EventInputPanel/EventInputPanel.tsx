import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { EmptyState } from '../../../../shared/ui/EmptyState';
import { useEventSearchQuery, useResolveEventMutation } from '../../events.queries';
import type { EventResolveResult } from '../../events.types';
import { EventSearchResults } from '../EventSearchResults';
import styles from './EventInputPanel.module.css';

/** 判定输入是否走「链接」路径（含 polymarket.com 或 URL 形态），否则走名称搜索。 */
const LINK_LIKE_PATTERN = /(polymarket\.com|^https?:\/\/)/i;
/** Polymarket 事件链接形态校验（前端只做形态校验，slug 提取交后端）。 */
const POLYMARKET_EVENT_PATTERN =
  /^(https?:\/\/)?(www\.)?polymarket\.com\/(event|market)\/[\w-]+/i;

export type EventInputPanelProps = {
  /** 链接解析成功后的导航回调（由页面提供，承接导航副作用编排）。 */
  onResolved: (result: EventResolveResult) => void;
};

/**
 * 手动事件输入（PRD §4.2、AC-2、design D4）。
 *
 * 单输入框：含 polymarket.com / URL 形态走链接解析（前端仅形态校验，形态非法就地提示不发请求），
 * 否则走名称搜索。链接解析走 `resolve` mutation，名称搜索走受控 `search` query。
 */
export function EventInputPanel({ onResolved }: EventInputPanelProps) {
  const { t } = useTranslation();
  const [inputValue, setInputValue] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [lastLink, setLastLink] = useState('');

  const searchQuery = useEventSearchQuery(searchTerm, searchTerm.length > 0);
  const resolveMutation = useResolveEventMutation({ onSuccess: onResolved });

  const resolveLink = (link: string) => {
    setSearchTerm('');
    setLastLink(link);
    resolveMutation.mutate(link);
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (resolveMutation.isPending) {
      return;
    }

    const value = inputValue.trim();
    if (!value) {
      return;
    }

    setFormError(null);

    if (LINK_LIKE_PATTERN.test(value)) {
      if (!POLYMARKET_EVENT_PATTERN.test(value)) {
        setFormError('events.input.invalidLink');
        return;
      }
      resolveLink(value);
      return;
    }

    resolveMutation.reset();
    setSearchTerm(value);
  };

  return (
    <section className={styles.panel} aria-label={t('events.input.label')}>
      <form className={styles.form} onSubmit={handleSubmit}>
        <label className={styles.field}>
          <span className={styles.fieldLabel}>{t('events.input.label')}</span>
          <input
            className={styles.input}
            type="text"
            value={inputValue}
            onChange={(event) => setInputValue(event.target.value)}
            placeholder={t('events.input.placeholder')}
            aria-invalid={formError !== null}
          />
        </label>
        <button
          type="submit"
          className={styles.submit}
          disabled={resolveMutation.isPending || inputValue.trim().length === 0}
        >
          {resolveMutation.isPending ? t('events.input.resolving') : t('events.input.submit')}
        </button>
      </form>

      {formError ? (
        <p className={styles.error} role="alert">
          {t(formError)}
        </p>
      ) : null}

      {resolveMutation.isError ? (
        <EmptyState
          title={t('events.input.notFound')}
          description={t('events.input.notFoundHint')}
          action={
            <button
              type="button"
              className={styles.retry}
              onClick={() => resolveLink(lastLink)}
              disabled={resolveMutation.isPending}
            >
              {t('events.input.retry')}
            </button>
          }
        />
      ) : null}

      {searchTerm ? (
        <EventSearchResults
          status={searchQuery.status}
          candidates={searchQuery.data?.candidates ?? []}
          searchScope={searchQuery.data?.searchScope}
          onRetry={() => void searchQuery.refetch()}
        />
      ) : null}
    </section>
  );
}
