# Tier 1 screen dataset (PW03-CD-01, Part A)

Built with `python -m harmonise.build_screen` from `data/raw/entsoe/`. Thirteen zones: SE3, NL, DE-LU, ES, the seven Italian zones, PL and LT, 2019–2025. Onshore wind only.

| File | What it holds |
| --- | --- |
| `hourly/<ZONE>.parquet` | One hourly UTC frame per zone, 2019–2025 by market-time year: `price_eur_mwh`, `load_mw`, `gen_wind_onshore_mw`, `gen_solar_mw`. An hour is empty unless fully covered; nothing is filled. |
| `native_prices/<ZONE>.parquet` | Day-ahead prices in their source step (hourly, 15 minutes from 1 Oct 2025) with `mtu_minutes`, for negative-price time and daily spreads. |
| `coverage.csv` | One row per zone, series and year: missing hours, longest gap, and whether the year passes the 98 % rule of the metric dictionary. Years are delivery years in CET/CEST. |
| `data_test_log.csv` | Every error and warning from the six data tests on the raw files. Nothing was fixed. |

## What the coverage table shows

Prices and load are complete everywhere (the worst is Spain 2025 load, 36 hours missing in the 28 April 2025 blackout). The gaps are all in wind and solar:

- **No data:** SE3 solar 2019–2021, Poland wind 2019, Poland solar 2019 and most of 2020. Italy CALA has nothing before 2021 because the zone was created on 1 January 2021; that is expected, not a gap.
- **A missing month:** Italy CSUD wind October 2025, Sardinia wind July 2024.
- **Sardinia solar:** Oct–Dec missing in 2021 and 2022, then 10–14 % of hours missing in 2023–2024, scattered around sunset and sunrise. This looks like night-time zeros reported as empty.

20 of 364 zone-series-years fall below 98 %; 8 of them are the expected Italy CALA years.

## Reading the data test log

- **Units:** fails on every raw file, because raw ENTSO-E columns are called `value` and `Actual Load`. The unit-in-name rule applies to the harmonised output, which passes it. The check also crashes on raw columns stored as pairs, e.g. `('Solar', 'Actual Aggregated')`.
- **Completeness errors for DE-LU 2021 and 2025** are not real gaps. Those files spell the same column two ways in different months; the tests judge each spelling separately, while the harmonisation joins them. The harmonised years are complete.
- **Clock-change errors** come from single missing or extra hours around the clock change (e.g. SE3 wind and solar 27 March 2022 has 22 hours), or from gappy days that look like short days (Sardinia solar).
- **Repeated values over 24 hours** in Italian wind (NORD, CNOR) and Dutch wind self-consumption: possible filled gaps in the source, kept as they are.
