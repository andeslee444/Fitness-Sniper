'use client';

import { useState } from 'react';
import { SchedulePanel } from '@/components/schedule/schedule-panel';
import { SnipeConfigSheet } from '@/components/schedule/snipe-config-sheet';
import type { ScheduleClass } from '@/components/schedule/schedule-panel';

export function SchedulePageClient() {
  const [sheetOpen, setSheetOpen] = useState(false);
  const [selectedClass, setSelectedClass] = useState<ScheduleClass | null>(null);
  const [snipeStudio, setSnipeStudio] = useState('');
  const [snipeLocation, setSnipeLocation] = useState('');

  function handleSnipeClick(cls: ScheduleClass, studioSlug: string, locationId: string) {
    setSelectedClass(cls);
    setSnipeStudio(studioSlug);
    setSnipeLocation(locationId);
    setSheetOpen(true);
  }

  const sheetKey = selectedClass
    ? `${snipeStudio}:${snipeLocation}:${selectedClass.class_date}:${selectedClass.class_time}`
    : 'empty';

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold sm:text-3xl">Schedule Explorer</h1>
        <p className="mt-1 text-sm text-zinc-400">Browse class schedules and create snipe targets</p>
      </div>
      <SchedulePanel onSnipeClick={handleSnipeClick} />
      <SnipeConfigSheet
        key={sheetKey}
        open={sheetOpen}
        onOpenChange={setSheetOpen}
        selectedClass={selectedClass}
        studioSlug={snipeStudio}
        locationId={snipeLocation}
      />
    </div>
  );
}
