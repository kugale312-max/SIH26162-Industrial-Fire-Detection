import pandas as pd
import numpy as np


print("======================================")
print("AI TRAINING DATA AUGMENTATION")
print("======================================")


# Load real training data
real_data = pd.read_csv(
    "data/ai_training_data.csv"
)

print(
    "Real observations:",
    len(real_data)
)


# =========================================================
# SYNTHETIC INDUSTRIAL FIRE SCENARIOS
# =========================================================

np.random.seed(42)

fire_samples = []


for i in range(20):

    baseline = np.random.uniform(
        0.5,
        3.0
    )

    # Abnormally high current FRP
    frp = baseline * np.random.uniform(
        2.0,
        5.0
    )

    frp_change = (
        (frp - baseline)
        / baseline
    ) * 100

    fire_samples.append({

        "latitude":
            np.random.uniform(
                18.35,
                18.85
            ),

        "longitude":
            np.random.uniform(
                73.65,
                74.35
            ),

        "frp":
            round(frp, 2),

        "baseline_frp":
            round(baseline, 2),

        "frp_change_percent":
            round(frp_change, 2),

        "confidence_score":
            np.random.choice(
                [70, 95],
                p=[0.2, 0.8]
            ),

        # Fire is near an industrial location
        "Distance_to_Industry_km":
            round(
                np.random.uniform(
                    0.2,
                    1.8
                ),
                2
            ),

        "near_industry_numeric":
            1,

        "detections":
            np.random.randint(
                1,
                4
            ),

        "classification":
            "Industrial Fire"
    })


synthetic_fire_data = pd.DataFrame(
    fire_samples
)


# =========================================================
# COMBINE REAL + SYNTHETIC DATA
# =========================================================

combined = pd.concat(
    [
        real_data,
        synthetic_fire_data
    ],
    ignore_index=True
)


# =========================================================
# SAVE
# =========================================================

combined.to_csv(
    "data/ai_training_augmented.csv",
    index=False
)


print()
print("======================================")
print("AUGMENTED DATASET")
print("======================================")

print(
    "Real records:",
    len(real_data)
)

print(
    "Synthetic fire records:",
    len(synthetic_fire_data)
)

print(
    "Total training records:",
    len(combined)
)


print()
print("Class distribution:")

print(
    combined[
        "classification"
    ].value_counts()
)


print()
print("✓ Saved:")
print(
    "data/ai_training_augmented.csv"
)

print()
print("======================================")
print("COMPLETED")
print("======================================")