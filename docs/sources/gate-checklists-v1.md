# PW03-MR-00 — Gate 1, Gate 3 and Gate 5 Screening Checklist (Proposed v1)

**Status:** Frozen working version for Sunday country screening. Pending Methodology & Validation sign-off.  
**Prepared:** 15 November 2026  
**Markets:** SE3, NL, DE-LU, ES, IT, PL, LT  
**Purpose:** A concise, traceable screening checklist. It is not a full investment case or a Gate 2 revenue model.

---

## 1. Scoring and Gate verdict rules

### 1.1 Score scale

| Score | Meaning | How to use it |
|---|---|---|
| 2 | Favourable | Evidence clearly supports the criterion and the route is operationally usable. |
| 1 | Partly favourable | The route or market exists, but there are material limitations, conditions, delays, or evidence gaps that can be managed or clarified. |
| 0 | Unfavourable | Reliable evidence confirms a material weakness or barrier. A score of 0 is not automatically a KO. |
| ND | Not determined | The evidence is missing, too weak, or not at the required geographic level. ND is not zero. |

Do not use decimal scores. Keep explanations, dates, geography, assumptions, calculations, and any KO flag in the Evidence & Metric cell.

### 1.2 Baseline Mandatory items for Proposed v1

The following five items are baseline Mandatory items. If any Mandatory item is ND or scores 0, the relevant Gate cannot receive PASS and should be marked CONDITIONAL unless a confirmed KO requires FAIL.

| Gate | Check ID | Mandatory? | Reason |
|---|---|---|---|
| Gate 1 | G1-01 | Yes | Flower needs a workable BRP/wholesale-market access route, directly or through a partner. |
| Gate 1 | G1-07 | Yes | The corporate baseload contracting structure must be legally and practically feasible. |
| Gate 3 | G3-01 | Yes | A minimum level of relevant demand is fundamental to commercial opportunity. |
| Gate 3 | G3-02 | Yes | Evidence of corporate buyer appetite is a core commercial screen. |
| Gate 5 | G5-01 | Yes | A credible renewable generation/capacity trajectory is required for long-term scalability. |

All other checklist items are **non-mandatory** for this first screen. In particular, G3-03 Futures Liquidity and G5-02 BESS Pipeline are non-mandatory because reliable public evidence may be incomplete. Their ND status must still be recorded and followed up where material.

### 1.3 Gate verdicts

| Verdict | Rule |
|---|---|
| FAIL | A pre-defined hard-KO condition is confirmed by sufficient evidence. |
| CONDITIONAL | No confirmed KO, but a Mandatory item is ND or scores 0, a material issue remains unresolved, or evidence is insufficient for a full pass. |
| PASS | No confirmed KO; every Mandatory item is evidenced and scores at least 1; and material non-mandatory issues are explained or reasonably mitigated. |

A KO must be based on evidence, not on an assumption. For Proposed v1, G1-01 and G1-07 are the only candidate hard-KO items. A KO is confirmed only if both relevant operating routes are infeasible. G1-03 is not a baseline Mandatory item. It can only become a KO question if Flower confirms that standalone BESS ancillary services are essential and both direct and partner routes are unavailable. No independent hard KO is assigned to Gate 3 or Gate 5 in this version.

**Important:** A score of 0 does not by itself mean FAIL. Use FAIL only when the specific hard-KO condition is confirmed. Otherwise, a Mandatory score of 0 leads to CONDITIONAL.

## 2. Geographic resolution rules

