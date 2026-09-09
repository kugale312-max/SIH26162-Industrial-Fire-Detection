import pandas as pd
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.impute import SimpleImputer


print("======================================")
print("TRAINING AI MODEL")
print("======================================")

# Load augmented training data
data = pd.read_csv("data/ai_training_augmented.csv")

print(f"Training records: {len(data)}")

# Features used by the AI model
features = [
    "frp",
    "baseline_frp",
    "frp_change_percent",
    "confidence_score",
    "Distance_to_Industry_km",
    "near_industry_numeric",
    "detections"
]

X = data[features].copy()

# Target
y = data["classification"]

# Handle missing values
imputer = SimpleImputer(strategy="median")
X = imputer.fit_transform(X)

# Encode class labels
encoder = LabelEncoder()
y_encoded = encoder.fit_transform(y)

print("\nClasses:")
for i, label in enumerate(encoder.classes_):
    print(f"{i}: {label}")

# Create Random Forest model
model = RandomForestClassifier(
    n_estimators=150,
    random_state=42,
    class_weight="balanced"
)

# Train model using complete dataset
model.fit(X, y_encoded)

# Create model directory
import os
os.makedirs("model", exist_ok=True)

# Save model
joblib.dump(model, "model/fire_classifier.pkl")

# Save encoder
joblib.dump(encoder, "model/label_encoder.pkl")

# Save imputer
joblib.dump(imputer, "model/imputer.pkl")

print("\n======================================")
print("MODEL TRAINING COMPLETED")
print("======================================")

print("\n✓ Model saved:")
print("model/fire_classifier.pkl")

print("\n✓ Label encoder saved:")
print("model/label_encoder.pkl")

print("\n✓ Imputer saved:")
print("model/imputer.pkl")

print("\nClasses learned by model:")
print(list(encoder.classes_))

print("\n======================================")
print("READY FOR REAL FIRMS PREDICTION")
print("======================================")