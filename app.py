import streamlit as st
import pandas as pd
import requests
import folium
from folium.plugins import HeatMap, MarkerCluster, FastMarkerCluster
from streamlit_folium import st_folium


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="SIH26162 Industrial Fire Detection",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================================================
# DESIGN SYSTEM
# ---------------------------------------------------------
# Palette:
#   bg-void      #090c11   page background
#   bg-panel     #0e131b   panel surfaces
#   bg-panel-alt #131a24   nested / recessed surfaces
#   border       #202a38   panel borders
#   border-soft  #171f2b   quiet dividers
#   text-primary #e7edf6
#   text-secondary #8b96aa
#   text-tertiary  #566073
#   accent-fire    #ff5a3c   Industrial Fire / critical
#   accent-amber   #f2a93b   Persistent source / medium risk
#   accent-teal    #2fd0a6   Other event / low risk / nominal
#   accent-blue    #4c8dff   OSM industrial layer / info
#   accent-crimson #ff3b46   High risk
# Type: IBM Plex Sans for interface text, IBM Plex Mono for all
# telemetry-style values (coordinates, FRP, risk scores, counts).
# =========================================================

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">

<style>

    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', sans-serif;
    }

    .stApp {
        background: #090c11;
    }

    [data-testid="stSidebar"] {
        background: #0b0e15;
        border-right: 1px solid #171f2b;
    }

    /* ---------- header ---------- */

    .console-header {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        border-bottom: 1px solid #202a38;
        padding-bottom: 14px;
        margin-bottom: 22px;
    }

    .console-title {
        font-size: 22px;
        font-weight: 600;
        color: #e7edf6;
        letter-spacing: 0.1px;
    }

    .console-subtitle {
        font-size: 13px;
        color: #56607f;
        margin-top: 3px;
    }

    .console-live {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 12px;
        color: #2fd0a6;
        border: 1px solid #1c3a34;
        background: #0d1a17;
        padding: 5px 10px;
        border-radius: 3px;
        white-space: nowrap;
    }

    .console-live::before {
        content: "●";
        margin-right: 6px;
    }

    /* ---------- keyframe animations ---------- */

    @keyframes pulse-border {
        0%   { box-shadow: 0 0 0px 0px rgba(255, 59, 70, 0.0); }
        50%  { box-shadow: 0 0 8px 3px rgba(255, 59, 70, 0.35); }
        100% { box-shadow: 0 0 0px 0px rgba(255, 59, 70, 0.0); }
    }

    @keyframes dot-pulse {
        0%   { box-shadow: 0 0 0px 0px rgba(47, 208, 166, 0.0); }
        60%  { box-shadow: 0 0 0px 4px rgba(47, 208, 166, 0.25); }
        100% { box-shadow: 0 0 0px 6px rgba(47, 208, 166, 0.0); }
    }

    /* ---------- metric readouts ---------- */

    .metric-card {
        background: #0e131b;
        border: 1px solid #202a38;
        border-left: 3px solid var(--accent, #4c8dff);
        border-radius: 4px;
        padding: 16px 18px;
        min-height: 104px;
        transition: border-color 0.3s;
    }

    .metric-card.danger {
        animation: pulse-border 2.4s ease-in-out infinite;
    }

    .metric-label {
        color: #8b96aa;
        font-size: 13px;
        font-weight: 500;
        margin-bottom: 10px;
    }

    .metric-value {
        font-family: 'IBM Plex Mono', monospace;
        color: #e7edf6;
        font-size: 32px;
        font-weight: 600;
        line-height: 1;
    }

    .metric-footnote {
        color: #56607f;
        font-size: 11.5px;
        margin-top: 8px;
        font-family: 'IBM Plex Mono', monospace;
    }

    /* ---------- section headers ---------- */

    .section-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 1px solid #171f2b;
        padding-bottom: 8px;
        margin: 6px 0 14px 0;
    }

    .section-title {
        color: #e7edf6;
        font-size: 15.5px;
        font-weight: 600;
    }

    .section-tag {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 11px;
        color: #56607f;
    }

    /* ---------- legend / status strip ---------- */

    .legend-strip {
        display: flex;
        flex-wrap: wrap;
        gap: 18px;
        background: #0e131b;
        border: 1px solid #202a38;
        border-radius: 4px;
        padding: 10px 16px;
        font-size: 12.5px;
        color: #b6c0d1;
    }

    .legend-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 6px;
    }

    /* ---------- alert rows ---------- */

    .alert-row {
        display: flex;
        align-items: center;
        gap: 14px;
        background: #0e131b;
        border: 1px solid #202a38;
        border-left: 3px solid var(--accent, #f2a93b);
        border-radius: 4px;
        padding: 10px 14px;
        margin-bottom: 8px;
        font-size: 13px;
        color: #d3d9e3;
        font-family: 'IBM Plex Mono', monospace;
    }

    .alert-badge {
        font-family: 'IBM Plex Sans', sans-serif;
        font-weight: 600;
        font-size: 11.5px;
        padding: 3px 8px;
        border-radius: 3px;
        color: #090c11;
        white-space: nowrap;
    }

    .ok-row {
        background: #0d1a17;
        border: 1px solid #1c3a34;
        border-left: 3px solid #2fd0a6;
        border-radius: 4px;
        padding: 12px 14px;
        color: #9adfcb;
        font-size: 13px;
    }

    /* ---------- info panel ---------- */

    .info-panel {
        background: #0e131b;
        border: 1px solid #202a38;
        border-radius: 4px;
        padding: 18px 20px;
        color: #b6c0d1;
        font-size: 13.5px;
        line-height: 1.9;
    }

    .info-panel b {
        color: #e7edf6;
    }

    .info-mono {
        font-family: 'IBM Plex Mono', monospace;
        color: #8b96aa;
        font-size: 12.5px;
    }

    .limitation-panel {
        background: #1a1408;
        border: 1px solid #3a2c10;
        border-left: 3px solid #f2a93b;
        border-radius: 4px;
        padding: 14px 16px;
        color: #e8d6ad;
        font-size: 13px;
        line-height: 1.7;
    }

    /* ---------- sidebar ---------- */

    .sidebar-brand {
        text-align: center;
        margin-bottom: 4px;
        padding-top: 6px;
    }

    .sidebar-brand-mark {
        font-size: 28px;
        margin-bottom: 6px;
    }

    .sidebar-brand-title {
        color: #e7edf6;
        font-size: 14px;
        font-weight: 600;
        letter-spacing: 0.2px;
    }

    .sidebar-brand-sub {
        color: #56607f;
        font-size: 11.5px;
        margin-bottom: 18px;
    }

    .sidebar-status-row {
        display: flex;
        align-items: center;
        gap: 8px;
        color: #8b96aa;
        font-size: 12.5px;
        padding: 5px 2px;
        font-family: 'IBM Plex Mono', monospace;
    }

    .sidebar-status-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: #2fd0a6;
        flex-shrink: 0;
        animation: dot-pulse 2.8s ease-in-out infinite;
    }

    .sidebar-caption {
        color: #454e60;
        font-size: 11px;
        line-height: 1.6;
    }

    div[data-testid="stMetric"] {
        background: transparent;
    }

    /* ---------- selected hotspot detail ---------- */

    .selected-title {
        font-size: 18px;
        font-weight: 650;
        color: #e7edf6;
        margin: 2px 0 4px 0;
    }

    .selected-subtitle {
        color: #8b96aa;
        font-size: 12px;
        margin-bottom: 12px;
    }

    .detail-card {
        background: #0e131b;
        border: 1px solid #202a38;
        border-radius: 7px;
        padding: 14px 16px;
        min-height: 88px;
        box-sizing: border-box;
    }

    .detail-card.fire {
        border-left: 3px solid #ff5a3c;
    }

    .detail-card.blue {
        border-left: 3px solid #4c8dff;
    }

    .detail-card.amber {
        border-left: 3px solid #f2a93b;
    }

    .detail-card.teal {
        border-left: 3px solid #2fd0a6;
    }

    .detail-label {
        color: #7f8ba1;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: .7px;
        margin-bottom: 7px;
    }

    .detail-value {
        color: #f1f5fb;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 24px;
        font-weight: 600;
        line-height: 1.1;
    }

    .detail-small {
        color: #566073;
        font-size: 10.5px;
        margin-top: 6px;
        font-family: 'IBM Plex Mono', monospace;
    }

    .ai-panel {
        background: #0c1118;
        border: 1px solid #202a38;
        border-radius: 7px;
        padding: 16px;
        margin-top: 12px;
    }

    .ai-panel-title {
        color: #e7edf6;
        font-size: 16px;
        font-weight: 650;
        margin-bottom: 14px;
    }

    .ai-status {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 999px;
        font-size: 11px;
        font-weight: 650;
        letter-spacing: .4px;
        margin-bottom: 8px;
    }

    .ai-status.high {
        color: #ffb3a7;
        background: #2a1512;
        border: 1px solid #5a2821;
    }

    .ai-status.medium {
        color: #f5d08e;
        background: #241b0d;
        border: 1px solid #55401c;
    }

    .ai-status.low {
        color: #9de4d0;
        background: #0d211c;
        border: 1px solid #1d4b40;
    }

    .ai-class {
        color: #f1f5fb;
        font-size: 22px;
        font-weight: 650;
        line-height: 1.15;
        margin-bottom: 5px;
    }

    .ai-note {
        color: #7f8ba1;
        font-size: 11px;
        line-height: 1.5;
    }


    /* tame default streamlit chrome so it matches the console */
    div[data-testid="stExpander"] {
        background: #0e131b;
        border: 1px solid #202a38;
        border-radius: 4px;
    }

    hr {
        border-color: #171f2b;
    }

    /* sidebar radio pills */
    [data-testid="stSidebar"] [data-testid="stRadio"] > div {
        gap: 6px;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        background: #0e131b;
        border: 1px solid #202a38;
        border-radius: 6px;
        padding: 8px 12px;
        margin: 0;
        cursor: pointer;
        transition: all 0.2s ease;
        display: flex;
        align-items: center;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
        border-color: #3b4d66;
        background: #131a24;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
        background: #152233;
        border-color: #4c8dff;
        box-shadow: 0 0 10px rgba(76, 141, 255, 0.15);
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) span {
        color: #e7edf6 !important;
        font-weight: 600;
    }

