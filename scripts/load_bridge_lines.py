from pathlib import Path
from urllib.parse import quote_plus
import subprocess

import geopandas as gpd
from pyproj import Geod
from sqlalchemy import create_engine, text
from geoalchemy2 import Geometry

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data' / 'processed' / 'ap-bridges-topology.geojson'

def docker_env(name):
    return subprocess.check_output(
        ['docker','compose','exec','-T','db','printenv',name],
        cwd=ROOT,
        text=True,
    ).strip()

def docker_port():
    value = subprocess.check_output(
        ['docker','compose','port','db','5432'],
        cwd=ROOT,
        text=True,
    ).strip()
    return int(value.rsplit(':',1)[1])

print('Reading:', SOURCE)

gdf = gpd.read_file(SOURCE)

print('Source rows:', len(gdf))
print(gdf.geom_type.value_counts())

gdf = gdf[gdf.geometry.notna()].copy()
gdf = gdf[gdf.geom_type == 'LineString'].copy()

if gdf.crs is None:
    gdf = gdf.set_crs(4326)
else:
    gdf = gdf.to_crs(4326)

geod = Geod(ellps='WGS84')
gdf['length_m'] = gdf.geometry.apply(lambda geom: abs(geod.geometry_length(geom)))

columns = {
    '@id': 'osm_way_id',
    'name': 'name',
    'bridge': 'bridge_tag',
    'highway': 'highway',
    'railway': 'railway',
    'ref': 'road_ref',
    'operator': 'operator',
    'lanes': 'lanes',
    'width': 'width',
    'maxweight': 'maxweight',
    'maxaxleload': 'maxaxleload',
    'bridge:structure': 'bridge_structure',
    'bridge:support': 'bridge_support',
    'structure': 'structure',
    'surface': 'surface',
    'start_date': 'start_date',
    'opening_date': 'opening_date',
    'flood_prone': 'flood_prone',
    'source': 'osm_source',
    'source:geometry': 'geometry_source',
    'geometry': 'geom',
}

keep = [c for c in columns if c in gdf.columns]
out = gdf[keep + ['length_m']].rename(columns=columns).copy()

out['osm_way_id'] = out['osm_way_id'].astype('int64')
out['source_code'] = 'OSM_AP_BRIDGE_GEOJSON'
out['geometry_provenance'] = 'OSM_WAY_GEOMETRY_DERIVED'
out['length_is_official'] = False

out = gpd.GeoDataFrame(out, geometry='geom', crs='EPSG:4326')
out = out.drop_duplicates(subset=['osm_way_id'], keep='last')

user = docker_env('POSTGRES_USER')
password = docker_env('POSTGRES_PASSWORD')
database = docker_env('POSTGRES_DB')
port = docker_port()

url = (
    'postgresql+psycopg2://'
    + quote_plus(user) + ':'
    + quote_plus(password)
    + '@127.0.0.1:' + str(port)
    + '/' + quote_plus(database)
)

engine = create_engine(url)

with engine.begin() as conn:
    conn.execute(text('CREATE SCHEMA IF NOT EXISTS staging'))

out.to_postgis(
    'osm_bridge_lines',
    engine,
    schema='staging',
    if_exists='replace',
    index=False,
    dtype={'geom': Geometry('LINESTRING', srid=4326)},
    chunksize=2000,
)

with engine.begin() as conn:
    conn.execute(text('''
        ALTER TABLE staging.osm_bridge_lines
        ADD PRIMARY KEY (osm_way_id)
    '''))
    conn.execute(text('''
        CREATE INDEX IF NOT EXISTS ix_osm_bridge_lines_geom
        ON staging.osm_bridge_lines
        USING GIST (geom)
    '''))
    conn.execute(text('''
        CREATE INDEX IF NOT EXISTS ix_osm_bridge_lines_highway
        ON staging.osm_bridge_lines (highway)
    '''))

print()
print('IMPORT COMPLETE')
print('Rows:', len(out))
print('Min length m:', round(out.length_m.min(),2))
print('Median length m:', round(out.length_m.median(),2))
print('Max length m:', round(out.length_m.max(),2))
print('Unique OSM ways:', out.osm_way_id.nunique())
