"""What each series is, as data: one row per series instead of if/else in the code.

Adding a series = adding a row here (and, if its raw columns look new, a branch in
adapters.py). The aggregation rule follows from the quantity (PW01-CD-04, section 1):
prices and power are averaged over the hour, energy is summed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Quantity = Literal["price", "power", "energy"]

AGGREGATION = {"price": "mean", "power": "mean", "energy": "sum"}
UNIT = {"price": "EUR/MWh", "power": "MW", "energy": "MWh"}


@dataclass(frozen=True)
class SeriesSpec:
    name: str  # ENTSO-E folder name under data/raw/entsoe/
    quantity: Quantity
    description: str

    @property
    def how(self) -> str:
        """Hourly aggregation: 'mean' or 'sum'."""
        return AGGREGATION[self.quantity]

    @property
    def unit(self) -> str:
        """Unit after harmonisation (prices always in EUR)."""
        return UNIT[self.quantity]

    @property
    def has_currency(self) -> bool:
        return self.quantity == "price"


SERIES_SPECS: dict[str, SeriesSpec] = {s.name: s for s in (
    SeriesSpec("day_ahead_prices", "price", "SDAC day-ahead clearing price"),
    SeriesSpec("total_load", "power", "actual total load, average MW per interval"),
    SeriesSpec("solar_generation", "power", "actual solar generation, average MW per interval"),
    SeriesSpec("wind_generation", "power", "actual wind generation per technology, average MW per interval"),
)}


def get_spec(series: str) -> SeriesSpec:
    try:
        return SERIES_SPECS[series]
    except KeyError:
        raise KeyError(f"unknown series {series!r}; known: {sorted(SERIES_SPECS)}") from None
