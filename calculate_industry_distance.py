import pandas as pd
from geopy.distance import geodesic


# =========================================================
# REAL FIRMS + REAL OSM INDUSTRIAL DATA
# =========================================================

print("======================================")
print("FIRMS → OSM INDUSTRIAL PROXIMITY")
print("======================================")


# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------

firms = pd.read_csv(
    "data/firms_processed.csv"
)

industries = pd.read_csv(
    "data/industrial_locations_real.csv"
)

print(
    "FIRMS hotspots:",
    len(firms)
)

print(
    "OSM industrial features:",
    len(industries)
)


# ---------------------------------------------------------
# FIND NEAREST INDUSTRIAL FEATURE
# ---------------------------------------------------------

nearest_names = []
nearest_distances = []
near_industry_values = []


for _, hotspot in firms.iterrows():

    hotspot_location = (
        hotspot["latitude"],
        hotspot["longitude"]
    )

    minimum_distance = float("inf")

    nearest_name = "None"

    # Search every OSM industrial feature
    for _, industry in industries.iterrows():

        industry_location = (
            industry["latitude"],
            industry["longitude"]
        )

        distance = geodesic(
            hotspot_location,
            industry_location
        ).kilometers

        if distance < minimum_distance:

            minimum_distance = distance

            nearest_name = industry["name"]


    # -----------------------------------------------------
    # Store result
    # -----------------------------------------------------

    nearest_names.append(
        nearest_name
    )

    nearest_distances.append(
        round(minimum_distance, 2)
    )

    # Prototype proximity threshold
    if minimum_distance <= 2:

        near_industry_values.append(
            "Yes"
        )

    else:

        near_industry_values.append(
            "No"
        )


# ---------------------------------------------------------
# ADD RESULTS
# ---------------------------------------------------------

firms[
    "Nearest Industrial Facility"
] = nearest_names

firms[
    "Distance to Industry (km)"
] = nearest_distances

firms[
    "near_industry"
] = near_industry_values


# ---------------------------------------------------------
# DISPLAY
# ---------------------------------------------------------

print()
print("======================================")
print("PROXIMITY RESULTS")
print("======================================")


print(
    firms[
        [
            "latitude",
            "longitude",
            "frp",
            "baseline_frp",
            "frp_change_percent",
            "detections",
            "Nearest Industrial Facility",
            "Distance to Industry (km)",
            "near_industry"
        ]
    ]
)


# ---------------------------------------------------------
# SAVE
# ---------------------------------------------------------

firms.to_csv(
    "data/firms_enriched.csv",
    index=False
)


print()
print("✓ Enriched FIRMS data saved:")
print("data/firms_enriched.csv")


print()
print("======================================")
print("PROXIMITY CALCULATION COMPLETED")
print("======================================")