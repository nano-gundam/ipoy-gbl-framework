# PW01-MV-01: Gate 1 & Gate 3 Screening Checklists (v0)

**Version:** v0 (Calibrated against Sweden)  
**Target Path:** `docs/checklists/gate-checklists-v0.md`  
**Aligned Architecture:** Flower Green Baseload (GBL) Back-to-Back Model & Standalone BESS Operations  
**Date Verified:** 2026-10-16  

---

## 1. Design Principles & Alignment with Flower's Business Model

Per Flower's official operational framework (*GBL Explained*), Green Baseload is **not** a physically co-located wind-plus-battery engineering project. Instead, it operates via three parallel market legs:
1. **Supply Leg (Pay-as-Produced PPA):** Flower buys variable wind/solar output at a fixed PPA price, protected by a **Negative Price Protection** clause ($\mathbb{I}[P_h^{DA} \ge 0]$) where PPA payments pause or output is curtailed during negative Day-Ahead (DA) price hours.
2. **Demand Leg (Baseload cPPA):** Flower sells 30%–50% ($0.3 \le s \le 0.5$) of expected annual generation as a flat 24/7 baseload profile to corporate off-takers at a fixed cPPA price, transferring **Guarantees of Origin (GoOs)** where requested.
3. **Market & BESS Leg (BRP + Standalone BESS):** Flower acts as the **Balance Responsible Party (BRP)** to clear volumes in the DA auction and settle imbalances, while operating its **Battery Energy Storage Systems (BESS) standalone** in profit-maximization mode across DA arbitrage and TSO ancillary services ($\max[\sum P_h^{DA}(D_h - C_h) + \sum P_h^{AS} Q_h^{AS}]$).

Consequently, **Gate 1 (Regulatory & Market Entry Feasibility)** tests whether Flower can legally and operationally execute BRP/BSP roles, negative-price dispatch, GoO transfers, and standalone BESS stacking without punitive double network charges. **Gate 3 (Commercial Opportunity)** tests whether the local B2B electricity market and corporate PPA liquidity are large and mature enough to absorb baseload cPPAs at a viable shape-risk premium.

### Scoring Convention
- **PASS (Green / 2 pts):** Statutory and market rules fully support Flower's operating model with standard onboarding.
- **FLAG (Yellow / 1 pt):** Market is legally accessible, but structural friction exists (e.g., severe regional grid congestion queues, partial DSO tariff ambiguity, or moderate liquidity requiring cross-border sleeving). Requires commercial/risk adjustment in Gate 2/4/5.
- **FAIL (Red / 0 pts — Hard Knock-out):** Legal prohibition or structural barrier prevents foreign BRP/BSP registration, bans corporate PPAs, or imposes unrecoverable double taxation on standalone storage. Country is eliminated at Gate 1/3.

---

## 2. Gate 1 Checklist: Regulatory, BRP/BSP & Grid Feasibility

