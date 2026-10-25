"""Forward-price input table at a stated evaluation date (PW02-CD-02).

    python -m metrics.forward_prices --archive <PowerFuturesCollector>/data/power_futures.sqlite
    python -m metrics.forward_prices --archive ... --evaluation-date 2026-10-09

Turns the power futures collector's archive into the one table the engine reads for
forward prices, following the strike rule (``docs/methods/strike-rule-v0.md``, section 2):

* Evaluation date E: the last complete trading day before the run, unless given. It is in
  the file name and in every row.
* ``avg_2m`` (the default the engine uses): mean daily settlement of one fixed delivery
  contract over trade dates in (E - 2 months, E]. Rows are grouped by the contract itself
  (``Cal-2027``), never by curve position (``front year``), which changes contract when
  the year rolls.
* ``single_day``: the settlement on E, beside every average, as the check.
* Only contracts whose delivery starts after E. A contract already in delivery is not a
  forward price.
* EEX first. Euronext only for a contract EEX does not list. Euronext publishes Nordic zones
  as an EPAD spread against the Nordic system price, so a Euronext zone price is
  system + EPAD on the same trade date.
* Euronext readings stamped before ``EURONEXT_FINAL_STAMP`` (CET, the exchange's own clock)
  still carry the previous session's settlement and are not used.
* Futures area codes become zone names through ``harmonise/zones.csv`` (``DE`` -> ``DE-LU``).
  An area with no row there (GB, CH, IT, the Nordic system price, ...) is left out and
  listed in the build report, never guessed.

Output, one row per zone x product x delivery period x method::

    zone, product, delivery_period, price_eur_mwh, evaluation_date, method,
    settlement_days_used, source,                                   <- Wenhao's columns
    settlement_days_expected, flag_thin, flag_missing_days, flag_no_volume,
    traded_volume_mwh, maturity_type, delivery_start, delivery_end,
    window_first_date, window_last_date, first_settlement_date, last_settlement_date,
    source_contract

The flags describe the contract over the two-month window and are the same on both of its
rows. ``flag_no_volume`` is empty for Euronext, which does not publish volume.

Licence: the table holds window averages and the one settlement on E. The daily settlement
history stays in the collector archive and never enters this repository (EEX terms; see
``docs/sources/power-futures-collector-operations.md``). Flower can replace this file with
its own prices: same columns, ``source = FLOWER``.
"""
from __future__ import annotations

import argparse
import datetime as dt
import logging
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from harmonise.zones import UnknownZoneError, resolve_zone

log = logging.getLogger(__name__)

SCHEMA_VERSION = "forward-prices-0.1"
WINDOW_MONTHS = 2
MATURITIES = ("Month", "Quarter", "Season", "Year")
PRODUCTS = {"Base": "base", "Peak": "peak"}
# Measured on the server snapshots, 2-23 Oct 2026: readings stamped before 15:00 CET differ
# from the day's final settlement 92-94% of the time, readings from 15:00 on match it in
# 7,257 of 7,259 cases. The strike rule says "about 17:00"; no Euronext stamp is ever later
# than 16:14, so 17:00 would drop every Euronext row.
EURONEXT_FINAL_STAMP = "15:00"
DIVERGENCE_REPORT_PCT = 10.0  # strike rule section 2: report both when they differ more

COLUMNS = [
    "zone", "product", "delivery_period", "price_eur_mwh", "evaluation_date", "method",
    "settlement_days_used", "source",
    "settlement_days_expected", "flag_thin", "flag_missing_days", "flag_no_volume",
    "traded_volume_mwh", "maturity_type", "delivery_start", "delivery_end",
    "window_first_date", "window_last_date", "first_settlement_date", "last_settlement_date",
    "source_contract",
]
METHODS = ("avg_2m", "single_day")
_KEY = ["zone", "product", "maturity_type", "delivery_period"]


class ForwardPriceError(ValueError):
    """The archive cannot give a table for the requested evaluation date."""


@dataclass
class BuildResult:
    table: pd.DataFrame
    evaluation_date: dt.date
    window_first_date: dt.date
    skipped_areas: dict[str, int] = field(default_factory=dict)
    archive_gaps: dict[str, list[str]] = field(default_factory=dict)
    euronext_stale_dropped: int = 0
    archive_span: dict[str, tuple[str, str]] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# dates
