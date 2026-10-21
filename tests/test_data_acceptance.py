"""Acceptance tests for downloaded data (PW01-MV-02).  One file, everything in it.

Every test takes ONE parquet file from ``data/raw/entsoe/SERIES/ZONE/YEAR.parquet``,
so the same six tests run on every series, zone and year found:

    pytest tests/test_data_acceptance.py                       # all of it
    pytest tests/test_data_acceptance.py -k "not selfcheck"    # only the real data
    pytest tests/test_data_acceptance.py -k selfcheck          # only the proof that the checks work (no data needed)
    pytest tests/test_data_acceptance.py -k "SE3 and 2024"     # one zone / year
    ACCEPTANCE_DATA_ROOT=/other/path pytest tests/test_data_acceptance.py
    python tests/test_data_acceptance.py --write-fake-data     # (re)write tests/fake_data

Layout of this file: 1. settings and check functions, 2. the six tests on real files,
3. fake-data builders and ``test_selfcheck_*`` (one deliberate error per check),
4. the fake files stored on disk.

Hard failures are test failures; soft findings (0.5-2 % missing, etc.) appear under
"warnings summary". Price limits and known plant closures live in ``tests/config/*.csv``.

Assumptions about the files (from PW01-CD-04 and the layout above). Change the
constants in section 1 if Coding & Data decides otherwise:

* one timestamp column called ``timestamp_utc`` (or a datetime index), stored
  timezone-aware in UTC, marking the START of each interval;
* a file holds one UTC calendar year;
* series are recognised by their folder name: "day_ahead", "generation", "load"/"demand", "capacity";
* optional provenance columns ``mtu_minutes`` and ``retrieved_at_utc``.
"""
from __future__ import annotations

import os
import re
import warnings
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from pandas.api.types import is_bool_dtype, is_datetime64_any_dtype, is_numeric_dtype

# =========================================================================== #
# 1. SETTINGS AND CHECK FUNCTIONS
#    Each check_* takes ONE file (DataFrame + Ctx) and returns a CheckResult:
#    errors = the file must not enter the model; warnings = have a look.
# =========================================================================== #
# --------------------------------------------------------------------------- #
# Settings
# --------------------------------------------------------------------------- #
CONFIG_DIR = Path(__file__).resolve().parent / "data_acceptance_tests"
LOCAL_TZ = "Europe/Berlin"  # delivery-day time zone for every zone (PW01-CD-04, section 2)
TIMESTAMP_COLUMNS = ("timestamp_utc", "timestamp", "datetime_utc", "time_utc")
META_COLUMNS = {  # not data values, so exempt from unit / plausibility rules
    "mtu_minutes", "source", "retrieved_at_utc", "schema_version",
    "fx_rate_eur", "currency_original",
}
STEPS_ALLOWED = (15.0, 60.0)  # minutes
MISSING_FAIL = 0.02  # fail above 2 % missing
MISSING_WARN = 0.005  # warn above 0.5 % missing
MAX_REPEAT_HOURS = 24.0  # the same value for MORE than this many hours = suspected fill
IGNORE_ZERO_RUNS = True  # night-time solar / polar winter legitimately repeat 0
CAPACITY_DROP_TOLERANCE_MW = 0.5  # rounding noise only
MAX_LISTED = 10  # how many gaps / examples to print per message
# Magnitude rules for the unit check (a correct-looking name can still hold the wrong unit).
# They use the 99th percentile of |value| so a few outliers cannot trigger them.
PRICE_P99_MIN_EUR_MWH = 5.0  # below this the column is probably EUR/kWh
PRICE_P99_MAX_EUR_MWH = 10_000.0
POWER_P99_MAX_MW = 200_000.0  # above this the column is probably kW or W (largest zone load is ~80,000 MW)
LOAD_P99_MIN_MW = 100.0  # a bidding-zone load below this is probably GW
BIGGEST_COLUMN_P99_MIN_MW = 100.0  # biggest generation / capacity column of a file: below this, all columns are probably GW
MIXED_STEP_RUN = 4  # this many consecutive intervals of a larger size = a second step, not a gap

# SDAC moved day-ahead prices from 60 to 15 minutes for delivery from 1 Oct 2025
# (00:00 CEST = 22:00 UTC on 30 Sep). That year's day-ahead files therefore
# legitimately contain BOTH steps; every other file must have exactly one.
SDAC_15MIN_START = pd.Timestamp("2025-09-30 22:00", tz="UTC")
SWITCH_YEARS = (2025,)

SERIES_KINDS = (  # first match wins; matched on the lower-cased SERIES folder name
    ("capacity", ("capacity",)),
    ("day_ahead_price", ("day_ahead", "dayahead", "da_price")),
    ("price", ("price",)),
    ("generation", ("generation", "gen_")),
    ("load", ("load", "demand")),
)
NONNEG_PREFIXES = ("gen_", "generation_", "load_", "demand_", "consumption_")
UNIT_SUFFIX = re.compile(r"_(?:[a-z]{3}_)?(?:mwh|mw|gwh|gw)$|_pct$|_h$")
NON_EUR_PRICE = re.compile(r"_(?!eur_)[a-z]{3}_mwh$")
EPOCH = pd.Timestamp("1970-01-01", tz="UTC")


# --------------------------------------------------------------------------- #
# Plumbing
# --------------------------------------------------------------------------- #
def series_kind(series: str) -> str:
    s = series.lower()
    for kind, keys in SERIES_KINDS:
        if any(k in s for k in keys):
            return kind
    return "other"


@dataclass(frozen=True)
class Ctx:
    series: str
    zone: str
    year: int
    path: Path | None = None

    @property
    def kind(self) -> str:
        return series_kind(self.series)

    @classmethod
    def from_path(cls, path: str | Path) -> "Ctx":
        p = Path(path)
        return cls(series=p.parent.parent.name, zone=p.parent.name, year=int(p.stem), path=p)


@dataclass
class CheckResult:
    check: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skipped: str | None = None

    @property
    def ok(self) -> bool:
        return not self.errors and self.skipped is None


class Blocked(Exception):
    """The file is too broken for this check to run (the timestamps test says why)."""


