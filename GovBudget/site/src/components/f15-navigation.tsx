import type { MouseEvent, Ref, ReactNode } from 'react';
import Link from 'next/link';
import styles from './f15-navigation.module.css';

export const F15_SECTIONS = [
  ['inspect', 'Aircraft'], ['funding', 'Budget & receipts'],
  ['field-notes', 'Countries & orders'], ['history', 'Family history'],
  ['compare', 'Compare aircraft'], ['research', 'Research tray'],
] as const;
export type F15Workspace = typeof F15_SECTIONS[number][0];

export function F15FamilyHeader({ children, recordPage = false }: { children?: ReactNode; recordPage?: boolean }) {
  const Heading = recordPage ? 'h2' : 'h1';
  return <header className={styles.header} data-f15-family-header="" data-record-page={recordPage || undefined}>
    <div><Link href="/explore/" className={styles.eyebrow}>Field guide · Air · USAF</Link>
      <Heading>F-15 <span>The Eagle family.</span></Heading>
      {!recordPage && <p>Aircraft variants and the P-1 and R-1 records that fund them.</p>}
    </div>
    {children && <div className={styles.controls}>{children}</div>}
  </header>;
}

/** One navigation contract for the family workspace and its six budget pages. */
export function F15Navigation({ active, base = '', saved = 0, onNavigate, navRef }: {
  active: F15Workspace; base?: string; saved?: number; navRef?: Ref<HTMLElement>;
  onNavigate?: (event: MouseEvent<HTMLAnchorElement>, workspace: F15Workspace) => void;
}) {
  return <nav ref={navRef} className={styles.navigation} data-testid="family-nav" aria-label="F-15 family sections">
    {F15_SECTIONS.map(([id,label]) => <a key={id} href={`${base}#${id}`} aria-current={active === id ? 'page' : undefined}
      onClick={onNavigate ? event => onNavigate(event, id) : undefined}>
      {label}{id === 'research' && saved > 0 ? ` (${saved})` : ''}
    </a>)}
  </nav>;
}
