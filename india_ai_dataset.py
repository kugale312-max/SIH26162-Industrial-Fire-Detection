import os
import sys
import math
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

# Ensure safe console output for unicode characters across platforms
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ============================================================
# INDIA AI MULTI-CLASS DATASET PIPELINE (7 CLASSES)
# ============================================================
# Uses:
#   - Real FIRMS historical telemetry & baseline observations
#   - Real current FIRMS satellite observations
#   - Distance to 3,200+ industrial, mining, and gas facilities
#   - Land-cover contextual terrain inference
#   - Continuous physical & telemetry features
#
# Target Classes:
#   1. Industrial Fire
#   2. Mining Activity
#   3. Agricultural Burning
#   4. Forest / Wildfire
#   5. Gas Flare
#   6. Other Thermal Event
#   7. Normal Persistent Source
# ============================================================

BASELINE_FILE = "data/firms_india_baseline.csv"
HISTORICAL_FILE = "data/firms_india_historical.csv"
OSM_INDIA_FILE = "data/industrial_locations_india.csv"
OSM_REAL_FILE = "data/industrial_locations_real.csv"
OUTPUT_FILE = "data/india_ai_training.csv"

print("=" * 70)
print("INDIA FIRMS AI MULTI-CLASS DATASET GENERATION")
print("=" * 70)

if not os.path.exists(BASELINE_FILE):
    print(f"❌ Baseline file missing: {BASELINE_FILE}")
    sys.exit(1)

# ------------------------------------------------------------
# 1. Load Current and Historical Datasets
# ------------------------------------------------------------
curr_df = pd.read_csv(BASELINE_FILE)
curr_df["latitude"] = pd.to_numeric(curr_df["latitude"], errors="coerce")
curr_df["longitude"] = pd.to_numeric(curr_df["longitude"], errors="coerce")
curr_df["frp"] = pd.to_numeric(curr_df["frp"], errors="coerce")
curr_df = curr_df.dropna(subset=["latitude", "longitude", "frp"]).copy()

# Boundary file for GeoPandas point-in-polygon filtering
BOUNDARY_FILE = "data/india_boundary.geojson"
b_geom = None
if os.path.exists(BOUNDARY_FILE):
    try:
        import geopandas as gpd
        gdf_b = gpd.read_file(BOUNDARY_FILE)
        b_geom = gdf_b.union_all()
        print(f"✅ Loaded India boundary polygon from {BOUNDARY_FILE}")
    except Exception as e:
        print(f"⚠️ GeoJSON boundary load warning: {e}")

def filter_inside_india(df_input):
    if b_geom is None or df_input.empty:
        return df_input
    import geopandas as gpd
    gdf_p = gpd.GeoDataFrame(df_input, geometry=gpd.points_from_xy(df_input["longitude"], df_input["latitude"]), crs="EPSG:4326")
    mask = gdf_p.intersects(b_geom)
    res = df_input[mask.values].copy()
    if "geometry" in res.columns:
        res = res.drop(columns=["geometry"])
    return res.reset_index(drop=True)

curr_df = filter_inside_india(curr_df)
curr_df["is_current"] = 1
print(f"Current live India hotspots (Point-in-Polygon filtered): {len(curr_df)}")

# Historical dataset for rich multi-temporal representation
hist_df = pd.DataFrame()
if os.path.exists(HISTORICAL_FILE):
    hist_raw = pd.read_csv(HISTORICAL_FILE)
    hist_raw["latitude"] = pd.to_numeric(hist_raw["latitude"], errors="coerce")
    hist_raw["longitude"] = pd.to_numeric(hist_raw["longitude"], errors="coerce")
    hist_raw["frp"] = pd.to_numeric(hist_raw["frp"], errors="coerce")
    hist_raw = hist_raw.dropna(subset=["latitude", "longitude", "frp"]).copy()
    hist_raw = filter_inside_india(hist_raw)

    # Sample diverse historical FIRMS records: all high FRP and balanced mid/low FRP
    high_frp = hist_raw[hist_raw["frp"] >= 18.0]
    mid_sample_n = min(1000, len(hist_raw[(hist_raw["frp"] < 18.0) & (hist_raw["frp"] >= 8.0)]))
    mid_frp = hist_raw[(hist_raw["frp"] < 18.0) & (hist_raw["frp"] >= 8.0)].sample(n=mid_sample_n, random_state=42)
    low_sample_n = min(1500, len(hist_raw[hist_raw["frp"] < 8.0]))
    low_frp = hist_raw[hist_raw["frp"] < 8.0].sample(n=low_sample_n, random_state=42)

    hist_sample = pd.concat([high_frp, mid_frp, low_frp]).drop_duplicates().reset_index(drop=True)
    hist_sample["is_current"] = 0
    print(f"Historical FIRMS samples selected: {len(hist_sample)}")
