import type { HTMLAttributes, ReactNode } from "react";
import styles from "./page-intro.module.css";

/** A server-rendered masthead shared by the research and reference pages. */
export function PageIntro({
  eyebrow,
  title,
  description,
  children,
  actions,
  titleProps,
  className = "",
}: {
  eyebrow: string;
  title: ReactNode;
  description?: ReactNode;
  children?: ReactNode;
  actions?: ReactNode;
  titleProps?: HTMLAttributes<HTMLHeadingElement> & {
    [key: `data-${string}`]: string | number | boolean | undefined;
  };
  className?: string;
}) {
  return (
    <div data-page-intro className={`${styles.intro} ${className}`}>
      <p className={`t-label ${styles.eyebrow}`} data-rule>{eyebrow}</p>
      <h1 {...titleProps} className={`${styles.title} ${titleProps?.className ?? ""}`}>
        {title}
      </h1>
      {description && <div className={styles.description} data-prose>{description}</div>}
      {actions && <div className={styles.actions}>{actions}</div>}
      {children && <div className={styles.context}>{children}</div>}
    </div>
  );
}
