import os
from io import StringIO
from datetime import datetime, timedelta

import pandas as pd
import requests
from dotenv import load_dotenv


# ============================================================
# CORRECT INDIA HISTORICAL FIRMS COLLECTION
# ============================================================
# IMPORTANT:
# The FIRMS Area API returns the most recent N days when DATE is
# omitted. For historical windows, DATE must be supplied.
#
# This script therefore requests separate dated 5-day windows.
# ============================================================

load_dotenv()

MAP_KEY = os.getenv("FIRMS_MAP_KEY")

if not MAP_KEY:
    print("❌ FIRMS_MAP_KEY not found in .env")
    raise SystemExit(1)

AREA = "68.0,6.0,97.5,37.5"

SOURCES = [
    "VIIRS_NOAA21_NRT",
    "VIIRS_NOAA20_NRT",
]

HISTORY_DAYS = 30
CHUNK_DAYS = 5

OUTPUT_FILE = "data/firms_india_historical.csv"


def fetch_window(source, start_date, days):
    """
    FIRMS historical Area API:
    /area/csv/MAP_KEY/SOURCE/AREA/DAY_RANGE/DATE
    """

    url = (
        "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{MAP_KEY}/{source}/{AREA}/{days}/"
        f"{start_date.strftime('%Y-%m-%d')}"
    )

    response = requests.get(
        url,
        timeout=180
    )

    response.raise_for_status()

    if not response.text.strip():
        return pd.DataFrame()

    return pd.read_csv(
        StringIO(response.text)
    )


def main():

    print("=" * 70)
    print("CORRECTED INDIA HISTORICAL NASA FIRMS COLLECTION")
    print("=" * 70)

    today = datetime.utcnow().date()

    # Start date is 29 days before today so the total period is
    # approximately 30 calendar days including today.
    first_date = today - timedelta(
        days=HISTORY_DAYS - 1
    )

    print(
        f"Requested date range: "
        f"{first_date} → {today}"
    )

    all_data = []

    for source in SOURCES:

        print("\n" + "-" * 70)
        print(f"Source: {source}")

        current_start = first_date

        while current_start <= today:

            remaining = (
                today - current_start
            ).days + 1

            days = min(
                CHUNK_DAYS,
                remaining
            )

            print(
                f"Requesting "
                f"{current_start} → "
                f"{current_start + timedelta(days=days-1)}"
            )

            try:

                df = fetch_window(
                    source,
                    current_start,
                    days
                )

                if df.empty:

                    print(
                        "  ⚠️ No records returned"
                    )

                else:

                    df["firms_source"] = source

                    all_data.append(df)

                    print(
                        f"  ✅ {len(df)} records"
                    )

            except requests.exceptions.Timeout:

                print(
                    "  ⏱️ Timeout - continuing"
                )

            except requests.exceptions.RequestException as exc:

                print(
                    f"  ❌ Request failed: {exc}"
                )

            except Exception as exc:

                print(
                    f"  ❌ Unexpected error: {exc}"
                )

            current_start += timedelta(
                days=days
            )


    if not all_data:

        print(
            "\n❌ No historical FIRMS data collected."
        )

        raise SystemExit(1)


    historical = pd.concat(
        all_data,
        ignore_index=True
    )

    historical = historical.drop_duplicates()


    # Clean numeric fields.
    for column in [
        "latitude",
        "longitude",
        "frp"
    ]:

        if column in historical.columns:

            historical[column] = pd.to_numeric(
                historical[column],
                errors="coerce"
            )


    historical = historical.dropna(
        subset=[
            "latitude",
            "longitude"
        ]
    )


    if "acq_date" in historical.columns:

        historical["acq_date"] = pd.to_datetime(
            historical["acq_date"],
            errors="coerce"
        )

        historical = historical.sort_values(
            "acq_date"
        )


    historical.to_csv(
        OUTPUT_FILE,
        index=False
    )


    print("\n" + "=" * 70)
    print("CORRECTED HISTORICAL COLLECTION COMPLETE")
    print("=" * 70)

    print(
        f"Total records : {len(historical):,}"
    )

    print(
        f"Saved to      : {OUTPUT_FILE}"
    )


    if "acq_date" in historical.columns:

        dates = historical[
            "acq_date"
        ].dropna()

        if not dates.empty:

            print(
                f"Actual date range: "
                f"{dates.min().date()} → "
                f"{dates.max().date()}"
            )


    if "frp" in historical.columns:

        print("\nFRP statistics:")

        print(
            f"Minimum FRP : "
            f"{historical['frp'].min():.2f} MW"
        )

        print(
            f"Maximum FRP : "
            f"{historical['frp'].max():.2f} MW"
        )

        print(
            f"Average FRP : "
            f"{historical['frp'].mean():.2f} MW"
        )


    print(
        "\n✅ Correct historical dataset ready."
    )


if __name__ == "__main__":
    main()
