from pathlib import Path


PATH = Path(
    "/app/scripts/"
    "step6c2b_import_statewide_ap_bridges.py"
)

source = PATH.read_text(
    encoding="utf-8"
)


def replace_region(
    source,
    start_marker,
    end_marker,
    replacement,
    label
):

    start = source.find(
        start_marker
    )

    if start < 0:
        raise RuntimeError(
            f"{label}: start marker not found"
        )

    end = source.find(
        end_marker,
        start
    )

    if end < 0:
        raise RuntimeError(
            f"{label}: end marker not found"
        )

    return (
        source[:start]
        + replacement
        + source[end:]
    )


# ============================================================
# A. Tell safety gate that we explicitly support the four
#    required schema fields.
# ============================================================

source = replace_region(
    source,

    "        supported_required = {",

    "\n\n        dangerous_required",

'''        supported_required = {
            "asset_code",
            "name",
            type_column,

            # Required SIMRAS asset schema fields handled
            # explicitly during OSM bridge promotion.
            "status",
            "identity_status",
            "representative_geometry",
            "is_estimated",
        }''',

    "supported_required"
)


# ============================================================
# B. Keep ordinary nullable asset fields parameterized.
#
# status / identity_status / is_estimated /
# representative_geometry are handled as special SQL
# expressions below.
# ============================================================

source = replace_region(
    source,

    "        optional_candidates = [",

    "\n\n        for column in optional_candidates:",

'''        optional_candidates = [
            "latitude",
            "longitude",
            "built_year",
            "material",
            "length_m",
            "width_m",
        ]''',

    "optional_candidates"
)


# ============================================================
# C. Replace INSERT construction.
#
# status:
#   reuse an existing valid DB status value, preferring ACTIVE.
#
# identity_status:
#   reuse a valid existing enum/text value, preferring
#   SOURCE_REPORTED then UNVERIFIED.
#
# representative_geometry:
#   real OSM bridge centroid in WGS84 / EPSG:4326.
#
# is_estimated:
#   TRUE because this canonical asset was promoted from an
#   open mapping source rather than primary-government identity.
# ============================================================

source = replace_region(
    source,

    '        sql_columns = ", ".join(',

    "\n\n        for index, row in enumerate(",

'''        sql_column_names = list(
            insertable_columns
        )

        sql_value_expressions = [
            f":{column}"
            for column
            in insertable_columns
        ]

        if "status" in asset_columns:

            sql_column_names.append(
                "status"
            )

            sql_value_expressions.append(
                """
                (
                    SELECT a.status
                    FROM public.assets a
                    WHERE a.status IS NOT NULL
                    ORDER BY
                        CASE
                            WHEN CAST(a.status AS TEXT) = 'ACTIVE'
                            THEN 0
                            ELSE 1
                        END,
                        a.id
                    LIMIT 1
                )
                """
            )

        if "identity_status" in asset_columns:

            sql_column_names.append(
                "identity_status"
            )

            sql_value_expressions.append(
                """
                (
                    SELECT a.identity_status
                    FROM public.assets a
                    WHERE a.identity_status IS NOT NULL
                    ORDER BY
                        CASE
                            WHEN CAST(
                                a.identity_status
                                AS TEXT
                            ) = 'SOURCE_REPORTED'
                            THEN 0

                            WHEN CAST(
                                a.identity_status
                                AS TEXT
                            ) = 'UNVERIFIED'
                            THEN 1

                            ELSE 2
                        END,
                        a.id
                    LIMIT 1
                )
                """
            )

        if "representative_geometry" in asset_columns:

            sql_column_names.append(
                "representative_geometry"
            )

            sql_value_expressions.append(
                """
                ST_SetSRID(
                    ST_MakePoint(
                        :geom_longitude,
                        :geom_latitude
                    ),
                    4326
                )
                """
            )

        if "is_estimated" in asset_columns:

            sql_column_names.append(
                "is_estimated"
            )

            sql_value_expressions.append(
                "TRUE"
            )

        sql_columns = ", ".join(
            f'"{column}"'
            for column
            in sql_column_names
        )

        sql_values = ", ".join(
            sql_value_expressions
        )

        asset_insert_sql = text(
            f"""
            INSERT INTO
                public.assets
                ({sql_columns})
            VALUES
                ({sql_values})
            RETURNING id
            """
        )''',

    "asset_insert_sql"
)


# ============================================================
# D. Add OSM centroid parameters used by PostGIS geometry.
# ============================================================

marker = '''                if "latitude" in insertable_columns:
'''

geometry_params = '''                # Coordinates are always available from
                # the actual OSM bridge LineString centroid.
                params["geom_longitude"] = row[
                    "longitude"
                ]

                params["geom_latitude"] = row[
                    "latitude"
                ]

'''

if geometry_params.strip() not in source:

    position = source.find(
        marker
    )

    if position < 0:
        raise RuntimeError(
            "Could not find per-asset parameter block."
        )

    source = (
        source[:position]
        + geometry_params
        + source[position:]
    )


PATH.write_text(
    source,
    encoding="utf-8"
)

print(
    "[PATCHED] Required public.assets fields supported."
)

print(
    "[PATCHED] representative_geometry = real OSM centroid."
)

print(
    "[PATCHED] existing DB status/identity enum values reused."
)

print(
    "[PATCHED] is_estimated = TRUE for OSM-promoted assets."
)
