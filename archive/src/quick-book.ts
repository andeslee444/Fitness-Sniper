/**
 * Quick Book - Minimal round-trip class booking
 * 
 * Usage:
 *   quickBook('barrys', 'noho', '6:00 PM', 'F-1')
 *   quickBook('aarmy', 'chelsea', '5:00 PM')
 * 
 * Created: 2026-02-13
 */

export interface QuickBookOptions {
  studio: 'barrys' | 'aarmy';
  location: string;
  targetTime?: string;      // e.g., "6:00 PM" - if not provided, books first available
  preferredSpot?: string;   // e.g., "F-1", "T-10" - if not provided, selects first available
  dryRun?: boolean;         // If true, stops before final confirmation
}

export interface BookingResult {
  success: boolean;
  className?: string;
  time?: string;
  spot?: string;
  error?: string;
  steps: string[];
}

const STUDIOS = {
  barrys: {
    scheduleUrl: (loc: string) => `https://www.barrys.com/schedule/${loc}`,
    iframe: 'iframe.visible',
  },
  aarmy: {
    scheduleUrl: () => 'https://mt.aarmy.com/index.html?_mt=%2Fschedule%2Fdaily',
    iframe: 'iframe',
  }
};

/**
 * OpenClaw browser command sequence for quick booking
 * 
 * Returns array of commands to execute via browser tool
 */
export function generateBookingCommands(opts: QuickBookOptions): object[] {
  const studio = STUDIOS[opts.studio];
  const url = opts.studio === 'barrys' 
    ? studio.scheduleUrl(opts.location)
    : (studio.scheduleUrl as () => string)();
  
  const commands: object[] = [];
  
  // Step 1: Navigate
  commands.push({
    action: 'navigate',
    profile: 'openclaw',
    targetUrl: url
  });
  
  // Step 2: Brief wait + snapshot
  commands.push({
    action: 'act',
    profile: 'openclaw',
    request: { kind: 'wait', timeMs: 1500 }
  });
  
  commands.push({
    action: 'snapshot',
    profile: 'openclaw',
    frame: studio.iframe,
    interactive: true
  });
  
  // Note: After snapshot, caller needs to:
  // 1. Find "Reserve" link ref matching target time
  // 2. Click it
  // 3. Select spot
  // 4. Confirm
  
  return commands;
}

/**
 * Complete booking script as shell commands
 * Can be piped to openclaw CLI
 */
export function generateShellScript(opts: QuickBookOptions): string {
  const studio = STUDIOS[opts.studio];
  const url = opts.studio === 'barrys' 
    ? studio.scheduleUrl(opts.location)
    : (studio.scheduleUrl as () => string)();
  
  return `#!/bin/bash
# Quick Book: ${opts.studio} ${opts.location}
# Target: ${opts.targetTime || 'first available'} at spot ${opts.preferredSpot || 'any'}

# Step 1: Navigate
echo "Navigating to schedule..."
openclaw browser navigate --url "${url}"

# Step 2: Wait for load
sleep 2

# Step 3: Get schedule
echo "Getting available classes..."
openclaw browser snapshot --frame "${studio.iframe}" --interactive

# Step 4: Find and click Reserve
# (Manual: look for link "Reserve" refs, click one)
# openclaw browser act --frame "${studio.iframe}" --click "eXX"

# Step 5: Select spot
# openclaw browser act --frame "${studio.iframe}" --click "eYY"

# Step 6: Confirm
# openclaw browser act --frame "${studio.iframe}" --click 'link "Buy & Reserve Class"'

echo "Done! Check browser for result."
`;
}

// Example: Print commands for Barry's NoHo
if (require.main === module) {
  console.log('=== Barry\'s NoHo Quick Book Commands ===\n');
  const commands = generateBookingCommands({
    studio: 'barrys',
    location: 'noho',
    targetTime: '6:00 PM',
    preferredSpot: 'F-1'
  });
  console.log(JSON.stringify(commands, null, 2));
  
  console.log('\n\n=== Shell Script Version ===\n');
  console.log(generateShellScript({
    studio: 'barrys',
    location: 'noho',
    targetTime: '6:00 PM',
    preferredSpot: 'F-1'
  }));
}
