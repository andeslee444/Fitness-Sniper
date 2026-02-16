/**
 * Auto-Sniper - Automatic class booking when spots open
 * 
 * Monitors target classes and books instantly when available.
 * Designed to run via cron/launchd every 1-5 minutes.
 * 
 * Created: 2026-02-13
 */

import * as fs from 'fs';
import * as path from 'path';

// ============================================================
// TYPES
// ============================================================

export interface ClassTarget {
  id: string;                    // Unique ID for this target
  studio: 'barrys' | 'aarmy';
  location: string;
  dayOfWeek: number;             // 0=Sun, 1=Mon, etc.
  time: string;                  // "6:00 AM", "6:00 PM"
  classType?: string;            // Optional filter
  instructor?: string;           // Optional preference
  preferredSpots?: string[];     // ["F-1", "F-3", "T-10"] in priority order
  enabled: boolean;
  lastChecked?: string;
  lastBooked?: string;
}

export interface SniperConfig {
  credentials: {
    barrys?: { email: string; password: string };
    aarmy?: { email: string; password: string };
  };
  targets: ClassTarget[];
  settings: {
    checkIntervalMs: number;     // How often to check (when running continuously)
    bookingWindowDays: number;   // How many days ahead classes open (usually 7)
    notifyOnBook: boolean;
    notifyPhone?: string;
    dryRun: boolean;             // If true, don't actually book
  };
}

export interface CheckResult {
  targetId: string;
  available: boolean;
  spotsFound: string[];
  booked: boolean;
  bookedSpot?: string;
  error?: string;
  timestamp: string;
}

// ============================================================
// BROWSER COMMANDS (for OpenClaw browser tool)
// ============================================================

const STUDIOS = {
  barrys: {
    scheduleUrl: (loc: string) => `https://www.barrys.com/schedule/${loc}`,
    iframe: 'iframe.visible',
    loginSelectors: {
      email: 'textbox "Email"',
      password: 'textbox "Password"',
      submit: 'button "Log in"'
    }
  },
  aarmy: {
    scheduleUrl: () => 'https://mt.aarmy.com/index.html?_mt=%2Fschedule%2Fdaily',
    iframe: 'iframe',
    loginSelectors: {
      email: 'textbox "Email"',
      password: 'textbox "Password"',
      submit: 'button "Log in"'
    }
  }
};

// ============================================================
// CORE SNIPER LOGIC
// ============================================================

/**
 * Load config from file
 */
export function loadConfig(): SniperConfig {
  const configPath = path.join(__dirname, '../config/sniper-config.json');
  if (!fs.existsSync(configPath)) {
    // Create default config
    const defaultConfig: SniperConfig = {
      credentials: {
        barrys: { email: '', password: '' },
        aarmy: { email: '', password: '' }
      },
      targets: [],
      settings: {
        checkIntervalMs: 60000,  // 1 minute
        bookingWindowDays: 7,
        notifyOnBook: true,
        notifyPhone: '+14255336828',
        dryRun: true  // Safe default
      }
    };
    fs.writeFileSync(configPath, JSON.stringify(defaultConfig, null, 2));
    console.log(`Created default config at ${configPath}`);
    return defaultConfig;
  }
  return JSON.parse(fs.readFileSync(configPath, 'utf-8'));
}

/**
 * Save config back to file
 */
export function saveConfig(config: SniperConfig): void {
  const configPath = path.join(__dirname, '../config/sniper-config.json');
  fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
}

/**
 * Calculate next occurrence of a class
 */
