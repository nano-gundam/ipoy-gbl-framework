# Progress log: Wenhao Gu (Method & Validation)

Status of my tasks from the Notion Tasks Tracker, kept next to the work itself. Notion status is set by the group leader. This file says what exists, where it is, and what is still open.

Last updated: 21 Nov 2026

## Open tasks

| Task | Notion status | Due | Output | Where it stands |
|---|---|---|---|---|
| PW02-MV-04 · Strike rule | Need review | 24 Oct (cards close 9 Nov) | `docs/methods/strike-rule-v0.md` | v0 merged 24 Oct. v0.1 (8 Nov) switches the producer price to the onshore capture rate after Flower's 26 Oct decision. Waiting for Devika's check. |
| PW02-MV-05 · Reference portfolio spec v0 | In progress | 26 Oct (cards close 9 Nov) | `docs/methods/reference-portfolio-spec-v0.md` | v0 merged 24 Oct. v0.1 (8 Nov): onshore wind only, SE3 settled. The workshop pre-read step was overtaken, since the definitions workshop moved to the 11 Dec visit. Waiting for Devika's review. |
| PW03-MV-00 · Methodology & Validation (with Devika) | In progress | 16 Nov | `docs/methods/reference-portfolio-spec-v1.md`, `docs/methods/metric-dictionary-v1.md`, `tests/hand_check_gate4.py` | v1 drafts up for review (16 Nov). Spec v1 folds in the strike rule and defines Gate 4 (EV, ES95, implied risk premium, score and verdict). Dictionary v1 adds the onshore capture rate, capture-rate erosion, the zone rule (Italy on zonal prices) and a Gate 2 threshold proposal. The thresholds are a proposal until Devika's MV-03 method is in. Flower's 16 Nov answers go into v1.1 before the 30 Nov lock. |

## Done

| Task | Output |
|---|---|
| PW01-MV-03 · Screening indicator definitions | `docs/methods/metric-dictionary-v0.md`, `tests/hand_check_se3_2024.py`, `tests/fixtures/se3_2024-07-27_29_entsoe.csv` |
| PW01-MV-04 · One-page options note for Flower | Sent to Aida, 8 Oct |

## Decisions from Flower that my documents depend on

- 16 Oct: past years struck from realised day-ahead prices, future years from the curve on a stated evaluation date. No futures history.
- 21 Nov (team): SE3 is the only benchmark for Gate 2 and Gate 4 thresholds, and offshore wind stays out of PW03 (kept for later, as Flower said on 26 Oct).
- 26 Oct: onshore wind first, offshore kept for later (look again where offshore is about 10% of generation). SE3 is the Swedish baseline. Prices and wind data at bidding-zone level, rules at national level. Screen Italy's seven zones before detailed work.

## Still open with Flower (carried into PW03 / D13)

1. Battery: 25 MW / 100 MWh or 100 MW / 400 MWh. Solar in or out.
2. Baseload share: is 40% the right central case.
3. Imbalance cost: include or not, and which per-zone figure.
4. ES95 on annual return or on euros.
5. One-year re-strike versus multi-year cPPA.
6. Producer price for future years: last year's capture rate, a 3-year average, or Flower's view.
7. Risk limit L for the implied risk premium (spec v1, 4.5). Until Flower answers, L = 0.

## Log

- 21 Nov: spec v1 and dictionary v1 revised: thresholds scored against SE3 only (was SE3, FI, DK1, DK2, DE-LU), offshore wind removed from every indicator, G4-01 margin given a 1 EUR/MWh floor. Hand check updated and passing.
- 16 Nov: PW03-MV-00 v1 drafts: reference portfolio spec v1 (strike rule folded in, Gate 4 definitions) and metric dictionary v1 (onshore capture rate, erosion, zone rule, Gate 2 threshold proposal). New `tests/hand_check_gate4.py --selftest` asserts Fixture G (EV 0.020333, ES95 0.24, RP* 25.5 / 14.875 EUR/MWh, bisection 26.228571), the erosion check (−0.013571) and the Gate 2 threshold table.
- 8 Nov: v0.1 of strike rule and reference portfolio spec (onshore wind only, SE3 settled). All checks re-run and unchanged: zero-margin identity, +10% price case (275k / 225k / 175k EUR), capture-rate drop (−250k EUR), Fixture A strike 12.303984, 43 weekdays in the default `avg_2m` window.
- 24 Oct: strike rule v0 and reference portfolio spec v0 merged.
- 19 Oct: metric dictionary v0 with SE3 2024 hand check.
