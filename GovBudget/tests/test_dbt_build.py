import os
import subprocess
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]

CONTRACT_COLS = (
    "contract_transaction_unique_key, action_date, federal_action_obligation, "
    "recipient_uei, recipient_name, recipient_parent_uei, recipient_parent_name, "
    "awarding_agency_name, awarding_sub_agency_name, naics_code, "
    "product_or_service_code, primary_place_of_performance_state_code, "
    "prime_award_transaction_place_of_performance_cd_current, award_id_piid, "
    "usaspending_permalink, contract_award_unique_key, "
    # Phase 5H flowdown columns (stg_flow_contracts)
    "awarding_office_name, extent_competed, number_of_offers_received"
)

ENTITY_XWALK_COLS = (
    "recipient_uei, recipient_name, parent_uei, parent_name, "
    "family_key, method, confidence, total_obligation"
)


def write_parquet(dir_path: Path, sql: str):
    dir_path.mkdir(parents=True, exist_ok=True)
    duckdb.sql(f"copy ({sql}) to '{dir_path}/part.parquet' (format parquet)")


JBOOK_BUDGET_LINE_COLS = (
    "exhibit, fiscal_year, account, account_title, organization,"
    " budget_activity, budget_activity_title, pe_bli, title, amount_type, amount_thousands,"
    " source_document_id"
)

JBOOK_DOCUMENT_COLS = (
    "id, org, exhibit_family, fiscal_year, title, source_url, sha256,"
    " bytes, downloaded_at, rel_path"
)

JBOOK_DETAIL_COLS = (
    "pe_bli, project_number, project_title, scenario, amount_millions,"
    " xml_path, reconciled, org, exhibit_family, fiscal_year, document_id,"
    " account"
)

JBOOK_NARRATIVE_COLS = (
    "pe_bli, project_number, kind, title, body, xml_path, org, fiscal_year"
)

JBOOK_AWARD_COLS = (
    # `account` (migration 014, ROADMAP #70): the ONE program a link belongs
    # to for a pe_bli two programs share; NULL for every key that names one.
    "pe_bli, exhibit, fiscal_year, organization, award_piid,"
    " recipient_name, recipient_uei, matched_obligation, method, confidence, score,"
    " rationale, account"
)


