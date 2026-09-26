-- R-DEC-SHAREDTITLE (controller ruling 2026-09-26, under the owner's
-- 2026-09-25 delegation): a lobbying mention is keyed on the bare pe_bli, so
-- on a budget-line code two or more programs share, fct_program_lobbying's
-- program_title must name EVERY member — never one member's title (the
-- min(title) the mart carried until this ruling, which /company/{slug}/ and
-- the /data/ fct_program_lobbying.parquet then published as the program a
-- filing matched). A code that names one program must carry exactly its title.
--
-- Returned rows are the FAILURES (dbt singular test convention):
--   'omits a member'                        a member's non-empty title is not
--       one of the label's " / "-separated names. The match is on whole
--       names, never on substrings: on '30' "Major Equipment" is a substring
--       of both siblings' titles ("Other Major Equipment", "Major Equipment,
--       OSD"), and a label naming only it must still fail.
--   'names something that is not a member'  every member is named but the
--       label is longer or shorter than the members' distinct titles joined
--       with " / " — it names a non-member, or repeats one.
with members as (
    select pe_bli, title
    from {{ ref('dim_programs') }}
    where coalesce(title, '') <> ''
    group by pe_bli, title
),
expected as (
    select pe_bli,
           sum(length(title)) + 3 * (count(*) - 1) as label_length
    from members
    group by pe_bli
),
labels as (
    select distinct pe_bli, program_title
    from {{ ref('fct_program_lobbying') }}
    where pe_bli in (select pe_bli from members)
),
omitted as (
    select l.pe_bli, l.program_title, m.title as member_title
    from labels l
    join members m on m.pe_bli = l.pe_bli
    where l.program_title is null
       or position(' / ' || m.title || ' / ' in ' / ' || l.program_title || ' / ') = 0
)
select pe_bli, program_title, member_title, 'omits a member' as failure
from omitted
union all
select l.pe_bli, l.program_title, null as member_title,
       'names something that is not a member' as failure
from labels l
join expected e on e.pe_bli = l.pe_bli
where length(l.program_title) <> e.label_length
  and not exists (
      select 1 from omitted o
      where o.pe_bli = l.pe_bli
        and o.program_title is not distinct from l.program_title
  )
