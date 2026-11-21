# Metric dictionary v1: screening indicators

Task: PW03-MV-00 (v0 was PW01-MV-03) · Author: Wenhao Gu · Review: Devika · For: Coding · Status: v1 draft, 16 Nov 2026, revised 21 Nov
Path in repo: `docs/methods/metric-dictionary-v1.md` (replaces `metric-dictionary-v0.md`, which stays as history)

**What changed in v1.**

- **Zone rule (0.7).** Rewritten. Every zone is computed, and a multi-zone country is scored by its best qualifying zone. Italy uses its seven zonal prices, never the national PUN.
- **Onshore wind only (0.1, 4, 6).** Wind means onshore wind (ENTSO-E B19) everywhere in this note. Offshore is out of scope for PW03 and is not computed: no offshore input, no all-wind columns. Flower asked on 26 Oct to keep offshore for later, so it can come back in a later version. The GBL strikes, Gate 2 and Gate 5 all use onshore.
- **Capture-rate erosion (4b).** New indicator: the yearly trend of the onshore capture rate.
- **Kept indicators and Gate 2 thresholds (8).** New section. Three indicators are scored, three are reported as context, and the rest stay in the table but are not used by any gate. Every zone is scored against **SE3 only**, the one benchmark. If Devika's MV-03 method differs, hers wins.
- **21 Nov revision.** Calibration set cut to SE3 only (it was SE3, FI, DK1, DK2 and DE-LU), and offshore wind removed, as the team agreed.
- Price, negative-price, spread and solar formulas and the fixtures in section 7 are unchanged. The only formula change from v0 is that wind is onshore only, so the v0 all-wind columns are gone.

This note fixes how every screening indicator for Gate 2 (economics) and Gate 5 (growth) is calculated. The test is simple. Two people coding the same indicator from this text should get the same number. Where I had to make a choice that the brief left open, it is marked **[choice]** so the team can push back on it before the code is written.

It builds on the data-format rules in `docs/methods/harmonisation.md` (PW01-CD-04, draft v0.1 of 12 Oct). If that note and this one disagree, harmonisation.md wins on storage and time handling, and this note wins on the indicator formulas.

---

## 0. Shared rules (apply to every indicator)

### 0.1 Inputs from ENTSO-E

| Series | ENTSO-E item | Code used | Stored column |
|---|---|---|---|
| Day-ahead price | 12.1.D Energy prices | document A44 | `price_eur_mwh` |
| Actual generation, solar | 16.1.B&C | PSR B16 | `gen_solar_mw` |
| Actual generation, wind onshore | 16.1.B&C | PSR B19 | `gen_wind_onshore_mw` |
| Actual total load | 6.1.A | document A65 | `load_mw` |
| Installed capacity per type | 14.1.A | document A68, PSR B16, B19, B25 | `cap_*_mw` |

**Not downloaded yet: installed capacity per bidding zone (A68).** The only capacity data in the repo, `docs/sources/capacity_values_detail.csv`, is per country (SE, not SE3) and has no Italy. Section 6 and the 100 MW scaling in the reference portfolio spec (section 1) are blocked until Coding downloads A68 per bidding zone.

Everything is computed **per bidding zone** (SE3, NL, DE-LU, ...). Country values are a separate step, see 0.7.

### 0.2 Time step

Series are stored in their original step, with `mtu_minutes` (15 or 60) on each row (harmonisation.md §1). Day-ahead prices are hourly until 30 Sep 2025 and 15-minute from delivery day 1 Oct 2025. Indicators use two kinds of series.

- **Hourly series.** Used for price level, volatility, capture rate and growth (sections 1, 2, 4, 6). Built with the shared `to_hourly()` function, so prices and power (MW) are the equal-weight mean of the slots in the hour. An hour is **valid** only if all its slots are present (four quarter-hours, or the one hourly value). If one quarter-hour is missing, the hour is missing. No partial averages. Why hourly here: these indicators must be comparable across 2019–2025, and a 15-minute series has more extreme values, which would make volatility jump in 2025 for reasons that have nothing to do with the market.
- **Native series.** Used for negative prices and daily spreads (sections 3 and 5), as harmonisation.md §1 requires. Hourly averaging hides short negative intervals and narrows intra-day spreads, and both matter for GBL and the battery. Each slot has a duration Δt = `mtu_minutes` / 60 hours.

Any year that contains 15-minute source data gets `flag_qh_source = true`, so a jump in late 2025 can be traced back to the step change.

### 0.3 Day, season and year

