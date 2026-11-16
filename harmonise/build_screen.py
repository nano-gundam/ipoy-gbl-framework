"""Build the checked Tier 1 screen dataset from the raw ENTSO-E files (PW03-CD-01, Part A).

    python -m harmonise.build_screen                 # the 13 screen zones, 2019-2025
    python -m harmonise.build_screen --zones SE3 NL  # a subset

For every screen zone it writes, under ``data/processed/entsoe/``:

* ``hourly/<ZONE>.parquet``: one continuous hourly UTC frame for 2019-2025 with
  ``price_eur_mwh``, ``load_mw``, ``gen_wind_onshore_mw``, ``gen_solar_mw``. Built with
  the shared ``harmonise()`` (an hour is empty unless fully covered; nothing is filled).
  Used for price level, volatility, capture rates and growth (metric dictionary 0.2).
* ``native_prices/<ZONE>.parquet``: day-ahead prices in their source step (60 min, and
  15 min from 1 Oct 2025) with ``mtu_minutes``. Used for negative-price time and daily
  spreads, which hourly averaging would distort (harmonisation.md section 1).

and two tables for the whole run:

* ``data_test_log.csv``: every error and warning of Devika's six data tests on the
  raw files, one row per finding (zone, series, year, check, level, message). Raw
  files that are missing are logged here too. Nothing is fixed.
* ``coverage.csv``: one row per zone, series and year (market-time year, CET/CEST, as
  the metric dictionary defines it): expected and missing hours, missing share,
  longest gap and where it starts, and whether the year passes the 98 % rule.

Scope: onshore wind only (PW03 brief).

Currency: ENTSO-E day-ahead prices are EUR, with one exception found in PW03. Poland's
prices are in PLN until delivery day 19 Nov 2019 (Poland joined market coupling on
20 Nov 2019), and the raw file does not say so. Those hours are converted with the ECB
reference rates in ``data/raw/ecb/`` (``NON_EUR_PRICES``) before harmonising. The data
tests still run on the unconverted raw files.
"""
from __future__ import annotations

import argparse
import sys
import warnings
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from harmonise.adapters import from_entsoe
from harmonise.clock import delivery_day
from harmonise.currency import to_eur
from harmonise.pipeline import harmonise
from harmonise.resample import infer_mtu_minutes
from harmonise.zones import resolve_zone, zone_info

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "entsoe"
OUT = ROOT / "data" / "processed" / "entsoe"

SCREEN_ZONES = ["SE3", "NL", "DE-LU", "ES", "IT-NORD", "IT-CNOR", "IT-CSUD", "IT-SUD",
                "IT-CALA", "IT-SICI", "IT-SARD", "PL", "LT"]
YEARS = range(2019, 2026)
MARKET_TZ = "Europe/Berlin"
VALID_YEAR_SHARE = 0.98  # metric dictionary 0.4

# series folder -> the value column kept in the screen dataset
SERIES = {
    "day_ahead_prices": "price_eur_mwh",
    "total_load": "load_mw",
    "wind_generation": "gen_wind_onshore_mw",
    "solar_generation": "gen_solar_mw",
}

# Years in which a zone did not exist, so "no data" is expected and not a gap.
# Calabria became its own bidding zone on 1 Jan 2021 (split from IT-SUD).
ZONE_NOT_YET_CREATED = {("IT-CALA", 2019), ("IT-CALA", 2020)}

# Raw day-ahead prices that are not in EUR although the file does not say so:
# zone -> (currency, last delivery day in that currency, ECB rates file in units per EUR).
NON_EUR_PRICES = {
    "PL": ("PLN", date(2019, 11, 19), ROOT / "data" / "raw" / "ecb" / "pln_eur_2018-12_2019-11.csv"),
}


def _entsoe_folder(zone: str) -> str:
    """'DE-LU' -> 'DE_LU', the folder name in data/raw/entsoe."""
    return zone_info(zone)["entsoe_area"]


