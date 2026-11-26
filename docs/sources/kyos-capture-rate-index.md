# KYOS Capture Rate Index

Monthly capture rates and capture prices for solar, onshore wind and offshore
wind, published by KYOS. We use them as an external reference to check our own
Gate 2 capture rates (`metrics/gate2.py`). We do not use them as an input to
any gate.

## Source

- Page: https://power.kyos.com/capture-rates
- Publisher: KYOS Energy Analytics (public page, no login)
- Fetched with: `ingest/kyos.py`
- Snapshot in this repo: fetched 2026-11-26, months 2016-01 to 2026-10

The numbers come from the endpoint behind the page's charts
(`POST /api/chart-data`). KYOS does not document it, so the request or response
format may change without notice. If the script stops working, the CSVs in
`data/raw/kyos/` remain the reference snapshot.

## What KYOS measures

- **Capture price** = generation-weighted average day-ahead price over the month (EUR/MWh).
- **Capture rate** = capture price / baseload price (%).
- **Negative prices:** hours with a negative price earn zero revenue, but their
  volume still counts in the denominator.
- **Generation profile:** KYOS uses its own profile per zone and technology. It
  does not publish the profile, so we cannot reproduce its numbers exactly.

KYOS only publishes monthly and rolling 12-month values. There is no hourly or
daily data.

## How it differs from our Gate 2 capture rate

| | KYOS | Gate 2 (`metrics/gate2.py`) |
|---|---|---|
| Generation | KYOS's own profile | ENTSO-E actual generation for the zone |
| Negative-price hours | Revenue set to 0, volume kept | Two variants: all hours, or P ≥ 0 hours only in the capture price |
| Hours used | Not stated | Only hours where both price and generation exist; month valid at ≥ 98 % |
| Resolution | Monthly, rolling yearly | Hourly input, monthly or yearly output |

The two series move together but are not the same. Over 2019–2025, KYOS reads
on average 1 to 3 percentage points below Gate 2 in most zones, 5.0 below in
SE3 and 7.7 below in ES. It reads above Gate 2 in IT-SUD, IT-SICI and IT-SARD.
The generation profile is the most likely cause; this is not yet confirmed.

## Zone codes

KYOS codes differ from ENTSO-E names. Files are grouped by the first two
letters of the KYOS code.

| KYOS code | ENTSO-E zone | File |
|---|---|---|
| SE1, SE2, SE3, SE4 | SE_1 … SE_4 | `SE/SE3_kyos_monthly.csv` |
| DE | DE-LU | `DE/DE_kyos_monthly.csv` |
| NL | NL | `NL/NL_kyos_monthly.csv` |
| ES | ES | `ES/ES_kyos_monthly.csv` |
| PL | PL | `PL/PL_kyos_monthly.csv` |
| LT | LT | `LT/LT_kyos_monthly.csv` |
| ITNO, ITCN, ITCS, ITSU, ITCA, ITSI, ITSA | IT-NORD, IT-CNOR, IT-CSUD, IT-SUD, IT-CALA, IT-SICI, IT-SARD | `IT/ITNO_kyos_monthly.csv` … |

All 13 screen zones are covered. SE1, SE2 and SE4 are extra.

## File format

`data/raw/kyos/<COUNTRY>/<CODE>_kyos_monthly.csv`, long format, one row per
zone, technology and month:

| Column | Type | Meaning |
|---|---|---|
| zone | str | KYOS code, e.g. `SE3`, `ITNO` |
| technology | str | `solar`, `onshore` or `offshore` |
| month | `YYYY-MM` | Delivery month |
| capture_rate_pct | float | Capture rate, % of baseload |
| capture_price_eur_mwh | float | Capture price, EUR/MWh |

## Known gaps

- ITCS onshore: Dec 2022 and Dec 2023 are missing on KYOS.
- Offshore values exist for zones with little or no offshore fleet (e.g. SE3).
  Treat them as KYOS's modelled profile, not as observed output.

## Updating

    python ingest/kyos.py                  # all 16 areas
    python ingest/kyos.py --zones SE3 DE   # a subset

The script pauses 1 s between requests. Re-run it monthly and commit the new
CSVs with the fetch date in the commit message.
