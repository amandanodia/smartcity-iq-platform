"""Add source-shaped raw import staging records.

Revision ID: 0002_raw_import_staging
Revises: 0001_initial_schema
"""
from alembic import op

from app import db
from app import models  # noqa: F401 - register all tables on metadata

revision = "0002_raw_import_staging"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade():
    # checkfirst supports both databases upgraded from the Phase 2 baseline
    # and fresh databases where the initial baseline migration created all
    # current metadata tables.
    db.metadata.tables["raw_imported_records"].create(bind=op.get_bind(), checkfirst=True)


def downgrade():
    db.metadata.tables["raw_imported_records"].drop(bind=op.get_bind(), checkfirst=True)