- Data are stored in UTC. Days, seasons and years are defined by the **delivery day in market time**, CET/CEST (Europe/Berlin), for every zone including Finland and the Baltics (harmonisation.md §2). **[choice]** GB and IE are outside SDAC, so for those two we use Europe/London. This needs confirming when their data source is chosen.
- A **day** is one delivery day. It has 24 hours, or 23 hours on the last Sunday of March and 25 hours on the last Sunday of October (92, 96 or 100 quarter-hours).
- A **year** y is every hour whose local date falls in calendar year y. That is 8,760 hours, or 8,784 in a leap year.
- **Seasons** are meteorological and stay inside the calendar year. **[choice]** Winter = Jan, Feb, Dec of the same year. Spring = Mar–May. Summer = Jun–Aug. Autumn = Sep–Nov. So "winter 2024" is Jan + Feb + Dec 2024, not Dec 2023 to Feb 2024. This keeps every season inside one yearly file.

### 0.4 Missing data

Following harmonisation.md, missing values stay empty and are never filled.

- **Valid day.** Every expected slot of that day has a value: 23, 24 or 25 hours, or 92, 96 or 100 quarter-hours.
- **Valid year** for an indicator. At least 98% of the expected hours have a value: 8,585 of 8,760, or 8,609 of 8,784 in a leap year (rounded up). This matches Devika's acceptance test, which fails a file above 2% missing.
- **Valid season.** Same 98% rule applied to the hours of that season.
- If the year or season is not valid, the indicator is **empty**, not zero, and `flag_low_coverage = true`.
- Every output row also carries `coverage_price_pct`, the share of expected hours with a valid price.

### 0.5 Numbers

- Standard deviation is the **sample** standard deviation (divide by n − 1). In pandas that is `.std()`. In numpy it is `np.std(x, ddof=1)`. This matters in the small test fixtures below.
- Store full precision. Round only for display. Tests compare with a tolerance of 1e-6.
- "Negative" means strictly below zero. A price of exactly 0.00 is not negative.

### 0.6 Notation

z = zone, y = year, h = hour, d = day. P_h = hourly day-ahead price (EUR/MWh). G_h = hourly generation of a technology (MW, which over one hour equals MWh). H_y = the set of valid hours of year y. |H_y| = how many there are.

### 0.7 Zone rule

**Compute every zone.** All indicators are computed per bidding zone, as named in `zones.csv`. Nothing is averaged across zones.

**Which zone stands for a country.** Flower contracts a wind park in one zone, so a multi-zone country is scored by one zone, not by an average.

1. A zone **qualifies** if its onshore wind generation in the last complete year is at least **1 TWh** **[choice]**. A zone with almost no wind cannot host the reference portfolio.
2. The country's Gate 2 score is the score of its **best qualifying zone**. Ties go to the zone with more onshore generation. Every qualifying zone is still reported, so the reader sees the spread.
3. Gate 4 (reference portfolio spec v1) runs on the same zone.

**By country in the PW03 scope.**

| Country | Zones | Rule |
|---|---|---|
| Sweden (benchmark) | SE3 | SE3 only. Flower confirmed this on 26 Oct |
| Netherlands, Spain, Poland, Lithuania | NL, ES, PL, LT | One zone each, nothing to choose |
| Germany | DE-LU | One combined zone. Never replaced by a Germany-only price |
| Italy | North, Centre-North, Centre-South, South, Calabria, Sicily, Sardinia | All seven computed. Best qualifying zone by the rule above. See below |

**Italy.**

- **Zonal prices only.** A wind PPA in Italy is settled against the zone where the park sits, so price, capture rate and spread all use the zonal day-ahead price and that zone's own onshore generation. The national PUN (PUN Index GME since 2025) is a consumer reference price and is not used.
- **2019–2020.** Italy's zones were redrawn on 1 Jan 2021, and Calabria became a zone of its own then. In the CD-07 data, only Calabria has no series before 2021. The other six zones have prices for 2019–2020, but under the old boundaries, so those years do not describe the same area. They are left out **[choice]**, not filled from a neighbour. So Italian multi-year indicators use 2021–2025, and this is written in every Italian table.
- **One scorecard.** Market Analysis keeps one Italy scorecard (gate checklist, section 6). The seven-zone numbers go into its Evidence cells. No zone is named the winner before the numbers are in.

**Peak load and capacity** (section 6) can still be summed to country level, with peak load taken as the maximum of the summed hourly load, not the sum of zone peaks.

---

## 1. Price level

**What it says.** How expensive power is on average in the zone.

**Formula.** Annual baseload average:

  price_mean_y = (1 / |H_y|) × Σ_{h ∈ H_y} P_h

The seasonal average is the same formula over the valid hours of that season.

**Inputs.** Hourly day-ahead price.

**Units.** EUR/MWh.

**Output columns.** `price_mean_eur_mwh`, `price_mean_winter_eur_mwh`, `price_mean_spring_eur_mwh`, `price_mean_summer_eur_mwh`, `price_mean_autumn_eur_mwh`.

