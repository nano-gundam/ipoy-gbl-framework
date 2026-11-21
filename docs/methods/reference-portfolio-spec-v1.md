# Reference portfolio specification v1, with the strike rule and the Gate 4 definitions

Task: PW03-MV-00 · Author: Wenhao Gu · Review: Devika · Status: v1 draft, 16 Nov 2026, revised 21 Nov · Path in repo: `docs/methods/reference-portfolio-spec-v1.md`

This note replaces two v0 notes: `reference-portfolio-spec-v0.md` (PW02-MV-05) and `strike-rule-v0.md` (PW02-MV-04). Both stay in the repository as history. From now on the engine reads its portfolio, its strikes and its Gate 4 numbers from this one note, and the 30 November data lock freezes it. **[choice]** marks what the team or Flower can still change before the lock. Column names refer to `metric-dictionary-v1.md`.

## What changed since v0.1

- The strike rule is now section 2 of this note. The formulas are the same.
- New section 4 defines Gate 4: expected value (EV), expected shortfall at 95% (ES95) and the implied risk premium, and how they give a Gate 4 score and verdict on the same scale as Gates 1, 3 and 5.
- Markets follow the PW03 scope: SE3 is the benchmark, and the six initial countries are NL, DE-LU, ES, IT, PL and LT. Italy is scored by the zone rule in metric dictionary v1, section 0.7.
- Onshore wind only and SE3 as the baseline (Flower, 26 Oct) are kept from v0.1. Offshore wind is out of scope.
- **21 Nov revision.** Gate 4 is scored against **SE3 only**. The earlier draft calibrated on SE3, FI, DK1, DK2 and DE-LU.
- Anything Flower answers at the 16 Nov meeting goes into v1.1 before the lock. The questions still open are in section 6.

## 1. The portfolio

The same portfolio is simulated in every zone, so differences in results come from the markets and not from the portfolio.

| # | Parameter | Value | Status |
|---|---|---|---|
| 1 | Wind | 100 MW onshore. Hourly output G_h = the zone's ENTSO-E onshore generation (B19) scaled to 100 MW by installed onshore capacity | Size from Flower 9 Oct, onshore from 26 Oct. Confirm size |
| 2 | Expected output V_P50 | Median annual energy of the scaled onshore profile over 2019–2025 | **[choice]** |
| 3 | Baseload share s | 40%, with 30% and 50% as sensitivities | **[choice]**, Flower's range is 30–50% |
| 4 | Baseload volume B | s × V_P50 / H, fixed for the contract year (H = hours in the year) | GBL Explained, section 1 |
| 5 | Strikes | Section 2 of this note | Flower guidance of 16 Oct. Confirm formulas |
| 6 | Battery | 100 MWh at 4 hours = 25 MW, operated standalone for profit (day-ahead arbitrage and ancillary services). It does not firm the wind | Reading of the 9 Oct answer. **The 100 MW / 400 MWh reading is still open** |
| 7 | Contract tenor | One year, struck again each year | **[choice]** |
| 8 | Negative-price protection | The PPA leg earns zero in every hour with a negative day-ahead price | GBL Explained, section 3 |
| 9 | Imbalance cost | Left out | As in GBL Explained |
| 10 | GoOs | Left out. They are priced into both legs and do not change the power PnL | GBL Explained, section 2 |
| 11 | Benchmark | SE3. Every zone is also reported relative to SE3 | Flower 26 Oct |

Two caveats carry over from v0.1. ENTSO-E capacity describes the start of each year, so scaling by it overstates output a little in a zone that builds a lot of wind during the year. And in zones where P_PPA falls below 5 EUR/MWh the return in section 4 is unstable, so it carries `flag_low_ppa_price` and the euro figure is used instead.

## 2. Strikes

Flower pays the wind producer P_PPA and charges the baseload buyer P_cPPA. Both strikes are fair prices with **no risk premium**. The premium is a result, measured in section 4.

**Past contract years.** Contract year y = one calendar year of delivery. The strike window is year y − 1.

  P_cPPA,y = `price_mean_eur_mwh`(z, y − 1)

  P_PPA,y = `capture_rate_nonneg_wind_onshore_ratio`(z, y − 1) × P_cPPA,y

Data start in 2019, so past contract years run from 2020 to the last complete year before the evaluation date. If year y − 1 fails the 98% coverage rule for price or wind, year y is dropped and flagged `flag_strike_missing`. Using all of year y − 1 is a small look-ahead, because a real contract is signed a few months before delivery. I accept that for v1.

