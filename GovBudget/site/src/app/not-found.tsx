import type { Metadata } from "next";
import { PageIntro } from "@/components/page-intro";
import Link from "next/link";
import { SITE_NAME } from "@/lib/site";

export const metadata: Metadata = {
  title: "Page Not Found",
  description: "The page you were looking for could not be found.",
};

export default function NotFound() {
  return (
    <div className="spine py-12">
      <PageIntro eyebrow="404 / A break in the trail" title="Let’s find the right page." description="This address does not resolve to a page. Search by program name, PE/BLI, company, or agency to pick up the investigation."/>
      <div className="flex flex-col sm:flex-row gap-3">
        <button
          data-search-trigger
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary text-primary-foreground px-6 py-2.5 text-sm font-semibold hover:opacity-90 transition-opacity"
          aria-label="Search for a program, company, or agency"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
            aria-hidden="true"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
          </svg>
          Search {SITE_NAME}
        </button>
        <Link
          href="/"
          className="inline-flex items-center justify-center rounded-lg border border-border bg-card text-foreground px-6 py-2.5 text-sm font-semibold hover:bg-muted transition-colors"
        >
          Home
        </Link>
        <Link
          href="/programs/"
          className="inline-flex items-center justify-center rounded-lg border border-border bg-card text-foreground px-6 py-2.5 text-sm font-semibold hover:bg-muted transition-colors"
        >
          Browse programs
        </Link>
      </div>
    </div>
  );
}
