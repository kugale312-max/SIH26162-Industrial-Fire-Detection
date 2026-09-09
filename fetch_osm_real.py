import requests
import pandas as pd
import os
import time


# =========================================================
# REAL OSM INDUSTRIAL DATA
# =========================================================

print("======================================")
print("OPENSTREETMAP INDUSTRIAL DATA")
print("======================================")


# ---------------------------------------------------------
# LOAD REAL FIRMS HOTSPOTS
# ---------------------------------------------------------

firms = pd.read_csv(
    "data/firms_real.csv"
)

print(
    "Real FIRMS hotspots:",
    len(firms)
)


# ---------------------------------------------------------
# OVERPASS API
# ---------------------------------------------------------

overpass_url = (
    "https://overpass-api.de/api/interpreter"
)


# ---------------------------------------------------------
# FIND INDUSTRIAL FEATURES
# ---------------------------------------------------------

all_features = []


for index, row in firms.iterrows():

    lat = row["latitude"]
    lon = row["longitude"]

    print()
    print(
        f"Searching OSM around hotspot {index + 1}: "
        f"{lat}, {lon}"
    )

    # Search approximately 5 km around hotspot
    query = f"""
    [out:json][timeout:30];

    (
      nwr(around:5000,{lat},{lon})["landuse"="industrial"];
      nwr(around:5000,{lat},{lon})["industrial"];
      nwr(around:5000,{lat},{lon})["building"="industrial"];
    );

    out center tags;
    """

    try:

        response = requests.post(
            overpass_url,
            data=query,
            headers={
                "User-Agent":
                "SIH26162-Industrial-Fire-Prototype/1.0"
            },
            timeout=45
        )

        print(
            "HTTP Status:",
            response.status_code
        )

        response.raise_for_status()

        osm_data = response.json()

        elements = osm_data.get(
            "elements",
            []
        )

        print(
            "OSM features found:",
            len(elements)
        )

        for element in elements:

            tags = element.get(
                "tags",
                {}
            )

            # -------------------------------------------------
            # Get coordinates
            # -------------------------------------------------

            if "lat" in element:

                feature_lat = element["lat"]
                feature_lon = element["lon"]

            elif "center" in element:

                feature_lat = element["center"]["lat"]
                feature_lon = element["center"]["lon"]

            else:

                continue


            # -------------------------------------------------
            # Feature name
            # -------------------------------------------------

            name = tags.get(
                "name",
                "Unnamed Industrial Feature"
            )

            industrial_type = (
                tags.get("industrial")
                or tags.get("landuse")
                or tags.get("building")
                or "industrial"
            )


            all_features.append({

                "name": name,

                "latitude":
                    feature_lat,

                "longitude":
                    feature_lon,

                "type":
                    industrial_type

            })

        # Avoid sending requests too quickly
        time.sleep(1)


    except Exception as e:

        print(
            "OSM ERROR:",
            e
        )


# =========================================================
# CREATE DATAFRAME
# =========================================================

print()
print("======================================")
print("PROCESSING OSM DATA")
print("======================================")


if all_features:

    industrial_locations = pd.DataFrame(
        all_features
    )

    # Remove duplicate OSM features
    industrial_locations = (
        industrial_locations
        .drop_duplicates(
            subset=[
                "latitude",
                "longitude"
            ]
        )
    )

else:

    industrial_locations = pd.DataFrame(
        columns=[
            "name",
            "latitude",
            "longitude",
            "type"
        ]
    )


print(
    "Unique industrial features:",
    len(industrial_locations)
)


# =========================================================
# SAVE
# =========================================================

os.makedirs(
    "data",
    exist_ok=True
)

output_file = (
    "data/industrial_locations_real.csv"
)

industrial_locations.to_csv(
    output_file,
    index=False
)


print()
print(
    "✓ Real OSM data saved:"
)

print(
    output_file
)


# =========================================================
# SHOW RESULTS
# =========================================================

if len(industrial_locations) > 0:

    print()
    print(
        industrial_locations.head(10)
    )

else:

    print()
    print(
        "⚠️ No OSM industrial features found."
    )


print()
print("======================================")
print("OSM FETCH COMPLETED")
print("======================================")