**Future contract years.** Strikes come from the forward-price table (PW02-CD-02) at evaluation date E, the last complete trading day before the run.

  P_cPPA,y = F(z, base, Cal-y, E), method `avg_2m`

  P_PPA,y = onshore CR_nonneg of the last complete year before E × P_cPPA,y **[choice]**

`avg_2m` is the mean daily settlement of that fixed contract over trade dates in (E − 2 months, E]. Prices are grouped by the contract itself (Cal-2027), never by curve position. `single_day` (the settlement on E) is run as a check. If a headline number moves more than 10% between the two, both are reported **[choice]**. Years past the last listed Cal contract carry `flag_beyond_curve` and get no strike. EEX first, Euronext only where EEX has no contract.

**Reporting rule.** Every forward-based result names its evaluation date. No table or chart mixes two evaluation dates. Past-year results do not depend on E and are fixed after the lock.

**Sensitivity.** A 24-month strike window (years y − 2 and y − 1 pooled). The first contract year then becomes 2021, so base case and sensitivity are compared on 2021–2025 only.

## 3. PnL of one contract year

For zone z and contract year y, with hourly price P_h, scaled onshore output G_h and B from section 1:

  PnL_PPA,y = Σ_h 1[P_h ≥ 0] × G_h × (P_h − P_PPA,y)

  PnL_cPPA,y = Σ_h B × (P_cPPA,y − P_h)

  PnL_GBL,y = PnL_PPA,y + PnL_cPPA,y

  PnL_total,y = PnL_GBL,y + PnL_BESS,y

This is the hourly form of the GBL Explained equations. One difference matters. GBL Explained uses the same V in both legs. Here B is fixed from V_P50 at signing, while G_h is the weather that actually came. A calm year sells the same B with less wind behind it. That is the volume risk, and it is in the result on purpose. PnL_BESS,y comes from the battery model note. The battery is run on its own, so the two parts are simply added.

## 4. Gate 4: the risk of the reference portfolio

Gate 4 asks one question: **how much risk premium would Flower have to charge in this zone to hold the GBL book's bad years within a limit?** EV and ES95 describe the distribution. The implied risk premium turns them into one number per zone that can be compared and scored.

### 4.1 Observations

- **Back-test.** One observation per zone and past contract year, 2020–2025. Six years per zone.
- **Simulation (Phase 2).** One observation per simulated year, at least **200 per zone** **[choice]**, so the worst 5% holds at least ten years.

Gate 4 is scored on the simulation only. Six back-test years cannot carry a 5% tail, because the worst 5% of six years is less than one year. Back-test numbers are reported beside it as a sense check and labelled as such.

### 4.2 Return

  r_y = PnL_total,y / (V_P50 × P_PPA,y)

That is, PnL as a share of the expected yearly payment to the wind producer. A share makes zones with different price levels comparable. The euro figure is reported beside it in every table.

### 4.3 Expected value

  EV = (1 / N) × Σ_y r_y

The strikes have no margin, so EV is the **EV of a zero-margin contract**. In the back-test it mostly shows price drift between the strike year and the delivery year: with the capture rate unchanged, PnL_GBL = V (P̄_y − P̄_y−1)(CR − s). Contract year 2023, struck on 2022 crisis prices, will probably set the loss tail in most zones. Charts should say this is price drift, not a data error.

### 4.4 Expected shortfall at 95%

Sort the N returns from lowest to highest. Let k = ⌈0.05 × N⌉ (k = 10 for N = 200).

  ES95 = − (1 / k) × Σ_{i=1..k} r_(i)

ES95 is reported as a **positive number for a loss**. ES95 = 0.24 means that in the worst 5% of years the book lost on average 24% of the expected PPA payment. A negative ES95 means even the bad years made money. No interpolation between years **[choice]**.

### 4.5 Implied risk premium

The implied risk premium RP* is the smallest margin m (EUR/MWh), added to P_cPPA, that brings ES95 down to a limit L:

  RP* = smallest m ≥ 0 such that ES95(m) ≤ L

The margin is paid on the baseload volume only, so it adds m × B × H = m × s × V_P50 euros to every year, and m × s / P_PPA,y to every return.

- **When every year has the same P_PPA** (the simulation at one evaluation date), every return moves by the same amount and the answer is closed form:

  RP* = max(0, (ES95(0) − L) × P_PPA / s)

