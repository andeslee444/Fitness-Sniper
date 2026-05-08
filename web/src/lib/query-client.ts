import { QueryClient, QueryCache } from '@tanstack/react-query';

export function makeQueryClient() {
  return new QueryClient({
    queryCache: new QueryCache({
      onError: (error) => {
        if (error instanceof Error && error.message.startsWith('HTTP 401')) {
          // Fire-and-forget refresh attempt; ignore failures — next navigation redirects to login.
          fetch('/api/auth/refresh', { method: 'POST' }).catch(() => {});
        }
      },
    }),
    defaultOptions: {
      queries: {
        staleTime: 30 * 1000, // 30 seconds global default
      },
    },
  });
}