| Topic | Geographic level | Required treatment |
|---|---|---|
| Regulation and legal market access | National | For SE3, use Swedish national rules. For DE-LU, check Germany and Luxembourg separately. |
| BRP/BSP qualification | National / relevant TSO product | Record the actual TSO, settlement-body or BSP qualification route and its scope. |
| Day-ahead prices | Bidding zone | Use SE3 for the SE3 market. Do not substitute Swedish national prices. |
| Wind and solar installed capacity / generation | Bidding zone where available | Use the relevant bidding-zone data. Label national data as a proxy when no zone split is available. |
| Industrial + commercial/public-services consumption | National proxy if no suitable zone split exists | Label `National Proxy for SE3` or the relevant proxy. Do not call it bidding-zone data. |
| Corporate PPA activity | National proxy if no zone split exists | State the geography and limitations. Existing PPA activity is a buyer-appetite proxy, not Flower's addressable market share. |
| DE-LU market prices and wind | DE-LU bidding zone where available | Do not replace the combined bidding-zone series with a Germany-only or Luxembourg-only series without labelling it. |
| DE-LU demand and corporate PPA activity | Combined Germany + Luxembourg evidence if same-scope data are available | If not, use `Germany-only proxy (Luxembourg excluded)`. Do not imply that Luxembourg is immaterial. |
| Italy | One national scorecard with an embedded seven-zone preliminary screen | Score national legal questions once. Explain bidding-zone differences in the relevant Evidence cells. Do not produce seven complete scorecards for the Sunday screen. |
| Lithuania (LT) / Baltic regulation | Reuse genuinely common regional research | Produce an LT scorecard only. Reuse Baltic-wide regulatory research only where the rule genuinely applies to Lithuania, and support every LT score with Lithuania-specific evidence (e.g. Litgrid, VERT and national legal sources). EE and LV are outside this PW03 scope. |

**SE3 description:** `Nuclear-dominant southern Swedish bidding zone with significant hydropower inflows and growing wind generation.` Do not describe SE3 as hydro-dominant based on Sweden-wide generation mix.

## 3. Gate 1 — Market access and regulatory feasibility

| Check ID | Mandatory? | Evaluation Question | Scoring anchor (2 / 1 / 0 / ND) |
|---|---|---|---|
| G1-01 | Yes | BRP Registration & Wholesale Market Access | **2:** Foreign entity can use a documented standard BRP route without a local generation licence. **1:** A foreign-entity route is identified, but eligibility, onboarding, collateral or direct-vs-partner details remain conditional or incomplete. **0:** Evidence confirms both direct and realistic third-party BRP routes are unavailable. **ND:** Foreign-entity eligibility or partner route is not established. |
| G1-02 | No | Imbalance Settlement Granularity & Transparency | **2:** 15-minute ISP is live and imbalance prices/settlement data are transparently published. **1:** 15-minute transition is incomplete, or pricing/transparency limitations create manageable exposure. **0:** Opaque or punitive rules prevent reliable imbalance-risk modelling. **ND:** ISP or settlement transparency cannot be verified. |
| G1-03 | No | Standalone BESS Ancillary Services Access | **2:** Standalone BESS can qualify directly or through an aggregator for the relevant FCR/aFRR/mFRR products under clear rules. **1:** Access is limited by product, duration, minimum size, testing, or partner requirements. **0:** Standalone BESS is confirmed legally barred from relevant reserve services. **ND:** BESS-specific eligibility or prequalification evidence is missing. |
| G1-04 | No | BESS Network Tariffs & Double-Charging Treatment | **2:** Applicable rules provide a clear exemption or tariff treatment that avoids material double network charges for the relevant BESS configuration. **1:** Relief is partial, conditional, time-limited, or varies by tariff/network level. **0:** Full, unrecoverable double network charges are confirmed for the relevant configuration. **ND:** Applicable national law and NRA/DSO tariff decisions have not been checked. |
| G1-05 | No | Negative Price Curtailment & Dispatch Freedom | **2:** Contractual negative-price protection and economic curtailment/dispatch are permitted without a material legal restriction. **1:** Permitted but subject to redispatch, grid-code, or operational coordination constraints. **0:** A confirmed legal rule prevents economic curtailment or overrides the relevant bilateral negative-price mechanism. **ND:** Contractual and market rules are not established. |
| G1-06 | No | Grid Connection Access & Queue Transparency | **2:** Transparent connection process and credible firm/flexible capacity route are evidenced for relevant locations. **1:** Congestion, long queues, or non-firm connection conditions exist but location-specific routes remain. **0:** A nationwide connection moratorium/freeze blocks relevant new connections. **ND:** No usable queue/capacity evidence at the relevant location. |
| G1-07 | Yes | Corporate PPA & Baseload Contracting Legal Feasibility | **2:** Both relevant physical and financial/virtual PPA structures have a workable legal and delivery route. **1:** At least one relevant structure is workable, but it needs a retailer/BRP sleeve, local contractual adaptation, or other material condition. **0:** All commercially relevant structures required by Flower are confirmed prohibited or infeasible. **ND:** National contract rules or the delivery route have not been verified. |

