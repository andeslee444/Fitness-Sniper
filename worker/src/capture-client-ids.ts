/**
 * Capture OAuth client_ids for iframe Mariana Tek studios.
 * Direct SPA studios use session auth (no client_id needed).
 *
 * Usage: npx tsx worker/src/capture-client-ids.ts
 */

import { chromium } from 'playwright-extra';
import StealthPlugin from 'puppeteer-extra-plugin-stealth';
import { STUDIOS } from '@fitness-sniper/shared';

chromium.use(StealthPlugin());
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

// Only iframe studios need OAuth client_ids
const IFRAME_STUDIOS = Object.entries(STUDIOS)
  .filter(([, s]) => s.iframe && s.iframe !== '')
  .map(([slug, s]) => ({ slug, tenant: s.tenant }));

async function captureForIframeStudio(
  slug: string,
  tenant: string,
  context: any,
): Promise<{ slug: string; tenant: string; clientId: string | null; error?: string }> {
  const page = await context.newPage();
  let clientId: string | null = null;

  page.on('request', (req: any) => {
    const url = req.url();
    if (url.includes('/o/authorize') && url.includes('client_id')) {
      const u = new URL(url);
      clientId = u.searchParams.get('client_id');
    }
  });

  try {
    // Step 1: Load schedule to find a class
    const scheduleUrl = `https://${tenant}.marianaiframes.com/iframe/schedule/daily/`;
    console.log(`[${slug}] Loading schedule: ${scheduleUrl}`);
    await page.goto(scheduleUrl, { timeout: 20000 });
    await page.waitForLoadState('networkidle').catch(() => {});
    await sleep(3000);

    // Dismiss cookies
    try {
      const btn = page.locator('button:has-text("ACCEPT"), button:has-text("Accept All")');
      if (await btn.first().isVisible({ timeout: 2000 }).catch(() => false)) {
        await btn.first().click();
        await sleep(1000);
      }
    } catch { /* */ }

    // Step 2: Find a reserve link — these are <a> tags with href like /iframe/classes/{id}/reserve
    const reserveLinks = await page.$$eval('a[href*="/reserve"]', (els: Element[]) =>
      els.map(e => (e as HTMLAnchorElement).href).slice(0, 3)
    );

    if (reserveLinks.length > 0) {
      console.log(`[${slug}] Found ${reserveLinks.length} reserve links. Navigating to first...`);
      await page.goto(reserveLinks[0], { timeout: 15000 });
    } else {
      // Try clicking a class row to find reserve
      const classLinks = await page.$$eval('a[href*="/classes/"]', (els: Element[]) =>
        els.map(e => (e as HTMLAnchorElement).href).slice(0, 3)
      );
      if (classLinks.length > 0) {
        console.log(`[${slug}] No reserve links, trying class link: ${classLinks[0]}`);
        await page.goto(classLinks[0], { timeout: 15000 });
      } else {
        // Construct a reserve URL by finding class IDs from the API
        console.log(`[${slug}] No links found, trying API to find a class...`);
        const today = new Date().toISOString().split('T')[0];
        const tomorrow = new Date(Date.now() + 86400000).toISOString().split('T')[0];
        try {
          const apiRes = await fetch(
            `https://${tenant}.marianatek.com/api/customer/v1/classes?min_start_date=${today}&max_start_date=${tomorrow}&page_size=5`
          );
          const apiData = await apiRes.json();
          const classes = apiData.results || [];
          if (classes.length > 0) {
            const classId = classes[0].id;
            const reserveUrl = `https://${tenant}.marianaiframes.com/iframe/classes/${classId}/reserve`;
            console.log(`[${slug}] Found class ${classId}, navigating to ${reserveUrl}`);
            await page.goto(reserveUrl, { timeout: 15000 });
          }
        } catch (e) {
          console.log(`[${slug}] API fetch failed: ${e}`);
        }
      }
    }

    await page.waitForLoadState('networkidle').catch(() => {});
    await sleep(2000);

    // Dismiss cookies again
    try {
      const btn = page.locator('button:has-text("ACCEPT"), button:has-text("Accept All")');
      if (await btn.first().isVisible({ timeout: 1000 }).catch(() => false)) {
        await btn.first().click();
        await sleep(500);
      }
    } catch { /* */ }

    // Step 3: Click "Log In" button
    const loginBtn = page.locator('button:has-text("Log In"), a:has-text("Log In"), button:has-text("LOG IN"), button:has-text("Sign In")');
    if (await loginBtn.first().isVisible({ timeout: 5000 }).catch(() => false)) {
      console.log(`[${slug}] Clicking Log In...`);
      await loginBtn.first().click();
      await sleep(4000);
    } else {
      console.log(`[${slug}] No Log In button found. Page URL: ${page.url()}`);
      const text = await page.evaluate(() => document.body?.innerText?.substring(0, 300) || '');
      console.log(`[${slug}] Page text: ${text.substring(0, 200)}`);
    }

    // Also check the page URL — client_id may be in the `next` query parameter
    if (!clientId) {
      const currentUrl = page.url();
      console.log(`[${slug}] After login click URL: ${currentUrl.substring(0, 200)}`);

      // Parse client_id from URL (could be in query or encoded in `next` param)
      const decoded = decodeURIComponent(decodeURIComponent(currentUrl));
      const cidMatch = decoded.match(/client_id[=]([a-zA-Z0-9]{20,50})/);
      if (cidMatch) {
        clientId = cidMatch[1];
        console.log(`[${slug}] Found client_id in URL: ${clientId}`);
      }
    }

    if (!clientId) {
      return { slug, tenant, clientId: null, error: 'client_id not captured' };
    }
    return { slug, tenant, clientId };
  } catch (err) {
    return { slug, tenant, clientId: null, error: err instanceof Error ? err.message : String(err) };
  } finally {
    await page.close();
  }
}

