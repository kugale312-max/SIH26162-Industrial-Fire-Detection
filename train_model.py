import pandas as pd
import os

from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

import joblib


# --------------------------------
# Load Dataset
# --------------------------------

data = pd.read_csv("data/firms_data.csv")

# Calculate change from normal thermal baseline

data["frp_change_percent"] = (
    (data["frp"] - data["baseline_frp"])
    / data["baseline_frp"]
) * 100

print("Dataset loaded successfully!")
print(data)


# --------------------------------
# Convert categorical data
# --------------------------------

data["near_industry"] = data["near_industry"].map({
    "Yes": 1,
    "No": 0
})

data["land_type"] = data["land_type"].map({
    "Industrial": 1,
    "Forest": 2,
    "Agriculture": 3
})


# --------------------------------
# Select Features
# --------------------------------

features = [
    "frp",
    "baseline_frp",
    "frp_change_percent",
    "confidence",
    "land_type",
    "near_industry",
    "detections",
    "duration_hours"
]

X = data[features]

y = data["classification"]


# --------------------------------
# Encode target labels
# --------------------------------

encoder = LabelEncoder()

y_encoded = encoder.fit_transform(y)


# --------------------------------
# Train/Test Split
# --------------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y_encoded,
    test_size=0.3,
    random_state=42,
    stratify=y_encoded
)


# --------------------------------
# Create Random Forest Model
# --------------------------------

model = RandomForestClassifier(
    n_estimators=100,
    random_state=42
)


# --------------------------------
# Train Model
# --------------------------------

model.fit(X_train, y_train)


# --------------------------------
# Test Model
# --------------------------------

predictions = model.predict(X_test)

accuracy = accuracy_score(
    y_test,
    predictions
)

print("\nModel Accuracy:", accuracy)

print("\nClassification Report:")
print(
    classification_report(
        y_test,
        predictions,
        target_names=encoder.classes_,
        zero_division=0
    )
)


# --------------------------------
# Save Model
# --------------------------------

os.makedirs("model", exist_ok=True)

joblib.dump(
    model,
    "model/fire_classifier.pkl"
)

joblib.dump(
    encoder,
    "model/label_encoder.pkl"
)

print("\nModel saved successfully!")