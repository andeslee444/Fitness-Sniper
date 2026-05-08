// Re-export browser-safe studio data from shared package (single source of truth).
// Do not import the shared package barrel here: it also exports server API clients.
export { STUDIOS, STUDIO_LOCATIONS, LOCATION_IDS } from '@fitness-sniper/shared/src/studios';
export { SPOT_PREFERENCES } from '@fitness-sniper/shared/src/types';
export type { StudioConfig, LocationInfo } from '@fitness-sniper/shared/src/studios';

// Web-only display constants

export const DAY_NAMES = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
export const DAY_ABBR = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

export const SEAT_PREFERENCES = [
  { value: 'front', label: 'Front Row' },
  { value: 'middle', label: 'Middle' },
  { value: 'back', label: 'Back / Treads' },
  { value: 'any', label: 'Any Available' },
] as const;
