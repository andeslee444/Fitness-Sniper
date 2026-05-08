import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { QUERY_KEYS } from '@/lib/query-keys';

export interface SnipePayload {
  target_type: 'recurring' | 'one_time';
  studio_slug: string;
  location_id: string;
  time: string | null;
  class_type: string | null;
  seat_preference: string;
  preferred_spots: string[];
  target_date?: string;
  day_of_week?: number;
}

export function useSnipeMutation(onSuccess?: () => void) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: SnipePayload) => {
      const res = await fetch('/api/targets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Failed to create snipe target');
      }
      return data;
    },
    onSuccess: () => {
      // Invalidate ALL calendar queries (partial key match covers all weeks)
      // This is important for recurring targets that affect multiple weeks
      queryClient.invalidateQueries({ queryKey: ['calendar'] });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.targets });
      toast.success('Snipe target created');
      onSuccess?.();
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Failed to create snipe target');
    },
  });
}
