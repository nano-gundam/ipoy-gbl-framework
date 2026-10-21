# PW01-MV-02: Acceptance tests for downloaded data

Entry checks that every file in `data/raw/entsoe/SERIES/ZONE/YEAR.parquet` must pass before it reaches the model. The first target is Lingyu's calibration download (PW01-CD-07). Built on Hsiang-Wei's draft rules (PW01-CD-04).

**Status:** written and verified on fake data. **Not yet run on Lingyu's real files, and the pull request is not yet opened.**

## Files

| File | Purpose |
|---|---|
| `tests/test_data_acceptance.py` | Everything in one file: the check functions, the six tests on real files, the self-check (one deliberate error per check) and the fake-data writer. |
| `tests/config/day_ahead_price_limits.csv` | Legal day-ahead min/max price by date, with sources. |
| `tests/config/known_capacity_drops.csv` | Plant closures that explain a drop in installed capacity (empty for now). Columns: `zone,column,year,reason`. |
| `tests/fake_data/` | The fake files, one folder per case, in the real layout, with `manifest.csv` naming the check each must trigger (4.9 MB). |

Requires `pandas`, `pyarrow`, `pytest`.

## How to run

```
pytest tests/test_data_acceptance.py                      # everything
pytest tests/test_data_acceptance.py -k "not selfcheck"   # only the real data under data/raw/entsoe
pytest tests/test_data_acceptance.py -k selfcheck         # proof the checks work (no data needed)
pytest tests/test_data_acceptance.py -k "SE3 and 2024"    # one zone / year
ACCEPTANCE_DATA_ROOT=/other/path pytest tests/test_data_acceptance.py
python tests/test_data_acceptance.py --write-fake-data    # rewrite tests/fake_data
```

Hard failures are test failures. Soft findings (0.5-2 % missing, missing previous-year file) appear under "warnings summary". Each failure names the file, the check and where the problem is.

## The six tests (each takes one file)

| Test | Fails when | Notes |
|---|---|---|
| `test_timestamps` | Not timezone-aware UTC; not increasing; duplicates; timestamps outside the file's year; more than one step; `mtu_minutes` disagrees with the timestamps | Steps allowed: 15 or 60 min. A stretch of 4+ regular larger intervals counts as a second step; a single large interval is a gap (completeness handles it). |
| `test_completeness` | More than 2 % of values missing in any column | Expected 8,760 / 8,784 values per year, x4 for 15-minute data. Warns above 0.5 %. Lists every gap (first 10 shown). Null values count as missing. A file downloaded part-way through its year is judged up to `retrieved_at_utc`. |
| `test_clock_changes` | Not exactly one 23-hour day in March and one 25-hour day in October, on the right Sundays | Converted to Europe/Berlin (market time, per CD-04). First and last local day are ignored (cut by the UTC year boundary). |
| `test_plausible_values` | Day-ahead price outside the legal limits for that date; generation or demand below 0; installed capacity drops with no listed closure | Price check applies to series whose folder name contains `day_ahead`. Capacity check compares with the previous year's file; if it is missing, only a warning. |
| `test_no_silent_gap_filling` | Same value repeated for more than 24 hours | Exactly 24 h passes, 25 h fails. Runs of exactly 0 are ignored (night-time solar). |
| `test_units_in_column_names` | A value column has no unit in its name, or its numbers are the wrong size for that unit | Magnitude uses the 99th percentile of the absolute values. Catches EUR/kWh stored as EUR/MWh, GW or kW stored as MW. Cannot catch ct/kWh (looks like a plausible EUR/MWh). |

## Proof that each test catches its error

Fake files are built in code (`test_selfcheck_*`) and also stored in `tests/fake_data/`. Every case contains one deliberate error, and the matching check must fail on it.

| Check | Deliberate errors |
|---|---|
| timestamps | naive (non-UTC) timestamps; duplicated hour; rows out of order; one row shifted by 30 min; 60/15-minute mix in a 2024 file (with and without `mtu_minutes`); wrong `mtu_minutes` |
| completeness | 3 % of rows deleted; a 10-day gap; 3 % nulls |
| clock changes | one October hour lost (24-hour day; only this check sees it, completeness passes); local wall-clock time labelled as UTC |
| plausible values | price 3,500 in 2021; price -600; negative generation; negative demand; capacity drop (and the same drop accepted once listed as a known closure) |
| silent gap-filling | 25 identical hours (price); 40 identical hours (generation) |
| units | price column named `price`; `gen_wind` without unit; price in EUR/kWh; load in GW; generation in kW |