def make_lake(data_dir: Path):
    jbooks = data_dir / "parquet/jbooks"
    jbooks.mkdir(parents=True, exist_ok=True)
    duckdb.sql(
        f"copy (select * from (values ('R-1','2026','0400','Research','DARPA','1','Basic Research',"
        f"'0601101E','DEFENSE RESEARCH','fy_2024_actuals','280494','1'),"
        # Phase 5H: fy_2026_total detail rows feed the budget flow river —
        # two programs under one BA so the flow tree has real fan-out,
        # plus a title-NULL, provenance-less rollup row that the dedup rules
        # MUST exclude (flow: title IS NOT NULL; decade series:
        # source_document_id IS NOT NULL + lake-verifiability withhold).
        f"('R-1','2026','0400','Research','DARPA','1','Basic Research',"
        f"'0601101E','DEFENSE RESEARCH','fy_2026_total','300000','1'),"
        f"('R-1','2026','0400','Research','DARPA','1','Basic Research',"
        f"'0601102E','APPLIED RESEARCH','fy_2026_total','100000','1'),"
        f"('R-1','2026','0400','Research','DARPA','1','Basic Research',"
        f"'0601101E',null,'fy_2026_total','400000',null),"
        # Decoy PB2024-edition titled row: dim_pe_titles' PB2026 fence
        # (fiscal_year = 2026) must keep it out of the alphabetical
        # fallback pool, or 'AAA ANCIENT NAME' would shadow the PB2026
        # title for 0601102E (adversarial review Finding A).
        f"('R-1','2024','0400','Research','DARPA','1','Basic Research',"
        f"'0601102E','AAA ANCIENT NAME','fy_2022_actuals','90000','2'),"
        # Phase 5E: PB2024 request row → fct_book_diff request_vs_actuals
        # pair with the PB2026 fy_2024_actuals row (FY2024 asked vs spent).
        f"('R-1','2024','0400','Research','DARPA','1','Basic Research',"
        f"'0601101E','DEFENSE RESEARCH','fy_2024_request','250000','2'),"
        # Phase 5E: PB2019 OSD row — its jbook details ship in TWO volumes
        # (docs 278/279 below); fct_decade_series must carry the
        # single-volume value 7,940, never the both-volumes sum 15,880
        # (assert_decade_series_pb2019_osd_single_volume).
        f"('R-1','2019','0400D','Research','OSD','3','Advanced Technology',"
        f"'0303140D8Z','Information Systems Security Program','fy_2019_total','7940','278'),"
        # Phase 5E Task 5 improvements (P-1R recompute correction): a modern
        # P-1 line with a nonzero P-1R reserve-component sibling sharing the
        # (pe_bli, amount_type) slug. P-1R is a SUBSET of P-1 (P-1 is the
        # inclusive total), so fct_decade_series must publish the P-1-only
        # value 1,775,293 — the naive P-1 + P-1R recompute (3,475,293) used
        # to withhold this grain (assert_decade_series_p1r_published_grains).
        f"('P-1','2025','3010F','Aircraft Procurement, Air Force','F','01','Combat Aircraft',"
        f"'C130J0','C-130J','fy_2023_actuals','1775293','300'),"
        f"('P-1R','2025','3010F','Aircraft Procurement, Air Force','F','01','Combat Aircraft',"
        f"'C130J0','C-130J','fy_2023_actuals','1700000','300'),"
        # Wave 5: ONE budget-line code, TWO unrelated Navy programs in two
        # appropriations — the live '3010' shape (LPD Flight II in
        # Shipbuilding & Conversion, Shipboard Tactical Communications in
        # Other Procurement). Both sides report fy_2026_total, so this is a
        # genuine collision on dim_programs' own anchor, and both carry
        # R-2/P-40 detail below. Before Wave 5 the detail source had no
        # account and the mart summed them into ONE row of $528.574M under
        # the communications title; assert_dim_programs_detail_account_single
        # fails on exactly that.
        f"('P-1','2026','1611N','Shipbuilding and Conversion, Navy','N','02','Other Warships',"
        f"'3010','LPD Flight II','fy_2024_actuals','500000','400'),"
        f"('P-1','2026','1611N','Shipbuilding and Conversion, Navy','N','02','Other Warships',"
        f"'3010','LPD Flight II','fy_2026_total','1000000','400'),"
        f"('P-1','2026','1810N','Other Procurement, Navy','N','01','Ship Propulsion',"
        f"'3010','Shipboard Tactical Communications','fy_2024_actuals','28574','401'),"
        f"('P-1','2026','1810N','Other Procurement, Navy','N','01','Ship Propulsion',"
        f"'3010','Shipboard Tactical Communications','fy_2026_total','50000','401'))"
        f" t({JBOOK_BUDGET_LINE_COLS})) to '{jbooks}/budget_lines.parquet' (format parquet)"
    )
    duckdb.sql(
        f"copy (select * from (values ('1','DARPA','rdte','2026','vol1.pdf',"
        f"'https://example.test/vol1.pdf','sha-darpa-2026','1000','2026-06-01','fy2026/darpa/vol1.pdf'),"
        f"('2','DARPA','rdte','2024','vol1.pdf',"
        f"'https://example.test/2024/vol1.pdf','sha-darpa-2024','1000','2026-06-01','fy2024/darpa/vol1.pdf'),"
        f"('278','OSD','rdte','2019','vol3a.pdf',"
        f"'https://example.test/2019/vol3a.pdf','sha-osd-2019-a','1000','2026-06-01','fy2019/osd/vol3a.pdf'),"
        f"('279','OSD','rdte','2019','vol3b.pdf',"
        f"'https://example.test/2019/vol3b.pdf','sha-osd-2019-b','1000','2026-06-01','fy2019/osd/vol3b.pdf'),"
        f"('300','AF','rollup','2025','p1_display.xlsx',"
        f"'https://example.test/2025/p1_display.xlsx','sha-af-2025','1000','2026-06-01','fy2025/af/p1_display.xlsx'),"
        # PM-review Sprint 1: FY2026 Army dual-volume pair — docs 344/351
        # EACH embed the same RDT&E XML (live: Vol 1 BA-1 / BA-2 PDFs), so
        # identical fy2026 detail tuples appear under both. dim_programs
        # must dedupe (assert_dim_programs_dual_volume_dedup_pin).
        f"('344','A','rdte','2026','RDTE - Vol 1 - Budget Activity 1.pdf',"
        f"'https://example.test/2026/army-vol1-ba1.pdf','sha-army-2026-ba1','1000','2026-06-01','fy2026/army/vol1ba1.pdf'),"
        f"('351','A','rdte','2026','RDTE - Vol 1 - Budget Activity 2.pdf',"
        f"'https://example.test/2026/army-vol1-ba2.pdf','sha-army-2026-ba2','1000','2026-06-01','fy2026/army/vol1ba2.pdf'),"
        # Wave 5: the two Navy procurement books behind the shared '3010'
        # key — different appropriations, different programs, one BLI code.
        f"('400','N','procurement','2026','SCN_Book.pdf',"
        f"'https://example.test/2026/scn.pdf','sha-navy-2026-scn','1000','2026-06-01','fy2026/n/SCN_Book.pdf'),"
        f"('401','N','procurement','2026','OPN_BA1_Book.pdf',"
        f"'https://example.test/2026/opn.pdf','sha-navy-2026-opn','1000','2026-06-01','fy2026/n/OPN_BA1_Book.pdf'))"
        f" t({JBOOK_DOCUMENT_COLS})) to '{jbooks}/documents.parquet' (format parquet)"
    )
    duckdb.sql(
        f"copy (select * from (values ('0601101E',null,'Defense Research','PriorYear','280.494',"
        f"'ProgramElement[0]','True','DARPA','rdte','2026','1',null),"
        # Decoy PB2024-edition row: scenario names are edition-RELATIVE
        # (PriorYear = FY2022 actuals in PB2024), so the dim_programs
        # PB2026 fence (fiscal_year = 2026) must exclude it — the
        # assert_dim_programs_pb2026_pin dbt test fails if it ever sums in.
        f"('0601101E',null,'Defense Research','PriorYear','424.332',"
        f"'ProgramElement[0]','True','DARPA','rdte','2024','2',null),"
        # Phase 5E PB2019 OSD dual-volume pair: docs 278 and 279 EACH embed
        # the complete OSD XML — identical (pe_bli, scenario, amount)
        # tuples under both documents (Task 5 binding (i)).
        f"('0303140D8Z',null,'Information Systems Security Program','BudgetYearOne','7.940',"
        f"'ProgramElement[0]','True','OSD','rdte','2019','278',null),"
        f"('0303140D8Z',null,'Information Systems Security Program','BudgetYearOne','7.940',"
        f"'ProgramElement[0]','True','OSD','rdte','2019','279',null),"
        # PM-review Sprint 1: FY2026 dual-volume duplication INSIDE the
        # PB2026 fence — docs 344/351 each carry the identical PriorYear
        # root tuple for 0601102A (live: 47 Army PEs doubled to 2× in
        # dim_programs). The distinct-tuple dedup must report 322.341,
        # never the raw both-volumes sum 644.682.
        f"('0601102A',null,'University Research Initiatives','PriorYear','322.341',"
        f"'ProgramElement[1]','True','A','rdte','2026','344',null),"
        f"('0601102A',null,'University Research Initiatives','PriorYear','322.341',"
        f"'ProgramElement[1]','True','A','rdte','2026','351',null),"
        # Wave 5: the shared-'3010' detail pair. Same pe_bli, different
        # appropriation on each row — the account column is the ONLY thing
        # that tells them apart, and dim_programs must not add 500.000 to
        # 28.574.
        f"('3010',null,'LPD Flight II','PriorYear','500.000',"
        f"'LineItem[0]','True','N','procurement','2026','400','1611N'),"
        f"('3010',null,'Shipboard Tactical Communications','PriorYear','28.574',"
        f"'LineItem[7]','True','N','procurement','2026','401','1810N'))"
        f" t({JBOOK_DETAIL_COLS})) to '{jbooks}/details.parquet' (format parquet)"
    )
    duckdb.sql(
        f"copy (select * from (values ('0601101E',null,'accomplishment','Defense Research',"
        f"'Some body text','ProgramElement[0]','DARPA','2026'),"
        # Wave 5: 0601102A has R-2 detail (docs 344/351) and NO budget_lines
        # row, so stg_budget_lines can give dim_programs no name for it —
        # exactly the live shape of Navy 3039/3043. Its title has to come from
        # the J-book's own narrative, or the program ships nameless and takes
        # the client search index down with it (not_null_dim_programs_title).
        f"('0601102A',null,'mission','University Research Initiatives',"
        f"'Basic research grants to universities.','ProgramElement[1]','A','2026'))"
        f" t({JBOOK_NARRATIVE_COLS})) to '{jbooks}/detail_narratives.parquet' (format parquet)"
    )
    duckdb.sql(
        f"copy (select * from (values ('0601101E','R-1','2026','DARPA','HR001124C0001',"
        f"'ACME RESEARCH','UEI1','5000000','account+tokens','high','4','test account','0400'),"
        # 2026-09-04 (#75 fix round 1, finding 1): HR001124C0002 is
        # account+tokens/high with NO matching adjudication row below — the
        # mart's demotion `case` (fct_budget_to_awards.sql) must publish it
        # as 'medium' while crosswalk_confidence keeps the raw 'high' tag.
        # The pre-existing HR001124C0001 fixture always had an adjudication
        # row, so it could never exercise this branch.
        f"('0601101E','R-1','2026','DARPA','HR001124C0002',"
        f"'WIDGET CORP','UEI2','3000000','account+tokens','high','4','test account, unadjudicated','0400'),"
        # HR001124C0003 is adjudicated 'reject' below (mechanical tag is
        # irrelevant) — must drop out of the mart entirely, not just get a
        # low confidence.
        f"('0601101E','R-1','2026','DARPA','HR001124C0003',"
        f"'GAMMA INC','UEI3','2000000','account+tokens','high','4','test account, rejected','0400'),"
        # ROADMAP #70: the shared '3010' code (LPD Flight II in 1611N,
        # Shipboard Tactical Communications in 1810N — the budget_lines rows
        # above) with ONE link per member. The mart must resolve each link's
        # program_title through (pe_bli, account) and must NOT fan either row
        # out across both dim_programs rows.
        f"('3010','P-1','2026','N','N0002420C0001',"
        f"'HUNTINGTON INGALLS','UEI4','9000000','fpds-ap','medium','1',"
        f"'FPDS account narrowing; shared BLI code resolved to account 1611N','1611N'),"
        f"('3010','P-1','2026','N','N0003917D0006',"
        f"'SERCO','UEI5','1000000','fpds-ap','medium','1',"
        f"'FPDS account narrowing; shared BLI code resolved to account 1810N','1810N'))"
        f" t({JBOOK_AWARD_COLS})) to '{jbooks}/budget_line_awards.parquet' (format parquet)"
    )
    # Hand-adjudication overlay (migration 010): the mart coalesces this over
    # the mechanical confidence — the fixture row exercises exactly that path
    # (mechanical 'high' confirmed as adjudicated 'high'). HR001124C0002 is
    # deliberately absent here (see comment above); HR001124C0003 is
    # adjudicated 'reject' so the mart's coalesce()/filter must drop it.
    duckdb.sql(
        f"copy (select * from (values ('HR001124C0001','0601101E','high','pinned',"
        f"'pinned-here','narrative-grep','fixture evidence','2','hand-adjudication-v1',"
        f"'2026-09-01T00:00:00Z'),"
        f"('HR001124C0003','0601101E','reject','contradicted',"
        f"'pinned-elsewhere:other','narrative-grep','fixture evidence','2','hand-adjudication-v1',"
        f"'2026-09-01T00:00:00Z'))"
        f" t(award_piid, pe_bli, adjudicated_confidence, award_verdict, pair_reason,"
        f" basis, evidence, refuter_lenses_passed, method, adjudicated_at))"
        f" to '{jbooks}/award_adjudications.parquet' (format parquet)"
    )
    write_parquet(
        data_dir / "parquet/contracts/fy=2017",
        f"select * from (values "
        f"('K1','2017-01-15','1000.5','UEI1','ACME','PUEI1','ACME PARENT','DoD','Army','336411','1510','CA','CA-52','HR001124C0001','https://www.usaspending.gov/award/CONT_AWD_HR001124C0001','CAUK1','ACC-APG','FULL AND OPEN COMPETITION','3'),"
        # K3 is a DEOBLIGATION on the same award, district and fiscal year as
        # K1 (ROADMAP #6 rider, 2026-09-11). Without it the fixture cannot tell
        # the by-year marts' positive_obligation formula apart from a wrong one:
        # a single positive transaction returns 1000.5 under both
        # sum(greatest(obl,0)) (transaction level, what the models do) and
        # greatest(sum(obl),0) (award level, what they must not do). With K3 the
        # two differ — 1000.5 vs 800.25 — and the fixture pins the right one.
        # Same award_id_piid and recipient, so award_count and recipient_count
        # stay 1 while transaction_count becomes 2.
        f"('K3','2017-06-30','-200.25','UEI1','ACME','PUEI1','ACME PARENT','DoD','Army','336411','1510','CA','CA-52','HR001124C0001','https://www.usaspending.gov/award/CONT_AWD_HR001124C0001','CAUK1','ACC-APG','FULL AND OPEN COMPETITION','3'),"
        f"('K2','2017-03-02','-50.25','UEI2','BETA','','','DoD','Navy','541330','R425','VA','VA-08',null,'https://www.usaspending.gov/award/CONT_AWD_K2',null,'NAVSEA HQ','NOT COMPETED',null)"
        f") t({CONTRACT_COLS})",
    )
    write_parquet(
        data_dir / "parquet/assistance/fy=2017",
        "select * from (values "
        "('A1','2017-02-01','5000','UEI1','ACME','PUEI1','ACME PARENT','DoD','Army','MARYLAND','MD-04','https://www.usaspending.gov/award/ASST_NON_A1','ASUK1')"
        ") t(assistance_transaction_unique_key, action_date, federal_action_obligation, "
        "recipient_uei, recipient_name, recipient_parent_uei, recipient_parent_name, "
        "awarding_agency_name, awarding_sub_agency_name, primary_place_of_performance_state_name, "
        "prime_award_transaction_place_of_performance_cd_current, "
        "usaspending_permalink, assistance_award_unique_key)",
    )
    # entity_xwalk fixture — one row, all 8 columns
    entities = data_dir / "parquet/entities"
    entities.mkdir(parents=True, exist_ok=True)
    duckdb.sql(
        f"copy (select * from (values "
        f"('UEI1','ACME','PUEI1','ACME PARENT INC','ACME PARENT','parent_name','high',6000.5))"
        f" t({ENTITY_XWALK_COLS})) to '{entities}/entity_xwalk.parquet' (format parquet)"
    )
    write_parquet(
        data_dir / "parquet/subawards/fy=2017",
        "select * from (values ('K1','250.0','1000.0','2017-05-01','SUEI1','GAMMA SUB')) "
        "t(prime_award_unique_key, subaward_amount, prime_award_amount, subaward_action_date, subawardee_uei, subawardee_name)",
    )
    write_parquet(
        data_dir / "parquet/mts_outlays",
        "select * from (values ('2017-10-31','Department of Defense','1000')) "
        "t(record_date, classification_desc, current_month_gross_outly_amt)",
    )
    # oversight fixtures for new efficiency marts — typed schema (backlog #11):
    # fiscal_year INTEGER, rate/amount columns DOUBLE, mapped BOOLEAN
    oversight = data_dir / "parquet/oversight"
    oversight.mkdir(parents=True, exist_ok=True)
    duckdb.sql(
        f"copy (select * from (values "
        f"('Medicare Fee-for-Service','Department of Health and Human Services','HHS',2023,7.66,31700000000.0,0.0,413900000000.0,'https://paymentaccuracy.gov/program/hhs-medicare-ffs'),"
        f"('Medicare Fee-for-Service','Department of Health and Human Services','HHS',2022,6.26,25740000000.0,0.0,411300000000.0,'https://paymentaccuracy.gov/program/hhs-medicare-ffs'),"
        f"('SNAP','Department of Agriculture','USDA',2023,5.74,5060000000.0,0.0,88100000000.0,'https://paymentaccuracy.gov/program/usda-snap'),"
        f"('SNAP','Department of Agriculture','USDA',2022,4.71,3970000000.0,0.0,84300000000.0,'https://paymentaccuracy.gov/program/usda-snap'),"
        f"('Earned Income Tax Credit','Department of the Treasury','TREASURY',2023,34.02,21900000000.0,0.0,64400000000.0,'https://paymentaccuracy.gov/program/treasury-eitc')"
        f") t(program, agency_name, agency_code, fiscal_year, rate_pct, derived_improper_amount_usd, unknown_rate_pct, outlays_usd, source_url))"
        f" to '{oversight}/improper_payments.parquet' (format parquet)"
    )
    duckdb.sql(
        f"copy (select * from (values "
        f"('DOD Contract Management','https://files.gao.gov/reports/GAO-25-107743/index.html#dod-contract','DOD',true,'DoD contract management','https://www.gao.gov/high-risk-list'),"
        f"('DOD Weapon Systems Acquisition','https://files.gao.gov/reports/GAO-25-107743/index.html#dod-weapons','DOD',true,'DoD weapons programs','https://www.gao.gov/high-risk-list'),"
        f"('Medicare/Medicaid','https://files.gao.gov/reports/GAO-25-107743/index.html#medicare','HHS',true,'CMS programs','https://www.gao.gov/high-risk-list'),"
        f"('Enforcement of Tax Laws','https://files.gao.gov/reports/GAO-25-107743/index.html#tax','TREASURY',true,'IRS enforcement','https://www.gao.gov/high-risk-list'),"
        f"('Unmapped Area','https://files.gao.gov/reports/GAO-25-107743/index.html#unmapped','',false,'no clear agency','https://www.gao.gov/high-risk-list')"
        f") t(area_title, area_url, agency_code, mapped, notes, source_url))"
        f" to '{oversight}/high_risk.parquet' (format parquet)"
    )
    # states fixtures for phase 4 marts
    states = data_dir / "parquet/states"
    states.mkdir(parents=True, exist_ok=True)
    duckdb.sql(
        f"copy (select * from (values "
        f"('Dept A','Agency','Travel','General Fund','2025','1000.0','False','https://open.fiscal.ca.gov/dept'),"
        f"('Dept A','Agency','Salaries & Wages','General Fund','2025','5000.0','False','https://open.fiscal.ca.gov/dept'),"
        f"('Dept B','Agency','Travel','General Fund','2025','2000.0','False','https://open.fiscal.ca.gov/dept'),"
        f"('Dept B','Agency','Grants and Subventions','General Fund','2025','50000.0','False','https://open.fiscal.ca.gov/dept')"
        f") t(department, agency, category, fund, fiscal_year, amount_usd, is_total, source_url))"
        f" to '{states}/ca_budget.parquet' (format parquet)"
    )
    duckdb.sql(
        f"copy (select * from (values "
        f"('CA','Dept A','Travel','2025','1000.0','https://open.fiscal.ca.gov/dept'),"
        f"('CA','Dept A','Salaries & Wages','2025','5000.0','https://open.fiscal.ca.gov/dept'),"
        f"('CA','Dept B','Travel','2025','2000.0','https://open.fiscal.ca.gov/dept'),"
        f"('CA','Dept B','Grants and Subventions','2025','50000.0','https://open.fiscal.ca.gov/dept')"
        f") t(jurisdiction, department, category, fiscal_year, amount_usd, source_url))"
        f" to '{states}/ca_checkbook_agg.parquet' (format parquet)"
    )
    duckdb.sql(
        f"copy (select * from (values "
        f"('CT','CT Dept 1','Out-Of-State Travel','2025','3000.0','https://data.ct.gov/q'),"
        f"('CT','CT Dept 1','In-State Travel','2025','500.0','https://data.ct.gov/q'),"
        f"('CT','CT Dept 1','State Aid Grants','2025','200000.0','https://data.ct.gov/q')"
        f") t(jurisdiction, department, category, fiscal_year, amount_usd, source_url))"
        f" to '{states}/ct_checkbook_agg.parquet' (format parquet)"
    )
    duckdb.sql(
        f"copy (select * from (values "
        f"('CA','2024','39000000','https://census.gov/pop'),"
        f"('CT','2024','3600000','https://census.gov/pop')"
        f") t(state, year, population, source_url))"
        f" to '{states}/state_population.parquet' (format parquet)"
    )
    # influence fixtures for phase 5A marts
    influence = data_dir / "parquet/influence"
    influence.mkdir(parents=True, exist_ok=True)
    duckdb.sql(
        f"copy (select * from (values "
        f"('uuid-lda-001','https://lda.gov/filings/public/filing/uuid-lda-001/print/','ACME PARENT INC','OUTSIDE FIRM LLC','2024','first_quarter','Q1','150000','','ACME PARENT','exact_family'),"
        f"('uuid-lda-002','https://lda.gov/filings/public/filing/uuid-lda-002/print/','ACME PARENT INC','ACME PARENT INC','2024','second_quarter','Q2','','50000','ACME PARENT','exact_family')"
        f") t(filing_uuid, url, client_name, registrant_name, filing_year, filing_period, filing_type,"
        f" income_usd, expenses_usd, family_key_guess, match_method))"
        f" to '{influence}/lda_filings.parquet' (format parquet)"
    )
    duckdb.sql(
        f"copy (select * from (values "
        f"('uuid-lda-001','DEF','Defense','FY26 NDAA issues related to JADC2 and acquisition.','[\"SENATE\"]'),"
        f"('uuid-lda-002','GOV','Government Issues','Issues related to C-130J aircraft and appropriations.','[]')"
        f") t(filing_uuid, issue_code, issue_display, description, agencies_json))"
        f" to '{influence}/lda_activities.parquet' (format parquet)"
    )
    duckdb.sql(
        f"copy (select * from (values "
        f"('uuid-lda-001','JANE DOE','Deputy Secretary of Defense (Smith Administration)'),"
        f"('uuid-lda-002','JOHN SMITH','')"
        f") t(filing_uuid, name, covered_position))"
        f" to '{influence}/lda_lobbyists.parquet' (format parquet)"
    )
    duckdb.sql(
        f"copy (select * from (values "
        f"('uuid-lda-001','0604122D8Z','JADC2','alias','FY26 NDAA issues related to JADC2 and acquisition.'),"
        f"('uuid-lda-002','2012C130J','C-130J','alias','Issues related to C-130J aircraft and appropriations.')"
        f") t(filing_uuid, pe_bli, matched_term, evidence_kind, description_snippet))"
        f" to '{influence}/lda_program_mentions.parquet' (format parquet)"
    )