async function main() {
  console.log(`🌐 Launching browser...\n`);
  const browser = await chromium.launch({
    headless: true,
    args: ['--disable-blink-features=AutomationControlled', '--no-sandbox'],
  });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    viewport: { width: 1280, height: 720 },
  });

  // Already known
  const known: Record<string, string> = { barrysbootcamp: 'sbLziNCoF5HcOhkSV6zRL8O7betwd3mDDIQbWZa3' };

  console.log(`📡 Iframe studios to capture: ${IFRAME_STUDIOS.filter(s => !(s.tenant in known)).map(s => s.slug).join(', ')}`);
  console.log(`Already known: ${Object.entries(known).map(([t, id]) => `${t}=${id.substring(0, 10)}...`).join(', ')}\n`);

  // Capture remaining iframe studios in parallel
  const toCapture = IFRAME_STUDIOS.filter(s => !(s.tenant in known));
  const results = await Promise.all(
    toCapture.map(s => captureForIframeStudio(s.slug, s.tenant, context))
  );

  await context.close();
  await browser.close();

  // Combine results
  console.log('\n' + '='.repeat(80));
  console.log('RESULTS');
  console.log('='.repeat(80));

  // Known
  for (const [tenant, id] of Object.entries(known)) {
    const slug = IFRAME_STUDIOS.find(s => s.tenant === tenant)?.slug || tenant;
    console.log(`✅ ${slug.padEnd(15)} ${id}  [known]`);
  }

  // Newly captured
  for (const r of results) {
    if (r.clientId) {
      console.log(`✅ ${r.slug.padEnd(15)} ${r.clientId}  [captured]`);
    } else {
      console.log(`❌ ${r.slug.padEnd(15)} ${r.error}`);
    }
  }

  // Direct SPA studios
  const spaStudios = Object.entries(STUDIOS)
    .filter(([, s]) => !s.iframe || s.iframe === '')
    .map(([slug]) => slug);
  console.log(`\n🔑 Direct SPA studios (session auth, no client_id needed):`);
  console.log(`   ${spaStudios.join(', ')}`);

  // Output TypeScript
  const allClientIds = { ...known };
  for (const r of results) {
    if (r.clientId) allClientIds[r.tenant] = r.clientId;
  }

  console.log('\n// ── Copy into mariana-tek.ts ──');
  console.log('const OAUTH_CLIENT_IDS: Record<string, string> = {');
  for (const [tenant, id] of Object.entries(allClientIds)) {
    console.log(`  '${tenant}': '${id}',`);
  }
  console.log('};');
}

main().catch(console.error);