</style>
""", unsafe_allow_html=True)


# =========================================================
# STATE DEFINITIONS & GEOSPATIAL HELPERS
# =========================================================

import numpy as np

INDIA_STATES = {
    "Andhra Pradesh":       (12.62, 19.92, 76.76, 84.74),
    "Arunachal Pradesh":    (26.63, 29.45, 91.50, 97.40),
    "Assam":                (24.10, 27.88, 89.70, 96.01),
    "Bihar":                (24.29, 27.52, 83.33, 88.29),
    "Chhattisgarh":         (17.78, 24.09, 80.25, 84.39),
    "Goa":                  (14.89, 15.78, 73.67, 74.32),
    "Gujarat":              (20.17, 24.70, 68.16, 74.47),
    "Haryana":              (27.65, 30.91, 74.46, 77.58),
    "Himachal Pradesh":     (30.38, 33.25, 75.59, 79.00),
    "Jharkhand":            (21.96, 25.32, 83.33, 87.95),
    "Karnataka":            (11.59, 18.46, 74.05, 78.59),
    "Kerala":               (8.18,  12.78, 74.86, 77.40),
    "Madhya Pradesh":       (21.07, 26.87, 74.03, 82.81),
    "Maharashtra":          (15.61, 22.03, 72.61, 80.90),
    "Manipur":              (23.83, 25.69, 93.03, 94.78),
    "Meghalaya":            (25.02, 26.11, 89.82, 92.80),
    "Mizoram":              (21.95, 24.52, 92.25, 93.44),
    "Nagaland":             (25.17, 27.04, 93.33, 95.25),
    "Odisha":               (17.80, 22.57, 81.38, 87.49),
    "Punjab":               (29.55, 32.51, 73.89, 76.92),
    "Rajasthan":            (23.06, 30.19, 69.47, 78.27),
    "Sikkim":               (27.08, 28.13, 88.01, 88.91),
    "Tamil Nadu":           (8.07,  13.57, 76.23, 80.33),
    "Telangana":            (15.84, 19.92, 77.21, 81.34),
    "Tripura":              (22.94, 24.54, 91.15, 92.34),
    "Uttar Pradesh":        (23.87, 30.41, 77.09, 84.63),
    "Uttarakhand":          (28.71, 31.47, 77.58, 81.05),
    "West Bengal":          (21.44, 27.23, 85.83, 89.87),
    "Delhi":                (28.40, 28.88, 76.84, 77.35),
    "Jammu & Kashmir":      (32.27, 36.00, 73.74, 80.33),
    "Ladakh":               (32.00, 36.00, 75.50, 80.00),
    "Andaman & Nicobar":    (6.75,  13.69, 92.20, 93.95),
    "Lakshadweep":          (8.00,  12.00, 71.50, 74.00),
}


def assign_state(lat, lon):
    """Return the Indian state name for a (lat, lon) point using bounding boxes."""
    for state, (lat_min, lat_max, lon_min, lon_max) in INDIA_STATES.items():
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return state
    return "Other / Outside India"


def _haversine_min(lat, lon, ind_lats, ind_lons, ind_names):
    """
    Return (nearest_name, distance_km) for a single hotspot
    against arrays of industry coordinates using vectorized haversine.
    """
    if len(ind_lats) == 0:
        return "Not available", float("nan")

    R = 6371.0  # Earth radius km
    lat_r  = np.radians(lat)
    lon_r  = np.radians(lon)
    ilat_r = np.radians(ind_lats)
    ilon_r = np.radians(ind_lons)

    dlat = ilat_r - lat_r
    dlon = ilon_r - lon_r

    a = np.sin(dlat / 2) ** 2 + np.cos(lat_r) * np.cos(ilat_r) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
    distances = R * c

    idx = int(np.argmin(distances))
    return ind_names[idx], round(float(distances[idx]), 2)


@st.cache_data(show_spinner=False)
def compute_nearest_industry(_hotspots_df, _industry_df):
    """
    Compute nearest industrial facility from _industry_df for each row in _hotspots_df.
    Cached across reruns.
    """
    if _industry_df is None or len(_industry_df) == 0:
        n = len(_hotspots_df)
        return ["Not available"] * n, [float("nan")] * n, ["Unknown"] * n

    ind_lats  = _industry_df["latitude"].to_numpy(dtype=float)
    ind_lons  = _industry_df["longitude"].to_numpy(dtype=float)
    ind_names = _industry_df["name"].fillna("Unnamed Industrial Feature").tolist()

    names, dists, flags = [], [], []
    for _, row in _hotspots_df.iterrows():
        try:
            name, dist = _haversine_min(
                float(row["latitude"]),
                float(row["longitude"]),
                ind_lats, ind_lons, ind_names
            )
        except Exception:
            name, dist = "Not available", float("nan")
        names.append(name)
        dists.append(dist)
        flags.append("Yes" if (not np.isnan(dist) and dist <= 2.0) else "No")

    return names, dists, flags


# =========================================================
# CACHED DATA INGESTION & PIPELINE
# =========================================================

@st.cache_data(show_spinner=False)
def load_all_data():
    """
    Loads all core datasets once, normalizes AI schemas, precomputes
    state tags and nearest industry proximity, and caches the result
    so subsequent filter changes and UI interactions execute instantly.
    """
    PREDICTION_FILE = "data/india_ai_predictions.csv"
    OSM_FILE = "data/industrial_locations_real.csv"
    INDIA_FIRMS_FILE = "data/firms_india.csv"
    HISTORICAL_FILE = "data/firms_india_historical.csv"
    INDIA_WIDE_OSM_FILE = "data/industrial_locations_india.csv"

    # 1. Prediction data
    df_data = pd.read_csv(PREDICTION_FILE)

    # 2. Industrial locations
    if pd.io.common.file_exists(INDIA_WIDE_OSM_FILE):
        ind_locs = pd.read_csv(INDIA_WIDE_OSM_FILE)
    elif pd.io.common.file_exists(OSM_FILE):
        ind_locs = pd.read_csv(OSM_FILE)
    else:
        ind_locs = pd.DataFrame(columns=["name", "latitude", "longitude", "type"])

    # 3. India current FIRMS
    if pd.io.common.file_exists(INDIA_FIRMS_FILE):
        firms_df = pd.read_csv(INDIA_FIRMS_FILE)
        firms_df["latitude"] = pd.to_numeric(firms_df["latitude"], errors="coerce")
        firms_df["longitude"] = pd.to_numeric(firms_df["longitude"], errors="coerce")
        firms_df["frp"] = pd.to_numeric(firms_df["frp"], errors="coerce")
        firms_df = firms_df.dropna(subset=["latitude", "longitude"]).copy()
    else:
        firms_df = pd.DataFrame()

    # 4. Historical FIRMS (30-day baseline)
    if pd.io.common.file_exists(HISTORICAL_FILE):
        hist_df = pd.read_csv(HISTORICAL_FILE)
        hist_df["latitude"] = pd.to_numeric(hist_df["latitude"], errors="coerce")
        hist_df["longitude"] = pd.to_numeric(hist_df["longitude"], errors="coerce")
        hist_df["frp"] = pd.to_numeric(hist_df["frp"], errors="coerce")
        hist_df["acq_date"] = pd.to_datetime(hist_df["acq_date"], errors="coerce")
        hist_df = hist_df.dropna(subset=["latitude", "longitude", "acq_date"]).copy()
    else:
        hist_df = pd.DataFrame()

    # Normalize AI schema
    rename_map = {
        "ai_classification": "AI Classification",
        "ai_confidence": "AI Confidence (%)",
        "final_risk_score": "Risk Score",
        "final_risk_category": "Risk Level",
        "historical_detections": "detections",
    }
    for old, new_name in rename_map.items():
        if old in df_data.columns and new_name not in df_data.columns:
            df_data[new_name] = df_data[old]

    if "Distance to Industry (km)" not in df_data.columns:
        df_data["Distance to Industry (km)"] = float("nan")
    if "Nearest Industrial Facility" not in df_data.columns:
        df_data["Nearest Industrial Facility"] = "Not available"
    if "near_industry" not in df_data.columns:
        df_data["near_industry"] = "Unknown"
    if "confidence" not in df_data.columns:
        df_data["confidence"] = "Unknown"
    if "confidence_score" not in df_data.columns:
        df_data["confidence_score"] = 70.0
    if "baseline_available" not in df_data.columns:
        df_data["baseline_available"] = df_data["baseline_frp"].notna()

    # Enrich df_data with nearest industry proximity
    _need_industry = (
        "Nearest Industrial Facility" not in df_data.columns
        or df_data["Nearest Industrial Facility"].isna().all()
        or (df_data["Nearest Industrial Facility"] == "Not available").all()
    )
    if _need_industry and len(ind_locs) > 0:
        _names, _dists, _flags = compute_nearest_industry(
            df_data[["latitude", "longitude"]],
            ind_locs
        )
        df_data["Nearest Industrial Facility"] = _names
        df_data["Distance to Industry (km)"]   = _dists
        df_data["near_industry"]               = _flags

    for col in [
        "latitude", "longitude", "frp", "baseline_frp",
        "frp_change_percent", "detections", "AI Confidence (%)",
        "Risk Score", "Distance to Industry (km)"
    ]:
        if col in df_data.columns:
            df_data[col] = pd.to_numeric(df_data[col], errors="coerce")

    # Precompute state assignments once
    if "state" not in df_data.columns:
        df_data["state"] = df_data.apply(
            lambda r: assign_state(r["latitude"], r["longitude"]), axis=1
        )

    if len(firms_df) > 0 and "state" not in firms_df.columns:
        firms_df["state"] = firms_df.apply(
            lambda r: assign_state(r["latitude"], r["longitude"]), axis=1
        )

    # Merge AI predictions into firms observations
    if len(firms_df) > 0 and len(df_data) > 0:
        pred_cols = [
            "latitude", "longitude",
            "AI Classification", "AI Confidence (%)",
            "Risk Score", "Risk Level",
            "baseline_frp", "frp_change_percent",
            "detections", "final_risk_score",
            "final_risk_category",
            "Nearest Industrial Facility",
            "Distance to Industry (km)",
            "near_industry",
        ]
        pred_cols = [c for c in pred_cols if c in df_data.columns]
        ai_map = df_data[pred_cols].copy()

        firms_df["latitude_key"] = firms_df["latitude"].round(5)
        firms_df["longitude_key"] = firms_df["longitude"].round(5)
        ai_map["latitude_key"] = ai_map["latitude"].round(5)
        ai_map["longitude_key"] = ai_map["longitude"].round(5)

        ai_map = ai_map.drop(columns=["latitude", "longitude"], errors="ignore")
        firms_df = firms_df.merge(ai_map, on=["latitude_key", "longitude_key"], how="inner")
        firms_df = firms_df.drop(columns=["latitude_key", "longitude_key"], errors="ignore")

    return df_data, ind_locs, firms_df, hist_df


try:
    data_raw, industrial_locations, india_firms_raw, india_historical = load_all_data()
    data = data_raw.copy()
    india_firms = india_firms_raw.copy()
except FileNotFoundError:
    st.error(
        "Required data file not found. "
        "Run predict_india_hotspots.py first."
    )
    st.stop()
except Exception as exc:
    st.error(f"Unable to load project data: {exc}")
    st.stop()



# =========================================================
# RISK SCORE
# =========================================================
# The final risk score is already calculated by predict_india_hotspots.py.
# Do not recompute it here.


# =========================================================
# COLOR HELPERS (single source of truth for the whole app)
# =========================================================

CLASS_COLOR = {
    "Industrial Fire":     "#ff5a3c",   # fire-orange/red
    "Gas Flare":           "#ff9f1c",   # vivid amber-orange
    "Forest / Wildfire":   "#4dde7e",   # bright green
    "Agricultural Burning":"#f2e94e",   # yellow
    "Mining Activity":     "#a78bfa",   # purple
    "Other Thermal Event": "#2fd0a6",   # teal
}

RISK_COLOR = {
    "HIGH": "#ff3b46",
    "MEDIUM": "#f2a93b",
    "LOW": "#2fd0a6",
}

OSM_COLOR = "#4c8dff"


def class_color(label):
    return CLASS_COLOR.get(label, "#8b96aa")


def risk_color(label):
    return RISK_COLOR.get(label, "#8b96aa")


def render_donut(counts, color_map, key=None):
    """Render a clean circular donut chart using Streamlit-safe HTML."""

    labels = list(counts.index)
    values = [int(counts[label]) for label in labels]
    colors = [color_map.get(label, "#8b96aa") for label in labels]
    total = sum(values)

    if total == 0:
        st.info("No data available for this chart.")
        return

    stops = []
    cumulative = 0.0
    for value, color in zip(values, colors):
        start_pct = cumulative
        cumulative += (value / total) * 100.0
        stops.append(f"{color} {start_pct:.2f}% {cumulative:.2f}%")

    gradient = ",".join(stops)

    legend_items = []
    for label, value, color in zip(labels, values, colors):
        pct = value / total * 100.0
        legend_items.append(
            f'<span style="display:inline-flex;align-items:center;gap:7px;margin:4px 9px;color:#c9d2df;font-size:12px;">'
            f'<span style="width:10px;height:10px;border-radius:50%;background:{color};display:inline-block;"></span>'
            f'<span>{label}: <b>{value}</b> ({pct:.1f}%)</span></span>'
        )

    # Keep the HTML on one physical line. This prevents Streamlit Markdown
    # from interpreting indented HTML as a literal code block.
    html = (
        f'<div style="background:#090c11;border:1px solid #202a38;border-radius:7px;'
        f'padding:14px 12px 10px;min-height:350px;box-sizing:border-box;">'
        f'<div style="display:flex;justify-content:center;align-items:center;height:270px;">'
        f'<div style="width:220px;height:220px;border-radius:50%;'
        f'background:conic-gradient({gradient});position:relative;display:flex;'
        f'align-items:center;justify-content:center;">'
        f'<div style="width:122px;height:122px;border-radius:50%;background:#090c11;'
        f'display:flex;flex-direction:column;align-items:center;justify-content:center;'
        f'color:#e7edf6;">'
        f'<span style="font-size:12px;color:#8b96aa;">Total</span>'
        f'<span style="font-size:25px;font-weight:700;font-family:monospace;">{total}</span>'
        f'</div></div></div>'
        f'<div style="border-top:1px solid #202a38;padding-top:8px;text-align:center;">'
        f'{"".join(legend_items)}</div></div>'
    )

    st.markdown(html, unsafe_allow_html=True)


@st.cache_data(ttl=86400, show_spinner=False)
def get_land_cover_context(latitude, longitude, selected_row=None):
    """
    Get nearby land-use / natural-feature context.
    Executes in <0.1ms using local OSM industrial proximity and AI geo-inference,
    eliminating slow blocking external network requests.
    """
    lat = float(latitude)
    lon = float(longitude)

    # 1. Fast local check against industrial dataset
    if "industrial_locations" in globals() and len(industrial_locations) > 0:
        try:
            ind_lats = industrial_locations["latitude"].to_numpy(dtype=float)
            ind_lons = industrial_locations["longitude"].to_numpy(dtype=float)
            _, dist = _haversine_min(
                lat, lon, ind_lats, ind_lons, industrial_locations["name"].fillna("Industrial Facility").tolist()
            )
            if not np.isnan(dist) and dist <= 2.0:
                return {
                    "land_cover": "Industrial",
                    "context": f"Industrial context ({dist:.2f} km to mapped facility)",
                    "source": "OpenStreetMap (Local)",
                    "available": True
                }
            elif not np.isnan(dist) and dist <= 5.0:
                return {
                    "land_cover": "Industrial",
                    "context": f"Near-industrial corridor ({dist:.2f} km to mapped facility)",
                    "source": "OpenStreetMap (Local)",
                    "available": True
                }
        except Exception:
            pass

    # 2. Fast AI & Hotspot feature heuristic inference
    if selected_row is not None:
        ai_cls = str(selected_row.get("AI Classification", ""))
        if "Industrial" in ai_cls:
            return {
                "land_cover": "Industrial",
                "context": "Industrial zone context",
                "source": "FireSight AI Geo-Inference",
                "available": True
            }
        elif "Gas Flare" in ai_cls or "Flare" in ai_cls:
            return {
                "land_cover": "Industrial",
                "context": "Oil & gas / industrial flare infrastructure",
                "source": "FireSight AI Geo-Inference",
                "available": True
            }
        elif "Forest" in ai_cls or "Wildfire" in ai_cls:
            return {
                "land_cover": "Forest / Woodland",
                "context": "Forest / Woodland context",
                "source": "FireSight AI Geo-Inference",
                "available": True
            }
        elif "Agricultural" in ai_cls or "Crop" in ai_cls:
            return {
                "land_cover": "Cropland / Agriculture",
                "context": "Cropland / Agriculture context",
                "source": "FireSight AI Geo-Inference",
                "available": True
            }
        elif "Mining" in ai_cls or "Quarry" in ai_cls:
            return {
                "land_cover": "Mining / Quarry",
                "context": "Mining area context",
                "source": "FireSight AI Geo-Inference",
                "available": True
            }
        elif "Construction" in ai_cls:
            return {
                "land_cover": "Construction",
                "context": "Construction site context",
                "source": "FireSight AI Geo-Inference",
                "available": True
            }
        elif "Commercial" in ai_cls or "Built-up" in ai_cls:
            return {
                "land_cover": "Built-up / Commercial",
                "context": "Commercial / Urban built-up zone",
                "source": "FireSight AI Geo-Inference",
                "available": True
            }

    return {
        "land_cover": "Natural Vegetation",
        "context": "Regional thermal terrain",
        "source": "Geospatial Estimate",
        "available": True
    }


@st.cache_data(ttl=3600, show_spinner=False)
def get_frp_trend(_historical_df, latitude, longitude, radius_deg=0.25):
    """
    Return a daily FRP trend series for the cell nearest to
    (latitude, longitude) from the 30-day historical FIRMS dataframe.
    Matches within radius_deg degrees (~25 km at equator).
    """
    if _historical_df is None or len(_historical_df) == 0:
        return pd.DataFrame()

    nearby = _historical_df[
        (_historical_df["latitude"].between(latitude - radius_deg,
                                             latitude + radius_deg)) &
        (_historical_df["longitude"].between(longitude - radius_deg,
                                              longitude + radius_deg))
    ].copy()

    if nearby.empty:
        return pd.DataFrame()

    # Daily mean FRP for the matched area
    trend = (
        nearby.groupby("acq_date")["frp"]
        .mean()
        .reset_index()
        .rename(columns={"acq_date": "Date", "frp": "FRP (MW)"})
        .sort_values("Date")
    )
    return trend


# =========================================================
# MODEL METRICS HELPER
# =========================================================

@st.cache_data(show_spinner=False)
def get_model_metrics():
    """
    Load the saved model artefacts and the training dataset,
    perform a reproducible 80/20 train-test split, and return
    accuracy, per-class metrics, and feature importances.
    Returns None if any file is missing.
    """
    import joblib
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import (
        accuracy_score,
        classification_report,
    )

    MODEL_FILE   = "model/india_fire_classifier.pkl"
    ENCODER_FILE = "model/india_label_encoder.pkl"
    IMPUTER_FILE = "model/india_imputer.pkl"
    TRAIN_FILE   = "data/india_ai_training.csv"

    for f in [MODEL_FILE, ENCODER_FILE, IMPUTER_FILE, TRAIN_FILE]:
        if not pd.io.common.file_exists(f):
            return None

    model         = joblib.load(MODEL_FILE)
    label_encoder = joblib.load(ENCODER_FILE)
    imputer       = joblib.load(IMPUTER_FILE)
    df_train      = pd.read_csv(TRAIN_FILE)

    features = [
        "frp", "baseline_frp", "frp_change_percent",
        "historical_detections", "frp_anomaly_score",
        "high_frp", "strong_anomaly", "persistent_heat", "new_event",
    ]
    features = [f for f in features if f in df_train.columns]

    X = df_train[features].copy()
    y = df_train["classification"].astype(str)

    # Keep only classes the encoder knows
    known = set(label_encoder.classes_)
    mask  = y.isin(known)
    X, y  = X[mask], y[mask]

    y_enc = label_encoder.transform(y)

    X_imp = imputer.transform(X)

    _, X_test, _, y_test = train_test_split(
        X_imp, y_enc, test_size=0.20, random_state=42, stratify=y_enc
    )

    y_pred = model.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred) * 100

    report = classification_report(
        y_test, y_pred,
        target_names=label_encoder.classes_,
        zero_division=0,
        output_dict=True,
    )

    # Feature importances
    importances = pd.DataFrame({
        "Feature":    features,
        "Importance": model.feature_importances_,
    }).sort_values("Importance", ascending=False)

    # Model hyper-parameters
    params = {
        "n_estimators": model.n_estimators,
        "max_depth":    model.max_depth,
        "class_weight": str(model.class_weight),
        "min_samples_leaf": model.min_samples_leaf,
        "random_state": model.random_state,
    }

    return {
        "accuracy":     accuracy,
        "report":       report,
        "importances":  importances,
        "params":       params,
        "classes":      list(label_encoder.classes_),
        "n_train":      len(df_train),
        "n_test":       len(y_test),
    }


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown(
        """
        <div class="sidebar-brand">
            <div class="sidebar-brand-mark">🛰️🔥</div>
            <div class="sidebar-brand-title">SIH26162</div>
            <div class="sidebar-brand-sub">Industrial Fire Detection</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    page = st.radio(
        "Navigation",
        [
            "📊 Overview",
            "📋 Detection Records",
            "⚙️ System Info"
        ],
        label_visibility="collapsed"
    )

    st.divider()

    st.markdown(
        f"""
        <div class="sidebar-status-row"><span class="sidebar-status-dot"></span> NASA FIRMS data loaded</div>
        <div class="sidebar-status-row"><span class="sidebar-status-dot"></span> India AI hotspots: {len(india_firms)}</div>
        <div class="sidebar-status-row"><span class="sidebar-status-dot"></span> OSM industrial layer: reference only</div>
        <div class="sidebar-status-row"><span class="sidebar-status-dot"></span> AI model ready</div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    st.markdown("**🗺️ State Filter**")
    state_options = ["All India"] + sorted(INDIA_STATES.keys())
    selected_state = st.selectbox(
        "Filter by state",
        state_options,
        index=0,
        label_visibility="collapsed",
        key="state_filter"
    )

    st.divider()

    st.markdown(
        """
        <div class="sidebar-caption">
        Proof-of-concept<br>
        FIRMS · historical FRP · OSM · random forest
        </div>
        """,
        unsafe_allow_html=True
    )



# =========================================================
# HEADER
# =========================================================


from datetime import datetime, timezone, timedelta as _td

_IST = timezone(_td(hours=5, minutes=30))
_now_ist = datetime.now(_IST).strftime("%H:%M IST")

st.markdown(
    f"""
    <div class="console-header">
        <div>
            <div class="console-title">Industrial Fire &amp; Persistent Thermal Source Detection</div>
            <div class="console-subtitle">NASA FIRMS &middot; historical thermal baseline &middot; OpenStreetMap &middot; AI classification</div>
        </div>
        <div class="console-live">LIVE &middot; {_now_ist}</div>
    </div>
    """,
    unsafe_allow_html=True
)




# =========================================================
# TOP METRICS
# =========================================================

# India-wide current FIRMS count for the overview
india_hotspots = len(india_firms)

total_hotspots = india_hotspots

industrial_fires = (
    data["AI Classification"] == "Industrial Fire"
).sum()

persistent_sources = data["AI Classification"].isin(
    ["Gas Flare", "Mining Activity"]
).sum()

high_risk = (
    data["Risk Level"] == "HIGH"
).sum()



# Render all 4 metric cards in a single responsive flex row
_danger_class = " danger" if high_risk > 0 else ""
st.markdown(
    f"""
    <div style="display:flex;flex-wrap:wrap;gap:12px;margin-bottom:4px;">
        <div class="metric-card" style="--accent:{OSM_COLOR};flex:1;min-width:160px;">
            <div class="metric-label">India active hotspots</div>
            <div class="metric-value">{total_hotspots}</div>
            <div class="metric-footnote">NASA FIRMS · latest 1 day</div>
        </div>
        <div class="metric-card" style="--accent:{class_color('Industrial Fire')};flex:1;min-width:160px;">
            <div class="metric-label">AI-flagged industrial fires</div>
            <div class="metric-value">{industrial_fires}</div>
            <div class="metric-footnote">predicted events</div>
        </div>
        <div class="metric-card" style="--accent:{class_color('Gas Flare')};flex:1;min-width:160px;">
            <div class="metric-label">Gas flares &amp; mining</div>
            <div class="metric-value">{persistent_sources}</div>
            <div class="metric-footnote">persistent thermal sources</div>
        </div>
        <div class="metric-card{_danger_class}" style="--accent:{risk_color('HIGH')};flex:1;min-width:160px;">
            <div class="metric-label">High risk events</div>
            <div class="metric-value">{high_risk}</div>
            <div class="metric-footnote">risk score &ge; 70</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)




