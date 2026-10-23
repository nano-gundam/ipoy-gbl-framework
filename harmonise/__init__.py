"""Harmonisation layer (PW01-CD-04): every zone's data in one time, unit and currency format.

Rules: docs/methods/harmonisation.md. Typical use:

    from harmonise import harmonise_file
    hourly = harmonise_file("data/raw/entsoe/day_ahead_prices/SE_3/2025.parquet")

Modules, in the order the pipeline uses them:
    zones      zone codes -> short names (zones.csv)
    specs      what each series is (quantity -> aggregation rule, unit)
    adapters   raw ENTSO-E layout -> standard value columns
    clock      local time -> UTC, delivery day, 23/24/25-hour days
    resample   native step (15/30/60 min) -> hourly, gaps stay NaN
    currency   original currency -> EUR with a dated ECB rate
    pipeline   harmonise(): all of the above in one call
"""
from harmonise.pipeline import SCHEMA_VERSION, combine, harmonise, harmonise_file
from harmonise.resample import daily_coverage, to_hourly

__all__ = ["SCHEMA_VERSION", "combine", "daily_coverage", "harmonise", "harmonise_file", "to_hourly"]
