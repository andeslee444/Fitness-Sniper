'use client';

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { TargetsList } from '@/components/targets-list';
import type { SnipeTarget } from '@/lib/types';

export function TargetsTabs({
  recurring,
  oneTime,
}: {
  recurring: SnipeTarget[];
  oneTime: SnipeTarget[];
}) {
  return (
    <Tabs defaultValue="recurring">
      <TabsList>
        <TabsTrigger value="recurring">Recurring ({recurring.length})</TabsTrigger>
        <TabsTrigger value="one_time">One-Time ({oneTime.length})</TabsTrigger>
      </TabsList>
      <TabsContent value="recurring">
        <TargetsList targets={recurring} />
      </TabsContent>
      <TabsContent value="one_time">
        <TargetsList targets={oneTime} />
      </TabsContent>
    </Tabs>
  );
}
