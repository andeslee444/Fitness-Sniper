/**
 * Studio Site Explorer
 * Explores multiple fitness studio websites to document structure for automation
 * 
 * Run: npx tsx src/explore-studios.ts
 */

import { chromium, Browser, Page } from 'playwright';
import * as fs from 'fs';
import * as path from 'path';

interface StudioConfig {
  name: string;
  bookingUrl: string;
  loginUrl?: string;
  selectors: {
    classCard?: string[];
    bookButton?: string[];
    loginForm?: string[];
    locationFilter?: string[];
  };
}

const STUDIOS: StudioConfig[] = [
  {
    name: "barrys",
    bookingUrl: "https://www.barrys.com/book/",
    loginUrl: "https://www.barrys.com/login/",
    selectors: {
      classCard: ['.class-card', '.schedule-item', '[data-class-id]', '.booking-tile', '.class-slot'],
      bookButton: ['button:has-text("Book")', '.book-btn', '[data-book]'],
      loginForm: ['input[type="email"]', 'input[name="email"]', '#email'],
      locationFilter: ['.location-filter', '[data-location]', '.studio-select'],
    }
  },
  {
    name: "soulcycle",
    bookingUrl: "https://www.soul-cycle.com/find-a-class/",
    loginUrl: "https://www.soul-cycle.com/login/",
    selectors: {
      classCard: ['.class-card', '.schedule-class', '[data-class]', '.class-item'],
      bookButton: ['button:has-text("Book")', '.book-class', '[data-book]'],
      loginForm: ['input[type="email"]', '#email', 'input[name="username"]'],
      locationFilter: ['.location-picker', '.studio-filter', '[data-studio]'],
    }
  },
  {
    name: "equinox",
    bookingUrl: "https://www.equinox.com/classes",
    loginUrl: "https://www.equinox.com/login",
    selectors: {
      classCard: ['.class-card', '.schedule-item', '.class-listing', '[data-class-id]'],
      bookButton: ['button:has-text("Book")', '.reserve-btn', '[data-reserve]'],
      loginForm: ['input[type="email"]', '#email', 'input[name="email"]'],
      locationFilter: ['.club-selector', '.location-filter', '[data-club]'],
    }
  },
  {
    name: "rumble",
    bookingUrl: "https://www.doyourumble.com/classes",
    loginUrl: "https://www.doyourumble.com/login",
    selectors: {
      classCard: ['.class-card', '.class-item', '[data-class]', '.schedule-class'],
      bookButton: ['button:has-text("Book")', '.book-btn', '[data-book]'],
      loginForm: ['input[type="email"]', '#email', 'input[name="email"]'],
      locationFilter: ['.location-select', '.studio-picker', '[data-location]'],
    }
  },
];

interface ExplorationResult {
  studio: string;
  url: string;
  timestamp: string;
  success: boolean;
  error?: string;
  title?: string;
  findings: {
    classCards: { selector: string; count: number }[];
    bookButtons: { selector: string; count: number }[];
    loginElements: { selector: string; count: number }[];
    locationFilters: { selector: string; count: number }[];
    allButtons: number;
    allInputs: number;
    forms: number;
  };
  recommendedSelectors: {
    classCard?: string;
    bookButton?: string;
    loginEmail?: string;
    locationFilter?: string;
  };
  screenshotPath?: string;
  networkRequests: string[];
}

