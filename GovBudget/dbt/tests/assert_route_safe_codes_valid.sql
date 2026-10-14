-- p1_route_safe_codes (families piece-1 follow-ups design §4.2, #194): every
-- owner-approved page key is a usable, unique address that names exactly one
-- printed code.
--   * page_key repeats in the seed;
--   * page_key is not [A-Z0-9]+ (it must pass the llms.txt /program/ pattern
--     and the receipts grammar, and survive a URL path segment);
--   * page_key is the pe_bli of a budget_lines row that does not print the
--     seed's code under the seed's account (the alias rows themselves print
--     it: pe_bli 0390DOM, line_item_code 'O&M', account 0390D);
--   * page_key is the pe_bli of a J-book detail row (no R-2/P-40 line may
--     share an alias's address).
with codes as (
    select account, line_item_code, page_key
    from {{ ref('p1_route_safe_codes') }}
)

select 'page_key repeats in the seed' as failure, page_key, null as pe_bli, count(*) as n
from codes
group by page_key
having count(*) > 1

union all

select 'page_key is not [A-Z0-9]+', page_key, null, 1
from codes
where not regexp_matches(page_key, '^[A-Z0-9]+$')

union all

select 'page_key is the pe_bli of a budget_lines row of another code', c.page_key, b.pe_bli, count(*)
from codes c
join {{ ref('stg_budget_lines') }} b
  on b.pe_bli = c.page_key
where b.account is distinct from c.account
   or b.line_item_code is distinct from c.line_item_code
group by c.page_key, b.pe_bli

union all

select 'page_key is the pe_bli of a J-book detail row', c.page_key, d.pe_bli, count(*)
from codes c
join {{ ref('stg_budget_details') }} d
  on d.pe_bli = c.page_key
group by c.page_key, d.pe_bli
