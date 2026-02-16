// Studio data for the frontend (mirrors shared/src/studios.ts)

export interface StudioInfo {
  name: string;
  slug: string;
}

export interface LocationInfo {
  id: string;
  name: string;
  address: string;
}

export const STUDIOS: Record<string, StudioInfo> = {
  barrys: { name: "Barry's Bootcamp", slug: 'barrys' },
  aarmy: { name: 'Aarmy', slug: 'aarmy' },
  slt: { name: 'SLT', slug: 'slt' },
  rumble: { name: 'Rumble Boxing', slug: 'rumble' },
  cyclebar: { name: 'CycleBar', slug: 'cyclebar' },
  clubpilates: { name: 'Club Pilates', slug: 'clubpilates' },
  yogasix: { name: 'YogaSix', slug: 'yogasix' },
  stretchlab: { name: 'StretchLab', slug: 'stretchlab' },
  purebarre: { name: 'Pure Barre', slug: 'purebarre' },
};

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

export const STUDIO_TIMES: Record<string, string[]> = {
  barrys: ['5:00 AM', '6:00 AM', '7:15 AM', '8:30 AM', '9:45 AM', '11:00 AM', '12:15 PM', '4:00 PM', '5:15 PM', '6:30 PM', '7:45 PM'],
  aarmy: ['6:00 AM', '7:00 AM', '8:15 AM', '12:00 PM', '5:00 PM', '6:00 PM', '7:00 PM'],
};

export const DAY_NAMES = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
export const DAY_ABBR = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

export const SEAT_PREFERENCES = [
  { value: 'front', label: 'Front Row' },
  { value: 'middle', label: 'Middle' },
  { value: 'back', label: 'Back / Treads' },
  { value: 'any', label: 'Any Available' },
] as const;

export const SPOT_PREFERENCES: Record<string, string[]> = {
  front: ['F-1', 'F-3', 'F-5', 'F-7', 'F-2', 'F-4', 'F-6', 'F-8'],
  middle: ['F-9', 'F-10', 'F-11', 'F-12', 'F-13', 'F-14', 'F-15', 'F-16'],
  back: ['T-1', 'T-3', 'T-5', 'T-7', 'T-2', 'T-4', 'T-6', 'T-8', 'T-9', 'T-10'],
  any: [],
};
