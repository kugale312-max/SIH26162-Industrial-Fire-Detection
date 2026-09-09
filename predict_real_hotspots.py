import pandas as pd
import joblib

print("======================================")
print("REAL FIRMS AI PREDICTION")
print("======================================")

# Load real enriched FIRMS data
data = pd.read_csv("data/firms_enriched.csv")

# Make real-data column name match the training-data column name
data = data.rename(columns={
    "Distance to Industry (km)": "Distance_to_Industry_km"
})

# Load trained AI model
model = joblib.load("model/fire_classifier.pkl")
encoder = joblib.load("model/label_encoder.pkl")
imputer = joblib.load("model/imputer.pkl")

# Convert FIRMS confidence to numerical score
confidence_map = {
    "l": 30,
    "n": 70,
    "h": 95
}

data["confidence_score"] = (
    data["confidence"]
    .astype(str)
    .str.lower()
    .map(confidence_map)
    .fillna(70)
)

# Convert industry proximity to numerical value
data["near_industry_numeric"] = (
    data["near_industry"]
    .astype(str)
    .str.lower()
    .map({
        "yes": 1,
        "no": 0
    })
    .fillna(0)
)

# Features must match training
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

# Handle missing values
X = imputer.transform(X)

# AI prediction
predictions = model.predict(X)

# Convert numerical prediction back to class
data["AI Classification"] = encoder.inverse_transform(predictions)

# Get prediction probability
probabilities = model.predict_proba(X)

data["AI Confidence (%)"] = (
    probabilities.max(axis=1) * 100
).round(1)

print("\n======================================")
print("AI PREDICTIONS")
print("======================================")

for _, row in data.iterrows():

    print("\n--------------------------------------")

    print(
        f"Location: "
        f"{row['latitude']}, {row['longitude']}"
    )

    print(f"FRP: {row['frp']} MW")

    print(
        f"Distance to Industry: "
        f"{row['Distance_to_Industry_km']} km"
    )

    print(
        f"AI Classification: "
        f"{row['AI Classification']}"
    )

    print(
        f"AI Confidence: "
        f"{row['AI Confidence (%)']}%"
    )

# Save predictions
data.to_csv(
    "data/firms_ai_predictions.csv",
    index=False
)

print("\n======================================")
print("✓ PREDICTION COMPLETED")
print("======================================")

print("\nSaved:")
print("data/firms_ai_predictions.csv")