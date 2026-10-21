# ENTSO-E data coverage audit

## Scope and method

- Sample period: January of each year from 2019 through 2025.
- Areas audited: 26.
- Series: day-ahead prices, wind generation, solar generation, total load, and installed capacity by technology.
- Exclusions: Great Britain/UK and Italy are excluded from this audit for now, consistent with the current project scope. UK data sourcing and Italian price-zone selection remain future tasks.
- Time-series acceptance rule: at least 6 years with status `OK`, and the maximum reported January missing-value rate across successful sampled years must be no more than 5%.
- Installed capacity is a point-in-time snapshot, so a time-series missing-value percentage is not applicable; its availability is assessed by the number of successful sampled years. Technology-category completeness must be checked separately.
- “First available year” means the earliest year with status `OK` in this audit. It does not establish full-year availability.

## Country/area summary

Each cell reports: first available year; number of successful sampled years out of 7; maximum January missing rate; and pass/fail status. `unknown` missingness is not treated as a pass.

| Area   | Country/code   | Day-ahead prices                         | Wind generation                                            | Solar generation                                           | Total load                                                 | Installed capacity                                |
|:-------|:---------------|:-----------------------------------------|:-----------------------------------------------------------|:-----------------------------------------------------------|:-----------------------------------------------------------|:--------------------------------------------------|
| AT     | AT             | 2019; 7/7 years; max missing 0.00%; PASS | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing N/A (snapshot); PASS |
| BE     | BE             | 2019; 7/7 years; max missing 0.00%; PASS | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing N/A (snapshot); PASS |
| CZ     | CZ             | 2019; 7/7 years; max missing 0.00%; PASS | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing N/A (snapshot); PASS |
| DE_LU  | DE_LU          | 2019; 7/7 years; max missing 0.00%; PASS | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing N/A (snapshot); PASS |
| DK_1   | DK             | 2019; 7/7 years; max missing 0.00%; PASS | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing 0.13%; PASS                   | 2019; 7/7 years; max missing N/A (snapshot); PASS |
| DK_2   | DK             | 2019; 7/7 years; max missing 0.00%; PASS | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing 0.13%; PASS                   | 2019; 7/7 years; max missing N/A (snapshot); PASS |
| EE     | EE             | 2019; 6/7 years; max missing 0.00%; PASS | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing N/A (snapshot); PASS |
| ES     | ES             | 2019; 7/7 years; max missing 0.00%; PASS | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 6/7 years; max missing N/A (snapshot); PASS |
| FI     | FI             | 2019; 7/7 years; max missing 0.00%; PASS | 2019; 7/7 years; max missing 0.00%; PASS                   | 2023; 3/7 years; max missing 0.00%; FAIL: <6 years         | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing N/A (snapshot); PASS |
| FR     | FR             | 2019; 7/7 years; max missing 0.00%; PASS | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing 2.02%; PASS                   | 2019; 7/7 years; max missing N/A (snapshot); PASS |
| HU     | HU             | 2019; 7/7 years; max missing 0.00%; PASS | 2019; 7/7 years; max missing 0.00%; PASS                   | 2020; 6/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing N/A (snapshot); PASS |
| IE_SEM | IE             | 2019; 7/7 years; max missing 0.00%; PASS | —; 0/7 years; max missing unknown; FAIL: no confirmed data | —; 0/7 years; max missing unknown; FAIL: no confirmed data | —; 0/7 years; max missing unknown; FAIL: no confirmed data | 2019; 7/7 years; max missing N/A (snapshot); PASS |
| LT     | LT             | 2019; 7/7 years; max missing 0.00%; PASS | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing N/A (snapshot); PASS |
| LV     | LV             | 2019; 7/7 years; max missing 0.00%; PASS | 2019; 7/7 years; max missing 0.00%; PASS                   | 2024; 2/7 years; max missing 0.00%; FAIL: <6 years         | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing N/A (snapshot); PASS |
| NL     | NL             | 2019; 7/7 years; max missing 0.00%; PASS | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing N/A (snapshot); PASS |
| NO_1   | NO             | 2019; 7/7 years; max missing 0.00%; PASS | 2019; 7/7 years; max missing 0.00%; PASS                   | 2025; 1/7 years; max missing 0.00%; FAIL: <6 years         | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing N/A (snapshot); PASS |
| NO_2   | NO             | 2019; 7/7 years; max missing 0.00%; PASS | 2019; 7/7 years; max missing 0.00%; PASS                   | —; 0/7 years; max missing unknown; FAIL: no confirmed data | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing N/A (snapshot); PASS |
| NO_3   | NO             | 2019; 7/7 years; max missing 0.00%; PASS | 2019; 7/7 years; max missing 0.00%; PASS                   | —; 0/7 years; max missing unknown; FAIL: no confirmed data | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing N/A (snapshot); PASS |
| NO_4   | NO             | 2019; 7/7 years; max missing 0.00%; PASS | 2019; 7/7 years; max missing 0.00%; PASS                   | —; 0/7 years; max missing unknown; FAIL: no confirmed data | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing N/A (snapshot); PASS |
| NO_5   | NO             | 2019; 7/7 years; max missing 0.00%; PASS | 2019; 2/7 years; max missing 0.00%; FAIL: <6 years         | —; 0/7 years; max missing unknown; FAIL: no confirmed data | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing N/A (snapshot); PASS |
| PL     | PL             | 2019; 7/7 years; max missing 0.00%; PASS | 2019; 7/7 years; max missing 0.00%; PASS                   | 2021; 5/7 years; max missing 0.00%; FAIL: <6 years         | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing N/A (snapshot); PASS |
| PT     | PT             | 2019; 7/7 years; max missing 0.00%; PASS | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing N/A (snapshot); PASS |
| SE_1   | SE             | 2019; 7/7 years; max missing 0.00%; PASS | 2019; 7/7 years; max missing 0.00%; PASS                   | 2022; 4/7 years; max missing 0.00%; FAIL: <6 years         | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing N/A (snapshot); PASS |
| SE_2   | SE             | 2019; 7/7 years; max missing 0.00%; PASS | 2019; 7/7 years; max missing 0.00%; PASS                   | 2022; 4/7 years; max missing 0.00%; FAIL: <6 years         | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing N/A (snapshot); PASS |
| SE_3   | SE             | 2019; 7/7 years; max missing 0.00%; PASS | 2019; 7/7 years; max missing 0.00%; PASS                   | 2022; 4/7 years; max missing 0.00%; FAIL: <6 years         | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing N/A (snapshot); PASS |
| SE_4   | SE             | 2019; 7/7 years; max missing 0.00%; PASS | 2019; 7/7 years; max missing 0.00%; PASS                   | 2022; 4/7 years; max missing 0.00%; FAIL: <6 years         | 2019; 7/7 years; max missing 0.00%; PASS                   | 2019; 7/7 years; max missing N/A (snapshot); PASS |

