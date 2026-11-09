"""
Unified ENTSO-E ingestion script for IPOY.

Optional:
    python scripts/entsoe_ingestion_unified.py --only-timeseries
    python scripts/entsoe_ingestion_unified.py --only-capacity
    python scripts/entsoe_ingestion_unified.py --force-timeseries

The script uses the same ENTSOE_API_TOKEN from the project-root .env.
Raw outputs remain in separate folders and are not harmonised together.
"""

from __future__ import annotations

import argparse
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from entsoe import EntsoePandasClient
from entsoe.mappings import Area
from tqdm import tqdm


# ============================================================
# 1. PROJECT PATHS, API CLIENT AND SHARED CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)

TOKEN = os.getenv("ENTSOE_API_TOKEN")
if not TOKEN:
    raise RuntimeError(
        f"ENTSOE_API_TOKEN not found. Check: {ENV_FILE}"
    )

CLIENT = EntsoePandasClient(api_key=TOKEN)

YEARS = list(range(2019, 2026))

# Historical time-series bidding zones.
ZONES = {
    "SE_1": {"country": "SE", "timezone": "Europe/Stockholm"},
    "SE_2": {"country": "SE", "timezone": "Europe/Stockholm"},
    "SE_3": {"country": "SE", "timezone": "Europe/Stockholm"},
    "SE_4": {"country": "SE", "timezone": "Europe/Stockholm"},
    "FI": {"country": "FI", "timezone": "Europe/Helsinki"},
    "DK_1": {"country": "DK", "timezone": "Europe/Copenhagen"},
    "DK_2": {"country": "DK", "timezone": "Europe/Copenhagen"},
    "DE_LU": {"country": "DE_LU", "timezone": "Europe/Berlin"},
    "BE": {"country": "BE", "timezone": "Europe/Brussels"},
    "NL": {"country": "NL", "timezone": "Europe/Amsterdam"},
    "FR": {"country": "FR", "timezone": "Europe/Paris"},
    "AT": {"country": "AT", "timezone": "Europe/Vienna"},
    "PL": {"country": "PL", "timezone": "Europe/Warsaw"},
    "ES": {"country": "ES", "timezone": "Europe/Madrid"},
    "PT": {"country": "PT", "timezone": "Europe/Lisbon"},
    "IE_SEM": {"country": "IE", "timezone": "Europe/Dublin"},
    "CZ": {"country": "CZ", "timezone": "Europe/Prague"},
    "HU": {"country": "HU", "timezone": "Europe/Budapest"},
    "EE": {"country": "EE", "timezone": "Europe/Tallinn"},
    "LV": {"country": "LV", "timezone": "Europe/Riga"},
    "LT": {"country": "LT", "timezone": "Europe/Vilnius"},
}

TIMESERIES = [
    "day_ahead_prices",
    "wind_generation",
    "solar_generation",
    "total_load",
]

REQUEST_PAUSE_SECONDS = 1.0
MAX_RETRIES = 3
RETRY_BASE_SECONDS = 2.0

TIMESERIES_OUTPUT_ROOT = PROJECT_ROOT / "data" / "raw" / "entsoe"
TIMESERIES_LOG_DIR = PROJECT_ROOT / "logs"
TIMESERIES_LOG_FILE = TIMESERIES_LOG_DIR / "entsoe_ingestion_log.csv"


# ============================================================
# 2. ENTSO-E TIME-SERIES FETCHERS
# ============================================================

def fetch_day_ahead_prices(zone, country, start, end):
    return CLIENT.query_day_ahead_prices(
        country_code=zone, start=start, end=end
    )


def fetch_wind_generation(zone, country, start, end):
    return CLIENT.query_generation(
        country_code=zone, start=start, end=end, psr_type="B19"
    )


def fetch_solar_generation(zone, country, start, end):
    return CLIENT.query_generation(
        country_code=zone, start=start, end=end, psr_type="B16"
    )


def fetch_total_load(zone, country, start, end):
    return CLIENT.query_load(
        country_code=zone, start=start, end=end
    )


FETCHERS = {
    "day_ahead_prices": fetch_day_ahead_prices,
    "wind_generation": fetch_wind_generation,
    "solar_generation": fetch_solar_generation,
    "total_load": fetch_total_load,
}


# ============================================================
# 3. ENTSO-E TIME-SERIES LOGGING AND FILE HANDLING
# ============================================================

