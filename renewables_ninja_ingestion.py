
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv


# ============================================================
# 1. Project configuration
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

TOKEN = os.getenv("RENEWABLES_NINJA_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "RENEWABLES_NINJA_TOKEN not found in IPOY/.env"
    )

BASE_URL = "https://www.renewables.ninja/api/data"

OUTPUT_ROOT = (
    PROJECT_ROOT / "data" / "raw" / "renewables_ninja"
)

LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "renewables_ninja_ingestion_log.csv"

MAX_RETRIES = 4
REQUEST_PAUSE_SECONDS = 3.0

# One representative point per bidding zone.
ZONES = {
    "FI": {
        "lat": 61.4981,
        "lon": 23.7608,
        "location": "Tampere, Finland",
    },
    "IE_SEM": {
        "lat": 53.4239,
        "lon": -7.9407,
        "location": "Athlone, Ireland",
    },
    "LV": {
        "lat": 56.9496,
        "lon": 24.1052,
        "location": "Riga, Latvia",
    },
    "PL": {
        "lat": 51.7592,
        "lon": 19.4550,
        "location": "Lodz, Poland",
    },
    "SE_1": {
        "lat": 65.5848,
        "lon": 22.1547,
        "location": "Lulea, Sweden",
    },
    "SE_2": {
        "lat": 62.3908,
        "lon": 17.3069,
        "location": "Sundsvall, Sweden",
    },
    "SE_3": {
        "lat": 59.3293,
        "lon": 18.0686,
        "location": "Stockholm, Sweden",
    },
    "SE_4": {
        "lat": 55.6050,
        "lon": 13.0038,
        "location": "Malmo, Sweden",
    },
}


# ============================================================
# 2. Explicit missing-file list: 21 PV + 1 Wind
# ============================================================

TASKS = []

# Solar PV: 21 missing annual files
SOLAR_MISSING = {
    "FI": [2019, 2020, 2021],
    "IE_SEM": [2019, 2020, 2021, 2022, 2023],
    "LV": [2019, 2020, 2021, 2022],
    "PL": [2019],
    "SE_1": [2019, 2020],
    "SE_2": [2019, 2020],
    "SE_3": [2019, 2020],
    "SE_4": [2019, 2020],
}

for zone, years in SOLAR_MISSING.items():
    for year in years:
        TASKS.append((zone, year, "solar_generation"))

# Onshore Wind: 1 missing annual file
TASKS.append(("PL", 2019, "wind_generation"))


# ============================================================
# 3. Simulation parameters
# ============================================================

PV_PARAMS = {
    "dataset": "merra2",
    "capacity": 1,
    "system_loss": 0.1,
    "tracking": 0,
    "tilt": 35,
    "azim": 180,
    "format": "json",
    "local_time": "false",
    "interpolate": "true",
}

WIND_PARAMS = {
    "dataset": "merra2",
    "capacity": 1,
    "height": 100,
    "turbine": "Vestas V80 2000",
    "format": "json",
    "local_time": "false",
    "interpolate": "true",
}


# ============================================================
# 4. API session
# ============================================================

SESSION = requests.Session()

SESSION.headers.update({
    "Authorization": f"Token {TOKEN}"
})


# ============================================================
# 5. Logging
# ============================================================

def write_log(
    zone,
    year,
    series,
    status,
    rows=None,
    error=None,
):
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    record = {
        "run_timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "zone": zone,
        "year": year,
        "series": series,
        "status": status,
        "rows": rows,
        "error": str(error)[:500] if error else None,
    }

    pd.DataFrame([record]).to_csv(
        LOG_FILE,
        mode="a",
        header=not LOG_FILE.exists(),
        index=False,
        encoding="utf-8",
    )


# ============================================================
# 6. Download one annual simulation
# ============================================================

