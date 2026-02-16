// ============================================================
// Studio Configurations (Mariana Tek)
// ============================================================

export interface StudioConfig {
  name: string;
  slug: string;
  platform: 'mariana-tek' | 'mindbody';
  scheduleUrl: string;
  loginUrl: string;
  iframe: string; // iframe selector, empty string for direct SPA
}

export const STUDIOS: Record<string, StudioConfig> = {
  barrys: {
    name: "Barry's Bootcamp",
    slug: 'barrys',
    platform: 'mariana-tek',
    scheduleUrl: 'https://www.barrys.com/schedule/{location}',
    loginUrl: 'https://barrysbootcamp.marianatek.com/auth/login/',
    iframe: 'iframe.visible',
  },
  aarmy: {
    name: 'Aarmy',
    slug: 'aarmy',
    platform: 'mariana-tek',
    scheduleUrl: 'https://mt.aarmy.com/index.html?_mt=%2Fschedule%2Fdaily',
    loginUrl: 'https://aarmy.marianatek.com/auth/login/',
    iframe: 'iframe',
  },
  slt: {
    name: 'SLT',
    slug: 'slt',
    platform: 'mariana-tek',
    scheduleUrl: 'https://www.sltnyc.com/book-a-class/',
    loginUrl: 'https://slt.marianatek.com/auth/login/',
    iframe: 'iframe',
  },
  rumble: {
    name: 'Rumble Boxing',
    slug: 'rumble',
    platform: 'mariana-tek',
    scheduleUrl: 'https://members.rumbleboxinggym.com/schedule/daily',
    loginUrl: 'https://members.rumbleboxinggym.com/auth/login',
    iframe: '',
  },
  cyclebar: {
    name: 'CycleBar',
    slug: 'cyclebar',
    platform: 'mariana-tek',
    scheduleUrl: 'https://members.cyclebar.com/schedule/daily',
    loginUrl: 'https://members.cyclebar.com/auth/login',
    iframe: '',
  },
  clubpilates: {
    name: 'Club Pilates',
    slug: 'clubpilates',
    platform: 'mariana-tek',
    scheduleUrl: 'https://members.clubpilates.com/schedule/daily',
    loginUrl: 'https://members.clubpilates.com/auth/login',
    iframe: '',
  },
  yogasix: {
    name: 'YogaSix',
    slug: 'yogasix',
    platform: 'mariana-tek',
    scheduleUrl: 'https://members.yogasix.com/schedule/daily',
    loginUrl: 'https://members.yogasix.com/auth/login',
    iframe: '',
  },
  stretchlab: {
    name: 'StretchLab',
    slug: 'stretchlab',
    platform: 'mariana-tek',
    scheduleUrl: 'https://members.stretchlab.com/schedule/daily',
    loginUrl: 'https://members.stretchlab.com/auth/login',
    iframe: '',
  },
  purebarre: {
    name: 'Pure Barre',
    slug: 'purebarre',
    platform: 'mariana-tek',
    scheduleUrl: 'https://members.purebarre.com/schedule/daily',
    loginUrl: 'https://members.purebarre.com/auth/login',
    iframe: '',
  },
};

// ============================================================
// Location Data
// ============================================================

export interface LocationInfo {
  id: string;
  name: string;
  address: string;
}

export const STUDIO_LOCATIONS: Record<string, LocationInfo[]> = {
  barrys: [
    { id: 'noho', name: 'NoHo', address: '636 Broadway' },
    { id: 'chelsea', name: 'Chelsea', address: '305 W 27th St' },
    { id: 'tribeca', name: 'Tribeca', address: '141 Watts St' },
    { id: 'brooklyn-heights', name: 'Brooklyn Heights', address: '194 Joralemon St' },
    { id: 'east-64th', name: 'East 64th', address: '213 E 64th St' },
    { id: 'east-86th', name: 'East 86th', address: '1526 2nd Ave' },
    { id: 'long-island-city', name: 'Long Island City', address: '29-11 Queens Plaza N' },
    { id: 'park-ave-south', name: 'Park Ave South', address: '393 Park Ave S' },
  ],
  aarmy: [
    { id: 'chelsea', name: 'Chelsea (A23)', address: '140 West 23rd St' },
    { id: 'noho', name: 'NoHo', address: '636 Broadway' },
  ],
  slt: [
    { id: 'ues', name: 'Upper East Side', address: '' },
    { id: 'uws', name: 'Upper West Side', address: '' },
    { id: 'nomad', name: 'NoMad', address: '' },
    { id: 'soho', name: 'SoHo', address: '' },
    { id: 'fidi', name: 'FiDi', address: '' },
    { id: 'brooklyn', name: 'Brooklyn', address: '' },
    { id: 'hoboken', name: 'Hoboken', address: '' },
  ],
};

// Mariana Tek internal location IDs (used for iframe-based studios)
export const LOCATION_IDS: Record<string, Record<string, string>> = {
  barrys: {
    noho: 'noho',
    chelsea: 'chelsea',
    tribeca: 'tribeca',
    'brooklyn-heights': 'brooklyn-heights',
    'east-64th': 'east-64th',
    'east-86th': 'east-86th',
    lic: 'long-island-city',
    'park-ave-south': 'park-ave-south',
  },
  aarmy: {
    chelsea: 'Chelsea (A23)',
    noho: 'NoHo',
  },
  slt: {
    ues: 'Upper East Side',
    uws: 'Upper West Side',
    nomad: 'NoMad',
    soho: 'SoHo',
    fidi: 'FiDi',
    brooklyn: 'Brooklyn',
    hoboken: 'Hoboken',
  },
};

// ============================================================
// Class Time Slots
// ============================================================

export const STUDIO_TIMES: Record<string, string[]> = {
  barrys: ['5:00 AM', '6:00 AM', '7:15 AM', '8:30 AM', '9:45 AM', '11:00 AM', '12:15 PM', '4:00 PM', '5:15 PM', '6:30 PM', '7:45 PM'],
  aarmy: ['6:00 AM', '7:00 AM', '8:15 AM', '12:00 PM', '5:00 PM', '6:00 PM', '7:00 PM'],
};