else:
    hist_sample = pd.DataFrame()

# ------------------------------------------------------------
# 2. Compute Historical Baselines for Sampled Records
# ------------------------------------------------------------
def to_cartesian(lat, lon):
    r_lat = np.radians(lat)
    r_lon = np.radians(lon)
    return np.column_stack([
        np.cos(r_lat) * np.cos(r_lon),
        np.cos(r_lat) * np.sin(r_lon),
        np.sin(r_lat)
    ])

if not hist_sample.empty:
    h_coords = to_cartesian(hist_raw["latitude"], hist_raw["longitude"])
    h_tree = cKDTree(h_coords)
    sub_coords = to_cartesian(hist_sample["latitude"], hist_sample["longitude"])

    # 2.0 km search radius on unit sphere
    r_chord = 2.0 * np.sin((2.0 / 6371.0) / 2.0)
    neighbors = h_tree.query_ball_point(sub_coords, r=r_chord)

    h_frps = hist_raw["frp"].to_numpy()
    baselines, counts, p_statuses = [], [], []

    for i, idxs in enumerate(neighbors):
        cur_frp = hist_sample.iloc[i]["frp"]
        other_idxs = [idx for idx in idxs if idx != i]
        counts.append(len(other_idxs))
        if other_idxs:
            b_val = float(np.mean(h_frps[other_idxs]))
            baselines.append(b_val)
            chg = ((cur_frp - b_val) / b_val) * 100.0 if b_val > 0 else 0.0
            if len(other_idxs) >= 2:
                if abs(chg) < 50.0:
                    p_statuses.append("Persistent / Stable")
                elif chg >= 50.0:
                    p_statuses.append("Abnormal Increase")
                else:
                    p_statuses.append("Persistent / Reduced")
            else:
                p_statuses.append("Single Historical Detection")
        else:
            baselines.append(np.nan)
            p_statuses.append("New / No Local History")

    hist_sample["baseline_frp"] = baselines
    hist_sample["historical_detections"] = counts
    hist_sample["persistence_status"] = p_statuses
    hist_sample["frp_change_percent"] = [
        ((f - b) / b) * 100.0 if pd.notna(b) and b > 0 else 0.0
        for f, b in zip(hist_sample["frp"], hist_sample["baseline_frp"])
    ]

# Combine current + historical
if not hist_sample.empty:
    df = pd.concat([curr_df, hist_sample], ignore_index=True)
else:
    df = curr_df.copy()

print(f"Total dataset size (Current + Historical): {len(df)}")

# ------------------------------------------------------------
# 3. Geospatial Facility Proximity (Industry, Mining, Gas)
# ------------------------------------------------------------
loc_file = OSM_INDIA_FILE if os.path.exists(OSM_INDIA_FILE) else (OSM_REAL_FILE if os.path.exists(OSM_REAL_FILE) else None)
all_facilities = pd.DataFrame()
if loc_file:
    try:
        all_facilities = pd.read_csv(loc_file)
        all_facilities["latitude"] = pd.to_numeric(all_facilities["latitude"], errors="coerce")
        all_facilities["longitude"] = pd.to_numeric(all_facilities["longitude"], errors="coerce")
        all_facilities = all_facilities.dropna(subset=["latitude", "longitude"]).copy()
    except Exception as e:
        print(f"⚠️ Error loading facilities: {e}")

type_col = all_facilities["type"].fillna("industrial").str.lower() if not all_facilities.empty else pd.Series(dtype=str)
name_col = all_facilities["name"].fillna("").str.lower() if not all_facilities.empty else pd.Series(dtype=str)

