"""Tests for the forward-price table (PW02-CD-02).

Run with ``pytest tests/test_forward_prices.py``. The tests build a small archive with the
collector's schema in a temporary folder, so no exchange data is stored in the repository.
The last test also runs on the real archive when ``FORWARD_PRICES_ARCHIVE`` points to it.
"""
from __future__ import annotations

import datetime as dt
import os
import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from metrics.forward_prices import (
    COLUMNS,
    DEFAULT_OUT_DIR,
    ForwardPriceError,
    build,
    default_evaluation_date,
    divergence,
    is_final_euronext,
    output_path,
    read_forward_prices,
    window_bounds,
)

E = dt.date(2026, 10, 23)          # a Friday
E_EARLIER = dt.date(2026, 10, 9)   # two weeks earlier
_ARCHIVE_COLUMNS = [
    "source", "trade_date", "contract_code", "bidding_zone", "zone_kind", "product",
    "maturity_type", "delivery_label", "delivery_start", "delivery_end",
    "settlement_price", "volume_mwh", "source_timestamp", "retrieved_at_utc",
]
_DELIVERY = {
    "Cal-2027": ("Year", "2027-01-01", "2027-12-31"),
    "Cal-2028": ("Year", "2028-01-01", "2028-12-31"),
    "Nov-2026": ("Month", "2026-11-01", "2026-11-30"),
    "Winter-2026": ("Season", "2026-10-01", "2027-03-31"),
}


def days(first: str, last: str) -> list[str]:
    return [d.date().isoformat() for d in pd.bdate_range(first, last)]


def row(trade_date, zone="DE", label="Cal-2027", price=100.0, *, source="EEX", kind="zonal",
        product="Base", code="DEBY", volume=8760.0, stamp="", retrieved=""):
    maturity, start, end = _DELIVERY[label]
    return {"source": source, "trade_date": trade_date, "contract_code": code,
            "bidding_zone": zone, "zone_kind": kind, "product": product,
            "maturity_type": maturity, "delivery_label": label, "delivery_start": start,
            "delivery_end": end, "settlement_price": price, "volume_mwh": volume,
            "source_timestamp": stamp, "retrieved_at_utc": retrieved}


def make_archive(path: Path, rows: list[dict], runs: list[tuple] | None = None) -> Path:
    """A small archive with the collector's schema; ``runs`` = (source, started_at_utc, status)."""
    db = path / "power_futures.sqlite"
    with sqlite3.connect(db) as conn:
        conn.execute(f"CREATE TABLE observations ({', '.join(_ARCHIVE_COLUMNS)})")
        conn.executemany(
            f"INSERT INTO observations VALUES ({', '.join('?' * len(_ARCHIVE_COLUMNS))})",
            [tuple(r[c] for c in _ARCHIVE_COLUMNS) for r in rows])
        if runs is not None:
            conn.execute("CREATE TABLE runs (source, started_at_utc, status, units_failed)")
            conn.executemany("INSERT INTO runs VALUES (?, ?, ?, 0)", runs)
    return db


def de_cal27(first="2026-08-03", last=None, price=lambda d: 100.0, **kw) -> list[dict]:
    return [row(d, price=price(d), **kw) for d in days(first, last or E.isoformat())]


def pick(table, zone="DE-LU", period="Cal-2027", method="avg_2m", product="base") -> pd.Series:
    hit = table[(table.zone == zone) & (table.delivery_period == period)
                & (table.method == method) & (table["product"] == product)]
    assert len(hit) == 1, hit
    return hit.iloc[0]


# --------------------------------------------------------------------------- #
# the window
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("e, first, n_weekdays", [
    ("2026-10-23", "2026-08-24", 45),
    ("2026-10-21", "2026-08-22", 43),   # the strike rule's example: 22 Aug-21 Oct, 43 weekdays
    ("2026-12-31", "2026-11-01", 44),   # month ends: (31 Oct, 31 Dec]
])
def test_window_is_two_calendar_months_ending_on_e(e, first, n_weekdays):
    lo, hi = window_bounds(dt.date.fromisoformat(e))
    assert (lo.isoformat(), hi.isoformat()) == (first, e)
    assert len(pd.bdate_range(lo, hi)) == n_weekdays


