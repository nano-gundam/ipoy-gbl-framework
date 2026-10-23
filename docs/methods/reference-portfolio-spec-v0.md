# Reference portfolio specification v0

Task: PW02-MV-05 · Author: Wenhao Gu · Review: Devika · Pre-read for the definitions workshop, sent by Aida · Status: draft v0, 22 Oct 2026
Path in repo: `docs/methods/reference-portfolio-spec-v0.md`

We simulate the same reference portfolio in every country, so that differences in results come from the markets themselves. Our log of Flower's 9 Oct answers gives its size as **100 MW of wind and a 100 MWh battery with 4 hours of storage**. The written minutes of that meeting do not record it, so question 1 asks Flower to confirm. Four parameters are still open. They are the strike rule, the baseload share, the battery's power rating and the expected shortfall convention. Each one below has a proposed value, a reason and an alternative, so the workshop can close it in one pass. The definitions lock on 30 November.

## What has changed since our 6 Oct options note

- **Decision 1 (which portfolio).** Flower answered it on 9 Oct with one fixed portfolio for every country. Sizing the battery per country for equal delivery reliability (our option B) is dropped. Solar is left out because the 9 Oct answer names only wind and a battery. On 16 Oct Jorge described GBL as "wind and solar PPAs" plus baseload, so question 1 asks about solar too.
- **Decision 3 (what the battery may do).** GBL Explained, section 6, settles it. The battery runs standalone for profit, on day-ahead arbitrage and ancillary services. It does not firm the wind, so shape risk stays in the PPA and cPPA legs.
- **Decision 2 (how risk is measured)** is still open and is item 6 below.

## The specification

| # | Parameter | Proposed value | Reason | Alternative | If the alternative is chosen |
|---|---|---|---|---|---|
| 1 | Wind | 100 MW. Hourly output = the zone's ENTSO-E wind generation (on + offshore) scaled to 100 MW by installed capacity | Size from Flower on 9 Oct. The zone profile is public for every country and is built the same way everywhere | A single representative park profile per zone (Flower data or reanalysis) | More realistic capture rate and imbalance, but results depend on which park is picked |
| 2 | Expected output V_P50 | P50 wind year: the median annual energy of the scaled profile over 2019–2025 | Volume risk is measured against a normal year, as a P50 is used when contracting | Mean year, or a long-term P50 from 20+ years of reanalysis | One extreme year pulls the mean. A long-term P50 is more robust but adds a data source |
| 3 | Baseload share s | **40%**, with 30% and 50% as sensitivities | Middle of Flower's permitted 30–50% range, and the central case of the GBL Explained worked example | Run 30%, 40% and 50% as three equal cases | Three times the results tables. The method is the same |
| 4 | Baseload volume B | s × V_P50 / H, fixed for the contract year | Formula in GBL Explained, section 1 | (none proposed) | n/a |
| 5 | Strike rule | **See PW02-MV-04.** Past years struck at the previous year's realised baseload price and wind capture rate. Future years struck from the forward curve on a stated evaluation date (two-month average) | Flower's guidance of 16 Oct | 24-month window for past years (sensitivity in MV-04) | Smoother strikes, so less year-on-year drift shows up as risk |
| 6 | Risk measure | **Expected shortfall at 95% on annual portfolio return**: the mean return of the worst 5% of simulated years. Return = annual PnL (GBL + battery) ÷ expected annual PPA payment, V_P50 × P_PPA **[choice]** | Stable, and comparable across countries with different price levels | ES95 on annual PnL in euros | With the same portfolio size everywhere, euros no longer penalise a country for needing a bigger battery. The figure adds directly to Flower's book, but high-price countries then look riskier partly because every cash flow is bigger |
| 7 | Battery | **100 MWh at 4 hours = 25 MW** | Reading of "100 MWh (4-hour)" in the 9 Oct answer | **100 MW at 4 hours = 400 MWh** (flagged: the answer can be read this way) | Battery revenue and risk scale about four times. The battery can then outweigh the GBL legs, and rankings move towards markets with wide price spreads and deep reserve markets |
| 8 | Battery operation | Standalone, profit-maximising across day-ahead arbitrage and ancillary services | GBL Explained, section 6 | (settled) | n/a |
| 9 | Contract tenor | One year, struck again each year | Matches the strike rule. Keeps every contract year a separate observation | Multi-year cPPA (3–5 years) at one strike | Price drift builds up over the tenor, so the tail gets much heavier |
| 10 | Negative-price protection | PPA leg earns zero in hours with a negative day-ahead price | GBL Explained, section 3 | (settled) | n/a |
| 11 | Imbalance cost | **Left out** in v0, as in GBL Explained | Too complex for v0, and Flower left it out of its own equations | A per-zone cost in EUR/MWh of wind output | Lowers wind PnL most in zones with poor forecasts or harsh imbalance pricing. Can reorder countries that score close together |
| 12 | Baseline market | **SE3**. Every country is also reported relative to it | Flower asked on 9 and 16 Oct for Sweden as the baseline, since it trades GBL there. SE3 holds most Swedish load **[choice]** | SE4, or all four Swedish zones | SE4 has higher and more volatile prices, so other countries would look calmer next to it |
| 13 | GoOs | Left out | GBL Explained, section 2: GoOs are valued separately from the power in both legs, so leaving them out does not change the power PnL | Include a GoO price on both legs | Small change, unless GoO prices differ a lot by country |

Three caveats. ENTSO-E capacity describes the start of each year (dictionary 6.1), so in a zone that adds a lot of wind during the year, scaling by it overstates output a little (items 1 and 2). In zones with very low prices, where P_PPA falls below 5 EUR/MWh, the return in item 6 becomes unstable. There it is reported with `flag_low_ppa_price` and the euro figure is used instead, the same guard as the low-baseload rule in dictionary section 4 **[choice]**. Battery efficiency, cycle limits and the reserve products it bids into are set in the battery model note.

**A note on item 6.** Our back-test has only six past contract years per zone (2020–2025), and the worst 5% of six years is less than one year. ES95 can therefore only be estimated from the simulation built in Phase 2. That needs at least 200 simulated years per zone **[choice]**, so that the tail holds at least ten years. v0 fixes how ES95 is defined. The numbers come in Phase 2.

## Questions for Flower, in the order that unlocks the most work

1. **Battery reading and portfolio size.** Is the battery 100 MWh with 25 MW power, or 100 MW with 400 MWh? It changes the scale of every battery result, and the battery model cannot start until we know. Please also confirm 100 MW of wind, and whether solar should be in.
2. **Baseload share.** Is 40% a fair central case? Or does Flower in practice sell close to one end of the 30–50% range?
3. **Imbalance cost.** Should we include it? If yes, does Flower have a per-zone figure (EUR/MWh) we can use, or should we estimate it from public imbalance prices?
4. **Risk measure.** Annual return as defined in item 6, or PnL in euros? Which matches how Flower reports risk internally?
5. **Contract tenor.** Does a one-year re-strike represent the risk well, or are Flower's cPPAs usually multi-year?
6. **Strike formulas.** Please confirm the two formulas in MV-04.
