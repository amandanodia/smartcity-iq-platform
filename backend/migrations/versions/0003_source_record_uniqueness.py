"""Prevent duplicate normalized records from the same dataset.

Revision ID: 0003_source_record_uniqueness
Revises: 0002_raw_import_staging
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_source_record_uniqueness"
down_revision = "0002_raw_import_staging"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    for table, name in [
        ("air_quality", "uq_air_quality_dataset_record"),
        ("traffic_statistics", "uq_traffic_dataset_record"),
        ("road_accidents", "uq_road_accidents_dataset_record"),
        ("water_statistics", "uq_water_dataset_record"),
        ("population_statistics", "uq_population_dataset_record"),
        ("infrastructure", "uq_infrastructure_dataset_record"),
    ]:
        existing = {item["name"] for item in inspector.get_unique_constraints(table)}
        if name not in existing:
            op.create_unique_constraint(name, table, ["dataset_id", "source_record_id"])


def downgrade():
    inspector = sa.inspect(op.get_bind())
    for table, name in [
        ("infrastructure", "uq_infrastructure_dataset_record"),
        ("population_statistics", "uq_population_dataset_record"),
        ("water_statistics", "uq_water_dataset_record"),
        ("road_accidents", "uq_road_accidents_dataset_record"),
        ("traffic_statistics", "uq_traffic_dataset_record"),
        ("air_quality", "uq_air_quality_dataset_record"),
    ]:
        existing = {item["name"] for item in inspector.get_unique_constraints(table)}
        if name in existing:
            op.drop_constraint(name, table, type_="unique")
