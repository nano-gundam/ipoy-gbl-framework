"""Download the monthly KYOS Capture Rate Index for one or more market areas.

The numbers come from the endpoint behind the charts on
https://power.kyos.com/capture-rates. It is not a documented API, so the
response format may change without notice.

Output (long format, one row per zone, technology and month):

    data/raw/kyos/<country>/<zone>_kyos_monthly.csv
        zone, technology, month, capture_rate_pct, capture_price_eur_mwh

    <country> is the first two letters of the KYOS code (SE3 -> SE, ITNO -> IT).
    KYOS codes differ from ENTSO-E names: DE is the DE-LU zone, and the Italian
    zones are ITNO, ITCN, ITCS, ITSU, ITCA, ITSI, ITSA.

See docs/sources/kyos-capture-rate-index.md for the method and code mapping.

Usage:
    python ingest/kyos.py                      # all 16 areas below
    python ingest/kyos.py --zones SE3 DE NL    # a subset
"""

import argparse
import time
from pathlib import Path
from urllib.parse import unquote

import pandas as pd
import requests

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "data" / "raw" / "kyos"

BASE_URL = "https://power.kyos.com"
PAGE_URL = f"{BASE_URL}/capture-rates"
DATA_URL = f"{BASE_URL}/api/chart-data"

TECHNOLOGIES = ["solar", "onshore", "offshore"]
# value sent as `unit` -> column name in the output
UNITS = {1: "capture_rate_pct", 2: "capture_price_eur_mwh"}
MONTHLY_RESOLUTION = 4
PAUSE_SECONDS = 1  # be gentle, this is someone else's website

# KYOS codes for the 13 screen zones, plus SE1, SE2 and SE4.
DEFAULT_ZONES = ["SE1", "SE2", "SE3", "SE4", "DE", "NL", "ES", "PL", "LT",
                 "ITNO", "ITCN", "ITCS", "ITSU", "ITCA", "ITSI", "ITSA"]


def open_session():
    """Load the page once to obtain the session cookie and CSRF token."""
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0"
    session.get(PAGE_URL, timeout=30).raise_for_status()
    session.headers.update({
        "X-XSRF-TOKEN": unquote(session.cookies["XSRF-TOKEN"]),
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json",
        "Referer": PAGE_URL,
    })
    return session


def fetch_monthly(session, zone, technology, unit):
    """Return a Series indexed by month start for one zone, technology and unit."""
    body = {
        "node": {"node": zone, "name": zone, "country": zone},
        "technology": technology,
        "unit": unit,
        "month": 1,
        "resolution": MONTHLY_RESOLUTION,
    }
    response = session.post(DATA_URL, json=body, timeout=30)
    response.raise_for_status()
    payload = response.json()

    # One series per year ("ES-2021"), each holding twelve monthly values.
    values = {}
    for series in payload["data"]:
        year = int(series["name"].rsplit("-", 1)[1])
        for month, value in enumerate(series["data"], start=1):
            if value is not None:
                values[pd.Timestamp(year=year, month=month, day=1)] = value
    return pd.Series(values, name=UNITS[unit], dtype=float).sort_index()


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--zones", nargs="+", default=DEFAULT_ZONES,
                        help="KYOS market area codes (default: the 16 areas in DEFAULT_ZONES)")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR,
                        help="output folder (default: data/raw/kyos)")
    args = parser.parse_args()

    session = open_session()
    for zone in args.zones:
        frames = []
        for technology in TECHNOLOGIES:
            columns = []
            for unit in UNITS:
                columns.append(fetch_monthly(session, zone, technology, unit))
                time.sleep(PAUSE_SECONDS)
            df = pd.concat(columns, axis=1).dropna(how="all")
            if df.empty:
                print(f"{zone} {technology}: no data on KYOS", flush=True)
                continue
            df.index.name = "month"
            df = df.reset_index()
            df.insert(0, "technology", technology)
            df.insert(0, "zone", zone)
            frames.append(df)
            print(f"{zone} {technology}: {len(df)} months, "
                  f"{df['month'].min():%Y-%m} -> {df['month'].max():%Y-%m}", flush=True)
        if frames:
            path = args.out_dir / zone[:2] / f"{zone}_kyos_monthly.csv"
            path.parent.mkdir(parents=True, exist_ok=True)
            pd.concat(frames).to_csv(path, index=False, date_format="%Y-%m")
            print(f"saved {path}", flush=True)


if __name__ == "__main__":
    main()
