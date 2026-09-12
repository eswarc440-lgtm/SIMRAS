import asyncio
import csv
import math
import os
import re

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


CWC_FILE = "/tmp/cwc_nrld_2019_ap_166.csv"
LEVEL_FILE = "/tmp/ap_level.csv"
STORAGE_FILE = "/tmp/ap_storage.csv"

IST = ZoneInfo("Asia/Kolkata")


def clean(value):
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    if value.upper() in {
        "-",
        "NA",
        "N/A",
        "UNKNOWN",
        "NULL",
        "NONE",
    }:
        return None

    return value


def number(value):
    value = clean(value)

    if value is None:
        return None

    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except Exception:
        return None


def integer(value):
    value = number(value)
    return int(round(value)) if value is not None else None


def norm(value):
    value = str(value or "").lower()

    value = value.replace("&", " and ")

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value,
    )

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


DROP = {
    "dam",
    "reservoir",
    "project",
    "tank",
    "barrage",
    "anicut",
    "weir",
    "scheme",
    "the",
}


def relaxed(value):
    return " ".join(
        word
        for word in norm(value).split()
        if word not in DROP
    )


def embedded_pic(asset_code):
    match = re.search(
        r"(AP\d{2}[A-Z]{2}\d{4})",
        str(asset_code or "").upper(),
    )

    return match.group(1) if match else None


def distance_km(lat1, lon1, lat2, lon2):

    values = (lat1, lon1, lat2, lon2)

    if any(value is None for value in values):
        return None

    try:
        lat1 = math.radians(float(lat1))
        lon1 = math.radians(float(lon1))
        lat2 = math.radians(float(lat2))
        lon2 = math.radians(float(lon2))
    except Exception:
        return None

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2.0) ** 2
    )

    return 6371.0088 * 2.0 * math.asin(math.sqrt(a))


def parse_observation_time(value):

    value = clean(value)

    if not value:
        return None

    try:
        local = datetime.strptime(
            value,
            "%d-%m-%Y %H:%M",
        ).replace(tzinfo=IST)

        return local.astimezone(
            timezone.utc
        )
    except Exception:
        return None


def latest_station_rows(path, value_column):

    latest = {}

    with open(
        path,
        encoding="utf-8-sig",
        newline="",
    ) as handle:

        for row in csv.DictReader(handle):

            station = clean(
                row.get("Station")
            )

            value = number(
                row.get(value_column)
            )

            observed = parse_observation_time(
                row.get("Data Acquisition Time")
            )

            if not station or value is None or observed is None:
                continue

            if observed > datetime.now(timezone.utc) + timedelta(days=1):
                continue

            key = norm(station)

            current = latest.get(key)

            if current is None or observed > current["observed"]:
                latest[key] = {
                    "station": station,
                    "value": value,
                    "observed": observed,
                    "latitude": number(row.get("Latitude")),
                    "longitude": number(row.get("Longitude")),
                }

    return list(latest.values())