def write_timeseries_log(
    zone, series, year, status, rows=None, error=None, attempt=None
):
    TIMESERIES_LOG_DIR.mkdir(parents=True, exist_ok=True)

    record = {
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "zone": zone,
        "series": series,
        "year": year,
        "start_utc": f"{year}-01-01T00:00:00+00:00",
        "end_utc_exclusive": f"{year + 1}-01-01T00:00:00+00:00",
        "rows": rows,
        "status": status,
        "attempt": attempt,
        "error": str(error)[:500] if error else None,
    }

    pd.DataFrame([record]).to_csv(
        TIMESERIES_LOG_FILE,
        mode="a",
        header=not TIMESERIES_LOG_FILE.exists(),
        index=False,
        encoding="utf-8",
    )


def normalise_timeseries_result(data, start, end):
    """Convert timezone-aware API timestamps to UTC; do not resample."""
    if data is None or data.empty:
        return None

    if isinstance(data, pd.Series):
        data = data.to_frame(name=data.name or "value")
    else:
        data = data.copy()

    if not isinstance(data.index, pd.DatetimeIndex):
        raise TypeError(
            "Expected DatetimeIndex from ENTSO-E; received "
            f"{type(data.index).__name__}."
        )

    if data.index.tz is None:
        raise ValueError(
            "API returned timezone-naive timestamps; refusing to guess timezone."
        )

    data.index = data.index.tz_convert("UTC")
    data.index.name = "timestamp_utc"
    data = data.loc[(data.index >= start) & (data.index < end)]
    data = data.sort_index()

    # Preserve original sampling interval and observations.
    return data if not data.empty else None


