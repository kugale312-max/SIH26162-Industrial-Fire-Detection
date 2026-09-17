import os
import sys
import requests
import pandas as pd
from io import StringIO
from dotenv import load_dotenv

# Ensure safe console output for unicode characters across platforms
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ============================================================
# HELPER FUNCTIONS FOR SECURITY & PRESERVATION
# ============================================================

def mask_key(text: str, key: str) -> str:
    """Mask sensitive API key from logs, URLs, and error messages."""
    if not key or not text:
        return str(text)
    return str(text).replace(key, "***REDACTED***")


EXPECTED_COLUMNS = [
    "latitude", "longitude", "bright_ti4", "scan", "track",
    "acq_date", "acq_time", "satellite", "instrument", "confidence",
    "version", "bright_ti5", "frp", "daynight", "firms_source"
]


def preserve_existing_data(file_path: str) -> pd.DataFrame:
    """
    Preserves existing CSV format and valid data if live fetching fails.
    If the file exists and has valid rows, it is retained intact.
    If it doesn't exist, an empty template with the standard schema is created.
    """
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        try:
            prev_df = pd.read_csv(file_path)
            if not prev_df.empty and "latitude" in prev_df.columns:
                print(f"📁 Preserved existing valid data: {file_path} ({len(prev_df)} records)")
                return prev_df
        except Exception as e:
            print(f"⚠️ Could not read existing data from {file_path}: {e}")

    # Fallback: create empty template with standard schema to protect downstream pipelines
    empty_df = pd.DataFrame(columns=EXPECTED_COLUMNS)
    empty_df.to_csv(file_path, index=False)
    print(f"📄 Initialized empty CSV schema at {file_path} with standard columns.")
    return empty_df


def validate_firms_map_key(map_key: str, timeout: int = 15) -> tuple:
    """
    Validates the NASA FIRMS MAP_KEY before requesting data.
    Queries the official NASA FIRMS mapkey status endpoint.
    Never prints or leaks the API key.
    Returns (is_valid: bool, message: str).
    """
    if not map_key or len(map_key) < 10:
        return False, "MAP_KEY is missing or too short."

    validation_url = f"https://firms.modaps.eosdis.nasa.gov/mapserver/mapkey_status/?MAP_KEY={map_key}"
    try:
        resp = requests.get(validation_url, timeout=timeout)
        safe_body = mask_key(resp.text[:300].strip(), map_key)

        if resp.status_code == 200:
            try:
                info = resp.json()
                limit = info.get("transaction_limit", "unknown")
                current = info.get("current_transactions", "unknown")
                interval = info.get("transaction_interval", "unknown")
                return True, f"Key valid. Transactions: {current}/{limit} per {interval}."
            except Exception:
                return True, f"Key valid (HTTP 200)."
        elif resp.status_code in (401, 403):
            return False, f"MAP_KEY is invalid or transaction limit reached (HTTP {resp.status_code}): {safe_body}"
        else:
            return False, f"Validation returned HTTP {resp.status_code}: {safe_body}"
    except requests.exceptions.RequestException as e:
        return False, f"Key validation connection error: {mask_key(str(e), map_key)}"


def print_summary(df: pd.DataFrame):
    """Prints statistics and sample of hotspots data."""
    if df.empty:
        return

    if "frp" in df.columns:
        frp_numeric = pd.to_numeric(df["frp"], errors="coerce").dropna()
        if not frp_numeric.empty:
            print("\nFRP Statistics:")
            print(f"Minimum FRP : {frp_numeric.min():.2f} MW")
            print(f"Maximum FRP : {frp_numeric.max():.2f} MW")
            print(f"Average FRP : {frp_numeric.mean():.2f} MW")

    if "confidence" in df.columns:
        print("\nConfidence:")
        print(df["confidence"].value_counts())

    if "satellite" in df.columns:
        print("\nSatellite:")
        print(df["satellite"].value_counts())

    print("\nFirst 5 hotspots:")
    print(df.head())


# ============================================================
# 1. LOAD FIRMS_MAP_KEY SECURELY FROM .env
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(DATA_DIR, "firms_india.csv")

MAP_KEY = os.getenv("FIRMS_MAP_KEY", "").strip()

if not MAP_KEY:
    print("❌ FIRMS_MAP_KEY not found in .env file.")
    print("Please add FIRMS_MAP_KEY=YOUR_KEY to .env.")
    preserve_existing_data(OUTPUT_FILE)
    sys.exit(1)

# ============================================================
# 2. VALIDATE API KEY BEFORE REQUESTING DATA
# ============================================================
print("============================================================")
print("Validating NASA FIRMS MAP_KEY...")
print("============================================================")
is_valid, val_msg = validate_firms_map_key(MAP_KEY)
if not is_valid:
    print(f"❌ Key validation failed: {val_msg}")
    preserve_existing_data(OUTPUT_FILE)
    sys.exit(1)
