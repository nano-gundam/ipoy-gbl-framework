# Data harmonisation rules

PW01-CD-04 · Coding & Data · draft v0.1, 12 Oct 2026 · for review by Methodology & Validation

**Purpose.** We download data for 14+ countries from several sources. This note fixes one rule for each place where sources differ, so that numbers are comparable and conversions happen in one place only. Lingyu's download code (CD-07) and Devika's acceptance tests are built on it. Changing a rule later means re-downloading, so please challenge it now.

**Principle.** Store what the source gave us, untouched, plus the minimum extra columns needed to convert it. Derived values are computed by shared functions in one module (`harmonise`), never in notebooks or scripts. Nothing is imputed, smoothed or filled silently. This is the convention the futures collector already follows.

## 1. Time step
- Day-ahead prices moved from hourly to 15-minute steps (SDAC) in October 2025, so most price series have a break in October 2025, and some other series were already 15-minute.
- **Rule:** every series is stored in its original step, with a column `mtu_minutes` (15 or 60) on each row. Conversion to hourly goes through one function, `to_hourly()`. Prices are averaged with equal weights over the hour, energy (MWh) is summed, power (MW) is averaged.
- **Why:** converting on download would destroy information that cannot be recovered, and the break date differs by source.
- **Consequence:** hourly averaging understates intra-hour spreads and negative-price time. Metrics that depend on them (BESS arbitrage, negative-price share) are computed on the native step, and the share of negative prices is reported as a share of time, not a count of hours.

## 2. Time zone
- **Rule:** all timestamps are stored in UTC (ENTSO-E delivers UTC), as timezone-aware ISO 8601. Local time is used only for display and for definitions that are local by nature.
- **Delivery day:** defined in market time (CET/CEST, Europe/Berlin) for every zone, including Finland and the Baltics, because SDAC gates and exchange products use it. Peak = Mon–Fri 08:00–20:00 CET/CEST, the exchanges' definition.
- **DST:** a delivery day has 23, 24 or 25 hours (92, 96 or 100 quarter-hours). Never assume 24 hours or 96 slots. Tests must cover the last Sunday of March and October.

## 3. Currency
- **Rule:** all analysis in EUR. Each row keeps `value_original`, `currency_original`, `fx_rate_eur` and the converted `value_eur`.
- **Rate source:** ECB euro foreign exchange reference rates, one per TARGET working day. On weekends and holidays the last published rate is carried forward. A rate is never taken from a later date.
- **Scope:** all futures in the archive are already EUR/MWh. Conversion is needed for GBP, SEK, DKK, PLN, CZK, HUF and RON sources (national ancillary-service and some spot data).

## 4. Taxes, levies and grid fees
- Wholesale prices exclude them. **Rule:** kept in a separate table per country (`levies_<country>`, with validity dates and source), and added only inside the model. Screening indicators stay pure wholesale, so countries are not ranked on policy differences that are not market signals.

## 5. Country and zone codes
- **Rule:** one lookup table (`zones.csv`) mapping ENTSO-E EIC codes to short names: bidding zones `SE3`, `DK1`, `NO2`, `DE-LU`, and ISO-2 country codes. All code uses the short names.
- **Known trap:** ENTSO-E spot uses `DE-LU`, while the futures collector (and EEX) use `DE`. The table carries both aliases, and joins go through it. Same for the Nordic system price (`NORDIC`, `zone_kind = system`).
- Unknown codes raise an error; they are never dropped.

## 6. Missing values
- **Rule:** missing is stored as empty/null, never as zero. A gap is reported by a coverage check (expected vs. received slots, using the DST-aware slot count from section 2) and is never filled silently. Any filling happens in a named, logged step and is flagged in a column.
- A completeness rule must be stated against the universe at that date, not the whole archive (the lesson from the collector's `gaps` check).

## 7. Units and column names
- EUR/MWh for prices, MW for power, MWh for energy. The unit is in every column name (`price_eur_mwh`, `capacity_mw`, `energy_mwh`).
- Provenance columns on every table: `source`, `retrieved_at_utc`, `schema_version`.

## Open points for review
1. Equal-weight hourly mean is right for prices; should volume-weighting be used for intraday series later?
2. Is CET/CEST delivery-day for Finland acceptable, or does Methodology want local EET for any metric?
3. Where do the levy tables live, and who maintains them (Market Research sources, Coding implements)?

**Done when:** Lingyu can write the download code from this note without asking how to store anything.
