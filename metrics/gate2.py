"""Gate 2 screening indicators per zone and year (PW03-CD-01, step 3).

    python -m metrics.gate2                  # 13 screen zones, 2019-2025
    python -m metrics.gate2 --zones SE3 NL   # a subset

Implements sections 1-5 of ``docs/methods/metric-dictionary-v0.md`` on the screen dataset
built by ``python -m harmonise.build_screen`` (``data/processed/entsoe/``):

1. price level, yearly and per season          hourly series
2. volatility: hourly std, std of daily change hourly series
3. negative-price time                         native series (60 or 15 min)
4. capture rates, wind onshore and solar       hourly series
5. daily 2 h and 4 h spreads                   native series, plus the hourly version

Writes ``data/processed/indicators/gate2_screen_<date>.csv``, one row per zone x year.

Departures from the dictionary, agreed for PW03:

* Wind is **onshore only** (PW03 brief). Offshore wind was not downloaded, so the wind
  columns are named ``*_wind_onshore_*`` instead of ``*_wind_*``. NL and DE-LU have large
  offshore fleets, so their onshore capture rate is not the full wind capture rate.
* ``flag_qh_source`` looks at the day-ahead price only (15-minute from 1 Oct 2025). Some
  load and generation series switch earlier; ``data_test_log.csv`` lists them.
* Coverage and the low-baseload flag are reported per technology
  (``flag_low_coverage_wind_onshore``, ``flag_low_baseload_solar``, ...), since the
  98 % rule and the baseload of section 4 are taken over that technology's hours.
  ``flag_low_coverage`` on its own refers to the price.
"""
from __future__ import annotations

import argparse
import datetime as dt
from functools import cache
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from harmonise.clock import MARKET_TZ, hours_in_day

ROOT = Path(__file__).resolve().parents[1]
SCREEN_DIR = ROOT / "data" / "processed" / "entsoe"
OUT_DIR = ROOT / "data" / "processed" / "indicators"

SCREEN_ZONES = ["SE3", "NL", "DE-LU", "ES", "IT-NORD", "IT-CNOR", "IT-CSUD", "IT-SUD",
                "IT-CALA", "IT-SICI", "IT-SARD", "PL", "LT"]
YEARS = range(2019, 2026)

VALID_SHARE_PCT = 98            # section 0.4
LOW_SOLAR_MWH = 100_000         # section 4: 100 GWh per year [choice]
LOW_BASELOAD_EUR_MWH = 5.0      # section 4 [choice]
SEASONS = {"winter": (1, 2, 12), "spring": (3, 4, 5), "summer": (6, 7, 8), "autumn": (9, 10, 11)}
TECHNOLOGIES = {"wind_onshore": "gen_wind_onshore_mw", "solar": "gen_solar_mw"}


