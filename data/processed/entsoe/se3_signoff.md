# SE3 sign-off (PW03-CD-01)

To: Devika · From: Fernando Monárdez · 15 Nov 2026

**Signed off:** SE3 day-ahead prices, total load and onshore wind for 2019 to 2025, and solar for 2022 to 2025. The solar capture rate for SE3 is therefore only counted from 2022.

## What was checked

The aim was to confirm that the screen dataset (`hourly/SE3.parquet` and `native_prices/SE3.parquet`, built with `python -m harmonise.build_screen`) gives the same numbers as the SE3 2024 reference values in `docs/methods/metric-dictionary-v0.md`, section 7.

1. **Input prices.** The 72 hours of 27 to 29 July 2024 (CEST) were cut from both files and compared with `tests/fixtures/se3_2024-07-27_29_entsoe.csv`. All 72 timestamps match, the window starts at 27 Jul 00:00 CEST (26 Jul 22:00 UTC), and the largest difference is 7e-15 EUR/MWh, which is floating-point noise.
2. **Reference results.** `tests/hand_check_se3_2024.py` was run on the slice from our hourly file. Every value matches section 7:

| Indicator | Result | Reference |
|---|---|---|
| Price mean, 72 h | 9.162083 | 9.162083 |
| Hourly std (n − 1) | 14.292575 | 14.292575 |
| Std of daily change (n − 1) | 13.043468 | 13.043468 |
| Negative hours | 21 | 21 |
| Mean negative price | −7.272381 | −7.272381 |
| Spread 2h | 29.478333 | 29.478333 |
| Spread 4h | 25.420833 | 25.420833 |

These numbers come from the hand-check script, not from the Gate 2 code, which is the next step. The same comparison will be repeated once the indicators are coded in `metrics/`.

3. **Coverage and data tests.** `coverage.csv` and `data_test_log.csv` were read for every SE3 series and year.

## Why the sign-off is partial

The acceptance criterion was that every data test passes. For SE3 this is not possible, for the following reasons:

- **Solar 2019 to 2021.** No raw file was downloaded for 2019 or 2020, and 2021 is 95 % empty (data only from 14 Dec 2021). None of these years passes the 98 % rule, so the solar indicators for SE3 are empty for 2019 to 2021.
- **27 March 2022.** Wind and solar each miss one hour (22:00 UTC), so the clock-change test finds a 22-hour day instead of a 23-hour one. Both years still pass the 98 % rule with one missing hour.
- **Units check.** It fails on all 26 SE3 raw files because raw columns are named `value`, `Actual Load`, `Wind Onshore` and `Solar`. The harmonised output uses `price_eur_mwh`, `load_mw`, `gen_wind_onshore_mw` and `gen_solar_mw`, so I believe the check is meant for the output, not the raw files. I would suggest we confirm this together.

Two further points do not block the sign-off, but could matter for later steps:

- **First hour of 2019.** Prices, load and wind miss 1 Jan 2019 00:00 CET. The raw files are split by UTC year, and this hour sits in the 2018 file, which was not downloaded. The same hour is missing in all 13 zones.
- **15-minute load and generation from 1 Dec 2025.** SE3 load, wind and solar switch to a 15-minute step on 1 Dec 2025, which is separate from the 1 Oct 2025 day-ahead switch. The hourly file averages these correctly, and the data test accepts it as a warning.

## Next steps

The Gate 2 indicators will be coded in `metrics/`, with Fixtures A to D as unit tests and this SE3 check repeated on the real code. We will then compute them for all 13 zones from 2019 to 2025.