@dataclass
class Prepared:
    body: pd.DataFrame  # indexed by UTC start time, sorted, duplicates dropped
    slot_min: np.ndarray  # length of each row in minutes (NaN for annual series)
    switch: pd.Timestamp | None  # set when a 60 -> 15 minute switch is present
    value_cols: list[str]


def get_timestamps(df: pd.DataFrame):
    """Return (timestamps as a positional Series, name of the column or None)."""
    for c in TIMESTAMP_COLUMNS:
        if c in df.columns:
            return df[c].reset_index(drop=True), c
    if isinstance(df.index, pd.DatetimeIndex):
        return pd.Series(df.index), None
    return None, None


def value_columns(df: pd.DataFrame, ts_col: str | None) -> list[str]:
    return [
        c for c in df.columns
        if c != ts_col and c not in META_COLUMNS
        and is_numeric_dtype(df[c]) and not is_bool_dtype(df[c])
    ]


def _is_utc(ts: pd.Series) -> bool:
    tz = ts.dt.tz
    if tz is None:
        return False
    return all(pd.Timestamp(s, tz=tz).utcoffset() == pd.Timedelta(0) for s in ("2024-01-15", "2024-07-15"))


def _diff_minutes(idx: pd.DatetimeIndex) -> np.ndarray:
    return np.diff((idx - EPOCH).total_seconds().to_numpy()) / 60.0


def _find_switch(d: np.ndarray, idx: pd.DatetimeIndex, ctx: Ctx) -> int | None:
    """Row number of the first 15-minute row if this is the 2025 day-ahead file with both steps."""
    if ctx.kind != "day_ahead_price" or ctx.year not in SWITCH_YEARS:
        return None
    hits = np.flatnonzero(d == 15.0)
    if hits.size == 0 or hits[0] == 0:
        return None  # fully hourly or fully 15-minute: the normal rule applies
    k = int(hits[0])
    if idx[k] < SDAC_15MIN_START:
        return None
    if np.all(d[:k] % 60 == 0) and np.all(d[k:] % 15 == 0):
        return k
    return None


def prepare(df: pd.DataFrame, ctx: Ctx) -> Prepared:
    ts, col = get_timestamps(df)
    if ts is None:
        raise Blocked("no timestamp column and no datetime index")
    if not is_datetime64_any_dtype(ts):
        raise Blocked("timestamps are not a datetime type")
    if ts.isna().any():
        raise Blocked("timestamps contain nulls")
    if not _is_utc(ts):
        raise Blocked("timestamps are not timezone-aware UTC")
    body = (df.drop(columns=[col]) if col else df).reset_index(drop=True)
    body.index = pd.DatetimeIndex(ts)
    body = body[~body.index.duplicated(keep="first")].sort_index()
    n = len(body)
    switch = None
    if ctx.kind == "capacity":
        slot = np.full(n, np.nan)
    else:
        if n < 2:
            raise Blocked("fewer than two timestamps")
        d = _diff_minutes(body.index)
        k = _find_switch(d, body.index, ctx)
        if k is not None:
            slot = np.where(np.arange(n) < k, 60.0, 15.0)
            switch = SDAC_15MIN_START
        else:
            vals, counts = np.unique(d, return_counts=True)
            slot = np.full(n, vals[np.argmax(counts)])
    return Prepared(body, slot, switch, value_columns(body, None))


def year_bounds(year: int) -> tuple[pd.Timestamp, pd.Timestamp]:
    return pd.Timestamp(year=year, month=1, day=1, tz="UTC"), pd.Timestamp(year=year + 1, month=1, day=1, tz="UTC")


