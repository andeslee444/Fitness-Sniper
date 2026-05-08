#!/usr/bin/env node

/**
 * Class Sniper - Auto-book competitive fitness classes
 */

import { BarrysAdapter } from './adapters/barrys.js';
import { ClassPreferences, ClassInfo, StudioCredentials } from './adapters/base.js';
import * as fs from 'fs';
import * as path from 'path';

// Load config
const CONFIG_PATH = path.join(process.cwd(), 'config', 'preferences.json');

interface Config {
  studios: {
    barrys?: {
      email: string;
      password: string;
      preferences: ClassPreferences;
    };
  };
  notifications: {
    email?: string;
    sms?: string;
  };
}

function loadConfig(): Config | null {
  try {
    if (!fs.existsSync(CONFIG_PATH)) {
      console.error('❌ Config file not found:', CONFIG_PATH);
      console.log('📝 Create config/preferences.json from the example');
      return null;
    }
    const raw = fs.readFileSync(CONFIG_PATH, 'utf-8');
    return JSON.parse(raw);
  } catch (error) {
    console.error('❌ Error loading config:', error);
    return null;
  }
}

async function searchClasses() {
  const config = loadConfig();
  if (!config) return;
  
  const barrysConfig = config.studios.barrys;
  if (!barrysConfig) {
    console.log('ℹ️ No Barry\'s config found');
    return;
  }
  
  const adapter = new BarrysAdapter();
  
  try {
    // Login
    const credentials: StudioCredentials = {
      email: barrysConfig.email,
      password: barrysConfig.password,
    };
    
    const loggedIn = await adapter.login(credentials);
    if (!loggedIn) {
      console.error('❌ Could not log in');
      return;
    }
    
    // Search
    const classes = await adapter.searchClasses(barrysConfig.preferences);
    
    console.log('\n📋 Found Classes:\n');
    for (const c of classes) {
      const status = c.isBookable ? '✅ Available' : c.isWaitlist ? '⏳ Waitlist' : '❌ Full';
      console.log(`  ${status} | ${c.date} ${c.time} | ${c.location} | ${c.instructor} | ${c.className}`);
    }
    
  } finally {
    await adapter.close();
  }
}

async function snipe() {
  const config = loadConfig();
  if (!config) return;
  
  const barrysConfig = config.studios.barrys;
  if (!barrysConfig) {
    console.log('ℹ️ No Barry\'s config found');
    return;
  }
  
  console.log('🎯 Class Sniper starting...\n');
  
  const adapter = new BarrysAdapter();
  
  try {
    // Login
    const credentials: StudioCredentials = {
      email: barrysConfig.email,
      password: barrysConfig.password,
    };
    
    const loggedIn = await adapter.login(credentials);
    if (!loggedIn) {
      console.error('❌ Could not log in');
      return;
    }
    
    // Search for classes
    const classes = await adapter.searchClasses(barrysConfig.preferences);
    
    if (classes.length === 0) {
      console.log('📭 No matching classes found');
      return;
    }
    
    // Filter to bookable classes
    const bookable = classes.filter(c => c.isBookable);
    
    if (bookable.length === 0) {
      console.log('📭 No bookable classes available (all full or waitlist)');
      console.log(`   Found ${classes.length} matching classes, but none have open spots`);
      return;
    }
    
    console.log(`\n🎯 Found ${bookable.length} bookable classes:\n`);
    
    // Sort by date/time
    bookable.sort((a, b) => {
      const dateCompare = a.date.localeCompare(b.date);
      if (dateCompare !== 0) return dateCompare;
      return a.time.localeCompare(b.time);
    });
    
    for (const c of bookable) {
      console.log(`  📍 ${c.date} ${c.time} | ${c.location} | ${c.instructor}`);
    }
    
    // Book the first available class
    const targetClass = bookable[0];
    console.log(`\n🎯 Attempting to book: ${targetClass.date} ${targetClass.time} at ${targetClass.location}...`);
    
    const result = await adapter.bookClass(targetClass);
    
    if (result.success) {
      console.log('\n✅ SUCCESS! Class booked!');
      console.log(`   📍 ${result.classInfo.location}`);
      console.log(`   📅 ${result.classInfo.date} ${result.classInfo.time}`);
      console.log(`   👤 ${result.classInfo.instructor}`);
      if (result.confirmationId) {
        console.log(`   🔖 Confirmation: ${result.confirmationId}`);
      }
      
      // TODO: Send notification
      await sendNotification(config, result.classInfo);
      
    } else {
      console.log('\n❌ Booking failed:', result.error);
    }
    
  } finally {
    await adapter.close();
  }
}

async function sendNotification(config: Config, classInfo: ClassInfo) {
  const { email, sms } = config.notifications;
  
  const message = `🎯 Class Sniper booked your class!\n\n` +
    `📍 ${classInfo.location}\n` +
    `📅 ${classInfo.date} at ${classInfo.time}\n` +
    `👤 Instructor: ${classInfo.instructor}\n` +
    `🏋️ ${classInfo.className}`;
  
  if (email) {
    console.log(`📧 Would send email to: ${email}`);
    // TODO: Implement email sending
  }
  
  if (sms) {
    console.log(`📱 Would send SMS to: ${sms}`);
    // TODO: Implement SMS sending
  }
  
  // For now, just log
  console.log('\n📬 Notification message:');
  console.log(message);
}

// CLI
const command = process.argv[2];

switch (command) {
  case 'search':
    searchClasses();
    break;
  case 'snipe':
    snipe();
    break;
  default:
    console.log(`
🎯 Class Sniper

Usage:
  npm run search   - Search for available classes
  npm run snipe    - Search and book first matching class

Setup:
  1. Copy config/preferences.example.json to config/preferences.json
  2. Edit with your credentials and preferences
  3. Run 'npm run snipe'
    `);
}
