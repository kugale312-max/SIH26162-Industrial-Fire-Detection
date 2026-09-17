import os
import sys
import pandas as pd
import numpy as np
import joblib

# Ensure safe console output for unicode characters across platforms
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ============================================================
# INDIA FIRMS AI MULTI-CLASS HOTSPOT PREDICTION
# ============================================================

INPUT_FILE = "data/india_ai_training.csv"
OUTPUT_FILE = "data/india_ai_predictions.csv"

MODEL_FILE = "model/india_fire_classifier.pkl"
ENCODER_FILE = "model/india_label_encoder.pkl"
IMPUTER_FILE = "model/india_imputer.pkl"

print("=" * 70)
print("INDIA FIRMS AI HOTSPOT PREDICTION (7 CLASSES + UNCERTAINTY)")
print("=" * 70)

for f in [INPUT_FILE, MODEL_FILE, ENCODER_FILE, IMPUTER_FILE]:
    if not os.path.exists(f):
        print(f"❌ Required file missing: {f}")
        sys.exit(1)

df_all = pd.read_csv(INPUT_FILE)

# Filter to current live hotspots for predictions (or all if not tagged)
if "is_current" in df_all.columns:
    df = df_all[df_all["is_current"] == 1].copy().reset_index(drop=True)
else:
    df = df_all.copy()

print(f"Loaded live hotspots to assess : {len(df)}")

model = joblib.load(MODEL_FILE)
label_encoder = joblib.load(ENCODER_FILE)
imputer = joblib.load(IMPUTER_FILE)

# ------------------------------------------------------------
# 1. Prepare Features
# ------------------------------------------------------------
features = [
    "frp",
    "baseline_frp",
    "frp_change_percent",
    "historical_detections",
    "frp_anomaly_score",
    "frp_ratio",
    "confidence_score",
    "is_night",
    "brightness_diff",
    "dist_to_industry_km",
    "dist_to_mining_km",
    "dist_to_gas_infrastructure_km",
    "near_industry",
    "near_mining",
    "near_gas_infra",
    "land_cover_code",
    "high_frp",
    "strong_anomaly",
    "persistent_heat",
    "new_event"
]

for col in features:
    if col not in df.columns:
        df[col] = 0.0

X = df[features].copy()
X_imputed = imputer.transform(X)

# ------------------------------------------------------------
# 2. Generate Probabilistic Predictions
# ------------------------------------------------------------
pred_encoded = model.predict(X_imputed)
pred_probs = model.predict_proba(X_imputed)

df["ai_classification"] = label_encoder.inverse_transform(pred_encoded)
df["ai_confidence"] = (pred_probs.max(axis=1) * 100.0).round(2)

# Save per-class probabilities
classes = label_encoder.classes_
for i, cls in enumerate(classes):
    safe_col = "prob_" + cls.lower().replace(" ", "_").replace("/", "_")
    df[safe_col] = (pred_probs[:, i] * 100.0).round(2)

# Compute second most probable class & prediction margin
sorted_indices = np.argsort(pred_probs, axis=1)
top_class_idx = sorted_indices[:, -1]
second_class_idx = sorted_indices[:, -2]

df["secondary_class"] = [classes[idx] for idx in second_class_idx]
top_probs = np.take_along_axis(pred_probs, top_class_idx[:, None], axis=1).squeeze()
second_probs = np.take_along_axis(pred_probs, second_class_idx[:, None], axis=1).squeeze()
df["prediction_margin"] = ((top_probs - second_probs) * 100.0).round(2)

# ------------------------------------------------------------
# 3. Uncertainty Flagging
# ------------------------------------------------------------
# Flag hotspot as uncertain if top confidence is < 60% OR the margin
# between top-1 and top-2 candidate classes is < 15%.
df["is_uncertain"] = (df["ai_confidence"] < 60.0) | (df["prediction_margin"] < 15.0)

def describe_uncertainty(row):
    if not row["is_uncertain"]:
        return "Confident Assessment"
    if row["ai_confidence"] < 60.0 and row["prediction_margin"] < 15.0:
        return f"Ambiguous ({row['ai_classification']} vs {row['secondary_class']})"
    elif row["prediction_margin"] < 15.0:
        return f"Borderline between {row['ai_classification']} & {row['secondary_class']}"
    else:
        return f"Low Confidence ({row['ai_confidence']:.1f}%)"

df["uncertainty_flag"] = df.apply(describe_uncertainty, axis=1)

# Ensure legacy columns for dashboard compatibility
if "nearest_industrial_facility" in df.columns and "Nearest Industrial Facility" not in df.columns:
    df["Nearest Industrial Facility"] = df["nearest_industrial_facility"]
if "dist_to_industry_km" in df.columns and "Distance to Industry (km)" not in df.columns:
    df["Distance to Industry (km)"] = df["dist_to_industry_km"]

# ------------------------------------------------------------
# 4. Final Risk Scoring & Classification Adjustment
# ------------------------------------------------------------
def compute_final_risk(row):
    base_score = float(row.get("risk_score", 30.0))
    ai_class = row["ai_classification"]

    # Consequence adjustment based on 7 classes
    if ai_class == "Industrial Fire":
        base_score += 12.0   # Highest threat to life and industrial assets
    elif ai_class == "Forest / Wildfire":
        base_score += 8.0    # Rapid spread environmental threat
    elif ai_class == "Gas Flare":
        base_score += 5.0    # Hazardous flame, usually controlled
    elif ai_class == "Agricultural Burning":
        base_score -= 5.0    # Controlled / seasonal cropland burn
    elif ai_class == "Mining Activity":
        base_score -= 8.0    # Controlled industrial pit/smolder operations
    elif ai_class == "Normal Persistent Source":
        base_score -= 12.0   # Routine operational kiln/furnace emitter
    # Other Thermal Event: 0 adjustment

    # If prediction is highly uncertain, slightly moderate extreme scores
    if row["is_uncertain"]:
        if base_score > 70.0:
            base_score -= 5.0

    return max(0.0, min(100.0, base_score))

df["final_risk_score"] = df.apply(compute_final_risk, axis=1).round(1)

def categorize_final_risk(score):
    if score >= 70.0:
        return "HIGH"
    elif score >= 40.0:
        return "MEDIUM"
    return "LOW"

df["final_risk_category"] = df["final_risk_score"].apply(categorize_final_risk)

# Sort by risk score descending
df = df.sort_values(by="final_risk_score", ascending=False).reset_index(drop=True)

# ------------------------------------------------------------
# 5. Save Output
# ------------------------------------------------------------
df.to_csv(OUTPUT_FILE, index=False)

print("\n" + "=" * 70)
print("AI PREDICTION GENERATION COMPLETE")
print("=" * 70)
print(f"Predictions generated : {len(df)}")
print(f"Saved to              : {OUTPUT_FILE}")

print("\nAI 7-Class Distribution:")
print(df["ai_classification"].value_counts().to_string())

print("\nFinal Risk Level Distribution:")
print(df["final_risk_category"].value_counts().to_string())

uncertain_count = int(df["is_uncertain"].sum())
print(f"\nUncertain Predictions : {uncertain_count} / {len(df)} ({uncertain_count/len(df)*100:.1f}%)")

print("\nTop 10 High-Risk Predictions:")
cols_to_show = [
    "latitude", "longitude", "frp", "frp_change_percent",
    "ai_classification", "ai_confidence", "is_uncertain",
    "final_risk_score", "final_risk_category"
]
print(df[[c for c in cols_to_show if c in df.columns]].head(10).to_string(index=False))

print("\n✅ India AI prediction dataset ready.")