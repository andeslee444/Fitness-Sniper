import { FeedHeadline } from "@/components/feed-headline";
import { FeedCardItemShell } from "@/components/feed-card-item-shell";
import type { FeedCard } from "@/lib/data";

/**
 * <FeedCardItem> — one /feed/ card, SERVER tree (feed/page.tsx). Moved out of
 * feed/page.tsx in Task 6 (#73) so the client-side section-expand path had a
 * stable import target; since ROADMAP #81 it is a thin wrapper: the markup is
 * <FeedCardItemShell> (feed-card-item-shell.tsx), shared with the client twin
 * (feed-card-item-client.tsx), and this component only supplies the headline.
 *
 * SERVER component — do not import this from a "use client" module. Its
 * headline is <FeedHeadline> (feed-headline.tsx → feedHeadlineSegments →
 * src/lib/data.ts, which is `import "server-only"`); that import breaks a
 * client bundle build, and vitest.client-graph.config.ts asserts it does.
 * The client expand path renders <FeedCardItemClient> instead.
 */
export function FeedCardItem({
  card,
  companySlug,
  hasProgramPage,
}: {
  card: FeedCard;
  /** See FeedCardItemShellProps.companySlug. */
  companySlug: string | null;
  /** See FeedCardItemShellProps.hasProgramPage. */
  hasProgramPage: boolean;
}) {
  return (
    <FeedCardItemShell
      card={card}
      companySlug={companySlug}
      hasProgramPage={hasProgramPage}
      headline={<FeedHeadline card={card} />}
    />
  );
}