# --------------------------------------------------------------------------- #
# the two methods
# --------------------------------------------------------------------------- #
def test_average_uses_window_only_and_single_day_is_e(tmp_path):
    # 999 before the window must not leak in; E itself settles at 130.
    price = lambda d: 999.0 if d < "2026-08-24" else (130.0 if d == E.isoformat() else 100.0)
    t = build(make_archive(tmp_path, de_cal27(price=price)), E).table

    avg, single = pick(t), pick(t, method="single_day")
    assert avg.price_eur_mwh == pytest.approx((44 * 100 + 130) / 45, abs=1e-4)
    assert (avg.settlement_days_used, avg.settlement_days_expected) == (45, 45)
    assert (avg.window_first_date, avg.window_last_date) == ("2026-08-24", "2026-10-23")
    assert single.price_eur_mwh == 130.0 and single.settlement_days_used == 1
    assert not avg.flag_thin and avg.source == "EEX" and avg.source_contract == "DEBY"
    assert list(t.columns) == COLUMNS
    assert (t.evaluation_date == E.isoformat()).all()


def test_each_fixed_contract_is_its_own_row(tmp_path):
    # Grouping by curve position ("front year") would mix Cal-2027 and Cal-2028.
    rows = de_cal27() + [row(d, label="Cal-2028", price=80.0) for d in days("2026-08-03", E.isoformat())]
    t = build(make_archive(tmp_path, rows), E).table
    assert pick(t).price_eur_mwh == 100.0
    assert pick(t, period="Cal-2028").price_eur_mwh == 80.0


def test_only_contracts_not_yet_in_delivery(tmp_path):
    rows = de_cal27() + [row(d, label=lbl, code=c) for d in days("2026-08-24", E.isoformat())
                         for lbl, c in (("Nov-2026", "DEBM"), ("Winter-2026", "DEBS"))]
    periods = set(build(make_archive(tmp_path, rows), E).table.delivery_period)
    assert periods == {"Cal-2027", "Nov-2026"}   # Winter-2026 started on 1 Oct


def test_flags_missing_days_and_no_volume(tmp_path):
    gappy = [row(d, label="Cal-2028", volume=None) for d in days("2026-09-14", E.isoformat())]
    t = build(make_archive(tmp_path, de_cal27() + gappy), E).table
    thin = pick(t, period="Cal-2028")
    assert thin.flag_missing_days and thin.flag_no_volume and thin.flag_thin
    assert thin.settlement_days_used == 30 and thin.settlement_days_expected == 45
    assert pd.isna(thin.traded_volume_mwh)
    # flags describe the contract and are repeated on its single-day row
    assert pick(t, period="Cal-2028", method="single_day").flag_thin


# --------------------------------------------------------------------------- #
# sources and zones
# --------------------------------------------------------------------------- #
def euronext(d, zone, kind, code, price, stamp_time="15:59", stamp=None, retrieved=""):
    return row(d, zone=zone, kind=kind, code=code, price=price, source="EURONEXT",
               volume=None, stamp=f"{d}T{stamp_time}" if stamp is None else stamp,
               retrieved=retrieved)


def test_euronext_zone_is_system_plus_epad_and_only_where_eex_has_none(tmp_path):
    window = days("2026-08-24", E.isoformat())
    rows = de_cal27()
    rows += [euronext(d, "NORDIC", "system", "NSBY", 60.0) for d in window]
    rows += [euronext(d, "LT", "epad", "VIBY", 35.0) for d in window]          # EEX has no LT
    rows += [euronext(d, "SE3", "epad", "STBY", 5.0) for d in window]          # EEX has SE3
    rows += [row(d, zone="SE3", code="3SBY", price=70.0) for d in window]
    t = build(make_archive(tmp_path, rows), E).table

    lt = pick(t, zone="LT")
    assert lt.price_eur_mwh == 95.0 and lt.source == "EURONEXT" and lt.source_contract == "NSBY+VIBY"
    assert pd.isna(lt.flag_no_volume)          # Euronext publishes no volume: unknown, not "none"
    se3 = t[(t.zone == "SE3") & (t.method == "avg_2m")]
    assert len(se3) == 1 and se3.iloc[0].source == "EEX" and se3.iloc[0].price_eur_mwh == 70.0
    assert "NORDIC" not in set(t.zone)