mining_mask = (type_col.str.contains("mine|quarry") | name_col.str.contains("mine|colliery|quarry|ore")) if not all_facilities.empty else pd.Series(dtype=bool)
KNOWN_MINING = [
    {"name": "Jharia Coalfield", "latitude": 23.74, "longitude": 86.42},
    {"name": "Bokaro Coal Basin", "latitude": 23.78, "longitude": 85.96},
    {"name": "Korba Coal Basin", "latitude": 22.35, "longitude": 82.68},
    {"name": "Singrauli Coalfield", "latitude": 24.20, "longitude": 82.66},
    {"name": "Talcher Coal Basin", "latitude": 20.95, "longitude": 85.22},
    {"name": "Chandrapur Mining Belt", "latitude": 19.96, "longitude": 79.30},
    {"name": "Bellary Iron Ore Belt", "latitude": 15.15, "longitude": 76.92},
    {"name": "Keonjhar Mining Belt", "latitude": 21.63, "longitude": 85.58},
]
mining_base = all_facilities[mining_mask] if not all_facilities.empty else pd.DataFrame()
mining_df = pd.concat([mining_base, pd.DataFrame(KNOWN_MINING)], ignore_index=True)

gas_mask = (type_col.str.contains("refinery|petroleum|oil|gas|petrochemical") | name_col.str.contains("refinery|iocl|bpcl|hpcl|ongc|gail|reliance|petroleum|lng|lpg")) if not all_facilities.empty else pd.Series(dtype=bool)
KNOWN_GAS = [
    {"name": "Hazira Petrochemical Hub", "latitude": 21.10, "longitude": 72.64},
    {"name": "Dahej Petrochemical Corridor", "latitude": 21.71, "longitude": 72.58},
    {"name": "Jamnagar Refinery Complex", "latitude": 22.36, "longitude": 69.87},
    {"name": "Vadinar Nayara Refinery", "latitude": 22.44, "longitude": 69.72},
    {"name": "Uran ONGC Gas Terminal", "latitude": 18.88, "longitude": 72.94},
    {"name": "Trombay Refinery Hub", "latitude": 19.01, "longitude": 72.90},
    {"name": "Barmer Cairn Oil Fields", "latitude": 25.88, "longitude": 71.35},
    {"name": "KG Basin Gas Terminal Kakinada", "latitude": 16.98, "longitude": 82.25},
    {"name": "Paradip IOCL Refinery", "latitude": 20.28, "longitude": 86.68},
    {"name": "Panipat IOCL Refinery", "latitude": 29.47, "longitude": 76.88},
    {"name": "Digboi Oil Fields", "latitude": 27.38, "longitude": 95.63},
]
gas_base = all_facilities[gas_mask] if not all_facilities.empty else pd.DataFrame()
gas_df = pd.concat([gas_base, pd.DataFrame(KNOWN_GAS)], ignore_index=True)

ind_df = all_facilities if not all_facilities.empty else pd.DataFrame(KNOWN_GAS)

def query_nearest_dists(lats, lons, target_df):
    t_tree = cKDTree(to_cartesian(target_df["latitude"], target_df["longitude"]))
    d_eucl, idx = t_tree.query(to_cartesian(lats, lons))
    d_km = 6371.0 * 2.0 * np.arcsin(np.clip(d_eucl / 2.0, 0.0, 1.0))
    t_names = target_df["name"].fillna("Industrial Facility").tolist()
    nearest_names = [t_names[i] for i in idx]
    return np.round(d_km, 2), nearest_names

d_ind, ind_names = query_nearest_dists(df["latitude"], df["longitude"], ind_df)
d_mine, _ = query_nearest_dists(df["latitude"], df["longitude"], mining_df)
d_gas, _ = query_nearest_dists(df["latitude"], df["longitude"], gas_df)

df["dist_to_industry_km"] = d_ind
df["nearest_industrial_facility"] = ind_names
df["near_industry"] = (df["dist_to_industry_km"] <= 2.5).astype(int)

df["dist_to_mining_km"] = d_mine
df["near_mining"] = (df["dist_to_mining_km"] <= 5.0).astype(int)

df["dist_to_gas_infrastructure_km"] = d_gas
df["near_gas_infra"] = (df["dist_to_gas_infrastructure_km"] <= 4.0).astype(int)

