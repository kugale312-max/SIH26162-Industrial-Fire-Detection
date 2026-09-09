import os
import time
import requests
import pandas as pd
from geopy.distance import geodesic

# ============================================================
# INDIA INDUSTRIAL CONTEXT ANALYSIS
# ============================================================

INPUT_FILE = "data/firms_india_baseline.csv"
OUTPUT_FILE = "data/firms_india_enriched.csv"

MAX_HOTSPOTS = 10
RADIUS_KM = 2
REQUEST_DELAY = 2

OVERPASS_URL = "https://overpass.kumi.systems/api/interpreter"

print("=" * 70)
print("INDIA FIRMS + OSM INDUSTRIAL CONTEXT ANALYSIS")
print("=" * 70)

# ------------------------------------------------------------
# Load baseline data
# ------------------------------------------------------------

df = pd.read_csv(INPUT_FILE)

print(f"Input hotspots : {len(df)}")

# ------------------------------------------------------------
# Select priority hotspots
# ------------------------------------------------------------

# Prioritize abnormal increase
priority = df[
    df["persistence_status"] == "Abnormal Increase"
].copy()

# Sort strongest anomalies first
priority = priority.sort_values(
    by="frp_change_percent",
    ascending=False
)

# Take top N
priority = priority.head(MAX_HOTSPOTS).copy()

print(f"Priority hotspots selected : {len(priority)}")

# ------------------------------------------------------------
# Overpass query
# ------------------------------------------------------------

def query_osm(lat, lon):

    query = f"""
    [out:json][timeout:60];
    (
      way(around:{RADIUS_KM * 1000},{lat},{lon})["landuse"="industrial"];
      way(around:{RADIUS_KM * 1000},{lat},{lon})["industrial"];
      way(around:{RADIUS_KM * 1000},{lat},{lon})["building"="industrial"];
      relation(around:{RADIUS_KM * 1000},{lat},{lon})["landuse"="industrial"];
      relation(around:{RADIUS_KM * 1000},{lat},{lon})["industrial"];
    );
    out center tags;
    """

    headers = {
        "User-Agent": "SIH26162-Industrial-Fire-Detection/1.0"
    }

    try:
        response = requests.post(
            OVERPASS_URL,
            data={"data": query},
            headers=headers,
            timeout=30
        )

        print(f"   HTTP status: {response.status_code}")

        if response.status_code == 429:
            print("   ⚠️ Rate limited")
            return []

        response.raise_for_status()

        return response.json().get("elements", [])

    except Exception as e:
        print(f"   ⚠️ OSM request failed: {e}")
        return []

# ------------------------------------------------------------
# Calculate distance
# ------------------------------------------------------------

def get_element_coordinates(element):

    if "center" in element:

        return (
            element["center"]["lat"],
            element["center"]["lon"]
        )

    return None


def nearest_industry(lat, lon, elements):

    if not elements:
        return None, None, None

    hotspot = (lat, lon)

    nearest_distance = None
    nearest_lat = None
    nearest_lon = None

    for element in elements:

        coords = get_element_coordinates(element)

        if coords is None:
            continue

        distance = geodesic(
            hotspot,
            coords
        ).km

        if nearest_distance is None or distance < nearest_distance:

            nearest_distance = distance
            nearest_lat = coords[0]
            nearest_lon = coords[1]

    return nearest_distance, nearest_lat, nearest_lon


# ------------------------------------------------------------
# Analyze hotspots
# ------------------------------------------------------------

results = []

for index, row in priority.iterrows():

    lat = row["latitude"]
    lon = row["longitude"]

    print()
    print(
        f"Hotspot {len(results)+1}/{len(priority)}"
    )

    print(
        f"Location: {lat:.5f}, {lon:.5f}"
    )

    print(
        f"FRP: {row['frp']:.2f} MW"
    )

    print(
        f"FRP change: {row['frp_change_percent']:.2f}%"
    )

    elements = query_osm(lat, lon)

    print(
        f"   OSM industrial features: {len(elements)}"
    )

    distance, industry_lat, industry_lon = nearest_industry(
        lat,
        lon,
        elements
    )

    if distance is not None:

        print(
            f"   Nearest industry: {distance:.2f} km"
        )

        near_industry = (
            "Yes" if distance <= 2 else "No"
        )

    else:

        print("   No industrial feature found")

        distance = None
        industry_lat = None
        industry_lon = None
        near_industry = "Unknown"

    results.append({

        "latitude": lat,
        "longitude": lon,

        "frp": row["frp"],

        "baseline_frp": row["baseline_frp"],

        "frp_change_percent":
            row["frp_change_percent"],

        "historical_detections":
            row["historical_detections"],

        "persistence_status":
            row["persistence_status"],

        "industry_distance_km":
            distance,

        "near_industry":
            near_industry,

        "industry_latitude":
            industry_lat,

        "industry_longitude":
            industry_lon,

        "osm_features":
            len(elements)
    })

    # Prevent Overpass rate limiting
    time.sleep(REQUEST_DELAY)


# ------------------------------------------------------------
# Save
# ------------------------------------------------------------

result_df = pd.DataFrame(results)

result_df.to_csv(
    OUTPUT_FILE,
    index=False
)

print()
print("=" * 70)
print("INDUSTRIAL CONTEXT ANALYSIS COMPLETE")
print("=" * 70)

print(
    f"Analyzed hotspots : {len(result_df)}"
)

print(
    f"Saved to           : {OUTPUT_FILE}"
)

print()
print("Industrial proximity:")

if len(result_df) > 0:

    print(
        result_df["near_industry"]
        .value_counts()
    )

print()
print("Sample results:")

print(
    result_df[
        [
            "latitude",
            "longitude",
            "frp",
            "frp_change_percent",
            "industry_distance_km",
            "near_industry"
        ]
    ].head(10)
)

print()
print("✅ OSM industrial context dataset ready.")