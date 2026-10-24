"""Time step: detect it per row, convert to hourly in one place (PW01-CD-04, sections 1 and 6).

Raw series keep their native step (15, 30 or 60 minutes), and the step can change
inside one file (SDAC moved day-ahead prices to 15 minutes on 1 Oct 2025; several
TSOs changed their load step mid-year). ``to_hourly`` is the only place where data
is aggregated, and it never fills: an hour that is not fully covered becomes NaN.
"""
from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd

from harmonise.clock import delivery_day, hours_in_day

ALLOWED_STEPS = (15, 30, 60)  # minutes; 30 is used by IE-SEM load
MIN_STEP_RUN = 4  # a step must repeat this many times in a row, otherwise the jump is a gap
Aggregation = Literal["mean", "sum"]


class StepError(ValueError):
    """The timestamps do not allow a safe hourly conversion."""


def _require_utc_index(index: pd.Index) -> pd.DatetimeIndex:
    """Every function below works on a sorted, duplicate-free UTC index; check it once."""
    if not isinstance(index, pd.DatetimeIndex) or index.tz is None:
        raise StepError("index must be a timezone-aware DatetimeIndex")
    if str(index.tz) != "UTC":
        raise StepError(f"index must be in UTC, found {index.tz}")
    if not index.is_unique:
        raise StepError(f"{index.duplicated().sum()} duplicated timestamp(s)")
    if not index.is_monotonic_increasing:
        raise StepError("timestamps are not sorted")
    return index


def _run_lengths(values: np.ndarray) -> np.ndarray:
    """For each element, the length of the run of equal consecutive values it belongs to."""
    n = len(values)
    if n == 0:
        return np.array([], dtype=int)
    starts = np.flatnonzero(np.r_[True, values[1:] != values[:-1]])
    lengths = np.diff(np.r_[starts, n])
    return np.repeat(lengths, lengths)


def infer_mtu_minutes(index: pd.DatetimeIndex) -> pd.Series:
    """Length in minutes of the interval each row covers (its market time unit, MTU).

    Each row's step is the distance to the next timestamp, but only when that distance
    is an allowed step AND repeats at least ``MIN_STEP_RUN`` times in a row. Anything
    else is a gap (a missing slot, or a 2-hour outage) and the row keeps the step of
    the row before it. Example, 15-minute data with one slot missing:

        distances  15 15 15 30 15 15 15      -> steps  15 15 15 15 15 15 15
                            ^ isolated 30 = gap, not a new 30-minute step
    """
    idx = _require_utc_index(index)
    if len(idx) < 2:
        raise StepError("need at least two timestamps to determine the step")
    dist = np.diff(idx.as_unit("ns").asi8) / 60e9  # nanoseconds -> minutes
    min_run = min(MIN_STEP_RUN, len(dist))  # a very short series cannot show a run of 4
    is_step = np.isin(dist, ALLOWED_STEPS) & (_run_lengths(dist) >= min_run)
    steps = pd.Series(np.where(is_step, dist, np.nan), dtype=float)
    steps = pd.concat([steps, pd.Series([np.nan])], ignore_index=True)  # last row: no next timestamp
    steps = steps.ffill().bfill()  # gap rows inherit the step before them (or after, at the start)
    if steps.isna().all():
        found = sorted(set(dist.tolist()))[:5]
        raise StepError(f"no regular step of {ALLOWED_STEPS} minutes found (distances seen: {found})")
    return pd.Series(steps.to_numpy().astype(int), index=idx, name="mtu_minutes")


def to_hourly(values: pd.DataFrame, how: Aggregation, mtu_minutes: pd.Series | None = None) -> pd.DataFrame:
    """Aggregate every column of ``values`` to whole UTC hours.

    how="mean": time-weighted mean, for prices (EUR/MWh) and power (MW).
    how="sum":  sum, for energy (MWh).

    Rules (no silent filling):
    * an hour is kept only if its non-missing rows cover all 60 minutes; otherwise NaN;
    * hours with no rows at all appear as NaN rows, so gaps stay visible;
    * a row must start on a multiple of its own step (no interval may cross an hour).

    Returns an hourly frame with the same columns, indexed by ``timestamp_utc``.
    """
    if how not in ("mean", "sum"):
        raise ValueError(f"how must be 'mean' or 'sum', not {how!r}")
    idx = _require_utc_index(values.index)
    non_numeric = [c for c in values.columns if not pd.api.types.is_numeric_dtype(values[c])]
    if non_numeric:
        raise StepError(f"to_hourly only takes numeric value columns; found {non_numeric}")
    mtu = infer_mtu_minutes(idx) if mtu_minutes is None else mtu_minutes.reindex(idx)

    minute_of_hour = idx.minute.to_numpy()
    if np.any(minute_of_hour % mtu.to_numpy() != 0):
        raise StepError("some intervals do not start on a multiple of their step and would cross an hour")

    hour = idx.floor("h")
    weight = mtu.to_numpy()[:, None]  # minutes covered by each row, one column per value column
    present = values.notna().to_numpy()
    covered = pd.DataFrame(present * weight, index=hour, columns=values.columns).groupby(level=0).sum()

    if how == "mean":
        weighted = values.mul(mtu, axis=0).set_axis(hour).groupby(level=0).sum(min_count=1)
        out = weighted / covered.where(covered > 0)
    else:
        out = values.set_axis(hour).groupby(level=0).sum(min_count=1)
    out = out.where(covered >= 60)  # partially covered hours are not averaged from what is left

    full = pd.date_range(hour.min(), hour.max(), freq="h", name="timestamp_utc")
    return out.reindex(full)


def daily_coverage(hourly: pd.DataFrame, column: str) -> pd.DataFrame:
    """Expected vs received hours per delivery day (market time), using 23/24/25-hour days.

    The first and last day of a series are usually cut by the UTC boundary, so they
    are reported like any other day; filter them out if you need whole days only.
    """
    days = delivery_day(hourly.index)
    received = hourly[column].notna().groupby(days).sum()
    expected = pd.Series([hours_in_day(d) for d in received.index], index=received.index)
    return pd.DataFrame({"expected_hours": expected, "received_hours": received,
                         "missing_hours": expected - received})