# --------------------------------------------------------------------------- #
def window_bounds(evaluation_date: dt.date, months: int = WINDOW_MONTHS) -> tuple[dt.date, dt.date]:
    """First and last trade date (both inclusive) of the window (E - months, E]."""
    e = pd.Timestamp(evaluation_date)
    first = (e - pd.DateOffset(months=months) + pd.Timedelta(days=1)).date()
    return first, e.date()


def weekdays(first: dt.date, last: dt.date) -> list[dt.date]:
    return [d.date() for d in pd.bdate_range(first, last)]


def default_evaluation_date(archive: Path, today: dt.date | None = None) -> dt.date:
    """Last complete trading day before ``today``: the latest EEX trade date before today.

    Warns when the archive stops short of the last weekday before today, which means the
    collector has not caught up and the table would be older than it needs to be.
    """
    today = today or dt.datetime.now(ZoneInfo("Europe/Berlin")).date()  # exchange clock
    with _connect(archive) as conn:
        row = conn.execute(
            "SELECT max(trade_date) FROM observations WHERE source = 'EEX' AND trade_date < ?",
            (today.isoformat(),),
        ).fetchone()
    if not row or not row[0]:
        raise ForwardPriceError(f"no EEX settlements before {today} in {archive}")
    latest = dt.date.fromisoformat(row[0])
    expected = (pd.Timestamp(today) - pd.offsets.BDay(1)).date()
    if latest < expected:
        log.warning("archive's latest EEX day is %s but the last weekday before %s is %s; "
                    "run the collector (or fetch the server database) first", latest, today, expected)
    return latest


# --------------------------------------------------------------------------- #
# reading the archive
# --------------------------------------------------------------------------- #
def _connect(path: Path) -> sqlite3.Connection:
    path = Path(path)
    if not path.is_file():
        raise ForwardPriceError(f"archive not found: {path}")
    return sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)


def read_window(archive: Path, first: dt.date, last: dt.date) -> pd.DataFrame:
    """Settled fixed-delivery observations with trade dates in [first, last]."""
    sql = f"""
        SELECT source, trade_date, contract_code, bidding_zone, zone_kind, product,
               maturity_type, delivery_label, delivery_start, delivery_end,
               settlement_price, volume_mwh, source_timestamp
        FROM observations
        WHERE trade_date BETWEEN ? AND ?
          AND maturity_type IN ({",".join("?" * len(MATURITIES))})
          AND product IN ({",".join("?" * len(PRODUCTS))})
          AND settlement_price IS NOT NULL
    """
    params = [first.isoformat(), last.isoformat(), *MATURITIES, *PRODUCTS]
    with _connect(archive) as conn:
        obs = pd.read_sql_query(sql, conn, params=params)
        days = pd.read_sql_query(
            "SELECT source, trade_date FROM observations WHERE trade_date BETWEEN ? AND ? "
            "GROUP BY source, trade_date", conn, params=params[:2])
        span = conn.execute(
            "SELECT source, min(trade_date), max(trade_date) FROM observations GROUP BY source"
        ).fetchall()
    obs.attrs["days_by_source"] = days.groupby("source")["trade_date"].apply(set).to_dict()
    obs.attrs["span"] = {s: (a, b) for s, a, b in span}
    return obs


# --------------------------------------------------------------------------- #
# building daily zone prices
# --------------------------------------------------------------------------- #
def _euronext_zone_prices(eu: pd.DataFrame) -> pd.DataFrame:
    """Euronext zone price per day = Nordic system settlement + the zone's EPAD spread."""
    system = eu[eu["zone_kind"] == "system"]
    epad = eu[eu["zone_kind"] == "epad"]
    on = ["trade_date", "product", "maturity_type", "delivery_label"]
    merged = epad.merge(
        system[on + ["settlement_price", "contract_code"]],
        on=on, suffixes=("", "_system"), how="inner",
    )
    merged["settlement_price"] = merged["settlement_price"] + merged["settlement_price_system"]
    merged["contract_code"] = merged["contract_code_system"] + "+" + merged["contract_code"]
    merged["volume_mwh"] = float("nan")  # Euronext publishes no volume
    return merged.drop(columns=["settlement_price_system", "contract_code_system"])


