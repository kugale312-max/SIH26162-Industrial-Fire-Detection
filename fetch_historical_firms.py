import pandas as pd
from geopy.distance import geodesic


# =========================================================
# LOAD REAL FIRMS DATA
# =========================================================

current = pd.read_csv(
    "data/firms_real.csv"
)

historical = pd.read_csv(
    "data/firms_historical.csv"
)

print("======================================")
print("REAL FIRMS BASELINE CALCULATION")
print("======================================")

print(
    "Current hotspots:",
    len(current)
)

print(
    "Historical hotspots:",
    len(historical)
)


# =========================================================
# CALCULATE BASELINE FOR EACH CURRENT HOTSPOT
# =========================================================

baseline_values = []
detection_counts = []


for _, current_row in current.iterrows():

    current_location = (
        current_row["latitude"],
        current_row["longitude"]
    )

    nearby_frp = []

    for _, historical_row in historical.iterrows():

        historical_location = (
            historical_row["latitude"],
            historical_row["longitude"]
        )

        distance = geodesic(
            current_location,
            historical_location
        ).kilometers

        # Historical hotspot within 2 km
        if distance <= 2:

            nearby_frp.append(
                historical_row["frp"]
            )

    # -----------------------------------------------------
    # Calculate baseline
    # -----------------------------------------------------

    if nearby_frp:

        baseline = sum(nearby_frp) / len(nearby_frp)

        detections = len(nearby_frp)

    else:

        baseline = float("nan")

        detections = 0

    baseline_values.append(
        baseline
    )

    detection_counts.append(
        detections
    )


# =========================================================
# ADD RESULTS
# =========================================================

current["baseline_frp"] = baseline_values

current["detections"] = detection_counts


# =========================================================
# FRP CHANGE %
# =========================================================

def calculate_frp_change(row):

    if pd.notna(row["baseline_frp"]) and row["baseline_frp"] > 0:

        return (
            (
                row["frp"]
                - row["baseline_frp"]
            )
            / row["baseline_frp"]
        ) * 100

    else:

        return float("nan")

current["frp_change_percent"] = current.apply(
    calculate_frp_change,
    axis=1
)


# =========================================================
# DISPLAY RESULTS
# =========================================================

print()
print("======================================")
print("BASELINE RESULTS")
print("======================================")

print(
    current[
        [
            "latitude",
            "longitude",
            "frp",
            "baseline_frp",
            "frp_change_percent",
            "detections"
        ]
    ]
)


# =========================================================
# SAVE
# =========================================================

current.to_csv(
    "data/firms_processed.csv",
    index=False
)

print()
print("✓ Processed FIRMS data saved:")
print("data/firms_processed.csv")

print()
print("======================================")
print("BASELINE CALCULATION COMPLETED")
print("======================================")