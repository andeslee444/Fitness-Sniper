"""scripts/fu/lake_parity.py — two lakes hold the same rows (follow-ups Task 21a)."""
import os
from urllib.parse import urlsplit, urlunsplit

import duckdb
import psycopg
import pytest

from fu.lake_parity import compare_pg, main, run  # scripts/ is on sys.path

ADMIN_DSN = os.environ.get("GOVBUDGET_TEST_PG_DSN", "postgresql://localhost/postgres")


def lake(root, rows, *, amounts=(0.1, 0.2, 0.3), schema="(code varchar, amount double)"):
    (root / "duckdb").mkdir(parents=True)
    (root / "parquet" / "jbooks").mkdir(parents=True)
    src = root / "parquet" / "jbooks" / "x.parquet"
    con = duckdb.connect()
    con.execute(f"create table t {schema}")
    con.executemany("insert into t values (?, ?)", rows)
    con.execute(f"copy t to '{src}' (format parquet)")
    con.close()
    con = duckdb.connect(str(root / "duckdb" / "govbudget.duckdb"))
    con.execute(f"create view v as select * from read_parquet('{src}')")
    con.execute("create table m as select sum(x) as total from (select unnest(?::double[]) as x)", [list(amounts)])
    con.close()
    return root


def test_equal_lakes_read_their_own_parquet_and_ignore_float_last_bits(tmp_path):
    a = lake(tmp_path / "a", [("O&M", 87404.0), ("0390DOM", 3243.0)])
    b = lake(tmp_path / "b", [("0390DOM", 3243.0), ("O&M", 87404.0)], amounts=(0.3, 0.2, 0.1))  # 0.6000000000000001 vs 0.6
    report = run(a, b, relations=["v", "m"], parquet=["jbooks/x.parquet"], work=tmp_path / "w")
    assert report["ok"], report
    assert report["relations"]["v"]["rows_a"] == 2


def test_a_moved_row_is_found_both_ways(tmp_path):
    a = lake(tmp_path / "a", [("O&M", 87404.0), ("RDT&E", 1002560.0)])
    b = lake(tmp_path / "b", [("0390DOM", 87404.0), ("RDT&E", 1002560.0)])
    report = run(a, b, relations=["v"], parquet=["jbooks/x.parquet"], work=tmp_path / "w")
    assert not report["ok"]
    assert (report["relations"]["v"]["a_not_b"], report["relations"]["v"]["b_not_a"]) == (1, 1)
    assert report["parquet"]["jbooks/x.parquet"]["samples_b_not_a"] == [{"code": "0390DOM", "amount": "87404.0"}]


def test_a_duplicate_row_is_a_difference(tmp_path):
    a = lake(tmp_path / "a", [("O&M", 1.0)])
    b = lake(tmp_path / "b", [("O&M", 1.0), ("O&M", 1.0)])
    assert run(a, b, relations=["v"], parquet=[], work=tmp_path / "w")["relations"]["v"]["b_not_a"] == 1


def test_a_schema_change_is_a_difference(tmp_path):
    a = lake(tmp_path / "a", [("O&M", 1.0)])
    b = lake(tmp_path / "b", [("O&M", 1)], schema="(code varchar, amount bigint)")
    assert run(a, b, relations=["v"], parquet=[], work=tmp_path / "w")["relations"]["v"]["schema_equal"] is False


def test_cli_verdicts_and_tool_errors(tmp_path, capsys):
    a = lake(tmp_path / "a", [("O&M", 1.0)])
    b = lake(tmp_path / "b", [("O&M", 1.0)])
    assert main(["--a", str(a), "--b", str(b), "--relation", "v", "--work", str(tmp_path / "w")]) == 0
    assert capsys.readouterr().out.strip().endswith("lake-parity: EQUAL")
    c = lake(tmp_path / "c", [("O&M", 2.0)])
    assert main(["--a", str(a), "--b", str(c), "--relation", "v", "--work", str(tmp_path / "w2")]) == 1
    assert capsys.readouterr().out.strip().endswith("lake-parity: DIFFERENT")
    assert main(["--a", str(a), "--b", str(b), "--relation", "nosuch", "--work", str(tmp_path / "w3")]) == 2
    assert "lake-parity: ERROR — " in capsys.readouterr().err
    assert main(["--a", str(a), "--b", str(a), "--relation", "v", "--work", str(tmp_path / "w4")]) == 2


@pytest.fixture
def two_dbs():
    try:
        admin = psycopg.connect(ADMIN_DSN, autocommit=True)
    except psycopg.OperationalError as e:
        pytest.skip(f"Postgres unavailable ({e})")
    names = ["govbudget_test_fu_parity_a", "govbudget_test_fu_parity_b"]
    dsns = []
    for name in names:
        admin.execute(f"drop database if exists {name}")
        admin.execute(f"create database {name}")
        dsn = urlunsplit(urlsplit(ADMIN_DSN)._replace(path="/" + name))
        with psycopg.connect(dsn, autocommit=True) as con:
            con.execute("create table budget_lines (id bigint primary key, account text, pe_bli text,"
                        " fiscal_year integer, amount_thousands numeric)")
        dsns.append(dsn)
    yield dsns
    for name in names:
        admin.execute(f"drop database if exists {name}")
    admin.close()


def test_postgres_rows_compare_without_ids(two_dbs):
    a, b = two_dbs
    with psycopg.connect(a, autocommit=True) as con:
        con.execute("insert into budget_lines values (47733, '0390D', '0390DOM', 2025, 84612),"
                    " (581202, '0390D', '0390DOM', 2026, 3243), (1, '3010F', 'F015EX', 2026, 1)")
    with psycopg.connect(b, autocommit=True) as con:
        con.execute("insert into budget_lines values (47733, '0390D', '0390DOM', 2025, 84612),"
                    " (581206, '0390D', '0390DOM', 2026, 3243), (1, '3010F', 'F015EX', 2026, 2)")
    report = compare_pg(a, b, "budget_lines", "account = '0390D'")
    assert report["ok"] and report["ids_equal"] is False
    assert (report["ids_a"], report["ids_b"]) == ([47733, 581202], [47733, 581206])
    with psycopg.connect(b, autocommit=True) as con:
        con.execute("update budget_lines set amount_thousands = 3244 where id = 581206")
    report = compare_pg(a, b, "budget_lines", "account = '0390D'")
    assert not report["ok"] and (report["a_not_b"], report["b_not_a"]) == (1, 1)