async function exploreStudio(browser: Browser, studio: StudioConfig): Promise<ExplorationResult> {
  const result: ExplorationResult = {
    studio: studio.name,
    url: studio.bookingUrl,
    timestamp: new Date().toISOString(),
    success: false,
    findings: {
      classCards: [],
      bookButtons: [],
      loginElements: [],
      locationFilters: [],
      allButtons: 0,
      allInputs: 0,
      forms: 0,
    },
    recommendedSelectors: {},
    networkRequests: [],
  };

  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    viewport: { width: 1280, height: 800 },
  });

  const page = await context.newPage();

  // Capture network requests
  page.on('request', request => {
    const url = request.url();
    if (url.includes('api') || url.includes('class') || url.includes('schedule') || url.includes('book')) {
      result.networkRequests.push(`${request.method()} ${url}`);
    }
  });

  try {
    console.log(`\n🔍 Exploring ${studio.name}...`);
    
    // Visit booking page
    await page.goto(studio.bookingUrl, { waitUntil: 'networkidle', timeout: 30000 });
    result.title = await page.title();
    
    // Test each selector type
    for (const selector of studio.selectors.classCard || []) {
      const count = await page.$$(selector).then(els => els.length);
      result.findings.classCards.push({ selector, count });
      if (count > 0 && !result.recommendedSelectors.classCard) {
        result.recommendedSelectors.classCard = selector;
      }
    }

    for (const selector of studio.selectors.bookButton || []) {
      const count = await page.$$(selector).then(els => els.length);
      result.findings.bookButtons.push({ selector, count });
      if (count > 0 && !result.recommendedSelectors.bookButton) {
        result.recommendedSelectors.bookButton = selector;
      }
    }

    for (const selector of studio.selectors.locationFilter || []) {
      const count = await page.$$(selector).then(els => els.length);
      result.findings.locationFilters.push({ selector, count });
      if (count > 0 && !result.recommendedSelectors.locationFilter) {
        result.recommendedSelectors.locationFilter = selector;
      }
    }

    // Count general elements
    result.findings.allButtons = await page.$$('button, [role="button"], .btn').then(els => els.length);
    result.findings.allInputs = await page.$$('input, select').then(els => els.length);
    result.findings.forms = await page.$$('form').then(els => els.length);

    // Take screenshot
    const screenshotDir = path.join(process.cwd(), 'exploration');
    if (!fs.existsSync(screenshotDir)) {
      fs.mkdirSync(screenshotDir, { recursive: true });
    }
    const screenshotPath = path.join(screenshotDir, `${studio.name}-booking.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });
    result.screenshotPath = screenshotPath;

    // Also check login page if available
    if (studio.loginUrl) {
      await page.goto(studio.loginUrl, { waitUntil: 'networkidle', timeout: 30000 });
      
      for (const selector of studio.selectors.loginForm || []) {
        const count = await page.$$(selector).then(els => els.length);
        result.findings.loginElements.push({ selector, count });
        if (count > 0 && !result.recommendedSelectors.loginEmail) {
          result.recommendedSelectors.loginEmail = selector;
        }
      }

      // Screenshot login page
      const loginScreenshotPath = path.join(screenshotDir, `${studio.name}-login.png`);
      await page.screenshot({ path: loginScreenshotPath, fullPage: true });
    }

    result.success = true;
    console.log(`✅ ${studio.name} exploration complete`);

  } catch (error) {
    result.error = String(error);
    console.error(`❌ ${studio.name} exploration failed:`, error);
  } finally {
    await context.close();
  }

  return result;
}

async function main() {
  console.log('🚀 Starting studio exploration...\n');
  console.log('Studios to explore:', STUDIOS.map(s => s.name).join(', '));

  const browser = await chromium.launch({
    headless: true, // Run headless for Harbor
  });

  const results: ExplorationResult[] = [];

  for (const studio of STUDIOS) {
    const result = await exploreStudio(browser, studio);
    results.push(result);
    
    // Brief pause between studios
    await new Promise(resolve => setTimeout(resolve, 2000));
  }

  await browser.close();

  // Save results
  const outputPath = path.join(process.cwd(), 'exploration', 'results.json');
  fs.writeFileSync(outputPath, JSON.stringify(results, null, 2));
  console.log(`\n📄 Results saved to ${outputPath}`);

  // Generate summary report
  const summaryPath = path.join(process.cwd(), 'exploration', 'SUMMARY.md');
  let summary = `# Studio Exploration Summary\n\nGenerated: ${new Date().toISOString()}\n\n`;

  for (const result of results) {
    summary += `## ${result.studio.toUpperCase()}\n\n`;
    summary += `- **URL:** ${result.url}\n`;
    summary += `- **Status:** ${result.success ? '✅ Success' : '❌ Failed'}\n`;
    if (result.error) {
      summary += `- **Error:** ${result.error}\n`;
    }
    summary += `- **Title:** ${result.title || 'N/A'}\n`;
    summary += `\n### Findings\n\n`;
    summary += `| Element | Count | Recommended Selector |\n`;
    summary += `|---------|-------|---------------------|\n`;
    summary += `| Class Cards | ${result.findings.classCards.reduce((sum, f) => sum + f.count, 0)} | \`${result.recommendedSelectors.classCard || 'none found'}\` |\n`;
    summary += `| Book Buttons | ${result.findings.bookButtons.reduce((sum, f) => sum + f.count, 0)} | \`${result.recommendedSelectors.bookButton || 'none found'}\` |\n`;
    summary += `| Location Filters | ${result.findings.locationFilters.reduce((sum, f) => sum + f.count, 0)} | \`${result.recommendedSelectors.locationFilter || 'none found'}\` |\n`;
    summary += `| Login Email | ${result.findings.loginElements.reduce((sum, f) => sum + f.count, 0)} | \`${result.recommendedSelectors.loginEmail || 'none found'}\` |\n`;
    summary += `\n### General Counts\n\n`;
    summary += `- Buttons: ${result.findings.allButtons}\n`;
    summary += `- Inputs: ${result.findings.allInputs}\n`;
    summary += `- Forms: ${result.findings.forms}\n`;
    summary += `\n### API Endpoints Detected\n\n`;
    if (result.networkRequests.length > 0) {
      for (const req of result.networkRequests.slice(0, 10)) {
        summary += `- \`${req}\`\n`;
      }
      if (result.networkRequests.length > 10) {
        summary += `- ... and ${result.networkRequests.length - 10} more\n`;
      }
    } else {
      summary += `- No API endpoints detected\n`;
    }
    summary += `\n---\n\n`;
  }

  fs.writeFileSync(summaryPath, summary);
  console.log(`📋 Summary saved to ${summaryPath}`);

  // Print quick summary
  console.log('\n📊 Quick Summary:\n');
  for (const result of results) {
    const status = result.success ? '✅' : '❌';
    const classCards = result.findings.classCards.reduce((sum, f) => sum + f.count, 0);
    const bookBtns = result.findings.bookButtons.reduce((sum, f) => sum + f.count, 0);
    console.log(`${status} ${result.studio.padEnd(12)} | Classes: ${classCards.toString().padStart(3)} | Book btns: ${bookBtns.toString().padStart(3)}`);
  }
}

main().catch(console.error);