### Gate 1 legal caution

Do not treat EU-level provisions as blanket BESS exemptions. Directive (EU) 2019/944 Article 36 concerns DSO ownership of storage. Article 15(5)(b) addresses specific active-customer circumstances and does not create a universal standalone-BESS exemption. Regulation (EU) 2019/943 Article 18(1) sets general principles for network tariffs; it does not automatically exempt BESS from all charges. Check national implementation and the applicable NRA/TSO tariff decisions.

## 4. Gate 3 — Commercial opportunity

| Check ID | Mandatory? | Evaluation Question | Scoring anchor (2 / 1 / 0 / ND) |
|---|---|---|---|
| G3-01 | Yes | Industrial & Commercial Electricity Demand Scale | **2:** Above 80 TWh/year. **1:** 20–80 TWh/year. **0:** Below 20 TWh/year. **ND:** No comparable demand value is available. These are provisional working anchors only, pending Flower's minimum ticket-size input. |
| G3-02 | Yes | Corporate PPA Activity & Buyer Appetite | **2:** Repeated, material, publicly documented corporate PPA activity over the review window. **1:** Some activity is documented, but it is more limited, concentrated, or less transparent. **0:** Reliable evidence confirms negligible activity or a material barrier to corporate PPAs. **ND:** Public evidence cannot reliably distinguish corporate from utility PPAs or is too incomplete. |
| G3-03 | No | Baseload Futures & Forward Hedging Liquidity | **2:** Actual trading evidence supports usable liquidity across relevant tenors (e.g. volume, open interest and/or bid-ask quotes). **1:** Contracts exist but liquidity, tenors or trading evidence are limited. **0:** Reliable evidence confirms no usable forward market or negligible liquidity. **ND:** Trading data are unavailable. A listed contract or short-term price average alone is not proof of liquidity. |
| G3-04 | No | GoO / EECS Market Functionality | **2:** Relevant issuing body and EECS Electricity Scheme are confirmed, AIB Hub connection is confirmed, and actual cross-border transfers are evidenced. **1:** A registry/issuing body or EECS arrangement exists, but one or more operational elements remain unverified. **0:** A formal restriction prevents relevant issuance or transfer. **ND:** Scheme membership, Hub connection or transfer evidence is missing. |

### G3-01 provisional demand anchor

Use the metric name `Industrial + Commercial/Public Services Electricity Consumption (TAM Proxy)`. The current Eurostat proxy is `FC_IND_E + FC_OTH_CP_E` in `nrg_bal_c` (SIEC E7000 Electricity). Because `FC_OTH_CP_E` includes commercial and public services, this is not a pure private-sector B2B measure.

The 20/80 TWh bands are labelled `[Working Screening Anchor — Pending Flower Minimum Ticket Size]`. They are not official statistical natural breaks and are not a confirmed Flower minimum-market-size threshold. Do not make discretionary buyer-size exceptions to the score. Record relevant large-buyer evidence in the Evidence cell for later calibration.

### Gate 2 boundary — non-scored context only

Gate 3 must not re-score Gate 2 economics. The following remain non-scored Gate 2 context: baseline price levels, price volatility, negative-price time, wind/solar capture rates and capture-rate erosion, and intraday 2-hour/4-hour spreads. Cite the shared metric dictionary rather than recalculating them in the Gate 3 scorecard.

## 5. Gate 5 — Scalability and market development

