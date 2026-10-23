# Strike rule v0: realised prices for the past, evaluation date for the future

Task: PW02-MV-04 · Author: Wenhao Gu · Check: Devika · Status: draft v0, 22 Oct 2026 · Path: `docs/methods/strike-rule-v0.md`

The reference portfolio has two fixed prices. Flower pays the wind producer P_PPA and charges the baseload buyer P_cPPA (GBL Explained, section 1). At the 16 Oct meeting (recording 33:03–39:23) Flower told us to use realised day-ahead prices for past years and the futures curve on a stated evaluation date for future years. No futures history is needed. This note turns that guidance into formulas. Both strikes are fair prices with **no risk premium**. The premium is measured as a result (section 4). **[choice]** marks what the team can still push back on. Column names refer to `metric-dictionary-v0.md`.

## 1. Past contract years

Contract year y = one calendar year of delivery (CET/CEST days). Each contract runs one year and is struck again the next year **[choice]**. Strike window = calendar year y − 1.

  P_cPPA,y = `price_mean_eur_mwh`(z, y − 1)

  P_PPA,y = `capture_rate_nonneg_wind_ratio`(z, y − 1) × P_cPPA,y

Both inputs already exist in the screening indicator table, on the hourly series. Data start in 2019, so past contract years run from 2020 to the last complete year before the evaluation date. The year that contains the evaluation date is part realised and part forward, and it is left out **[choice]**. If year y − 1 fails the 98% rule for price or wind (dictionary 0.4), the strike is empty and year y is dropped with `flag_strike_missing`. A real contract is signed a few months before delivery, so using all of year y − 1 is a small look-ahead. I accept that for v0.

## 2. Future contract years

Strikes come from the forward-price table (PW02-CD-02) at its evaluation date E. E is the last complete trading day before the run, as Flower suggested (36:46). Flower may later load its own forward curve into the same table, with `source = FLOWER` (39:02–39:23).

  P_cPPA,y = F(z, base, Cal-y, E), method `avg_2m`

  P_PPA,y = CR_nonneg of the last complete year before E × P_cPPA,y **[choice]**

`avg_2m` = mean daily settlement of that fixed contract over trade dates in (E − 2 months, E]. Prices are grouped by the contract itself (Cal-2027), never by curve position such as "front year". Flower proposed the two-month average to smooth daily moves and said a single day is also fine (37:04–38:22). So `single_day`, the settlement on E, is run as the check. If a headline number moves more than 10% between the two, both are reported **[choice]**. Future years run from the year after E to the last listed Cal contract. Later years get no strike and carry `flag_beyond_curve`. EEX is the first source, Euronext only where EEX has no contract. Euronext rows stamped before about 17:00 CET may hold the previous settlement and are not used. Futures `DE` joins spot `DE-LU` through `zones.csv`.

**Columns for Fernando M.** One row per zone × product × delivery period × evaluation date × method: `zone`, `product` (base / peak), `delivery_period` (Cal-2027), `price_eur_mwh`, `evaluation_date`, `method` (avg_2m / single_day), `settlement_days_used`, `source` (EEX / EURONEXT). Suggested extras: `settlement_days_expected` (22 Aug–21 Oct 2026 has 43 weekdays) and `flag_thin` (missing days or no traded volume). The full daily settlement history stays out of the repository, as the EEX licence requires.

## 3. Reporting rule

Every forward-based result names its evaluation date, in tables and figure captions. Forward prices are refreshed before each Flower review and each presentation. An older result keeps its old date and is never relabelled. No table or chart mixes two evaluation dates. Past-year results do not depend on E and are fixed after the 30 Nov lock.

## 4. What changes meaning

- **Implied risk premium.** The margin added to P_cPPA that would bring a result to a target, for example ES95 within a limit. It is now measured against a trailing-spot strike for past years (`rp_implied_vs_trailing_spot_eur_mwh`) and against the forward strike for future years (`rp_implied_vs_forward_eur_mwh`, with `evaluation_date` beside it). The two are different quantities and stay in separate columns.
- **Forward risk premium against realised spot is dropped.** It needs forward prices from before each delivery year, which we do not collect.
- **Back-tested EV is the EV of a zero-margin contract.** Its spread shows how prices drift between the strike year and the delivery year. With the capture rate unchanged, PnL_GBL = V (P̄_y − P̄_y−1)(CR − s). CR is normally well above s, so the portfolio gains when prices rise and loses when they fall. Contract year 2023, struck on 2022 crisis prices, will probably set the loss tail in most zones, and 2022 the best year. The charts should say this is price drift, not a data error.

## 5. Sensitivity

24-month window: P_cPPA and CR_nonneg are computed over the **pooled** 24 months of years y − 2 and y − 1, not as the mean of two annual values. The first contract year becomes 2021, so base case and sensitivity are compared on 2021–2025 only.

---

## Appendix (not part of the one page): checks and open points

**Checks with known answers.**

- Fixture A (dictionary section 7) as year y − 1: P_cPPA = 12.625, P_PPA = 12.625 × 0.974573 = **12.303984** EUR/MWh.
- Zero-margin identity. Struck from the GBL Explained example year (P̄ = 50, CR = 0.85): P_cPPA = 50, P_PPA = 42.5. If year y repeats that year exactly, PnL_GBL = **0** at s = 30%, 40% and 50%. The engine must reproduce this (pairs with MV-01).
- Same strikes, year y prices 10% higher (P̄ = 55, CR = 0.85, V = 100,000 MWh): PnL_GBL = 275,000 / **225,000** / 175,000 € at s = 30 / 40 / 50%. At 40% the PPA leg gives +425,000 and the cPPA leg −200,000. This matches V (P̄_y − P̄_y−1)(CR − s) in section 4.
- Same strikes, capture rate falls to 0.80 (P̄ = 50): PnL_GBL = **−250,000 €** at every share. Capture risk sits entirely on the PPA leg, so the share does not change it.

**Open points.**

1. Flower to confirm both formulas and the one-year re-strike at the workshop.
2. Producer price for future years: last year's CR_nonneg, a 3-year average, or Flower's own capture-rate view?
3. Is 10% the right trigger for reporting the single-day check?