def _raw_path(series: str, zone: str, year: int) -> Path:
    return RAW / series / _entsoe_folder(zone) / f"{year}.parquet"


def _read_raw(series: str, zone: str, year: int) -> pd.DataFrame:
    """One raw file, with any non-EUR price hours (``NON_EUR_PRICES``) converted to EUR."""
    raw = pd.read_parquet(_raw_path(series, zone, year))
    if series != "day_ahead_prices" or zone not in NON_EUR_PRICES:
        return raw
    currency, last_day, rates_path = NON_EUR_PRICES[zone]
    in_currency = np.array([d <= last_day for d in delivery_day(raw.index)])
    if not in_currency.any():
        return raw
    rates = pd.read_csv(rates_path, index_col=0).iloc[:, 0]
    eur, _ = to_eur(raw.loc[in_currency, "value"], currency, rates)
    raw = raw.copy()
    raw.loc[in_currency, "value"] = eur.to_numpy()
    return raw


# --------------------------------------------------------------------------- #
# 1. Data tests on the raw files
# --------------------------------------------------------------------------- #
def _load_acceptance_tests():
    """Import Devika's checks from tests/ without running pytest."""
    sys.path.insert(0, str(ROOT / "tests"))
    import test_data_acceptance as acc  # noqa: E402

    return acc


def run_data_tests(zones: list[str]) -> pd.DataFrame:
    acc = _load_acceptance_tests()
    rows = []
    for series in SERIES:
        for zone in zones:
            for year in YEARS:
                path = _raw_path(series, zone, year)
                base = {"zone": zone, "series": series, "year": year}
                if not path.exists():
                    expected = (zone, year) in ZONE_NOT_YET_CREATED
                    rows.append({**base, "check": "file", "level": "info" if expected else "error",
                                 "message": "zone did not exist yet (created 1 Jan 2021)" if expected
                                 else "no raw file downloaded"})
                    continue
                df = pd.read_parquet(path)
                ctx = acc.Ctx.from_path(path)
                results = []
                for name, check in acc.CHECKS.items():
                    try:
                        results.append(check(df, ctx))
                    except Exception as exc:  # a check that cannot read the file is itself a finding
                        rows.append({**base, "check": name, "level": "error",
                                     "message": f"check crashed: {type(exc).__name__}: {exc}"})
                for result in results:
                    for msg in result.errors:
                        rows.append({**base, "check": result.check, "level": "error", "message": msg})
                    for msg in result.warnings:
                        rows.append({**base, "check": result.check, "level": "warning", "message": msg})
                    if result.skipped:
                        rows.append({**base, "check": result.check, "level": "skipped", "message": result.skipped})
    return pd.DataFrame(rows, columns=["zone", "series", "year", "check", "level", "message"])


# --------------------------------------------------------------------------- #
# 2. Harmonised hourly frame and native prices, one per zone
# --------------------------------------------------------------------------- #
def _full_grid() -> pd.DatetimeIndex:
    start = pd.Timestamp(f"{YEARS[0]}-01-01", tz=MARKET_TZ).tz_convert("UTC")
    end = pd.Timestamp(f"{YEARS[-1] + 1}-01-01", tz=MARKET_TZ).tz_convert("UTC")
    return pd.date_range(start, end, freq="h", inclusive="left", name="timestamp_utc")


def build_hourly(zone: str) -> pd.DataFrame:
    grid = _full_grid()
    out = pd.DataFrame(index=grid)
    out.insert(0, "zone", zone)
    for series, column in SERIES.items():
        parts = []
        for year in YEARS:
            path = _raw_path(series, zone, year)
            if not path.exists():
                continue
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")  # data warnings are already in the test log
                h = harmonise(_read_raw(series, zone, year), series=series, zone=zone, year=year)
            parts.append(h[column])
        values = pd.concat(parts).sort_index() if parts else pd.Series(dtype=float)
        if values.index.has_duplicates:
            raise ValueError(f"{zone} {series}: overlapping hours between yearly files")
        out[column] = values.reindex(grid)
    out["source"] = "entsoe"
    out["schema_version"] = "screen-0.1"
    return out