- **When P_PPA differs by year** (the back-test), returns move by different amounts and the worst years can change order. Then RP* is found by bisection on [0, 200] EUR/MWh to 0.001 EUR/MWh. ES95(m) falls as m rises, so bisection always works.

**The limit L.** Flower has not told us its risk appetite. Until it does, **L = 0** **[choice]**: the premium that makes the average of the worst 5% of years break even. It reads easily ("the price of making a bad year cost nothing") and needs no number from Flower. If Flower gives a limit, only L changes.

**Two columns, never mixed** (strike rule, section 4): `rp_implied_vs_trailing_spot_eur_mwh` for past contract years and `rp_implied_vs_forward_eur_mwh` for future years, with `evaluation_date` beside it. The forward-risk premium against realised spot is dropped, because it needs forward prices from before each delivery year, which we do not collect.

### 4.6 Gate 4 score and verdict

Gate 4 uses the same scale as the Gate 1, 3 and 5 checklist (`docs/sources/gate-checklists-v1.md`): scores 2 / 1 / 0 / ND and verdicts PASS / CONDITIONAL / FAIL.

| Check ID | Mandatory? | Metric | Scoring anchor (2 / 1 / 0 / ND) |
|---|---|---|---|
| G4-01 | Yes | RP* from the simulation, L = 0 | **2:** RP* ≤ SE3's RP*. **1:** above SE3's, by no more than the margin. **0:** more than the margin above. **ND:** fewer than 200 simulated years, or `flag_low_ppa_price` |
| G4-02 | No | EV of the zero-margin contract | Context only, not scored |
| G4-03 | No | ES95 at m = 0 | Context only, not scored. It feeds G4-01 |

G4-01 uses the same idea as Gate 2 (metric dictionary v1, section 8.2): SE3 is the one benchmark, because Flower already trades GBL there. A zone that needs no more premium than SE3 scores 2. **Margin [choice]:** 25% of SE3's RP*, but at least 1 EUR/MWh, so the rule still works if SE3's RP* is zero or close to it. If Devika's MV-03 method sets the margin differently, her method wins and this table follows it.

**Verdict.** PASS if G4-01 = 2. CONDITIONAL if G4-01 = 1, 0 or ND. Gate 4 has **no hard KO** in v1, the same as Gates 3 and 5 in the checklist, so it cannot FAIL. One difference from the checklist is deliberate: there a Mandatory score of 1 can still PASS, but Gate 4 has only one Mandatory metric, so it needs a 2 **[choice]**.

### 4.7 Output for Coding

One row per zone × observation, `data/processed/gate4/portfolio_years.parquet`: `zone`, `source` (backtest / sim), `contract_year` or `sim_id`, `s`, `p_ppa_eur_mwh`, `p_cppa_eur_mwh`, `evaluation_date` (future years only), `v_actual_mwh`, `pnl_ppa_eur`, `pnl_cppa_eur`, `pnl_bess_eur`, `pnl_total_eur`, `return_ratio`, plus the flags.

One row per zone × source × s, `data/processed/gate4/gate4_summary.parquet`: `n_years`, `ev_return_ratio`, `es95_loss_ratio`, `rp_implied_vs_trailing_spot_eur_mwh` or `rp_implied_vs_forward_eur_mwh`, `limit_l`, `gate4_score`, `gate4_verdict`, and the same three numbers in euros.

## 5. Checks with known answers

From v0 (all still hold):

- Fixture A (metric dictionary, section 7) as year y − 1: P_cPPA = 12.625, P_PPA = 12.625 × 0.974573 = **12.303984** EUR/MWh.
- Zero-margin identity. Struck from the GBL Explained example year (P̄ = 50, CR = 0.85): P_cPPA = 50, P_PPA = 42.5. If year y repeats that year, PnL_GBL = **0** at s = 30%, 40% and 50%.
- Same strikes, prices 10% higher (P̄ = 55, V = 100,000 MWh): PnL_GBL = 275,000 / **225,000** / 175,000 € at s = 30 / 40 / 50%.
- Same strikes, capture rate down to 0.80: PnL_GBL = **−250,000 €** at every share.
- GBL Explained worked example (P_PPA = 35, P_cPPA = 55, P̄ = 50, CR = 0.85): PnL_GBL = 900,000 / **950,000** / 1,000,000 € at s = 30 / 40 / 50%.