async def main():

    database_url = os.environ.get(
        "DATABASE_URL"
    )

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL missing"
        )

    if database_url.startswith(
        "postgresql://"
    ):
        database_url = database_url.replace(
            "postgresql://",
            "postgresql+asyncpg://",
            1,
        )

    engine = create_async_engine(
        database_url,
        pool_pre_ping=True,
    )


    with open(
        CWC_FILE,
        encoding="utf-8-sig",
        newline="",
    ) as handle:

        cwc = list(
            csv.DictReader(handle)
        )


    if len(cwc) != 166:
        raise RuntimeError(
            "CWC loader expected exactly 166 rows"
        )


    async with engine.begin() as conn:

        # ====================================================
        # RAW CWC
        # ====================================================

        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS
                public.cwc_ap_nrld_2019
                (
                    pic TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    operator TEXT,

                    latitude DOUBLE PRECISION,
                    longitude DOUBLE PRECISION,

                    completion_year INTEGER,

                    river_basin TEXT,
                    river TEXT,
                    nearest_city TEXT,
                    seismic_zone TEXT,
                    dam_type TEXT,

                    height_m DOUBLE PRECISION,
                    length_m DOUBLE PRECISION,
                    dam_volume_m3 DOUBLE PRECISION,

                    gross_storage_mcm DOUBLE PRECISION,
                    reservoir_area_m2 DOUBLE PRECISION,
                    effective_storage_mcm DOUBLE PRECISION,

                    purpose TEXT,
                    spillway_capacity_cumecs DOUBLE PRECISION,

                    source_authority TEXT,
                    source_document TEXT,
                    source_url TEXT,
                    evidence_class TEXT,

                    loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )


        for row in cwc:

            params = {
                "pic": row["pic"],
                "name": row["name"],
                "operator": clean(row["operator"]),
                "latitude": number(row["latitude"]),
                "longitude": number(row["longitude"]),
                "completion_year": integer(row["completion_year"]),
                "river_basin": clean(row["river_basin"]),
                "river": clean(row["river"]),
                "nearest_city": clean(row["nearest_city"]),
                "seismic_zone": clean(row["seismic_zone"]),
                "dam_type": clean(row["dam_type"]),
                "height_m": number(row["height_m"]),
                "length_m": number(row["length_m"]),
                "dam_volume_m3": number(row["dam_volume_m3"]),
                "gross_storage_mcm": number(row["gross_storage_mcm"]),
                "reservoir_area_m2": number(row["reservoir_area_m2"]),
                "effective_storage_mcm": number(row["effective_storage_mcm"]),
                "purpose": clean(row["purpose"]),
                "spillway_capacity_cumecs":
                    number(row["spillway_capacity_cumecs"]),
                "source_authority": row["source_authority"],
                "source_document": row["source_document"],
                "source_url": row["source_url"],
                "evidence_class": "GOVERNMENT_FACT",
            }

            await conn.execute(
                text(
                    """
                    INSERT INTO public.cwc_ap_nrld_2019
                    (
                        pic,
                        name,
                        operator,
                        latitude,
                        longitude,
                        completion_year,
                        river_basin,
                        river,
                        nearest_city,
                        seismic_zone,
                        dam_type,
                        height_m,
                        length_m,
                        dam_volume_m3,
                        gross_storage_mcm,
                        reservoir_area_m2,
                        effective_storage_mcm,
                        purpose,
                        spillway_capacity_cumecs,
                        source_authority,
                        source_document,
                        source_url,
                        evidence_class,
                        loaded_at
                    )
                    VALUES
                    (
                        :pic,
                        :name,
                        :operator,
                        :latitude,
                        :longitude,
                        :completion_year,
                        :river_basin,
                        :river,
                        :nearest_city,
                        :seismic_zone,
                        :dam_type,
                        :height_m,
                        :length_m,
                        :dam_volume_m3,
                        :gross_storage_mcm,
                        :reservoir_area_m2,
                        :effective_storage_mcm,
                        :purpose,
                        :spillway_capacity_cumecs,
                        :source_authority,
                        :source_document,
                        :source_url,
                        :evidence_class,
                        NOW()
                    )
                    ON CONFLICT (pic)
                    DO UPDATE SET
                        name=EXCLUDED.name,
                        operator=EXCLUDED.operator,
                        latitude=EXCLUDED.latitude,
                        longitude=EXCLUDED.longitude,
                        completion_year=EXCLUDED.completion_year,
                        river_basin=EXCLUDED.river_basin,
                        river=EXCLUDED.river,
                        nearest_city=EXCLUDED.nearest_city,
                        seismic_zone=EXCLUDED.seismic_zone,
                        dam_type=EXCLUDED.dam_type,
                        height_m=EXCLUDED.height_m,
                        length_m=EXCLUDED.length_m,
                        dam_volume_m3=EXCLUDED.dam_volume_m3,
                        gross_storage_mcm=EXCLUDED.gross_storage_mcm,
                        reservoir_area_m2=EXCLUDED.reservoir_area_m2,
                        effective_storage_mcm=EXCLUDED.effective_storage_mcm,
                        purpose=EXCLUDED.purpose,
                        spillway_capacity_cumecs=EXCLUDED.spillway_capacity_cumecs,
                        source_authority=EXCLUDED.source_authority,
                        source_document=EXCLUDED.source_document,
                        source_url=EXCLUDED.source_url,
                        evidence_class=EXCLUDED.evidence_class,
                        loaded_at=NOW()
                    """
                ),
                params,
            )


        # ====================================================
        # ENGINEERING PROFILE
        # ====================================================

        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS
                public.dam_barrage_engineering_profiles
                (
                    asset_id BIGINT PRIMARY KEY
                        REFERENCES public.assets(id)
                        ON DELETE CASCADE,

                    asset_code TEXT NOT NULL,
                    asset_type TEXT NOT NULL,

                    cwc_pic TEXT,
                    cwc_name TEXT,

                    cwc_latitude DOUBLE PRECISION,
                    cwc_longitude DOUBLE PRECISION,

                    river_basin TEXT,
                    river TEXT,
                    nearest_city TEXT,
                    seismic_zone TEXT,
                    structure_type TEXT,

                    height_m DOUBLE PRECISION,
                    length_m DOUBLE PRECISION,
                    dam_volume_m3 DOUBLE PRECISION,

                    gross_storage_mcm DOUBLE PRECISION,
                    reservoir_area_m2 DOUBLE PRECISION,
                    effective_storage_mcm DOUBLE PRECISION,

                    spillway_capacity_cumecs DOUBLE PRECISION,

                    purpose TEXT,
                    completion_year INTEGER,

                    source_authority TEXT,
                    source_document TEXT,
                    source_url TEXT,
                    evidence_class TEXT,

                    quality_status TEXT,
                    match_method TEXT,
                    match_score DOUBLE PRECISION,

                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )


        assets = (
            await conn.execute(
                text(
                    """
                    SELECT
                        id,
                        asset_code,
                        name,
                        district,
                        latitude,
                        longitude,
                        CAST(asset_type AS TEXT) AS asset_type
                    FROM public.assets
                    WHERE LOWER(CAST(asset_type AS TEXT))
                        IN ('dam','barrage')
                    ORDER BY id
                    """
                )
            )
        ).mappings().all()


        by_pic = {
            row["pic"]: row
            for row in cwc
        }

        exact = {}
        relaxed_map = {}

        for row in cwc:

            exact.setdefault(
                norm(row["name"]),
                [],
            ).append(row)

            relaxed_map.setdefault(
                relaxed(row["name"]),
                [],
            ).append(row)


        used = set()
        matched = []
        unresolved = []


        for asset in assets:

            selected = None
            method = None
            score = None


            pic = embedded_pic(
                asset["asset_code"]
            )

            if pic and pic in by_pic and pic not in used:
                selected = by_pic[pic]
                method = "EXACT_CWC_PIC"
                score = 1.0


            if selected is None:

                candidates = [
                    row
                    for row in exact.get(
                        norm(asset["name"]),
                        [],
                    )
                    if row["pic"] not in used
                ]

                if len(candidates) == 1:
                    selected = candidates[0]
                    method = "EXACT_NORMALIZED_NAME"
                    score = 0.995


            if selected is None:

                candidates = [
                    row
                    for row in relaxed_map.get(
                        relaxed(asset["name"]),
                        [],
                    )
                    if row["pic"] not in used
                ]

                if len(candidates) == 1:
                    selected = candidates[0]
                    method = "UNIQUE_RELAXED_NAME"
                    score = 0.98


            if selected is None:

                unresolved.append(
                    {
                        "asset_code": asset["asset_code"],
                        "name": asset["name"],
                    }
                )
                continue


            used.add(selected["pic"])


            params = {
                "asset_id": int(asset["id"]),
                "asset_code": asset["asset_code"],
                "asset_type": str(asset["asset_type"]).lower(),

                "cwc_pic": selected["pic"],
                "cwc_name": selected["name"],

                "cwc_latitude": number(selected["latitude"]),
                "cwc_longitude": number(selected["longitude"]),

                "river_basin": clean(selected["river_basin"]),
                "river": clean(selected["river"]),
                "nearest_city": clean(selected["nearest_city"]),
                "seismic_zone": clean(selected["seismic_zone"]),
                "structure_type": clean(selected["dam_type"]),

                "height_m": number(selected["height_m"]),
                "length_m": number(selected["length_m"]),
                "dam_volume_m3": number(selected["dam_volume_m3"]),

                "gross_storage_mcm":
                    number(selected["gross_storage_mcm"]),

                "reservoir_area_m2":
                    number(selected["reservoir_area_m2"]),

                "effective_storage_mcm":
                    number(selected["effective_storage_mcm"]),

                "spillway_capacity_cumecs":
                    number(selected["spillway_capacity_cumecs"]),

                "purpose": clean(selected["purpose"]),
                "completion_year":
                    integer(selected["completion_year"]),

                "source_authority":
                    "Government of India / Central Water Commission",

                "source_document":
                    "National Register of Large Dams 2019",

                "source_url":
                    selected["source_url"],

                "evidence_class":
                    "GOVERNMENT_FACT",

                "quality_status":
                    "CWC_NRLD_2019_VERIFIED",

                "match_method":
                    method,

                "match_score":
                    score,
            }


            await conn.execute(
                text(
                    """
                    INSERT INTO
                    public.dam_barrage_engineering_profiles
                    (
                        asset_id,
                        asset_code,
                        asset_type,
                        cwc_pic,
                        cwc_name,
                        cwc_latitude,
                        cwc_longitude,
                        river_basin,
                        river,
                        nearest_city,
                        seismic_zone,
                        structure_type,
                        height_m,
                        length_m,
                        dam_volume_m3,
                        gross_storage_mcm,
                        reservoir_area_m2,
                        effective_storage_mcm,
                        spillway_capacity_cumecs,
                        purpose,
                        completion_year,
                        source_authority,
                        source_document,
                        source_url,
                        evidence_class,
                        quality_status,
                        match_method,
                        match_score,
                        updated_at
                    )
                    VALUES
                    (
                        :asset_id,
                        :asset_code,
                        :asset_type,
                        :cwc_pic,
                        :cwc_name,
                        :cwc_latitude,
                        :cwc_longitude,
                        :river_basin,
                        :river,
                        :nearest_city,
                        :seismic_zone,
                        :structure_type,
                        :height_m,
                        :length_m,
                        :dam_volume_m3,
                        :gross_storage_mcm,
                        :reservoir_area_m2,
                        :effective_storage_mcm,
                        :spillway_capacity_cumecs,
                        :purpose,
                        :completion_year,
                        :source_authority,
                        :source_document,
                        :source_url,
                        :evidence_class,
                        :quality_status,
                        :match_method,
                        :match_score,
                        NOW()
                    )
                    ON CONFLICT (asset_id)
                    DO UPDATE SET
                        asset_code=EXCLUDED.asset_code,
                        asset_type=EXCLUDED.asset_type,
                        cwc_pic=EXCLUDED.cwc_pic,
                        cwc_name=EXCLUDED.cwc_name,
                        cwc_latitude=EXCLUDED.cwc_latitude,
                        cwc_longitude=EXCLUDED.cwc_longitude,
                        river_basin=EXCLUDED.river_basin,
                        river=EXCLUDED.river,
                        nearest_city=EXCLUDED.nearest_city,
                        seismic_zone=EXCLUDED.seismic_zone,
                        structure_type=EXCLUDED.structure_type,
                        height_m=EXCLUDED.height_m,
                        length_m=EXCLUDED.length_m,
                        dam_volume_m3=EXCLUDED.dam_volume_m3,
                        gross_storage_mcm=EXCLUDED.gross_storage_mcm,
                        reservoir_area_m2=EXCLUDED.reservoir_area_m2,
                        effective_storage_mcm=EXCLUDED.effective_storage_mcm,
                        spillway_capacity_cumecs=EXCLUDED.spillway_capacity_cumecs,
                        purpose=EXCLUDED.purpose,
                        completion_year=EXCLUDED.completion_year,
                        source_authority=EXCLUDED.source_authority,
                        source_document=EXCLUDED.source_document,
                        source_url=EXCLUDED.source_url,
                        evidence_class=EXCLUDED.evidence_class,
                        quality_status=EXCLUDED.quality_status,
                        match_method=EXCLUDED.match_method,
                        match_score=EXCLUDED.match_score,
                        updated_at=NOW()
                    """
                ),
                params,
            )


            matched.append(
                {
                    "asset_id": int(asset["id"]),
                    "asset_code": asset["asset_code"],
                    "asset_name": asset["name"],

                    "asset_latitude": number(asset["latitude"]),
                    "asset_longitude": number(asset["longitude"]),

                    "cwc_pic": selected["pic"],
                    "cwc_name": selected["name"],

                    "cwc_latitude":
                        number(selected["latitude"]),

                    "cwc_longitude":
                        number(selected["longitude"]),
                }
            )


        # ====================================================
        # HYDROLOGY
        # ====================================================

        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS
                public.dam_barrage_current_hydrology
                (
                    asset_id BIGINT PRIMARY KEY
                        REFERENCES public.assets(id)
                        ON DELETE CASCADE,

                    asset_code TEXT NOT NULL,

                    level_station TEXT,
                    water_level_m DOUBLE PRECISION,
                    water_level_time TIMESTAMPTZ,

                    storage_station TEXT,
                    current_storage_mcm DOUBLE PRECISION,
                    storage_time TIMESTAMPTZ,

                    source_authority TEXT,
                    evidence_class TEXT,

                    level_match_method TEXT,
                    storage_match_method TEXT,

                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )


        def match_station(station):

            station_name = station["station"]

            name_matches = [
                asset
                for asset in matched
                if (
                    norm(station_name)
                    == norm(asset["asset_name"])
                    or norm(station_name)
                    == norm(asset["cwc_name"])
                )
            ]

            if len(name_matches) == 1:
                return name_matches[0], "EXACT_STATION_NAME"


            relaxed_matches = [
                asset
                for asset in matched
                if (
                    relaxed(station_name)
                    == relaxed(asset["asset_name"])
                    or relaxed(station_name)
                    == relaxed(asset["cwc_name"])
                )
            ]

            if len(relaxed_matches) == 1:
                return relaxed_matches[0], "RELAXED_STATION_NAME"


            geo = []

            for asset in matched:

                target_lat = (
                    asset["cwc_latitude"]
                    if asset["cwc_latitude"] is not None
                    else asset["asset_latitude"]
                )

                target_lon = (
                    asset["cwc_longitude"]
                    if asset["cwc_longitude"] is not None
                    else asset["asset_longitude"]
                )

                km = distance_km(
                    station["latitude"],
                    station["longitude"],
                    target_lat,
                    target_lon,
                )

                if km is not None and km <= 2.0:
                    geo.append((km, asset))

            geo.sort(key=lambda item: item[0])

            if len(geo) == 1:
                return geo[0][1], "GEOGRAPHIC_2KM"

            if len(geo) > 1:
                if geo[1][0] - geo[0][0] >= 0.5:
                    return geo[0][1], "GEOGRAPHIC_2KM"

            return None, None


        level_rows = latest_station_rows(
            LEVEL_FILE,
            "Manual Daily Reservoir water level (m)",
        )

        storage_rows = latest_station_rows(
            STORAGE_FILE,
            "Manual Daily Reservoir storage (mcm)",
        )


        hydro = {}


        for station in level_rows:

            asset, method = match_station(station)

            if not asset:
                continue

            item = hydro.setdefault(
                asset["asset_id"],
                {
                    "asset": asset,
                },
            )

            item["level"] = {
                **station,
                "method": method,
            }


        for station in storage_rows:

            asset, method = match_station(station)

            if not asset:
                continue

            item = hydro.setdefault(
                asset["asset_id"],
                {
                    "asset": asset,
                },
            )

            item["storage"] = {
                **station,
                "method": method,
            }


        for asset_id, item in hydro.items():

            asset = item["asset"]

            level = item.get("level", {})
            storage = item.get("storage", {})

            params = {
                "asset_id": asset_id,
                "asset_code": asset["asset_code"],

                "level_station": level.get("station"),
                "water_level_m": level.get("value"),
                "water_level_time": level.get("observed"),

                "storage_station": storage.get("station"),
                "current_storage_mcm": storage.get("value"),
                "storage_time": storage.get("observed"),

                "source_authority":
                    "National Water Data Portal / Andhra Pradesh Surface Water",

                "evidence_class":
                    "GOVERNMENT_OBSERVATION",

                "level_match_method":
                    level.get("method"),

                "storage_match_method":
                    storage.get("method"),
            }


            await conn.execute(
                text(
                    """
                    INSERT INTO
                    public.dam_barrage_current_hydrology
                    (
                        asset_id,
                        asset_code,
                        level_station,
                        water_level_m,
                        water_level_time,
                        storage_station,
                        current_storage_mcm,
                        storage_time,
                        source_authority,
                        evidence_class,
                        level_match_method,
                        storage_match_method,
                        updated_at
                    )
                    VALUES
                    (
                        :asset_id,
                        :asset_code,
                        :level_station,
                        :water_level_m,
                        :water_level_time,
                        :storage_station,
                        :current_storage_mcm,
                        :storage_time,
                        :source_authority,
                        :evidence_class,
                        :level_match_method,
                        :storage_match_method,
                        NOW()
                    )
                    ON CONFLICT (asset_id)
                    DO UPDATE SET
                        asset_code=EXCLUDED.asset_code,
                        level_station=COALESCE(
                            EXCLUDED.level_station,
                            dam_barrage_current_hydrology.level_station
                        ),
                        water_level_m=COALESCE(
                            EXCLUDED.water_level_m,
                            dam_barrage_current_hydrology.water_level_m
                        ),
                        water_level_time=COALESCE(
                            EXCLUDED.water_level_time,
                            dam_barrage_current_hydrology.water_level_time
                        ),
                        storage_station=COALESCE(
                            EXCLUDED.storage_station,
                            dam_barrage_current_hydrology.storage_station
                        ),
                        current_storage_mcm=COALESCE(
                            EXCLUDED.current_storage_mcm,
                            dam_barrage_current_hydrology.current_storage_mcm
                        ),
                        storage_time=COALESCE(
                            EXCLUDED.storage_time,
                            dam_barrage_current_hydrology.storage_time
                        ),
                        source_authority=EXCLUDED.source_authority,
                        evidence_class=EXCLUDED.evidence_class,
                        level_match_method=COALESCE(
                            EXCLUDED.level_match_method,
                            dam_barrage_current_hydrology.level_match_method
                        ),
                        storage_match_method=COALESCE(
                            EXCLUDED.storage_match_method,
                            dam_barrage_current_hydrology.storage_match_method
                        ),
                        updated_at=NOW()
                    """
                ),
                params,
            )


        raw_count = int(
            await conn.scalar(
                text(
                    """
                    SELECT COUNT(*)
                    FROM public.cwc_ap_nrld_2019
                    """
                )
            )
        )

        profile_count = int(
            await conn.scalar(
                text(
                    """
                    SELECT COUNT(*)
                    FROM public.dam_barrage_engineering_profiles
                    """
                )
            )
        )

        hydro_count = int(
            await conn.scalar(
                text(
                    """
                    SELECT COUNT(*)
                    FROM public.dam_barrage_current_hydrology
                    """
                )
            )
        )


        prakasam = (
            await conn.execute(
                text(
                    """
                    SELECT
                        a.asset_code,
                        a.name,
                        p.cwc_pic,
                        p.cwc_name,
                        p.river,
                        p.river_basin,
                        p.structure_type,
                        p.height_m,
                        p.length_m,
                        p.gross_storage_mcm,
                        p.effective_storage_mcm,
                        p.spillway_capacity_cumecs,
                        p.completion_year,
                        p.source_authority,
                        h.water_level_m,
                        h.water_level_time,
                        h.current_storage_mcm,
                        h.storage_time
                    FROM public.assets a
                    LEFT JOIN
                        public.dam_barrage_engineering_profiles p
                        ON p.asset_id=a.id
                    LEFT JOIN
                        public.dam_barrage_current_hydrology h
                        ON h.asset_id=a.id
                    WHERE a.asset_code='AP_DAM_00001'
                    LIMIT 1
                    """
                )
            )
        ).mappings().first()


        print()
        print("=" * 100)
        print("ML-7C DATABASE RECOVERY")
        print("=" * 100)

        print("Canonical assets :", len(assets))
        print("CWC raw rows     :", raw_count)
        print("Matched profiles :", profile_count)
        print("Unresolved       :", len(unresolved))
        print("Hydrology assets :", hydro_count)

        print()
        print("PRAKASAM")

        for key, value in prakasam.items():
            print(f"{key:<30}: {value}")


        if raw_count != 166:
            raise RuntimeError(
                "CWC DB count is not 166"
            )


        if prakasam["cwc_pic"] != "AP01MH0009":
            raise RuntimeError(
                "Prakasam CWC matching failed"
            )


        if abs(
            float(prakasam["height_m"]) - 22.25
        ) > 0.01:
            raise RuntimeError(
                "Prakasam height verification failed"
            )


        if abs(
            float(prakasam["length_m"]) - 1233.0
        ) > 0.1:
            raise RuntimeError(
                "Prakasam length verification failed"
            )


        print()
        print("DATABASE_RECOVERY=PASS")


    await engine.dispose()


asyncio.run(main())