print(f"✅ {val_msg}")

# ============================================================
# 3. INDIA BOUNDING BOX (Replaces invalid 'IND' country code)
# ============================================================
# The FIRMS /api/area/csv/ endpoint requires [west,south,east,north]
# coordinates. Passing country codes like 'IND' causes:
# "Invalid area. Expects: [west,south,east,north]".
WEST = 68.0
SOUTH = 6.0
EAST = 97.5
NORTH = 37.5

AREA = f"{WEST},{SOUTH},{EAST},{NORTH}"

# ============================================================
# 4. SATELLITE SOURCES & CONFIGURATION
# ============================================================
SOURCES = [
    "VIIRS_NOAA21_NRT",
    "VIIRS_NOAA20_NRT",
    "VIIRS_SNPP_NRT"
]

DAY_RANGE = int(os.getenv("FIRMS_DAY_RANGE", "3"))


# ============================================================
# 5. FETCH DATA WITH SAFE DEBUGGING
# ============================================================

def fetch_source_data(source: str, map_key: str, area: str, day_range: int, timeout: int = 120) -> pd.DataFrame:
    """
    Fetches FIRMS CSV data for a specific source and bounding box.
    Logs HTTP status and response errors safely without revealing the key.
    """
    url = (
        f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{map_key}/{source}/{area}/{day_range}"
    )
    masked_url = mask_key(url, map_key)

    print(f"\nRequesting: {source} (Day range: {day_range})")
    print(f"URL: {masked_url}")

    try:
        response = requests.get(url, timeout=timeout)
        print("HTTP Status:", response.status_code)

        if response.status_code != 200:
            safe_err = mask_key(response.text[:300].strip(), map_key)
            print(f"❌ Failed to fetch data for {source} (HTTP {response.status_code}): {safe_err}")
            return pd.DataFrame()

        text = response.text.strip()

        # Check for API error messages that might be returned with HTTP 200
        if text.startswith("Invalid") or "error" in text.lower()[:60]:
            safe_err = mask_key(text[:300], map_key)
            print(f"❌ FIRMS API error for {source}: {safe_err}")
            return pd.DataFrame()

        df = pd.read_csv(StringIO(text))

        if df.empty:
            print(f"⚠️ No hotspots found for {source}")
            return pd.DataFrame()

        # Add satellite source column
        df["firms_source"] = source
        print(f"✅ {len(df)} hotspots found for {source}")
        return df

    except requests.exceptions.Timeout:
        print(f"⏱️ Request timed out for {source} after {timeout}s")
        return pd.DataFrame()

    except requests.exceptions.RequestException as e:
        print(f"❌ Request error for {source}: {mask_key(str(e), map_key)}")
        return pd.DataFrame()

    except Exception as e:
        print(f"❌ Unexpected error for {source}: {mask_key(str(e), map_key)}")
        return pd.DataFrame()


# ============================================================
# 6. RUN FETCH PIPELINE
# ============================================================
all_data = []

print("\n" + "=" * 60)
print(f"Fetching India FIRMS data (BBox: {AREA}, Day Range: {DAY_RANGE})")
print("=" * 60)

for source in SOURCES:
    df = fetch_source_data(source, MAP_KEY, AREA, DAY_RANGE)
    if not df.empty:
        all_data.append(df)

# If day range returned no hotspots, attempt day range 3 or fallback to preserved data
if not all_data and DAY_RANGE < 3:
    print("\n" + "-" * 60)
    print("⚠️ No hotspots detected for requested Day Range. Attempting Day Range 3...")
    print("-" * 60)
    for source in SOURCES:
        df = fetch_source_data(source, MAP_KEY, AREA, 3)
        if not df.empty:
            all_data.append(df)

# ============================================================
# 7. MERGE, BOUNDARY FILTER, AND SAVE DATA
# ============================================================

if not all_data:
    print("\n" + "=" * 60)
    print("⚠️ No new FIRMS data received from active satellite passes.")
    print("Preserving existing dataset...")
    print("=" * 60)
    preserved_df = preserve_existing_data(OUTPUT_FILE)
    if not preserved_df.empty:
        print(f"✅ Preserved {len(preserved_df)} hotspots in {OUTPUT_FILE}.")
        print_summary(preserved_df)
        sys.exit(0)
    else:
        print("❌ No existing data available to preserve.")
        sys.exit(1)

new_df = pd.concat(all_data, ignore_index=True)
print(f"\nNewly fetched FIRMS records across all sensors: {len(new_df):,}")

