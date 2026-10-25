# Forward-price table, evaluation date 2026-10-23

File: `forward_prices_2026-10-23.csv` · built 2026-10-25 14:12 UTC from `power_futures.sqlite` · forward-prices-0.1

Window for `avg_2m`: trade dates 2026-08-24 to 2026-10-23 (45 weekdays). Archive span: EEX 2026-08-06 to 2026-10-23; EURONEXT 2026-09-18 to 2026-10-23.

657 contracts in 24 zones, 407 flagged thin (100 with missing days, 391 with no traded volume). 655 single-day check rows.

## Zones

| zone | contracts | cal_years | thin | source |
| --- | --- | --- | --- | --- |
| AT | 52 | Cal-2027, Cal-2028, Cal-2029, Cal-2030, Cal-2031, Cal-2032 | 36 | EEX |
| BE | 19 | Cal-2027, Cal-2028, Cal-2029, Cal-2030, Cal-2031, Cal-2032 | 7 | EEX |
| CZ | 38 | Cal-2027, Cal-2028, Cal-2029, Cal-2030, Cal-2031, Cal-2032 | 24 | EEX |
| DE-LU | 71 | Cal-2027, Cal-2028, Cal-2029, Cal-2030, Cal-2031, Cal-2032, Cal-2033, Cal-2034, Cal-2035, Cal-2036 | 26 | EEX |
| DK1 | 19 | Cal-2027, Cal-2028, Cal-2029, Cal-2030, Cal-2031, Cal-2032 | 11 | EEX |
| DK2 | 19 | Cal-2027, Cal-2028, Cal-2029, Cal-2030, Cal-2031, Cal-2032 | 10 | EEX |
| ES | 27 | Cal-2027, Cal-2028, Cal-2029, Cal-2030, Cal-2031, Cal-2032, Cal-2033, Cal-2034, Cal-2035, Cal-2036 | 7 | EEX |
| FI | 19 | Cal-2027, Cal-2028, Cal-2029, Cal-2030, Cal-2031, Cal-2032 | 13 | EEX |
| FR | 56 | Cal-2027, Cal-2028, Cal-2029, Cal-2030, Cal-2031, Cal-2032, Cal-2033, Cal-2034, Cal-2035, Cal-2036 | 16 | EEX |
| GR | 19 | Cal-2027, Cal-2028, Cal-2029, Cal-2030, Cal-2031, Cal-2032 | 8 | EEX |
| HU | 38 | Cal-2027, Cal-2028, Cal-2029, Cal-2030, Cal-2031, Cal-2032 | 25 | EEX |
| IE-SEM | 19 | Cal-2027, Cal-2028, Cal-2029, Cal-2030, Cal-2031, Cal-2032 | 11 | EEX |
| LT | 10 | Cal-2027, Cal-2028, Cal-2029 | 10 | EURONEXT |
| NL | 42 | Cal-2027, Cal-2028, Cal-2029, Cal-2030, Cal-2031, Cal-2032, Cal-2033, Cal-2034, Cal-2035, Cal-2036 | 17 | EEX |
| NO1 | 19 | Cal-2027, Cal-2028, Cal-2029, Cal-2030, Cal-2031, Cal-2032 | 17 | EEX |
| NO2 | 19 | Cal-2027, Cal-2028, Cal-2029, Cal-2030, Cal-2031, Cal-2032 | 19 | EEX |
| NO3 | 19 | Cal-2027, Cal-2028, Cal-2029, Cal-2030, Cal-2031, Cal-2032 | 17 | EEX |
| NO4 | 19 | Cal-2027, Cal-2028, Cal-2029, Cal-2030, Cal-2031, Cal-2032 | 17 | EEX |
| NO5 | 19 | Cal-2027, Cal-2028, Cal-2029, Cal-2030, Cal-2031, Cal-2032 | 19 | EEX |
| PL | 38 | Cal-2027, Cal-2028, Cal-2029, Cal-2030, Cal-2031, Cal-2032 | 34 | EEX |
| SE1 | 19 | Cal-2027, Cal-2028, Cal-2029, Cal-2030, Cal-2031, Cal-2032 | 18 | EEX |
| SE2 | 19 | Cal-2027, Cal-2028, Cal-2029, Cal-2030, Cal-2031, Cal-2032 | 13 | EEX |
| SE3 | 19 | Cal-2027, Cal-2028, Cal-2029, Cal-2030, Cal-2031, Cal-2032 | 15 | EEX |
| SE4 | 19 | Cal-2027, Cal-2028, Cal-2029, Cal-2030, Cal-2031, Cal-2032 | 17 | EEX |

## Futures areas left out (no row in harmonise/zones.csv)

