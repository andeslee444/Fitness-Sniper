/**
 * Fast Booking Flow - Minimal round trips
 * 
 * Optimized for speed: batch operations, skip unnecessary waits,
 * parallel where possible.
 * 
 * Target: Login → Schedule → Reserve → Seat → Confirm in ~10 seconds
 */

// ============================================================
// OPENCLAW BROWSER AUTOMATION VERSION
// Use with: openclaw browser commands
// ============================================================

export interface BookingRequest {
  studio: 'barrys' | 'aarmy';
  location: string;
  classTime: string;  // e.g., "6:00 PM"
  credentials: {
    email: string;
    password: string;
  };
  preferredSpot?: string;  // e.g., "12" or "front-center"
}

export const STUDIO_CONFIG = {
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

/**
 * OpenClaw Browser Commands for Fast Booking
 * 
 * These are the exact commands to run via browser tool.
 * Each step is optimized for speed.
 */
export const BOOKING_COMMANDS = {
  /**
   * Step 1: Navigate to schedule (1 call)
   */
  navigateToSchedule: (studio: 'barrys' | 'aarmy', location: string) => ({
    action: 'navigate',
    profile: 'openclaw',
    targetUrl: studio === 'barrys' 
      ? `https://www.barrys.com/schedule/${location}`
      : 'https://mt.aarmy.com/index.html?_mt=%2Fschedule%2Fdaily'
  }),

  /**
   * Step 2: Click Reserve on target class (1 call)
   * Uses text matching for speed
   */
  clickReserve: (classTime: string) => ({
    action: 'act',
    profile: 'openclaw',
    frame: 'iframe.visible',  // Barry's
    request: {
      kind: 'click',
      ref: `link "Reserve"`,  // Will need to find near time
    }
  }),

  /**
   * Step 3: Fill login form (1 call with batch)
   */
  fillLogin: (email: string, password: string) => ({
    action: 'act',
    profile: 'openclaw',
    frame: 'iframe.visible',
    request: {
      kind: 'fill',
      fields: [
        { ref: 'textbox "Email"', text: email },
        { ref: 'textbox "Password"', text: password }
      ]
    }
  }),

  /**
   * Step 4: Submit login (1 call)
   */
  submitLogin: () => ({
    action: 'act',
    profile: 'openclaw', 
    frame: 'iframe.visible',
    request: {
      kind: 'click',
      ref: 'button "Log in"',
      submit: true
    }
  }),

  /**
   * Step 5: Select spot (1 call)
   */
  selectSpot: (spotNumber?: string) => ({
    action: 'act',
    profile: 'openclaw',
    frame: 'iframe.visible',
    request: {
      kind: 'click',
      ref: spotNumber ? `button "${spotNumber}"` : 'button >> nth=0'  // First available
    }
  }),

  /**
   * Step 6: Confirm booking (1 call)
   */
  confirmBooking: () => ({
    action: 'act',
    profile: 'openclaw',
    frame: 'iframe.visible',
    request: {
      kind: 'click',
      ref: 'button "Confirm"'
    }
  })
};

/**
 * Complete booking script - copy/paste ready
 * 
 * Usage: Run each command in sequence via OpenClaw browser tool
 */
export function generateBookingScript(req: BookingRequest): string {
  const config = STUDIO_CONFIG[req.studio];
  const scheduleUrl = req.studio === 'barrys' 
    ? config.scheduleUrl(req.location)
    : (config.scheduleUrl as () => string)();

  return `
# Fast Booking: ${req.studio.toUpperCase()} - ${req.location} @ ${req.classTime}
# Target: 6 browser calls, ~10-15 seconds total

## Step 1: Navigate to schedule
browser action=navigate profile=openclaw targetUrl="${scheduleUrl}"

## Step 2: Wait for schedule to load (brief)
browser action=act profile=openclaw request='{"kind":"wait","timeMs":1500}'

## Step 3: Find and click Reserve for ${req.classTime}
# First, snapshot to find the correct reserve link
browser action=snapshot profile=openclaw frame="${config.iframe}" interactive=true

## Step 4: Click the Reserve link (use ref from snapshot)
# Look for: link "Reserve" near "${req.classTime}"
browser action=act profile=openclaw frame="${config.iframe}" request='{"kind":"click","ref":"RESERVE_REF_HERE"}'

## Step 5: Fill login (if modal appears)
browser action=act profile=openclaw frame="${config.iframe}" request='{"kind":"fill","fields":[{"ref":"textbox \\"Email\\"","text":"${req.credentials.email}"},{"ref":"textbox \\"Password\\"","text":"${req.credentials.password}"}]}'

## Step 6: Submit login
browser action=act profile=openclaw frame="${config.iframe}" request='{"kind":"click","ref":"button \\"Log in\\""}'

## Step 7: Select spot (after login redirects to spot selection)
browser action=act profile=openclaw frame="${config.iframe}" request='{"kind":"wait","timeMs":2000}'
browser action=snapshot profile=openclaw frame="${config.iframe}" interactive=true
# Click available spot
browser action=act profile=openclaw frame="${config.iframe}" request='{"kind":"click","ref":"SPOT_REF_HERE"}'

## Step 8: Confirm booking
browser action=act profile=openclaw frame="${config.iframe}" request='{"kind":"click","ref":"button \\"Confirm\\""}'
`;
}

// Quick test function
export function printBarrysBookingScript() {
  const script = generateBookingScript({
    studio: 'barrys',
    location: 'noho',
    classTime: '6:00 PM',
    credentials: {
      email: 'andes.leelee@gmail.com',
      password: 'Cheeseslice8!'
    }
  });
  console.log(script);
}
