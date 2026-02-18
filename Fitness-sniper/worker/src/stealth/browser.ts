/**
 * Stealth Browser — Playwright with anti-detection
 *
 * Uses playwright-extra + stealth plugin + fingerprint randomization
 * to avoid bot detection on Mariana Tek / MindBody sites.
 */

import { chromium } from 'playwright-extra';
import StealthPlugin from 'puppeteer-extra-plugin-stealth';
import type { Browser, BrowserContext } from 'playwright';

// Register stealth plugin — handles webdriver, plugins, chrome.runtime,
// canvas fingerprinting, WebGL, and many other detection vectors.
chromium.use(StealthPlugin());

export interface StealthBrowserOptions {
  headless?: boolean;
  proxy?: string;
}

const USER_AGENTS = [
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
];

const VIEWPORTS = [
  { width: 1440, height: 900 },
  { width: 1536, height: 864 },
  { width: 1920, height: 1080 },
  { width: 1366, height: 768 },
];

function pick<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

export async function launchStealthBrowser(
  opts: StealthBrowserOptions = {},
): Promise<{ browser: Browser; context: BrowserContext }> {
  const { headless = true, proxy } = opts;

  const launchOptions: Parameters<typeof chromium.launch>[0] = {
    headless,
    args: [
      '--disable-blink-features=AutomationControlled',
      '--disable-features=IsolateOrigins,site-per-process',
      '--no-sandbox',
    ],
  };

  if (proxy) {
    launchOptions.proxy = { server: proxy };
  }

  const browser = await chromium.launch(launchOptions);

  const viewport = pick(VIEWPORTS);
  const userAgent = pick(USER_AGENTS);

  const context = await browser.newContext({
    userAgent,
    viewport,
    locale: 'en-US',
    timezoneId: 'America/New_York',
    geolocation: { latitude: 40.7128, longitude: -74.006 }, // NYC
    permissions: ['geolocation'],
  });

  return { browser, context };
}