def test_stale_euronext_readings_are_dropped(tmp_path):
    window = days("2026-08-24", E.isoformat())
    rows = de_cal27()
    rows += [euronext(d, "NORDIC", "system", "NSBY", 60.0) for d in window]
    # The last ten days were read in the morning and still carry the previous settlement.
    rows += [euronext(d, "LT", "epad", "VIBY", 35.0 if i < 35 else 999.0,
                      "15:59" if i < 35 else "11:10") for i, d in enumerate(window)]
    res = build(make_archive(tmp_path, rows), E)
    lt = pick(res.table, zone="LT")
    assert lt.price_eur_mwh == 95.0 and lt.settlement_days_used == 35 and lt.flag_missing_days
    assert res.euronext_stale_dropped == 10
    assert res.table[(res.table.zone == "LT") & (res.table.method == "single_day")].empty


@pytest.mark.parametrize("trade_date, stamp, final", [
    ("2026-10-23", "2026-10-23T15:59", True),
    ("2026-10-23", "2026-10-23T15:00", True),    # the cutoff itself counts
    ("2026-10-23", "2026-10-23T14:59", False),   # morning reading, previous settlement
    ("2026-10-23", "2026-10-22T15:59", False),   # yesterday's final price filed under today
    ("2026-10-23", "", False),                   # no stamp: cannot be judged
    ("2026-10-23", None, False),
])
def test_final_euronext_reading_needs_same_day_stamp_after_cutoff(trade_date, stamp, final):
    frame = pd.DataFrame({"trade_date": [trade_date], "source_timestamp": [stamp],
                          "retrieved_at_utc": [""]})
    assert is_final_euronext(frame).tolist() == [final]


@pytest.mark.parametrize("trade_date, retrieved_utc, final", [
    ("2026-09-22", "2026-09-22T18:26:22+00:00", True),    # 20:26 CEST, after settlement
    ("2026-09-22", "2026-09-22T13:05:00+00:00", True),    # 15:05 CEST: the cutoff is local time
    ("2026-09-22", "2026-09-22T12:30:00+00:00", False),   # 14:30 CEST, before the cutoff
    ("2026-09-18", "2026-09-19T22:29:44+00:00", True),    # read on a later day
    ("2026-09-22", "", False),                            # nothing to judge by
    ("2026-12-01", "2026-12-01T14:30:00+00:00", True),    # winter: 15:30 CET
])
def test_unstamped_reading_is_judged_by_retrieval_time(trade_date, retrieved_utc, final):
    frame = pd.DataFrame({"trade_date": [trade_date], "source_timestamp": [None],
                          "retrieved_at_utc": [retrieved_utc]})
    assert is_final_euronext(frame).tolist() == [final]


def test_a_stamp_is_never_overruled_by_retrieval_time():
    # Read in the evening, but the page still said 11:10: the stamp decides.
    frame = pd.DataFrame({"trade_date": ["2026-10-23"], "source_timestamp": ["2026-10-23T11:10"],
                          "retrieved_at_utc": ["2026-10-23T19:00:00+00:00"]})
    assert is_final_euronext(frame).tolist() == [False]


def test_unstamped_days_are_recovered_in_the_table(tmp_path):
    window = days("2026-08-24", E.isoformat())
    evening = lambda d: f"{d}T18:30:00+00:00"
    rows = de_cal27()
    rows += [euronext(d, "NORDIC", "system", "NSBY", 60.0, stamp="", retrieved=evening(d)) for d in window]
    rows += [euronext(d, "LT", "epad", "VIBY", 35.0, stamp="", retrieved=evening(d)) for d in window]
    res = build(make_archive(tmp_path, rows), E)
    assert pick(res.table, zone="LT").settlement_days_used == 45
    assert res.euronext_stale_dropped == 0


def test_euronext_reading_stamped_on_an_earlier_day_is_not_used(tmp_path):
    window = days("2026-08-24", E.isoformat())
    rows = de_cal27() + [euronext(d, "NORDIC", "system", "NSBY", 60.0) for d in window]
    # The last day carries the previous day's final settlement under today's trade date.
    rows += [euronext(d, "LT", "epad", "VIBY", 35.0 if d != E.isoformat() else 999.0,
                      stamp=f"{d}T15:59" if d != E.isoformat() else "2026-10-22T15:59")
             for d in window]
    res = build(make_archive(tmp_path, rows), E)
    lt = pick(res.table, zone="LT")
    assert lt.price_eur_mwh == 95.0 and lt.settlement_days_used == 44
    assert res.table[(res.table.zone == "LT") & (res.table.method == "single_day")].empty
    assert res.euronext_stale_dropped == 1