BG (900 obs.), CH (1800 obs.), GB (1260 obs.), HR (1800 obs.), IT (2340 obs.), RO (1800 obs.), RS (900 obs.), SI (1800 obs.), SK (1800 obs.)

## Collector runs in the window that did not end ok

_none_

## Archive days missing in the window (weekdays with no rows at all)

- EEX: 0 — none
- EURONEXT: 24 — 2026-08-24, 2026-08-25, 2026-08-26, 2026-08-27, 2026-08-28, 2026-08-31, 2026-09-01, 2026-09-02, 2026-09-03, 2026-09-04, 2026-09-07, 2026-09-08, 2026-09-09, 2026-09-10, 2026-09-11, 2026-09-14, 2026-09-15, 2026-09-16, 2026-09-17, 2026-09-23, 2026-09-24, 2026-09-29, 2026-09-30, 2026-10-01

Euronext readings not used because they are not that day's settlement (no stamp, a stamp from an earlier day, or stamped before 15:00 CET), counted only for contracts EEX does not list: 45.

## Single day against two-month average: 395 of 655 contracts differ by more than 10%

Largest differences, Cal contracts:

| zone | product | maturity_type | delivery_period | avg_2m | single_day | diff_eur_mwh | diff_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ES | base | Year | Cal-2027 | 93.02 | 128.25 | 35.23 | 37.88 |
| FR | base | Year | Cal-2027 | 90.30 | 117.44 | 27.14 | 30.05 |
| FR | peak | Year | Cal-2027 | 99.26 | 124.73 | 25.47 | 25.66 |
| IE-SEM | base | Year | Cal-2027 | 169.76 | 207.00 | 37.24 | 21.94 |
| IE-SEM | base | Year | Cal-2028 | 130.16 | 158.00 | 27.84 | 21.39 |
| BE | base | Year | Cal-2027 | 128.07 | 152.92 | 24.85 | 19.41 |
| DK1 | base | Year | Cal-2027 | 124.48 | 148.26 | 23.78 | 19.10 |
| NL | base | Year | Cal-2027 | 128.49 | 152.75 | 24.26 | 18.88 |
| DK2 | base | Year | Cal-2027 | 125.66 | 149.01 | 23.35 | 18.59 |
| AT | base | Year | Cal-2027 | 144.16 | 170.06 | 25.90 | 17.96 |
| DE-LU | base | Year | Cal-2027 | 131.00 | 154.42 | 23.42 | 17.88 |
| NO5 | base | Year | Cal-2027 | 85.79 | 101.01 | 15.22 | 17.74 |
| GR | base | Year | Cal-2027 | 129.13 | 151.70 | 22.57 | 17.48 |
| NL | peak | Year | Cal-2027 | 137.96 | 161.78 | 23.82 | 17.26 |
| CZ | base | Year | Cal-2027 | 137.74 | 161.17 | 23.43 | 17.01 |

Largest differences, all contracts:

| zone | product | maturity_type | delivery_period | avg_2m | single_day | diff_eur_mwh | diff_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| NO4 | base | Month | Mar-2027 | 20.09 | 37.10 | 17.01 | 84.68 |
| SE1 | base | Month | Mar-2027 | 40.73 | 70.13 | 29.40 | 72.20 |
| SE2 | base | Month | Mar-2027 | 33.13 | 56.79 | 23.66 | 71.44 |
| FR | peak | Month | May-2027 | 32.52 | 50.55 | 18.03 | 55.45 |
| FR | peak | Month | Apr-2027 | 49.69 | 74.57 | 24.88 | 50.06 |
| FR | peak | Quarter | Q2-2027 | 42.73 | 63.24 | 20.51 | 48.00 |
| ES | base | Quarter | Q2-2027 | 63.05 | 93.00 | 29.95 | 47.50 |
| FR | base | Month | Jun-2027 | 46.37 | 68.22 | 21.85 | 47.11 |
| FR | base | Month | Apr-2027 | 68.47 | 99.92 | 31.45 | 45.92 |
| FR | base | Quarter | Q2-2027 | 52.74 | 76.96 | 24.22 | 45.91 |
| ES | base | Quarter | Q3-2027 | 91.09 | 129.00 | 37.91 | 41.62 |
| FR | peak | Quarter | Q3-2027 | 57.21 | 80.01 | 22.80 | 39.86 |
| FR | base | Quarter | Q3-2027 | 66.84 | 93.02 | 26.18 | 39.16 |
| FR | base | Month | May-2027 | 45.78 | 63.20 | 17.42 | 38.05 |
| ES | base | Year | Cal-2027 | 93.02 | 128.25 | 35.23 | 37.88 |

