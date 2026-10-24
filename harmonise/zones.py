"""Zone codes: one lookup table, one function (PW01-CD-04, section 5).

Every source spells zones differently: ENTSO-E folders use ``SE_3`` and ``DE_LU``,
EEX and the futures collector use ``DE``, the API uses EIC codes. All code in this
repo uses the short name in ``zones.csv`` (``SE3``, ``DE-LU``) and gets it through
``resolve_zone``. An unknown code raises; it is never dropped or guessed.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

ZONES_CSV = Path(__file__).with_name("zones.csv")


class UnknownZoneError(KeyError):
    """A zone code that is not in zones.csv. Add a row there instead of working around it."""


@lru_cache(maxsize=1)
def load_zones() -> pd.DataFrame:
    """Read zones.csv once. Indexed by the short name (``zone``)."""
    zones = pd.read_csv(ZONES_CSV, dtype=str, keep_default_na=False)
    return zones.set_index("zone", drop=False)


@lru_cache(maxsize=1)
def _lookup() -> dict[str, str]:
    """Map every known spelling (short name, ENTSO-E area, EIC, aliases) to the short name."""
    table: dict[str, str] = {}
    for row in load_zones().itertuples(index=False):
        spellings = [row.zone, row.entsoe_area, row.eic, *filter(None, row.aliases.split(";"))]
        for s in spellings:
            key = s.strip().upper()
            if key in table and table[key] != row.zone:  # the table itself is wrong: fail loudly
                raise ValueError(f"zones.csv: {s!r} points to both {table[key]} and {row.zone}")
            table[key] = row.zone
    return table


def resolve_zone(code: str) -> str:
    """Return the short zone name for any known spelling, e.g. ``"SE_3" -> "SE3"``, ``"DE" -> "DE-LU"``."""
    try:
        return _lookup()[str(code).strip().upper()]
    except KeyError:
        raise UnknownZoneError(f"unknown zone code {code!r}; add it to {ZONES_CSV.name}") from None


def zone_info(code: str) -> pd.Series:
    """The full zones.csv row for a zone (EIC, country, local time zone, ...)."""
    return load_zones().loc[resolve_zone(code)]