def test_stale_count_ignores_euronext_rows_for_contracts_eex_lists(tmp_path):
    window = days("2026-08-24", E.isoformat())
    rows = de_cal27()
    rows += [euronext(d, "NORDIC", "system", "NSBY", 60.0) for d in window]
    rows += [euronext(d, "LT", "epad", "VIBY", 35.0, "11:10" if i < 3 else "15:59")
             for i, d in enumerate(window)]
    # SE3 is on EEX, so its Euronext readings are never used, stale or not.
    rows += [row(d, zone="SE3", code="3SBY", price=70.0) for d in window]
    rows += [euronext(d, "SE3", "epad", "STBY", 5.0, "11:10") for d in window]
    res = build(make_archive(tmp_path, rows), E)
    assert res.euronext_stale_dropped == 3
    assert pick(res.table, zone="SE3").source == "EEX"


# --------------------------------------------------------------------------- #
# the run log
# --------------------------------------------------------------------------- #
def test_unrecovered_partial_run_stops_the_build(tmp_path):
    runs = [("EEX", "2026-10-20T18:30:00+00:00", "partial")]   # the last run of the window
    db = make_archive(tmp_path, de_cal27(), runs)
    with pytest.raises(ForwardPriceError, match="no later run recovered"):
        build(db, E)
    res = build(db, E, allow_problem_runs=True)
    assert res.problem_runs[0]["status"] == "partial" and res.problem_runs[0]["covered_by"] == ""


def test_partial_eex_run_recovered_by_a_later_run_is_only_reported(tmp_path):
    runs = [("EEX", "2026-10-01T18:30:00+00:00", "partial"),
            ("EEX", "2026-10-02T18:30:00+00:00", "ok")]
    res = build(make_archive(tmp_path, de_cal27(), runs), E)
    assert res.problem_runs == [{"source": "EEX", "started": "2026-10-01 20:30", "status": "partial",
                                 "units_failed": 0, "covered_by": "2026-10-02 20:30"}]


def test_failed_euronext_run_needs_a_same_day_run_after_the_cutoff(tmp_path):
    morning_fail = ("EURONEXT", "2026-10-13T05:07:00+00:00", "failed")     # 07:07 CEST
    afternoon_ok = ("EURONEXT", "2026-10-13T15:07:00+00:00", "ok")         # 17:07 CEST
    next_day_ok = ("EURONEXT", "2026-10-14T15:07:00+00:00", "ok")
    with pytest.raises(ForwardPriceError):
        build(make_archive(tmp_path, de_cal27(), [morning_fail, next_day_ok]), E)
    (tmp_path / "power_futures.sqlite").unlink()
    res = build(make_archive(tmp_path, de_cal27(), [morning_fail, afternoon_ok]), E)
    assert res.problem_runs[0]["covered_by"] == "2026-10-13 17:07"


def test_runs_outside_the_window_are_ignored(tmp_path):
    runs = [("EEX", "2026-07-01T18:30:00+00:00", "failed")]
    assert build(make_archive(tmp_path, de_cal27(), runs), E).problem_runs == []


def test_default_output_folder_is_in_the_repository_not_the_working_directory():
    assert DEFAULT_OUT_DIR.is_absolute()
    assert DEFAULT_OUT_DIR == Path(__file__).resolve().parents[1] / "data" / "processed" / "forward_prices"


def test_unknown_areas_are_left_out_and_reported(tmp_path):
    rows = de_cal27() + [row(d, zone="GB", code="GBBY") for d in days("2026-08-24", E.isoformat())]
    res = build(make_archive(tmp_path, rows), E)
    assert set(res.table.zone) == {"DE-LU"}
    assert res.skipped_areas == {"GB": 45}


