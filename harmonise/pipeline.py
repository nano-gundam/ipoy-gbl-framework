"""One call from raw input to hourly UTC data in EUR (PW01-CD-04).

    hourly = harmonise(raw, series="day_ahead_prices", zone="SE_3")
    hourly = harmonise_file("data/raw/entsoe/total_load/DE_LU/2024.parquet")

Every series and zone goes through the same steps; what differs is looked up in
zones.csv (zone codes) and specs.py (aggregation rule, unit). The output has the same
shape for every zone of a series:

    index            timestamp_utc  (tz-aware UTC, hourly, start of the hour; with ``year``,
                     every hour of that UTC year, so a file that covers only part of the
                     year shows the rest as empty rows instead of hiding it)
    zone             short name from zones.csv, e.g. "SE3", "DE-LU"
    <value columns>  price_eur_mwh | load_mw | gen_solar_mw | gen_wind_onshore_mw
    mtu_minutes      step of the output rows: always 60 (the source step stays in the raw file)
    currency_original, fx_rate_eur      (price series only)
    source, retrieved_at_utc, schema_version
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from harmonise.adapters import from_entsoe
from harmonise.clock import local_to_utc
from harmonise.currency import CurrencyError, assert_eur, to_eur
from harmonise.resample import StepError, to_hourly
from harmonise.specs import get_spec
from harmonise.zones import resolve_zone

SCHEMA_VERSION = "harmonise-0.1"


def _to_utc_index(raw: pd.DataFrame, local_tz: str | None) -> pd.DataFrame:
    """Put the raw frame on a UTC index. Local (naive) timestamps need ``local_tz``."""
    idx = pd.DatetimeIndex(raw.index)
    if idx.tz is None:
        if local_tz is None:
            raise ValueError("timestamps have no time zone; pass local_tz (e.g. 'Europe/Berlin') to convert them")
        idx = local_to_utc(idx, local_tz)
    else:
        idx = idx.tz_convert("UTC")
    return raw.set_axis(idx)


def _full_year(hourly: pd.DataFrame, year: int, retrieved_at_utc: pd.Timestamp | None) -> pd.DataFrame:
    """Reindex to every hour of one UTC year, so missing months appear as empty rows.

    A file downloaded during its own year (e.g. 2026 in October) is only expected up
    to the download time, the same rule as Devika's acceptance tests (``year_window``).
    Rows that exist are never cut: the grid always reaches the last row of data.
    """
    start = pd.Timestamp(year=year, month=1, day=1, tz="UTC")
    end = pd.Timestamp(year=year + 1, month=1, day=1, tz="UTC")
    outside = hourly.index[(hourly.index < start) | (hourly.index >= end)]
    if len(outside):
        raise StepError(f"{len(outside)} hour(s) fall outside {year} UTC, e.g. {outside[0]}; is the file mislabelled?")
    if retrieved_at_utc is not None:
        end = min(end, pd.Timestamp(retrieved_at_utc, tz="UTC").floor("h"))
    if len(hourly):
        end = max(end, hourly.index[-1] + pd.Timedelta(hours=1))
    grid = pd.date_range(start, end, freq="h", inclusive="left", name="timestamp_utc")
    return hourly.reindex(grid)


def harmonise(
    raw: pd.DataFrame,
    series: str,
    zone: str,
    *,
    year: int | None = None,
    currency: str = "EUR",
    fx_rates: pd.Series | None = None,
    local_tz: str | None = None,
    source: str = "entsoe",
    retrieved_at_utc: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Turn one raw series for one zone into the standard hourly frame (see module docstring).

    ``year``: the UTC year the raw input covers. When given, the output has one row
    for every hour of that year (missing ones empty); without it, the output runs
    from the first to the last hour of data.
    ``currency`` is what the SOURCE is in; ENTSO-E is EUR. A non-EUR price needs
    ``fx_rates`` (dated ECB rates) or this raises.
    """
    spec = get_spec(series)
    zone = resolve_zone(zone)
    if currency.upper() != "EUR" and not spec.has_currency:
        raise CurrencyError(f"{series} is measured in {spec.unit}; a currency only applies to prices")

    # 1. raw layout -> standard columns, native step
    values = from_entsoe(raw, series, currency)
    # 2. UTC index (local sources are converted here, DST-aware)
    values = _to_utc_index(values, local_tz).sort_index()
    # 3. native step -> whole hours (mean for price/power, sum for energy); gaps stay NaN
    hourly = to_hourly(values, spec.how)
    if year is not None:
        hourly = _full_year(hourly, year, retrieved_at_utc)
    # 4. currency: the rate is fixed per delivery day and an hour never crosses a
    #    delivery day, so converting after aggregation gives the same result as before
    if spec.has_currency:
        original = f"price_{currency.lower()}_mwh"
        eur, fx = to_eur(hourly[original], currency, fx_rates)
        hourly["price_eur_mwh"] = eur
        hourly["currency_original"] = currency.upper()
        hourly["fx_rate_eur"] = fx.where(eur.notna())
    # 5. identification and provenance
    hourly.insert(0, "zone", zone)
    hourly["mtu_minutes"] = 60
    hourly["source"] = source
    hourly["retrieved_at_utc"] = pd.Timestamp(retrieved_at_utc, tz="UTC") if retrieved_at_utc else pd.NaT
    hourly["schema_version"] = SCHEMA_VERSION
    hourly.attrs = {"series": spec.name, "zone": zone, "quantity": spec.quantity, "unit": spec.unit,
                    "currency": "EUR" if spec.has_currency else None}
    return _order_columns(hourly)


META_COLUMNS = ["mtu_minutes", "currency_original", "fx_rate_eur", "source", "retrieved_at_utc", "schema_version"]


def _order_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Fixed column order: zone, EUR/MW value columns, original-currency price, metadata."""
    values = [c for c in frame.columns if c not in META_COLUMNS and c != "zone"]
    original_price = [c for c in values if c.startswith("price_") and c != "price_eur_mwh"]
    main = [c for c in values if c not in original_price]
    meta = [c for c in META_COLUMNS if c in frame.columns]
    return frame[["zone", *main, *original_price, *meta]]


def harmonise_file(path: str | Path, **kwargs) -> pd.DataFrame:
    """Harmonise one file laid out as ``.../SERIES/ZONE/YEAR.parquet``.

    Series, zone and year come from the path; the output covers the whole UTC year.
    """
    p = Path(path)
    if p.stem.isdigit():
        kwargs.setdefault("year", int(p.stem))
    return harmonise(pd.read_parquet(p), series=p.parent.parent.name, zone=p.parent.name, **kwargs)


def combine(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Stack harmonised frames of the same series (several zones or years) into one.

    Refuses frames that are not in EUR or not of the same series, so numbers in
    different currencies or units can never end up in one column.
    """
    if not frames:
        raise ValueError("nothing to combine")
    series = {f.attrs.get("series") for f in frames}
    if len(series) != 1 or None in series:
        raise ValueError(f"combine only stacks harmonised frames of one series; found {series}")
    for f in frames:
        assert_eur(f)
    return pd.concat(frames).sort_index(kind="stable")
