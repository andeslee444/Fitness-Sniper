// Re-export studio data from shared package (single source of truth)
export { STUDIOS, STUDIO_LOCATIONS, STUDIO_TIMES, LOCATION_IDS, SPOT_PREFERENCES } from '@fitness-sniper/shared';
export type { StudioConfig, LocationInfo } from '@fitness-sniper/shared';

// Web-only display constants

export const DAY_NAMES = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
export const DAY_ABBR = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

export const SEAT_PREFERENCES = [
  { value: 'front', label: 'Front Row' },
  { value: 'middle', label: 'Middle' },
  { value: 'back', label: 'Back / Treads' },
  { value: 'any', label: 'Any Available' },
] as const;
