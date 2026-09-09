import os
import time
import math
import requests
import pandas as pd


# ============================================================
# INDIA INDUSTRIAL PROXIMITY ANALYSIS
# ============================================================
# Input:
#   data/firms_india_baseline.csv
#
# Output:
#   data/firms_india_enriched.csv
#
# Strategy:
#   1. Select important hotspots instead of querying OSM for all
#      438 observations.
#   2. Query OpenStreetMap Overpass around those hotspots.
#   3. Calculate nearest industrial feature and distance.
#   4. Add near_industry = Yes/No.
#
# This keeps the prototype practical and reduces Overpass load.
# ============================================================

INPUT_FILE = "data/firms_india_baseline.csv"
OUTPUT_FILE = "data/firms_india_enriched.csv"

SEARCH_RADIUS_KM = 5.0
NEAR_INDUSTRY_KM = 2.0

# Maximum number of hotspots to query in this prototype.
MAX_HOTSPOTS = 60

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0

    p1 = math.radians(lat1)
    p2 = math.radians(lat2)

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(p1)
        * math.cos(p2)
        * math.sin(dlon / 2) ** 2
    )

    return 2 * r * math.asin(math.sqrt(a))


def query_overpass(lat, lon):
    """Find industrial OSM features within 5 km."""

    radius_m = int(SEARCH_RADIUS_KM * 1000)

    query = f"""
    [out:json][timeout:45];

    (
      node(around:{radius_m},{lat},{lon})["landuse"="industrial"];
      way(around:{radius_m},{lat},{lon})["landuse"="industrial"];
      relation(around:{radius_m},{lat},{lon})["landuse"="industrial"];

      node(around:{radius_m},{lat},{lon})["industrial"];
      way(around:{radius_m},{lat},{lon})["industrial"];
      relation(around:{radius_m},{lat},{lon})["industrial"];

      node(around:{radius_m},{lat},{lon})["building"="industrial"];
      way(around:{radius_m},{lat},{lon})["building"="industrial"];
      relation(around:{radius_m},{lat},{lon})["building"="industrial"];
    );

    out center tags;
    """

    last_error = None

    for url in OVERPASS_URLS:

        try:

            response = requests.post(
                url,
                data=query,
                timeout=60
            )

            response.raise_for_status()

            return response.json().get("elements", [])

        except Exception as exc:
            last_error = exc
            continue

    print(f"    ⚠️ Overpass unavailable: {last_error}")
    return []


def element_coordinates(element):

    if element.get("type") == "node":

        return (
            element.get("lat"),
            element.get("lon")
        )

    center = element.get("center", {})

    return (
        center.get("lat"),
        center.get("lon")
    )


def main():

    print("=" * 70)
    print("INDIA OSM INDUSTRIAL PROXIMITY ANALYSIS")
    print("=" * 70)

    if not os.path.exists(INPUT_FILE):

        print(f"❌ Missing: {INPUT_FILE}")
        raise SystemExit(1)

    df = pd.read_csv(INPUT_FILE)

    print(f"Input hotspots: {len(df):,}")

    # Ensure numeric fields.
    for col in [
        "latitude",
        "longitude",
        "frp",
        "frp_change_percent",
        "historical_detections"
    ]:

        if col in df.columns:

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

    df = df.dropna(
        subset=["latitude", "longitude"]
    ).copy()

    # --------------------------------------------------------
    # Select the most relevant hotspots.
    # --------------------------------------------------------

    df["_priority"] = 0.0

    # Abnormal increase is important.
    df.loc[
        df["persistence_status"] == "Abnormal Increase",
        "_priority"
    ] += 1000

    # High FRP gets additional priority.
    df["_priority"] += (
        df["frp"].fillna(0) * 5
    )

    # New events also deserve attention.
    df.loc[
        df["persistence_status"] == "New / No Local History",
        "_priority"
    ] += 200

    selected = (
        df.sort_values(
            "_priority",
            ascending=False
        )
        .head(MAX_HOTSPOTS)
        .copy()
    )

    print(
        f"Selected {len(selected)} hotspots "
        f"for OSM analysis."
    )

    # Default values for every hotspot.
    df["Nearest Industrial Facility"] = "Not analyzed"
    df["Distance to Industry (km)"] = float("nan")
    df["near_industry"] = "Not analyzed"

    analyzed = 0
    total_features = 0

    # --------------------------------------------------------
    # Query OSM for selected hotspots.
    # --------------------------------------------------------

    for index, row in selected.iterrows():

        analyzed += 1

        lat = row["latitude"]
        lon = row["longitude"]

        print(
            f"\n[{analyzed}/{len(selected)}] "
            f"{lat:.5f}, {lon:.5f}"
        )

        elements = query_overpass(
            lat,
            lon
        )

        print(
            f"    OSM features: {len(elements)}"
        )

        if not elements:
            df.loc[
                index,
                "Nearest Industrial Facility"
            ] = "No OSM industrial feature found"

            df.loc[
                index,
                "near_industry"
            ] = "No"

            time.sleep(0.5)
            continue

        total_features += len(elements)

        nearest_name = None
        nearest_distance = float("inf")

        for element in elements:

            elat, elon = element_coordinates(
                element
            )

            if elat is None or elon is None:
                continue

            distance = haversine_km(
                lat,
                lon,
                elat,
                elon
            )

            if distance < nearest_distance:

                tags = element.get(
                    "tags",
                    {}
                )

                name = (
                    tags.get("name")
                    or tags.get("industrial")
                    or tags.get("landuse")
                    or tags.get("building")
                    or "Unnamed Industrial Feature"
                )

                nearest_distance = distance
                nearest_name = name

        if nearest_name is not None:

            df.loc[
                index,
                "Nearest Industrial Facility"
            ] = nearest_name

            df.loc[
                index,
                "Distance to Industry (km)"
            ] = nearest_distance

            df.loc[
                index,
                "near_industry"
            ] = (
                "Yes"
                if nearest_distance <= NEAR_INDUSTRY_KM
                else "No"
            )

            print(
                f"    Nearest: {nearest_name}"
            )

            print(
                f"    Distance: "
                f"{nearest_distance:.2f} km"
            )

            print(
                f"    Near industry: "
                f"{'Yes' if nearest_distance <= NEAR_INDUSTRY_KM else 'No'}"
            )

        time.sleep(1)

    df = df.drop(
        columns=["_priority"],
        errors="ignore"
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("OSM INDUSTRIAL ANALYSIS COMPLETE")
    print("=" * 70)

    print(
        f"Total India hotspots : {len(df):,}"
    )

    print(
        f"OSM hotspots analyzed: {analyzed:,}"
    )

    print(
        f"OSM features found   : {total_features:,}"
    )

    print(
        f"Saved to             : {OUTPUT_FILE}"
    )

    analyzed_df = df[
        df["near_industry"] != "Not analyzed"
    ]

    if not analyzed_df.empty:

        print("\nIndustrial proximity:")

        print(
            analyzed_df[
                "near_industry"
            ].value_counts()
        )

    print("\nSample enriched records:")

    columns = [
        "latitude",
        "longitude",
        "frp",
        "baseline_frp",
        "frp_change_percent",
        "historical_detections",
        "persistence_status",
        "Nearest Industrial Facility",
        "Distance to Industry (km)",
        "near_industry"
    ]

    columns = [
        c for c in columns
        if c in df.columns
    ]

    print(df[columns].head(10).to_string(index=False))

    print(
        "\n✅ India industrial-context dataset ready."
    )


if __name__ == "__main__":
    main()
