import os
import sys
import pandas as pd
import numpy as np

# Ensure safe console output for unicode characters across platforms
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ============================================================
# INDIA AI TRAINING DATASET
# ============================================================

BASELINE_FILE = "data/firms_india_baseline.csv"
OUTPUT_FILE = "data/india_ai_training.csv"

print("=" * 70)
print("INDIA FIRMS AI TRAINING DATASET")
print("=" * 70)

# ------------------------------------------------------------
# Load corrected baseline
# ------------------------------------------------------------

df = pd.read_csv(BASELINE_FILE)

print(f"Input hotspots : {len(df)}")

# ------------------------------------------------------------
# Clean numeric columns
# ------------------------------------------------------------

numeric_columns = [
    "frp",
    "baseline_frp",
    "frp_change_percent",
    "historical_detections"
]

for col in numeric_columns:
    if col in df.columns:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

# ------------------------------------------------------------
# Handle missing values
# ------------------------------------------------------------

df["baseline_available"] = (
    df["baseline_frp"].notna().astype(int)
)

df["frp_change_percent"] = (
    df["frp_change_percent"].fillna(0)
)

df["historical_detections"] = (
    df["historical_detections"].fillna(0)
)

# ------------------------------------------------------------
# Remove obvious Sri Lanka points
# ------------------------------------------------------------
# The original India bounding box included Sri Lanka.
# This simple filter removes the obvious southern points.
#
# It is NOT a replacement for a proper India administrative
# boundary; production deployment should use an official
# country polygon.

before = len(df)

df = df[
    ~(
        (df["latitude"] < 8.0) &
        (df["longitude"] > 79.0) &
        (df["longitude"] < 82.5)
    )
].copy()

removed = before - len(df)

print(f"Obvious non-India points removed : {removed}")
print(f"Remaining hotspots               : {len(df)}")

# ------------------------------------------------------------
# Create AI features
# ------------------------------------------------------------

df["frp_anomaly_score"] = (
    df["frp_change_percent"].clip(
        lower=-100,
        upper=500
    )
)

df["high_frp"] = (
    df["frp"] >= 20
).astype(int)

df["strong_anomaly"] = (
    df["frp_change_percent"] >= 100
).astype(int)

df["persistent_heat"] = (
    df["historical_detections"] >= 2
).astype(int)

df["new_event"] = (
    df["historical_detections"] == 0
).astype(int)

# ------------------------------------------------------------
# Prototype rule-based labels  (6 classes)
# ------------------------------------------------------------
#
# Industrial Fire    : sharp FRP spike + abnormal increase, not persistent
# Gas Flare          : extremely high persistent FRP — always-on flame
# Forest / Wildfire  : high FRP burst, brand-new event (no history)
# Agricultural Burn  : moderate FRP, many historical detections, low baseline
# Mining Activity    : low-moderate stable persistent heat
# Other Thermal Event: everything else
#
# These are heuristic labels for demonstrating the classifier.
# They are NOT ground-truth incident labels.
# ------------------------------------------------------------

def assign_label(row):

    change       = float(row["frp_change_percent"])
    frp          = float(row["frp"])
    detections   = float(row["historical_detections"])
    status       = row["persistence_status"]
    baseline     = row["baseline_frp"]

    has_baseline = not (
        isinstance(baseline, float) and pd.isna(baseline)
    )
    baseline_val = float(baseline) if has_baseline else 0.0

    is_persistent = status in [
        "Persistent / Stable",
        "Persistent / Reduced"
    ]
    is_abnormal   = status == "Abnormal Increase"
    is_new        = status == "New / No Local History" or detections == 0

    # ---- Gas Flare ----
    # Always-on very high FRP source with long history
    if (
        frp >= 30
        and detections >= 10
        and is_persistent
        and abs(change) < 80
    ):
        return "Gas Flare"

    # ---- Industrial Fire ----
    # Sudden abnormal spike above a known baseline
    if (
        is_abnormal
        and change >= 100
        and frp >= 10
        and not is_new
    ):
        return "Industrial Fire"

    # ---- Forest / Wildfire ----
    # Large heat burst with no or very little prior history
    if (
        frp >= 15
        and is_new
        and change >= 50
    ):
        return "Forest / Wildfire"

    # ---- Agricultural Burning ----
    # Many past detections (seasonal), moderate FRP, not extreme anomaly
    if (
        detections >= 5
        and frp < 40
        and abs(change) < 150
        and not is_persistent
    ):
        return "Agricultural Burning"

    # ---- Mining Activity ----
    # Low-moderate stable heat, persistent, moderate history
    if (
        is_persistent
        and frp < 30
        and detections >= 2
    ):
        return "Mining Activity"

    return "Other Thermal Event"


df["classification"] = df.apply(
    assign_label,
    axis=1
)


# ------------------------------------------------------------
# Risk score
# ------------------------------------------------------------

def calculate_risk(row):

    score = 0

    # FRP
    if row["frp"] >= 50:
        score += 35
    elif row["frp"] >= 20:
        score += 25
    elif row["frp"] >= 10:
        score += 15
    else:
        score += 5

    # FRP anomaly
    change = row["frp_change_percent"]

    if change >= 300:
        score += 40
    elif change >= 100:
        score += 30
    elif change >= 50:
        score += 20
    elif change > 0:
        score += 10

    # New event
    if row["historical_detections"] == 0:
        score += 15

    # Persistent stable heat reduces fire suspicion
    if row["persistence_status"] in [
        "Persistent / Stable",
        "Persistent / Reduced"
    ]:
        score -= 15

    return max(0, min(100, score))


df["risk_score"] = df.apply(
    calculate_risk,
    axis=1
)

# ------------------------------------------------------------
# Risk category
# ------------------------------------------------------------

def risk_category(score):

    if score >= 70:
        return "HIGH"

    if score >= 40:
        return "MEDIUM"

    return "LOW"


df["risk_category"] = df["risk_score"].apply(
    risk_category
)

# ------------------------------------------------------------
# AI training features
# ------------------------------------------------------------

feature_columns = [
    "frp",
    "baseline_frp",
    "frp_change_percent",
    "historical_detections",
    "frp_anomaly_score",
    "high_frp",
    "strong_anomaly",
    "persistent_heat",
    "new_event"
]

# Make sure all columns exist
for col in feature_columns:

    if col not in df.columns:
        df[col] = 0

# ------------------------------------------------------------
# Save
# ------------------------------------------------------------

df.to_csv(
    OUTPUT_FILE,
    index=False
)

print()
print("=" * 70)
print("AI DATASET CREATED")
print("=" * 70)

print(f"Records : {len(df)}")
print(f"Saved   : {OUTPUT_FILE}")

print()
print("Classification distribution:")
print(
    df["classification"].value_counts()
)

print()
print("Risk distribution:")
print(
    df["risk_category"].value_counts()
)

print()
print("Top 10 highest-risk hotspots:")

print(
    df[
        [
            "latitude",
            "longitude",
            "frp",
            "frp_change_percent",
            "historical_detections",
            "classification",
            "risk_score",
            "risk_category"
        ]
    ]
    .sort_values(
        "risk_score",
        ascending=False
    )
    .head(10)
    .to_string(index=False)
)

print()
print("✅ India AI training dataset ready.")