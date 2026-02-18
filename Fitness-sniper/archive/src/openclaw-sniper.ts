/**
 * OpenClaw Sniper - Browser-integrated auto-booking
 * 
 * This is designed to be run by OpenClaw's cron system.
 * It outputs browser commands that OpenClaw executes.
 * 
 * Usage: Add to OpenClaw cron with agentTurn payload
 * 
 * Created: 2026-02-13
 */

import * as fs from 'fs';
import * as path from 'path';

// ============================================================
// CONFIGURATION
// ============================================================

const CONFIG = {
  barrys: {
    email: 'andes.leelee@gmail.com',
    password: 'Cheeseslice8!',
    scheduleUrl: (loc: string) => `https://www.barrys.com/schedule/${loc}`,
    iframe: 'iframe.visible'
  },
  aarmy: {
    email: 'andes.leelee@gmail.com', 
    password: 'Ilovebex823',
    scheduleUrl: () => 'https://mt.aarmy.com/index.html?_mt=%2Fschedule%2Fdaily',
    iframe: 'iframe'
  }
};

// Target classes to snipe
const TARGETS = [
  // Barry's MWF 6am
  { studio: 'barrys', location: 'noho', day: 1, time: '6:00 AM', spots: ['F-1', 'F-3', 'T-1'] },
  { studio: 'barrys', location: 'noho', day: 3, time: '6:00 AM', spots: ['F-1', 'F-3', 'T-1'] },
  { studio: 'barrys', location: 'noho', day: 5, time: '6:00 AM', spots: ['F-1', 'F-3', 'T-1'] },
];

// ============================================================
// HELPERS
// ============================================================

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

function isInBookingWindow(classDate: Date): boolean {
  const now = new Date();
  const windowEnd = new Date(now);
  windowEnd.setDate(windowEnd.getDate() + 7); // 7 day window
  return classDate >= now && classDate <= windowEnd;
}

// ============================================================
// MAIN SNIPER PROMPT
// ============================================================

/**
 * Generate prompt for OpenClaw to execute sniper
 * This is what gets sent to the agent via cron
 */
export function generateSniperPrompt(): string {
  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const now = new Date();
  
  let prompt = `🎯 CLASS SNIPER CHECK - ${now.toLocaleString()}

Check these targets and book if available:

`;

  let hasTargetsToCheck = false;
  
  for (const target of TARGETS) {
    const nextClass = getNextClassDate(target.day, target.time);
    const inWindow = isInBookingWindow(nextClass);
    
    if (!inWindow) continue;
    hasTargetsToCheck = true;
    
    const config = CONFIG[target.studio as keyof typeof CONFIG];
    const url = target.studio === 'barrys' 
      ? (config.scheduleUrl as (loc: string) => string)(target.location)
      : (config.scheduleUrl as () => string)();
    
    prompt += `## ${target.studio.toUpperCase()} ${target.location} - ${dayNames[target.day]} ${target.time}
- URL: ${url}
- Iframe: ${config.iframe}
- Preferred spots: ${target.spots.join(', ')}
- Next class: ${nextClass.toLocaleDateString()}

`;
  }
  
  if (!hasTargetsToCheck) {
    return `🎯 CLASS SNIPER CHECK - ${now.toLocaleString()}

No targets in booking window. All classes are either:
- Already past
- More than 7 days away

Next check will run in 5 minutes.`;
  }
  
  prompt += `## BOOKING FLOW

For each target above:
1. Navigate to the URL
2. Wait 1.5s, then snapshot the iframe with interactive=true
3. Look for "link \\"Reserve\\"" refs near the target time
4. If found and NOT waitlist:
   a. Click the Reserve link
   b. Wait 1s, snapshot again to see spot selection
   c. Find preferred spot (or first available)
   d. Click the spot
   e. Wait 0.5s, click "link \\"Buy & Reserve Class\\""
   f. Report success!
5. If waitlist only, skip (don't join waitlist)
6. If no Reserve found, report "not available"

IMPORTANT: Only book ONE class per run. If you book successfully, stop and report.

Report format:
✅ BOOKED: [studio] [location] [day] [time] - Spot [X]
❌ NOT AVAILABLE: [studio] [location] [day] [time] - [reason]
⏭️ SKIPPED: [studio] [location] [day] [time] - [reason]
`;

  return prompt;
}

// ============================================================
// CLI OUTPUT
// ============================================================

if (require.main === module) {
  console.log(generateSniperPrompt());
}

export { TARGETS, CONFIG };
