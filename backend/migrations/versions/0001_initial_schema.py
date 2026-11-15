"""Create the SmartCity IQ relational schema.

Revision ID: 0001_initial_schema
Revises:
"""
from alembic import op

from app import db
from app import models  # noqa: F401 - register all tables on metadata

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # This is the baseline revision. Subsequent revisions should use explicit
    # Alembic operations so upgrades remain incremental and reviewable.
    db.metadata.create_all(bind=op.get_bind())


def downgrade():
    db.metadata.drop_all(bind=op.get_bind())