## Raw query statuses

- `NoMatchingDataError`: 69 records
- `OK`: 824 records
- `REVIEW_RESOLUTION`: 15 records
- `ReadTimeout`: 2 records

## Installed-capacity cross-check


The capacity detail file `capacity_values_detail(3).csv` contains 1657 records across 18 country codes and 7 years. Technology categories observed include: Biomass, Energy storage, Fossil Brown coal/Lignite, Fossil Coal-derived gas, Fossil Gas, Fossil Hard coal, Fossil Oil, Fossil Oil shale, Fossil Peat, Geothermal, Hydro Pumped Storage, Hydro Run-of-river and pondage, Hydro Water Reservoir, Marine, Nuclear, Other, Other renewable, Solar, Waste, Wind Offshore, Wind Onshore. Verify that the wind and solar capacity categories are present for each intended market; the presence of any capacity record does not by itself prove all technology categories are complete.


## Interpretation and limitations

- `PASS` means the series meets the audit rule above based on the current January samples; it does not guarantee uninterrupted availability throughout every full year.
- `NO_MATCH` / `NoMatchingDataError` means the API returned no matching dataset for the query. Do not interpret this as zero generation or zero capacity.
- `REVIEW_RESOLUTION` requires checking the returned time interval and expected observation count before deciding whether the series passes.
- `ReadTimeout` is an unresolved request failure, not evidence that data are unavailable. Retry these queries before excluding a market.
- For generation data, confirm that the API response is filtered to the intended technology and that missingness is calculated for the target series, not merely for any non-null column in a multi-column response.
- Before using this audit for final market selection, manually review all non-`PASS` cells and confirm technology-specific capacity completeness.

## Generated files

- Summary table: `docs/sources/entsoe-coverage-summary.csv`
- Detailed table: `docs/sources/entsoe-coverage-detail.csv`
- This report: `docs/sources/entsoe-coverage.md`