| Check ID | Mandatory? | Evaluation Question | Scoring anchor (2 / 1 / 0 / ND) |
|---|---|---|---|
| G5-01 | Yes | Wind & Solar Capacity Trajectory | **2:** Relevant-zone wind and solar capacity/generation show a sustained, credible growth trajectory. **1:** Growth is positive but uneven, concentrated in one technology/zone, or constrained by credible delivery risks. **0:** Adequate official data confirm no material trajectory or a sustained decline. **ND:** Comparable zone-level time series are missing. |
| G5-02 | No | BESS Installed Capacity & Credible Pipeline | **2:** Official evidence shows commissioned capacity plus a material under-construction/permitted pipeline. **1:** Some commissioned capacity or credible pipeline exists, but coverage/scale is limited. **0:** An adequate official registry confirms no material capacity or pipeline. **ND:** No reliable registry or project-status data. |
| G5-03 | No | 2030 NECP Renewable & Storage Targets | **2:** Quantified renewable/storage targets are supported by credible policies and visible delivery progress. **1:** Targets exist, but progress, implementation or delivery credibility is mixed. **0:** Official evidence shows material failure to deliver or policy direction inconsistent with the targets. **ND:** The relevant final NECP and progress evidence have not been reviewed. |
| G5-04 | No | PICASSO / MARI Balancing Integration | **2:** The relevant TSO is operationally integrated into both PICASSO and MARI. **1:** It is integrated into one, or one/both are in a confirmed testing or phased implementation stage. **0:** It is integrated into neither and no credible implementation path is documented. **ND:** TSO participation/status is not verified. |
| G5-05 | No | 2027–2035 Enacted Market-design Reforms & Long-term Scalability | **2:** Enacted legislation or formal TSO/NRA plans clearly improve access, flexibility, liquidity or scalable deployment. **1:** Formal measures exist but are phased, delayed, narrow or uncertain in effect. **0:** Enacted restrictions or formal plans materially constrain scalability. **ND:** Only speculative announcements or no usable forward-looking evidence are available. |

### Gate 5 evidence rules

- Separate BESS capacity into **commissioned**, **under construction**, and **permitted/approved**. Do not merge them into installed capacity.
- Prefer TSO/NRA/official registers. Missing ENTSO-E B25 data is ND, never zero.
- G5-05 covers future enacted rules and formal TSO/NRA plans. Current BRP/BSP onboarding and current grid-connection queues remain Gate 1 topics.
- Prioritise onshore wind in the initial screen. Research offshore wind separately in greater depth only when offshore generation is approximately 10% or more of the relevant market's generation. This ~10% is a research-scope trigger, not a score threshold.

## 6. Practical country-specific instructions

### Italy

Aida produces **one Italy scorecard**, not seven full scorecards. Score national legal/regulatory questions once. For zone-sensitive questions, especially G5-01 and any Gate 2 Context reference, put a concise preliminary scan of all seven bidding zones in the same Evidence cell. State the data used, identify the shortlisted zones only after checking the evidence, and explain why other zones are lower priority. Do not pre-fill `IT-Sud`, `IT-Sicilia`, `IT-Sardegna`, or `IT-Nord` as confirmed winners without supporting data.

### Lithuania (LT) — Baltic regulatory context

Common Baltic regulatory research may be reused where the rule genuinely applies to Lithuania. Produce one Lithuania scorecard only, with Lithuania-specific evidence (e.g. Litgrid, VERT and national legal sources). Estonia (EE) and Latvia (LV) are not part of this PW03-MR-00 seven-market scope and must not receive separate scorecards.

### Capture-rate comparison with KYOS

Keep the team's bidding-zone/country calculations separate from KYOS asset/park-level outputs. Label the calculation basis and explain the difference. Do not modify one dataset merely to force numerical agreement.

## 7. Required scorecard format

Every country scorecard must use this exact five-column header:

`Check ID | Evaluation Question | Score (0/1/2/ND) | Evidence & Metric | Source URL`

Use one row per checklist item. In the Evidence cell, state the reporting year, geographic level, proxy label, source limitation and missing evidence where relevant. Put `[VERIFY URL]` beside a generic landing-page link when the exact supporting subpage still needs manual verification.

## 8. Sunday hand-off checklist

1. Fill all 16 rows for each assigned market. Use ND rather than infer missing values.
2. Apply the same Mandatory status and scoring anchors in every country.
3. Add a country × Gate verdict matrix using PASS / CONDITIONAL / FAIL.
4. Keep Italy to one national scorecard with a seven-zone preliminary screen in the relevant Evidence cells.
5. Flag unresolved Flower/Methodology questions separately. Do not silently convert proposed assumptions into approved rules.
6. Use standard GitHub Flavored Markdown pipe tables (`|`); do not convert tables to Pandoc grid or multiline syntax.

**Version status:** Proposed v1 frozen for the Sunday screening exercise. Any substantive methodology change requires Methodology & Validation review.
