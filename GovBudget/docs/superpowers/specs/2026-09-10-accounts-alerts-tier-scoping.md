# Accounts, saved searches and alerts — scoping note

**Date:** 2026-09-10
**Status:** SCOPING ONLY — no decision taken, no design beyond the options below
**Filed as:** ROADMAP backlog (the "Accounts / saved searches / alerts" entry)

---

## Context

`docs/superpowers/specs/2026-06-11-phase5b-product-surface-design.md:109-111`
named "accounts/auth, saved searches/alerts (first paid tier, post-launch)" an
explicit v1 non-goal, and the phase ledger's Post-launch row (`ROADMAP.md:35`)
has carried it as "backlog" ever since. Two months after launch there is no
entry, no spec and no route — this note exists so the decision can be taken
rather than re-deferred.

Half of it already shipped, statically. `site/scripts/generate-feeds.mjs`
writes, at build time, `/rss.xml`, `/feed.xml`, `/atom.xml`, one feed per event
type, and per-subject watch feeds — **287 program and 63 company feeds** live
today (`/coverage/`, 2026-09-10). Every item carries the dollars the event is
about and a `/fact/{id}` receipt permalink. A reader who wants to be told when
a program moves can already subscribe; what they cannot do is save a search,
get email, or have any state the site remembers.

The reason is the architecture, not a missing feature: the site is a **fully
static export**. There is no server, no session, no database, and no user data
anywhere in the system. Accounts are not a feature on this stack; they are a
different stack.

## Options

**A. Stay static; deepen the feeds.** Per-event-type sidecars (backlog #88),
per-district and per-agency watch feeds, and a documented "how to watch this
page" affordance. Cost: hours to days per feed family, inside the existing
build. No runtime, no user data, no recurring bill. Ceiling: a reader must
bring their own feed reader, and nothing can be sent to them.

**B. Email digest, no accounts.** A subscribe form posting to a hosted
newsletter provider; a scheduled job turns `feed.json` into a digest. Cost: a
form endpoint (the static export has none — either a provider-hosted form or
one serverless function), the provider's fee, and a privacy policy, because the
project would hold email addresses for the first time. Ceiling: one list for
everyone, or coarse per-topic lists; no per-user saved searches.

**C. Full accounts tier.** Auth, a database, a server runtime (Vercel functions
+ hosted Postgres), saved searches, per-user alert rules, billing, account
deletion, and the support burden that comes with all of it. Cost: weeks of
build and the project's first permanent operating cost and on-call surface — a
static site cannot be down in the way a login can.

## Risks

- **User data.** The project's entire safety story today is "static files, no
  user data". B and C end that, permanently, for an unproven revenue line.
- **An alert is a claim made on someone's behalf.** Cited-or-absent has to
  survive an email body with no citation panel next to it; a digest that says
  "this program was cut 40%" without the receipt is the site's own rule broken
  in the reader's inbox.
- **The corpus is not on a refresh schedule.** Backlog #8 (refresh automation)
  is open (`ROADMAP.md:680-687`) and the award corpus was last ingested
  2026-06-11 (`data/manifest.jsonl`, newest `downloaded_at`). Alerts fired from
  a stale warehouse are worse than no alerts: they imply currency the data does
  not have. **B and C should be blocked on #8**, not merely sequenced after it.
- **Billing means obligations** — refunds, tax, dunning — that no part of this
  project currently models.

## The open decision

**Does Fiscal Receipts take on a server and user data at all?**

- *No* → close the backlog entry as a deliberate non-goal, say so on the ledger
  row, and take Option A's feed depth as the whole of "alerts".
- *Yes* → which of B or C, who operates it, and confirm the #8 dependency is
  accepted as a hard prerequisite rather than a nice-to-have.

Nothing below the decision is designed here on purpose: schema, pricing and UI
are worth nothing until the first question is answered.