| Check ID | Evaluation Question | Why It Matters for Flower (GBL + BESS) | PASS (Green) Criteria | FLAG (Yellow) Criteria | FAIL (Red / Knock-out) Criteria | Required Source Type (MR-02 / MR-03) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **G1-01** | **Foreign BRP Registration & Wholesale Market Access:** Can a non-domestic EU/EEA trading entity register as a Balance Responsible Party (BRP) and trade directly on the Day-Ahead and Intraday exchanges? | Flower must sit between Partner A (PPA) and Partner B (cPPA) as BRP, bidding forecast wind volumes into the DA auction and buying back flat baseload volumes. | Foreign EU/EEA entity can become a BRP via standard TSO/settlement contract (e.g., eSett, Bilanzkreisvertrag) without requiring a local generation license. | Local subsidiary or fiscal representative is required for tax/collateral purposes, adding 3–6 months of administrative lead time. | BRP status is restricted to state-owned utilities or vertically integrated domestic incumbents. | TSO BRP Onboarding Guide / Imbalance Settlement Body (e.g., eSett, TSO Portal) |
| **G1-02** | **Imbalance Settlement Granularity & Transparency (15-min ISP):** Does the market operate on a 15-minute Imbalance Settlement Period (ISP) with transparent, non-punitive single/dual pricing rules? | Accurate imbalance settlement is essential for managing forecast deviations on wind PaP PPAs and optimizing intraday positions. | 15-min ISP is live (aligned with EU Electricity Balancing Guideline EBGL) with transparent TSO/settlement publication of imbalance prices. | Transition to 15-min ISP is delayed or dual-price penalties create asymmetric imbalance exposure requiring higher risk premiums. | Opaque, retrospective, or punitive administrative imbalance penalties that prevent algorithmic risk modeling. | TSO Balancing Agreement / Settlement Rules |
| **G1-03** | **Standalone BESS Ancillary Services Access (BSP Role):** Can standalone battery storage (BESS) prequalify as a Balancing Service Provider (BSP) to bid into FCR, aFRR, and mFRR capacity and energy markets? | Flower operates BESS standalone in profit-maximization mode ($\max[\text{DA} + \text{AS}]$). Reserve market access is a primary revenue driver for BESS. | Standalone BESS and aggregators can prequalify independently for FCR, aFRR, and mFRR under clear technical PQ guidelines. | BESS allowed in FCR, but aFRR/mFRR face restrictive duration rules (>2–4h minimum) or TSO-zone-specific manual testing bottlenecks. | Standalone BESS is legally barred from providing TSO system reserves or restricted to thermal/hydro generators. | TSO Ancillary Services & Prequalification Rules |
| **G1-04** | **BESS Double Network Charge & Tariff Exemption:** Is grid-scale standalone BESS exempt from paying double network charges (i.e., taxed both as final consumption when charging and as generation when discharging)? | Double grid fees destroy standalone BESS DA arbitrage spreads and reduce net reserve margins. EU Directive 2019/944 & Regulation 2024/1747 mandate removal of double charges. | Statutory federal/national exemption or >80% tariff relief for grid-scale BESS feeding back into the grid (e.g., DE EnWG § 118 Abs. 6). | Partial exemption (e.g., transmission fee waived, but local DSO volumetric/capacity charges or flexible connection caps apply). | Full double taxation (charging treated as irreversible final industrial consumption with non-refundable grid tariffs and levies). | National Energy Regulator (NRA) Tariff Methodology / Electricity Act |
| **G1-05** | **Negative Price Curtailment & Dispatch Freedom:** Do market and grid rules allow contractual curtailment or automated dispatch shut-off during negative Day-Ahead price hours? | Flower's PaP PPA relies on the Negative Price Protection indicator $\mathbb{I}[P_h^{DA} \ge 0]$ to avoid paying fixed PPA prices when DA prices drop below 0 €/MWh. | Full contractual freedom to curtail or pass through negative DA prices; no statutory must-run obligation on merchant/PPA wind parks. | Redispatch 2.0 or TSO congestion rules require administrative coordination prior to automated price-driven curtailment. | Regulatory prohibition on economic curtailment or mandatory floor payments that override bilateral PPA negative-price clauses. | National Electricity Market Law / TSO Grid Code |
| **G1-06** | **Grid Connection Access & Queue Transparency (BESS & Wind):** Are TSO/DSO grid connection procedures transparent, and is firm or flexible (non-firm) capacity available for new BESS/RES assets? | Even with financial GBL hedging, physical BESS deployment and new wind PPA supply depend on viable grid connection timelines. | Transparent connection process with available substation capacity or established flexible/time-bound connection contracts. | Severe regional grid congestion (e.g., multi-year waitlists on capacity maps), requiring location-specific screening or non-firm contracts. | Nationwide moratorium/freeze on grid feed-in/off-take connections for BESS and renewable energy projects. | TSO Connection Rules / National Grid Capacity Map |

---

## 3. Gate 3 Checklist: Commercial Opportunity & Corporate PPA Demand

| Check ID | Evaluation Question | Why It Matters for Flower (GBL + BESS) | PASS (Green)