def save_timeseries_parquet(data, zone, series, year):
    output_path = (
        TIMESERIES_OUTPUT_ROOT / series / zone / f"{year}.parquet"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = output_path.with_suffix(".tmp.parquet")
    data.to_parquet(temp_path, index=True)
    temp_path.replace(output_path)
    return output_path


def existing_timeseries_file_is_valid(path):
    if not path.exists():
        return False
    try:
        existing = pd.read_parquet(path)
        return not existing.empty
    except Exception:
        return False


# ============================================================
# 4. DOWNLOAD ONE ENTSO-E TIME-SERIES FILE
# ============================================================

def download_timeseries_one(zone, year, series, force=False):
    country = ZONES[zone]["country"]

    start = pd.Timestamp(f"{year}-01-01", tz="UTC")
    end = pd.Timestamp(f"{year + 1}-01-01", tz="UTC")

    output_path = (
        TIMESERIES_OUTPUT_ROOT / series / zone / f"{year}.parquet"
    )

    if not force and existing_timeseries_file_is_valid(output_path):
        existing = pd.read_parquet(output_path)
        print(f"SKIP {zone} | {series} | {year}: valid file exists")
        write_timeseries_log(
            zone, series, year, "SKIPPED_EXISTING", rows=len(existing)
        )
        return

    fetch = FETCHERS[series]

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(
                f"FETCH {zone} | {series} | {year} "
                f"(attempt {attempt}/{MAX_RETRIES})"
            )

            result = fetch(zone, country, start, end)
            result = normalise_timeseries_result(result, start, end)

            if result is None:
                write_timeseries_log(
                    zone, series, year, "NO_DATA",
                    rows=0, attempt=attempt
                )
                print(f"NO DATA {zone} | {series} | {year}")
                return

            saved_path = save_timeseries_parquet(
                result, zone, series, year
            )
            print(
                f"OK {zone} | {series} | {year} | {len(result)} rows "
                f"| {saved_path.relative_to(PROJECT_ROOT)}"
            )
            write_timeseries_log(
                zone, series, year, "SUCCESS",
                rows=len(result), attempt=attempt
            )
            return

        except Exception as exc:
            error_name = type(exc).__name__

            if error_name == "NoMatchingDataError":
                write_timeseries_log(
                    zone, series, year, "NO_MATCHING_DATA",
                    error=exc, attempt=attempt
                )
                print(f"NO MATCHING DATA {zone} | {series} | {year}: {exc}")
                return

            if attempt == MAX_RETRIES:
                write_timeseries_log(
                    zone, series, year, "FAILED",
                    error=exc, attempt=attempt
                )
                print(
                    f"FAILED {zone} | {series} | {year}: "
                    f"{error_name}: {exc}"
                )
            else:
                wait_seconds = RETRY_BASE_SECONDS ** attempt
                print(
                    f"RETRY {zone} | {series} | {year}: "
                    f"{error_name}; waiting {wait_seconds}s"
                )
                time.sleep(wait_seconds)

        finally:
            time.sleep(REQUEST_PAUSE_SECONDS)


def run_timeseries_download(args):
    total = len(args.zones) * len(args.years) * len(args.series)

    print("\n" + "=" * 72)
    print("ENTSO-E HISTORICAL TIME-SERIES INGESTION")
    print("Zones:", ", ".join(args.zones))
    print("Years:", ", ".join(map(str, sorted(args.years))))
    print("Series:", ", ".join(args.series))
    print("Planned combinations:", total)
    print("Output:", TIMESERIES_OUTPUT_ROOT)
    print("Log:", TIMESERIES_LOG_FILE)
    print("=" * 72)

    for zone in args.zones:
        for year in sorted(args.years):
            for series in args.series:
                download_timeseries_one(
                    zone, year, series, force=args.force_timeseries
                )


# ============================================================
# 5. INSTALLED CAPACITY CONFIGURATION (ENTSO-E 14.1.A)
# ============================================================

CAPACITY_OUTPUT_DIR = (
    PROJECT_ROOT / "data" / "raw" / "entsoe_capacity"
)
CAPACITY_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CAPACITY_OUTPUT_CSV = CAPACITY_OUTPUT_DIR / "capacity_raw.csv"
CAPACITY_LOG_CSV = CAPACITY_OUTPUT_DIR / "download_log.csv"

CAPACITY_START_YEAR = 2019
CAPACITY_END_YEAR = 2025
CAPACITY_RETRY_TIMES = 3
CAPACITY_RETRY_DELAY = 5
CAPACITY_REQUEST_DELAY = 1

TARGET_COUNTRIES = [
    "AT", "BE", "CZ", "DE_LU", "DK", "EE",
    "ES", "FI", "FR", "HU", "IE", "LT",
    "LV", "NL", "NO", "PL", "PT", "SE",
]

CAPACITY_LOG_COLUMNS = [
    "country", "eic_code", "year", "status", "records", "message"
]
CAPACITY_DATA_COLUMNS = [
    "country", "eic_code", "year", "timestamp", "technology",
    "capacity_value", "unit", "source"
]


def build_capacity_areas():
    missing = [
        code for code in TARGET_COUNTRIES
        if code not in Area.__members__
    ]
    if missing:
        raise ValueError(
            "Target areas missing from entsoe-py Area mapping: "
            f"{missing}. Capacity download was not started."
        )
    return {code: Area[code].value for code in TARGET_COUNTRIES}


def download_capacity_one(area_code, eic_code, year):
    start = pd.Timestamp(
        f"{year}-01-01 00:00:00", tz="Europe/Brussels"
    )
    end = pd.Timestamp(
        f"{year + 1}-01-01 00:00:00", tz="Europe/Brussels"
    )

    last_error = None

    for attempt in range(1, CAPACITY_RETRY_TIMES + 1):
        try:
            # The entsoe-py client accepts the area code as country_code.
            df = CLIENT.query_installed_generation_capacity(
                country_code=area_code,
                start=start,
                end=end,
            )

            if df is None or df.empty:
                return None, "NO_DATA"

            result = (
                df.rename_axis("timestamp")
                  .reset_index()
                  .melt(
                      id_vars=["timestamp"],
                      var_name="technology",
                      value_name="capacity_value",
                  )
            )

            result["country"] = area_code
            result["year"] = year
            result["eic_code"] = eic_code
            result["unit"] = "MW"
            result["source"] = "ENTSO-E 14.1.A"
            result = result[CAPACITY_DATA_COLUMNS]

            result["capacity_value"] = pd.to_numeric(
                result["capacity_value"], errors="coerce"
            )
            result = result.dropna(subset=["capacity_value"])

            if result.empty:
                return None, "NO_DATA"

            return result, "SUCCESS"

        except Exception as exc:
            last_error = str(exc)
            print(
                f"Capacity retry {attempt}/{CAPACITY_RETRY_TIMES} | "
                f"{area_code} | {year} | {last_error}"
            )
            if attempt < CAPACITY_RETRY_TIMES:
                time.sleep(CAPACITY_RETRY_DELAY * attempt)

    return None, f"ERROR: {last_error}"


def run_capacity_download():
    target_areas = build_capacity_areas()

    if CAPACITY_OUTPUT_CSV.exists():
        all_data = pd.read_csv(CAPACITY_OUTPUT_CSV)
        if not all_data.empty:
            all_data["year"] = pd.to_numeric(
                all_data["year"], errors="coerce"
            ).astype("Int64")
            all_data = all_data[
                all_data["country"].isin(TARGET_COUNTRIES)
                & all_data["year"].between(
                    CAPACITY_START_YEAR, CAPACITY_END_YEAR
                )
            ].copy()
    else:
        all_data = pd.DataFrame(columns=CAPACITY_DATA_COLUMNS)

    if CAPACITY_LOG_CSV.exists():
        logs = pd.read_csv(CAPACITY_LOG_CSV)
        if not logs.empty and "country" in logs.columns:
            logs = logs[
                logs["country"].isin(TARGET_COUNTRIES)
                & pd.to_numeric(logs["year"], errors="coerce").between(
                    CAPACITY_START_YEAR, CAPACITY_END_YEAR
                )
            ].copy()
    else:
        logs = pd.DataFrame(columns=CAPACITY_LOG_COLUMNS)

    completed = set()
    if not logs.empty:
        latest_status = logs.drop_duplicates(
            subset=["country", "year"], keep="last"
        )
        completed = {
            (row.country, int(row.year))
            for row in latest_status.itertuples()
            if row.status in ("SUCCESS", "NO_DATA")
            and pd.notna(row.year)
        }

    tasks = [
        (country, eic_code, year)
        for country, eic_code in target_areas.items()
        for year in range(CAPACITY_START_YEAR, CAPACITY_END_YEAR + 1)
        if (country, year) not in completed
    ]

    print("\n" + "=" * 72)
    print("ENTSO-E INSTALLED CAPACITY INGESTION (14.1.A)")
    print("Target areas:", len(target_areas))
    print("Target codes:", ", ".join(target_areas))
    print(
        f"Years: {CAPACITY_START_YEAR}-{CAPACITY_END_YEAR}"
    )
    print("Maximum combinations:", len(target_areas) * 7)
    print("Already completed:", len(completed))
    print("Tasks remaining:", len(tasks))
    print("Output:", CAPACITY_OUTPUT_CSV)
    print("Log:", CAPACITY_LOG_CSV)
    print("=" * 72)

    for area_code, eic_code, year in tqdm(
        tasks, desc="Downloading installed capacity"
    ):
        data, status = download_capacity_one(
            area_code, eic_code, year
        )

        records = 0
        if data is not None:
            records = len(data)
            all_data = pd.concat(
                [all_data, data], ignore_index=True
            )
            all_data = all_data.drop_duplicates(
                subset=[
                    "country", "year", "timestamp", "technology"
                ],
                keep="last",
            )
            all_data.to_csv(CAPACITY_OUTPUT_CSV, index=False)

        log_row = {
            "country": area_code,
            "eic_code": eic_code,
            "year": year,
            "status": status,
            "records": records,
            "message": status,
        }
        logs = pd.concat(
            [logs, pd.DataFrame([log_row])],
            ignore_index=True,
        )
        logs.to_csv(CAPACITY_LOG_CSV, index=False)
        time.sleep(CAPACITY_REQUEST_DELAY)

    print("\nCapacity download summary:")
    if not all_data.empty:
        print("Records:", len(all_data))
        print("Areas:", all_data["country"].nunique())
        print(
            "Years:",
            sorted(all_data["year"].dropna().astype(int).unique()),
        )
        print("Technologies:", all_data["technology"].nunique())
    else:
        print("No capacity records are currently available.")


# ============================================================
# 6. COMMAND-LINE INTERFACE
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Unified ENTSO-E time-series and capacity ingestion."
    )
    parser.add_argument(
        "--only-timeseries",
        action="store_true",
        help="Run only prices, wind, solar and total-load downloads.",
    )
    parser.add_argument(
        "--only-capacity",
        action="store_true",
        help="Run only installed generation capacity downloads.",
    )
    parser.add_argument(
        "--zones",
        nargs="+",
        choices=list(ZONES),
        default=list(ZONES),
        help="Bidding zones for time-series downloads.",
    )
    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        default=YEARS,
        help="Years for time-series downloads (2019-2025).",
    )
    parser.add_argument(
        "--series",
        nargs="+",
        choices=TIMESERIES,
        default=TIMESERIES,
        help="Time-series types to download.",
    )
    parser.add_argument(
        "--force-timeseries",
        action="store_true",
        help="Redownload time-series files even if valid files exist.",
    )

    args = parser.parse_args()

    if args.only_timeseries and args.only_capacity:
        parser.error(
            "Choose either --only-timeseries or --only-capacity, not both."
        )

    invalid_years = [year for year in args.years if year not in YEARS]
    if invalid_years:
        parser.error(
            f"Years must be between 2019 and 2025: {invalid_years}"
        )

    if not args.only_capacity:
        run_timeseries_download(args)

    if not args.only_timeseries:
        run_capacity_download()

    print("\nUnified ENTSO-E ingestion process finished.")


if __name__ == "__main__":
    main()
