"""Gate 2 indicators against the known answers in metric-dictionary-v0, section 7.

Fixtures A, B and D are synthetic; the SE3 test uses the real 27-29 July 2024 sample,
both from ``tests/fixtures`` and from the built screen file when it exists. Tolerance 1e-6.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from harmonise.resample import to_hourly
from metrics.gate2 import (
    capture,
    daily_change_std,
    daily_means,
    daily_spreads,
    min_valid_hours,
    negative_time,
    zone_year,
)

ROOT = Path(__file__).resolve().parents[1]
TOL = 1e-6


def _local_day(day: str, values, freq="h") -> pd.Series:
    """Values on one local (CET/CEST) delivery day, indexed in UTC."""
    start = pd.Timestamp(day, tz="Europe/Berlin")
    idx = pd.date_range(start, periods=len(values), freq=freq).tz_convert("UTC")
    return pd.Series(values, index=idx, dtype=float)


def _hourly_mtu(s: pd.Series, minutes: int = 60) -> pd.Series:
    return pd.Series(minutes, index=s.index)


# --------------------------------------------------------------------------- #
# Fixture A: one valid day (a summer Sunday)
# --------------------------------------------------------------------------- #
A_PRICE = [18.0, 15.5, 14.0, 12.0, 10.5, 8.0, 5.0, 2.0, 0.5, -1.5, -6.0, -3.5,
           0.0, 1.0, 4.0, 9.0, 16.0, 24.0, 32.0, 38.5, 35.0, 28.0, 22.0, 19.0]
A_SOLAR = [0, 0, 0, 0, 0, 10, 40, 90, 150, 200, 240, 260,
           260, 240, 200, 150, 90, 40, 10, 0, 0, 0, 0, 0]
A_WIND = [800, 820, 850, 870, 900, 950, 1000, 1050, 1100, 1150, 1180, 1200,
          1150, 1100, 1000, 900, 800, 700, 600, 550, 500, 520, 560, 600]
A_DAY = "2024-07-28"


@pytest.fixture
def fixture_a():
    return (_local_day(A_DAY, A_PRICE), _local_day(A_DAY, A_SOLAR), _local_day(A_DAY, A_WIND))


def test_fixture_a_price_level_and_hourly_std(fixture_a):
    price, _, _ = fixture_a
    assert price.mean() == pytest.approx(12.625, abs=TOL)
    assert price.std() == pytest.approx(12.550983, abs=TOL)


def test_fixture_a_negative_time(fixture_a):
    price, _, _ = fixture_a
    neg = negative_time(price, _hourly_mtu(price))
    assert neg["neg_hours_equiv_h"] == 3  # hour 12 is exactly 0.0 and does not count
    assert neg["neg_price_mean_eur_mwh"] == pytest.approx(-3.666667, abs=TOL)
    assert neg["neg_time_share_pct"] == pytest.approx(3 / 24 * 100, abs=TOL)


def test_fixture_a_spreads(fixture_a):
    price, _, _ = fixture_a
    spreads = daily_spreads(price, _hourly_mtu(price))
    assert len(spreads) == 1
    assert spreads["spread_2h"].iat[0] == pytest.approx(41.5, abs=TOL)
    assert spreads["spread_4h"].iat[0] == pytest.approx(36.125, abs=TOL)


def test_fixture_a_solar_capture(fixture_a):
    price, solar, _ = fixture_a
    c = capture(price, solar)
    assert c["capture_price"] == pytest.approx(1.512626, abs=TOL)
    assert c["capture_rate"] == pytest.approx(0.119812, abs=TOL)
    assert c["capture_rate_nonneg"] == pytest.approx(0.349319, abs=TOL)


def test_fixture_a_wind_capture(fixture_a):
    price, _, wind = fixture_a
    c = capture(price, wind)
    assert c["capture_price"] == pytest.approx(9.597122, abs=TOL)
    assert c["capture_rate"] == pytest.approx(0.760168, abs=TOL)
    assert c["capture_rate_nonneg"] == pytest.approx(0.974573, abs=TOL)


def test_capture_sets_negative_generation_to_zero(fixture_a):
    price, solar, _ = fixture_a
    night = solar.copy()
    night.iloc[0] = -3.0  # own use at night
    c = capture(price, night)
    assert c["n_neg_gen_fixed"] == 1
    assert c["capture_price"] == pytest.approx(1.512626, abs=TOL)


def test_negative_time_without_negative_prices_is_empty():
    price = _local_day(A_DAY, [5.0] * 24)
    assert np.isnan(negative_time(price, _hourly_mtu(price))["neg_price_mean_eur_mwh"])


# --------------------------------------------------------------------------- #
# Fixture B: day-to-day volatility
# --------------------------------------------------------------------------- #
B_DAYS = [dt.date(2024, 3, 4) + dt.timedelta(days=i) for i in range(4)]


def test_fixture_b_daily_change_std():
    std, n = daily_change_std(pd.Series([20.0, 35.0, 30.0, 12.0], index=B_DAYS))
    assert n == 3
    assert std == pytest.approx(16.623277, abs=TOL)


def test_fixture_b_invalid_day_breaks_the_chain():
    std, n = daily_change_std(pd.Series([20.0, 35.0, np.nan, 12.0], index=B_DAYS))
    assert n == 1
    assert np.isnan(std)  # one change left: empty, not 0


def test_daily_means_needs_every_hour():
    price = pd.concat([_local_day("2024-03-04", [10.0] * 24), _local_day("2024-03-05", [20.0] * 24)])
    price.iloc[30] = np.nan
    means = daily_means(price)
    assert means.iloc[0] == 10.0
    assert np.isnan(means.iloc[1])


# --------------------------------------------------------------------------- #
# Fixture D: 15-minute conversion and clock changes
# --------------------------------------------------------------------------- #
def test_fixture_d_to_hourly():
    idx = pd.date_range("2025-10-01 00:00", periods=8, freq="15min", tz="UTC")
    qh = pd.DataFrame({"price_eur_mwh": [40, 44, 52, 60, 40, np.nan, 52, 60]}, index=idx)
    hourly = to_hourly(qh, "mean", pd.Series(15, index=idx))["price_eur_mwh"]
    assert hourly.iloc[0] == pytest.approx(49.0, abs=TOL)
    assert np.isnan(hourly.iloc[1])  # not 50.67


def test_fixture_d_negative_time_on_quarter_hours():
    price = _local_day("2025-10-02", [-2.0, -6.0, 5.0, 7.0], freq="15min")
    neg = negative_time(price, _hourly_mtu(price, 15))
    assert neg["neg_hours_equiv_h"] == pytest.approx(0.5, abs=TOL)
    assert neg["neg_price_mean_eur_mwh"] == pytest.approx(-4.0, abs=TOL)
    assert price.mean() == pytest.approx(1.0, abs=TOL)  # an hourly count would see no negative hour


def test_fixture_d_quarter_hour_spread_uses_8_and_16_slots():
    values = np.arange(96, dtype=float)  # 0, 1, ..., 95
    price = _local_day("2025-10-02", values, freq="15min")
    spreads = daily_spreads(price, _hourly_mtu(price, 15))
    assert spreads["spread_2h"].iat[0] == pytest.approx(values[-8:].mean() - values[:8].mean(), abs=TOL)
    assert spreads["spread_4h"].iat[0] == pytest.approx(values[-16:].mean() - values[:16].mean(), abs=TOL)


@pytest.mark.parametrize("day, hours", [("2024-03-31", 23), ("2024-10-27", 25)])
def test_fixture_d_clock_change_days_are_valid(day, hours):
    start = pd.Timestamp(day, tz="Europe/Berlin").tz_convert("UTC")
    price = pd.Series(np.arange(hours, dtype=float), index=pd.date_range(start, periods=hours, freq="h"))
    assert daily_means(price).notna().all()
    assert len(daily_spreads(price, _hourly_mtu(price))) == 1
    assert daily_means(price.iloc[:-1]).isna().all()  # one hour short is not a valid day


def test_fixture_d_valid_year_thresholds():
    assert min_valid_hours(8784) == 8609
    assert min_valid_hours(8760) == 8585


# --------------------------------------------------------------------------- #
# SE3 2024 reference values (real data)
# --------------------------------------------------------------------------- #
SE3_EXPECTED = {
    "price_mean": 9.162083, "price_std_hourly": 14.292575, "std_daily_change": 13.043468,
    "neg_hours": 21, "neg_price_mean": -7.272381, "spread_2h": 29.478333, "spread_4h": 25.420833,
}
SE3_WINDOW = (pd.Timestamp("2024-07-26 22:00", tz="UTC"), pd.Timestamp("2024-07-29 21:00", tz="UTC"))


def _se3_check(price: pd.Series) -> None:
    assert len(price) == 72 and price.notna().all()
    mtu = _hourly_mtu(price)
    assert price.mean() == pytest.approx(SE3_EXPECTED["price_mean"], abs=TOL)
    assert price.std() == pytest.approx(SE3_EXPECTED["price_std_hourly"], abs=TOL)
    std, n = daily_change_std(daily_means(price))
    assert (std, n) == (pytest.approx(SE3_EXPECTED["std_daily_change"], abs=TOL), 2)
    neg = negative_time(price, mtu)
    assert neg["neg_hours_equiv_h"] == SE3_EXPECTED["neg_hours"]
    assert neg["neg_price_mean_eur_mwh"] == pytest.approx(SE3_EXPECTED["neg_price_mean"], abs=TOL)
    spreads = daily_spreads(price, mtu)
    assert len(spreads) == 3
    assert spreads["spread_2h"].mean() == pytest.approx(SE3_EXPECTED["spread_2h"], abs=TOL)
    assert spreads["spread_4h"].mean() == pytest.approx(SE3_EXPECTED["spread_4h"], abs=TOL)


def test_se3_reference_fixture_file():
    ref = pd.read_csv(ROOT / "tests/fixtures/se3_2024-07-27_29_entsoe.csv", parse_dates=["time_utc"])
    _se3_check(ref.set_index("time_utc")["price_eur_mwh"])


@pytest.mark.parametrize("folder", ["hourly", "native_prices"])
def test_se3_reference_built_screen_file(folder):
    path = ROOT / "data/processed/entsoe" / folder / "SE3.parquet"
    if not path.exists():
        pytest.skip("screen dataset not built (python -m harmonise.build_screen)")
    _se3_check(pd.read_parquet(path).loc[SE3_WINDOW[0]:SE3_WINDOW[1], "price_eur_mwh"])


# --------------------------------------------------------------------------- #
# One full zone-year row
# --------------------------------------------------------------------------- #
def test_zone_year_on_built_se3_2024():
    hourly_path = ROOT / "data/processed/entsoe/hourly/SE3.parquet"
    if not hourly_path.exists():
        pytest.skip("screen dataset not built (python -m harmonise.build_screen)")
    hourly = pd.read_parquet(hourly_path)
    native = pd.read_parquet(ROOT / "data/processed/entsoe/native_prices/SE3.parquet")
    row = zone_year(hourly, native, "SE3", 2024)
    assert row["expected_hours"] == 8784
    assert not row["flag_low_coverage"] and not row["flag_qh_source"]
    assert row["n_daily_changes"] == 365
    assert row["n_spread_days"] == 366
    # with only hourly prices in 2024, the native and hourly spreads must agree
    assert row["spread_2h_eur_mwh"] == pytest.approx(row["spread_2h_hourly_eur_mwh"], abs=TOL)
    assert 0 < row["capture_rate_wind_onshore_ratio"] < 1.2


def test_pl_2019_prices_converted_from_pln():
    """PL raw prices are PLN until delivery day 19 Nov 2019; the screen file must be EUR."""
    path = ROOT / "data/processed/entsoe/hourly/PL.parquet"
    if not path.exists():
        pytest.skip("screen dataset not built (python -m harmonise.build_screen)")
    price = pd.read_parquet(path)["price_eur_mwh"]
    before = price["2019-11-12 23:00":"2019-11-19 22:00"].mean()  # last PLN week, converted
    after = price["2019-11-19 23:00":"2019-11-26 22:00"].mean()   # first EUR week
    assert 30 < before < 80 and 30 < after < 80
    assert 30 < price["2018-12-31 23:00":"2019-12-31 22:00"].mean() < 80
