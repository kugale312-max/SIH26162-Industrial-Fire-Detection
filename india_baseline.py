import os
import sys
import math
import numpy as np
import pandas as pd

# Ensure safe console output for unicode characters across platforms
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# ============================================================
# INDIA FIRMS BASELINE + PERSISTENCE
# ============================================================
# Input:
#   data/firms_india.csv
#   data/firms_india_historical.csv
#
# Output:
#   data/firms_india_baseline.csv
#
# For every current FIRMS hotspot, this script finds historical
# FIRMS observations within 2 km and calculates:
#   - historical baseline FRP
#   - number of historical detections
#   - FRP change %
#   - persistence status
# ============================================================

CURRENT_FILE = "data/firms_india.csv"
HISTORICAL_FILE = "data/firms_india_historical.csv"
OUTPUT_FILE = "data/firms_india_baseline.csv"

SEARCH_RADIUS_KM = 2.0


def haversine_km(lat1, lon1, lat2, lon2):
    """Distance between two latitude/longitude points in km."""

    r = 6371.0

    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    return 2 * r * math.asin(math.sqrt(a))


def main():

    print("=" * 70)
    print("INDIA FIRMS BASELINE + PERSISTENCE ANALYSIS")
    print("=" * 70)

    if not os.path.exists(CURRENT_FILE):
        print(f"❌ Missing file: {CURRENT_FILE}")
        raise SystemExit(1)

    if not os.path.exists(HISTORICAL_FILE):
        print(f"❌ Missing file: {HISTORICAL_FILE}")
        raise SystemExit(1)

    current = pd.read_csv(CURRENT_FILE)
    historical = pd.read_csv(HISTORICAL_FILE)

    print(f"Current hotspots     : {len(current):,}")
    print(f"Historical records   : {len(historical):,}")

    # Numeric cleanup
    for df in [current, historical]:

        df["latitude"] = pd.to_numeric(
            df["latitude"], errors="coerce"
        )

        df["longitude"] = pd.to_numeric(
            df["longitude"], errors="coerce"
        )

        df["frp"] = pd.to_numeric(
            df["frp"], errors="coerce"
        )

    current = current.dropna(
        subset=["latitude", "longitude", "frp"]
    ).copy()

    historical = historical.dropna(
        subset=["latitude", "longitude", "frp"]
    ).copy()

    # Convert dates where available.
    if "acq_date" in current.columns:
        current["acq_date"] = pd.to_datetime(
            current["acq_date"],
            errors="coerce"
        )

    if "acq_date" in historical.columns:
        historical["acq_date"] = pd.to_datetime(
            historical["acq_date"],
            errors="coerce"
        )

    results = []

    print("\nCalculating local historical baselines...")

    h_lats = historical["latitude"].to_numpy()
    h_lons = historical["longitude"].to_numpy()
    h_frps = historical["frp"].to_numpy()
    has_dates = "acq_date" in current.columns and "acq_date" in historical.columns
    h_dates = historical["acq_date"].to_numpy() if has_dates else None

    for index, row in current.iterrows():

        current_lat = row["latitude"]
        current_lon = row["longitude"]
        current_frp = row["frp"]

        distances = []

        # Coarse bounding-box filter: 2.0 km is < 0.02 deg; ±0.03 deg is ~3.3 km
        candidate_mask = (
            (h_lats >= current_lat - 0.03) & (h_lats <= current_lat + 0.03) &
            (h_lons >= current_lon - 0.03) & (h_lons <= current_lon + 0.03)
        )
        candidate_indices = np.where(candidate_mask)[0]

        for h_index in candidate_indices:

            # Do not compare an observation with itself when the
            # same observation appears in the historical collection.
            if (
                has_dates
                and pd.notna(row.get("acq_date"))
                and pd.notna(h_dates[h_index])
                and row["acq_date"] == h_dates[h_index]
                and abs(current_lat - h_lats[h_index]) < 1e-7
                and abs(current_lon - h_lons[h_index]) < 1e-7
            ):
                continue

            distance = haversine_km(
                current_lat,
                current_lon,
                h_lats[h_index],
                h_lons[h_index]
            )

            if distance <= SEARCH_RADIUS_KM:
                distances.append(
                    (h_index, distance, h_frps[h_index])
                )

        # Historical observations near this hotspot.
        nearby = [
            item for item in distances
            if item[2] > 0
        ]

        if nearby:

            baseline = sum(
                item[2] for item in nearby
            ) / len(nearby)

            detections = len(nearby)

            nearest_distance = min(
                item[1] for item in nearby
            )

            frp_change = (
                (current_frp - baseline)
                / baseline
            ) * 100 if baseline > 0 else float("nan")

        else:

            baseline = float("nan")
            detections = 0
            nearest_distance = float("nan")
            frp_change = float("nan")


        # --------------------------------------------------------
        # Persistence classification
        # --------------------------------------------------------
        #
        # This is a prototype rule, not a ground-truth fire label.
        #
        # 2+ historical detections + modest FRP change:
        #       persistent / recurring thermal source
        #
        # Large increase:
        #       abnormal thermal event
        #
        # No historical observations:
        #       new thermal event
        # --------------------------------------------------------

        if detections >= 2 and pd.notna(frp_change):

            if abs(frp_change) < 50:
                persistence = "Persistent / Stable"
            elif frp_change >= 50:
                persistence = "Abnormal Increase"
            else:
                persistence = "Persistent / Reduced"

        elif detections == 1:

            if pd.notna(frp_change) and frp_change >= 50:
                persistence = "Abnormal Increase"
            else:
                persistence = "Single Historical Detection"

        else:

            persistence = "New / No Local History"


        result = row.to_dict()

        result["baseline_frp"] = baseline
        result["historical_detections"] = detections
        result["nearest_historical_distance_km"] = nearest_distance
        result["frp_change_percent"] = frp_change
        result["persistence_status"] = persistence

        results.append(result)


    output = pd.DataFrame(results)

    output.to_csv(
        OUTPUT_FILE,
        index=False
    )


    print("\n" + "=" * 70)
    print("BASELINE ANALYSIS COMPLETE")
    print("=" * 70)

    print(f"Processed hotspots : {len(output):,}")
    print(f"Saved to           : {OUTPUT_FILE}")

    if "persistence_status" in output.columns:

        print("\nPersistence status:")

        print(
            output["persistence_status"]
            .value_counts()
        )

    if "baseline_frp" in output.columns:

        available = output["baseline_frp"].notna().sum()

        print(
            f"\nBaseline available : "
            f"{available:,}/{len(output):,}"
        )

    if "frp_change_percent" in output.columns:

        changes = output[
            "frp_change_percent"
        ].dropna()

        if not changes.empty:

            print(
                f"Average FRP change : "
                f"{changes.mean():.2f}%"
            )

            print(
                f"Maximum FRP change : "
                f"{changes.max():.2f}%"
            )

    print("\nFirst 5 processed hotspots:")
    print(
        output[
            [
                "latitude",
                "longitude",
                "frp",
                "baseline_frp",
                "historical_detections",
                "frp_change_percent",
                "persistence_status"
            ]
        ].head()
    )

    print("\n✅ India baseline dataset ready.")


if __name__ == "__main__":
    main()