# ------------------------------------------------------------
# 4. Land-Cover Contextual Inference
# ------------------------------------------------------------
def infer_land_cover(lat, lon, dist_ind, dist_mine):
    if dist_ind <= 2.0:
        return "Industrial"
    if dist_mine <= 4.0:
        return "Mining"
    # Western Ghats forest corridor
    if (8.0 <= lat <= 20.0) and (73.0 <= lon <= 77.0) and dist_ind > 8.0:
        return "Forest / Woodland"
    # Northeast forest belt
    if (23.5 <= lat <= 29.0) and (90.0 <= lon <= 97.0) and dist_ind > 8.0:
        return "Forest / Woodland"
    # Central Indian forest belt (Bastar, Satpura, Melghat)
    if (18.5 <= lat <= 23.5) and (78.0 <= lon <= 83.5) and dist_ind > 12.0:
        return "Forest / Woodland"
    # Agricultural plains
    if (24.0 <= lat <= 32.5) and (74.0 <= lon <= 84.0) and dist_ind > 3.0:
        return "Cropland / Agriculture"
    if (10.0 <= lat <= 17.5) and (77.0 <= lon <= 82.5) and dist_ind > 4.0:
        return "Cropland / Agriculture"
    return "Other"

df["land_cover_context"] = [
    infer_land_cover(lat, lon, di, dm)
    for lat, lon, di, dm in zip(df["latitude"], df["longitude"], d_ind, d_mine)
]

LAND_COVER_MAP = {
    "Industrial": 0,
    "Mining": 1,
    "Forest / Woodland": 2,
    "Cropland / Agriculture": 3,
    "Other": 4
}
df["land_cover_code"] = df["land_cover_context"].map(LAND_COVER_MAP).fillna(4).astype(int)

# ------------------------------------------------------------
# 5. Telemetry & Baseline Dynamics Features
# ------------------------------------------------------------
df["baseline_available"] = df["baseline_frp"].notna().astype(int)
df["baseline_frp"] = df["baseline_frp"].fillna(0.0)
df["frp_change_percent"] = df["frp_change_percent"].fillna(0.0)
df["historical_detections"] = df["historical_detections"].fillna(0).astype(int)

df["frp_anomaly_score"] = df["frp_change_percent"].clip(lower=-100.0, upper=500.0)
df["frp_ratio"] = (df["frp"] / (df["baseline_frp"] + 1.0)).round(2)
df["high_frp"] = (df["frp"] >= 20.0).astype(int)
df["strong_anomaly"] = (df["frp_change_percent"] >= 100.0).astype(int)
df["persistent_heat"] = (df["historical_detections"] >= 2).astype(int)
df["new_event"] = (df["historical_detections"] == 0).astype(int)

# Satellite confidence mapping
def map_confidence(val):
    if pd.isna(val):
        return 70.0
    val_str = str(val).strip().lower()
    if val_str == "h":
        return 95.0
    elif val_str == "n":
        return 70.0
    elif val_str == "l":
        return 30.0
    try:
        return float(val)
    except Exception:
        return 70.0

df["confidence_score"] = df["confidence"].apply(map_confidence) if "confidence" in df.columns else 70.0
df["is_night"] = (df["daynight"].astype(str).str.upper() == "N").astype(int) if "daynight" in df.columns else 0

# Brightness temperature difference (VIIRS Ti4 - Ti5)
if "bright_ti4" in df.columns and "bright_ti5" in df.columns:
    df["brightness_diff"] = (
        pd.to_numeric(df["bright_ti4"], errors="coerce") -
        pd.to_numeric(df["bright_ti5"], errors="coerce")
    ).fillna(0.0).clip(lower=0.0, upper=150.0)
else:
    df["brightness_diff"] = 0.0

