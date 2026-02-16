/**
 * Stealth Browser — Playwright with anti-detection
 *
 * Uses playwright-extra + stealth plugin + fingerprint randomization
 * to avoid bot detection on Mariana Tek / MindBody sites.
 */

import { chromium, Browser, BrowserContext } from 'playwright';

export interface StealthBrowserOptions {
  headless?: boolean;
  proxy?: string;
}

const USER_AGENTS = [
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
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

  // Stealth overrides — remove webdriver flag and navigator.plugins
  await context.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
    Object.defineProperty(navigator, 'plugins', {
      get: () => [1, 2, 3, 4, 5], // non-empty plugins array
    });
    Object.defineProperty(navigator, 'languages', {
      get: () => ['en-US', 'en'],
    });
    // Override chrome detection
    (window as any).chrome = { runtime: {} };
  });

  return { browser, context };
}
