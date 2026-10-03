-- p1_era_line_map grain: one row per era key per edition (families piece 1,
-- spec §4.4). (edition, era_key) is stricter than the spec's key (edition,
-- account, organization, budget_activity, era_key): the era key already
-- carries account and organization, so a duplicate here means one era key
-- printed two budget activities, or two decision rows covered one key
-- (overlapping ranges — assert_p1_era_map_decisions_no_overlap.sql names them).
select edition, era_key, count(*) as n
from {{ ref('p1_era_line_map') }}
group by edition, era_key
having count(*) > 1
