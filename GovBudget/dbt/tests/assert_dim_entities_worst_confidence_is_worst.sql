-- A family's worst_confidence is its WEAKEST member's tier: no family may read
-- 'high' while any member of it is 'medium'. Before 2026-09-25 dim_entities
-- took min(confidence) over the text, which returned the BEST tier ('high'
-- sorts before 'medium') — 29 families, NAN on /companies/, read high with a
-- medium member (integration final check). Returns the offending families.
select e.family_key, e.worst_confidence
from {{ ref('dim_entities') }} e
join {{ ref('entity_xwalk') }} x on x.family_key = e.family_key
where e.worst_confidence = 'high' and x.confidence = 'medium'
group by 1, 2
