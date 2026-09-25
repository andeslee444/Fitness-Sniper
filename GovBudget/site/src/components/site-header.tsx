"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Dialog, Popover } from "radix-ui";
import { ArrowUpRight, ChevronDown, Menu, X } from "lucide-react";
import { SITE_NAME } from "@/lib/site";
import {
  SITE_NAVIGATION,
  PRIMARY_NAVIGATION,
  isNavigationCurrent,
} from "@/lib/site-navigation";
import { ReceiptsToggle } from "@/components/receipts-toggle";
import { SearchTriggerButton } from "@/components/search/command-palette";
import styles from "./site-header.module.css";

/** A 56px site shell. Mount once inside ReceiptsProvider. */
export function SiteHeader() {
  const pathname = usePathname() ?? "/";
  const [desktopOpen, setDesktopOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const searchHandoff = useRef(false);
  const closeMenus = () => {
    setDesktopOpen(false);
    setMobileOpen(false);
  };
  useEffect(() => {
    // A keyboard search can begin while navigation owns the focus. Close the
    // navigation layer before handing focus to the global search dialog.
    const close = () => {
      searchHandoff.current = true;
      setDesktopOpen(false);
      setMobileOpen(false);
    };
    document.addEventListener("fiscal-search-open", close);
    return () => document.removeEventListener("fiscal-search-open", close);
  }, []);
  const restoreMenuFocus = (event: Event) => {
    if (!searchHandoff.current) return;
    event.preventDefault();
    document
      .querySelector<HTMLElement>('[data-testid="search-input"]')
      ?.focus();
    searchHandoff.current = false;
  };

  const menuGroups = (
    <nav data-site-nav aria-label="All sections" className={styles.groups}>
      {SITE_NAVIGATION.map((group) => (
        <div key={group.label} className={styles.group}>
          <p className={`t-label ${styles.groupTitle}`}>{group.label}</p>
          {group.links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              onClick={closeMenus}
              aria-label={link.label}
              aria-current={
                isNavigationCurrent(pathname, link.href) ? "page" : undefined
              }
              className={styles.menuLink}
            >
              <span>
                {link.label}
                <ArrowUpRight size={13} aria-hidden="true" />
              </span>
              <small>{link.detail}</small>
            </Link>
          ))}
        </div>
      ))}
    </nav>
  );

  return (
    <header className={styles.header}>
      <div className={`spine ${styles.bar}`}>
        <Link
          href="/"
          className={`text-base font-semibold ${styles.brand}`}
          aria-label={`${SITE_NAME} home`}
          onClick={closeMenus}
        >
          <svg
            className={styles.mark}
            viewBox="0 0 28 30"
            aria-hidden="true"
            fill="none"
          >
            <path
              d="M4 2h20v26l-4-2-3 2-3-2-3 2-3-2-4 2V2Z"
              stroke="currentColor"
              strokeWidth="1.5"
            />
            <path
              d="M9 9h10M9 14h10M9 19h5"
              stroke="currentColor"
              strokeWidth="1.5"
            />
          </svg>
          <span>{SITE_NAME}</span>
        </Link>

        <nav
          data-site-nav
          aria-label="Main navigation"
          className={styles.primary}
        >
          {PRIMARY_NAVIGATION.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={styles.primaryLink}
              aria-current={
                isNavigationCurrent(pathname, link.href) ? "page" : undefined
              }
            >
              {link.label}
            </Link>
          ))}
          <Popover.Root
            open={desktopOpen}
            onOpenChange={(next) => {
              if (next) searchHandoff.current = false;
              setDesktopOpen(next);
            }}
          >
            {/* No {" "} after "More". The trigger is inline-flex with a
                0.25rem gap, so that space never painted. It cost a
                `<!-- --> ` text node in the HTML of every page. Measured on
                the chain-F build: the trigger's width and the chevron's x are
                the same with the space and without it. */}
            <Popover.Trigger
              className={styles.more}
              aria-label="Browse all sections"
            >
              More
              <ChevronDown size={13} aria-hidden="true" />
            </Popover.Trigger>
            <Popover.Portal>
              <Popover.Content
                className={styles.desktopPanel}
                sideOffset={12}
                align="end"
                collisionPadding={16}
                aria-label="Browse all sections"
                onCloseAutoFocus={restoreMenuFocus}
              >
                <div className={`text-base font-semibold ${styles.panelHeading}`}>
                  <span>Find your next question.</span>
                  <Popover.Close
                    aria-label="Close all sections"
                    className={styles.iconButton}
                  >
                    <X size={18} />
                  </Popover.Close>
                </div>
                {menuGroups}
              </Popover.Content>
            </Popover.Portal>
          </Popover.Root>
        </nav>

        <div className={styles.controls}>
          <SearchTriggerButton />
          <span className={styles.desktopReceipts}>
            <ReceiptsToggle />
          </span>
          <Dialog.Root
            open={mobileOpen}
            onOpenChange={(next) => {
              if (next) searchHandoff.current = false;
              setMobileOpen(next);
            }}
          >
            <Dialog.Trigger
              className={`${styles.iconButton} ${styles.mobileTrigger}`}
              aria-label="Open navigation menu"
              aria-controls={mobileOpen ? "mobile-nav-panel" : undefined}
            >
              <Menu size={20} aria-hidden="true" />
            </Dialog.Trigger>
            <Dialog.Portal>
              <Dialog.Overlay className={styles.overlay} />
              <Dialog.Content
                id="mobile-nav-panel"
                className={styles.mobilePanel}
                aria-describedby={undefined}
                onCloseAutoFocus={restoreMenuFocus}
              >
                <div className={`text-base font-semibold ${styles.panelHeading}`}>
                  <Dialog.Title>Explore Fiscal Receipts</Dialog.Title>
                  <Dialog.Close
                    className={styles.iconButton}
                    aria-label="Close navigation menu"
                  >
                    <X size={20} aria-hidden="true" />
                  </Dialog.Close>
                </div>
                {menuGroups}
                <div className={styles.mobileSettings}>
                  <ReceiptsToggle />
                  <span>Citations always remain available.</span>
                </div>
              </Dialog.Content>
            </Dialog.Portal>
          </Dialog.Root>
        </div>
      </div>
    </header>
  );
}
