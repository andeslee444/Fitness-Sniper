/**
 * Class Sniper - Auto-booking for fitness classes
 * 
 * Monitors schedules and books classes automatically when they become available.
 * Supports Barry's, Aarmy, and other Mariana Tek-powered studios.
 * 
 * Created: 2026-02-13
 */

import * as fs from 'fs';
import * as path from 'path';

interface ClassTarget {
  studio: 'barrys' | 'aarmy';
  location: string;
  dayOfWeek: number;  // 0 = Sunday, 1 = Monday, etc.
  time: string;       // "6:00 AM", "7:00 PM", etc.
  classType?: string; // Optional: "Full Body", "Glutes & Arms", etc.
  instructor?: string; // Optional: Preferred instructor
}

interface Preferences {
  studios: {
    barrys?: {
      email: string;
      password: string;
      preferences?: {
        locations: string[];
        classTypes: string[];
        preferredTimes: string[];
        preferredInstructors: string[];
      };
    };
    aarmy?: {
      email: string;
      password: string;
      preferences?: {
        locations: string[];
        classTypes: string[];
        preferredTimes: string[];
        preferredInstructors: string[];
      };
    };
  };
  notifications: {
    method: 'imessage' | 'sms' | 'email';
    phone?: string;
    email?: string;
  };
  targets?: ClassTarget[];
}

/**
 * Load preferences from config file
 */
function loadPreferences(): Preferences {
  const configPath = path.join(__dirname, '../config/preferences.json');
  if (!fs.existsSync(configPath)) {
    throw new Error(`Config file not found: ${configPath}`);
  }
  return JSON.parse(fs.readFileSync(configPath, 'utf-8'));
}

/**
 * Calculate next occurrence of a day/time
 */
function getNextOccurrence(dayOfWeek: number, time: string): Date {
  const now = new Date();
  const [timePart, ampm] = time.split(' ');
  let [hours, minutes] = timePart.split(':').map(Number);
  
  if (ampm === 'PM' && hours !== 12) hours += 12;
  if (ampm === 'AM' && hours === 12) hours = 0;
  
  const target = new Date(now);
  target.setHours(hours, minutes || 0, 0, 0);
  
  // Find next occurrence of this day
  const daysUntil = (dayOfWeek - now.getDay() + 7) % 7;
  target.setDate(target.getDate() + daysUntil);
  
  // If it's today but time has passed, go to next week
  if (daysUntil === 0 && target <= now) {
    target.setDate(target.getDate() + 7);
  }
  
  return target;
}

/**
 * Check when booking window opens for a class
 * Barry's: Opens at midnight, 7 days before
 * Aarmy: Similar timing
 */
function getBookingWindowOpen(classDate: Date, studio: 'barrys' | 'aarmy'): Date {
  const bookingOpen = new Date(classDate);
  bookingOpen.setDate(bookingOpen.getDate() - 7);
  bookingOpen.setHours(0, 0, 0, 0);
  return bookingOpen;
}

/**
 * Main sniper loop
 */
async function runSniper() {
  console.log('🎯 Class Sniper Starting...');
  
  const prefs = loadPreferences();
  console.log('Loaded preferences');
  
  // Default targets if not specified
  const targets: ClassTarget[] = prefs.targets || [
    // Barry's morning classes
    { studio: 'barrys', location: 'noho', dayOfWeek: 1, time: '6:00 AM' },
    { studio: 'barrys', location: 'noho', dayOfWeek: 3, time: '6:00 AM' },
    { studio: 'barrys', location: 'noho', dayOfWeek: 5, time: '6:00 AM' },
    
    // Aarmy evening classes
    { studio: 'aarmy', location: 'chelsea', dayOfWeek: 2, time: '6:00 PM' },
    { studio: 'aarmy', location: 'chelsea', dayOfWeek: 4, time: '6:00 PM' },
  ];
  
  console.log(`Monitoring ${targets.length} class targets`);
  
  for (const target of targets) {
    const nextClass = getNextOccurrence(target.dayOfWeek, target.time);
    const bookingOpens = getBookingWindowOpen(nextClass, target.studio);
    
    const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    console.log(`- ${target.studio} ${target.location}: ${dayNames[target.dayOfWeek]} ${target.time}`);
    console.log(`  Next class: ${nextClass.toLocaleString()}`);
    console.log(`  Booking opens: ${bookingOpens.toLocaleString()}`);
  }
  
  // TODO: Implement actual monitoring loop
  // For now, just print the schedule
  console.log('\n✅ Sniper configured. Ready to book!');
}

// Run if called directly
if (require.main === module) {
  runSniper().catch(console.error);
}

export { runSniper, loadPreferences, getNextOccurrence, getBookingWindowOpen };