# --------------------------------------------------------------------------- #
# Rules shared by every indicator (section 0)
# --------------------------------------------------------------------------- #
def min_valid_hours(expected: int) -> int:
    """At least 98 % of the expected hours, rounded up: 8,585 of 8,760, 8,609 of 8,784."""
    return -(-VALID_SHARE_PCT * expected // 100)  # integer ceiling, no float rounding


def is_valid(n_valid: int, expected: int) -> bool:
    return expected > 0 and n_valid >= min_valid_hours(expected)


@cache
def _hours_in_day(day: dt.date) -> int:
    return hours_in_day(day)


def local_days(index: pd.DatetimeIndex) -> pd.Index:
    """Delivery day of each UTC timestamp, in market time (section 0.3)."""
    return pd.Index(index.tz_convert(MARKET_TZ).date, name="delivery_day")


# --------------------------------------------------------------------------- #
# 1. Price level and 2. volatility (hourly series)
# --------------------------------------------------------------------------- #
def daily_means(price_hourly: pd.Series) -> pd.Series:
    """Mean price of each delivery day; NaN unless all 23, 24 or 25 hours are present."""
    days = local_days(price_hourly.index)
    grouped = price_hourly.groupby(days)
    count, mean = grouped.count(), grouped.mean()
    expected = pd.Series([_hours_in_day(d) for d in count.index], index=count.index)
    return mean.where(count == expected)


def daily_change_std(daily: pd.Series) -> tuple[float, int]:
    """Section 2, formula B: sample std of D_d - D_(d-1) over consecutive valid days.

    ``daily`` is indexed by date (one year); invalid days are NaN or absent. A missing day
    breaks the chain, so both changes that touch it drop out. Returns (std, n_changes);
    std is NaN when fewer than two changes are left.
    """
    if daily.empty:
        return np.nan, 0
    full = pd.date_range(min(daily.index), max(daily.index), freq="D").date
    changes = daily.reindex(full).diff().dropna()
    return float(changes.std()), len(changes)


# --------------------------------------------------------------------------- #
# 3. Negative-price time and 5. daily spreads (native series)
# --------------------------------------------------------------------------- #
def negative_time(price: pd.Series, mtu_minutes: pd.Series) -> dict:
    """Section 3 on the native series: hours-equivalent, share of time and mean price below 0."""
    ok = price.notna()
    p, dt_h = price[ok], mtu_minutes[ok] / 60
    neg = p < 0  # strictly below zero; 0.00 is not negative
    neg_hours = float(dt_h[neg].sum())
    total_hours = float(dt_h.sum())
    return {
        "neg_time_share_pct": neg_hours / total_hours * 100 if total_hours else np.nan,
        "neg_hours_equiv_h": neg_hours,
        "neg_price_mean_eur_mwh": float((dt_h[neg] * p[neg]).sum() / neg_hours) if neg_hours else np.nan,
    }


def _day_spread(prices: np.ndarray, k: int) -> float:
    s = np.sort(prices)
    return s[-k:].mean() - s[:k].mean()


def daily_spreads(price: pd.Series, mtu_minutes: pd.Series) -> pd.DataFrame:
    """Section 5: 2 h and 4 h spread of every valid delivery day.

    A day is valid when it has one step and all of its slots (92/96/100 quarter-hours or
    23/24/25 hours). k = 2 h / step slots for the 2 h spread, 4 h / step for the 4 h one.
    """
    frame = pd.DataFrame({"p": price.to_numpy(), "mtu": mtu_minutes.to_numpy()},
                         index=local_days(price.index))
    rows = {}
    for day, g in frame.groupby(level=0):
        steps = g["mtu"].unique()
        if len(steps) != 1:
            continue
        step = int(steps[0])
        p = g["p"].dropna().to_numpy(dtype=float)
        if len(p) != _hours_in_day(day) * 60 // step:
            continue
        rows[day] = (_day_spread(p, 120 // step), _day_spread(p, 240 // step))
    return pd.DataFrame.from_dict(rows, orient="index", columns=["spread_2h", "spread_4h"])


# --------------------------------------------------------------------------- #
# 4. Capture rate (hourly series)
# --------------------------------------------------------------------------- #
def capture(price: pd.Series, gen: pd.Series) -> dict:
    """Section 4 over the hours where both price and generation are present.

    Negative generation (own use at night) is set to 0 and counted. Baseload is the mean
    price over the same hours. The non-negative variant keeps hours with P >= 0 in the
    capture price and divides by the same all-hours baseload.
    """
    both = price.notna() & gen.notna()
    p, g = price[both], gen[both]
    n_neg_gen = int((g < 0).sum())
    g = g.clip(lower=0)
    baseload = float(p.mean()) if len(p) else np.nan
    energy = float(g.sum())
    capture_price = float((g * p).sum() / energy) if energy else np.nan
    nonneg = p >= 0
    energy_nonneg = float(g[nonneg].sum())
    capture_nonneg = float((g[nonneg] * p[nonneg]).sum() / energy_nonneg) if energy_nonneg else np.nan
    return {
        "n_hours": int(both.sum()),
        "baseload": baseload,
        "capture_price": capture_price,
        "capture_rate": capture_price / baseload if baseload else np.nan,
        "capture_rate_nonneg": capture_nonneg / baseload if baseload else np.nan,
        "energy_mwh": energy,
        "n_neg_gen_fixed": n_neg_gen,
    }


# --------------------------------------------------------------------------- #
# One zone x year row
# --------------------------------------------------------------------------- #
def zone_year(hourly: pd.DataFrame, native: pd.DataFrame, zone: str, year: int) -> dict:
    """All Gate 2 columns for one zone and delivery year (local CET/CEST year)."""
    h = hourly[hourly.index.tz_convert(MARKET_TZ).year == year]
    n = native[native.index.tz_convert(MARKET_TZ).year == year]
    price = h["price_eur_mwh"]
    expected = len(h)
    n_price = int(price.notna().sum())
    price_ok = is_valid(n_price, expected)
    row: dict = {
        "zone": zone, "year": year, "expected_hours": expected,
        "coverage_price_pct": n_price / expected * 100 if expected else np.nan,
        "flag_low_coverage": not price_ok,
        "flag_qh_source": bool((n["mtu_minutes"] == 15).any()),
    }

    # 1. price level, year and seasons
    row["price_mean_eur_mwh"] = float(price.mean()) if price_ok else np.nan
    months = h.index.tz_convert(MARKET_TZ).month
    for season, season_months in SEASONS.items():
        sp = price[np.isin(months, season_months)]
        ok = is_valid(int(sp.notna().sum()), len(sp))
        row[f"price_mean_{season}_eur_mwh"] = float(sp.mean()) if ok else np.nan

    # 2. volatility
    row["price_std_hourly_eur_mwh"] = float(price.std()) if price_ok else np.nan
    std_change, n_changes = daily_change_std(daily_means(price))
    row["price_std_daily_change_eur_mwh"] = std_change if price_ok else np.nan
    row["n_daily_changes"] = n_changes

    # 3. negative-price time (native)
    neg = negative_time(n["price_eur_mwh"], n["mtu_minutes"])
    row.update(neg if price_ok else {k: np.nan for k in neg})

    # 4. capture rates
    for tech, column in TECHNOLOGIES.items():
        c = capture(price, h[column])
        ok = is_valid(c["n_hours"], expected)
        row[f"coverage_{tech}_pct"] = c["n_hours"] / expected * 100 if expected else np.nan
        row[f"capture_price_{tech}_eur_mwh"] = c["capture_price"] if ok else np.nan
        row[f"capture_rate_{tech}_ratio"] = c["capture_rate"] if ok else np.nan
        row[f"capture_rate_nonneg_{tech}_ratio"] = c["capture_rate_nonneg"] if ok else np.nan
        row[f"energy_{tech}_gwh"] = c["energy_mwh"] / 1000 if ok else np.nan
        row[f"n_neg_gen_fixed_{tech}"] = c["n_neg_gen_fixed"]
        row[f"flag_low_coverage_{tech}"] = not ok
        row[f"flag_low_baseload_{tech}"] = bool(ok and abs(c["baseload"]) < LOW_BASELOAD_EUR_MWH)
    row["flag_low_solar"] = bool(not row["flag_low_coverage_solar"]
                                 and row["energy_solar_gwh"] * 1000 < LOW_SOLAR_MWH)

    # 5. daily spreads (native for Gate 2, hourly for comparison across the 2025 switch)
    native_spreads = daily_spreads(n["price_eur_mwh"], n["mtu_minutes"])
    hourly_spreads = daily_spreads(price, pd.Series(60, index=price.index))
    for name, frame, suffix in (("native", native_spreads, ""), ("hourly", hourly_spreads, "_hourly")):
        for k in ("2h", "4h"):
            value = float(frame[f"spread_{k}"].mean()) if price_ok and len(frame) else np.nan
            row[f"spread_{k}{suffix}_eur_mwh"] = value
    row["n_spread_days"] = len(native_spreads)
    return row


def screen(zones: list[str] = SCREEN_ZONES, years=YEARS, screen_dir: Path = SCREEN_DIR) -> pd.DataFrame:
    rows = []
    for zone in zones:
        hourly = pd.read_parquet(screen_dir / "hourly" / f"{zone}.parquet")
        native = pd.read_parquet(screen_dir / "native_prices" / f"{zone}.parquet")
        rows += [zone_year(hourly, native, zone, year) for year in years]
    return pd.DataFrame(rows)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--zones", nargs="*", default=SCREEN_ZONES)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args(argv)
    table = screen(args.zones)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    path = args.out_dir / f"gate2_screen_{dt.datetime.now(dt.UTC).astimezone(ZoneInfo(MARKET_TZ)).date().isoformat()}.csv"
    table.to_csv(path, index=False)
    print(f"{len(table)} zone-years -> {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}")
    print(f"low price coverage: {int(table.flag_low_coverage.sum())}, "
          f"low wind coverage: {int(table.flag_low_coverage_wind_onshore.sum())}, "
          f"low solar coverage: {int(table.flag_low_coverage_solar.sum())}")


if __name__ == "__main__":
    main()