def daily_zone_prices(obs: pd.DataFrame, euronext_final_stamp: str = EURONEXT_FINAL_STAMP
                      ) -> tuple[pd.DataFrame, dict[str, int], int]:
    """One settlement per zone, product, contract and trade date, with its source.

    Returns the daily frame, the futures areas left out (no zones.csv row) with their
    observation counts, and the number of stale Euronext readings dropped.
    """
    eex = obs[(obs["source"] == "EEX") & (obs["zone_kind"] == "zonal")]
    eu = obs[obs["source"] == "EURONEXT"]
    stamp_time = eu["source_timestamp"].fillna("").str[11:16]
    final = (stamp_time >= euronext_final_stamp) & (stamp_time != "")
    stale = int((~final).sum())
    eu = _euronext_zone_prices(eu[final])

    daily = pd.concat([eex, eu], ignore_index=True)
    skipped: dict[str, int] = {}
    zone_of: dict[str, str | None] = {}
    for area in daily["bidding_zone"].unique():
        try:
            zone_of[area] = resolve_zone(area)
        except UnknownZoneError:
            zone_of[area] = None
    daily["zone"] = daily["bidding_zone"].map(zone_of)
    for area, n in daily.loc[daily["zone"].isna(), "bidding_zone"].value_counts().items():
        skipped[area] = int(n)
    # The Nordic system price is not a zone, but it is used above for the Euronext zones.
    daily = daily[daily["zone"].notna()].copy()

    daily["product"] = daily["product"].map(PRODUCTS)
    daily = daily.rename(columns={"delivery_label": "delivery_period"})

    # EEX first: Euronext only for a contract EEX does not list in the window.
    eex_keys = set(map(tuple, daily.loc[daily["source"] == "EEX", _KEY].itertuples(index=False)))
    is_eu = daily["source"] == "EURONEXT"
    covered = pd.Series([tuple(k) in eex_keys for k in daily[_KEY].itertuples(index=False)],
                        index=daily.index)
    daily = daily[~(is_eu & covered)]

    dupes = daily.duplicated(_KEY + ["trade_date"], keep=False)
    if dupes.any():
        sample = daily.loc[dupes, _KEY + ["trade_date", "source"]].head(4).to_dict("records")
        raise ForwardPriceError(f"two settlements for one contract and day, e.g. {sample}")
    return daily, skipped, stale


