"""Currency: everything in EUR, converted with a dated rate (PW01-CD-04, section 3).

ENTSO-E publishes day-ahead prices in EUR for every zone we use, so for ENTSO-E data
the conversion is the identity. Other sources (N2EX in GBP, Nordic or Central-European
national data in NOK, SEK, PLN, CZK, HUF, ...) are not, and this module makes sure a
non-EUR series can never be used, or mixed with EUR series, without a dated rate.

Rate convention: ECB euro reference rates, quoted as units of currency per 1 EUR
(e.g. GBP 0.85). value_eur = value / rate. For each delivery day the latest rate on
or before that day is used: weekends and holidays carry the last rate forward, and a
rate is never taken from a later date.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from harmonise.clock import delivery_day

MAX_RATE_AGE_DAYS = 5  # longest ECB gap is a holiday weekend; older than this = wrong rate table
PRICE_COLUMN = re.compile(r"^price_(?P<currency>[a-z]{3})_mwh$")


class CurrencyError(ValueError):
    """A non-EUR value without a usable dated exchange rate."""


def to_eur(values: pd.Series, currency: str, fx_rates: pd.Series | None = None) -> tuple[pd.Series, pd.Series]:
    """Convert a UTC-indexed series to EUR. Returns ``(value_eur, fx_rate_eur)``.

    ``fx_rates`` is one currency's ECB series: index = rate date, value = units per EUR.
    It is required for anything that is not EUR; without it this raises instead of
    letting a GBP number pass as a EUR number.
    """
    currency = currency.upper()
    if currency == "EUR":
        return values.copy(), pd.Series(1.0, index=values.index, name="fx_rate_eur")
    if fx_rates is None:
        raise CurrencyError(f"series is in {currency}; pass dated ECB {currency}/EUR rates (fx_rates) to convert it")

    rates = pd.Series(fx_rates, dtype=float).dropna()
    rates.index = pd.to_datetime(rates.index).normalize()
    rates = rates.sort_index()
    if (rates <= 0).any():
        raise CurrencyError("exchange rates must be positive")

    # For each row: its delivery day, then the latest rate dated on or before that day.
    days = pd.to_datetime(pd.Series(delivery_day(values.index), index=values.index))
    pos = rates.index.searchsorted(days.to_numpy(), side="right") - 1  # -1 = no rate that early
    if (pos < 0).any():
        first = days[pos < 0].iloc[0].date()
        raise CurrencyError(f"no {currency} rate on or before {first}; the rate table starts {rates.index[0].date()}")
    rate_dates = rates.index[pos]
    age = (days.to_numpy() - rate_dates.to_numpy()) / np.timedelta64(1, "D")
    if (age > MAX_RATE_AGE_DAYS).any():
        worst = days[age > MAX_RATE_AGE_DAYS].iloc[0].date()
        raise CurrencyError(f"newest {currency} rate before {worst} is more than {MAX_RATE_AGE_DAYS} days old")

    fx = pd.Series(rates.to_numpy()[pos], index=values.index, name="fx_rate_eur")
    return values / fx, fx


def assert_eur(frame: pd.DataFrame) -> None:
    """Refuse a frame that holds a non-EUR price without its converted EUR column.

    Used before frames are combined, so a GBP column cannot sit next to EUR columns
    and be read as EUR by mistake.
    """
    found = [PRICE_COLUMN.match(c) for c in frame.columns]
    non_eur = [m.group(0) for m in found if m and m.group("currency") != "eur"]
    if non_eur and "price_eur_mwh" not in frame.columns:
        raise CurrencyError(f"non-EUR price column(s) {non_eur} without price_eur_mwh; convert with to_eur first")
