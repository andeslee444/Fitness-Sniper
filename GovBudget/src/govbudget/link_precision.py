"""Shared held-out tally over unique links in the published population."""
import json

import duckdb


def published_link_rows(duckdb_path) -> list[dict] | None:
    with duckdb.connect(str(duckdb_path), read_only=True) as con:
        try:
            rows = con.execute("select distinct award_piid, pe_bli, method from fct_budget_to_awards where confidence in ('high','medium') and award_piid is not null and pe_bli is not null and method is not null").fetchall()
        except duckdb.CatalogException:
            return None  # Minimal test warehouses may have no link mart.
    methods = {}
    for piid, pe, method in rows:
        pair = (piid, pe)
        if pair in methods and methods[pair] != method:
            raise ValueError(f'Published precision unit has conflicting methods: {pair}')
        methods[pair] = method
    return [{'award_piid':piid,'pe_bli':pe,'method':method} for (piid,pe),method in sorted(methods.items())]


def published_relation(from_mart: bool) -> str:
    if from_mart:
        return "select distinct award_piid, pe_bli, method from jsonb_to_recordset(%(published_links)s::jsonb) as links(award_piid text, pe_bli text, method text)"
    return "select distinct award_piid, pe_bli, method from budget_line_awards where confidence in ('high','medium')"


def precision_tally_sql(sample_id: str | None, *, from_mart: bool = False) -> str:
    run_clause = '' if sample_id is None else 'and s.sample_id = %(sample_id)s'
    return f"""
        with published as ({published_relation(from_mart)}), judged as (
            select s.sample_id, b.method, s.verdict, s.adjudicated_at
            from link_precision_samples s
            join published b on b.award_piid = s.award_piid and b.pe_bli = s.pe_bli
            where s.verdict is not null and s.rubric = %(rubric)s {run_clause}
        ), latest as (
            select method, max(sample_id) as sample_id from judged group by method
        )
        select j.method, j.sample_id,
            count(*) filter (where j.verdict = 'confirmed') as confirmed,
            count(*) as sampled, max(j.adjudicated_at) as judged_at
        from judged j join latest l on l.method=j.method and l.sample_id=j.sample_id
        group by j.method,j.sample_id order by j.method
    """


def tally_params(rubric: str, sample_id: str | None, published_links: list[dict] | None) -> dict:
    return {'rubric':rubric,'sample_id':sample_id,'published_links':json.dumps(published_links)}
