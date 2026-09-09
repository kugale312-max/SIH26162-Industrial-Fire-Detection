import os
import pandas as pd
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

# ============================================================
# INDIA FIRMS RANDOM FOREST MODEL
# ============================================================

INPUT_FILE = "data/india_ai_training.csv"

MODEL_DIR = "model"
os.makedirs(MODEL_DIR, exist_ok=True)

MODEL_FILE = os.path.join(
    MODEL_DIR,
    "india_fire_classifier.pkl"
)

ENCODER_FILE = os.path.join(
    MODEL_DIR,
    "india_label_encoder.pkl"
)

IMPUTER_FILE = os.path.join(
    MODEL_DIR,
    "india_imputer.pkl"
)

print("=" * 70)
print("INDIA FIRMS AI MODEL TRAINING")
print("=" * 70)

# ------------------------------------------------------------
# Load dataset
# ------------------------------------------------------------

df = pd.read_csv(INPUT_FILE)

print(f"Training records : {len(df)}")

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
y = df["classification"].astype(str)

# ------------------------------------------------------------
# Encode labels
# ------------------------------------------------------------

label_encoder = LabelEncoder()

y_encoded = label_encoder.fit_transform(y)

print()
print("Classes:")

for i, label in enumerate(label_encoder.classes_):
    print(f"  {i}: {label}")

# ------------------------------------------------------------
# Handle missing values
# ------------------------------------------------------------

imputer = SimpleImputer(strategy="median")

X_imputed = imputer.fit_transform(X)

# ------------------------------------------------------------
# Train/test split
# ------------------------------------------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X_imputed,
    y_encoded,
    test_size=0.20,
    random_state=42,
    stratify=y_encoded
)

print()
print(f"Training samples : {len(X_train)}")
print(f"Testing samples  : {len(X_test)}")

# ------------------------------------------------------------
# Random Forest
# ------------------------------------------------------------

model = RandomForestClassifier(
    n_estimators=200,
    random_state=42,
    class_weight="balanced",
    max_depth=8,
    min_samples_leaf=2
)

model.fit(
    X_train,
    y_train
)

# ------------------------------------------------------------
# Evaluation
# ------------------------------------------------------------

predictions = model.predict(X_test)

accuracy = accuracy_score(
    y_test,
    predictions
)

print()
print("=" * 70)
print("MODEL EVALUATION")
print("=" * 70)

print(
    f"Test accuracy : {accuracy * 100:.2f}%"
)

print()
print("Classification report:")

print(
    classification_report(
        y_test,
        predictions,
        target_names=label_encoder.classes_,
        zero_division=0
    )
)

# ------------------------------------------------------------
# Feature importance
# ------------------------------------------------------------

print()
print("Feature importance:")

importance = pd.DataFrame({
    "feature": features,
    "importance": model.feature_importances_
})

importance = importance.sort_values(
    "importance",
    ascending=False
)

print(
    importance.to_string(index=False)
)

# ------------------------------------------------------------
# Save model
# ------------------------------------------------------------

joblib.dump(
    model,
    MODEL_FILE
)

joblib.dump(
    label_encoder,
    ENCODER_FILE
)

joblib.dump(
    imputer,
    IMPUTER_FILE
)

print()
print("=" * 70)
print("MODEL TRAINING COMPLETE")
print("=" * 70)

print(f"Model    : {MODEL_FILE}")
print(f"Encoder  : {ENCODER_FILE}")
print(f"Imputer  : {IMPUTER_FILE}")

print()
print("✅ India Random Forest model ready.")