def test_dbt_build_succeeds_on_fixture_lake(tmp_path):
    make_lake(tmp_path)
    (tmp_path / "duckdb").mkdir()
    env = {
        **os.environ,
        "GOVBUDGET_DATA": str(tmp_path),
        "GOVBUDGET_DUCKDB": str(tmp_path / "duckdb" / "test.duckdb"),
    }
    result = subprocess.run(
        ["uv", "run", "dbt", "build", "--project-dir", "dbt", "--profiles-dir", "dbt"],
        cwd=ROOT, env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    con = duckdb.connect(str(tmp_path / "duckdb" / "test.duckdb"))
    # 4 since the ROADMAP #6 rider added K3, a deobligation on K1's award.
    assert con.sql("select count(*) from fct_award_transactions").fetchone()[0] == 4
    assert con.sql("select count(*) from dim_recipients").fetchone()[0] == 2
    # UEI1 = K1 1000.5 + K3 -200.25 + A1 5000 (a NET total, deobligation included).
    assert con.sql(
        "select total_obligation from dim_recipients where recipient_uei='UEI1'"
    ).fetchone()[0] == 5800.25
    # Phase 5A influence mart assertions
    assert con.sql("select count(*) from fct_influence").fetchone()[0] >= 1
    assert con.sql(
        "select lobbying_total_usd from fct_influence"
        " where family_key='ACME PARENT' and filing_year='2024'"
    ).fetchone()[0] == 200000.0  # 150000 income + 50000 expenses
    assert con.sql("select count(*) from fct_program_lobbying").fetchone()[0] == 2
    assert con.sql("select count(*) from dim_lobbyists").fetchone()[0] == 2
    # revolving_door true for JANE DOE (has covered_position), false for JOHN SMITH
    assert con.sql(
        "select revolving_door from dim_lobbyists where name='JANE DOE'"
    ).fetchone()[0] is True
    assert con.sql(
        "select revolving_door from dim_lobbyists where name='JOHN SMITH'"
    ).fetchone()[0] is False
    # Phase 5B-3 new mart assertions
    # fct_feed_events: the fixture has no yoy_swing or new_entrant thresholds met
    # (only 1 budget row at 280494 thousands, no |pct_change|>=50 since only 1 FY).
    # The model must exist and be queryable; row count >= 0.
    assert con.sql("select count(*) from fct_feed_events").fetchone()[0] >= 0
    # dim_pe_titles (backlog #14): canonical title per pe_bli from titled
    # detail rows — the fixture's single titled budget_lines row must resolve.
    assert con.sql(
        "select title from dim_pe_titles where pe_bli='0601101E'"
    ).fetchone()[0] == 'DEFENSE RESEARCH'
    # PB2026 fences (Finding A): dim_programs' fy2024_actual_millions is a
    # PB2026-semantic column — the fixture's PB2024 PriorYear decoy row
    # (FY2022 actuals!) must NOT sum in (280.494, never 704.826)…
    assert con.sql(
        "select fy2024_actual_millions from dim_programs where pe_bli='0601101E'"
    ).fetchone()[0] == 280.494
    # …and dim_pe_titles' fallback pool is PB2026-only: the PB2024 decoy
    # title must not shadow the PB2026 title alphabetically.
    assert con.sql(
        "select title from dim_pe_titles where pe_bli='0601102E'"
    ).fetchone()[0] == 'APPLIED RESEARCH'
    # fct_budget_to_awards (#75 fix round 1, finding 1): mart demotion
    # coverage. HR001124C0001 is the adjudicated control — adjudicated
    # 'high' publishes as 'high', confidence_source='adjudicated'.
    control = con.sql(
        "select confidence, crosswalk_confidence, confidence_source"
        " from fct_budget_to_awards where award_piid='HR001124C0001'"
    ).fetchone()
    assert control == ('high', 'high', 'adjudicated')
    # HR001124C0002 is account+tokens/high with NO adjudication row — the
    # demotion `case` in fct_budget_to_awards.sql must publish 'medium'
    # while crosswalk_confidence keeps the raw mechanical 'high' tag.
    demoted = con.sql(
        "select confidence, crosswalk_confidence, confidence_source"
        " from fct_budget_to_awards where award_piid='HR001124C0002'"
    ).fetchone()
    assert demoted == ('medium', 'high', 'mechanical')
    # HR001124C0003 is adjudicated 'reject' — it must drop out of the mart
    # entirely (not merely demoted), regardless of its mechanical tag.
    assert con.sql(
        "select count(*) from fct_budget_to_awards where award_piid='HR001124C0003'"
    ).fetchone()[0] == 0
    # ROADMAP #70: the two links on the shared '3010' code each resolve to
    # their OWN member's title through (pe_bli, account), and neither fans out
    # across both dim_programs rows (the pre-#70 `programs` CTE deduped to one
    # row per pe_bli precisely to stop that, and still does for account-NULL
    # rows — this asserts the account-qualified join is a strict refinement).
    split = con.sql(
        "select award_piid, account, program_title, count(*) over () as n_rows"
        " from fct_budget_to_awards where pe_bli='3010' order by award_piid"
    ).fetchall()
    assert split == [
        ('N0002420C0001', '1611N', 'LPD Flight II', 2),
        ('N0003917D0006', '1810N', 'Shipboard Tactical Communications', 2),
    ], split
    # An ordinary (single-program) pe_bli keeps its own title either way — the
    # account-qualified join resolves it when dim_programs carries the account,
    # the bare-key CTE when it does not.
    assert con.sql(
        "select account, program_title from fct_budget_to_awards"
        " where award_piid='HR001124C0002'"
    ).fetchone() == ('0400', 'DEFENSE RESEARCH')
    # fct_district_programs: the fixture contracts have CA-52 district + award HR001124C0001
    # which matches the high-confidence jbook_award. Expect >= 1 row.
    assert con.sql("select count(*) from fct_district_programs").fetchone()[0] >= 1
    # Task 27: uniqueness on (pop_state, pop_district, pe_bli, account) — the
    # member grain. account is NULL for every code that names one program, so
    # the sentinel is what makes the NULL side countable (mirrors
    # assert_district_programs_grain_unique).
    assert con.sql(
        "select count(*) from ("
        "  select pop_state, pop_district, pe_bli,"
        "         coalesce(account, '(unresolved)') as account_key"
        "  from fct_district_programs"
        "  group by 1,2,3,4 having count(*) > 1"
        ")"
    ).fetchone()[0] == 0
    # The fixture's one district-linked award carries account '0400' (the
    # budget_line_awards row above), so the mart emits it rather than NULL.
    assert con.sql(
        "select account from fct_district_programs where pop_district='CA-52'"
    ).fetchall() == [('0400',)]
    # ── ROADMAP #6: district × fiscal_year drill-down ────────────────────
    # The fixture's only district-linked award is HR001124C0001 (CA-52,
    # contracts partition fy=2017) matched to the high-confidence jbook_award
    # on pe_bli 0601101E. (HR001124C0002 is demoted to medium and
    # HR001124C0003 is adjudicated 'reject', so neither joins.) It carries TWO
    # transactions: K1 +1000.5 and the K3 deobligation -200.25. Both by-year
    # marts must hold exactly one CA-52 row, in FY2017, netting to 800.25.
    #
    # The 800.25/1000.5 pair is the point of the rider: positive_obligation is
    # summed at the TRANSACTION level (sum(greatest(obl,0)) = 1000.5), not at
    # the award level: greatest(sum(obl),0) is 800.25 here, so the two formulas
    # disagree and this row pins the right one. Measured read-only against the
    # shipped warehouse 2026-09-11: 278 of the 924 district-year cells differ
    # by more than a cent between the two formulas (293 differ at all).
    assert con.sql(
        "select fiscal_year, award_count, total_obligation, positive_obligation"
        " from fct_district_totals_by_year where pop_district='CA-52'"
    ).fetchall() == [(2017, 1, 800.25, 1000.5)]
    assert con.sql(
        "select fiscal_year, pe_bli, transaction_count, award_count,"
        "       recipient_count, total_obligation, positive_obligation"
        " from fct_district_programs_by_year where pop_district='CA-52'"
    ).fetchall() == [(2017, '0601101E', 2, 1, 1, 800.25, 1000.5)]
    # The by-year models carry the SAME labels as their all-years siblings —
    # a title that drifts between the two would put one program's dollars
    # under two names on the same page (the #70 species).
    assert con.sql(
        "select program_title, organization from fct_district_programs_by_year"
        " where pop_district='CA-52'"
    ).fetchone() == con.sql(
        "select program_title, organization from fct_district_programs"
        " where pop_district='CA-52'"
    ).fetchone()
    # Grain uniqueness, both models (mirrors assert_district_by_year_grain_unique).
    assert con.sql(
        "select count(*) from ("
        "  select pop_state, pop_district, fiscal_year"
        "  from fct_district_totals_by_year group by 1,2,3 having count(*) > 1"
        ")"
    ).fetchone()[0] == 0
    assert con.sql(
        "select count(*) from ("
        "  select pop_state, pop_district, pe_bli, fiscal_year"
        "  from fct_district_programs_by_year group by 1,2,3,4 having count(*) > 1"
        ")"
    ).fetchone()[0] == 0
    # THE CONTRACT 18b's gate 9 leg f depends on: the by-year rows sum back to
    # the headline model. Tolerance, never an exact magnitude — see ruling 8.
    assert con.sql(
        "select max(abs(d.total_obligation - y.s)) from fct_district_totals d"
        " join (select pop_state, pop_district, sum(total_obligation) s"
        "       from fct_district_totals_by_year group by 1,2) y"
        "   using (pop_state, pop_district)"
    ).fetchone()[0] < 0.01
    # Task 27: the pair is joined on the account too, with IS NOT DISTINCT
    # FROM rather than USING — a NULL account (every code that names one
    # program) would drop out of an equality join and leave the contract
    # silently unchecked for exactly the rows that make up almost all of it.
    assert con.sql(
        "select max(abs(p.total_obligation - s.s)) from fct_district_programs p"
        " join (select pop_state, pop_district, pe_bli, account,"
        "              sum(total_obligation) s"
        "       from fct_district_programs_by_year group by 1,2,3,4) s"
        "   on p.pop_state is not distinct from s.pop_state"
        "  and p.pop_district is not distinct from s.pop_district"
        "  and p.pe_bli is not distinct from s.pe_bli"
        "  and p.account is not distinct from s.account"
    ).fetchone()[0] < 0.01
    # fct_family_obligations_by_year: UEI1 → ACME PARENT family; 3 transactions across fiscal years
    assert con.sql("select count(*) from fct_family_obligations_by_year").fetchone()[0] >= 1
    # stg_contracts / stg_assistance now carry usaspending_permalink + award_unique_key
    assert con.sql(
        "select usaspending_permalink from fct_award_transactions"
        " where transaction_key='K1'"
    ).fetchone()[0] == 'https://www.usaspending.gov/award/CONT_AWD_HR001124C0001'
    assert con.sql(
        "select award_unique_key from fct_award_transactions"
        " where transaction_key='A1'"
    ).fetchone()[0] == 'ASUK1'
    # Subaward outlier guard: stg_subawards must expose is_amount_suspect flag.
    # The fixture has 1 clean row (subaward 250 <= prime 1000), so is_amount_suspect=False.
    suspect_count = con.sql(
        "select count(*) from stg_subawards where is_amount_suspect = true"
    ).fetchone()[0]
    assert suspect_count == 0, (
        f"fixture has no suspect rows but got {suspect_count} — guard is misfiring"
    )
    clean_count = con.sql(
        "select count(*) from stg_subawards where is_amount_suspect = false"
    ).fetchone()[0]
    assert clean_count == 1, f"expected 1 clean subaward row, got {clean_count}"

    # Phase 5H fct_flow_edges — budget river (dedup rule: title IS NOT NULL,
    # amount_type='fy_2026_total'; the 400000 rollup row must NOT count)
    assert con.sql(
        "select amount from fct_flow_edges where river='budget'"
        " and level_from='total' and node_to='DARPA'"
    ).fetchone()[0] == 400000.0  # 300000 + 100000 detail rows only
    # 4 since Wave 5 added the shared-'3010' pair: DARPA's two PEs plus the
    # two Navy programs that share one budget-line code. Their being TWO
    # edges rather than one fused edge is the point.
    assert con.sql(
        "select count(*) from fct_flow_edges where river='budget'"
        " and level_to='program'"
    ).fetchone()[0] == 4
    assert con.sql(
        "select amount from fct_flow_edges where river='budget'"
        " and node_to='DARPA|0400|1|0601101E'"
    ).fetchone()[0] == 300000.0
    # Spend river: competed_class mapping + offers buckets from the fixture
    # contracts (K1 + K3 full-and-open/3 offers, K2 not-competed/null offers);
    # the assistance row must NOT appear (contracts only). 800.25 = K1 1000.5
    # net of the K3 deobligation -200.25, both in the same class and bucket.
    assert con.sql(
        "select competed_class, offers_bucket, amount from fct_flow_edges"
        " where river='spend' and level_from='total' and competed_class='full_and_open'"
    ).fetchall() == [("full_and_open", "3-4", 800.25)]
    assert con.sql(
        "select competed_class, offers_bucket, amount from fct_flow_edges"
        " where river='spend' and level_from='total' and competed_class='not_competed'"
    ).fetchall() == [("not_competed", "unknown", -50.25)]
    # office → family edge resolves the entity_xwalk family for UEI1
    assert con.sql(
        "select node_to from fct_flow_edges where river='spend'"
        " and level_from='office' and node_from='Army|ACC-APG'"
    ).fetchone()[0] == "ACME PARENT"
    # UEI2 has no xwalk row — family falls back to upper(recipient_name)
    assert con.sql(
        "select node_to from fct_flow_edges where river='spend'"
        " and level_from='office' and node_from='Navy|NAVSEA HQ'"
    ).fetchone()[0] == "BETA"

    # Phase 5E Task 5: fct_decade_series + fct_book_diff
    # PB2026 PriorYear pin row at the edition-aware grain (280,494 $K)
    assert con.sql(
        "select amount from fct_decade_series where pe_bli='0601101E'"
        " and fy=2024 and edition_year=2026"
    ).fetchone()[0] == 280494.0
    # the poisoned fy_2026_total grain (provenance-less 400000 twin in the
    # raw lake) is WITHHELD by the lake-verifiability filter — the series
    # never publishes a value the verify-phase5e gate cannot recompute
    assert con.sql(
        "select count(*) from fct_decade_series where pe_bli='0601101E'"
        " and edition_year=2026 and amount_type_kind='request'"
    ).fetchone()[0] == 0
    # PB2019 OSD dual-volume (binding (i)): the single-volume value 7,940,
    # never the both-volumes sum 15,880
    assert con.sql(
        "select amount from fct_decade_series where pe_bli='0303140D8Z'"
        " and edition_year=2019 and amount_type_kind='request'"
    ).fetchone()[0] == 7940.0
    # P-1R recompute correction (Task 5 improvements): the C130J0 grain has
    # a nonzero P-1R sibling under the same slug — it must be PUBLISHED with
    # the P-1-only value (P-1 ⊇ P-1R; the reserve share must never sum in),
    # not withheld by a naive P-1 + P-1R lake recompute.
    assert con.sql(
        "select amount from fct_decade_series where pe_bli='C130J0'"
        " and fy=2023 and edition_year=2025"
    ).fetchone()[0] == 1775293.0
    # single-source grains carry a workbook fact_id (Task 6 minting handoff)
    assert con.sql(
        "select source_fact_id from fct_decade_series where pe_bli='0303140D8Z'"
        " and edition_year=2019 and amount_type_kind='request'"
    ).fetchone()[0] is not None
    # book diff: FY2024 asked (PB2024 request) vs FY2024 spent (PB2026 actuals)
    assert con.sql(
        "select from_value, to_value, delta from fct_book_diff"
        " where pe_bli='0601101E' and diff_kind='request_vs_actuals'"
    ).fetchall() == [(250000.0, 280494.0, 30494.0)]

    # Finding 4: entity_xwalk.recipient_uei uniqueness guard
    # The dbt unique test in schema.yml gates the build. To prove that a duplicate
    # UEI would double-count obligation totals (motivating the guard), verify the
    # fixture has exactly 1 row for UEI1 in entity_xwalk — no fan-out.
    assert con.sql(
        "select count(*) from entity_xwalk where recipient_uei='UEI1'"
    ).fetchone()[0] == 1, "entity_xwalk must have exactly 1 row per UEI (duplicate would double-count)"

    # ROADMAP #10 — the ABSENT half of the SAM extract's two states. make_lake
    # writes no data/parquet/sam/entities.parquet, which is every machine
    # today: the key that fills it is the owner's to mint. The mart must still
    # BUILD (dim_entities is a view and fct_influence refs it, so a hard read
    # of a missing parquet takes down the whole export, not one column), and
    # every sam_* column must be NULL rather than invented.
    assert not (tmp_path / "parquet" / "sam" / "entities.parquet").exists(), (
        "this case is only meaningful while the fixture lake has NO sam parquet"
    )
    sam_cols = [
        r[0] for r in con.sql("describe dim_entities").fetchall()
        if r[0].startswith("sam_")
    ]
    assert sam_cols == [
        "sam_uei", "sam_legal_business_name", "sam_cage_code",
        "sam_registration_status", "sam_registration_expiration_date",
        "sam_business_types", "sam_primary_naics", "sam_public_url",
        "sam_source_url", "sam_retrieved_at",
    ], sam_cols
    row = con.sql(
        "select dominant_registration_uei, sam_uei, sam_legal_business_name,"
        " sam_registration_status, sam_cage_code, sam_primary_naics,"
        " worst_confidence"
        " from dim_entities where family_key='ACME PARENT'"
    ).fetchone()
    # The dominant member's registration is still derived (it is what the SAM
    # extract will be keyed on); only the SAM answer is missing.
    assert row[0] == "PUEI1"
    assert row[1:6] == (None, None, None, None, None), row
    assert row[6] == "high", "an absent extract must not touch the tier"


def test_dim_entities_tolerates_a_zero_row_sam_parquet(tmp_path):
    """ROADMAP #10 — the third state, between absent and populated: the parquet
    EXISTS and holds no rows (`govbudget sam extract --schema-only`, or a run
    that was refused before it fetched anything). The LEFT JOIN must match
    nothing and null every sam_* column, not fail and not invent.
    """
    from govbudget.sam_entities import write_entities_parquet

    make_lake(tmp_path)
    (tmp_path / "duckdb").mkdir()
    out = write_entities_parquet([], tmp_path / "parquet" / "sam")
    assert out.exists()
    env = {
        **os.environ,
        "GOVBUDGET_DATA": str(tmp_path),
        "GOVBUDGET_DUCKDB": str(tmp_path / "duckdb" / "test.duckdb"),
    }
    result = subprocess.run(
        ["uv", "run", "dbt", "build", "--project-dir", "dbt", "--profiles-dir", "dbt",
         "--select", "+dim_entities"],
        cwd=ROOT, env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    con = duckdb.connect(str(tmp_path / "duckdb" / "test.duckdb"))
    try:
        assert con.sql("select count(*) from dim_entities").fetchone()[0] == 1
        assert con.sql(
            "select sam_uei, sam_legal_business_name, sam_registration_status"
            " from dim_entities where family_key='ACME PARENT'"
        ).fetchone() == (None, None, None)
    finally:
        con.close()


def test_dim_entities_carries_the_sam_registration_once_the_extract_has_run(tmp_path):
    """ROADMAP #10 — the PRESENT half. Same fixture lake, plus one SAM row for
    the dominant member's registration (PUEI1), written by the extract's OWN
    writer so the mart is read through the schema the extract produces.

    Scoped to `+dim_entities` (entity_xwalk, dim_entities and their assertions)
    — the full-lake build above already covers everything downstream, and the
    only thing this case adds is the join.
    """
    from govbudget.sam_entities import write_entities_parquet

    make_lake(tmp_path)
    (tmp_path / "duckdb").mkdir()
    write_entities_parquet(
        [
            {
                "sam_uei": "PUEI1",
                "legal_business_name": "ACME PARENT INCORPORATED",
                "cage_code": "9Z9Z9",
                "registration_status": "Active",
                "registration_expiration_date": "2027-01-31",
                "business_types": "For Profit Organization; Manufacturer of Goods",
                "primary_naics": "336411",
                "public_url": "https://sam.gov/entity/PUEI1",
                "source_url": "https://api.sam.gov/entity-information/v4/entities?ueiSAM=PUEI1",
                "retrieved_at": "2026-09-12T00:00:00+00:00",
                "response_sha256": "0" * 64,
            },
            # A registration nothing points at: the LEFT JOIN must ignore it
            # rather than add a family or duplicate one.
            {
                "sam_uei": "UNRELATED0001",
                "legal_business_name": "SOMEONE ELSE LLC",
                "cage_code": None,
                "registration_status": "Expired",
                "registration_expiration_date": None,
                "business_types": None,
                "primary_naics": None,
                "public_url": "https://sam.gov/entity/UNRELATED0001",
                "source_url": "https://api.sam.gov/entity-information/v4/entities?ueiSAM=UNRELATED0001",
                "retrieved_at": "2026-09-12T00:00:00+00:00",
                "response_sha256": "1" * 64,
            },
        ],
        tmp_path / "parquet" / "sam",
    )
    env = {
        **os.environ,
        "GOVBUDGET_DATA": str(tmp_path),
        "GOVBUDGET_DUCKDB": str(tmp_path / "duckdb" / "test.duckdb"),
    }
    result = subprocess.run(
        ["uv", "run", "dbt", "build", "--project-dir", "dbt", "--profiles-dir", "dbt",
         "--select", "+dim_entities"],
        cwd=ROOT, env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    con = duckdb.connect(str(tmp_path / "duckdb" / "test.duckdb"))
    try:
        assert con.sql("select count(*) from dim_entities").fetchone()[0] == 1, (
            "the SAM join must not add or fan out families"
        )
        row = con.sql(
            "select sam_uei, sam_legal_business_name, sam_cage_code,"
            " sam_registration_status, sam_registration_expiration_date,"
            " sam_business_types, sam_primary_naics, sam_public_url,"
            " sam_source_url, sam_retrieved_at, worst_confidence"
            " from dim_entities where family_key='ACME PARENT'"
        ).fetchone()
        assert row[:10] == (
            "PUEI1",
            "ACME PARENT INCORPORATED",
            "9Z9Z9",
            "Active",
            "2027-01-31",
            "For Profit Organization; Manufacturer of Goods",
            "336411",
            "https://sam.gov/entity/PUEI1",
            "https://api.sam.gov/entity-information/v4/entities?ueiSAM=PUEI1",
            "2026-09-12T00:00:00+00:00",
        ), row
        # display_name is still the registered string from the award lake, and
        # the tier is still the crosswalk's: SAM enriches, it never regrades.
        assert row[10] == "high"
        assert con.sql(
            "select display_name from dim_entities where family_key='ACME PARENT'"
        ).fetchone()[0] == "ACME PARENT INC"
    finally:
        con.close()


def test_entity_xwalk_duplicate_uei_would_double_count(tmp_path):
    """Prove that a duplicate recipient_uei in entity_xwalk fans-out obligation totals.

    This test documents WHY the dbt unique test matters: without the guard a
    single award joins twice, doubling the reported obligation.
    The test does NOT run dbt — it directly verifies the SQL fan-out behaviour.
    """
    import duckdb

    # Single award transaction: UEI1 → $1000
    con = duckdb.connect()
    con.execute(
        "create table awards as "
        "select 'UEI1' as recipient_uei, 1000.0 as obligation"
    )
    # Duplicate UEI in xwalk (two rows for same UEI1)
    con.execute(
        "create table xwalk_with_dup as "
        "select 'UEI1' as recipient_uei, 'FAM_A' as family_key union all "
        "select 'UEI1' as recipient_uei, 'FAM_A' as family_key"
    )
    # This join fans-out: 1 award × 2 xwalk rows = doubled total
    doubled = con.execute(
        "select sum(a.obligation) from awards a join xwalk_with_dup x "
        "on a.recipient_uei = x.recipient_uei"
    ).fetchone()[0]
    assert doubled == 2000.0, f"duplicate UEI causes double-count: got {doubled}"

    # With unique UEI (correct state): total is 1000
    con.execute(
        "create table xwalk_unique as "
        "select 'UEI1' as recipient_uei, 'FAM_A' as family_key"
    )
    correct = con.execute(
        "select sum(a.obligation) from awards a join xwalk_unique x "
        "on a.recipient_uei = x.recipient_uei"
    ).fetchone()[0]
    assert correct == 1000.0, f"unique UEI gives correct total: got {correct}"
    con.close()


def _singular_test_sql(name: str, **refs: str) -> str:
    """The committed dbt singular test's own SQL, with its {{ ref(...) }}
    macros replaced by plain table names so it can run against a throwaway
    DuckDB. Reading the real file (rather than restating the query here) is
    the point: the assertion this test exercises is the one dbt runs."""
    sql = (ROOT / "dbt" / "tests" / f"{name}.sql").read_text()
    for model, table in refs.items():
        sql = sql.replace("{{ ref('%s') }}" % model, table)
    assert "{{" not in sql, f"unsubstituted macro left in {name}.sql"
    return sql


def test_an_unresolvable_high_link_on_a_shared_code_is_caught_before_it_fuses():
    """ROADMAP #70 fix round 1, finding 4; narrowed by Task 27 (2026-09-19).

    Until Task 27 fct_district_programs grouped on (state, district, pe_bli)
    and took min() of the label columns, so a shared BLI code carrying HIGH
    links on BOTH members summed two programs' money into one district card
    under whichever title sorts first. The guard therefore fired on any shared
    code with two account keys — and on 2026-09-19 it did, for '0145'
    (1506N x5, 1508N x3).

    The model now carries the account, so two ACCOUNT-RESOLVED members no
    longer fuse: they are two rows. What an account grain still cannot
    separate is an account-NULL high link sitting beside an account-resolved
    one on the same shared code — the NULL names BOTH members, so its dollars
    belong to an unknown member while its sibling's are filed under a named
    one. That is the shape this assertion now returns.

    Like test_entity_xwalk_duplicate_uei_would_double_count, this does not run
    dbt: it runs the committed assertion against each configuration.
    """
    import duckdb

    con = duckdb.connect()
    con.execute(
        "create table links (pe_bli varchar, account varchar,"
        " confidence varchar, award_piid varchar)"
    )
    con.execute(
        "create table programs (pe_bli varchar, account varchar,"
        " account_title varchar, org varchar)"
    )
    # dim_programs' own shape for the two shared codes used below: '3010' is
    # split by ACCOUNT (1611N/1810N), '20' by ORGANIZATION (one account).
    con.execute(
        "insert into programs values"
        " ('3010','1611N','Shipbuilding and Conversion, Navy','N'),"
        " ('3010','1810N','Other Procurement, Navy','N'),"
        " ('20','0300D','Procurement, Defense-Wide','DCSA'),"
        " ('20','0300D','Procurement, Defense-Wide','DTRA'),"
        " ('0601101E',null,null,'DARPA')"
    )
    sql = _singular_test_sql(
        "assert_district_programs_single_member_high_links",
        fct_budget_to_awards="links",
        dim_programs="programs",
    )

    # The shape the OLD model fused and the new grain separates: '3010' high
    # on both members, each account-resolved. Two mart rows, two titles, two
    # fact_ids — nothing to announce.
    con.execute(
        "insert into links values"
        " ('3010','1611N','high','N0002420C0001'),"
        " ('3010','1810N','high','N0003917D0006')"
    )
    assert con.execute(sql).fetchall() == []

    # The MIXED shape (2026-09-04 final review, finding I7), which the account
    # grain does NOT resolve. An account-NULL high link names BOTH members of
    # a shared code — an overlay-raised `account+subagency` high row is
    # exactly that — so one beside an account-resolved high link on the same
    # pe_bli puts an unknown member's money on the page beside a named
    # member's. Returns (pe_bli, n_accounts, n_unresolved_links,
    # n_resolved_links, n_high_links).
    con.execute("delete from links")
    con.execute(
        "insert into links values"
        " ('3010','1611N','high','N0002420C0001'),"
        " ('3010',null,'high','N0003917D0006')"
    )
    mixed = con.execute(sql).fetchall()
    assert mixed == [("3010", 2, 1, 1, 2)], mixed

    # An ORDINARY code's account-NULL high links are not a shared code at all
    # — '0601101E' has one dim_programs row, so its NULL account names the one
    # program it always named and nothing is unresolved.
    con.execute("delete from links")
    con.execute(
        "insert into links values"
        " ('0601101E',null,'high','HR001124C0001'),"
        " ('0601101E',null,'high','HR001124C0002'),"
        " ('3010','1611N','high','N0002420C0001'),"
        " ('3010','1810N','medium','N0003917D0006')"
    )
    assert con.execute(sql).fetchall() == []
    con.close()


def test_two_members_of_a_shared_code_in_one_district_keep_their_own_rows():
    """Task 27: the account-qualified grain, run against the committed models.

    The fusion assert_district_programs_single_member_high_links announced on
    2026-09-19 is the day both members of one code earn high-confidence links
    whose awards land in the SAME district: the pre-Task-27 model grouped them
    into one row and labelled it min(program_title). Both district models now
    group on the account, so each member keeps its own row, its own title and
    its own dollars — and the two must move in lockstep, because
    assert_district_by_year_reconciles joins them on that grain.

    Like the guard test above, this does not run dbt: it runs the committed
    model SQL against a throwaway DuckDB.
    """
    import duckdb

    con = duckdb.connect()
    con.execute(
        "create table txns (transaction_key varchar, award_id_piid varchar,"
        " recipient_uei varchar, pop_state varchar, pop_district varchar,"
        " fiscal_year integer, obligation double)"
    )
    con.execute(
        "insert into txns values"
        " ('T1','N0002420C0001','UEI1','VA','VA-08',2025,900000.0),"
        " ('T2','N0003917D0006','UEI2','VA','VA-08',2025,100000.0),"
        " ('T3','HR001124C0001','UEI3','CA','CA-52',2025,800.25)"
    )
    con.execute(
        "create table links (award_piid varchar, pe_bli varchar,"
        " program_title varchar, organization varchar, account varchar,"
        " confidence varchar)"
    )
    con.execute(
        "insert into links values"
        " ('N0002420C0001','3010','LPD Flight II','N','1611N','high'),"
        " ('N0003917D0006','3010','Shipboard Tactical Communications','N',"
        "  '1810N','high'),"
        " ('HR001124C0001','0601101E','DEFENSE RESEARCH','DARPA',null,'high')"
    )
    rows = con.execute(
        "select pop_state, pop_district, pe_bli, account, program_title,"
        " total_obligation from (" + _model_sql(
            "fct_district_programs",
            fct_award_transactions="txns", fct_budget_to_awards="links",
        ) + ") order by pop_district, total_obligation desc"
    ).fetchall()
    assert rows == [
        ("CA", "CA-52", "0601101E", None, "DEFENSE RESEARCH", 800.25),
        ("VA", "VA-08", "3010", "1611N", "LPD Flight II", 900000.0),
        ("VA", "VA-08", "3010", "1810N",
         "Shipboard Tactical Communications", 100000.0),
    ], rows

    # The by-year sibling splits the same way, at the same grain plus the year.
    by_year = con.execute(
        "select pop_state, pop_district, pe_bli, account, fiscal_year,"
        " program_title, total_obligation from (" + _model_sql(
            "fct_district_programs_by_year",
            fct_award_transactions="txns", fct_budget_to_awards="links",
        ) + ") order by pop_district, total_obligation desc"
    ).fetchall()
    assert by_year == [
        ("CA", "CA-52", "0601101E", None, 2025, "DEFENSE RESEARCH", 800.25),
        ("VA", "VA-08", "3010", "1611N", 2025, "LPD Flight II", 900000.0),
        ("VA", "VA-08", "3010", "1810N", 2025,
         "Shipboard Tactical Communications", 100000.0),
    ], by_year
    con.close()


def _model_sql(name: str, **refs: str) -> str:
    """A committed mart model's own SQL with its `{{ ref(...) }}` macros
    replaced by plain table names, so it can run against a throwaway DuckDB.
    Same reasoning as _singular_test_sql: the assertion below exercises the
    SQL dbt actually builds, not a restatement of it."""
    sql = (ROOT / "dbt" / "models" / "marts" / f"{name}.sql").read_text()
    for model, table in refs.items():
        sql = sql.replace("{{ ref('%s') }}" % model, table)
    assert "{{" not in sql, f"unsubstituted macro left in {name}.sql"
    return sql


def test_high_only_index_is_withheld_over_zero_dollars_or_one_positive_family():
    """ROADMAP #80 fix round 1 (2026-09-11), findings 1 and 7.

    The first floor counted high-confidence AWARDS and LINKED FAMILIES and
    nothing else, so it published an index for two shapes that say nothing
    about a market:

      · every high link summing to zero (or negative) obligations. Each
        family's share_pct falls into the `else 0` branch, `sum(share*share)`
        is 0.0 — a number, not NULL — and the card headlined "Competitive"
        with $0 and a top contractor picked alphabetically by the tie-break.
        13 shipped programs, one of them headlining -$2,328,281.
      · two LINKED families where only one holds positive dollars: HHI 10,000
        (one family at 100% of the positive dollars) next to a card reading
        "Contractor Families: 2". 7 shipped programs.

    The floor now measures positive-dollar families and positive net program
    dollars, and withholds top_family_high with the index. Delete either
    clause from fct_program_concentration.sql and the corresponding case
    below publishes again.
    """
    import duckdb

    con = duckdb.connect()
    con.execute("create table tx (award_id_piid varchar, obligation double)")
    con.execute(
        "create table links (pe_bli varchar, award_piid varchar,"
        " confidence varchar, recipient_uei varchar, recipient_name varchar)"
    )
    con.execute("create table xwalk (recipient_uei varchar, family_key varchar)")
    con.execute(
        "insert into xwalk values ('U1','ALPHA'),('U2','BRAVO'),('U3','CHARLIE')"
    )

    con.execute(
        "insert into tx values"
        # CLEAR: two positive families over three awards
        " ('A1', 600.0), ('A2', 300.0), ('A3', 100.0),"
        # ZERO: three awards carrying no positive obligation at all
        " ('Z1', 0.0), ('Z2', 0.0), ('Z3', 0.0),"
        # ONEPOS: two linked families, only one with positive dollars
        " ('P1', 900.0), ('P2', 100.0), ('P3', 0.0),"
        # NEG: two positive families, net negative after a deobligation
        " ('N1', 100.0), ('N2', 50.0), ('N3', -500.0)"
    )
    con.execute(
        "insert into links values"
        " ('CLEAR','A1','high','U1','Alpha'),"
        " ('CLEAR','A2','high','U2','Bravo'),"
        " ('CLEAR','A3','high','U2','Bravo'),"
        " ('ZERO','Z1','high','U1','Alpha'),"
        " ('ZERO','Z2','high','U2','Bravo'),"
        " ('ZERO','Z3','high','U3','Charlie'),"
        " ('ONEPOS','P1','high','U1','Alpha'),"
        " ('ONEPOS','P2','high','U1','Alpha'),"
        " ('ONEPOS','P3','high','U2','Bravo'),"
        " ('NEG','N1','high','U1','Alpha'),"
        " ('NEG','N2','high','U2','Bravo'),"
        " ('NEG','N3','high','U2','Bravo')"
    )

    rows = {
        r[0]: r
        for r in con.execute(
            "select pe_bli, hhi_high, top_family_high, family_count_high,"
            " positive_family_count_high, award_count_high, program_dollars_high"
            " from ("
            + _model_sql(
                "fct_program_concentration",
                fct_award_transactions="tx",
                fct_budget_to_awards="links",
                entity_xwalk="xwalk",
            )
            + ")"
        ).fetchall()
    }
    con.close()

    # The control publishes: 3 awards, 2 positive families, $1,000 net.
    pe, hhi, top, fams, pos_fams, awards, dollars = rows["CLEAR"]
    assert hhi is not None and round(hhi, 6) == 5200.0, rows["CLEAR"]
    assert (top, fams, pos_fams, awards, dollars) == ("ALPHA", 2, 2, 3, 1000.0)

    # Zero dollars: counts are published, the index and the "leader" are not,
    # and program_dollars_high stays the true sum rather than going NULL
    # (NULL there means "no high link at all", a different fact).
    assert rows["ZERO"][1:] == (None, None, 3, 0, 3, 0.0), rows["ZERO"]

    # One positive family out of two linked ones.
    assert rows["ONEPOS"][1:] == (None, None, 2, 1, 3, 1000.0), rows["ONEPOS"]

    # Net negative dollars, two positive-share families.
    assert rows["NEG"][1:] == (None, None, 2, 2, 3, -350.0), rows["NEG"]
