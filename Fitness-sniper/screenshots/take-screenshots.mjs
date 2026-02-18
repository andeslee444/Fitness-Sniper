import { chromium } from 'playwright';

const BASE = 'http://localhost:3000';
const DIR = '/Users/andeslee/Documents/Cursor-Projects/Fitness-sniper/screenshots';

const publicPages = [
  { name: '01-landing', url: '/' },
  { name: '02-login', url: '/login' },
  { name: '03-signup', url: '/signup' },
];

// These will redirect to /login if not authenticated
const authPages = [
  { name: '04-dashboard', url: '/dashboard' },
  { name: '05-targets', url: '/targets' },
  { name: '06-history', url: '/history' },
  { name: '07-credentials', url: '/credentials' },
];

async function run() {
  const browser = await chromium.launch();

  // Desktop
  const desktop = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    colorScheme: 'dark',
  });

  // Mobile
  const mobile = await browser.newContext({
    viewport: { width: 390, height: 844 },
    colorScheme: 'dark',
    isMobile: true,
  });

  for (const p of [...publicPages, ...authPages]) {
    const dPage = await desktop.newPage();
    await dPage.goto(BASE + p.url, { waitUntil: 'networkidle', timeout: 10000 }).catch(() => {});
    await dPage.waitForTimeout(500);
    await dPage.screenshot({ path: `${DIR}/${p.name}-desktop.png`, fullPage: true });
    console.log(`✓ ${p.name} desktop (at ${dPage.url()})`);
    await dPage.close();

    const mPage = await mobile.newPage();
    await mPage.goto(BASE + p.url, { waitUntil: 'networkidle', timeout: 10000 }).catch(() => {});
    await mPage.waitForTimeout(500);
    await mPage.screenshot({ path: `${DIR}/${p.name}-mobile.png`, fullPage: true });
    console.log(`✓ ${p.name} mobile (at ${mPage.url()})`);
    await mPage.close();
  }

  await browser.close();
  console.log('\nDone! Screenshots saved to:', DIR);
}

run().catch(console.error);