## Thin Cal contracts

| zone | product | delivery_period | settlement_days_used | settlement_days_expected | traded_volume_mwh | source |
| --- | --- | --- | --- | --- | --- | --- |
| AT | base | Cal-2030 | 45 | 45 |  | EEX |
| AT | base | Cal-2031 | 45 | 45 |  | EEX |
| AT | base | Cal-2032 | 45 | 45 |  | EEX |
| AT | peak | Cal-2028 | 45 | 45 |  | EEX |
| AT | peak | Cal-2029 | 45 | 45 |  | EEX |
| AT | peak | Cal-2030 | 45 | 45 |  | EEX |
| AT | peak | Cal-2031 | 45 | 45 |  | EEX |
| AT | peak | Cal-2032 | 45 | 45 |  | EEX |
| BE | base | Cal-2031 | 45 | 45 |  | EEX |
| BE | base | Cal-2032 | 45 | 45 |  | EEX |
| CZ | base | Cal-2030 | 45 | 45 |  | EEX |
| CZ | base | Cal-2031 | 45 | 45 |  | EEX |
| CZ | base | Cal-2032 | 45 | 45 |  | EEX |
| CZ | peak | Cal-2030 | 45 | 45 |  | EEX |
| CZ | peak | Cal-2031 | 45 | 45 |  | EEX |
| CZ | peak | Cal-2032 | 45 | 45 |  | EEX |
| DE-LU | peak | Cal-2032 | 45 | 45 |  | EEX |
| DK1 | base | Cal-2029 | 45 | 45 |  | EEX |
| DK1 | base | Cal-2030 | 45 | 45 |  | EEX |
| DK1 | base | Cal-2031 | 45 | 45 |  | EEX |
| DK1 | base | Cal-2032 | 45 | 45 |  | EEX |
| DK2 | base | Cal-2029 | 45 | 45 |  | EEX |
| DK2 | base | Cal-2030 | 45 | 45 |  | EEX |
| DK2 | base | Cal-2031 | 45 | 45 |  | EEX |
| DK2 | base | Cal-2032 | 45 | 45 |  | EEX |
| FI | base | Cal-2028 | 45 | 45 |  | EEX |
| FI | base | Cal-2029 | 45 | 45 |  | EEX |
| FI | base | Cal-2030 | 45 | 45 |  | EEX |
| FI | base | Cal-2031 | 45 | 45 |  | EEX |
| FI | base | Cal-2032 | 45 | 45 |  | EEX |
| FR | peak | Cal-2031 | 45 | 45 |  | EEX |
| FR | peak | Cal-2032 | 45 | 45 |  | EEX |
| HU | base | Cal-2032 | 45 | 45 |  | EEX |
| HU | peak | Cal-2027 | 45 | 45 |  | EEX |
| HU | peak | Cal-2028 | 45 | 45 |  | EEX |
| HU | peak | Cal-2029 | 45 | 45 |  | EEX |
| HU | peak | Cal-2030 | 45 | 45 |  | EEX |
| HU | peak | Cal-2031 | 45 | 45 |  | EEX |
| HU | peak | Cal-2032 | 45 | 45 |  | EEX |
| IE-SEM | base | Cal-2027 | 45 | 45 |  | EEX |
| IE-SEM | base | Cal-2028 | 45 | 45 |  | EEX |
| IE-SEM | base | Cal-2029 | 45 | 45 |  | EEX |
| IE-SEM | base | Cal-2030 | 45 | 45 |  | EEX |
| IE-SEM | base | Cal-2031 | 45 | 45 |  | EEX |
| IE-SEM | base | Cal-2032 | 45 | 45 |  | EEX |
| LT | base | Cal-2027 | 20 | 45 |  | EURONEXT |
| LT | base | Cal-2028 | 5 | 45 |  | EURONEXT |
| LT | base | Cal-2029 | 3 | 45 |  | EURONEXT |
| NL | base | Cal-2032 | 45 | 45 |  | EEX |
| NL | base | Cal-2033 | 45 | 45 |  | EEX |
| NL | base | Cal-2034 | 45 | 45 |  | EEX |
| NL | base | Cal-2035 | 45 | 45 |  | EEX |
| NL | base | Cal-2036 | 45 | 45 |  | EEX |
| NL | peak | Cal-2030 | 45 | 45 |  | EEX |
| NL | peak | Cal-2031 | 45 | 45 |  | EEX |
| NL | peak | Cal-2032 | 45 | 45 |  | EEX |
| NO1 | base | Cal-2027 | 45 | 45 |  | EEX |
| NO1 | base | Cal-2028 | 45 | 45 |  | EEX |
| NO1 | base | Cal-2029 | 45 | 45 |  | EEX |
| NO1 | base | Cal-2031 | 45 | 45 |  | EEX |
| NO1 | base | Cal-2032 | 45 | 45 |  | EEX |
| NO2 | base | Cal-2027 | 45 | 45 |  | EEX |
| NO2 | base | Cal-2028 | 45 | 45 |  | EEX |
| NO2 | base | Cal-2029 | 45 | 45 |  | EEX |
| NO2 | base | Cal-2030 | 45 | 45 |  | EEX |
| NO2 | base | Cal-2031 | 45 | 45 |  | EEX |
| NO2 | base | Cal-2032 | 45 | 45 |  | EEX |
| NO3 | base | Cal-2027 | 45 | 45 |  | EEX |
| NO3 | base | Cal-2028 | 45 | 45 |  | EEX |
| NO3 | base | Cal-2029 | 45 | 45 |  | EEX |
| NO3 | base | Cal-2030 | 45 | 45 |  | EEX |
| NO3 | base | Cal-2031 | 45 | 45 |  | EEX |
| NO3 | base | Cal-2032 | 45 | 45 |  | EEX |
| NO4 | base | Cal-2028 | 45 | 45 |  | EEX |
| NO4 | base | Cal-2029 | 45 | 45 |  | EEX |
| NO4 | base | Cal-2030 | 45 | 45 |  | EEX |
| NO4 | base | Cal-2031 | 45 | 45 |  | EEX |
| NO4 | base | Cal-2032 | 45 | 45 |  | EEX |
| NO5 | base | Cal-2027 | 45 | 45 |  | EEX |
| NO5 | base | Cal-2028 | 45 | 45 |  | EEX |
| NO5 | base | Cal-2029 | 45 | 45 |  | EEX |
| NO5 | base | Cal-2030 | 45 | 45 |  | EEX |
| NO5 | base | Cal-2031 | 45 | 45 |  | EEX |
| NO5 | base | Cal-2032 | 45 | 45 |  | EEX |
| PL | base | Cal-2027 | 45 | 45 |  | EEX |
| PL | base | Cal-2028 | 45 | 45 |  | EEX |
| PL | base | Cal-2029 | 45 | 45 |  | EEX |
| PL | base | Cal-2030 | 45 | 45 |  | EEX |
| PL | base | Cal-2031 | 45 | 45 |  | EEX |
| PL | base | Cal-2032 | 45 | 45 |  | EEX |
| PL | peak | Cal-2027 | 45 | 45 |  | EEX |
| PL | peak | Cal-2028 | 45 | 45 |  | EEX |
| PL | peak | Cal-2029 | 45 | 45 |  | EEX |
| PL | peak | Cal-2030 | 45 | 45 |  | EEX |
| PL | peak | Cal-2031 | 45 | 45 |  | EEX |
| PL | peak | Cal-2032 | 45 | 45 |  | EEX |
| SE1 | base | Cal-2027 | 45 | 45 |  | EEX |
| SE1 | base | Cal-2028 | 45 | 45 |  | EEX |
| SE1 | base | Cal-2029 | 45 | 45 |  | EEX |
| SE1 | base | Cal-2030 | 45 | 45 |  | EEX |
| SE1 | base | Cal-2031 | 45 | 45 |  | EEX |
| SE1 | base | Cal-2032 | 45 | 45 |  | EEX |
| SE2 | base | Cal-2028 | 45 | 45 |  | EEX |
| SE2 | base | Cal-2029 | 45 | 45 |  | EEX |
| SE2 | base | Cal-2030 | 45 | 45 |  | EEX |
| SE2 | base | Cal-2031 | 45 | 45 |  | EEX |
| SE2 | base | Cal-2032 | 45 | 45 |  | EEX |
| SE3 | base | Cal-2028 | 45 | 45 |  | EEX |
| SE3 | base | Cal-2029 | 45 | 45 |  | EEX |
| SE3 | base | Cal-2030 | 45 | 45 |  | EEX |
| SE3 | base | Cal-2031 | 45 | 45 |  | EEX |
| SE3 | base | Cal-2032 | 45 | 45 |  | EEX |
| SE4 | base | Cal-2027 | 45 | 45 |  | EEX |
| SE4 | base | Cal-2028 | 45 | 45 |  | EEX |
| SE4 | base | Cal-2029 | 45 | 45 |  | EEX |
| SE4 | base | Cal-2030 | 45 | 45 |  | EEX |
| SE4 | base | Cal-2031 | 45 | 45 |  | EEX |
| SE4 | base | Cal-2032 | 45 | 45 |  | EEX |
