import os
import sys
import pandas as pd
import joblib

# Ensure safe console output for unicode characters across platforms
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ============================================================
# INDIA FIRMS AI PREDICTION
# ============================================================

INPUT_FILE = "data/india_ai_training.csv"
OUTPUT_FILE = "data/india_ai_predictions.csv"

MODEL_FILE = "model/india_fire_classifier.pkl"
ENCODER_FILE = "model/india_label_encoder.pkl"
IMPUTER_FILE = "model/india_imputer.pkl"

print("=" * 70)
print("INDIA FIRMS AI HOTSPOT PREDICTION")
print("=" * 70)

# ------------------------------------------------------------
# Load files
# ------------------------------------------------------------

df = pd.read_csv(INPUT_FILE)

model = joblib.load(MODEL_FILE)
label_encoder = joblib.load(ENCODER_FILE)
imputer = joblib.load(IMPUTER_FILE)

print(f"Input hotspots : {len(df)}")

# ------------------------------------------------------------
# Features
# ------------------------------------------------------------

features = [
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

X = df[features].copy()

# ------------------------------------------------------------
# Impute missing values
# ------------------------------------------------------------

X_imputed = imputer.transform(X)

# ------------------------------------------------------------
# AI prediction
# ------------------------------------------------------------

prediction_encoded = model.predict(X_imputed)

prediction_probability = model.predict_proba(
    X_imputed
)

df["ai_classification"] = label_encoder.inverse_transform(
    prediction_encoded
)

# Highest probability
df["ai_confidence"] = (
    prediction_probability.max(axis=1) * 100
).round(2)

# ------------------------------------------------------------
# AI probabilities for each class
# ------------------------------------------------------------

class_names = label_encoder.classes_

for i, class_name in enumerate(class_names):

    safe_name = (
        class_name
        .lower()
        .replace(" ", "_")
    )

    df[f"prob_{safe_name}"] = (
        prediction_probability[:, i] * 100
    ).round(2)

# ------------------------------------------------------------
# Final risk score
# ------------------------------------------------------------

def calculate_final_risk(row):

    score = float(row["risk_score"])

    # AI classification adjustment for all 6 classes
    ai_class = row["ai_classification"]

    if ai_class == "Industrial Fire":
        score += 10     # highest threat
    elif ai_class == "Gas Flare":
        score += 5      # persistent hazard
    elif ai_class == "Forest / Wildfire":
        score += 8      # rapid-spread risk
    elif ai_class == "Agricultural Burning":
        score -= 5      # controlled / seasonal — lower threat
    elif ai_class == "Mining Activity":
        score -= 10     # stable known source — lowest threat
    # "Other Thermal Event" → no adjustment

    return max(0, min(100, score))



df["final_risk_score"] = df.apply(
    calculate_final_risk,
    axis=1
)

# ------------------------------------------------------------
# Final risk category
# ------------------------------------------------------------

def risk_category(score):

    if score >= 70:
        return "HIGH"

    elif score >= 40:
        return "MEDIUM"

    return "LOW"


df["final_risk_category"] = (
    df["final_risk_score"]
    .apply(risk_category)
)

# ------------------------------------------------------------
# Sort by risk
# ------------------------------------------------------------

df = df.sort_values(
    by="final_risk_score",
    ascending=False
).reset_index(drop=True)

# ------------------------------------------------------------
# Save
# ------------------------------------------------------------

df.to_csv(
    OUTPUT_FILE,
    index=False
)

# ------------------------------------------------------------
# Results
# ------------------------------------------------------------

print()
print("=" * 70)
print("AI PREDICTION COMPLETE")
print("=" * 70)

print(f"Predictions generated : {len(df)}")
print(f"Saved to              : {OUTPUT_FILE}")

print()
print("AI classification:")

print(
    df["ai_classification"]
    .value_counts()
)

print()
print("Final risk category:")

print(
    df["final_risk_category"]
    .value_counts()
)

print()
print("Top 15 AI predictions:")

print(
    df[
        [
            "latitude",
            "longitude",
            "frp",
            "frp_change_percent",
            "historical_detections",
            "ai_classification",
            "ai_confidence",
            "final_risk_score",
            "final_risk_category"
        ]
    ]
    .head(15)
    .to_string(index=False)
)

print()
print("✅ India AI prediction dataset ready.")