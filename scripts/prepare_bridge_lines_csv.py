from pathlib import Path

import geopandas as gpd
import pandas as pd
from pyproj import Geod

src = Path(r"data\processed\ap-bridges-topology.geojson")
dst = Path(r"data\processed\osm_bridge_lines_import.csv")

if not src.exists():
    raise FileNotFoundError(src)

print("Reading:", src)

g = gpd.read_file(src)

print("SOURCE ROWS:", len(g))
print("GEOMETRY TYPES:")
print(g.geom_type.value_counts())

# Keep only real bridge way line geometry.
g = g[g.geometry.notna()].copy()
g = g[g.geom_type == "LineString"].copy()

if g.crs is None:
    g = g.set_crs("EPSG:4326")
else:
    g = g.to_crs("EPSG:4326")

# Geodesic length in metres.
geod = Geod(ellps="WGS84")
g["length_m"] = g.geometry.apply(
    lambda geom: abs(geod.geometry_length(geom))
)

# Store geometry temporarily as WKT for COPY into PostgreSQL.
g["geom_wkt"] = g.geometry.to_wkt()

def col(name):
    if name in g.columns:
        return g[name]
    return pd.Series([None] * len(g), index=g.index)

out = pd.DataFrame({
    "osm_way_id": col("@id"),
    "name": col("name"),
    "bridge_tag": col("bridge"),
    "highway": col("highway"),
    "railway": col("railway"),
    "road_ref": col("ref"),
    "operator": col("operator"),
    "lanes": col("lanes"),
    "width": col("width"),
    "maxweight": col("maxweight"),
    "maxaxleload": col("maxaxleload"),
    "bridge_structure": col("bridge:structure"),
    "bridge_support": col("bridge:support"),
    "structure": col("structure"),
    "surface": col("surface"),
    "start_date": col("start_date"),
    "opening_date": col("opening_date"),
    "flood_prone": col("flood_prone"),
    "osm_source": col("source"),
    "geometry_source": col("source:geometry"),
    "length_m": g["length_m"],
    "source_code": "OSM_AP_BRIDGE_GEOJSON",
    "geometry_provenance": "OSM_WAY_GEOMETRY_DERIVED",
    "length_is_official": False,
    "geom_wkt": g["geom_wkt"],
})

out["osm_way_id"] = pd.to_numeric(
    out["osm_way_id"],
    errors="raise"
).astype("int64")

out = out.drop_duplicates(
    subset=["osm_way_id"],
    keep="last"
)

out.to_csv(
    dst,
    index=False,
    encoding="utf-8"
)

print()
print("CSV CREATED:", dst)
print("ROWS:", len(out))
print("UNIQUE WAYS:", out["osm_way_id"].nunique())
print("MIN LENGTH M:", round(out["length_m"].min(), 2))
print("MEDIAN LENGTH M:", round(out["length_m"].median(), 2))
print("MAX LENGTH M:", round(out["length_m"].max(), 2))
