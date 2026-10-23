"""Time-zone and delivery-day rules (PW01-CD-04, section 2).

Storage is always UTC. Local time appears in two places only:
* converting a source that delivers local time (``local_to_utc``);
* the delivery day, which is defined in market time (CET/CEST, Europe/Berlin) for
  every zone, Finland and the Baltics included.

A delivery day has 23, 24 or 25 hours. Nothing in this module assumes 24.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd

MARKET_TZ = "Europe/Berlin"  # SDAC gate times and exchange products use this clock


class ClockError(ValueError):
    """A local timestamp that cannot be placed on the UTC axis without guessing."""


def local_to_utc(timestamps: pd.DatetimeIndex, tz: str) -> pd.DatetimeIndex:
    """Convert local wall-clock timestamps (no time zone attached) to UTC.

    The two clock-change days are handled explicitly instead of letting pandas guess:
    * spring (last Sunday of March): 02:00-02:59 local does not exist. A timestamp in
      that hour means the source is wrong, so we raise.
    * autumn (last Sunday of October): 02:00-02:59 local happens twice. The first
      occurrence is summer time, the second winter time; pandas tells them apart by the
      order of the rows (``ambiguous="infer"``). If a repeated hour appears only once,
      the order cannot tell, so we raise rather than pick one.

    Timestamps that already carry a time zone are simply converted to UTC.
    """
    idx = pd.DatetimeIndex(timestamps)
    if idx.tz is not None:
        return idx.tz_convert("UTC")
    try:
        localised = idx.tz_localize(tz, ambiguous="infer", nonexistent="raise")
    except ValueError as err:  # pandas raises ValueError for both DST cases
        raise ClockError(f"cannot convert local time in {tz} to UTC: {err}") from err
    return localised.tz_convert("UTC")


def delivery_day(timestamps_utc: pd.DatetimeIndex) -> pd.Index:
    """Delivery day (a ``datetime.date``) of each UTC timestamp, in market time."""
    return pd.Index(pd.DatetimeIndex(timestamps_utc).tz_convert(MARKET_TZ).date, name="delivery_day")


def hours_in_day(day: dt.date | str, tz: str = MARKET_TZ) -> int:
    """Length of one local day in hours: 23 (March change), 25 (October change) or 24."""
    start = pd.Timestamp(day).tz_localize(tz)
    end = (pd.Timestamp(day) + pd.Timedelta(days=1)).tz_localize(tz)
    return int((end - start) / pd.Timedelta(hours=1))


def expected_slots(day: dt.date | str, mtu_minutes: int, tz: str = MARKET_TZ) -> int:
    """How many intervals a complete delivery day has: e.g. 92, 96 or 100 quarter-hours."""
    return hours_in_day(day, tz) * 60 // mtu_minutes