**Special cases.**
- Gaps: the average is taken over valid hours only. Missing hours are dropped, not treated as zero. Coverage rule 0.4 applies to the year and to each season separately.
- 15-minute era: use the hourly series from 0.2.
- This is a time-weighted average. It is not weighted by load or by volume.

---

## 2. Price volatility

**What it says.** How much prices swing. Two measures, because they catch different things. The first catches swings inside the day. The second catches swings from one day to the next.

**Formula A, hourly volatility.**

  price_std_hourly_y = sample standard deviation of { P_h : h ∈ H_y }

**Formula B, day-to-day volatility.**

1. For each valid day d, the daily average D_d = mean of its hourly prices.
2. For each pair of consecutive days where both are valid and both fall in year y, ΔD_d = D_d − D_{d−1}.
3. price_std_daily_change_y = sample standard deviation of all ΔD_d in year y.

The first change of the year is 2 Jan − 1 Jan. The change from 31 Dec of the previous year is **not** used. **[choice]** This keeps each year self-contained. A full year therefore has 364 changes, or 365 in a leap year.

**Do not use log returns or percentage changes.** Prices go negative and close to zero, so ln(P_t / P_{t−1}) is undefined or explodes. Changes are plain differences in EUR/MWh.

**Inputs.** Hourly day-ahead price.

**Units.** EUR/MWh for both.

**Output columns.** `price_std_hourly_eur_mwh`, `price_std_daily_change_eur_mwh`, plus `n_daily_changes` (how many ΔD_d went in).

**Special cases.**
- Gaps: a missing day breaks the chain. If day d is invalid, both ΔD_d and ΔD_{d+1} are skipped. Formula B also needs the 98% year rule, counted in hours.
- Clock-change days: D_d is the mean over 23 or 25 hours. No adjustment.
- 15-minute era: hourly series only (0.2). Volatility from Oct 2025 on is slightly understated compared with the raw 15-minute data. Flagged by `flag_qh_source`.

---

## 3. Negative-price time

**What it says.** How often and how deeply prices go below zero. This matters directly for GBL, because the negative-price protection clause applies in exactly these periods.

**Formula.** On the **native** series (0.2). Let S_y be the valid slots of year y, each with price P_s and duration Δt_s (1 h or 0.25 h), and N_y = the slots with P_s < 0.

  neg_hours_equiv_y = Σ_{s ∈ N_y} Δt_s

  neg_time_share_y = neg_hours_equiv_y / Σ_{s ∈ S_y} Δt_s × 100

  neg_price_mean_y = Σ_{s ∈ N_y} Δt_s × P_s / neg_hours_equiv_y

Before Oct 2025 every slot is one hour, so neg_hours_equiv is simply the number of negative hours. As harmonisation.md §1 asks, the headline number for comparing zones and years is the **share of time**, not a count.

**Inputs.** Day-ahead price in its native step.

**Units.** Hours, %, and EUR/MWh (a negative number).

**Output columns.** `neg_time_share_pct`, `neg_hours_equiv_h`, `neg_price_mean_eur_mwh`.

**Special cases.**
- If no slot is negative, `neg_price_mean_eur_mwh` is **empty**, not zero. Zero would read as "negative prices at 0 EUR/MWh".
- Gaps: count over valid slots only. Because a year can be valid with up to 2% missing, the count is not scaled up. That is why the share of time is the comparable number.
- Exactly 0.00 EUR/MWh does not count. Nordic zones have many hours at 0.00 or −0.01, so this line moves the number. Keep it strict.

---

## 4. Capture rate (wind and solar)

**What it says.** The average price a wind or solar park actually earned, compared with the plain average price. Below 1 means the technology produces most when prices are low.

**Formula.** For technology t (wind or solar), let H_y,t = the hours in year y where both P_h and G_h are valid.

  capture_price_t,y = Σ_{h ∈ H_y,t} (G_h × P_h) / Σ_{h ∈ H_y,t} G_h

  baseload_t,y = (1 / |H_y,t|) × Σ_{h ∈ H_y,t} P_h

  capture_rate_t,y = capture_price_t,y / baseload_t,y

The denominator uses **the same hours** as the numerator. **[choice]** Otherwise a gap in the generation data would shift the ratio for no reason.

**Wind** = onshore wind only, G_h = `gen_wind_onshore_mw`. The reference portfolio is onshore only, so offshore is not part of any indicator. If a zone reports no onshore series, the wind columns are empty.

**Solar** = `gen_solar_mw`.

**Variant used in the GBL PnL.** Flower's GBL note (8 Oct 2026) defines the capture price over hours with non-negative prices, because the PPA pays nothing in negative hours. So we report a second version as well:

  capture_price_nonneg_t,y = Σ_{h ∈ H_y,t, P_h ≥ 0} (G_h × P_h) / Σ_{h ∈ H_y,t, P_h ≥ 0} G_h

  capture_rate_nonneg_t,y = capture_price_nonneg_t,y / baseload_t,y

