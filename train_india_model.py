import os
import sys
import json
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score
)

# Ensure safe console output for unicode characters across platforms
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ============================================================
# INDIA FIRMS MULTI-CLASS RANDOM FOREST CLASSIFIER
# ============================================================
INPUT_FILE = "data/india_ai_training.csv"
MODEL_DIR = "model"
os.makedirs(MODEL_DIR, exist_ok=True)

MODEL_FILE = os.path.join(MODEL_DIR, "india_fire_classifier.pkl")
ENCODER_FILE = os.path.join(MODEL_DIR, "india_label_encoder.pkl")
IMPUTER_FILE = os.path.join(MODEL_DIR, "india_imputer.pkl")
METRICS_FILE = os.path.join(MODEL_DIR, "model_metrics.json")
EVAL_CSV_FILE = "data/india_ai_test_evaluation.csv"

print("=" * 70)
print("TRAINING FIRESIGHT AI 7-CLASS CLASSIFIER")
print("=" * 70)

if not os.path.exists(INPUT_FILE):
    print(f"❌ Input training file missing: {INPUT_FILE}")
    sys.exit(1)

df = pd.read_csv(INPUT_FILE)
print(f"Total dataset records : {len(df)}")

# ------------------------------------------------------------
# 1. Feature Definition
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
y = df["classification"].astype(str)

# ------------------------------------------------------------
# 2. Encode Labels
# ------------------------------------------------------------
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)
classes = list(label_encoder.classes_)

print(f"\nTarget classes ({len(classes)}):")
for i, cls in enumerate(classes):
    count = int((y == cls).sum())
    print(f"  [{i}] {cls:26s} : {count:5d} samples ({count/len(df)*100:5.1f}%)")

# ------------------------------------------------------------
# 3. Stratified Train / Test Split (Preventing Data Leakage)
# ------------------------------------------------------------
# Split occurs BEFORE any imputation to ensure strictly zero test data leakage
X_train_raw, X_test_raw, y_train, y_test = train_test_split(
    X,
    y_encoded,
    test_size=0.20,
    random_state=42,
    stratify=y_encoded
)

print(f"\nTrain samples : {len(X_train_raw)}")
print(f"Test samples  : {len(X_test_raw)}")

# ------------------------------------------------------------
# 4. Imputation (Fitted ONLY on X_train to prevent leakage)
# ------------------------------------------------------------
imputer = SimpleImputer(strategy="median")
X_train = imputer.fit_transform(X_train_raw)
X_test = imputer.transform(X_test_raw)

# ------------------------------------------------------------
# 5. Model Architecture & Training (Handling Class Imbalance)
# ------------------------------------------------------------
params = {
    "n_estimators": 250,
    "max_depth": 12,
    "min_samples_split": 4,
    "min_samples_leaf": 2,
    "class_weight": "balanced_subsample",
    "random_state": 42,
    "n_jobs": -1
}

model = RandomForestClassifier(**params)
model.fit(X_train, y_train)

# ------------------------------------------------------------
# 6. Comprehensive Evaluation on Held-Out Test Set
# ------------------------------------------------------------
y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)

accuracy = accuracy_score(y_test, y_pred) * 100.0
macro_f1 = f1_score(y_test, y_pred, average="macro", zero_division=0) * 100.0
weighted_f1 = f1_score(y_test, y_pred, average="weighted", zero_division=0) * 100.0
macro_prec = precision_score(y_test, y_pred, average="macro", zero_division=0) * 100.0
macro_rec = recall_score(y_test, y_pred, average="macro", zero_division=0) * 100.0

report_dict = classification_report(
    y_test,
    y_pred,
    target_names=classes,
    output_dict=True,
    zero_division=0
)

cm = confusion_matrix(y_test, y_pred)
cm_list = cm.tolist()