def download_one(zone, year, series, force=False):

    location = ZONES[zone]

    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"

    output_dir = OUTPUT_ROOT / series / zone
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{year}.parquet"
    metadata_file = output_dir / f"{year}_metadata.json"

    # Skip existing valid files
    if output_file.exists() and not force:
        try:
            existing = pd.read_parquet(output_file)

            if not existing.empty:
                print(
                    f"SKIP {zone} | {series} | {year}: "
                    "file already exists"
                )
                write_log(
                    zone, year, series,
                    "SKIPPED_EXISTING",
                    rows=len(existing),
                )
                return

        except Exception:
            print("Existing file unreadable. Redownloading.")

    # Select model and parameters
    if series == "solar_generation":
        endpoint = f"{BASE_URL}/pv"
        params = PV_PARAMS.copy()

    elif series == "wind_generation":
        endpoint = f"{BASE_URL}/wind"
        params = WIND_PARAMS.copy()

    else:
        raise ValueError(f"Unsupported series: {series}")

    params.update({
        "lat": location["lat"],
        "lon": location["lon"],
        "date_from": start_date,
        "date_to": end_date,
    })

    print(
        f"\nFETCH {zone} | {series} | {year} "
        f"| {location['location']}"
    )

    # Retry API requests
    for attempt in range(1, MAX_RETRIES + 1):

        try:
            response = SESSION.get(
                endpoint,
                params=params,
                timeout=(30,600),
            )

            if response.status_code == 429:
                wait = int(
                    response.headers.get("Retry-After", "60")
                )
                print(f"Rate limited. Waiting {wait}s.")
                time.sleep(wait)
                continue

            response.raise_for_status()

            result = response.json()

            if "data" not in result or not result["data"]:
                raise ValueError("API returned no data.")

            # Convert API data into DataFrame
            data = pd.DataFrame.from_dict(
                result["data"],
                orient="index",
            )

            # Renewables.ninja timestamps are Unix milliseconds
            data.index = pd.to_datetime(
                pd.to_numeric(data.index),
                unit="ms",
                utc=True,
            )

            data.index.name = "timestamp_utc"
            data = data.sort_index()

            # Standardise the output column name
            if "electricity" not in data.columns:
                raise ValueError(
                    f"Missing electricity column: "
                    f"{list(data.columns)}"
                )

            data = data[["electricity"]].rename(
                columns={"electricity": "electricity_kW"}
            )

            # Basic data validation
            if data.empty:
                raise ValueError("Empty DataFrame.")

            if data.index.has_duplicates:
                raise ValueError("Duplicate timestamps detected.")

            if not data.index.is_monotonic_increasing:
                raise ValueError("Timestamps are not sorted.")

            expected_rows = (
                8784 if pd.Timestamp(
                    f"{year}-01-01"
                ).is_leap_year else 8760
            )

            if len(data) != expected_rows:
                raise ValueError(
                    f"Expected {expected_rows} hourly rows, "
                    f"received {len(data)}."
                )

            if data.isna().any().any():
                raise ValueError("NaN values detected.")

            # Save Parquet atomically
            temp_file = output_file.with_suffix(
                ".tmp.parquet"
            )

            data.to_parquet(
                temp_file,
                index=True,
            )

            temp_file.replace(output_file)

            # Save full API metadata and request parameters
            metadata = {
                "source": "Renewables.ninja",
                "zone": zone,
                "year": year,
                "series": series,
                "location": location,
                "request_parameters": params,
                "api_metadata": result.get("metadata", {}),
                "rows": len(data),
                "time_resolution": "1 hour",
                "timezone": "UTC",
                "output_unit": "kW",
                "expected_rows": expected_rows,
                "license": "CC BY-NC 4.0",
                "retrieved_at_utc": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

            metadata_file.write_text(
                json.dumps(
                    metadata,
                    indent=4,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            print(
                f"SUCCESS {zone} | {year} | "
                f"{len(data)} rows"
            )
            print(f"Saved: {output_file}")

            write_log(
                zone, year, series,
                "SUCCESS",
                rows=len(data),
            )

            return

        except Exception as exc:

            print(
                f"ERROR {zone} | {year} | "
                f"Attempt {attempt}/{MAX_RETRIES}: {exc}"
            )

            if attempt == MAX_RETRIES:
                write_log(
                    zone, year, series,
                    "FAILED",
                    error=exc,
                )

            else:
                time.sleep(5 * attempt)

        finally:
            time.sleep(REQUEST_PAUSE_SECONDS)


# ============================================================
# 7. Main
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description="Renewables.ninja missing data ingestion"
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Redownload even if a valid file exists.",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("RENEWABLES.NINJA INGESTION")
    print("Solar PV missing files: 21")
    print("Onshore Wind missing files: 1")
    print(f"Total planned tasks: {len(TASKS)}")
    print(f"Output: {OUTPUT_ROOT}")
    print(f"Log: {LOG_FILE}")
    print("=" * 70)

    for zone, year, series in TASKS:
        download_one(
            zone=zone,
            year=year,
            series=series,
            force=args.force,
        )

    print("\nAll tasks processed.")
    print(f"Review log: {LOG_FILE}")


if __name__ == "__main__":
    main()