The denominator is still the all-hours baseload average, as in the GBL note, where the same P̄_DA appears in the cPPA leg.

**Inputs.** Hourly day-ahead price, hourly onshore wind and solar generation.

**Units.** Capture price in EUR/MWh. Capture rate is a ratio with no unit (report 0.85, not 85).

**Output columns.** `capture_price_wind_onshore_eur_mwh`, `capture_rate_wind_onshore_ratio`, `capture_rate_nonneg_wind_onshore_ratio`, `capture_price_solar_eur_mwh`, `capture_rate_solar_ratio`, `capture_rate_nonneg_solar_ratio`. These are the names already used in `metrics/gate2.py` (PW03-CD-01).

**Flags per technology.** The 98% rule and the baseload average are taken over each technology's own hours H_y,t, so these flags carry the technology in their name: `flag_low_coverage_wind_onshore`, `flag_low_baseload_wind_onshore`, `flag_low_coverage_solar`, `flag_low_baseload_solar`, with `coverage_wind_onshore_pct` and `coverage_solar_pct` beside them. `flag_low_coverage` with no suffix is the price flag of 0.4. Same names as `metrics/gate2.py`.

**Special cases.**
- Negative generation values (ENTSO-E sometimes reports small negative solar at night, which is the plant's own use). Set G_h = 0 for this indicator and count them in `n_neg_gen_fixed`. Devika's tests will also flag them.
- Gaps: the 98% rule applies to H_y,t.
- Zones with almost no solar (SE1, SE2, NO zones, for example). Annual solar energy is Σ G_h over H_y,solar, in MWh. If it is below **100 GWh** **[choice]**, compute the number anyway but set `flag_low_solar = true`, and Gate 2 does not use it. If ENTSO-E has no solar series for the zone, the solar columns are empty.
- Baseload average close to zero. If |baseload_t,y| < 5 EUR/MWh **[choice]**, the ratio is unstable. Report it, set `flag_low_baseload_<t> = true`, and let the gate look at capture price instead. This mostly affects northern Nordic zones in wet years.
- 15-minute era: both price and generation use the hourly series.

---

## 4b. Capture-rate erosion (new in v1)

**What it says.** Whether onshore wind is earning less and less of the average price each year. This is what hurts a fixed PPA price after signing: the strike assumes last year's capture rate, and a falling capture rate makes the PPA leg lose money (the −250,000 € check in the reference portfolio spec).

**Formula.** Ordinary least-squares slope of the annual non-negative onshore capture rate against the year, over the valid years Y in the window:

  cr_erosion = Σ_{y ∈ Y} (y − ȳ)(CR_y − C̄R) / Σ_{y ∈ Y} (y − ȳ)²

with CR_y = `capture_rate_nonneg_wind_onshore_ratio` of year y, and ȳ, C̄R their means over Y. The window is 2019–2025, or 2021–2025 for Italian zones (0.7).

**Units.** Capture-rate points per year. −0.01 means the capture rate falls by one point (0.01) a year.

**Output columns.** `cr_erosion_wind_onshore_per_year`, `n_erosion_years`.

**Special cases.**
- At least **5 valid years** **[choice]**. With fewer, the slope is empty.
- Years with `flag_low_baseload_wind_onshore` are left out of Y, because their ratio is unstable. Years with `flag_low_coverage_wind_onshore` have no CR_y and drop out too.
- A missing year is dropped, not interpolated. The slope uses the actual year numbers, so a gap does not bend the line.

**Check.** CR = 0.90, 0.88, 0.87, 0.85, 0.86, 0.83, 0.81 for 2019–2025: Σ (y − ȳ)² = 28, Σ (y − ȳ)(CR − C̄R) = −0.38, slope **−0.013571** per year. Drop 2021 and the slope is **−0.013602**.

---

## 5. Daily price spread (battery arbitrage proxy)

**What it says.** What a 2-hour or 4-hour battery could earn per MWh of capacity per day, by buying in the cheapest hours and selling in the most expensive ones.

**Formula.** On the **native** series (0.2). For each valid day d, sort its slot prices from lowest to highest. Let k = 2 h / Δt, which is 2 slots for hourly data and 8 slots for 15-minute data. For the 4-hour version, k = 4 h / Δt (4 or 16).

  spread_2h_d = (mean of the k highest prices) − (mean of the k lowest prices)

  spread_2h_y = mean of spread_2h_d over valid days in y. The same applies to spread_4h_y.

A battery can follow a 15-minute price, so the native step is the right one to measure what it could earn. For days before Oct 2025 the result is the same as the hourly version.

**[choice]** To keep the 2025 jump readable, also report `spread_2h_hourly_eur_mwh` and `spread_4h_hourly_eur_mwh` from the hourly series for every year. Gate 2 uses the native version.

**What it deliberately leaves out.** **[choice]** The highest and lowest hours are picked without regard to their order in the day, so it does not check that charging comes before discharging. No round-trip losses, one cycle per day, no state-of-charge limits. This is an upper bound on a simple daily arbitrage and is meant for ranking zones, not for valuing a battery. A real dispatch model comes later.

**Inputs.** Day-ahead price in its native step, plus the hourly series for the `_hourly` columns.

**Units.** EUR/MWh.

**Output columns.** `spread_2h_eur_mwh`, `spread_4h_eur_mwh`, `spread_2h_hourly_eur_mwh`, `spread_4h_hourly_eur_mwh`, `n_spread_days`.

**Special cases.**
- Gaps: invalid days are skipped. Year validity uses the 98% rule.
- Clock-change days: sort the slots that exist. No adjustment.
- Ties: when several slots share the same price, which one is "picked" does not change the mean. No tie rule is needed.
- The day of the step change (1 Oct 2025) is a full 15-minute day, so no day mixes the two steps.

---

## 6. Growth (Gate 5)

**What it says.** How fast wind, solar and batteries are being built in the zone, and how large they are compared with the zone's demand.

### 6.1 Installed capacity

  cap_t,y = ENTSO-E 14.1.A installed capacity for technology t, for the year labelled y.

- Wind = B19 (onshore only).
- Solar = B16.
- Battery = B25 (energy storage).

**Blocked in PW03.** 14.1.A is not downloaded per bidding zone yet (0.1), so this section cannot be computed for SE3 or the Italian zones until it is.

ENTSO-E publishes 14.1.A once per year, and the value is meant to describe the start of that year. **[choice]** We use the label as it is and do not shift years. The growth labelled y is therefore mostly what was built during y − 1. Write this in any figure caption.

### 6.2 Yearly growth

  cap_growth_t,y = cap_t,y − cap_t,y−1           (MW)

  cap_growth_pct_t,y = cap_growth_t,y / cap_t,y−1 × 100   (%)

- If either year is missing, both are empty.
- If cap_t,y−1 = 0, the percentage is empty, because growth from zero is not a percentage.

Over the full window, also report the compound annual growth rate:

  cap_cagr_t = (cap_t,last / cap_t,first)^(1 / (last − first)) − 1

with first = 2019 and last = 2025, or the first and last years that have data, written down in `cagr_years`.

### 6.3 Share of peak demand

  load_peak_y = maximum hourly `load_mw` over valid hours in year y

  cap_share_peak_t,y = cap_t,y / load_peak_y   (ratio)

**Inputs.** 14.1.A installed capacity, 6.1.A actual total load.

**Units.** MW, %, ratio.

**Output columns.** `cap_wind_mw` (onshore), `cap_solar_mw`, `cap_battery_mw`, `cap_growth_*_mw`, `cap_growth_*_pct`, `cap_cagr_*_ratio`, `load_peak_mw`, `cap_share_peak_*_ratio`.

**Special cases.**
- Battery: B25 on ENTSO-E is patchy and in many zones simply not reported. Missing is **empty**, never 0. Most battery values will probably have to come from another source (national TSO lists or Flower). Until we have one, Gate 5 scores battery only where B25 exists, with `flag_battery_source = "entsoe"` or `"none"`.
- Capacity that drops from one year to the next: keep the value. Devika's test flags it for a manual check, and the growth is reported as negative.
- Load peak with gaps: the year must pass the 98% rule. Otherwise `load_peak_mw` is empty, because a missing winter evening can hide the real peak.
- 15-minute load: hourly mean first (0.2), then the maximum. The hourly peak is a bit lower than the quarter-hour peak. This is fine as long as it is done the same way everywhere.

---

## 7. Test cases with known answers

These fixtures are small enough to check with a calculator. Lingyu's code should reproduce every number to 1e-6. Fixtures A–D are **synthetic**, shaped like an SE3 summer Sunday, and chosen to hit the edge cases (negative hours, a price of exactly 0, midday solar at negative prices). The last part of this section adds a real SE3 sample.

### Fixture A: one valid day, 24 local hours

| Hour (local) | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Price, EUR/MWh | 18.0 | 15.5 | 14.0 | 12.0 | 10.5 | 8.0 | 5.0 | 2.0 | 0.5 | −1.5 | −6.0 | −3.5 |
| Solar, MW | 0 | 0 | 0 | 0 | 0 | 10 | 40 | 90 | 150 | 200 | 240 | 260 |
| Onshore wind, MW | 800 | 820 | 850 | 870 | 900 | 950 | 1000 | 1050 | 1100 | 1150 | 1180 | 1200 |

| Hour (local) | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Price, EUR/MWh | 0.0 | 1.0 | 4.0 | 9.0 | 16.0 | 24.0 | 32.0 | 38.5 | 35.0 | 28.0 | 22.0 | 19.0 |
| Solar, MW | 260 | 240 | 200 | 150 | 90 | 40 | 10 | 0 | 0 | 0 | 0 | 0 |
| Onshore wind, MW | 1150 | 1100 | 1000 | 900 | 800 | 700 | 600 | 550 | 500 | 520 | 560 | 600 |

Expected results, treating this one day as the whole period:

| Indicator | Working | Answer |
|---|---|---|
| Price mean | 303.0 / 24 | **12.625** EUR/MWh |
| Hourly std (n − 1) | | **12.550983** EUR/MWh |
| (check: std with n instead, which is wrong) | | 12.286722 |
| Negative hours | hours 9, 10, 11. Hour 12 is 0.0 and does not count | **3** |
| Mean negative price | (−1.5 − 6.0 − 3.5) / 3 | **−3.666667** EUR/MWh |
| Spread 2h | (38.5 + 35.0)/2 − (−6.0 − 3.5)/2 = 36.75 − (−4.75) | **41.5** EUR/MWh |
| Spread 4h | (38.5 + 35 + 32 + 28)/4 − (−6 − 3.5 − 1.5 + 0)/4 = 33.375 − (−2.75) | **36.125** EUR/MWh |
| Solar capture price | Σ G·P = 2995.0, Σ G = 1980 | **1.512626** EUR/MWh |
| Solar capture rate | 1.512626 / 12.625 | **0.119812** |
| Solar capture rate, non-negative hours | 5645.0 / 1280 = 4.410156, then / 12.625 | **0.349319** |
| Wind capture price | Σ G·P = 200100, Σ G = 20850 | **9.597122** EUR/MWh |
| Wind capture rate | 9.597122 / 12.625 | **0.760168** |
| Wind capture rate, non-negative hours | 213105 / 17320 = 12.303984, then / 12.625 | **0.974573** |

The solar capture rate is extreme on purpose. Solar peaks exactly in the negative hours, which is what a sunny Nordic Sunday looks like.

### Fixture B: day-to-day volatility

Four consecutive valid days with daily averages 20.0, 35.0, 30.0, 12.0 EUR/MWh.

Changes: +15.0, −5.0, −18.0. Sample std (n − 1 = 2): **16.623277** EUR/MWh, with n_daily_changes = 3.

Same days, but day 3 is invalid: then both changes that touch day 3 drop out, only +15.0 is left, and the std of one value is empty (NaN). The code must return empty here, not 0.

### Fixture C: growth

| Year | Wind MW | Solar MW | Battery MW | Peak load MW |
|---|---|---|---|---|
| 2022 | 2000 | 150 | (missing) | 14000 |
| 2023 | 2400 | 300 | 20 | 14500 |
| 2024 | 2700 | 300 | 60 | 15000 |

| Result | Answer |
|---|---|
| Wind growth 2023 / 2024 | 400 MW, 20.0% / 300 MW, 12.5% |
| Solar growth 2023 / 2024 | 150 MW, 100.0% / 0 MW, 0.0% |
| Battery growth 2023 | empty (2022 missing) |
| Battery growth 2024 | 40 MW, 200.0% |
| Wind CAGR 2022–2024 | (2700/2000)^(1/2) − 1 = **0.161895** |
| Share of peak 2024: wind / solar / battery | **0.18 / 0.02 / 0.004** |

### Fixture D: 15-minute conversion and clock changes

- `to_hourly()`: quarter-hour prices 40, 44, 52, 60 → hourly **49.0**. Quarter-hours 40, (missing), 52, 60 → hourly **missing**, not 50.67.
- Negative time on the native series: quarter-hours −2, −6, 5, 7 give `neg_hours_equiv_h` = 2 × 0.25 = **0.5** h and a mean negative price of **−4.0**. The hourly mean of that hour is 1.0, so an hourly count would have missed it. This is why section 3 uses the native step.
- Spread on the native series: on a 15-minute day, spread_2h uses the 8 highest and 8 lowest quarter-hours.
- 31 Mar 2024 in Europe/Berlin has 23 hours. 27 Oct 2024 has 25. Both are valid days if all their slots are present.
- 2024 needs at least 8,609 valid hours out of 8,784 to be a valid year.

### SE3 2024 reference values (real data)

A small real sample, so Lingyu has known answers on ENTSO-E data as well as on the fixtures.

- **Sample.** SE3 day-ahead prices (ENTSO-E 12.1.D, EUR/MWh), delivery days 27–29 July 2024 in CET/CEST. That is 72 hours, UTC 2024-07-26 22:00 to 2024-07-29 21:00. Read from the Transparency Platform table view on 19 Oct 2026. I chose these days because Sunday 28 July has a seven-hour run of negative prices from 11:00 to 17:00, an hour at exactly 0.00, and a negative night that follows.
- **File.** The same 72 values are in `tests/fixtures/se3_2024-07-27_29_entsoe.csv` (UTC timestamps, `price_eur_mwh`).

| Hour (CEST) | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Sat 27 Jul | 19.20 | 18.99 | 19.08 | 19.39 | 19.63 | 19.79 | 20.46 | 20.97 | 21.88 | 22.48 | 21.99 | 21.55 |
| Sun 28 Jul | 21.75 | 21.32 | 20.76 | 19.60 | 18.98 | 19.90 | 20.97 | 21.68 | 22.14 | 4.99 | 0.00 | −2.43 |
| Mon 29 Jul | −0.59 | −0.92 | −1.27 | −1.57 | −1.27 | −0.81 | −0.01 | 1.28 | 0.42 | 0.54 | −0.05 | −0.16 |

| Hour (CEST) | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Sat 27 Jul | 20.99 | 17.37 | 17.49 | 20.24 | 20.63 | 20.98 | 21.79 | 22.54 | 22.23 | 21.77 | 21.63 | 20.16 |
| Sun 28 Jul | −15.04 | −29.80 | −48.69 | −33.53 | −13.28 | −0.26 | 4.97 | 5.83 | 4.97 | 4.91 | 2.68 | −0.10 |
| Mon 29 Jul | −0.19 | −1.70 | −0.98 | −0.07 | 4.96 | 15.04 | 16.61 | 19.06 | 18.27 | 14.05 | 8.54 | 4.94 |

Expected results, treating these three days as the whole period:

| Indicator | Working | Answer |
|---|---|---|
| Price mean, 72 h | 659.67 / 72 | **9.162083** EUR/MWh |
| Hourly std (n − 1) | | **14.292575** EUR/MWh |
| Daily means | 493.23 / 24, 72.32 / 24, 94.12 / 24 | 20.551250, 3.013333, 3.921667 |
| Std of daily change (n − 1) | changes −17.537917 and +0.908333. With two values the std is the gap between them / √2 = 18.446250 / 1.414214 | **13.043468** EUR/MWh |
| Negative hours | 8 on 28 Jul (11:00–17:00 and 23:00) + 13 on 29 Jul (00:00–06:00 and 10:00–15:00). 28 Jul 10:00 is exactly 0.00 and does not count | **21** |
| Mean negative price | −152.72 / 21 | **−7.272381** EUR/MWh |
| Spread 2h per day | 27 Jul: 22.51 − 17.43 = 5.08. 28 Jul: 21.945 − (−41.11) = 63.055. 29 Jul: 18.665 − (−1.635) = 20.30 | mean **29.478333** EUR/MWh |
| Spread 4h per day | 27 Jul: 22.31 − 18.2325 = 4.0775. 28 Jul: 21.7225 − (−31.765) = 53.4875. 29 Jul: 17.245 − (−1.4525) = 18.6975 | mean **25.420833** EUR/MWh |

`python tests/hand_check_se3_2024.py tests/fixtures/se3_2024-07-27_29_entsoe.csv` prints the same numbers. Lingyu's code, run on the CD-07 SE3 2024 file and cut to these three days, should match them to 1e-6. If it does not, compare the 72 input prices first, then the time zone.

---

## 8. Gate 2: kept indicators and thresholds

Gate 2 asks whether a zone's power market suits the reference portfolio, before any simulation. It uses the same scale as the Gate 1, 3 and 5 checklist (`docs/sources/gate-checklists-v1.md`): scores 2 / 1 / 0 / ND and verdicts PASS / CONDITIONAL / FAIL.

### 8.1 What is kept

**Scored.** Level indicators use the mean of the valid years 2023–2025 **[choice]**, so the 2022 crisis does not decide the score. The 2019–2025 median is reported as a sensitivity.

| Check ID | Mandatory? | Indicator | Column | Better is | Why it matters for the portfolio |
|---|---|---|---|---|---|
| G2-01 | Yes | Onshore wind capture rate, non-negative hours | `capture_rate_nonneg_wind_onshore_ratio` | Higher | Sets the PPA strike and the shape cost of turning wind into baseload |
| G2-02 | Yes | Capture-rate erosion | `cr_erosion_wind_onshore_per_year` | Less negative | A falling capture rate is the main loss on a fixed PPA price |
| G2-03 | No | 4-hour daily spread | `spread_4h_eur_mwh` | Higher | What the standalone 4-hour battery can earn from arbitrage |

**Reported as context, not scored.** These work in both directions for this portfolio. Their net effect shows up in Gate 4, where the portfolio is actually simulated.

| Indicator | Column | Why it is not scored |
|---|---|---|
| Baseload price level | `price_mean_eur_mwh` | The strikes are set from it, so a zero-margin book is neither better nor worse at a high price. It scales the euro figures |
| Hourly volatility | `price_std_hourly_eur_mwh` | Risk for the GBL legs, revenue for the battery |
| Negative-price time and depth | `neg_time_share_pct`, `neg_price_mean_eur_mwh` | The protection clause zeroes the PPA leg, while the baseload leg still buys at negative prices |

**Kept in the table but not used by any gate.** Seasonal means, day-to-day volatility, solar capture rates (solar is not in the portfolio), the 2-hour spread (the battery is 4 hours) and the `_hourly` spread columns (check columns for the 15-minute step). Section 6 (growth) feeds Gate 5, not Gate 2.

### 8.2 Threshold rule (proposal)

Every zone is compared with **SE3**, the only benchmark. Flower already trades GBL there, so a zone at least as good as SE3 on an indicator is a market Flower knows it can work in.

For each scored indicator:

1. **Reference** = SE3's value of that indicator, over the same window.
2. **Score 2**: at least as good as SE3.
3. **Score 1**: worse than SE3, by no more than the margin (inclusive).
4. **Score 0**: worse than SE3 by more than the margin.
5. **ND**: the indicator is empty, or carries `flag_low_coverage_wind_onshore` or `flag_low_baseload_wind_onshore` (G2-01, G2-02), or `flag_low_coverage` (G2-03). If **SE3's own value** is ND on a check, there is no reference, so every zone is ND on that check.

| Check ID | Margin **[choice]** |
|---|---|
| G2-01 | 0.05 (five capture-rate points) |
| G2-02 | 0.01 per year |
| G2-03 | 20% of SE3's value |

SE3 itself always scores 2. With one reference market the margins carry more weight than before, so Devika's MV-03 step checks them against Flower's own view of SE3 (9 Oct ratings): if Flower sees SE3 as only just workable, the margins are too generous.

**Gate 2 verdict**, as in the checklist:

- **PASS**: G2-01 and G2-02 both score at least 1, and G2-03 is explained if it scores 0 or ND.
- **CONDITIONAL**: G2-01 or G2-02 scores 0 or is ND.
- **FAIL**: not used. Gate 2 has **no hard KO** in v1.

### 8.3 Test on made-up numbers

| Zone | G2-01 capture rate | G2-02 erosion | G2-03 spread 4h (EUR/MWh) |
|---|---|---|---|
| **SE3 (reference)** | **0.82** | **−0.010** | **45** (margin 9) |
| Zone X | 0.86 → **2** | −0.005 → **2** | 50 → **2** |
| Zone Y | 0.79 → **1** | −0.015 → **1** | 40 → **1** |
| Zone Z | 0.75 → **0** | −0.025 → **0** | 30 → **0** |
| Edge: exactly 0.82 / −0.010 / 45 | **2** | **2** | **2** |
| Edge: exactly 0.77 / −0.020 / 36 | **1** | **1** | **1** |

Verdicts: X and Y PASS. Z CONDITIONAL. Floating-point edge cases are compared with a tolerance of 1e-9.

## 9. Open points for the team

1. **Thresholds.** The rule in 8.2 is my proposal. Devika's MV-03 method decides it. The margins especially need her check against Flower's ratings.
2. **Zone qualification.** Is 1 TWh of onshore generation the right cut-off for a zone that can host the portfolio?
3. **Battery capacity source.** ENTSO-E B25 is still too thin to score Gate 5 on its own (unchanged from v0).
4. **GB.** Still depends on a non-ENTSO-E source converted to EUR per harmonisation.md. GB is outside the PW03 scope.
5. **Solar threshold.** The 100 GWh cut-off only matters if solar comes back into the portfolio.
6. **Installed capacity per zone.** A68 has to be downloaded per bidding zone for section 6 and for the 100 MW scaling in the reference portfolio (0.1). For Coding.

## Output tables (suggested)

One row per zone × year, saved as `data/processed/indicators/screen_indicators.parquet`, with the columns named above plus `zone`, `year`, `coverage_price_pct`, and the flags `flag_low_coverage`, `flag_qh_source`, `flag_low_solar`, `flag_low_coverage_<t>`, `flag_low_baseload_<t>` (section 4), `flag_battery_source`.

New in v1: one row per zone, saved as `data/processed/indicators/gate2_scores.parquet`, with `zone`, `country`, `is_benchmark` (true for SE3), `qualifies` (0.7), `cr_erosion_wind_onshore_per_year`, `n_erosion_years`, the three window means, SE3's values and the margins used, `g2_01_score`, `g2_02_score`, `g2_03_score` and `gate2_verdict`.