New for Gate 4 (Fixture G, synthetic, 30 years, s = 0.4, P_PPA = 42.5 EUR/MWh in every year, V_P50 = 100,000 MWh):

  returns = 0.12, 0.08, 0.05, 0.10, −0.02, 0.03, 0.07, −0.30, 0.01, 0.04, 0.09, −0.06, 0.02, 0.06, 0.11, −0.10, 0.00, 0.05, 0.03, 0.08, 0.04, −0.18, 0.06, 0.02, 0.07, 0.01, 0.09, −0.04, 0.05, 0.03

| Result | Working | Answer |
|---|---|---|
| EV | 0.61 / 30 | **0.020333** |
| k | ⌈0.05 × 30⌉ | **2** |
| ES95 | −(−0.30 − 0.18) / 2 | **0.24** |
| RP*, L = 0 | 0.24 × 42.5 / 0.4 | **25.5** EUR/MWh (1,020,000 € a year) |
| RP*, L = 0.10 | 0.14 × 42.5 / 0.4 | **14.875** EUR/MWh (595,000 € a year) |
| Check | add m × 0.4 / 42.5 to every return and recompute ES95 | 0 and 0.10 |
| Same returns, P_PPA,y = 40, 42.5, 45, 47.5, 50 repeating | bisection, L = 0 | **26.228571** EUR/MWh |

G4-01 scoring (section 4.6), with SE3's RP* = 20 EUR/MWh (margin 5): a zone at 18 scores 2, at 24 or 25 scores 1, at 26 scores 0. With SE3's RP* = 0 the margin is the 1 EUR/MWh floor: 0.8 scores 1 and 1.5 scores 0.

`python tests/hand_check_gate4.py --selftest` asserts every number in this table, the erosion check in metric dictionary v1 (section 4b) and its Gate 2 threshold test (section 8.3).

## 6. Questions for Flower, in the order that unlocks the most work

1. **Battery.** 100 MWh with 25 MW, or 100 MW with 400 MWh? The battery model cannot start without it. Please also confirm 100 MW of onshore wind.
2. **Strikes.** Do you confirm both formulas and the one-year re-strike? For future years, should the producer price use last year's capture rate, a 3-year average, or your own capture-rate view?
3. **Risk limit L.** How do you judge a bad year internally: a loss limit in euros, a share of the contract value, or something else? Until we hear, we use L = 0.
4. **Baseload share.** Is 40% a fair central case?
5. **Contract tenor.** Are your cPPAs usually one year, or several years at one strike?

## Appendix A. Plain-language version for the other groups

- **Reference portfolio.** The same imaginary book in every country: 100 MW of onshore wind, a 100 MWh battery, and 40% of the expected wind sold as a flat block to a customer. Same book everywhere, so any difference comes from the market.
- **Strike.** The two fixed prices in the book. For past years we use last year's average market price, and last year's wind capture rate times that price for the wind producer. For future years we use the futures price on a named date.
- **Zero margin.** We do not add any profit on top of the strikes. That way the results show the market's risk, not our pricing.
- **Return.** A year's profit or loss as a share of what Flower expects to pay the wind producer that year. 0.10 means a profit of 10% of that payment.
- **EV.** The average return over all years. Close to zero is expected, because there is no margin.
- **ES95.** Take the worst 5% of years and average their losses. ES95 = 0.24 means a bad year loses about a quarter of the yearly PPA payment.
- **Implied risk premium.** How many euros per MWh Flower would have to add to the customer's price so that those bad years break even. The lower it is, the safer the country.
- **Gate 4 verdict.** PASS if a country needs no more premium than SE3, where Flower already trades GBL. CONDITIONAL otherwise. Gate 4 never fails a country on its own.

## Appendix B. Questions for the other groups

**Coding**

1. Can the engine store results per hour for one zone-year, so we can check PnL_PPA and PnL_cPPA by hand on Fixture A before the full run?
2. Which evaluation date will the first future-year run use? It has to be written on every result.
3. Does metric dictionary v1's onshore-only capture rate (`capture_rate_nonneg_wind_onshore_ratio`) exist in the indicator table yet, or should the engine compute it?
4. Who writes PnL_BESS, and when can Gate 4 expect its first numbers?

**Market Analysis**

1. For SE3, do you have any evidence of the risk premium Flower or other sellers actually charge? It would tell us whether our RP* numbers are realistic.
2. For Italy, which zones do you see as realistic for an onshore wind PPA? We use it to check the zone rule.
