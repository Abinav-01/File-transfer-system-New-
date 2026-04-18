"""Record when cleanup or manual deletion removed the stored object.

Revision ID: 7c4a2d9e61b0
Revises: 408633f7b277
"""

from alembic import op
import sqlalchemy as sa

revision = "7c4a2d9e61b0"
down_revision = "408633f7b277"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "uploads",
        sa.Column("object_deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("uploads", "object_deleted_at")
