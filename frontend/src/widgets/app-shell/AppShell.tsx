import clsx from 'clsx';
import { useTranslation } from 'react-i18next';
import { NavLink, Outlet } from 'react-router-dom';

import { LanguageSwitcher } from '../../shared/ui/LanguageSwitcher';
import styles from './AppShell.module.css';

/** 两顶层 Tab（PRD §4.0）：激活态由 URL path 决定，默认落事件列表。 */
const TOP_TABS = [
  { to: '/events', labelKey: 'nav.eventList' },
  { to: '/ranking', labelKey: 'nav.ranking' },
] as const;

/**
 * 应用外壳（PRD §4.0、AC-9 基座）。
 * 顶层导航（两 Tab）+ 语言切换 + 内容 outlet；功能页正文由下游 change 填充。
 */
export function AppShell() {
  const { t } = useTranslation();

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <span className={styles.brand}>{t('app.title')}</span>
          <nav className={styles.nav} aria-label={t('nav.primaryLabel')}>
            {TOP_TABS.map((tab) => (
              <NavLink
                key={tab.to}
                to={tab.to}
                className={({ isActive }) => clsx(styles.tab, isActive && styles.tabActive)}
              >
                {t(tab.labelKey)}
              </NavLink>
            ))}
          </nav>
          <LanguageSwitcher />
        </div>
      </header>
      <main className={styles.main}>
        <div className={styles.content}>
          <Outlet />
        </div>
      </main>
    </div>
  );
}