export function getNextClassDate(dayOfWeek: number, time: string): Date {
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

/**
 * Check if a class is within booking window
 */
export function isInBookingWindow(classDate: Date, windowDays: number): boolean {
  const now = new Date();
  const windowStart = new Date(now);
  const windowEnd = new Date(now);
  windowEnd.setDate(windowEnd.getDate() + windowDays);
  
  return classDate >= windowStart && classDate <= windowEnd;
}

/**
 * Generate browser commands for checking a class
 */
export function generateCheckCommands(target: ClassTarget): object[] {
  const studio = STUDIOS[target.studio];
  const url = target.studio === 'barrys'
    ? studio.scheduleUrl(target.location)
    : (studio.scheduleUrl as () => string)();

  return [
    // Navigate
    { action: 'navigate', profile: 'openclaw', targetUrl: url },
    // Wait
    { action: 'act', profile: 'openclaw', request: { kind: 'wait', timeMs: 1500 } },
    // Snapshot schedule
    { action: 'snapshot', profile: 'openclaw', frame: studio.iframe, interactive: true }
  ];
}

/**
 * Generate browser commands for booking a class
 */
export function generateBookCommands(
  target: ClassTarget,
  reserveRef: string,
  spotRef: string
): object[] {
  const studio = STUDIOS[target.studio];
  
  return [
    // Click Reserve
    { 
      action: 'act', 
      profile: 'openclaw', 
      frame: studio.iframe,
      request: { kind: 'click', ref: reserveRef }
    },
    // Wait for spot selection
    { action: 'act', profile: 'openclaw', request: { kind: 'wait', timeMs: 1000 } },
    // Click spot
    {
      action: 'act',
      profile: 'openclaw',
      frame: studio.iframe,
      request: { kind: 'click', ref: spotRef }
    },
    // Wait for confirm modal
    { action: 'act', profile: 'openclaw', request: { kind: 'wait', timeMs: 500 } },
    // Click confirm
    {
      action: 'act',
      profile: 'openclaw',
      frame: studio.iframe,
      request: { kind: 'click', ref: 'link "Buy & Reserve Class"' }
    }
  ];
}

/**
 * Parse snapshot to find available classes
 */
export function parseScheduleSnapshot(snapshot: string, targetTime: string): {
  found: boolean;
  reserveRef?: string;
  isWaitlist: boolean;
} {
  const lines = snapshot.split('\n');
  
  // Look for Reserve link near the target time
  // Format: "6:00 PM" or "18:00"
  let foundTimeSection = false;
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    
    // Check if this line contains our target time
    if (line.includes(targetTime) || line.includes(targetTime.replace(' ', ''))) {
      foundTimeSection = true;
    }
    
    // If we're in the time section, look for Reserve
    if (foundTimeSection) {
      const reserveMatch = line.match(/link "Reserve" \[ref=(e\d+)\]/);
      if (reserveMatch) {
        return { found: true, reserveRef: reserveMatch[1], isWaitlist: false };
      }
      
      const waitlistMatch = line.match(/link "Join Waitlist" \[ref=(e\d+)\]/);
      if (waitlistMatch) {
        return { found: true, reserveRef: waitlistMatch[1], isWaitlist: true };
      }
      
      // If we hit another time, we've passed our target
      if (line.match(/\d{1,2}:\d{2}/) && !line.includes(targetTime)) {
        foundTimeSection = false;
      }
    }
  }
  
  // Fallback: just find first Reserve link
  const anyReserve = snapshot.match(/link "Reserve" \[ref=(e\d+)\]/);
  if (anyReserve) {
    return { found: true, reserveRef: anyReserve[1], isWaitlist: false };
  }
  
  return { found: false, isWaitlist: false };
}

/**
 * Parse spot selection snapshot to find best available spot
 */
export function parseSpotSnapshot(
  snapshot: string, 
  preferredSpots?: string[]
): { spotRef?: string; spotName?: string } {
  const lines = snapshot.split('\n');
  const availableSpots: { ref: string; name: string }[] = [];
  
  for (const line of lines) {
    // Match: button "Available Spot" [ref=e49] with img: F-1
    const spotMatch = line.match(/button "Available Spot" \[ref=(e\d+)\].*?img: ([A-Z]+-\d+)/);
    if (spotMatch) {
      availableSpots.push({ ref: spotMatch[1], name: spotMatch[2] });
    }
  }
  
  if (availableSpots.length === 0) return {};
  
  // If we have preferences, try to match them
  if (preferredSpots && preferredSpots.length > 0) {
    for (const pref of preferredSpots) {
      const match = availableSpots.find(s => s.name === pref);
      if (match) return { spotRef: match.ref, spotName: match.name };
    }
  }
  
  // Otherwise return first available
  return { spotRef: availableSpots[0].ref, spotName: availableSpots[0].name };
}

// ============================================================
// MAIN SNIPER RUNNER
// ============================================================

