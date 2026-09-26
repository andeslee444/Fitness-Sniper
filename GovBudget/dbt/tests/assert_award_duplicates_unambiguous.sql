-- ROADMAP #133 (2026-09-25): a transaction key that appears more than once in
-- one award archive is resolved ONLY when it is a proven fiscal-year move —
-- exactly two copies, two different fiscal-year archives, two different
-- parseable last_modified_dates (audit_award_duplicate_copies, the acceptance
-- rule of scripts/reconcile_award_moves.py). Returns every copy of every other
-- duplicate — two copies in one fiscal year, equal dates, three or more
-- copies, a missing or unparseable date — with the reason, the fiscal year and
-- the part file, so a failing build says which rows to review. Nothing here is
-- retired: unique_fct_award_transactions_transaction_key fails on the same
-- keys, exactly as it did before the rule existed.
--
-- depends_on: {{ ref('fct_award_transactions') }}
-- (runs after the warehouse is built, beside the unique test, instead of
-- skipping it: a failure here must not hide the guard's own failure.)
select
    award_type,
    transaction_key,
    fiscal_year,
    last_modified_date,
    source_file,
    copies,
    ambiguity
from {{ ref('audit_award_duplicate_copies') }}
where resolution = 'ambiguous'
