// ============================================================
// Studio Configurations (Mariana Tek)
// ============================================================

export interface StudioConfig {
  name: string;
  slug: string;
  platform: 'mariana-tek' | 'xponential' | 'mindbody';
  tenant: string; // MT subdomain (e.g. 'barrysbootcamp' → barrysbootcamp.marianatek.com)
  scheduleUrl: string;
  loginUrl: string;
  iframe: string; // iframe selector, empty string for direct SPA
  membersDomain?: string; // Xponential member portal (e.g. 'members.cyclebar.com')
  bookingWindowDays: number; // How far ahead bookings open (scheduler uses this)
}

export const STUDIOS: Record<string, StudioConfig> = {
  barrys: {
    name: "Barry's Bootcamp",
    slug: 'barrys',
    platform: 'mariana-tek',
    tenant: 'barrysbootcamp',
    scheduleUrl: 'https://www.barrys.com/schedule/{location}',
    loginUrl: 'https://barrysbootcamp.marianatek.com/auth/login/',
    iframe: 'iframe.visible',
    bookingWindowDays: 7,
  },
  aarmy: {
    name: 'Aarmy',
    slug: 'aarmy',
    platform: 'mariana-tek',
    tenant: 'aarmy',
    scheduleUrl: 'https://mt.aarmy.com/index.html?_mt=%2Fschedule%2Fdaily',
    loginUrl: 'https://aarmy.marianatek.com/auth/login/',
    iframe: 'iframe',
    bookingWindowDays: 7,
  },
  slt: {
    name: 'SLT',
    slug: 'slt',
    platform: 'mariana-tek',
    tenant: 'slt',
    scheduleUrl: 'https://www.sltnyc.com/book-a-class/',
    loginUrl: 'https://slt.marianatek.com/auth/login/',
    iframe: 'iframe',
    bookingWindowDays: 7,
  },
  rumble: {
    name: 'Rumble Boxing',
    slug: 'rumble',
    platform: 'xponential',
    tenant: 'rumbleboxinggym',
    membersDomain: 'https://members.rumbleboxinggym.com',
    scheduleUrl: 'https://members.rumbleboxinggym.com/schedule/daily',
    loginUrl: 'https://members.rumbleboxinggym.com/auth/login',
    iframe: '',
    bookingWindowDays: 3,
  },
  cyclebar: {
    name: 'CycleBar',
    slug: 'cyclebar',
    platform: 'xponential',
    tenant: 'cyclebar',
    membersDomain: 'https://members.cyclebar.com',
    scheduleUrl: 'https://members.cyclebar.com/schedule/daily',
    loginUrl: 'https://members.cyclebar.com/auth/login',
    iframe: '',
    bookingWindowDays: 3,
  },
  clubpilates: {
    name: 'Club Pilates',
    slug: 'clubpilates',
    platform: 'xponential',
    tenant: 'clubpilates',
    membersDomain: 'https://members.clubpilates.com',
    scheduleUrl: 'https://members.clubpilates.com/schedule/daily',
    loginUrl: 'https://members.clubpilates.com/auth/login',
    iframe: '',
    bookingWindowDays: 3,
  },
  yogasix: {
    name: 'YogaSix',
    slug: 'yogasix',
    platform: 'xponential',
    tenant: 'yogasix',
    membersDomain: 'https://members.yogasix.com',
    scheduleUrl: 'https://members.yogasix.com/schedule/daily',
    loginUrl: 'https://members.yogasix.com/auth/login',
    iframe: '',
    bookingWindowDays: 3,
  },
  stretchlab: {
    name: 'StretchLab',
    slug: 'stretchlab',
    platform: 'xponential',
    tenant: 'stretchlab',
    membersDomain: 'https://members.stretchlab.com',
    scheduleUrl: 'https://members.stretchlab.com/schedule/daily',
    loginUrl: 'https://members.stretchlab.com/auth/login',
    iframe: '',
    bookingWindowDays: 3,
  },
  purebarre: {
    name: 'Pure Barre',
    slug: 'purebarre',
    platform: 'xponential',
    tenant: 'purebarre',
    membersDomain: 'https://members.purebarre.com',
    scheduleUrl: 'https://members.purebarre.com/schedule/daily',
    loginUrl: 'https://members.purebarre.com/auth/login',
    iframe: '',
    bookingWindowDays: 3,
  },
  practiceroom: {
    name: 'Practice Room',
    slug: 'practiceroom',
    platform: 'mariana-tek',
    tenant: 'practiceroomnyc',
    scheduleUrl: 'https://practiceroomnyc.com/classes/',
    loginUrl: 'https://practiceroomnyc.marianatek.com/auth/login/',
    iframe: 'iframe',
    bookingWindowDays: 7,
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
  practiceroom: [
    { id: 'noho', name: 'NoHo', address: '650 Broadway, 4th Fl' },
    { id: 'williamsburg', name: 'Williamsburg', address: '173 N 3rd St' },
  ],
  // Xponential brands — location IDs are API slugs (e.g. 'rumble-noho')
  rumble: [
    { id: 'rumble-noho', name: 'NoHo', address: '700 Broadway' },
    { id: 'rumble-flatiron-chelsea', name: 'Flatiron/Chelsea', address: '146 W 23rd St' },
    { id: 'rumble-upper-east-side', name: 'Upper East Side Boxing', address: '1495 3rd Ave' },
    { id: 'rumble-upper-east-side-ny', name: 'Upper East Side Training', address: '1495 3rd Ave' },
    { id: 'rumble-jersey-city', name: 'Jersey City', address: '134 Bay St' },
    { id: 'rumble-hoboken', name: 'Hoboken', address: '1202 Shipyard Lane' },
  ],
  cyclebar: [
    { id: 'cyclebar-noho', name: 'NoHo', address: '51 Astor Place' },
    { id: 'cyclebar-flatiron', name: 'Flatiron', address: '39 W 21st St' },
    { id: 'cyclebar-nomad', name: 'NoMad', address: '420 Park Ave S' },
    { id: 'cyclebar-ues-67th', name: 'UES 67th', address: '201 E 67th St' },
    { id: 'cyclebar-jersey-city', name: 'Jersey City', address: '65 Bay St' },
    { id: 'cyclebar-hoboken', name: 'Hoboken', address: '720 Monroe St' },
  ],
  clubpilates: [
    { id: 'clubpilates-tribeca-ny', name: 'Tribeca', address: '47 Murray St' },
    { id: 'clubpilates-west-village', name: 'West Village', address: '389 6th Ave' },
    { id: 'clubpilates-gramercy-ny', name: 'Gramercy', address: '381 Second Ave' },
    { id: 'clubpilates-west-chelsea', name: 'West Chelsea', address: '601 W 26th St' },
    { id: 'clubpilates-penn-station', name: 'Penn Station', address: '501 7th Ave' },
    { id: 'clubpilates-midtown-east', name: 'Midtown East', address: '850 2nd Ave' },
    { id: 'clubpilates-west-57th-ny', name: 'West 57th', address: '601 W 57th St' },
    { id: 'clubpilates-cobble-hill-ny', name: 'Cobble Hill', address: '181 Pacific St, Brooklyn' },
    { id: 'clubpilates-park-slope-ny', name: 'Park Slope', address: '336 Flatbush Ave, Brooklyn' },
    { id: 'clubpilates-north-3rd-ny', name: 'North 3rd', address: '56 N 3rd St, Brooklyn' },
  ],
  yogasix: [
    // No NYC locations — add when available
  ],
  stretchlab: [
    { id: 'stretchlab-tribeca', name: 'Tribeca', address: '157 Chambers St' },
    { id: 'stretchlab-union-square-nyc', name: 'Union Square', address: '791 Broadway' },
    { id: 'stretchlab-midtown-east', name: 'Midtown East', address: '1100 2nd Ave' },
    { id: 'stretchlab-columbus-circle', name: 'Columbus Circle', address: '332 W 57th St' },
    { id: 'stretchlab-cobble-hill', name: 'Cobble Hill', address: '321 Court St, Brooklyn' },
    { id: 'stretchlab-upper-east-side', name: 'Upper East Side', address: '1660 First Ave' },
  ],
  purebarre: [
    { id: 'purebarre-new-york-city-tribeca-ny', name: 'Tribeca', address: '110 Reade St' },
    { id: 'purebarre-new-york-union-square-ny', name: 'Union Square', address: '78 5th Ave' },
    { id: 'purebarre-flatiron-ny', name: 'Flatiron', address: '39 W 21st St' },
    { id: 'purebarre-new-york-financial-district-ny', name: 'Financial District', address: '80 Pine St' },
    { id: 'purebarre-brooklyn-cobble-hill-ny', name: 'Cobble Hill', address: '266 Court St, Brooklyn' },
    { id: 'purebarre-brooklyn-williamsburg-ny', name: 'Williamsburg', address: '204 Wythe Ave, Brooklyn' },
    { id: 'purebarre-brooklyn-park-slope-ny', name: 'Park Slope', address: '178 5th Ave, Brooklyn' },
    { id: 'purebarre-new-york-upper-east-side-second-avenue-ny', name: 'UES Second Ave', address: '1237 2nd Ave' },
    { id: 'purebarre-new-york-upper-west-side-columbus-avenue-ny', name: 'UWS Columbus Ave', address: '412 Columbus Ave' },
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
  practiceroom: {
    noho: 'NoHo',
    williamsburg: 'Williamsburg',
  },
};

