import os
import requests
import pandas as pd
from io import StringIO
from dotenv import load_dotenv

print("======================================")
print("NASA FIRMS DATA FETCH")
print("======================================")

# Load .env
load_dotenv()

MAP_KEY = os.getenv("FIRMS_MAP_KEY")

if not MAP_KEY:
    raise ValueError("FIRMS_MAP_KEY not found in .env")

print("✓ FIRMS MAP KEY FOUND")

# -------------------------------------------------
# STUDY AREA: PUNE REGION
# -------------------------------------------------

WEST = 73.65
SOUTH = 18.35
EAST = 74.35
NORTH = 18.85

AREA = f"{WEST},{SOUTH},{EAST},{NORTH}"

# -------------------------------------------------
# FIRMS DATA SOURCE
# -------------------------------------------------

# -------------------------------------------------
# FIRMS SATELLITE SOURCES
# -------------------------------------------------

SOURCES = [
    "VIIRS_NOAA21_NRT",
    "VIIRS_NOAA20_NRT",
    "VIIRS_SNPP_NRT"
]

DAY_RANGE = 5

all_data = []

for source in SOURCES:

    print()
    print(f"Requesting: {source}")

    url = (
        "https://firms.modaps.eosdis.nasa.gov/"
        f"api/area/csv/{MAP_KEY}/"
        f"{source}/{AREA}/{DAY_RANGE}"
    )

    try:

        response = requests.get(
            url,
            timeout=60
        )

        print("HTTP Status:", response.status_code)

        response.raise_for_status()

        source_data = pd.read_csv(
            StringIO(response.text)
        )

        print(
            f"Hotspots from {source}: "
            f"{len(source_data)}"
        )

        if len(source_data) > 0:
            all_data.append(source_data)

    except Exception as e:

        print(
            f"Error downloading {source}: {e}"
        )


# -------------------------------------------------
# COMBINE ALL SATELLITE DATA
# -------------------------------------------------

if all_data:

    data = pd.concat(
        all_data,
        ignore_index=True
    )

else:

    data = pd.DataFrame(
        columns=[
            "latitude",
            "longitude",
            "acq_date",
            "acq_time",
            "satellite",
            "confidence",
            "frp"
        ]
    )

print()
print("======================================")
print("COMBINED REAL FIRMS DATA")
print("======================================")

print("Total hotspots:", len(data))

# -------------------------------------------------
# SAVE COMBINED REAL FIRMS DATA
# -------------------------------------------------

os.makedirs("data", exist_ok=True)

output_file = "data/firms_real.csv"

data.to_csv(
    output_file,
    index=False
)

print()
print("✓ Combined real FIRMS data saved:")
print(output_file)

print()
print("First 5 real hotspots:")

if len(data) > 0:
    print(
        data[
            [
                "latitude",
                "longitude",
                "acq_date",
                "acq_time",
                "satellite",
                "confidence",
                "frp"
            ]
        ].head()
    )

    print()
    print("FRP statistics:")
    print(data["frp"].describe())

    print()
    print("Confidence distribution:")
    print(data["confidence"].value_counts())

else:
    print("No FIRMS hotspots found.")

print()
print("======================================")
print("REAL FIRMS FETCH COMPLETED")
print("======================================")