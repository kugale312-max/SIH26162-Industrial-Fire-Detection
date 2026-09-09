import os
import requests
import pandas as pd
from dotenv import load_dotenv

# Load NASA FIRMS API key from .env
load_dotenv()

MAP_KEY = os.getenv("FIRMS_MAP_KEY")

if not MAP_KEY:
    print("❌ FIRMS_MAP_KEY not found in .env file.")
    print("Please add:")
    print("FIRMS_MAP_KEY=YOUR_MAP_KEY")
    exit()

# ============================================================
# INDIA BOUNDING BOX
# ============================================================
# Approximate India region
WEST = 68.0
SOUTH = 6.0
EAST = 97.5
NORTH = 37.5

AREA = f"{WEST},{SOUTH},{EAST},{NORTH}"

# ============================================================
# NASA FIRMS SATELLITE SOURCES
# ============================================================
SOURCES = [
    "VIIRS_NOAA21_NRT",
    "VIIRS_NOAA20_NRT"
]

DAY_RANGE = 1

# Output folder
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

OUTPUT_FILE = os.path.join(DATA_DIR, "firms_india.csv")

# ============================================================
# FETCH FIRMS DATA
# ============================================================

all_data = []

for source in SOURCES:

    print("\n" + "=" * 60)
    print(f"Fetching India FIRMS data from: {source}")
    print("=" * 60)

    url = (
        f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{MAP_KEY}/{source}/{AREA}/{DAY_RANGE}"
    )

    try:
        response = requests.get(url, timeout=120)

        print("HTTP Status:", response.status_code)

        if response.status_code != 200:
            print(f"❌ Failed to fetch data for {source}")
            print(response.text[:500])
            continue

        # Convert CSV response into DataFrame
        from io import StringIO

        df = pd.read_csv(StringIO(response.text))

        if df.empty:
            print(f"⚠️ No hotspots found for {source}")
            continue

        # Add satellite source
        df["firms_source"] = source

        all_data.append(df)

        print(f"✅ {len(df)} hotspots found")

    except requests.exceptions.Timeout:
        print(f"⏱️ Request timed out for {source}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")

    except Exception as e:
        print(f"❌ Unexpected error: {e}")


# ============================================================
# COMBINE DATA
# ============================================================

if not all_data:

    print("\n❌ No FIRMS data received.")
    print("Possible reasons:")
    print("1. API key is invalid")
    print("2. No hotspots were detected")
    print("3. NASA FIRMS server is temporarily unavailable")

    exit()


combined_df = pd.concat(all_data, ignore_index=True)

# Remove duplicate coordinates/time observations
combined_df = combined_df.drop_duplicates()

# ============================================================
# SAVE DATA
# ============================================================

combined_df.to_csv(OUTPUT_FILE, index=False)

print("\n" + "=" * 60)
print("INDIA FIRMS DATA COLLECTION COMPLETE")
print("=" * 60)

print(f"Total hotspots: {len(combined_df)}")
print(f"Saved to: {OUTPUT_FILE}")

# ============================================================
# SUMMARY
# ============================================================

if "frp" in combined_df.columns:

    print("\nFRP Statistics:")
    print(f"Minimum FRP : {combined_df['frp'].min():.2f} MW")
    print(f"Maximum FRP : {combined_df['frp'].max():.2f} MW")
    print(f"Average FRP : {combined_df['frp'].mean():.2f} MW")

if "confidence" in combined_df.columns:

    print("\nConfidence:")
    print(combined_df["confidence"].value_counts())

if "satellite" in combined_df.columns:

    print("\nSatellite:")
    print(combined_df["satellite"].value_counts())

print("\nFirst 5 hotspots:")
print(combined_df.head())

print("\n✅ Done!")