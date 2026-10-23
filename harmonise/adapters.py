"""Source adapters: raw source layout -> standard value columns, still in the native step.

One adapter per SOURCE, not per country. Today there is one source (ENTSO-E, as
downloaded by the entsoe-py client into data/raw/entsoe/SERIES/ZONE/YEAR.parquet).

What the ENTSO-E files look like (surveyed 22 Oct 2026, 2019-2025, 21 zones):
* day_ahead_prices  one column ``value`` (EUR/MWh)
* total_load        one column ``Actual Load`` (MW)
* solar/wind        per technology, in one of three spellings, sometimes mixed in ONE
                    file because months were downloaded separately and concatenated:
                      ``Solar``                                (flat name)
                      ``('Solar', 'Actual Aggregated')``       (real 2-level column)
                      ``"('Solar', 'Actual Aggregated')"``     (the same, saved as a string)
                    plus ``Actual Consumption`` (self-consumption, almost always 0).
"""
from __future__ import annotations

import ast
import re
import warnings

import pandas as pd

from harmonise.specs import get_spec

GENERATION = "Actual Aggregated"
CONSUMPTION = "Actual Consumption"


class AdapterError(ValueError):
    """The raw file does not look like what this adapter knows how to read."""


class DataWarning(UserWarning):
    """Something in the raw data that is kept out of the output but deserves a look."""


def _slug(text: str) -> str:
    """'Wind Onshore' -> 'wind_onshore'."""
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _parse_generation_column(col) -> tuple[str, str]:
    """Any of the three spellings -> (technology, kind)."""
    if isinstance(col, tuple):
        return col[0], col[1]
    if isinstance(col, str) and col.startswith("("):
        parsed = ast.literal_eval(col)  # "('Solar', 'Actual Aggregated')" -> tuple, no code executed
        return parsed[0], parsed[1]
    return str(col), GENERATION  # flat name = generation


def _coalesce(parts: list[pd.Series], label: str) -> pd.Series:
    """Merge columns that hold the same quantity for different months into one.

    Where two of them have a value for the same timestamp the values must agree;
    otherwise we cannot know which is right and raise.
    """
    merged = parts[0]
    for part in parts[1:]:
        both = merged.notna() & part.notna()
        if both.any() and not (merged[both] - part[both]).abs().le(1e-6).all():
            raise AdapterError(f"{label}: two raw columns disagree at {int(both.sum())} timestamp(s)")
        merged = merged.combine_first(part)
    return merged


def _generation(raw: pd.DataFrame) -> pd.DataFrame:
    gen: dict[str, list[pd.Series]] = {}
    consumption: list[pd.Series] = []
    for col in raw.columns:
        tech, kind = _parse_generation_column(col)
        if kind == GENERATION:
            gen.setdefault(tech, []).append(raw[col])
        elif kind == CONSUMPTION:
            consumption.append(raw[col])
        else:
            raise AdapterError(f"unknown generation column {col!r}")

    # Self-consumption is not generation; it is left out of the output (open point for
    # Methodology). It is almost always 0; if not, say so instead of dropping it quietly.
    for c in consumption:
        nonzero = int((c.fillna(0) != 0).sum())
        if nonzero:
            warnings.warn(f"{c.name}: {nonzero} non-zero self-consumption value(s) left out of the output",
                          DataWarning, stacklevel=3)

    out = pd.DataFrame({f"gen_{_slug(t)}_mw": _coalesce(parts, t) for t, parts in gen.items()})
    if out.empty:
        raise AdapterError("no generation column found")
    return out


def from_entsoe(raw: pd.DataFrame, series: str, currency: str = "EUR") -> pd.DataFrame:
    """Rename and reshape one ENTSO-E raw frame into standard value columns.

    The index and the time step are left exactly as they are; time handling is the
    next step's job. Prices are named after their ORIGINAL currency
    (``price_eur_mwh``, or ``price_gbp_mwh`` before conversion).
    """
    spec = get_spec(series)
    if spec.name == "day_ahead_prices":
        if list(raw.columns) != ["value"]:
            raise AdapterError(f"day_ahead_prices: expected one column 'value', found {list(raw.columns)}")
        out = raw[["value"]].rename(columns={"value": f"price_{currency.lower()}_mwh"})
    elif spec.name == "total_load":
        if list(raw.columns) != ["Actual Load"]:
            raise AdapterError(f"total_load: expected one column 'Actual Load', found {list(raw.columns)}")
        out = raw[["Actual Load"]].rename(columns={"Actual Load": "load_mw"})
    else:  # solar_generation, wind_generation
        out = _generation(raw)
    out = out.astype(float)
    out.index.name = "timestamp_utc"
    return out