def build_native_prices(zone: str) -> pd.DataFrame:
    parts = []
    for year in YEARS:
        path = _raw_path("day_ahead_prices", zone, year)
        if not path.exists():
            continue
        raw = _read_raw("day_ahead_prices", zone, year)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            values = from_entsoe(raw, "day_ahead_prices", "EUR")
        idx = pd.DatetimeIndex(values.index)
        values = values.set_axis(idx.tz_convert("UTC") if idx.tz else idx.tz_localize("UTC")).sort_index()
        values.index.name = "timestamp_utc"
        frame = values[["price_eur_mwh"]].copy()
        frame["mtu_minutes"] = infer_mtu_minutes(frame.index).to_numpy()
        parts.append(frame)
    out = pd.concat(parts).sort_index()
    out = out[~out.index.duplicated(keep="first")]
    out.insert(0, "zone", zone)
    return out


# --------------------------------------------------------------------------- #
# 3. Coverage per zone, series and market-time year
# --------------------------------------------------------------------------- #
def _longest_gap(missing: np.ndarray, index: pd.DatetimeIndex) -> tuple[int, pd.Timestamp | None]:
    if not missing.any():
        return 0, None
    padded = np.r_[False, missing, False].astype(int)
    starts = np.flatnonzero(np.diff(padded) == 1)
    ends = np.flatnonzero(np.diff(padded) == -1)
    lengths = ends - starts
    i = int(lengths.argmax())
    return int(lengths[i]), index[starts[i]]


def coverage(hourly: pd.DataFrame) -> pd.DataFrame:
    zone = hourly["zone"].iat[0]
    local_year = hourly.index.tz_convert(MARKET_TZ).year
    rows = []
    for series, column in SERIES.items():
        for year in YEARS:
            in_year = local_year == year
            values = hourly.loc[in_year, column]
            missing = values.isna().to_numpy()
            gap, gap_start = _longest_gap(missing, values.index)
            n_missing = int(missing.sum())
            share = n_missing / len(values)
            if (zone, year) in ZONE_NOT_YET_CREATED:
                note = "zone did not exist yet"
            elif not _raw_path(series, zone, year).exists():
                note = "no raw file"
            else:
                note = ""
            rows.append({
                "zone": zone, "series": series, "year": year,
                "expected_hours": len(values), "missing_hours": n_missing,
                "missing_share": round(share, 6),
                "longest_gap_hours": gap,
                "longest_gap_start_utc": gap_start.isoformat() if gap_start is not None else "",
                "valid_year": share <= 1 - VALID_YEAR_SHARE,
                "note": note,
            })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--zones", nargs="*", default=SCREEN_ZONES)
    args = parser.parse_args(argv)
    zones = [resolve_zone(z) for z in args.zones]

    (OUT / "hourly").mkdir(parents=True, exist_ok=True)
    (OUT / "native_prices").mkdir(parents=True, exist_ok=True)

    log = run_data_tests(zones)
    log.to_csv(OUT / "data_test_log.csv", index=False)
    print(f"data tests: {len(log)} findings ({(log.level == 'error').sum()} errors)")

    cov = []
    for zone in zones:
        hourly = build_hourly(zone)
        hourly.to_parquet(OUT / "hourly" / f"{zone}.parquet")
        build_native_prices(zone).to_parquet(OUT / "native_prices" / f"{zone}.parquet")
        cov.append(coverage(hourly))
        print(f"{zone}: done")
    cov = pd.concat(cov, ignore_index=True)
    cov.to_csv(OUT / "coverage.csv", index=False)
    print(f"coverage: {(~cov.valid_year).sum()} of {len(cov)} zone-series-years below 98 %  ({date.today()})")


if __name__ == "__main__":
    main()
