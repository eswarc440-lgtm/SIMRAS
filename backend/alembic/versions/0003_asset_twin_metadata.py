"""Add provenance and dimensions for asset-specific twin models.

Revision ID: 0003_asset_twin_metadata
Revises: 0002_statewide_map_features
Create Date: 2026-08-29
"""

import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003_asset_twin_metadata"
down_revision = "0002_statewide_map_features"
branch_labels = None
depends_on = None


FLAGSHIP_MODELS = {
    "AP_DAM_00001": {
        "format": "parametric",
        "version": "1.0",
        "fidelity_level": "L1",
        "model_source": "AP Water Resources Department published dimensions",
        "source_url": "https://irrigation.ap.gov.in/wrd/home/krishna",
        "dimensions": {
            "length_m": 1232.92,
            "gate_count": 70,
            "gate_width_m": 12.19,
            "gate_height_m": 3.66,
            "constructed_year": 1957,
            "representation": "dimension_derived_parametric",
        },
    },
    "AP_BR_00001": {
        "format": "parametric",
        "version": "1.0",
        "fidelity_level": "L1",
        "model_source": "Published Godavari Arch Bridge engineering profile",
        "source_url": "https://rmc.ap.gov.in/tourism/prominent_places_rajahmundry",
        "dimensions": {
            "length_m": 2745.0,
            "span_count": 28,
            "main_span_m": 97.55,
            "structural_form": "bowstring_girder",
            "material": "prestressed_concrete",
            "representation": "dimension_derived_parametric",
        },
    },
}


def upgrade() -> None:
    op.add_column("asset_models", sa.Column("source_url", sa.Text(), nullable=True))
    op.add_column(
        "asset_models",
        sa.Column(
            "dimensions",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    connection = op.get_bind()
    statement = sa.text(
        """
        UPDATE asset_models AS model
        SET
            format = :format,
            version = :version,
            fidelity_level = :fidelity_level,
            model_source = :model_source,
            source_url = :source_url,
            dimensions = CAST(:dimensions AS jsonb),
            is_asset_specific = true,
            updated_at = now()
        FROM assets AS asset
        WHERE model.asset_id = asset.id
          AND asset.asset_code = :asset_code
          AND model.is_active = true
        """
    )

    for asset_code, metadata in FLAGSHIP_MODELS.items():
        connection.execute(
            statement,
            {
                "asset_code": asset_code,
                **{key: value for key, value in metadata.items() if key != "dimensions"},
                "dimensions": json.dumps(metadata["dimensions"]),
            },
        )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            UPDATE asset_models AS model
            SET
                format = 'procedural',
                version = '1',
                fidelity_level = 'L0',
                model_source = 'SIMRAS procedural illustration',
                is_asset_specific = false,
                updated_at = now()
            FROM assets AS asset
            WHERE model.asset_id = asset.id
              AND asset.asset_code IN ('AP_DAM_00001', 'AP_BR_00001')
              AND model.is_active = true
            """
        )
    )
    op.drop_column("asset_models", "dimensions")
    op.drop_column("asset_models", "source_url")