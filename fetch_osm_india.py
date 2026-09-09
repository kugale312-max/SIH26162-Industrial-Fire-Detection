"""
fetch_osm_india.py  — fetch named industrial facilities India-wide from OSM
"""
import requests, pandas as pd, time, sys

OUTPUT_FILE = "data/industrial_locations_india.csv"

ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

QUERY = """
[out:json][timeout:90];
area["name"="India"]["admin_level"="2"]->.india;
(
  node["landuse"="industrial"]["name"](area.india);
  way["landuse"="industrial"]["name"](area.india);
  node["man_made"="works"]["name"](area.india);
  node["power"="plant"]["name"](area.india);
  way["power"="plant"]["name"](area.india);
  node["industrial"="refinery"]["name"](area.india);
  way["industrial"="refinery"]["name"](area.india);
  node["industrial"="mine"]["name"](area.india);
  way["industrial"="mine"]["name"](area.india);
  node["man_made"="petroleum_well"]["name"](area.india);
);
out center tags;
"""

print("=" * 60)
print("OVERPASS OSM INDIA INDUSTRIAL FETCH")
print("=" * 60)

elements = []
for ep in ENDPOINTS:
    print(f"\nTrying {ep} ...")
    try:
        r = requests.post(ep, data=QUERY, timeout=100,
                          headers={"User-Agent": "FireSight-AI-SIH26162/1.0"})
        r.raise_for_status()
        elements = r.json().get("elements", [])
        print(f"  Got {len(elements)} elements")
        break
    except Exception as e:
        print(f"  Failed: {e}")
        time.sleep(2)

if not elements:
    print("\nAll endpoints failed — keeping existing OSM file.")
    sys.exit(0)

rows = []
for el in elements:
    tags = el.get("tags", {})
    name = tags.get("name", "").strip()
    if not name:
        continue
    lat = el.get("lat") or (el.get("center") or {}).get("lat")
    lon = el.get("lon") or (el.get("center") or {}).get("lon")
    if lat is None or lon is None:
        continue
    ftype = (tags.get("industrial") or tags.get("power") or
             tags.get("man_made") or tags.get("landuse") or "industrial")
    rows.append({"name": name, "latitude": float(lat),
                 "longitude": float(lon), "type": ftype})

df = pd.DataFrame(rows).drop_duplicates(subset=["name","latitude","longitude"])
df.to_csv(OUTPUT_FILE, index=False)
print(f"\nSaved {len(df)} named facilities -> {OUTPUT_FILE}")
print(df["type"].value_counts().head(8).to_string())