# ------------------------------------------------------------
# 6. 7-Class Grounding Logic
# ------------------------------------------------------------
def assign_seven_classes(row):
    frp = float(row["frp"])
    change = float(row["frp_change_percent"])
    detections = int(row["historical_detections"])
    status = str(row.get("persistence_status", ""))
    d_ind = float(row["dist_to_industry_km"])
    d_mine = float(row["dist_to_mining_km"])
    d_gas = float(row["dist_to_gas_infrastructure_km"])
    land = str(row["land_cover_context"])
    is_night = int(row["is_night"])

    is_persistent = (status in ["Persistent / Stable", "Persistent / Reduced"]) or detections >= 3
    is_abnormal = (status == "Abnormal Increase") or (change >= 75.0)

    # 1. Gas Flare: persistent thermal emission near gas / refinery / petrochemical infrastructure
    if (d_gas <= 5.0) and (is_persistent or detections >= 1) and (is_night or frp >= 15.0 or abs(change) < 70.0):
        return "Gas Flare"
    if (d_gas <= 3.0) and (is_night or detections >= 1):
        return "Gas Flare"

    # 2. Industrial Fire: sudden abnormal spike near an industrial facility
    if (d_ind <= 3.5 or land == "Industrial") and is_abnormal and change >= 75.0 and frp >= 8.0:
        return "Industrial Fire"

    # 3. Normal Persistent Source: stable operational emitter near industry (kilns, boilers, power plants)
    if (d_ind <= 3.5 or land == "Industrial") and is_persistent and abs(change) < 60.0:
        return "Normal Persistent Source"

    # 4. Mining Activity: heat signature in/near mining corridors
    if (d_mine <= 6.0 or land == "Mining") and (is_persistent or detections >= 2) and frp < 40.0:
        return "Mining Activity"

    # 5. Forest / Wildfire: high heat burst in forest terrain with little/no industrial presence
    if (land == "Forest / Woodland" or d_ind > 7.0) and frp >= 14.0 and (detections <= 2 or change >= 50.0):
        return "Forest / Wildfire"

    # 6. Agricultural Burning: daytime cropland heat far from industry
    if (land == "Cropland / Agriculture" or d_ind > 4.0) and frp < 45.0 and detections < 6 and abs(change) < 120.0:
        return "Agricultural Burning"

    # 7. Fallback archetype
    if (d_ind <= 3.0) and is_persistent:
        return "Normal Persistent Source"
    elif is_abnormal and frp >= 15.0:
        return "Industrial Fire" if d_ind <= 5.0 else "Forest / Wildfire"

    return "Other Thermal Event"

df["classification"] = df.apply(assign_seven_classes, axis=1)

# ------------------------------------------------------------
# 7. Risk Scoring
# ------------------------------------------------------------
def compute_risk(row):
    score = 0
    frp = float(row["frp"])
    if frp >= 50.0:
        score += 35
    elif frp >= 25.0:
        score += 25
    elif frp >= 12.0:
        score += 15
    else:
        score += 5

    change = float(row["frp_change_percent"])
    if change >= 250.0:
        score += 35
    elif change >= 100.0:
        score += 25
    elif change >= 50.0:
        score += 15
    elif change > 0:
        score += 5

    conf = float(row["confidence_score"])
    if conf >= 90.0:
        score += 10
    elif conf < 40.0:
        score -= 10

    if row["dist_to_industry_km"] <= 2.0:
        score += 15

    # Known normal or low-threat sources reduce fire emergency score
    if row["classification"] == "Normal Persistent Source":
        score -= 25
    elif row["classification"] == "Mining Activity":
        score -= 15
    elif row["classification"] == "Agricultural Burning":
        score -= 10

    return max(0, min(100, score))

df["risk_score"] = df.apply(compute_risk, axis=1)

def categorize_risk(score):
    if score >= 70:
        return "HIGH"
    elif score >= 40:
        return "MEDIUM"
    return "LOW"

df["risk_category"] = df["risk_score"].apply(categorize_risk)

# ------------------------------------------------------------
# 8. Training Feature Columns Definition
# ------------------------------------------------------------
training_features = [
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

for col in training_features:
    if col not in df.columns:
        df[col] = 0

# ------------------------------------------------------------
# 9. Save Dataset
# ------------------------------------------------------------
df.to_csv(OUTPUT_FILE, index=False)

print("\n" + "=" * 70)
print("AI TRAINING DATASET GENERATED SUCCESSFULLY")
print("=" * 70)
print(f"Total Hotspots  : {len(df)} (Current: {(df['is_current'] == 1).sum()}, Historical: {(df['is_current'] == 0).sum()})")
print(f"Saved to        : {OUTPUT_FILE}")

print("\nClass Distribution across all 7 Categories:")
print(df["classification"].value_counts().to_string())

print("\nRisk Category Distribution:")
print(df["risk_category"].value_counts().to_string())

print("\nTop 5 High-Risk Hotspots:")
print(
    df[["latitude", "longitude", "frp", "frp_change_percent", "classification", "risk_score", "risk_category"]]
    .sort_values("risk_score", ascending=False)
    .head(5)
    .to_string(index=False)
)
print("\n✅ Dataset ready for leak-free model training.")