/**
 * Main sniper check - run this via cron
 * 
 * Outputs commands to execute via OpenClaw browser tool
 */
export async function runSniperCheck(): Promise<void> {
  console.log('🎯 Auto-Sniper Check Starting...');
  console.log(`Time: ${new Date().toISOString()}`);
  
  const config = loadConfig();
  const { targets, settings } = config;
  
  const enabledTargets = targets.filter(t => t.enabled);
  console.log(`\nEnabled targets: ${enabledTargets.length}`);
  
  if (enabledTargets.length === 0) {
    console.log('No enabled targets. Add targets to config/sniper-config.json');
    return;
  }
  
  for (const target of enabledTargets) {
    const nextClass = getNextClassDate(target.dayOfWeek, target.time);
    const inWindow = isInBookingWindow(nextClass, settings.bookingWindowDays);
    
    const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    console.log(`\n[${target.id}] ${target.studio} ${target.location}`);
    console.log(`  ${dayNames[target.dayOfWeek]} @ ${target.time}`);
    console.log(`  Next class: ${nextClass.toLocaleString()}`);
    console.log(`  In booking window: ${inWindow ? 'YES ✅' : 'NO (skip)'}`);
    
    if (!inWindow) continue;
    
    // Generate check commands
    console.log('\n  Commands to check availability:');
    const commands = generateCheckCommands(target);
    commands.forEach((cmd, i) => {
      console.log(`  ${i + 1}. ${JSON.stringify(cmd)}`);
    });
    
    // Update last checked
    target.lastChecked = new Date().toISOString();
  }
  
  saveConfig(config);
  console.log('\n✅ Sniper check complete. Run commands above to check availability.');
}

/**
 * Add a new target
 */
export function addTarget(target: Omit<ClassTarget, 'id' | 'enabled'>): ClassTarget {
  const config = loadConfig();
  
  const newTarget: ClassTarget = {
    ...target,
    id: `${target.studio}-${target.location}-${target.dayOfWeek}-${target.time.replace(/[: ]/g, '')}`,
    enabled: true
  };
  
  // Check for duplicate
  const existing = config.targets.find(t => t.id === newTarget.id);
  if (existing) {
    console.log(`Target already exists: ${newTarget.id}`);
    return existing;
  }
  
  config.targets.push(newTarget);
  saveConfig(config);
  console.log(`Added target: ${newTarget.id}`);
  return newTarget;
}

/**
 * List all targets
 */
export function listTargets(): void {
  const config = loadConfig();
  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  
  console.log('\n🎯 Sniper Targets:');
  console.log('─'.repeat(60));
  
  for (const target of config.targets) {
    const status = target.enabled ? '✅' : '⏸️';
    const nextClass = getNextClassDate(target.dayOfWeek, target.time);
    
    console.log(`${status} [${target.id}]`);
    console.log(`   ${target.studio} ${target.location} - ${dayNames[target.dayOfWeek]} @ ${target.time}`);
    console.log(`   Next: ${nextClass.toLocaleDateString()}`);
    if (target.preferredSpots) {
      console.log(`   Spots: ${target.preferredSpots.join(', ')}`);
    }
    console.log('');
  }
}

// ============================================================
// CLI
// ============================================================

if (require.main === module) {
  const args = process.argv.slice(2);
  const command = args[0];
  
  switch (command) {
    case 'check':
      runSniperCheck();
      break;
      
    case 'list':
      listTargets();
      break;
      
    case 'add':
      // Example: npx ts-node auto-sniper.ts add barrys noho 1 "6:00 AM" F-1,F-3,T-10
      if (args.length < 5) {
        console.log('Usage: add <studio> <location> <dayOfWeek> <time> [spots]');
        console.log('Example: add barrys noho 1 "6:00 AM" F-1,F-3,T-10');
        process.exit(1);
      }
      addTarget({
        studio: args[1] as 'barrys' | 'aarmy',
        location: args[2],
        dayOfWeek: parseInt(args[3]),
        time: args[4],
        preferredSpots: args[5]?.split(',')
      });
      break;
      
    default:
      console.log('Auto-Sniper Commands:');
      console.log('  check  - Run sniper check for all enabled targets');
      console.log('  list   - List all targets');
      console.log('  add    - Add a new target');
  }
}