# --------------------------------------------------------------------------- #
# the table
# --------------------------------------------------------------------------- #
def build(archive: Path, evaluation_date: dt.date | None = None, *,
          euronext_final_stamp: str = EURONEXT_FINAL_STAMP, today: dt.date | None = None
          ) -> BuildResult:
    """Build the forward-price table for one evaluation date from the collector archive."""
    e = evaluation_date or default_evaluation_date(archive, today)
    if e.weekday() >= 5:
        raise ForwardPriceError(f"evaluation date {e} is a weekend day, not a trading day")
    first, last = window_bounds(e)
    obs = read_window(archive, first, last)
    days_by_source = obs.attrs["days_by_source"]
    if e.isoformat() not in days_by_source.get("EEX", set()):
        raise ForwardPriceError(f"the archive holds no EEX settlements on the evaluation date {e}")

    daily, skipped, stale = daily_zone_prices(obs, euronext_final_stamp)
    daily = daily[daily["delivery_start"] > e.isoformat()]
    if daily.empty:
        raise ForwardPriceError(f"no forward contracts found for {e}")

    expected = len(weekdays(first, last))
    g = daily.groupby(_KEY, sort=True)
    contracts = g.agg(
        price_avg=("settlement_price", "mean"),
        settlement_days_used=("trade_date", "nunique"),
        traded_volume_mwh=("volume_mwh", lambda v: v.sum(min_count=1)),
        source=("source", "first"),
        source_contract=("contract_code", "first"),
        delivery_start=("delivery_start", "first"),
        delivery_end=("delivery_end", "first"),
        first_settlement_date=("trade_date", "min"),
        last_settlement_date=("trade_date", "max"),
    ).reset_index()
    on_e = daily[daily["trade_date"] == e.isoformat()].set_index(_KEY)["settlement_price"]
    contracts["price_single"] = contracts.set_index(_KEY).index.map(on_e)

    contracts["settlement_days_expected"] = expected
    contracts["flag_missing_days"] = contracts["settlement_days_used"] < expected
    no_vol = contracts["traded_volume_mwh"].fillna(0) <= 0
    contracts["flag_no_volume"] = pd.array(
        [None if src == "EURONEXT" else bool(nv) for src, nv in zip(contracts["source"], no_vol)],
        dtype="boolean")
    contracts["flag_thin"] = contracts["flag_missing_days"] | contracts["flag_no_volume"].fillna(False)
    contracts.loc[contracts["source"] == "EURONEXT", "traded_volume_mwh"] = float("nan")

    common = {"evaluation_date": e.isoformat()}
    avg = contracts.assign(
        price_eur_mwh=contracts["price_avg"], method="avg_2m",
        window_first_date=first.isoformat(), window_last_date=last.isoformat(), **common)
    single = contracts[contracts["price_single"].notna()].assign(
        price_eur_mwh=lambda x: x["price_single"], method="single_day", settlement_days_used=1,
        settlement_days_expected=1, window_first_date=e.isoformat(),
        window_last_date=e.isoformat(), **common)
    table = pd.concat([avg, single], ignore_index=True)[COLUMNS]
    table["price_eur_mwh"] = table["price_eur_mwh"].round(4)
    table["traded_volume_mwh"] = table["traded_volume_mwh"].round(1)
    table["method"] = pd.Categorical(table["method"], categories=METHODS)
    table = table.sort_values(["zone", "product", "maturity_type", "delivery_start", "method"],
                              ignore_index=True)
    table["method"] = table["method"].astype(str)

    gaps = {src: sorted(d.isoformat() for d in weekdays(first, last)
                        if d.isoformat() not in days_by_source.get(src, set()))
            for src in ("EEX", "EURONEXT")}
    return BuildResult(table=table, evaluation_date=e, window_first_date=first,
                       skipped_areas=skipped, archive_gaps=gaps,
                       euronext_stale_dropped=stale, archive_span=obs.attrs["span"])


def divergence(table: pd.DataFrame) -> pd.DataFrame:
    """avg_2m against single_day per contract, largest relative difference first."""
    wide = table.pivot_table(index=_KEY, columns="method", values="price_eur_mwh",
                             observed=True).dropna()
    wide["diff_eur_mwh"] = wide["single_day"] - wide["avg_2m"]
    wide["diff_pct"] = 100 * wide["diff_eur_mwh"] / wide["avg_2m"].abs()
    return wide.reindex(wide["diff_pct"].abs().sort_values(ascending=False).index).reset_index()


# --------------------------------------------------------------------------- #
# reading and writing
# --------------------------------------------------------------------------- #
def output_path(out_dir: Path, evaluation_date: dt.date) -> Path:
    return Path(out_dir) / f"forward_prices_{evaluation_date.isoformat()}.csv"


def read_forward_prices(path: Path) -> pd.DataFrame:
    """Read a forward-price table (ours or Flower's) and check it can be used as is.

    Enforces the reporting rule: one table, one evaluation date.
    """
    t = pd.read_csv(path, dtype={"zone": str, "delivery_period": str, "evaluation_date": str})
    missing = [c for c in COLUMNS[:8] if c not in t.columns]
    if missing:
        raise ForwardPriceError(f"{path}: missing columns {missing}")
    dates = t["evaluation_date"].unique()
    if len(dates) != 1:
        raise ForwardPriceError(f"{path}: mixes evaluation dates {sorted(dates)}")
    bad = set(t["method"]) - set(METHODS)
    if bad:
        raise ForwardPriceError(f"{path}: unknown method(s) {sorted(bad)}")
    if t.duplicated(["zone", "product", "delivery_period", "method"]).any():
        raise ForwardPriceError(f"{path}: duplicate zone/product/delivery_period/method rows")
    return t