print("\n" + "=" * 70)
print("TEST SET EVALUATION METRICS (HELD-OUT 20% SPLIT)")
print("=" * 70)
print(f"Overall Test Accuracy  : {accuracy:6.2f}%")
print(f"Macro F1-Score         : {macro_f1:6.2f}%")
print(f"Weighted F1-Score      : {weighted_f1:6.2f}%")
print(f"Macro Precision        : {macro_prec:6.2f}%")
print(f"Macro Recall           : {macro_rec:6.2f}%")

print("\nDetailed Per-Class Performance:")
print(f"{'Class Name':26s} | {'Prec (%)':8s} | {'Rec (%)':8s} | {'F1 (%)':8s} | {'Support':7s}")
print("-" * 65)
for cls in classes:
    r = report_dict[cls]
    print(f"{cls:26s} | {r['precision']*100:8.2f} | {r['recall']*100:8.2f} | {r['f1-score']*100:8.2f} | {int(r['support']):7d}")

print("\nConfusion Matrix (Rows: Ground Truth, Cols: Predicted):")
header_str = "    " + "".join([f"[{i:^5d}]" for i in range(len(classes))])
print(header_str)
for i, row in enumerate(cm):
    row_str = f"[{i}] " + "".join([f"{val:^7d}" for val in row]) + f"  ({classes[i]})"
    print(row_str)

# ------------------------------------------------------------
# 7. Feature Importances
# ------------------------------------------------------------
importance_df = pd.DataFrame({
    "Feature": features,
    "Importance": model.feature_importances_
}).sort_values("Importance", ascending=False).reset_index(drop=True)

print("\nTop 10 Feature Importances:")
print(importance_df.head(10).to_string(index=False))

# ------------------------------------------------------------
# 8. Save Model Artefacts & Metrics
# ------------------------------------------------------------
joblib.dump(model, MODEL_FILE)
joblib.dump(label_encoder, ENCODER_FILE)
joblib.dump(imputer, IMPUTER_FILE)

# Save test evaluation CSV for auditability
test_eval_df = X_test_raw.copy()
test_eval_df["true_class"] = label_encoder.inverse_transform(y_test)
test_eval_df["predicted_class"] = label_encoder.inverse_transform(y_pred)
test_eval_df["confidence"] = (y_prob.max(axis=1) * 100.0).round(2)
sorted_probs = np.sort(y_prob, axis=1)
test_eval_df["prediction_margin"] = ((sorted_probs[:, -1] - sorted_probs[:, -2]) * 100.0).round(2)
test_eval_df["is_uncertain"] = (test_eval_df["confidence"] < 60.0) | (test_eval_df["prediction_margin"] < 15.0)
test_eval_df.to_csv(EVAL_CSV_FILE, index=False)

ist = timezone(timedelta(hours=5, minutes=30))
metrics_payload = {
    "evaluated_at": datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S IST"),
    "accuracy": round(accuracy, 2),
    "macro_f1": round(macro_f1, 2),
    "weighted_f1": round(weighted_f1, 2),
    "macro_precision": round(macro_prec, 2),
    "macro_recall": round(macro_rec, 2),
    "n_train": len(X_train),
    "n_test": len(X_test),
    "classes": classes,
    "features": features,
    "params": {k: str(v) for k, v in params.items()},
    "report": report_dict,
    "confusion_matrix": cm_list,
    "importances": importance_df.to_dict(orient="records"),
    "uncertain_samples_pct": round(float(test_eval_df["is_uncertain"].mean() * 100.0), 2)
}

with open(METRICS_FILE, "w", encoding="utf-8") as f:
    json.dump(metrics_payload, f, indent=4)

print("\n" + "=" * 70)
print("MODEL TRAINING & EVALUATION COMPLETE")
print("=" * 70)
print(f"Model saved      : {MODEL_FILE}")
print(f"Encoder saved    : {ENCODER_FILE}")
print(f"Imputer saved    : {IMPUTER_FILE}")
print(f"Metrics saved    : {METRICS_FILE}")
print(f"Test audit saved : {EVAL_CSV_FILE}")
print("\n✅ Leak-free model ready.")