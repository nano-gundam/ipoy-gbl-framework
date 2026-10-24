"""Unit tests for the harmonise package (PW01-CD-04).

Run with ``pytest tests/test_harmonise.py``. These tests build their own small inputs and
need no downloaded data, except the end-to-end tests at the bottom, which skip when
``data/raw/entsoe`` is absent.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from harmonise.adapters import AdapterError, DataWarning, from_entsoe
from harmonise.clock import (
    ClockError,
    delivery_day,
    expected_slots,
    hours_in_day,
    local_to_utc,
)
from harmonise.currency import CurrencyError, assert_eur, to_eur
from harmonise.pipeline import combine, harmonise, harmonise_file
from harmonise.resample import StepError, daily_coverage, infer_mtu_minutes, to_hourly
from harmonise.zones import UnknownZoneError, resolve_zone, zone_info

SPRING_2025 = dt.date(2025, 3, 30)  # 23-hour day
AUTUMN_2025 = dt.date(2025, 10, 26)  # 25-hour day


# --------------------------------------------------------------------------- #
# zones
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("code, expected", [
    ("SE_3", "SE3"),               # ENTSO-E folder name
    ("SE3", "SE3"),                # short name itself
    ("se3", "SE3"),                # case does not matter
    ("10Y1001A1001A46L", "SE3"),   # EIC code
    ("DE_LU", "DE-LU"),
    ("DE", "DE-LU"),               # EEX / futures-collector alias (the known trap)
    ("IE_SEM", "IE-SEM"),
    ("IT_NORD", "IT-NORD"),        # Italian, Norwegian and Greek zones (added 24 Oct)
    ("NO_2", "NO2"),
    ("10Y1001A1001A48H", "NO5"),
    ("GR", "GR"),
])
def test_resolve_zone_accepts_every_spelling(code, expected):
    assert resolve_zone(code) == expected


def test_unknown_zone_raises():
    with pytest.raises(UnknownZoneError):
        resolve_zone("XX_9")


def test_zone_info_has_local_tz():
    assert zone_info("SE_3")["local_tz"] == "Europe/Stockholm"


# --------------------------------------------------------------------------- #
# clock
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("day, hours, quarters", [
    (SPRING_2025, 23, 92),
    (AUTUMN_2025, 25, 100),
    (dt.date(2025, 6, 1), 24, 96),
])
def test_day_length_is_dst_aware(day, hours, quarters):
    assert hours_in_day(day) == hours
    assert expected_slots(day, 15) == quarters
    assert expected_slots(day, 60) == hours


def test_local_to_utc_23_hour_day():
    # A local source on the spring day: 02:00 is skipped by the clock.
    local = pd.date_range("2025-03-30 00:00", periods=23, freq="h")  # naive
    local = local[local.hour != 2].append(pd.DatetimeIndex(["2025-03-31 00:00"]))
    utc = local_to_utc(local, "Europe/Berlin")
    assert utc[0] == pd.Timestamp("2025-03-29 23:00", tz="UTC")  # 00:00 CET = 23:00 UTC
    assert utc[2] == pd.Timestamp("2025-03-30 01:00", tz="UTC")  # 03:00 CEST = 01:00 UTC
    assert utc.is_unique and utc.is_monotonic_increasing


def test_local_to_utc_rejects_nonexistent_hour():
    with pytest.raises(ClockError):
        local_to_utc(pd.DatetimeIndex(["2025-03-30 02:30"]), "Europe/Berlin")


def test_local_to_utc_25_hour_day():
    # The source repeats 02:00 local: first summer time, then winter time.
    hours = [0, 1, 2, 2, *range(3, 24)]
    local = pd.DatetimeIndex([pd.Timestamp("2025-10-26") + pd.Timedelta(hours=h) for h in hours])
    utc = local_to_utc(local, "Europe/Berlin")
    assert len(utc) == 25 and utc.is_unique
    assert list(utc[2:4]) == [pd.Timestamp("2025-10-26 00:00", tz="UTC"), pd.Timestamp("2025-10-26 01:00", tz="UTC")]


def test_local_to_utc_rejects_unpaired_repeated_hour():
    with pytest.raises(ClockError):
        local_to_utc(pd.DatetimeIndex(["2025-10-26 02:00", "2025-10-26 03:00"]), "Europe/Berlin")


def test_delivery_day_uses_market_time():
    # 23:30 UTC on 31 Jan is already 00:30 on 1 Feb in Berlin (CET = UTC+1).
    days = delivery_day(pd.DatetimeIndex(["2025-01-31 22:30", "2025-01-31 23:30"], tz="UTC"))
    assert list(days) == [dt.date(2025, 1, 31), dt.date(2025, 2, 1)]


# --------------------------------------------------------------------------- #
# resample: step detection and hourly aggregation
# --------------------------------------------------------------------------- #
def utc_range(start: str, periods: int, minutes: int) -> pd.DatetimeIndex:
    return pd.date_range(start, periods=periods, freq=f"{minutes}min", tz="UTC")


def test_infer_mtu_handles_the_sdac_switch():
    idx = utc_range("2025-09-30 18:00", 4, 60).append(utc_range("2025-09-30 22:00", 8, 15))
    assert infer_mtu_minutes(idx).tolist() == [60] * 4 + [15] * 8


def test_infer_mtu_treats_a_single_missing_slot_as_a_gap():
    idx = utc_range("2024-01-01", 12, 15).delete(5)  # one quarter-hour missing
    assert set(infer_mtu_minutes(idx)) == {15}


def test_infer_mtu_rejects_irregular_timestamps():
    with pytest.raises(StepError):
        infer_mtu_minutes(pd.DatetimeIndex(["2024-01-01 00:00", "2024-01-01 00:07", "2024-01-01 00:50"], tz="UTC"))


def test_15_to_60_mean_for_prices_and_sum_for_energy():
    idx = utc_range("2025-11-01", 8, 15)
    raw = pd.DataFrame({"price_eur_mwh": [10, 20, 30, 40, 0, 0, 0, 100.0]}, index=idx)
    mean = to_hourly(raw, "mean")
    assert mean["price_eur_mwh"].tolist() == [25.0, 25.0]
    energy = pd.DataFrame({"energy_mwh": [1, 2, 3, 4, 5, 5, 5, 5.0]}, index=idx)
    assert to_hourly(energy, "sum")["energy_mwh"].tolist() == [10.0, 20.0]


def test_hourly_input_passes_through_unchanged():
    idx = utc_range("2024-06-01", 24, 60)
    raw = pd.DataFrame({"load_mw": np.arange(24, dtype=float)}, index=idx)
    out = to_hourly(raw, "mean")
    assert out["load_mw"].tolist() == raw["load_mw"].tolist()
    assert out.index.equals(raw.index.rename("timestamp_utc"))


def test_partly_covered_hour_becomes_nan():
    idx = utc_range("2025-11-01", 8, 15)
    raw = pd.DataFrame({"price_eur_mwh": [10, 20, np.nan, 40, 1, 2, 3, 4.0]}, index=idx)
    out = to_hourly(raw, "mean")
    assert np.isnan(out["price_eur_mwh"].iloc[0])  # 3 of 4 quarters is not averaged
    assert out["price_eur_mwh"].iloc[1] == 2.5


def test_23_and_25_hour_days_survive_aggregation():
    # One whole market-time delivery day of 15-minute data, each day in UTC.
    for day, start_utc, hours in ((SPRING_2025, "2025-03-29 23:00", 23), (AUTUMN_2025, "2025-10-25 22:00", 25)):
        idx = utc_range(start_utc, hours * 4, 15)
        raw = pd.DataFrame({"load_mw": 1000.0}, index=idx)
        out = to_hourly(raw, "mean")
        assert len(out) == hours
        assert set(delivery_day(out.index)) == {day}
        assert daily_coverage(out, "load_mw").loc[day, "missing_hours"] == 0


def test_missing_day_stays_missing():
    idx = utc_range("2024-03-03 23:00", 3 * 24, 60)  # 4, 5, 6 March in CET
    raw = pd.DataFrame({"load_mw": 500.0}, index=idx)
    raw = raw[delivery_day(raw.index) != dt.date(2024, 3, 5)]  # drop the middle day
    out = to_hourly(raw, "mean")
    assert len(out) == 72  # the hourly grid is complete...
    assert out["load_mw"].isna().sum() == 24  # ...but the missing day is NaN, not filled
    cov = daily_coverage(out, "load_mw")
    assert cov.loc[dt.date(2024, 3, 5), "missing_hours"] == 24
    assert cov.loc[dt.date(2024, 3, 4), "missing_hours"] == 0


def test_to_hourly_rejects_non_utc_index():
    raw = pd.DataFrame({"load_mw": [1.0, 2.0]}, index=pd.date_range("2024-01-01", periods=2, freq="h"))
    with pytest.raises(StepError):
        to_hourly(raw, "mean")


# --------------------------------------------------------------------------- #
# currency
# --------------------------------------------------------------------------- #
GBP_RATES = pd.Series({"2025-01-02": 0.80, "2025-01-03": 0.82, "2025-01-06": 0.84})  # Fri 3 Jan, Mon 6 Jan


def test_eur_is_the_identity():
    prices = pd.Series([50.0, 60.0], index=utc_range("2025-01-03", 2, 60))
    eur, fx = to_eur(prices, "EUR")
    assert eur.tolist() == [50.0, 60.0] and fx.tolist() == [1.0, 1.0]


@pytest.mark.parametrize("currency", ["GBP", "NOK", "PLN", "CZK", "HUF"])
def test_non_eur_without_rates_is_refused(currency):
    prices = pd.Series([50.0], index=utc_range("2025-01-03", 1, 60))
    with pytest.raises(CurrencyError):
        to_eur(prices, currency)


def test_weekend_uses_fridays_rate_never_mondays():
    # Sat 4 Jan and Sun 5 Jan 2025 (market time) have no ECB rate: Friday's 0.82 applies.
    prices = pd.Series(82.0, index=pd.DatetimeIndex(["2025-01-03 12:00", "2025-01-04 12:00", "2025-01-05 12:00",
                                                     "2025-01-06 12:00"], tz="UTC"))
    eur, fx = to_eur(prices, "GBP", GBP_RATES)
    assert fx.tolist() == [0.82, 0.82, 0.82, 0.84]
    assert eur.iloc[0] == pytest.approx(100.0)


def test_delivery_day_not_utc_day_picks_the_rate():
    # 23:30 UTC on Thu 2 Jan is delivery day Fri 3 Jan in market time -> Friday's rate.
    prices = pd.Series([82.0], index=pd.DatetimeIndex(["2025-01-02 23:30"], tz="UTC"))
    assert to_eur(prices, "GBP", GBP_RATES)[1].iloc[0] == 0.82


def test_rate_from_the_future_or_stale_is_refused():
    early = pd.Series([50.0], index=utc_range("2025-01-01 06:00", 1, 60))  # before the first rate
    with pytest.raises(CurrencyError):
        to_eur(early, "GBP", GBP_RATES)
    late = pd.Series([50.0], index=utc_range("2025-03-01", 1, 60))  # table ends in January
    with pytest.raises(CurrencyError):
        to_eur(late, "GBP", GBP_RATES)


def test_assert_eur_refuses_unconverted_price_column():
    with pytest.raises(CurrencyError):
        assert_eur(pd.DataFrame({"price_gbp_mwh": [1.0]}))
    assert_eur(pd.DataFrame({"price_gbp_mwh": [1.0], "price_eur_mwh": [1.2]}))  # converted: fine
    assert_eur(pd.DataFrame({"load_mw": [1.0]}))  # no price at all: fine


# --------------------------------------------------------------------------- #
# adapters: ENTSO-E raw layouts
# --------------------------------------------------------------------------- #
def test_price_and_load_columns_are_renamed_with_units():
    idx = utc_range("2024-01-01", 2, 60)
    assert list(from_entsoe(pd.DataFrame({"value": [1.0, 2.0]}, index=idx), "day_ahead_prices").columns) == [
        "price_eur_mwh"]
    assert list(from_entsoe(pd.DataFrame({"Actual Load": [1.0, 2.0]}, index=idx), "total_load").columns) == [
        "load_mw"]


def test_generation_merges_the_three_spellings():
    # Mirrors DE_LU/2025: Jan-Jun as a string-of-tuple column, Jul-Dec as a flat column.
    idx = utc_range("2025-06-30 23:00", 4, 60)
    raw = pd.DataFrame({
        "('Solar', 'Actual Aggregated')": [5.0, 6.0, np.nan, np.nan],
        "('Solar', 'Actual Consumption')": [0.0, 0.0, np.nan, np.nan],
        "Solar": [np.nan, np.nan, 7.0, 8.0],
    }, index=idx)
    out = from_entsoe(raw, "solar_generation")
    assert list(out.columns) == ["gen_solar_mw"]
    assert out["gen_solar_mw"].tolist() == [5.0, 6.0, 7.0, 8.0]


def test_generation_reads_real_two_level_columns():
    idx = utc_range("2024-01-01", 2, 60)
    raw = pd.DataFrame({("Wind Onshore", "Actual Aggregated"): [1.0, 2.0],
                        ("Wind Onshore", "Actual Consumption"): [0.0, 0.0]}, index=idx)
    assert from_entsoe(raw, "wind_generation")["gen_wind_onshore_mw"].tolist() == [1.0, 2.0]


def test_generation_refuses_conflicting_columns():
    idx = utc_range("2024-01-01", 2, 60)
    raw = pd.DataFrame({"Solar": [1.0, 2.0], "('Solar', 'Actual Aggregated')": [1.0, 9.0]}, index=idx)
    with pytest.raises(AdapterError):
        from_entsoe(raw, "solar_generation")


def test_nonzero_self_consumption_is_reported_not_dropped_silently():
    idx = utc_range("2024-01-01", 2, 60)
    raw = pd.DataFrame({"Wind Onshore": [1.0, np.nan], "('Wind Onshore', 'Actual Consumption')": [np.nan, 850.0]},
                       index=idx)
    with pytest.warns(DataWarning):
        from_entsoe(raw, "wind_generation")


def test_unexpected_raw_columns_are_refused():
    with pytest.raises(AdapterError):
        from_entsoe(pd.DataFrame({"price": [1.0]}, index=utc_range("2024-01-01", 1, 60)), "day_ahead_prices")
    with pytest.raises(KeyError):
        from_entsoe(pd.DataFrame({"value": [1.0]}), "imbalance_prices")


# --------------------------------------------------------------------------- #
# pipeline: one call, same shape for every zone
# --------------------------------------------------------------------------- #
PRICE_COLUMNS = ["zone", "price_eur_mwh", "mtu_minutes", "currency_original", "fx_rate_eur", "source",
                 "retrieved_at_utc", "schema_version"]


def test_harmonise_15_minute_prices_to_hourly():
    raw = pd.DataFrame({"value": [10, 20, 30, 40, 50, 50, 50, 50.0]}, index=utc_range("2025-11-03", 8, 15))
    out = harmonise(raw, "day_ahead_prices", "DE_LU")
    assert list(out.columns) == PRICE_COLUMNS
    assert out["zone"].unique().tolist() == ["DE-LU"]
    assert out["price_eur_mwh"].tolist() == [25.0, 50.0]
    assert out.attrs["unit"] == "EUR/MWh" and out.attrs["series"] == "day_ahead_prices"


def test_harmonise_converts_gbp_only_with_rates():
    raw = pd.DataFrame({"value": [82.0] * 4}, index=utc_range("2025-01-03 10:00", 4, 60))
    with pytest.raises(CurrencyError):
        harmonise(raw, "day_ahead_prices", "DE_LU", currency="GBP")
    out = harmonise(raw, "day_ahead_prices", "DE_LU", currency="GBP", fx_rates=GBP_RATES)
    assert out["price_eur_mwh"].round(6).tolist() == [100.0] * 4
    assert out["price_gbp_mwh"].tolist() == [82.0] * 4  # original kept next to the converted value
    assert out["currency_original"].unique().tolist() == ["GBP"]


def test_harmonise_load_has_no_currency_columns():
    raw = pd.DataFrame({"Actual Load": [1000.0] * 8}, index=utc_range("2024-01-01", 8, 15))
    out = harmonise(raw, "total_load", "SE_3")
    assert list(out.columns) == ["zone", "load_mw", "mtu_minutes", "source", "retrieved_at_utc", "schema_version"]
    with pytest.raises(CurrencyError):
        harmonise(raw, "total_load", "SE_3", currency="SEK")


def test_harmonise_local_time_source_needs_local_tz():
    raw = pd.DataFrame({"value": [1.0] * 6}, index=pd.date_range("2025-06-01 00:00", periods=6, freq="h"))
    with pytest.raises(ValueError):
        harmonise(raw, "day_ahead_prices", "SE3")
    out = harmonise(raw, "day_ahead_prices", "SE3", local_tz="Europe/Stockholm")
    assert out.index[0] == pd.Timestamp("2025-05-31 22:00", tz="UTC")  # 00:00 CEST


def test_combine_refuses_mixed_series():
    idx = utc_range("2024-01-01", 4, 60)
    price = harmonise(pd.DataFrame({"value": [1.0] * 4}, index=idx), "day_ahead_prices", "SE3")
    load = harmonise(pd.DataFrame({"Actual Load": [1.0] * 4}, index=idx), "total_load", "SE3")
    assert len(combine([price, price.assign(zone="SE4")])) == 8
    with pytest.raises(ValueError):
        combine([price, load])


def test_year_fills_the_whole_year_so_missing_months_show():
    # Like IE-SEM solar 2024: data only from mid-November.
    raw = pd.DataFrame({"Solar": 0.0}, index=utc_range("2024-11-13 17:00", 24 * 10, 60))
    out = harmonise(raw, "solar_generation", "IE_SEM", year=2024)
    assert len(out) == 8784  # every hour of 2024
    assert out.index[0] == pd.Timestamp("2024-01-01", tz="UTC")
    assert out["gen_solar_mw"].isna().sum() == 8784 - 240  # Jan to mid-Nov is empty, not hidden


def test_year_refuses_rows_outside_that_year():
    raw = pd.DataFrame({"value": [1.0] * 4}, index=utc_range("2024-12-31 22:00", 4, 60))
    with pytest.raises(StepError):
        harmonise(raw, "day_ahead_prices", "SE3", year=2024)


def test_year_downloaded_mid_year_is_expected_only_until_download():
    raw = pd.DataFrame({"value": [1.0] * 48}, index=utc_range("2026-01-01", 48, 60))
    out = harmonise(raw, "day_ahead_prices", "SE3", year=2026, retrieved_at_utc="2026-01-03 05:30")
    assert out.index[-1] == pd.Timestamp("2026-01-03 04:00", tz="UTC")  # up to the download hour
    assert out["price_eur_mwh"].isna().sum() == 5


def test_without_year_output_spans_first_to_last_hour():
    raw = pd.DataFrame({"value": [1.0] * 4}, index=utc_range("2024-06-01", 4, 60))
    assert len(harmonise(raw, "day_ahead_prices", "SE3")) == 4


# --------------------------------------------------------------------------- #
# end to end on real ENTSO-E files + Devika's acceptance checks (PW01-MV-02)
# --------------------------------------------------------------------------- #
RAW = Path(__file__).resolve().parents[1] / "data" / "raw" / "entsoe"
needs_data = pytest.mark.skipif(not RAW.exists(), reason="data/raw/entsoe not present")

REAL_CASES = [
    ("day_ahead_prices", "SE_3", 2025),  # SE3: hourly until 30 Sep, 15-minute after
    ("day_ahead_prices", "DE_LU", 2025),  # same switch, another zone: must give the same shape
    ("total_load", "DE_LU", 2024),  # a pure 15-minute series
    ("total_load", "SE_3", 2024),  # the same series, hourly in the source
]


@needs_data
@pytest.mark.parametrize("series, zone, year", REAL_CASES)
def test_real_file_passes_acceptance_checks(series, zone, year):
    import test_data_acceptance as acceptance  # Devika's checks, unchanged

    out = harmonise_file(RAW / series / zone / f"{year}.parquet")
    results = acceptance.run_all(out, acceptance.Ctx(series=series, zone=out.attrs["zone"], year=year))
    errors = [f"{r.check}: {e}" for r in results for e in r.errors]
    assert not errors, "\n".join(errors)
    assert len(out) == (8784 if year == 2024 else 8760)  # one row per UTC hour of the year


@needs_data
def test_15_minute_zone_and_se3_come_out_in_the_same_shape():
    se3 = harmonise_file(RAW / "day_ahead_prices" / "SE_3" / "2025.parquet")
    de = harmonise_file(RAW / "day_ahead_prices" / "DE_LU" / "2025.parquet")
    assert list(se3.columns) == list(de.columns) == PRICE_COLUMNS
    assert se3.dtypes.equals(de.dtypes)
    assert se3.index.equals(de.index)
    assert set(se3["mtu_minutes"]) == {60}  # the step of the OUTPUT rows (Devika's checks rely on this)


@needs_data
def test_partial_year_file_shows_its_missing_months():
    # IE-SEM solar 2024 holds only 13 Nov - 31 Dec in the raw file.
    out = harmonise_file(RAW / "solar_generation" / "IE_SEM" / "2024.parquet")
    assert len(out) == 8784
    assert out["gen_solar_mw"].isna().mean() > 0.8