def write_report(result: BuildResult, path: Path, csv_name: str, archive: Path) -> None:
    t, e = result.table, result.evaluation_date
    avg = t[t["method"] == "avg_2m"]
    div = divergence(t)
    big = div[div["diff_pct"].abs() > DIVERGENCE_REPORT_PCT]
    cal = div[div["maturity_type"] == "Year"]

    def md(df: pd.DataFrame) -> str:
        if df.empty:
            return "_none_"
        cell = lambda v: f"{v:.2f}" if isinstance(v, float) else ("" if v is None or v is pd.NA else str(v))
        rows = [" | ".join(df.columns), " | ".join("---" for _ in df.columns)]
        rows += [" | ".join(cell(v) for v in r) for r in df.itertuples(index=False)]
        return "\n".join(f"| {r} |" for r in rows)

    zones = (avg.groupby("zone")
             .agg(contracts=("delivery_period", "size"),
                  cal_years=("delivery_period", lambda s: ", ".join(
                      p for p in sorted(set(s)) if p.startswith("Cal-"))),
                  thin=("flag_thin", "sum"), source=("source", lambda s: "/".join(sorted(set(s)))))
             .reset_index())
    lines = [
        f"# Forward-price table, evaluation date {e}",
        "",
        (f"File: `{csv_name}` · built {dt.datetime.now(dt.UTC):%Y-%m-%d %H:%M} UTC "
         f"from `{Path(archive).name}` · {SCHEMA_VERSION}"),
        "",
        f"Window for `avg_2m`: trade dates {result.window_first_date} to {e} "
        f"({len(weekdays(result.window_first_date, e))} weekdays). "
        f"Archive span: " + "; ".join(f"{s} {a} to {b}" for s, (a, b) in sorted(result.archive_span.items())) + ".",
        "",
        (f"{len(avg)} contracts in {avg['zone'].nunique()} zones, "
         f"{int(avg['flag_thin'].sum())} flagged thin "
         f"({int(avg['flag_missing_days'].sum())} with missing days, "
         f"{int(avg['flag_no_volume'].fillna(False).sum())} with no traded volume). "
         f"{len(t) - len(avg)} single-day check rows."),
        "",
        "## Zones",
        "",
        md(zones),
        "",
        "## Futures areas left out (no row in harmonise/zones.csv)",
        "",
        ", ".join(f"{a} ({n} obs.)" for a, n in sorted(result.skipped_areas.items())) or "_none_",
        "",
        "## Archive days missing in the window (weekdays with no rows at all)",
        "",
        *[f"- {s}: {len(d)} — {', '.join(d) if d else 'none'}" for s, d in result.archive_gaps.items()],
        "",
        (f"Euronext readings dropped as stale (stamped before {EURONEXT_FINAL_STAMP} CET): "
         f"{result.euronext_stale_dropped}."),
        "",
        (f"## Single day against two-month average: {len(big)} of {len(div)} contracts "
         f"differ by more than {DIVERGENCE_REPORT_PCT:.0f}%"),
        "",
        "Largest differences, Cal contracts:",
        "",
        md(cal.head(15)),
        "",
        "Largest differences, all contracts:",
        "",
        md(div.head(15)),
        "",
        "## Thin Cal contracts",
        "",
        md(avg[(avg["maturity_type"] == "Year") & avg["flag_thin"]][
            ["zone", "product", "delivery_period", "settlement_days_used",
             "settlement_days_expected", "traded_volume_mwh", "source"]]),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--archive", required=True, type=Path,
                   help="the collector's power_futures.sqlite")
    p.add_argument("--evaluation-date", type=dt.date.fromisoformat,
                   help="ISO date; default the last complete trading day in the archive")
    p.add_argument("--out-dir", type=Path, default=Path("data/processed/forward_prices"))
    p.add_argument("--euronext-final-stamp", default=EURONEXT_FINAL_STAMP)
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    result = build(args.archive, args.evaluation_date,
                   euronext_final_stamp=args.euronext_final_stamp)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out = output_path(args.out_dir, result.evaluation_date)
    result.table.to_csv(out, index=False, lineterminator="\n")
    report = out.with_name(out.stem + "_report.md")
    write_report(result, report, out.name, args.archive)
    avg = result.table[result.table["method"] == "avg_2m"]
    log.info("wrote %s: %d contracts, %d zones, %d thin; report %s",
             out, len(avg), avg["zone"].nunique(), int(avg["flag_thin"].sum()), report.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