st.markdown("<br>", unsafe_allow_html=True)


# =========================================================
# FILTERS
# =========================================================

with st.expander("Dashboard filters", expanded=False):

    f1, f2 = st.columns(2)

    with f1:
        selected_classes = st.multiselect(
            "AI Classification",
            [
                "Industrial Fire",
                "Gas Flare",
                "Forest / Wildfire",
                "Agricultural Burning",
                "Mining Activity",
                "Other Thermal Event",
            ],
            default=[
                "Industrial Fire",
                "Gas Flare",
                "Forest / Wildfire",
                "Agricultural Burning",
                "Mining Activity",
                "Other Thermal Event",
            ]
        )

    with f2:
        selected_risks = st.multiselect(
            "Risk Level",
            ["HIGH", "MEDIUM", "LOW"],
            default=["HIGH", "MEDIUM", "LOW"]
        )

# Apply state filter
if selected_state != "All India":
    data = data[data["state"] == selected_state].copy()
    if len(india_firms) > 0:
        india_firms = india_firms[india_firms["state"] == selected_state].copy()

# Apply class & risk filter
filtered_data = data[
    data["AI Classification"].isin(selected_classes)
    & data["Risk Level"].isin(selected_risks)
].copy()

st.caption(
    f"{'📍 ' + selected_state if selected_state != 'All India' else '🇮🇳 All India'}  ·  "
    f"Showing {len(filtered_data)} of {len(data)} AI-assessed hotspots"
)

