/**
 * Base interface for fitness studio adapters
 */

export interface ClassInfo {
  id: string;
  studio: string;
  location: string;
  date: string; // YYYY-MM-DD
  time: string; // HH:MM
  instructor: string;
  className: string;
  spotsAvailable: number;
  isBookable: boolean;
  isWaitlist: boolean;
}

export interface BookingResult {
  success: boolean;
  classInfo: ClassInfo;
  confirmationId?: string;
  error?: string;
}

export interface ClassPreferences {
  locations: string[];
  times: {
    weekdays?: string[]; // ["06:00-08:00", "18:00-20:00"]
    weekends?: string[]; // ["09:00-11:00"]
  };
  instructors?: string[];
  classTypes?: string[]; // ["Full Body", "Arms & Abs"]
  daysInAdvance: number;
}

export interface StudioCredentials {
  email: string;
  password: string;
}

export interface StudioAdapter {
  name: string;
  
  /**
   * Login to the studio's booking system
   */
  login(credentials: StudioCredentials): Promise<boolean>;
  
  /**
   * Search for available classes matching preferences
   */
  searchClasses(preferences: ClassPreferences): Promise<ClassInfo[]>;
  
  /**
   * Book a specific class
   */
  bookClass(classInfo: ClassInfo): Promise<BookingResult>;
  
  /**
   * Check if currently logged in
   */
  isLoggedIn(): Promise<boolean>;
  
  /**
   * Close browser/cleanup
   */
  close(): Promise<void>;
}
