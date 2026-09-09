import pandas as pd
from geopy.distance import geodesic


# =========================================================
# CREATE AI TRAINING DATASET
# =========================================================

print("======================================")
print("AI TRAINING DATASET CREATION")
print("======================================")


# ---------------------------------------------------------
# LOAD REAL DATA
# ---------------------------------------------------------

historical = pd.read_csv(
    "data/firms_historical.csv"
)

industries = pd.read_csv(
    "data/industrial_locations_real.csv"
)

print("Historical FIRMS records:", len(historical))
print("OSM industrial features:", len(industries))


# ---------------------------------------------------------
# FIND NEAREST INDUSTRIAL FEATURE
# ---------------------------------------------------------

nearest_distances = []
near_industry_values = []


for _, hotspot in historical.iterrows():

    hotspot_location = (
        hotspot["latitude"],
        hotspot["longitude"]
    )

    minimum_distance = float("inf")

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

    nearest_distances.append(
        round(minimum_distance, 2)
    )

    if minimum_distance <= 2:
        near_industry_values.append("Yes")
    else:
        near_industry_values.append("No")


historical["Distance_to_Industry_km"] = nearest_distances

historical["near_industry"] = near_industry_values


# =========================================================
# CALCULATE PERSISTENCE
# =========================================================

historical["acq_date"] = pd.to_datetime(
    historical["acq_date"]
)

historical["detections"] = 0


# Count nearby historical observations
# within 2 km of each hotspot

for i, hotspot in historical.iterrows():

    hotspot_location = (
        hotspot["latitude"],
        hotspot["longitude"]
    )

    count = 0

    for j, other in historical.iterrows():

        if i == j:
            continue

        other_location = (
            other["latitude"],
            other["longitude"]
        )

        distance = geodesic(
            hotspot_location,
            other_location
        ).kilometers

        if distance <= 2:
            count += 1

    historical.loc[
        i,
        "detections"
    ] = count


# =========================================================
# CALCULATE LOCAL BASELINE FRP
# =========================================================

baseline_values = []


for i, hotspot in historical.iterrows():

    hotspot_location = (
        hotspot["latitude"],
        hotspot["longitude"]
    )

    nearby_frp = []

    for j, other in historical.iterrows():

        if i == j:
            continue

        other_location = (
            other["latitude"],
            other["longitude"]
        )

        distance = geodesic(
            hotspot_location,
            other_location
        ).kilometers

        if distance <= 2:

            nearby_frp.append(
                other["frp"]
            )

    if nearby_frp:

        baseline = sum(
            nearby_frp
        ) / len(nearby_frp)

    else:

        baseline = hotspot["frp"]

    baseline_values.append(
        baseline
    )


historical["baseline_frp"] = baseline_values


# =========================================================
# FRP CHANGE
# =========================================================

historical["frp_change_percent"] = (

    (
        historical["frp"]
        - historical["baseline_frp"]
    )
    /
    historical["baseline_frp"]

) * 100


# =========================================================
# PROTOTYPE LABEL GENERATION
# =========================================================

def generate_label(row):

    frp_change = row["frp_change_percent"]

    # Abnormally high FRP near industry
    if (
        frp_change >= 50
        and row["near_industry"] == "Yes"
    ):
        return "Industrial Fire"

    # Repeated thermal activity
    elif (
        row["detections"] >= 2
        and abs(frp_change) < 50
    ):
        return "Normal Persistent Source"

    # Everything else
    else:
        return "Other Thermal Event"


historical["classification"] = historical.apply(
    generate_label,
    axis=1
)


# =========================================================
# PREPARE AI FEATURES
# =========================================================

historical["confidence_score"] = (
    historical["confidence"]
    .map({
        "l": 30,
        "n": 70,
        "h": 95
    })
    .fillna(70)
)


historical["near_industry_numeric"] = (
    historical["near_industry"]
    .map({
        "Yes": 1,
        "No": 0
    })
)


# =========================================================
# SAVE TRAINING DATASET
# =========================================================

training_columns = [
    "latitude",
    "longitude",
    "frp",
    "baseline_frp",
    "frp_change_percent",
    "confidence_score",
    "Distance_to_Industry_km",
    "near_industry_numeric",
    "detections",
    "classification"
]


training_data = historical[
    training_columns
]


training_data.to_csv(
    "data/ai_training_data.csv",
    index=False
)


# =========================================================
# DISPLAY RESULTS
# =========================================================

print()
print("======================================")
print("TRAINING DATASET CREATED")
print("======================================")

print(
    training_data.to_string(
        index=False
    )
)

print()
print("======================================")
print("CLASS DISTRIBUTION")
print("======================================")

print(
    training_data[
        "classification"
    ].value_counts()
)

print()
print("✓ Saved:")
print("data/ai_training_data.csv")

print()
print("======================================")
print("COMPLETED")
print("======================================")