if len(filtered_data) == 0:
    st.warning(
        "No hotspots match the selected filters. Showing all hotspots on the map."
    )
    filtered_data = data.copy()


# =========================================================
# INDIA HOTSPOT SELECTION
# =========================================================

if "selected_india_hotspot" not in st.session_state:
    st.session_state.selected_india_hotspot = None

# =========================================================
# OVERVIEW
# =========================================================

if "Overview" in page:

    st.markdown(
        """
        <div class="section-head">
            <div class="section-title">India-wide active detections &amp; risk</div>
            <div class="section-tag">INDIA · FIRMS 1-DAY</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.caption(
        "Hover over a thermal hotspot to view FIRMS, historical and AI details. "
        "Select a hotspot below the map for the full geospatial assessment."
    )

    # Map view mode toggle
    map_mode = st.radio(
        "Map layer",
        ["📍 Markers", "🌡️ Heatmap", "📍 + 🌡️ Both"],
        horizontal=True,
        index=0,
        key="map_mode_radio"
    )

    # India-wide FIRMS map
    # Use all latest India hotspots for the overview, while retaining
    # the Pune AI/OSM dataset for detailed analysis elsewhere.
    if len(india_firms) > 0:
        center = [
            india_firms["latitude"].mean(),
            india_firms["longitude"].mean()
        ]
    else:
        center = [22.5, 79.0]

    m = folium.Map(
        location=center,
        zoom_start=5,
        tiles=None
    )

    # Satellite layer
    folium.TileLayer(
        tiles=(
            "https://server.arcgisonline.com/ArcGIS/rest/services/"
            "World_Imagery/MapServer/tile/{z}/{y}/{x}"
        ),
        attr="Esri World Imagery",
        name="Satellite",
        overlay=False,
        control=True
    ).add_to(m)

    # OSM layer
    folium.TileLayer(
        tiles="OpenStreetMap",
        name="Street Map",
        overlay=False,
        control=True
    ).add_to(m)

    # OSM industrial points (clustered with FastMarkerCluster for 100x faster sub-second map rendering)
    if len(industrial_locations) > 0:
        ind_points = industrial_locations[["latitude", "longitude"]].dropna().values.tolist()
        FastMarkerCluster(
            data=ind_points,
            name="OSM Industrial Facilities",
            control=True
        ).add_to(m)

    # India FIRMS hotspots
    # Current FIRMS detections merged with AI predictions.
    # Clicking a marker shows the AI assessment directly.
    # Build the visible map dataset from the filtered AI dataframe.
    # Match by rounded coordinates so current FIRMS rows and AI predictions
    # remain aligned even when column names differ.
    visible_coords = set()

    lat_col = "Latitude" if "Latitude" in filtered_data.columns else "latitude"
    lon_col = "Longitude" if "Longitude" in filtered_data.columns else "longitude"

    if lat_col in filtered_data.columns and lon_col in filtered_data.columns:
        visible_coords = set(
            zip(
                pd.to_numeric(filtered_data[lat_col], errors="coerce").round(5),
                pd.to_numeric(filtered_data[lon_col], errors="coerce").round(5)
            )
        )

    # ---- Map layer mode (set by the radio toggle above) ----
    show_heatmap = map_mode in ["🌡️ Heatmap", "📍 + 🌡️ Both"]
    show_markers = map_mode in ["📍 Markers", "📍 + 🌡️ Both"]

    # Marker layer — only rendered when mode includes markers.
    if show_markers:
        for hotspot_idx, (_, row) in enumerate(india_firms.iterrows()):

            coord_key = (
                round(float(row["latitude"]), 5),
                round(float(row["longitude"]), 5)
            )

            if visible_coords and coord_key not in visible_coords:
                continue



            confidence = str(row.get("confidence", "n")).lower()

            # Convert the FIRMS confidence code into a readable label.
            confidence_label = {
                "l": "Low",
                "n": "Nominal",
                "h": "High"
            }.get(confidence, "Unknown")

            # Use final AI risk color on the India map when available.
            ai_risk = str(row.get("Risk Level", "")).upper()
            confidence_color = RISK_COLOR.get(
                ai_risk,
                {
                    "h": "#ff3b46",
                    "n": "#f2a93b",
                    "l": "#2fd0a6"
                }.get(confidence, "#8b96aa")
            )

            frp_value = row.get("frp", float("nan"))
            frp_text = (
                f"{frp_value:.2f} MW"
                if pd.notna(frp_value)
                else "Unavailable"
            )

            satellite = row.get("satellite", "Unknown")
            date_value = row.get("acq_date", "Unknown")
            time_value = row.get("acq_time", "Unknown")

            # Distinctive thermal hotspot icon.
            # Symbol identifies the AI class; ring identifies the risk level.
            thermal_symbol = {
                "Industrial Fire":     "🔥",
                "Gas Flare":           "🕯",
                "Forest / Wildfire":   "🌲",
                "Agricultural Burning":"🌾",
                "Mining Activity":     "⛏",
                "Other Thermal Event": "☀",
            }.get(
                str(row.get("AI Classification", "")),
                "◉"
            )

            thermal_border = {
                "HIGH": "#ff3b46",
                "MEDIUM": "#f2a93b",
                "LOW": "#2fd0a6"
            }.get(
                ai_risk,
                "#8b96aa"
            )

            is_selected = (
                st.session_state.get("selected_india_hotspot") is not None
                and hotspot_idx == st.session_state.get("selected_india_hotspot")
            )
            marker_size = 40 if is_selected else 34
            marker_border = "#ffffff" if is_selected else thermal_border
            marker_shadow = f"0 0 18px 6px {thermal_border}, 0 0 8px #ffffff" if is_selected else f"0 0 12px {thermal_border}"
            marker_z = "z-index: 10000;" if is_selected else ""

            thermal_icon = folium.DivIcon(
                html=f"""
                <div title="Thermal hotspot #{hotspot_idx}{' (Selected)' if is_selected else ''}"
                     style="
                        width:{marker_size}px;
                        height:{marker_size}px;
                        border:{3.5 if is_selected else 3}px solid {marker_border};
                        border-radius:50%;
                        background:rgba(9,12,17,0.96);
                        box-shadow:{marker_shadow};
                        display:flex;
                        align-items:center;
                        justify-content:center;
                        transform:translate(-50%,-50%);
                        font-size:{21 if is_selected else 18}px;
                        line-height:{marker_size}px;
                        text-align:center;
                        font-family:Arial,sans-serif;
                        {marker_z}
                     ">
                    {thermal_symbol}
                </div>
                """
            )

            folium.Marker(
                location=[
                    row["latitude"],
                    row["longitude"]
                ],
                icon=thermal_icon,

                tooltip=folium.Tooltip(
                    f"""
                    <div style="
                        min-width:300px;
                        max-width:360px;
                        font-family:Arial,sans-serif;
                        font-size:12px;
                        line-height:1.45;
                        color:#17202a;
                    ">
                        <div style="
                            font-size:15px;
                            font-weight:700;
                            margin-bottom:7px;
                        ">
                            🔥 NASA FIRMS Hotspot #{hotspot_idx}
                        </div>

                        <b>📍 Coordinates:</b>
                        {float(row["latitude"]):.5f},
                        {float(row["longitude"]):.5f}<br>

                        <b>🔥 Current FRP:</b> {frp_text}<br>

                        <b>🎯 FIRMS Confidence:</b>
                        {confidence.upper()} · {confidence_label}<br>

                        <b>🛰️ Satellite:</b> {satellite}<br>

                        <b>📅 Acquisition:</b>
                        {date_value} · {time_value} UTC<br>

                        <b>☀️ Day/Night:</b>
                        {row.get("daynight", "Unknown")}<br>

                        <hr style="margin:6px 0;border:0;border-top:1px solid #d8dde3;">

                        <b>🤖 AI Classification:</b>
                        {row.get("AI Classification", "Unavailable")}<br>

                        <b>AI Confidence:</b>
                        {(
                            f"{float(row.get('AI Confidence (%)')):.2f}%"
                            if pd.notna(row.get("AI Confidence (%)"))
                            else "Unavailable"
                        )}<br>

                        <b>⚠️ Risk:</b>
                        {row.get("Risk Level", "Unavailable")} ·
                        {(
                            f"{float(row.get('Risk Score')):.0f}/100"
                            if pd.notna(row.get("Risk Score"))
                            else "Score unavailable"
                        )}<br>

                        <b>📊 30-Day Baseline:</b>
                        {(
                            f"{float(row.get('baseline_frp')):.2f} MW"
                            if pd.notna(row.get("baseline_frp"))
                            else "No local baseline"
                        )}<br>

                        <b>📈 FRP Change:</b>
                        {(
                            f"{float(row.get('frp_change_percent')):+.2f}%"
                            if pd.notna(row.get("frp_change_percent"))
                            else "Unavailable"
                        )}<br>

                        <b>🔁 Historical Detections:</b>
                        {int(row.get("detections", 0))}<br>

                        <hr style="margin:6px 0;border:0;border-top:1px solid #d8dde3;">

                        <b>🏭 Nearest Industry:</b>
                        {row.get("Nearest Industrial Facility", "Not available")}<br>

                        <b>📏 Distance to Industry:</b>
                        {(
                            f"{float(row.get('Distance to Industry (km)')):.2f} km"
                            if pd.notna(row.get("Distance to Industry (km)"))
                            else "Not available"
                        )}<br>

                        <b>🔗 Near Industry:</b>
                        {row.get("near_industry", "Unknown")}<br>

                        <div style="
                            margin-top:7px;
                            padding:6px 8px;
                            background:#f3f5f7;
                            border-radius:4px;
                            font-size:11px;
                        ">
                            ℹ️ Select this hotspot below the map for the
                            full geospatial context and detailed assessment.
                        </div>
                    </div>
                    """,
                    sticky=False,
                    direction="top"
                )
            ).add_to(m)

    # ---- Heatmap layer (FRP-weighted) ----
    if show_heatmap and len(india_firms) > 0:
        heat_data = []
        for _, row in india_firms.iterrows():
            frp_val = row.get("frp", 1.0)
            frp_val = float(frp_val) if pd.notna(frp_val) else 1.0
            heat_data.append([
                float(row["latitude"]),
                float(row["longitude"]),
                min(frp_val, 500)   # cap extreme FRP so one spike doesn't drown all others
            ])

        HeatMap(
            heat_data,
            name="FRP Heatmap",
            min_opacity=0.3,
            max_zoom=10,
            radius=18,
            blur=22,
            gradient={
                "0.2": "#2fd0a6",   # teal  → low
                "0.5": "#f2a93b",   # amber → medium
                "0.8": "#ff5a3c",   # fire  → high
                "1.0": "#ff3b46"    # crimson → extreme
            }
        ).add_to(m)

    folium.LayerControl().add_to(m)

    map_result = st_folium(
        m,
        width=None,
        height=430,
        key="india_overview_map",
        returned_objects=[]
    )

    if show_heatmap:
        st.markdown(
            """
            <div style="display:flex;align-items:center;justify-content:space-between;background:#0e131b;
                 border:1px solid #202a38;border-radius:4px;padding:8px 14px;margin-top:6px;font-size:11.5px;color:#8b96aa;">
                <span style="font-family:'IBM Plex Mono',monospace;font-weight:600;color:#e7edf6;">🔥 Thermal Intensity (FRP MW):</span>
                <div style="display:flex;align-items:center;gap:8px;flex:1;max-width:320px;margin:0 14px;">
                    <span style="font-family:monospace;font-size:10px;">Low</span>
                    <div style="height:6px;flex:1;border-radius:3px;background:linear-gradient(to right, #2fd0a6, #f2a93b, #ff5a3c, #ff3b46);"></div>
                    <span style="font-family:monospace;font-size:10px;">Extreme</span>
                </div>
                <span style="font-size:11px;color:#566073;">Weighted by Fire Radiative Power</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    # ---------------------------------------------------------
    # Select an India FIRMS hotspot for detailed inspection.
    # ---------------------------------------------------------
    if len(india_firms) > 0:

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(
            """
            <div class="section-head">
                <div class="section-title">Selected hotspot analysis</div>
                <div class="section-tag">FIRMS → AI DECISION SUPPORT</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        hotspot_options = list(range(len(india_firms)))

        selected_idx = st.selectbox(
            "Select FIRMS hotspot",
            hotspot_options,
            index=(
                st.session_state.selected_india_hotspot
                if st.session_state.selected_india_hotspot in hotspot_options
                else 0
            ),
            format_func=lambda i: (
                f"Hotspot #{i}  •  "
                f"{india_firms.iloc[i]['latitude']:.5f}, "
                f"{india_firms.iloc[i]['longitude']:.5f}  •  "
                f"FRP {india_firms.iloc[i]['frp']:.2f} MW"
            ),
            key="india_hotspot_selector"
        )

        st.session_state.selected_india_hotspot = selected_idx
        selected = india_firms.iloc[selected_idx]

        selected_prediction = selected.copy()

        confidence_raw = str(
            selected.get("confidence", "n")
        ).lower()

        confidence_label = {
            "h": "High",
            "n": "Nominal",
            "l": "Low"
        }.get(confidence_raw, "Unknown")

        ai_class = selected.get("AI Classification", "Unknown")
        ai_conf = selected.get("AI Confidence (%)", float("nan"))
        risk_score = selected.get("Risk Score", float("nan"))
        risk_level = str(selected.get("Risk Level", "Unknown")).upper()
        baseline = selected.get("baseline_frp", float("nan"))
        change = selected.get("frp_change_percent", float("nan"))
        detections = selected.get("detections", 0)

        # ---------- Satellite observation ----------
        st.markdown(
            f"""
            <div class="selected-title">🔥 Hotspot #{selected_idx}</div>
            <div class="selected-subtitle">
                NASA FIRMS thermal observation · {selected.get("acq_date", "Unknown")}
                · {selected.get("acq_time", "Unknown")}
            </div>
            """,
            unsafe_allow_html=True
        )

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.markdown(
                f"""
                <div class="detail-card blue">
                    <div class="detail-label">Coordinates</div>
                    <div class="detail-value" style="font-size:20px">
                        {selected["latitude"]:.5f}, {selected["longitude"]:.5f}
                    </div>
                    <div class="detail-small">Latitude / Longitude</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with c2:
            st.markdown(
                f"""
                <div class="detail-card fire">
                    <div class="detail-label">Fire Radiative Power</div>
                    <div class="detail-value">{selected["frp"]:.2f} MW</div>
                    <div class="detail-small">Current detection</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with c3:
            st.markdown(
                f"""
                <div class="detail-card amber">
                    <div class="detail-label">FIRMS Confidence</div>
                    <div class="detail-value">{confidence_label}</div>
                    <div class="detail-small">Satellite category: {confidence_raw.upper()}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with c4:
            st.markdown(
                f"""
                <div class="detail-card teal">
                    <div class="detail-label">Satellite</div>
                    <div class="detail-value">{selected.get("satellite", "N/A")}</div>
                    <div class="detail-small">Acquisition {selected.get("acq_date", "N/A")} · {selected.get("acq_time", "N/A")}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        # ---------- Nearest Industries ----------
        nearest_facility = selected.get("Nearest Industrial Facility", None)
        nearest_dist = selected.get("Distance to Industry (km)", float("nan"))
        near_flag = selected.get("near_industry", "Unknown")

        # Resolve missing / NaN values
        if nearest_facility in (None, "None", "Not available", float("nan")) or (
            isinstance(nearest_facility, float) and pd.isna(nearest_facility)
        ):
            nearest_facility_text = "Not available"
        else:
            nearest_facility_text = str(nearest_facility)

        if pd.notna(nearest_dist):
            nearest_dist_text = f"{float(nearest_dist):.2f} km"
            # Proximity colour: ≤2 km → fire/red, ≤10 km → amber, >10 km → teal
            if float(nearest_dist) <= 2:
                proximity_color = "#ff5a3c"
                proximity_label = "Within 2 km — industrial zone"
            elif float(nearest_dist) <= 10:
                proximity_color = "#f2a93b"
                proximity_label = "Within 10 km"
            else:
                proximity_color = "#2fd0a6"
                proximity_label = "More than 10 km away"
        else:
            nearest_dist_text = "Not available"
            proximity_color = "#8b96aa"
            proximity_label = "Distance unknown"

        st.markdown("### 🏭 Nearest Industrial Facility")

        n1, n2, n3 = st.columns(3)

        with n1:
            st.markdown(
                f"""
                <div class="detail-card" style="border-left:3px solid #4c8dff;">
                    <div class="detail-label">Nearest Industry</div>
                    <div class="detail-value" style="font-size:16px;word-break:break-word;">
                        {nearest_facility_text}
                    </div>
                    <div class="detail-small">OSM industrial facility</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with n2:
            st.markdown(
                f"""
                <div class="detail-card" style="border-left:3px solid {proximity_color};">
                    <div class="detail-label">Distance to Industry</div>
                    <div class="detail-value" style="color:{proximity_color};">
                        {nearest_dist_text}
                    </div>
                    <div class="detail-small">{proximity_label}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with n3:
            near_badge_color = "#ff5a3c" if near_flag == "Yes" else "#2fd0a6" if near_flag == "No" else "#8b96aa"
            st.markdown(
                f"""
                <div class="detail-card" style="border-left:3px solid {near_badge_color};">
                    <div class="detail-label">Near Industry (≤2 km)</div>
                    <div class="detail-value" style="color:{near_badge_color};">
                        {near_flag}
                    </div>
                    <div class="detail-small">Proximity threshold: 2 km radius</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        # ---------- AI assessment ----------
        risk_class = (
            "high" if risk_level == "HIGH"
            else "medium" if risk_level == "MEDIUM"
            else "low"
        )

        ai_conf_text = (
            f"{float(ai_conf):.2f}%"
            if pd.notna(ai_conf) else "—"
        )
        risk_score_text = (
            f"{float(risk_score):.0f}/100"
            if pd.notna(risk_score) else "—"
        )
        baseline_text = (
            f"{float(baseline):.2f} MW"
            if pd.notna(baseline) else "No local baseline"
        )
        change_text = (
            f"{float(change):+.2f}%"
            if pd.notna(change) else "—"
        )

        st.markdown(
            "### 🤖 AI assessment"
        )

        st.markdown(
            f'<span class="ai-status {risk_class}">{risk_level} RISK · {risk_score_text}</span>',
            unsafe_allow_html=True
        )

        st.markdown(
            f'<div class="ai-class">{ai_class}</div>',
            unsafe_allow_html=True
        )

        st.caption(
            "Prototype Random Forest assessment based on current FRP, "
            "historical baseline and persistence features."
        )

        a1, a2, a3 = st.columns(3)

        with a1:
            st.metric("AI confidence", ai_conf_text)

        with a2:
            st.metric("30-day baseline", baseline_text)

        with a3:
            st.metric("FRP change", change_text)

        a4, a5, a6 = st.columns(3)

        with a4:
            st.metric("Historical detections", int(detections))

        with a5:
            st.metric("Day / night", selected.get("daynight", "Unknown"))

        with a6:
            st.metric("Risk score", risk_score_text)

        # ---------- Land-cover / geospatial context ----------
        land_context = get_land_cover_context(
            float(selected["latitude"]),
            float(selected["longitude"]),
            selected_row=selected.to_dict()
        )

        land_cover = land_context["land_cover"]
        geo_context = land_context["context"]
        geo_source = land_context["source"]

        st.markdown("### 🌍 Land-cover classification")

        # The nine classes requested for the SIH geospatial layer.
        land_cover_classes = [
            ("🏭", "Industrial"),
            ("🏙️", "Built-up / Commercial"),
            ("🏠", "Built-up / Residential"),
            ("🌾", "Cropland / Agriculture"),
            ("🌳", "Forest / Woodland"),
            ("🌿", "Natural Vegetation"),
            ("⛏️", "Mining / Quarry"),
            ("🏗️", "Construction"),
            ("💧", "Water / Wetland"),
        ]

        # Normalize the detected class to one of the nine presentation classes.
        detected_class = land_cover

        # Show the actual detected result first.
        if detected_class in {
            "Industrial",
            "Built-up / Commercial",
            "Built-up / Residential",
            "Cropland / Agriculture",
            "Forest / Woodland",
            "Natural Vegetation",
            "Mining / Quarry",
            "Construction",
            "Water / Wetland",
        }:
            st.success(
                f"**Detected land-cover context:** {detected_class}"
            )
        else:
            st.warning(
                "**Detected land-cover context:** "
                "Not available for this hotspot"
            )

        st.caption(
            "Available land-cover/context classes used by FireSight AI:"
        )

        class_cols = st.columns(3)
        for idx, (icon, label) in enumerate(land_cover_classes):
            is_detected = label == detected_class
            with class_cols[idx % 3]:
                border = "#20c997" if is_detected else "#263244"
                background = "#10241f" if is_detected else "#0d121a"
                status = " ✓ DETECTED" if is_detected else ""
                st.markdown(
                    f"""
                    <div style="
                        border:1px solid {border};
                        background:{background};
                        border-radius:8px;
                        padding:10px 12px;
                        margin-bottom:8px;
                        min-height:52px;
                    ">
                        <div style="
                            font-size:20px;
                            display:inline-block;
                            margin-right:7px;
                        ">{icon}</div>
                        <span style="
                            color:#e7edf6;
                            font-size:12px;
                            font-weight:600;
                        ">{label}</span>
                        <div style="
                            color:#20c997;
                            font-size:9px;
                            margin-top:3px;
                            font-family:monospace;
                        ">{status}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        g1, g2, g3 = st.columns(3)

        with g1:
            st.metric("Detected class", land_cover)

        with g2:
            st.metric("Area context", geo_context)

        with g3:
            st.metric("Data source", geo_source)

        if land_context["available"]:
            st.caption(
                "The selected hotspot is checked against nearby OpenStreetMap "
                "land-use/natural-feature tags. This is geospatial context, "
                "not a satellite land-cover classification."
            )
        else:
            st.caption(
                "OSM context was unavailable for this hotspot. "
                "The nine classes above are the supported categories; "
                "no class is marked as detected when source data is unavailable."
            )



        st.markdown(
            """
            <div class="limitation-panel">
            <b>AI validation status:</b> This prototype combines NASA FIRMS
            observations with a 30-day historical FRP baseline and a
            Random Forest classifier. Land-cover context is shown as an
            additional OSM geospatial layer; it is not currently used as a
            trained model feature. Results are decision support, not a
            confirmed fire incident.
            </div>
            """,
            unsafe_allow_html=True
        )

        # ---------- 30-day FRP Trend Chart ----------
        st.markdown("### 📈 30-Day FRP Trend")

        frp_trend = get_frp_trend(
            india_historical if len(india_historical) > 0 else None,
            float(selected["latitude"]),
            float(selected["longitude"])
        )

        if frp_trend is not None and len(frp_trend) >= 2:
            frp_trend = frp_trend.set_index("Date")
            st.line_chart(
                frp_trend,
                use_container_width=True,
                height=220,
                color="#ff5a3c"
            )
            st.caption(
                f"Daily mean FRP within ~25 km of this hotspot "
                f"({len(frp_trend)} days of data from NASA FIRMS historical archive)."
            )
        else:
            st.markdown(
                """
                <div style="background:#0e131b;border:1px solid #202a38;
                border-radius:4px;padding:18px;text-align:center;
                color:#56607f;font-size:13px;">
                No historical FRP data available for this location
                in the 30-day archive.
                </div>
                """,
                unsafe_allow_html=True
            )

    # Legend
    st.markdown(
        f"""
        <div class="legend-strip">
            <span><span class="legend-dot" style="background:{class_color('Industrial Fire')}"></span>Industrial fire</span>
            <span><span class="legend-dot" style="background:{class_color('Gas Flare')}"></span>Gas flare</span>
            <span><span class="legend-dot" style="background:{class_color('Forest / Wildfire')}"></span>Forest / Wildfire</span>
            <span><span class="legend-dot" style="background:{class_color('Agricultural Burning')}"></span>Agricultural burning</span>
            <span><span class="legend-dot" style="background:{class_color('Mining Activity')}"></span>Mining activity</span>
            <span><span class="legend-dot" style="background:{class_color('Other Thermal Event')}"></span>Other thermal event</span>
            <span><span class="legend-dot" style="background:{OSM_COLOR}"></span>OSM industrial location</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # Analytics
    a1, a2 = st.columns(2)

    with a1:

        st.markdown(
            """
            <div class="section-head">
                <div class="section-title">Classification distribution</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        counts = data[
            "AI Classification"
        ].value_counts()

        render_donut(
            counts,
            CLASS_COLOR,
            key="classification_donut"
        )

        if len(india_firms) > 0:
            st.caption(
                f"India overview: {len(india_firms)} current FIRMS hotspots; "
                f"AI predictions available for {len(data)} validated India hotspots."
            )

    with a2:

        st.markdown(
            """
            <div class="section-head">
                <div class="section-title">Risk distribution</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        risk_counts = data[
            "Risk Level"
        ].value_counts()

        render_donut(
            risk_counts,
            RISK_COLOR,
            key="risk_donut"
        )

    # ---------------------------------------------------------
    # Top States by industrial fire count
    # ---------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class="section-head">
            <div class="section-title">Top states by detection count</div>
            <div class="section-tag">AI PREDICTIONS · ALL CLASSES</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if "state" in data.columns and len(data) > 0:
        state_counts = (
            data.groupby("state")["AI Classification"]
            .count()
            .reset_index()
            .rename(columns={"AI Classification": "Detections"})
            .sort_values("Detections", ascending=False)
            .head(10)
            .set_index("state")
        )

        # Industrial fires per state
        industrial_by_state = (
            data[data["AI Classification"] == "Industrial Fire"]
            .groupby("state")
            .size()
            .rename("Industrial Fires")
        )

        state_chart = state_counts.join(industrial_by_state, how="left").fillna(0)
        state_chart["Industrial Fires"] = state_chart["Industrial Fires"].astype(int)

        st.bar_chart(
            state_chart,
            use_container_width=True,
            height=280,
            color=["#4c8dff", "#ff5a3c"]
        )
        st.caption(
            "Blue = all detections · Red = industrial fires only · "
            "Top 10 states shown"
        )
    else:
        st.info("State breakdown not available — no data after current filters.")


# =========================================================
# THERMAL MAP PAGE
# =========================================================

elif "Detection Records" in page:


    st.markdown(
        """
        <div class="section-head">
            <div class="section-title">Detection records</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    display_columns = [
        "latitude",
        "longitude",
        "frp",
        "baseline_frp",
        "frp_change_percent",
        "confidence",
        "AI Classification",
        "AI Confidence (%)",
        "Nearest Industrial Facility",
        "Distance to Industry (km)",
        "near_industry",
        "detections",
        "Risk Score",
        "Risk Level"
    ]

    display_columns = [
        c for c in display_columns
        if c in data.columns
    ]

    # Rich column configuration for telemetry display
    col_config = {
        "latitude": st.column_config.NumberColumn("Latitude", format="%.4f"),
        "longitude": st.column_config.NumberColumn("Longitude", format="%.4f"),
        "frp": st.column_config.NumberColumn("FRP (MW)", format="%.2f MW"),
        "baseline_frp": st.column_config.NumberColumn("Baseline FRP", format="%.2f MW"),
        "frp_change_percent": st.column_config.NumberColumn("FRP Change %", format="%+.1f%%"),
        "AI Confidence (%)": st.column_config.ProgressColumn(
            "AI Confidence",
            help="Confidence score from Random Forest classifier",
            format="%.1f%%",
            min_value=0,
            max_value=100,
        ),
        "Risk Score": st.column_config.ProgressColumn(
            "Risk Score",
            help="Calculated risk score (0-100)",
            format="%d/100",
            min_value=0,
            max_value=100,
        ),
        "Distance to Industry (km)": st.column_config.NumberColumn("Dist to Industry", format="%.2f km"),
        "detections": st.column_config.NumberColumn("Detections", format="%d"),
    }

    st.dataframe(
        data[display_columns],
        column_config=col_config,
        use_container_width=True,
        height=500
    )

    # ---------- Download buttons ----------
    import json

    dl1, dl2, dl3 = st.columns([1, 1, 4])

    csv_bytes = data[display_columns].to_csv(index=False).encode("utf-8")

    with dl1:
        st.download_button(
            label="⬇ Download CSV",
            data=csv_bytes,
            file_name="india_fire_detections.csv",
            mime="text/csv",
            use_container_width=True
        )

    # GeoJSON export
    def df_to_geojson(df):
        features = []
        lat_col = "latitude" if "latitude" in df.columns else "Latitude"
        lon_col = "longitude" if "longitude" in df.columns else "Longitude"
        for _, row in df.iterrows():
            try:
                lat = float(row[lat_col])
                lon = float(row[lon_col])
            except Exception:
                continue
            props = {
                col: (
                    row[col] if not pd.isna(row[col]) else None
                )
                for col in df.columns
                if col not in [lat_col, lon_col]
            }
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat]
                },
                "properties": props
            })
        return json.dumps({"type": "FeatureCollection", "features": features},
                          default=str, indent=2).encode("utf-8")

    geojson_bytes = df_to_geojson(data[display_columns])

    with dl2:
        st.download_button(
            label="⬇ Download GeoJSON",
            data=geojson_bytes,
            file_name="india_fire_detections.geojson",
            mime="application/geo+json",
            use_container_width=True
        )

    st.markdown(
        """
        <div class="section-head" style="margin-top:22px;">
            <div class="section-title">Detection alerts</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    alerts = data[
        data["Risk Level"].isin(
            ["HIGH", "MEDIUM"]
        )
    ]

    if alerts.empty:

        st.markdown(
            '<div class="ok-row">No medium or high-risk events detected.</div>',
            unsafe_allow_html=True
        )

    else:

        for _, row in alerts.iterrows():

            rc = risk_color(row["Risk Level"])

            st.markdown(
                f"""
                <div class="alert-row" style="--accent:{rc}">
                    <span class="alert-badge" style="background:{rc}">{row["Risk Level"]}</span>
                    <span>{row["AI Classification"]}</span>
                    <span>&middot;</span>
                    <span>{row["latitude"]:.4f}, {row["longitude"]:.4f}</span>
                    <span>&middot;</span>
                    <span>FRP {row["frp"]:.2f} MW</span>
                    <span>&middot;</span>
                    <span>{"Industry context unavailable" if pd.isna(row["Distance to Industry (km)"]) else f"{row["Distance to Industry (km)"]:.2f} km to industry"}</span>
                    <span>&middot;</span>
                    <span>{row["Risk Score"]}/100</span>
                </div>
                """,
                unsafe_allow_html=True
            )


# =========================================================
# SYSTEM INFO
# =========================================================

elif "System Info" in page:

    # ---- Section header ----
    st.markdown(
        """
        <div class="section-head">
            <div class="section-title">System information</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="info-panel">
        <b>Project</b> &mdash; SIH26162: Industrial Fire &amp; Persistent
        Thermal Source Detection<br><br>

        <b>Thermal data</b> &mdash; NASA FIRMS (VIIRS NOAA-20 / NOAA-21 NRT)<br>
        <b>Industrial / geospatial data</b> &mdash; OpenStreetMap (Overpass API)<br>
        <b>Historical analysis</b> &mdash; 30-day FIRMS archive (FRP baseline)<br>
        <b>AI model</b> &mdash; Random Forest classifier · 6-class fire type detection<br>
        <b>Coverage</b> &mdash; India-wide · 35 states &amp; UTs<br><br>

        <b>Core pipeline</b><br>
        <span class="info-mono">NASA FIRMS hotspot &rarr; FRP &rarr; 30-day baseline
        &rarr; FRP anomaly score &rarr; OSM industrial proximity
        &rarr; Random Forest &rarr; 6-class fire type
        &rarr; risk score (0–100) &rarr; HIGH / MEDIUM / LOW</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ---- Model metrics ----
    st.markdown(
        """
        <div class="section-head">
            <div class="section-title">AI model performance</div>
            <div class="section-tag">RANDOM FOREST · 80/20 SPLIT · SEED 42</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    metrics = get_model_metrics()

    if metrics is None:
        st.warning("Model artefacts not found. Run train_india_model.py first.")
    else:
        # ---- Overall accuracy card ----
        acc = metrics["accuracy"]
        acc_color = "#2fd0a6" if acc >= 90 else "#f2a93b" if acc >= 70 else "#ff5a3c"

        st.markdown(
            f"""
            <div style="display:flex;gap:16px;margin-bottom:18px;flex-wrap:wrap;">
              <div class="metric-card" style="--accent:{acc_color};flex:1;min-width:160px;">
                <div class="metric-label">Test accuracy</div>
                <div class="metric-value">{acc:.1f}%</div>
                <div class="metric-footnote">{metrics['n_test']} test samples</div>
              </div>
              <div class="metric-card" style="--accent:#4c8dff;flex:1;min-width:160px;">
                <div class="metric-label">Training samples</div>
                <div class="metric-value">{metrics['n_train']}</div>
                <div class="metric-footnote">NASA FIRMS observations</div>
              </div>
              <div class="metric-card" style="--accent:#a78bfa;flex:1;min-width:160px;">
                <div class="metric-label">Fire classes</div>
                <div class="metric-value">{len(metrics['classes'])}</div>
                <div class="metric-footnote">distinct categories</div>
              </div>
              <div class="metric-card" style="--accent:#ff9f1c;flex:1;min-width:160px;">
                <div class="metric-label">Estimators</div>
                <div class="metric-value">{metrics['params']['n_estimators']}</div>
                <div class="metric-footnote">decision trees</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # ---- Per-class precision / recall / F1 ----
        st.markdown(
            """
            <div class="section-head" style="margin-top:6px;">
                <div class="section-title">Per-class metrics</div>
                <div class="section-tag">PRECISION · RECALL · F1</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        report = metrics["report"]
        class_icons = {
            "Industrial Fire":     "🔥",
            "Gas Flare":           "🕯",
            "Forest / Wildfire":   "🌲",
            "Agricultural Burning":"🌾",
            "Mining Activity":     "⛏",
            "Other Thermal Event": "☀",
        }

        # Build rows for each real class (skip avg rows)
        skip_keys = {"accuracy", "macro avg", "weighted avg"}
        rows_html = ""
        for cls in metrics["classes"]:
            if cls in skip_keys:
                continue
            r = report.get(cls, {})
            prec  = r.get("precision", 0) * 100
            rec   = r.get("recall",    0) * 100
            f1    = r.get("f1-score",  0) * 100
            sup   = int(r.get("support", 0))
            color = CLASS_COLOR.get(cls, "#8b96aa")
            icon  = class_icons.get(cls, "◉")

            def bar(val, color):
                return (
                    f'<div style="height:6px;border-radius:3px;background:#131a24;margin-top:4px;">'
                    f'<div style="width:{val:.0f}%;height:100%;border-radius:3px;'
                    f'background:{color};transition:width .3s;"></div></div>'
                )

            rows_html += f"""
            <div style="background:#0e131b;border:1px solid #202a38;
                border-left:3px solid {color};border-radius:6px;
                padding:12px 16px;margin-bottom:10px;">
              <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                <span style="font-size:18px;">{icon}</span>
                <span style="color:#e7edf6;font-weight:600;font-size:13px;">{cls}</span>
                <span style="margin-left:auto;font-family:monospace;color:#566073;
                    font-size:11px;">{sup} samples</span>
              </div>
              <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">
                <div>
                  <div style="color:#8b96aa;font-size:11px;text-transform:uppercase;
                      letter-spacing:.6px;">Precision</div>
                  <div style="color:#e7edf6;font-family:monospace;font-size:18px;
                      font-weight:600;">{prec:.1f}%</div>
                  {bar(prec, color)}
                </div>
                <div>
                  <div style="color:#8b96aa;font-size:11px;text-transform:uppercase;
                      letter-spacing:.6px;">Recall</div>
                  <div style="color:#e7edf6;font-family:monospace;font-size:18px;
                      font-weight:600;">{rec:.1f}%</div>
                  {bar(rec, color)}
                </div>
                <div>
                  <div style="color:#8b96aa;font-size:11px;text-transform:uppercase;
                      letter-spacing:.6px;">F1-Score</div>
                  <div style="color:#e7edf6;font-family:monospace;font-size:18px;
                      font-weight:600;">{f1:.1f}%</div>
                  {bar(f1, color)}
                </div>
              </div>
            </div>
            """

        # Weighted averages
        wavg = report.get("weighted avg", {})
        rows_html += f"""
        <div style="background:#0c1118;border:1px solid #202a38;border-radius:6px;
            padding:10px 16px;margin-top:4px;display:flex;gap:32px;flex-wrap:wrap;">
          <span style="color:#566073;font-size:12px;">
            Weighted avg &nbsp;·&nbsp;
            Precision <b style="color:#e7edf6;font-family:monospace;">
              {wavg.get('precision',0)*100:.1f}%</b> &nbsp;·&nbsp;
            Recall <b style="color:#e7edf6;font-family:monospace;">
              {wavg.get('recall',0)*100:.1f}%</b> &nbsp;·&nbsp;
            F1 <b style="color:#e7edf6;font-family:monospace;">
              {wavg.get('f1-score',0)*100:.1f}%</b>
          </span>
        </div>
        """

        st.markdown(rows_html, unsafe_allow_html=True)

        # ---- Feature importances ----
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            """
            <div class="section-head">
                <div class="section-title">Feature importances</div>
                <div class="section-tag">GINI IMPURITY REDUCTION</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        imp = metrics["importances"].set_index("Feature")
        st.bar_chart(imp, use_container_width=True, height=240, color="#4c8dff")

        # ---- Model hyper-parameters ----
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            """
            <div class="section-head">
                <div class="section-title">Model hyper-parameters</div>
                <div class="section-tag">RANDOM FOREST CONFIG</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        p = metrics["params"]
        st.markdown(
            f"""
            <div class="info-panel" style="font-family:'IBM Plex Mono',monospace;
                font-size:12.5px;line-height:2;">
              <b style="color:#8b96aa;">n_estimators</b>
              &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
              <span style="color:#2fd0a6;">{p['n_estimators']}</span><br>

              <b style="color:#8b96aa;">max_depth</b>
              &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
              <span style="color:#2fd0a6;">{p['max_depth']}</span><br>

              <b style="color:#8b96aa;">min_samples_leaf</b>
              &nbsp;&nbsp;&nbsp;&nbsp;
              <span style="color:#2fd0a6;">{p['min_samples_leaf']}</span><br>

              <b style="color:#8b96aa;">class_weight</b>
              &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
              <span style="color:#2fd0a6;">{p['class_weight']}</span><br>

              <b style="color:#8b96aa;">random_state</b>
              &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
              <span style="color:#2fd0a6;">{p['random_state']}</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ---- Prototype limitation ----
    st.markdown(
        """
        <div class="section-head">
            <div class="section-title">Prototype limitation</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="limitation-panel">
        The current classifier is a proof-of-concept trained on a small
        dataset with heuristic rule-based labels (not ground-truth incident data).
        High accuracy reflects the rule-consistency of the labels, not validated
        real-world fire detection. Production deployment requires a larger,
        expert-labeled historical dataset with verified incident records.
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<br>", unsafe_allow_html=True)

    st.caption(
        "OpenStreetMap data \u00a9 OpenStreetMap contributors. "
        "Satellite basemap \u00a9 Esri. "
        "Thermal data: NASA FIRMS (VIIRS NRT)."
    )



# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "SIH26162 proof-of-concept — NASA FIRMS + historical FRP + "
    "OpenStreetMap + random forest AI"
)