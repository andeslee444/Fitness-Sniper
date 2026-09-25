"""Layout regressions from public P-1/R-1/P-1R documents across services."""
from govbudget.budget_pdf_receipts import match_cell, normalize_header, wrapped_title
from govbudget.program_pdf_receipts import cost_row_match, reserve_match
from test_budget_pdf_receipts import procurement_page, row, word


def test_complete_wrapped_title_is_required():
    words = [word('Lower', 40, 140), word('Tier', 70, 140), word('Air', 40, 150), word('Defense', 60, 150), word('1', 10, 150), word('200', 320, 150, 350), word('2', 10, 175)]
    assert wrapped_title(words, 150, 14, 250, 175) == 'Lower Tier Air Defense'
    page = procurement_page(title='Air Defense')
    page['words'] += [word('Lower Tier', 40, 140)]
    assert match_cell(page, row(title='Air Defense'), 'FY 2024 Actuals Amount', 100, 'P-1') is None
    assert match_cell(page, row(title='Lower Tier Air Defense'), 'FY 2024 Actuals Amount', 100, 'P-1')


def test_army_account_is_supported_without_cross_service_alias():
    page = procurement_page()
    page['text'] = 'Department of the Army\nAppropriation: 2031A'
    assert match_cell(page, row(account='2031A'), 'FY 2024 Actuals Amount', 100, 'P-1')
    assert match_cell(page, row(), 'FY 2024 Actuals Amount', 100, 'P-1') is None


def test_public_classified_aggregate_sentinel_is_tightly_scoped():
    page = procurement_page()
    page['words'] = [word('No', 10, 120), word('Act', 270, 120), word('999', 10, 160), word('999999999', 40, 160), word('Classified Programs', 90, 160), word('02', 270, 160), word('100', 320, 160, 350)]
    page['_columns'] = {'R-1': [dict(header='FY 2024 Actuals', normalized=normalize_header('FY 2024 Actuals'), edge=350, body_top=130)]}
    record = row(line='999', code='9999999999', title='Classified Programs', activity='02')
    assert match_cell(page, record, 'FY 2024 Actuals Amount', 100, 'R-1')
    assert match_cell(page, record | {'code': '9999999998'}, 'FY 2024 Actuals Amount', 100, 'R-1') is None
    assert match_cell(page, record | {'activity': '03'}, 'FY 2024 Actuals Amount', 100, 'R-1') is None


def reserve_page(number, words, previous=None):
    return dict(page_number=number, accounts=['2034A'], width=792, height=612,
                words=[word('Sec', 281, 120)] + words, _previous=previous,
                _columns={'P-1R': [dict(header='FY 2026 Disc Request', normalized=normalize_header('FY 2026 Disc Request'), edge=450, body_top=140)]})


def test_reserve_activity_can_span_several_verified_pages_and_title_can_wrap():
    first = reserve_page(1, [word('Budget', 35.8, 165), word('Activity', 70, 165), word('01:', 115, 165)])
    second = reserve_page(2, [], first)
    third = reserve_page(3, [word('Signals,', 35.8, 200), word('All Types', 35.8, 210), word('National', 64, 235), word('Guard', 110, 235), word('100', 430, 235, 450), word('Reserve', 64, 250), word('20', 440, 250, 450)], second)
    record = row(account='2034A', activity='01', title='Signals, All Types', cost_type='T')
    assert reserve_match(third, record, 'FY 2026 Request Amount', 100, 2026)['word']['text'] == '100'
    assert reserve_match(third, record | {'title': 'Signals'}, 'FY 2026 Request Amount', 100, 2026) is None
    assert reserve_match(third, record | {'activity': '02'}, 'FY 2026 Request Amount', 100, 2026) is None
    assert reserve_match(third, record | {'cost_type': 'R'}, 'FY 2026 Request Amount', 100, 2026) is None
    assert reserve_match(third, record | {'cost_type': 'R'}, 'FY 2026 Request Amount', 20, 2026)
    third['_previous'] = None
    assert reserve_match(third, record, 'FY 2026 Request Amount', 100, 2026) is None


def test_reserve_component_continues_after_title_on_previous_page():
    first = reserve_page(1, [word('Budget', 35.8, 165), word('Activity', 70, 165), word('01:', 115, 165), word('Simulators, All Types', 35.8, 550)])
    second = reserve_page(2, [word('Reserve', 64, 170), word('20', 440, 170, 450), word('Different Program', 35.8, 200), word('Reserve', 64, 230), word('20', 440, 230, 450)], first)
    record = row(account='2034A', activity='01', title='Simulators, All Types', cost_type='R')
    match = reserve_match(second, record, 'FY 2026 Request Amount', 20, 2026)
    assert match['word']['top'] == 170
    assert match['identity_page_number'] == 1


def test_shipbuilding_label_does_not_include_earlier_fiscal_columns():
    page = procurement_page(title='CVN-81')
    page['words'] += [word('Subsequent Full Funding for FY 2020', 49.9, 168), word('100', 320, 168, 350), word('200', 430, 168, 450)]
    record = row(title='CVN-81', cost_type='L', row_label='Subsequent Full Funding for FY 2020')
    assert cost_row_match(page, record, 'FY 2025 Enacted Amount', 200, 2026)['word']['x1'] == 450
    assert cost_row_match(page, record | {'row_label': 'Subsequent Full Funding for FY 2021'}, 'FY 2025 Enacted Amount', 200, 2026) is None


def test_reserve_continuation_stops_at_new_activity():
    first = reserve_page(1, [word('Budget', 35.8, 165), word('Activity', 70, 165), word('01:', 115, 165), word('Simulators, All Types', 35.8, 550)])
    second = reserve_page(2, [word('Budget', 35.8, 155), word('Activity', 70, 155), word('02:', 115, 155), word('Reserve', 64, 180), word('20', 440, 180, 450)], first)
    record = row(account='2034A', activity='01', title='Simulators, All Types', cost_type='R')
    assert reserve_match(second, record, 'FY 2026 Request Amount', 20, 2026) is None


def test_rdte_activity_must_be_in_its_column():
    page = procurement_page()
    page['words'] = [word('No', 10, 120), word('Act', 270, 120), word('1', 10, 160), word('0601102A', 40, 160), word('Project', 90, 160), word('02', 125, 160), word('03', 270, 160), word('100', 320, 160, 350)]
    page['_columns'] = {'R-1': [dict(header='FY 2024 Actuals', normalized=normalize_header('FY 2024 Actuals'), edge=350, body_top=130)]}
    record = row(code='0601102A', title='Project 02', activity='02')
    assert match_cell(page, record, 'FY 2024 Actuals Amount', 100, 'R-1') is None
    assert match_cell(page, record | {'activity': '03'}, 'FY 2024 Actuals Amount', 100, 'R-1')