def test_peak_kept_other_products_dropped(tmp_path):
    rows = de_cal27() + [row(d, product=p, code=c, price=110.0)
                         for d in days("2026-08-24", E.isoformat())
                         for p, c in (("Peak", "DEPY"), ("PeakMo-Su", "DEXY"))]
    t = build(make_archive(tmp_path, rows), E).table
    assert set(t["product"]) == {"base", "peak"}
    assert pick(t, product="peak").price_eur_mwh == 110.0


# --------------------------------------------------------------------------- #
# evaluation dates
# --------------------------------------------------------------------------- #
def test_rebuild_for_an_earlier_evaluation_date(tmp_path):
    # Prices rise one euro per trading day, so every window has its own known average.
    window_days = days("2026-08-03", E.isoformat())
    price = lambda d: 100.0 + window_days.index(d)
    db = make_archive(tmp_path, de_cal27(price=price))

    later, earlier = build(db, E), build(db, E_EARLIER)
    t = earlier.table
    assert (t.evaluation_date == E_EARLIER.isoformat()).all()
    expected_days = days("2026-08-10", E_EARLIER.isoformat())
    assert pick(t).price_eur_mwh == pytest.approx(sum(map(price, expected_days)) / len(expected_days))
    assert pick(t, method="single_day").price_eur_mwh == price(E_EARLIER.isoformat())
    assert pick(later.table).price_eur_mwh > pick(t).price_eur_mwh
    # the same archive and date always give the same table
    pd.testing.assert_frame_equal(t, build(db, E_EARLIER).table)

    out = output_path(tmp_path, E_EARLIER)
    assert out.name == "forward_prices_2026-10-09.csv"
    t.to_csv(out, index=False)
    assert len(read_forward_prices(out)) == len(t)


def test_default_evaluation_date_is_last_trading_day_before_run(tmp_path):
    db = make_archive(tmp_path, de_cal27())
    assert default_evaluation_date(db, today=dt.date(2026, 10, 25)) == E          # run on Sunday
    assert default_evaluation_date(db, today=E) == dt.date(2026, 10, 22)          # E not yet complete


def test_refuses_dates_without_settlements(tmp_path):
    db = make_archive(tmp_path, de_cal27())
    with pytest.raises(ForwardPriceError, match="weekend"):
        build(db, dt.date(2026, 10, 24))
    with pytest.raises(ForwardPriceError, match="no EEX settlements"):
        build(db, dt.date(2026, 10, 26))


def test_reader_refuses_a_table_mixing_evaluation_dates(tmp_path):
    db = make_archive(tmp_path, de_cal27())
    mixed = pd.concat([build(db, E).table, build(db, E_EARLIER).table])
    path = tmp_path / "mixed.csv"
    mixed.to_csv(path, index=False)
    with pytest.raises(ForwardPriceError, match="mixes evaluation dates"):
        read_forward_prices(path)


def test_divergence_lists_largest_relative_move_first(tmp_path):
    price = lambda d: 130.0 if d == E.isoformat() else 100.0
    rows = de_cal27(price=price) + [row(d, label="Cal-2028") for d in days("2026-08-03", E.isoformat())]
    div = divergence(build(make_archive(tmp_path, rows), E).table)
    assert list(div.delivery_period) == ["Cal-2027", "Cal-2028"]
    assert div.iloc[1].diff_pct == 0.0


# --------------------------------------------------------------------------- #
# the real archive (local only: the archive is never in the repository)
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not os.environ.get("FORWARD_PRICES_ARCHIVE"),
                    reason="set FORWARD_PRICES_ARCHIVE to the collector's power_futures.sqlite")
def test_real_archive_rebuilds_for_an_earlier_date():
    db = Path(os.environ["FORWARD_PRICES_ARCHIVE"])
    res = build(db, E_EARLIER)
    t = res.table
    assert (t.evaluation_date == E_EARLIER.isoformat()).all()
    assert t.price_eur_mwh.notna().all()
    assert not t.duplicated(["zone", "product", "delivery_period", "method"]).any()
    assert (t.delivery_start > E_EARLIER.isoformat()).all()
    for zone in ("SE3", "FI", "DK1", "DE-LU", "BE", "NL", "FR", "AT"):   # calibration + fixed set
        assert not t[(t.zone == zone) & (t.delivery_period == "Cal-2027")].empty, zone
    assert res.archive_gaps["EEX"] == []
