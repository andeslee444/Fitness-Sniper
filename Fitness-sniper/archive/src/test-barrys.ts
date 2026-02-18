/**
 * Test script to explore Barry's website structure
 * Run: npm test
 */

import { chromium } from 'playwright';

async function exploreSite() {
  console.log('🔍 Exploring Barry\'s website structure...\n');
  
  const browser = await chromium.launch({
    headless: false,
    slowMo: 500,
  });
  
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
  });
  
  const page = await context.newPage();
  
  try {
    // 1. Visit homepage
    console.log('📍 Visiting homepage...');
    await page.goto('https://www.barrys.com/', { waitUntil: 'networkidle' });
    console.log('   Title:', await page.title());
    
    // 2. Visit booking page
    console.log('\n📍 Visiting booking page...');
    await page.goto('https://www.barrys.com/book/', { waitUntil: 'networkidle' });
    console.log('   URL:', page.url());
    console.log('   Title:', await page.title());
    
    // 3. Look for login elements
    console.log('\n🔐 Looking for login elements...');
    const loginLink = await page.$('a:has-text("Log In"), a:has-text("Sign In"), .login-link');
    if (loginLink) {
      console.log('   Found login link');
      const href = await loginLink.getAttribute('href');
      console.log('   Href:', href);
    } else {
      console.log('   No login link found on page');
    }
    
    // 4. Check for location selector
    console.log('\n📍 Looking for location selector...');
    const locationSelectors = await page.$$('[data-location], .location-select, .studio-selector, select');
    console.log(`   Found ${locationSelectors.length} potential location selectors`);
    
    // 5. Check for class cards
    console.log('\n📋 Looking for class cards...');
    const classCards = await page.$$('.class-card, .schedule-item, .class-slot, [data-class], .booking-tile');
    console.log(`   Found ${classCards.length} potential class cards`);
    
    // 6. Get page structure
    console.log('\n📄 Page structure (main elements):');
    const mainElements = await page.$$('main, .main-content, #content, [role="main"]');
    for (const el of mainElements) {
      const tagName = await el.evaluate(node => node.tagName);
      const className = await el.getAttribute('class');
      console.log(`   ${tagName}: ${className || '(no class)'}`);
    }
    
    // 7. Look for any interactive elements
    console.log('\n🔘 Interactive elements:');
    const buttons = await page.$$('button, [role="button"], .btn');
    console.log(`   Buttons: ${buttons.length}`);
    
    const inputs = await page.$$('input, select');
    console.log(`   Inputs/Selects: ${inputs.length}`);
    
    // 8. Screenshot for reference
    console.log('\n📸 Taking screenshot...');
    await page.screenshot({ 
      path: 'config/barrys-booking-page.png',
      fullPage: true 
    });
    console.log('   Saved to config/barrys-booking-page.png');
    
    // 9. Get network requests (to find API endpoints)
    console.log('\n🌐 Monitoring network requests (reload page)...');
    const requests: string[] = [];
    page.on('request', request => {
      const url = request.url();
      if (url.includes('api') || url.includes('class') || url.includes('schedule')) {
        requests.push(`${request.method()} ${url}`);
      }
    });
    
    await page.reload({ waitUntil: 'networkidle' });
    
    console.log('   API-like requests found:');
    for (const req of requests.slice(0, 10)) {
      console.log(`     ${req}`);
    }
    
    console.log('\n✅ Exploration complete!');
    console.log('   Check the screenshot and adjust selectors in barrys.ts as needed.\n');
    
    // Keep browser open for manual inspection
    console.log('⏳ Browser will close in 30 seconds (inspect manually if needed)...');
    await page.waitForTimeout(30000);
    
  } catch (error) {
    console.error('❌ Error:', error);
  } finally {
    await browser.close();
  }
}

exploreSite();