# Merge with existing active data within rolling active window to prevent single-pass wiping
from datetime import datetime, timezone, timedelta
now_utc = datetime.now(timezone.utc)
active_window_days = max(DAY_RANGE, 3)
cutoff_date = (now_utc - timedelta(days=active_window_days)).strftime("%Y-%m-%d")

if os.path.exists(OUTPUT_FILE) and os.path.getsize(OUTPUT_FILE) > 0:
    try:
        existing_df = pd.read_csv(OUTPUT_FILE)
        if not existing_df.empty and "latitude" in existing_df.columns and "acq_date" in existing_df.columns:
            valid_existing = existing_df[existing_df["acq_date"].astype(str) >= cutoff_date].copy()
            print(f"Retaining {len(valid_existing):,} active hotspots from rolling window (>= {cutoff_date}).")
            combined_df = pd.concat([new_df, valid_existing], ignore_index=True)
        else:
            combined_df = new_df
    except Exception as e:
        print(f"Notice during rolling merge: {e}")
        combined_df = new_df
else:
    combined_df = new_df

# Deduplicate coordinates and acquisition date
dedup_cols = ["latitude", "longitude", "acq_date"]
if all(c in combined_df.columns for c in dedup_cols):
    combined_df["_lat_round"] = pd.to_numeric(combined_df["latitude"], errors="coerce").round(4)
    combined_df["_lon_round"] = pd.to_numeric(combined_df["longitude"], errors="coerce").round(4)
    before_dedup = len(combined_df)
    combined_df = combined_df.drop_duplicates(subset=["_lat_round", "_lon_round", "acq_date"]).drop(columns=["_lat_round", "_lon_round"])
    print(f"Deduplicated detections: {before_dedup:,} -> {len(combined_df):,}")
else:
    combined_df = combined_df.drop_duplicates()

# ============================================================
# POINT-IN-POLYGON INDIA BOUNDARY FILTERING
# ============================================================
BOUNDARY_FILE = os.path.join(DATA_DIR, "india_boundary.geojson")
if os.path.exists(BOUNDARY_FILE):
    try:
        import geopandas as gpd
        print("\n" + "=" * 60)
        print("Applying GeoPandas point-in-polygon boundary filtering...")
        print("=" * 60)
        gdf_boundary = gpd.read_file(BOUNDARY_FILE)
        boundary_geom = gdf_boundary.union_all() if hasattr(gdf_boundary, "union_all") else gdf_boundary.unary_union

        combined_df["latitude"] = pd.to_numeric(combined_df["latitude"], errors="coerce")
        combined_df["longitude"] = pd.to_numeric(combined_df["longitude"], errors="coerce")
        combined_df = combined_df.dropna(subset=["latitude", "longitude"]).copy().reset_index(drop=True)

        gdf_points = gpd.GeoDataFrame(
            combined_df,
            geometry=gpd.points_from_xy(combined_df["longitude"], combined_df["latitude"]),
            crs="EPSG:4326"
        )
        mask = gdf_points.intersects(boundary_geom)
        removed_count = int((~mask).sum())
        combined_df = combined_df[mask.values].copy()

        if "geometry" in combined_df.columns:
            combined_df = combined_df.drop(columns=["geometry"])

        print(f"✅ Filtered using {BOUNDARY_FILE}")
        print(f"  Points inside India   : {len(combined_df):,}")
        print(f"  Points outside India  : {removed_count:,} (removed)")
    except Exception as e:
        print(f"⚠️ Boundary filtering warning: {e}")

# Sort by date descending and FRP descending
if "acq_date" in combined_df.columns and "frp" in combined_df.columns:
    combined_df["frp"] = pd.to_numeric(combined_df["frp"], errors="coerce")
    combined_df = combined_df.sort_values(by=["acq_date", "frp"], ascending=[False, False])
combined_df = combined_df.reset_index(drop=True)

# Save updated data
combined_df.to_csv(OUTPUT_FILE, index=False)

print("\n" + "=" * 60)
print("INDIA FIRMS DATA COLLECTION COMPLETE")
print("=" * 60)

print(f"Total active India hotspots : {len(combined_df):,}")
print(f"Saved to                    : {OUTPUT_FILE}")

if "acq_date" in combined_df.columns:
    print("\nDate Distribution:")
    print(combined_df["acq_date"].value_counts().to_string())

ne_count = len(combined_df[(combined_df["longitude"] >= 88.0) & (combined_df["latitude"] >= 21.5)])
print(f"\nNortheast India hotspots    : {ne_count:,}")

# ============================================================
# 8. SUMMARY
# ============================================================
print_summary(combined_df)
print("\n✅ Done!")