Boundary and no-false-alarm tests also pass: 24 identical hours allowed; a zero run allowed; 1 % missing warns but passes; UTC-year edges not mistaken for short days; price limits switch exactly at the right hour (below).

**Verification run**
- 81 passed, 6 skipped (the six real-data tests, skipped because no data is present), on pandas 3.0.2 and on pandas 2.2.3.
- Mutation check: loosening the completeness threshold, the repeat threshold and the load-unit rule each made the matching self-check fail.

## Day-ahead price limits (SDAC)

| Valid from (UTC) | Min | Max | Source |
|---|---|---|---|
| 2018-01-01 | -500 | 3,000 | ACER Decision 04/2017 |
| 2022-05-10 22:00 (delivery 11 May 2022) | -500 | 4,000 | automatic rise after the 3 Apr 2022 trigger |
| 2022-09-20 22:00 (delivery 21 Sep 2022) | -500 | 5,000 | automatic rise after 4,000 EUR/MWh in LT/LV/EE on 17 Aug 2022 (Nord Pool operational message, 23 Aug 2022) |

**Correction to my earlier draft:** it stopped at 4,000 and would have wrongly failed valid prices between 4,000 and 5,000 in late 2022.

**Still open:** ACER Decisions 01/2023 and 02/2026 set a 4,000 reference value with an automatic +500 step. I could not confirm the date the cap actually returned to 4,000, nor whether any later automatic change occurred, so the table stays at 5,000 for all later dates (permissive: it never gives a false failure, but would miss a value between 4,000 and 5,000 after the reset). Market Research should confirm and tighten. The check only covers SDAC zones.

## Assumptions to confirm (all editable in section 1 of the test file)

1. **Timestamp column** is `timestamp_utc`, marks the START of the interval, and a file holds one UTC calendar year. CD-04 does not fix any of these three.
2. **The 2025 day-ahead file may switch once from 60 to 15 minutes** (SDAC, delivery from 1 Oct 2025, 22:00 UTC on 30 Sep). This contradicts "one fixed step per file", but the market really switched. Every other file must have exactly one step.
3. **Series folder names** contain `day_ahead`, `generation`, `load` / `demand`, `capacity`.
4. **Runs of exactly 0** are not flagged as silent filling.
5. **Unit columns:** CD-04 section 3 keeps columns such as `value_eur` / `value_original`, while section 7 requires a unit in every column name. The units test follows section 7 and will fail on such columns. Hsiang-Wei should decide which rule wins.

## Known limitations

- Never run on the real calibration download.
- A unit given in ct/kWh, or a small-size error inside the normal range, is not detected.
- Installed-capacity check needs the previous year's file next to it.
- The "exactly one 23-hour / 25-hour day" check counts any such day, so an unrelated one-hour gap on another day also fails it (the message names the dates).

## Pull request (to open) and message to Lingyu

**PR title:** PW01-MV-02: acceptance tests for downloaded data

**PR description:** Entry checks for every file under `data/raw/entsoe/SERIES/ZONE/YEAR.parquet` (timestamps, completeness, clock changes, plausible values, silent gap-filling, units). One file, `tests/test_data_acceptance.py`, plus price-limit and closure tables in `tests/config/` and fake files in `tests/fake_data/`. Run `pytest tests/test_data_acceptance.py -k selfcheck` to see that each check catches its deliberate error. Five assumptions need confirming (section above).

**Message to Lingyu:** The acceptance tests for CD-07 are in the PR. After each download, run `pytest tests/test_data_acceptance.py -k "not selfcheck"`. A failure names the file, the check and where the problem is. Please tell me if your files use a different timestamp column name, or if the series folder names differ from `day_ahead...`, `generation...`, `load...`, `installed_capacity...`.

**Done when:** the PR is merged and the first run on Lingyu's real download has been reviewed.
