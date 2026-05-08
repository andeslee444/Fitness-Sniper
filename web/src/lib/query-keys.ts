export const QUERY_KEYS = {
  dashboardStats: ['dashboard', 'stats'] as const,
  workerStatus: ['worker', 'status'] as const,
  jobs: ['jobs'] as const,
  calendarWeek: (weekStart: string) => ['calendar', weekStart] as const,
  targets: ['targets'] as const,
  history: (page: number) => ['history', page] as const,
  schedules: (studioSlug: string, locationId: string) =>
    ['schedules', studioSlug, locationId] as const,
} as const;
