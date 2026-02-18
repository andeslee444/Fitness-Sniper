#!/usr/bin/env npx ts-node
/**
 * Sniper Runner - Executes auto-booking via OpenClaw
 * 
 * Run via: npx ts-node scripts/sniper-runner.ts
 * Or via launchd every 5 minutes
 * 
 * Created: 2026-02-13
 */

import * as fs from 'fs';
import * as path from 'path';
import { execSync } from 'child_process';

interface SniperConfig {
  credentials: {
    barrys?: { email: string; password: string };
    aarmy?: { email: string; password: string };
  };
  targets: Array<{
    id: string;
    studio: 'barrys' | 'aarmy';
    location: string;
    dayOfWeek: number;
    time: string;
    preferredSpots?: string[];
    enabled: boolean;
    lastChecked?: string;
    lastBooked?: string;
  }>;
  settings: {
    checkIntervalMs: number;
    bookingWindowDays: number;
    notifyOnBook: boolean;
    notifyPhone?: string;
    dryRun: boolean;
  };
}

interface BookingLog {
  timestamp: string;
  targetId: string;
  action: 'check' | 'book' | 'skip' | 'error';
  details: string;
}

const CONFIG_PATH = path.join(__dirname, '../config/sniper-config.json');
const LOG_PATH = path.join(__dirname, '../logs/sniper.log');
const STATE_PATH = path.join(__dirname, '../state/sniper-state.json');

// Ensure directories exist
fs.mkdirSync(path.dirname(LOG_PATH), { recursive: true });
fs.mkdirSync(path.dirname(STATE_PATH), { recursive: true });

function log(entry: BookingLog): void {
  const line = `[${entry.timestamp}] ${entry.action.toUpperCase()} [${entry.targetId}] ${entry.details}`;
  console.log(line);
  fs.appendFileSync(LOG_PATH, line + '\n');
}

function loadConfig(): SniperConfig {
  return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf-8'));
}

function getNextClassDate(dayOfWeek: number, time: string): Date {
  const now = new Date();
  const [timePart, ampm] = time.split(' ');
  let [hours, minutes] = timePart.split(':').map(Number);
  
  if (ampm?.toUpperCase() === 'PM' && hours !== 12) hours += 12;
  if (ampm?.toUpperCase() === 'AM' && hours === 12) hours = 0;
  
  const target = new Date(now);
  target.setHours(hours, minutes || 0, 0, 0);
  
  const daysUntil = (dayOfWeek - now.getDay() + 7) % 7;
  target.setDate(target.getDate() + daysUntil);
  
  if (daysUntil === 0 && target <= now) {
    target.setDate(target.getDate() + 7);
  }
  
  return target;
}

function isInBookingWindow(classDate: Date, windowDays: number): boolean {
  const now = new Date();
  const windowEnd = new Date(now);
  windowEnd.setDate(windowEnd.getDate() + windowDays);
  return classDate >= now && classDate <= windowEnd;
}

/**
 * Execute OpenClaw browser command and return output
 */
function browserCommand(cmd: string): string {
  try {
    const result = execSync(`openclaw browser ${cmd}`, {
      encoding: 'utf-8',
      timeout: 30000
    });
    return result;
  } catch (err: any) {
    return err.stdout || err.message;
  }
}

/**
 * Send notification via iMessage
 */
function notify(message: string, phone?: string): void {
  if (!phone) return;
  try {
    // Use AppleScript for iMessage
    const script = `tell application "Messages"
      set targetService to 1st account whose service type = iMessage
      set targetBuddy to participant "${phone}" of targetService
      send "${message}" to targetBuddy
    end tell`;
    execSync(`osascript -e '${script}'`);
  } catch (err) {
    console.error('Failed to send notification:', err);
  }
}

/**
 * Main sniper execution
 */
async function runSniper(): Promise<void> {
  console.log('🎯 Class Sniper Running...');
  console.log(`Time: ${new Date().toISOString()}\n`);
  
  const config = loadConfig();
  const { targets, settings, credentials } = config;
  
  const enabledTargets = targets.filter(t => t.enabled);
  
  if (enabledTargets.length === 0) {
    console.log('No enabled targets.');
    return;
  }
  
  for (const target of enabledTargets) {
    const nextClass = getNextClassDate(target.dayOfWeek, target.time);
    const inWindow = isInBookingWindow(nextClass, settings.bookingWindowDays);
    
    const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    
    log({
      timestamp: new Date().toISOString(),
      targetId: target.id,
      action: 'check',
      details: `${target.studio} ${target.location} ${dayNames[target.dayOfWeek]} ${target.time} - Next: ${nextClass.toLocaleDateString()}`
    });
    
    if (!inWindow) {
      log({
        timestamp: new Date().toISOString(),
        targetId: target.id,
        action: 'skip',
        details: 'Not in booking window yet'
      });
      continue;
    }
    
    // Check if already booked today
    if (target.lastBooked) {
      const lastBooked = new Date(target.lastBooked);
      const today = new Date();
      if (lastBooked.toDateString() === today.toDateString()) {
        log({
          timestamp: new Date().toISOString(),
          targetId: target.id,
          action: 'skip',
          details: 'Already booked today'
        });
        continue;
      }
    }
    
    // Navigate to schedule
    const studio = target.studio;
    const scheduleUrl = studio === 'barrys'
      ? `https://www.barrys.com/schedule/${target.location}`
      : 'https://mt.aarmy.com/index.html?_mt=%2Fschedule%2Fdaily';
    const iframe = studio === 'barrys' ? 'iframe.visible' : 'iframe';
    
    console.log(`  Checking ${scheduleUrl}...`);
    
    // In a real implementation, we'd use the browser tool here
    // For now, output the commands that would be run
    console.log(`\n  === Commands for ${target.id} ===`);
    console.log(`  1. browser action=navigate targetUrl="${scheduleUrl}"`);
    console.log(`  2. browser action=act request='{"kind":"wait","timeMs":1500}'`);
    console.log(`  3. browser action=snapshot frame="${iframe}" interactive=true`);
    console.log(`  4. [Parse snapshot for "Reserve" near "${target.time}"]`);
    console.log(`  5. [If found: click Reserve → select spot → confirm]`);
    console.log('');
    
    // Update last checked
    target.lastChecked = new Date().toISOString();
  }
  
  // Save updated config
  fs.writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2));
  
  console.log('✅ Sniper check complete.');
}

// Run
runSniper().catch(console.error);