def year_window(body: pd.DataFrame, ctx: Ctx) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Slots that must exist. A file downloaded part-way through its year is judged up to the download time."""
    start, end = year_bounds(ctx.year)
    if "retrieved_at_utc" in body.columns:
        ret = pd.to_datetime(body["retrieved_at_utc"], utc=True, errors="coerce").max()
        if pd.notna(ret) and ret < end:
            end = ret.floor("h")
    return start, end


def expected_index(prep: Prepared, start: pd.Timestamp, end: pd.Timestamp) -> pd.DatetimeIndex:
    if prep.switch is not None:
        hourly = pd.date_range(start, min(prep.switch, end), freq="60min", inclusive="left")
        quarter = pd.date_range(max(prep.switch, start), end, freq="15min", inclusive="left")
        return hourly.append(quarter)
    return pd.date_range(start, end, freq=f"{int(prep.slot_min[0])}min", inclusive="left")


def expected_slot_count(year: int, step_minutes: int) -> int:
    start, end = year_bounds(year)
    return int((end - start) / pd.Timedelta(minutes=step_minutes))


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """Start/end (inclusive) of each run of True."""
    if not mask.any():
        return []
    m = np.concatenate(([False], mask, [False]))
    edges = np.flatnonzero(m[1:] != m[:-1])
    return list(zip(edges[0::2], edges[1::2] - 1))


def _fmt_runs(index: pd.DatetimeIndex, mask: np.ndarray) -> str:
    runs = _runs(mask)
    shown = [f"{index[a]:%Y-%m-%d %H:%M}->{index[b]:%Y-%m-%d %H:%M} UTC ({b - a + 1} slots)" for a, b in runs[:MAX_LISTED]]
    more = f"; +{len(runs) - MAX_LISTED} more gaps" if len(runs) > MAX_LISTED else ""
    return "; ".join(shown) + more


def eu_clock_change_dates(year: int) -> tuple[date, date]:
    """Local dates of the EU clock changes: last Sunday of March and of October."""
    def last_sunday(month: int) -> date:
        d = date(year, month, 31)
        return d - timedelta(days=(d.weekday() + 1) % 7)
    return last_sunday(3), last_sunday(10)


def _examples(items, limit: int = MAX_LISTED) -> str:
    items = list(items)
    text = ", ".join(str(i) for i in items[:limit])
    return text + (f", +{len(items) - limit} more" if len(items) > limit else "")


# --------------------------------------------------------------------------- #
# 1. Timestamps
# --------------------------------------------------------------------------- #
def check_timestamps(df: pd.DataFrame, ctx: Ctx) -> CheckResult:
    r = CheckResult("timestamps")
    ts, col = get_timestamps(df)
    if ts is None:
        r.errors.append(f"no timestamp column (looked for {TIMESTAMP_COLUMNS}) and no datetime index")
        return r
    if not is_datetime64_any_dtype(ts):
        r.errors.append(f"timestamps are stored as {ts.dtype}, not as a datetime type")
        return r
    if ts.isna().any():
        r.errors.append(f"{int(ts.isna().sum())} null timestamp(s)")
        return r
    if not _is_utc(ts):
        r.errors.append(f"timestamps are not timezone-aware UTC (dtype {ts.dtype}); store them as UTC")
        return r

    if not ts.is_monotonic_increasing:
        back = np.flatnonzero(ts.diff().dt.total_seconds().to_numpy() < 0)
        r.errors.append(
            f"timestamps are not increasing at {len(back)} place(s); first at row {back[0]} "
            f"({ts.iloc[back[0]]} follows {ts.iloc[back[0] - 1]})")
    dup = ts[ts.duplicated()]
    if len(dup):
        r.errors.append(f"{len(dup)} duplicated timestamp(s): {_examples(dup.drop_duplicates())}")
    start, end = year_bounds(ctx.year)
    outside = ts[(ts < start) | (ts >= end)]
    if len(outside):
        r.errors.append(f"{len(outside)} timestamp(s) outside {ctx.year} UTC, e.g. {_examples(outside)}")

    if ctx.kind == "capacity":  # annual values: no step to check
        return r
    idx = pd.DatetimeIndex(ts.drop_duplicates().sort_values())
    if len(idx) < 2:
        r.errors.append("fewer than two timestamps: cannot determine the step")
        return r
    d = _diff_minutes(idx)
    if _find_switch(d, idx, ctx) is None:
        vals, counts = np.unique(d, return_counts=True)
        step = float(vals[np.argmax(counts)])
        if step not in STEPS_ALLOWED:
            r.errors.append(f"the usual step is {step:g} minutes; it must be 15 or 60")
        else:
            bad = np.flatnonzero((d < step) | (d % step != 0))
            if bad.size:
                found = sorted({float(x) for x in d[bad]})
                r.errors.append(
                    f"{bad.size} interval(s) do not fit the {step:g}-minute step (found {found} minutes); "
                    f"first after {idx[bad[0]]}. One file must have ONE step"
                    + (" (15- and 60-minute rows are mixed)" if {15.0, 60.0} <= set(vals) else ""))
            # a stretch of regular larger intervals is a second step, whereas a single large one is just a gap
            for v in (x for x in vals if x > step):
                runs = [(a, b) for a, b in _runs(d == v) if b - a + 1 >= MIXED_STEP_RUN]
                if runs:
                    a, b = runs[0]
                    r.errors.append(
                        f"the file mixes steps: {b - a + 1} consecutive intervals of {v:g} minutes from {idx[a]} "
                        f"in a file that is otherwise {step:g}-minute. One file must have ONE step")
    try:
        prep = prepare(df, ctx)
    except Blocked:
        return r
    if "mtu_minutes" in prep.body.columns:
        mtu = prep.body["mtu_minutes"].to_numpy(dtype=float)
        wrong = np.flatnonzero(mtu != prep.slot_min)
        if wrong.size:
            r.errors.append(
                f"mtu_minutes disagrees with the timestamps on {wrong.size} row(s); first at {prep.body.index[wrong[0]]} "
                f"(column says {mtu[wrong[0]]:g}, timestamps imply {prep.slot_min[wrong[0]]:g})")
    return r


# --------------------------------------------------------------------------- #
# 2. Completeness
# --------------------------------------------------------------------------- #
def check_completeness(df: pd.DataFrame, ctx: Ctx) -> CheckResult:
    r = CheckResult("completeness")
    if ctx.kind == "capacity":
        r.skipped = "annual series: no hourly completeness to check"
        return r
    try:
        prep = prepare(df, ctx)
    except Blocked as e:
        r.skipped = f"blocked by the timestamps check: {e}"
        return r
    if not prep.value_cols:
        r.errors.append("no value columns found")
        return r
    start, end = year_window(prep.body, ctx)
    exp = expected_index(prep, start, end)
    grid = prep.body.reindex(exp)
    for c in prep.value_cols:
        miss = grid[c].isna().to_numpy()
        share = float(miss.mean()) if len(exp) else 0.0
        if share > MISSING_FAIL:
            r.errors.append(
                f"{c}: {share:.2%} missing ({int(miss.sum())} of {len(exp)} values; limit {MISSING_FAIL:.1%}). "
                f"Gaps: {_fmt_runs(exp, miss)}")
        elif share > MISSING_WARN:
            r.warnings.append(
                f"{c}: {share:.2%} missing ({int(miss.sum())} of {len(exp)} values; warn above {MISSING_WARN:.1%}). "
                f"Gaps: {_fmt_runs(exp, miss)}")
    return r


# --------------------------------------------------------------------------- #
# 3. Clock changes
# --------------------------------------------------------------------------- #
def check_clock_changes(df: pd.DataFrame, ctx: Ctx) -> CheckResult:
    r = CheckResult("clock_changes")
    if ctx.kind == "capacity":
        r.skipped = "annual series: no clock changes to check"
        return r
    try:
        prep = prepare(df, ctx)
    except Blocked as e:
        r.skipped = f"blocked by the timestamps check: {e}"
        return r
    local_days = prep.body.index.tz_convert(LOCAL_TZ).date
    hours = pd.Series(prep.slot_min / 60.0, index=local_days).groupby(level=0).sum()
    inner = hours.iloc[1:-1]  # first and last local day are cut by the UTC year boundary
    spring, autumn = eu_clock_change_dates(ctx.year)
    for day, want, month in ((spring, 23, "March"), (autumn, 25, "October")):
        if not (hours.index[0] < day < hours.index[-1]):
            continue  # file does not reach this clock change (partial year)
        found = inner[np.isclose(inner, want)]
        actual = hours.get(day)
        if len(found) != 1:
            r.errors.append(
                f"expected exactly one {want}-hour day in {month}, found {len(found)}"
                + (f" ({_examples(found.index)})" if len(found) else "")
                + f"; the clock-change day {day} has {actual:g} hours of data")
        elif found.index[0] != day:
            r.errors.append(f"the {want}-hour day is {found.index[0]}, but the clock change is on {day}")
    return r


# --------------------------------------------------------------------------- #
# 4. Plausible values
# --------------------------------------------------------------------------- #
def load_price_limits(path: Path | None = None) -> pd.DataFrame:
    lim = pd.read_csv(path or CONFIG_DIR / "day_ahead_price_limits.csv")
    lim["valid_from_utc"] = pd.to_datetime(lim["valid_from_utc"], utc=True)
    return lim.sort_values("valid_from_utc").reset_index(drop=True)


def load_known_drops(path: Path | None = None) -> pd.DataFrame:
    p = path or CONFIG_DIR / "known_capacity_drops.csv"
    if not Path(p).exists():
        return pd.DataFrame(columns=["zone", "column", "year", "reason"])
    return pd.read_csv(p, dtype={"zone": str, "column": str})


def _drop_explained(known: pd.DataFrame, zone: str, column: str, year: int) -> bool:
    if known.empty:
        return False
    hit = known[(known["zone"] == zone) & (known["year"] == year) & (known["column"].isin([column, "*"]))]
    return not hit.empty


def check_plausible_values(df: pd.DataFrame, ctx: Ctx, price_limits: pd.DataFrame | None = None,
                           known_drops: pd.DataFrame | None = None) -> CheckResult:
    r = CheckResult("plausible_values")
    try:
        prep = prepare(df, ctx)
    except Blocked as e:
        r.skipped = f"blocked by the timestamps check: {e}"
        return r
    body, cols = prep.body, prep.value_cols

    # prices: inside the legal day-ahead limits that applied on that date
    if ctx.kind == "day_ahead_price":
        lim = price_limits if price_limits is not None else load_price_limits()
        pos = pd.DatetimeIndex(lim["valid_from_utc"]).searchsorted(body.index, side="right") - 1
        if (pos < 0).any():
            r.errors.append(f"no price limit defined before {lim['valid_from_utc'].iloc[0]:%Y-%m-%d}; add it to config/day_ahead_price_limits.csv")
        else:
            lo, hi = lim["min_eur_mwh"].to_numpy()[pos], lim["max_eur_mwh"].to_numpy()[pos]
            for c in [c for c in cols if c.startswith("price") and not NON_EUR_PRICE.search(c)]:
                v = body[c].to_numpy(dtype=float)
                bad = np.flatnonzero((v < lo) | (v > hi))
                if bad.size:
                    ex = [f"{body.index[i]:%Y-%m-%d %H:%M} = {v[i]:g} (allowed {lo[i]:g}..{hi[i]:g})" for i in bad]
                    r.errors.append(f"{c}: {bad.size} value(s) outside the day-ahead limits: {_examples(ex, 5)}")

    # generation / demand: never negative
    nonneg = cols if ctx.kind in ("generation", "load") else [c for c in cols if c.startswith(NONNEG_PREFIXES)]
    for c in nonneg:
        neg = np.flatnonzero(body[c].to_numpy(dtype=float) < 0)
        if neg.size:
            ex = [f"{body.index[i]:%Y-%m-%d %H:%M} = {body[c].iloc[i]:g}" for i in neg]
            r.errors.append(f"{c}: {neg.size} negative value(s): {_examples(ex, 5)}")

    # installed capacity: no drops without a known closure
    if ctx.kind == "capacity":
        known = known_drops if known_drops is not None else load_known_drops()
        _check_capacity(body, cols, ctx, known, r)
    return r


def _check_capacity(body: pd.DataFrame, cols: list[str], ctx: Ctx, known: pd.DataFrame, r: CheckResult) -> None:
    for c in cols:
        if (body[c] < 0).any():
            r.errors.append(f"{c}: negative installed capacity")
        drops = (body[c].diff() < -CAPACITY_DROP_TOLERANCE_MW).to_numpy()
        for i in np.flatnonzero(drops):
            _report_drop(r, known, ctx, c, body.index[i].year, body[c].iloc[i - 1], body[c].iloc[i])
    prev_path = ctx.path.with_name(f"{ctx.year - 1}.parquet") if ctx.path else None
    if prev_path is not None and prev_path.exists():
        try:
            prev = prepare(pd.read_parquet(prev_path), Ctx(ctx.series, ctx.zone, ctx.year - 1, prev_path)).body
        except Blocked as e:
            r.warnings.append(f"previous year's file could not be compared ({e})")
            return
        for c in cols:
            if c in prev.columns and len(prev) and len(body) and body[c].iloc[0] < prev[c].iloc[-1] - CAPACITY_DROP_TOLERANCE_MW:
                _report_drop(r, known, ctx, c, body.index[0].year, prev[c].iloc[-1], body[c].iloc[0])
    else:
        r.warnings.append(f"no {ctx.year - 1} file next to this one: the year-on-year capacity drop check was skipped")


def _report_drop(r: CheckResult, known: pd.DataFrame, ctx: Ctx, col: str, year: int, before: float, after: float) -> None:
    if not _drop_explained(known, ctx.zone, col, year):
        r.errors.append(
            f"{col}: installed capacity fell from {before:g} to {after:g} MW in {year} and no closure is listed "
            f"for {ctx.zone} in config/known_capacity_drops.csv")


# --------------------------------------------------------------------------- #
# 5. Silent gap-filling
# --------------------------------------------------------------------------- #
def check_silent_fill(df: pd.DataFrame, ctx: Ctx) -> CheckResult:
    r = CheckResult("silent_gap_filling")
    if ctx.kind == "capacity":
        r.skipped = "annual series: repeated values are normal"
        return r
    try:
        prep = prepare(df, ctx)
    except Blocked as e:
        r.skipped = f"blocked by the timestamps check: {e}"
        return r
    idx, slot = prep.body.index, prep.slot_min
    contiguous = np.zeros(len(idx), dtype=bool)
    contiguous[1:] = np.isclose(_diff_minutes(idx), slot[:-1])
    for c in prep.value_cols:
        v = prep.body[c].to_numpy(dtype=float)
        same = np.zeros(len(v), dtype=bool)
        same[1:] = (v[1:] == v[:-1]) & ~np.isnan(v[1:]) & ~np.isnan(v[:-1])
        link = same & contiguous
        grp = np.cumsum(~link)  # a new group starts wherever a row does NOT repeat the previous one
        hours = np.bincount(grp, weights=slot) / 60.0
        sizes = np.bincount(grp)
        starts = np.flatnonzero(~link)
        flagged = []
        for g in np.flatnonzero((hours > MAX_REPEAT_HOURS + 1e-9) & (sizes >= 2)):
            first = starts[g - 1]
            if IGNORE_ZERO_RUNS and v[first] == 0:
                continue
            flagged.append(f"{v[first]:g} for {hours[g]:g} h from {idx[first]:%Y-%m-%d %H:%M} UTC")
        if flagged:
            r.errors.append(
                f"{c}: {len(flagged)} run(s) of one unchanged value longer than {MAX_REPEAT_HOURS:g} h "
                f"(likely copied into a gap): {_examples(flagged, 5)}")
    return r


# --------------------------------------------------------------------------- #
# 6. Units in column names
# --------------------------------------------------------------------------- #
def _p99(s: pd.Series) -> float:
    a = np.abs(s.to_numpy(dtype=float))
    a = a[~np.isnan(a)]
    return float(np.percentile(a, 99)) if a.size else float("nan")


def check_units(df: pd.DataFrame, ctx: Ctx) -> CheckResult:
    """The unit must be in the column name AND the numbers must be of the size that unit implies."""
    r = CheckResult("units")
    _, col = get_timestamps(df)
    cols = value_columns(df, col)
    if not cols:
        r.errors.append("no numeric value columns found")
    bad = [c for c in cols if not UNIT_SUFFIX.search(c)]
    if bad:
        r.errors.append(f"value column(s) without a unit in the name (e.g. price_eur_mwh, gen_mw): {', '.join(bad)}")

    p99 = {c: _p99(df[c]) for c in cols}
    for c in cols:
        p = p99[c]
        if np.isnan(p):
            continue
        if c.startswith("price") and c.endswith("_eur_mwh"):
            if p < PRICE_P99_MIN_EUR_MWH:
                r.errors.append(f"{c}: 99th percentile of |value| is {p:g}, too small for EUR/MWh; stored in EUR/kWh?")
            elif p > PRICE_P99_MAX_EUR_MWH:
                r.errors.append(f"{c}: 99th percentile of |value| is {p:g}, too large for EUR/MWh; stored in cents?")
        elif c.endswith("_mw"):
            if p > POWER_P99_MAX_MW:
                r.errors.append(f"{c}: 99th percentile of |value| is {p:g}, too large for MW; stored in kW or W?")
            if c.startswith(("load_", "demand_")) and p < LOAD_P99_MIN_MW:
                r.errors.append(f"{c}: 99th percentile of |value| is {p:g}, too small for a zone load in MW; stored in GW?")
    power = [p99[c] for c in cols if c.endswith("_mw") and not c.startswith("price") and not np.isnan(p99[c])]
    if ctx.kind in ("generation", "capacity") and power and max(power) < BIGGEST_COLUMN_P99_MIN_MW:
        r.errors.append(f"every power column is below {BIGGEST_COLUMN_P99_MIN_MW:g} MW at the 99th percentile "
                        f"(largest {max(power):g}); stored in GW?")
    return r


CHECKS = {
    "timestamps": check_timestamps,
    "completeness": check_completeness,
    "clock_changes": check_clock_changes,
    "plausible_values": check_plausible_values,
    "silent_gap_filling": check_silent_fill,
    "units": check_units,
}


def run_all(df: pd.DataFrame, ctx: Ctx) -> list[CheckResult]:
    return [fn(df, ctx) for fn in CHECKS.values()]


# =========================================================================== #
# 2. THE SIX TESTS ON REAL FILES
# =========================================================================== #
DATA_ROOT = Path(os.environ.get("ACCEPTANCE_DATA_ROOT", Path(__file__).resolve().parents[1] / "data" / "raw" / "entsoe"))
FILES = sorted(DATA_ROOT.glob("*/*/*.parquet"))


class DataQualityWarning(UserWarning):
    """A soft finding: the file passes but someone should look at it."""


def _files():
    if not FILES:
        return [pytest.param(None, marks=pytest.mark.skip(reason=f"no parquet files under {DATA_ROOT}"))]
    return [pytest.param(f, id=f"{f.parent.parent.name}/{f.parent.name}/{f.stem}") for f in FILES]


@lru_cache(maxsize=8)
def _load(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path)


def _run(check, path: Path):
    result = check(_load(path), Ctx.from_path(path))
    for w in result.warnings:
        warnings.warn(f"{path.parent.parent.name}/{path.parent.name}/{path.stem}: {w}", DataQualityWarning, stacklevel=2)
    if result.skipped:
        pytest.skip(result.skipped)
    assert not result.errors, "\n" + "\n".join(f"- {e}" for e in result.errors)


@pytest.mark.parametrize("path", _files())
def test_timestamps(path):
    """UTC, always increasing, no duplicates, one fixed step (hourly or 15-minute)."""
    _run(check_timestamps, path)


@pytest.mark.parametrize("path", _files())
def test_completeness(path):
    """Right number of values per year; fail above 2 % missing, warn above 0.5 %, gaps listed."""
    _run(check_completeness, path)


@pytest.mark.parametrize("path", _files())
def test_clock_changes(path):
    """In local time: exactly one 23-hour day (March) and one 25-hour day (October)."""
    _run(check_clock_changes, path)


@pytest.mark.parametrize("path", _files())
def test_plausible_values(path):
    """Prices inside the day-ahead limits for that date; generation/demand >= 0; capacity does not drop unexplained."""
    _run(check_plausible_values, path)


@pytest.mark.parametrize("path", _files())
def test_no_silent_gap_filling(path):
    """No value repeated unchanged for more than 24 hours in a row."""
    _run(check_silent_fill, path)


@pytest.mark.parametrize("path", _files())
def test_units_in_column_names(path):
    """Every value column carries its unit, e.g. price_eur_mwh, gen_mw."""
    _run(check_units, path)


# =========================================================================== #
# 3. SELF-CHECK: fake files with one deliberate error each (no real data needed)
# =========================================================================== #
RETRIEVED = pd.Timestamp("2026-10-12 08:00", tz="UTC")
DA, GEN, LOAD, CAP = "day_ahead_prices", "generation_per_type", "actual_load", "installed_capacity"


# --------------------------------------------------------------------------- #
# Fake data
# --------------------------------------------------------------------------- #
def make_frame(kind, year=2024, step=60, seed=0, switch_at=None, retrieved=RETRIEVED, end=None):
    """One clean, plausible file. switch_at: hourly before this UTC time, 15-minute from then on."""
    rng = np.random.default_rng(seed)
    start = pd.Timestamp(year=year, month=1, day=1, tz="UTC")
    stop = end or pd.Timestamp(year=year + 1, month=1, day=1, tz="UTC")
    if switch_at is None:
        idx = pd.date_range(start, stop, freq=f"{step}min", inclusive="left")
        mtu = np.full(len(idx), step)
    else:
        idx = pd.date_range(start, switch_at, freq="60min", inclusive="left").append(
            pd.date_range(switch_at, stop, freq="15min", inclusive="left"))
        mtu = np.where(idx < switch_at, 60, 15)
    n, hour = len(idx), idx.hour.to_numpy() + idx.minute.to_numpy() / 60
    df = pd.DataFrame({"timestamp_utc": idx})
    if kind == DA:
        df["price_eur_mwh"] = np.round(60 + 25 * np.sin(2 * np.pi * hour / 24) + rng.normal(0, 8, n), 2)
    elif kind == GEN:
        df["gen_wind_mw"] = np.round(np.abs(rng.normal(800, 200, n)), 1)
        df["gen_solar_mw"] = np.round(np.clip(500 * np.sin(np.pi * (hour - 6) / 12), 0, None) * (1 + rng.normal(0, .02, n)), 1)
        df["gen_hydro_mw"] = np.round(rng.normal(1500, 100, n), 1)
    elif kind == LOAD:
        df["load_mw"] = np.round(5000 + 800 * np.sin(2 * np.pi * hour / 24) + rng.normal(0, 50, n), 1)
    df["mtu_minutes"] = mtu
    df["source"] = "entsoe"
    df["retrieved_at_utc"] = retrieved
    df["schema_version"] = 1
    return df


def make_capacity(year, wind=1000.0, solar=400.0):
    return pd.DataFrame({
        "timestamp_utc": [pd.Timestamp(year=year, month=1, day=1, tz="UTC")],
        "capacity_wind_mw": [wind], "capacity_solar_mw": [solar],
        "source": "entsoe", "retrieved_at_utc": RETRIEVED, "schema_version": 1,
    })


def write(root, df, series, year, zone="SE3"):
    path = root / "data" / "raw" / "entsoe" / series / zone / f"{year}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return path


def run(check, path, **kw):
    return check(pd.read_parquet(path), Ctx.from_path(path), **kw)


# --------------------------------------------------------------------------- #
# Clean files must pass everything
# --------------------------------------------------------------------------- #
CLEAN = {
    "price_hourly_2023": (DA, dict(year=2023)),
    "price_hourly_leap_2024": (DA, dict(year=2024)),
    "price_15min_2024": (DA, dict(year=2024, step=15)),
    "price_2025_switches_to_15min": (DA, dict(year=2025, switch_at=SDAC_15MIN_START)),
    "generation_2024": (GEN, dict(year=2024)),
    "load_2024": (LOAD, dict(year=2024)),
    "price_partial_2026": (DA, dict(year=2026, end=pd.Timestamp("2026-10-13 12:00", tz="UTC"),
                                    retrieved=pd.Timestamp("2026-10-13 11:30", tz="UTC"))),
}


@pytest.mark.parametrize("name", CLEAN)
def test_selfcheck_clean_file_passes_every_check(name, tmp_path):
    series, kw = CLEAN[name]
    path = write(tmp_path, make_frame(series, **kw), series, kw["year"])
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        results = run_all(pd.read_parquet(path), Ctx.from_path(path))
    for res in results:
        assert not res.errors, f"{res.check}: {res.errors}"
        assert not res.warnings, f"{res.check}: {res.warnings}"
        assert res.skipped is None, f"{res.check} was skipped: {res.skipped}"


def test_selfcheck_clean_capacity_passes(tmp_path):
    write(tmp_path, make_capacity(2023, 1000), CAP, 2023)
    path = write(tmp_path, make_capacity(2024, 1200), CAP, 2024)
    for res in run_all(pd.read_parquet(path), Ctx.from_path(path)):
        assert not res.errors and not res.warnings, (res.check, res.errors, res.warnings)


def test_selfcheck_expected_value_counts():
    assert expected_slot_count(2023, 60) == 8760
    assert expected_slot_count(2024, 60) == 8784  # leap year
    assert expected_slot_count(2023, 15) == 4 * 8760
    assert expected_slot_count(2024, 15) == 4 * 8784


def test_selfcheck_clock_change_dates():
    assert eu_clock_change_dates(2024) == (pd.Timestamp("2024-03-31").date(), pd.Timestamp("2024-10-27").date())
    assert eu_clock_change_dates(2025) == (pd.Timestamp("2025-03-30").date(), pd.Timestamp("2025-10-26").date())
    assert eu_clock_change_dates(2026) == (pd.Timestamp("2026-03-29").date(), pd.Timestamp("2026-10-25").date())


# --------------------------------------------------------------------------- #
# One deliberate error per case: (check that must fail, series, year, how to break the frame)
# --------------------------------------------------------------------------- #
def _drop_rows(df, rows):
    return df.drop(index=rows).reset_index(drop=True)


def _t(df, ts):
    return int(df.index[df["timestamp_utc"] == pd.Timestamp(ts, tz="UTC")][0])


def _naive(df):
    df["timestamp_utc"] = df["timestamp_utc"].dt.tz_localize(None)
    return df


def _duplicate_hour(df):
    return pd.concat([df.iloc[:101], df.iloc[[100]], df.iloc[101:]], ignore_index=True)


def _out_of_order(df):
    df.iloc[[200, 201]] = df.iloc[[201, 200]].to_numpy()
    return df


def _half_hour_row(df):
    df.loc[300, "timestamp_utc"] += pd.Timedelta(minutes=30)
    return df


def _wrong_mtu(df):
    df["mtu_minutes"] = 15
    return df


def _local_time_labelled_utc(df):
    local = df["timestamp_utc"].dt.tz_convert("Europe/Berlin").dt.tz_localize(None)
    df["timestamp_utc"] = local.dt.tz_localize("UTC")
    return df


def _october_hour_missing(df):
    # the 25-hour day lost one hour: 24 hours of data, as if the clock change were ignored
    return _drop_rows(df, [_t(df, "2024-10-26 23:00")])


def _missing_share(share):
    def f(df):
        rows = np.random.default_rng(1).choice(len(df), int(share * len(df)), replace=False)
        return _drop_rows(df, rows)
    return f


def _ten_day_gap(df):
    first = _t(df, "2023-05-10 00:00")
    return _drop_rows(df, range(first, first + 240))


def _null_values(df):
    rows = np.random.default_rng(2).choice(len(df), int(0.03 * len(df)), replace=False)
    df.loc[rows, "price_eur_mwh"] = np.nan
    return df


def _set(col, row, value):
    def f(df):
        df.loc[row, col] = value
        return df
    return f


def _repeat(col, n, value=42.0):
    def f(df):
        df.loc[500:500 + n - 1, col] = value
        return df
    return f


def _scale(col, factor):
    def f(df):
        df[col] = df[col] * factor
        return df
    return f


def _rename(old, new):
    return lambda df: df.rename(columns={old: new})


def _mixed_steps_2024(df):
    # hourly until 1 Oct, 15-minute afterwards: allowed only in the 2025 day-ahead file
    return make_frame(DA, 2024, switch_at=pd.Timestamp("2024-10-01 00:00", tz="UTC"))


def _mixed_steps_no_mtu(df):
    return _mixed_steps_2024(df).drop(columns=["mtu_minutes"])


CASES = [
    # id,                          check,               series, year, break the frame
    ("timestamps_not_utc",         "timestamps",        DA,  2024, _naive),
    ("timestamps_duplicate_hour",  "timestamps",        DA,  2024, _duplicate_hour),
    ("timestamps_out_of_order",    "timestamps",        DA,  2024, _out_of_order),
    ("timestamps_half_hour_row",   "timestamps",        DA,  2024, _half_hour_row),
    ("timestamps_mixed_step_2024", "timestamps",        DA,  2024, _mixed_steps_2024),
    ("timestamps_mixed_step_no_mtu", "timestamps",     DA,  2024, _mixed_steps_no_mtu),
    ("timestamps_wrong_mtu_col",   "timestamps",        DA,  2024, _wrong_mtu),
    ("completeness_3pct_missing",  "completeness",      DA,  2023, _missing_share(0.03)),
    ("completeness_ten_day_gap",   "completeness",      DA,  2023, _ten_day_gap),
    ("completeness_3pct_nulls",    "completeness",      DA,  2023, _null_values),
    ("clock_october_hour_lost",    "clock_changes",     DA,  2024, _october_hour_missing),
    ("clock_local_time_as_utc",    "clock_changes",     DA,  2024, _local_time_labelled_utc),
    ("values_price_above_cap_2021", "plausible_values", DA,  2021, _set("price_eur_mwh", 1000, 3500.0)),
    ("values_price_below_floor",   "plausible_values",  DA,  2023, _set("price_eur_mwh", 1000, -600.0)),
    ("values_negative_generation", "plausible_values",  GEN, 2024, _set("gen_wind_mw", 1000, -5.0)),
    ("values_negative_demand",     "plausible_values",  LOAD, 2024, _set("load_mw", 1000, -1.0)),
    ("fill_25h_same_value",        "silent_gap_filling", DA, 2024, _repeat("price_eur_mwh", 25)),
    ("fill_repeated_generation",   "silent_gap_filling", GEN, 2024, _repeat("gen_hydro_mw", 40, 1500.0)),
    ("units_price_without_unit",   "units",             DA,  2024, _rename("price_eur_mwh", "price")),
    ("units_generation_no_unit",   "units",             GEN, 2024, _rename("gen_wind_mw", "gen_wind")),
    ("units_price_in_eur_kwh",     "units",             DA,  2024, _scale("price_eur_mwh", 0.001)),
    ("units_load_in_gw",           "units",             LOAD, 2024, _scale("load_mw", 0.001)),
    ("units_generation_in_kw",     "units",             GEN, 2024, _scale("gen_wind_mw", 1000.0)),
]


@pytest.mark.parametrize("case", CASES, ids=[c[0] for c in CASES])
def test_selfcheck_each_deliberate_error_is_caught(case, tmp_path):
    _, check, series, year, breaker = case
    path = write(tmp_path, breaker(make_frame(series, year)), series, year)
    result = run(CHECKS[check], path)
    assert result.errors, f"{check} did NOT catch the deliberate error"


def test_selfcheck_capacity_drop_is_caught_and_a_known_closure_is_accepted(tmp_path):
    write(tmp_path, make_capacity(2023, wind=1000), CAP, 2023)
    path = write(tmp_path, make_capacity(2024, wind=900), CAP, 2024)
    assert run(check_plausible_values, path).errors, "capacity drop was not caught"
    known = pd.DataFrame([{"zone": "SE3", "column": "capacity_wind_mw", "year": 2024, "reason": "plant X closed"}])
    assert not run(check_plausible_values, path, known_drops=known).errors


# --------------------------------------------------------------------------- #
# The checks must not over-fire
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("year,when,value,legal", [
    (2021, "2021-02-11 16:00", 3500.0, False),  # cap was 3000
    (2022, "2022-05-10 21:00", 3500.0, False),  # last hour before the cap rose to 4000
    (2022, "2022-05-10 22:00", 3500.0, True),   # first hour under the 4000 cap
    (2022, "2022-07-11 16:00", 4500.0, False),  # cap 4000
    (2022, "2022-09-20 21:00", 4500.0, False),  # last hour before the cap rose to 5000
    (2022, "2022-09-20 22:00", 4500.0, True),   # first hour under the 5000 cap
    (2023, "2023-02-11 16:00", 5500.0, False),  # above every cap ever in force
    (2023, "2023-02-11 16:00", -500.0, True),   # exactly the floor is legal
    (2023, "2023-02-11 16:00", -500.01, False),
])
def test_selfcheck_price_limits_depend_on_the_date(year, when, value, legal, tmp_path):
    df = make_frame(DA, year)
    df.loc[_t(df, when), "price_eur_mwh"] = value
    path = write(tmp_path, df, DA, year)
    assert (not run(check_plausible_values, path).errors) == legal


def test_selfcheck_a_run_of_exactly_24_hours_is_allowed_but_25_is_not(tmp_path):
    ok = write(tmp_path, _repeat("price_eur_mwh", 24)(make_frame(DA, 2024)), DA, 2024)
    assert not run(check_silent_fill, ok).errors


def test_selfcheck_zero_runs_are_not_flagged_as_filling(tmp_path):
    path = write(tmp_path, _repeat("gen_solar_mw", 72, 0.0)(make_frame(GEN, 2024)), GEN, 2024)
    assert not run(check_silent_fill, path).errors


def test_selfcheck_one_percent_missing_warns_but_passes(tmp_path):
    path = write(tmp_path, _missing_share(0.01)(make_frame(DA, 2023)), DA, 2023)
    res = run(check_completeness, path)
    assert not res.errors
    assert len(res.warnings) == 1 and "Gaps:" in res.warnings[0]


def test_selfcheck_gap_list_names_the_missing_days(tmp_path):
    path = write(tmp_path, _ten_day_gap(make_frame(DA, 2023)), DA, 2023)
    msg = run(check_completeness, path).errors[0]
    assert "2023-05-10 00:00->2023-05-19 23:00" in msg and "240 slots" in msg


def test_selfcheck_a_lost_october_hour_is_a_clock_error_not_a_completeness_error(tmp_path):
    """One missing hour is 0.01 % of the year, so only the clock-change test can see it."""
    path = write(tmp_path, _october_hour_missing(make_frame(DA, 2024)), DA, 2024)
    assert run(check_clock_changes, path).errors
    assert not run(check_completeness, path).errors


def test_selfcheck_utc_year_edges_are_not_mistaken_for_short_days(tmp_path):
    """A UTC-year file starts at 01:00 local time, so 1 January looks like a 23-hour day. It must be ignored."""
    path = write(tmp_path, make_frame(DA, 2023), DA, 2023)
    assert not run(check_clock_changes, path).errors


def test_selfcheck_two_step_file_is_rejected_outside_the_2025_day_ahead_exception(tmp_path):
    """The 60 -> 15 minute switch is only tolerated in the 2025 day-ahead file."""
    mixed = make_frame(DA, 2025, switch_at=SDAC_15MIN_START)
    assert not run(check_timestamps, write(tmp_path, mixed, DA, 2025)).errors
    assert run(check_timestamps, write(tmp_path, mixed, GEN, 2025)).errors  # same data in a generation series


# --------------------------------------------------------------------------- #
# Fake files on disk, for reviewers:  python tests/test_data_acceptance.py --write-fake-data
# --------------------------------------------------------------------------- #
FAKE_DIR = Path(__file__).resolve().parent / "fake_data"


def write_fake_data(dest: Path = FAKE_DIR) -> pd.DataFrame:
    """Write one folder per case (same layout as data/raw/entsoe) and a manifest of what each must trigger."""
    rows = []
    for name, (series, kw) in CLEAN.items():
        p = write(dest / f"clean_{name}", make_frame(series, **kw), series, kw["year"])
        rows.append((f"clean_{name}", "", p.relative_to(dest).as_posix()))
    for cid, check, series, year, breaker in CASES:
        p = write(dest / cid, breaker(make_frame(series, year)), series, year)
        rows.append((cid, check, p.relative_to(dest).as_posix()))
    write(dest / "capacity_drop", make_capacity(2023, wind=1000), CAP, 2023)
    p = write(dest / "capacity_drop", make_capacity(2024, wind=900), CAP, 2024)
    rows.append(("capacity_drop", "plausible_values", p.relative_to(dest).as_posix()))
    manifest = pd.DataFrame(rows, columns=["case", "must_fail_check", "file"])
    manifest.to_csv(dest / "manifest.csv", index=False)
    return manifest


def _manifest_rows():
    m = FAKE_DIR / "manifest.csv"
    if not m.exists():
        return [pytest.param(None, marks=pytest.mark.skip(reason="no tests/fake_data folder; run --write-fake-data"))]
    return [pytest.param(r, id=r["case"]) for r in pd.read_csv(m).fillna("").to_dict("records")]


@pytest.mark.parametrize("row", _manifest_rows())
def test_selfcheck_committed_fake_files(row):
    """The fake files stored in the repo: broken ones must be caught by their check, clean ones must pass everything."""
    path = FAKE_DIR / row["file"]
    df, ctx = pd.read_parquet(path), Ctx.from_path(path)
    if row["must_fail_check"]:
        assert CHECKS[row["must_fail_check"]](df, ctx).errors, f"{row['must_fail_check']} did not catch {row['case']}"
    else:
        for res in run_all(df, ctx):
            assert not res.errors, f"{res.check}: {res.errors}"


if __name__ == "__main__":
    import sys
    if "--write-fake-data" in sys.argv:
        print(write_fake_data().to_string(index=False))
    else:
        print("usage: python tests/test_data_acceptance.py --write-fake-data   (or run it with pytest)")
