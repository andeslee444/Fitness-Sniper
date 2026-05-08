/**
 * Arketa API Discovery Script
 *
 * Uses Playwright to intercept network requests during the Saint NYC
 * booking flow. Run this to discover/verify API endpoints.
 *
 * Usage: npx tsx worker/src/discover-arketa.ts
 *
 * What it does:
 * 1. Opens https://app.arketa.co/saint with network interception
 * 2. Logs all API requests/responses during browsing
 * 3. User can manually click through booking flow
 * 4. Script captures auth headers, booking endpoints, request/response shapes
 */

import { chromium } from 'playwright';

const ARKETA_URL = 'https://app.arketa.co/saint';

async function main() {
  console.log('Launching browser...');
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    locale: 'en-US',
    timezoneId: 'America/New_York',
  });

  const page = await context.newPage();

  // Intercept all API requests
  const apiRequests: Array<{
    url: string;
    method: string;
    headers: Record<string, string>;
    postData: string | null;
    status?: number;
    response?: string;
  }> = [];

  page.on('request', (request) => {
    const url = request.url();
    if (url.includes('/api/') || url.includes('identitytoolkit') || url.includes('securetoken')) {
      const entry = {
        url,
        method: request.method(),
        headers: request.headers(),
        postData: request.postData(),
      };
      apiRequests.push(entry);
      console.log(`\n>>> ${entry.method} ${url}`);
      if (entry.postData) {
        try {
          const parsed = JSON.parse(entry.postData);
          console.log('    Body:', JSON.stringify(parsed, null, 2).substring(0, 500));
        } catch {
          console.log('    Body:', entry.postData.substring(0, 200));
        }
      }
      // Log auth headers
      const authHeader = request.headers()['authorization'];
      if (authHeader) {
        console.log('    Auth:', authHeader.substring(0, 80) + '...');
      }
    }
  });

  page.on('response', async (response) => {
    const url = response.url();
    if (url.includes('/api/') || url.includes('identitytoolkit') || url.includes('securetoken')) {
      const status = response.status();
      console.log(`\n<<< ${status} ${url}`);
      try {
        const body = await response.text();
        if (body.length < 2000) {
          console.log('    Response:', body);
        } else {
          console.log('    Response (truncated):', body.substring(0, 500) + '...');
        }
      } catch {
        console.log('    (could not read response body)');
      }
    }
  });

  console.log(`\nNavigating to ${ARKETA_URL}...`);
  console.log('Instructions:');
  console.log('  1. Log in with your Saint NYC account');
  console.log('  2. Browse the schedule and click on a session');
  console.log('  3. Go through the checkout flow (you can cancel before confirming)');
  console.log('  4. All API calls will be logged to the console');
  console.log('  5. Close the browser when done\n');

  await page.goto(ARKETA_URL);

  // Wait for user to close the browser
  await page.waitForEvent('close', { timeout: 600000 }).catch(() => {});

  console.log('\n\n========== API Request Summary ==========');
  for (const req of apiRequests) {
    console.log(`${req.method} ${req.url}`);
    if (req.postData) {
      try {
        console.log('  Body:', JSON.stringify(JSON.parse(req.postData), null, 2).substring(0, 300));
      } catch {
        console.log('  Body:', req.postData.substring(0, 200));
      }
    }
    console.log('');
  }

  await browser.close();
}

main().catch(console.error);
