# Progress log: Wenhao Gu (Method & Validation)

Status of my tasks from the Notion Tasks Tracker, kept next to the work itself. Notion status is set by the group leader. This file says what exists, where it is, and what is still open.

Last updated: 8 Nov 2026

## Open tasks

| Task | Notion status | Due | Output | Where it stands |
|---|---|---|---|---|
| PW02-MV-04 · Strike rule | Need review | 24 Oct (cards close 9 Nov) | `docs/methods/strike-rule-v0.md` | v0 merged 24 Oct. v0.1 (8 Nov) switches the producer price to the onshore capture rate after Flower's 26 Oct decision. Waiting for Devika's check. |
| PW02-MV-05 · Reference portfolio spec v0 | In progress | 26 Oct (cards close 9 Nov) | `docs/methods/reference-portfolio-spec-v0.md` | v0 merged 24 Oct. v0.1 (8 Nov): onshore wind only, SE3 settled. The workshop pre-read step was overtaken, since the definitions workshop moved to the 11 Dec visit. Waiting for Devika's review. |
| PW03-MV-00 · Methodology & Validation (with Devika) | Not started | 16 Nov | Spec v1, metric dictionary v1, question list | Not started. Split with Devika still to agree. |

## Done

| Task | Output |
|---|---|
| PW01-MV-03 · Screening indicator definitions | `docs/methods/metric-dictionary-v0.md`, `tests/hand_check_se3_2024.py`, `tests/fixtures/se3_2024-07-27_29_entsoe.csv` |
| PW01-MV-04 · One-page options note for Flower | Sent to Aida, 8 Oct |

## Decisions from Flower that my documents depend on

- 16 Oct: past years struck from realised day-ahead prices, future years from the curve on a stated evaluation date. No futures history.
- 26 Oct: onshore wind first, offshore kept for later (look again where offshore is about 10% of generation). SE3 is the Swedish baseline. Prices and wind data at bidding-zone level, rules at national level. Screen Italy's seven zones before detailed work.

## Still open with Flower (carried into PW03 / D13)

1. Battery: 25 MW / 100 MWh or 100 MW / 400 MWh. Solar in or out.
2. Baseload share: is 40% the right central case.
3. Imbalance cost: include or not, and which per-zone figure.
4. ES95 on annual return or on euros.
5. One-year re-strike versus multi-year cPPA.
6. Producer price for future years: last year's capture rate, a 3-year average, or Flower's view.

## Log

- 8 Nov: v0.1 of strike rule and reference portfolio spec (onshore wind only, SE3 settled). All checks re-run and unchanged: zero-margin identity, +10% price case (275k / 225k / 175k EUR), capture-rate drop (−250k EUR), Fixture A strike 12.303984, 43 weekdays in the default `avg_2m` window.
- 24 Oct: strike rule v0 and reference portfolio spec v0 merged.
- 19 Oct: metric dictionary v0 with SE3 2024 hand check.
