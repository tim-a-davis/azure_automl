"""Add private field to datasets

Revision ID: 0009
Revises: 0008
Create Date: 2025-07-19 12:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    """Add private field to datasets table."""

    # Add private column to datasets table
    with op.batch_alter_table("datasets", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "private", sa.Boolean(), nullable=False, server_default=sa.text("0")
            )
        )


def downgrade():
    """Remove private field from datasets table."""

    # Remove private column from datasets table
    with op.batch_alter_table("datasets", schema=None) as batch_op:
        batch_op.drop_column("private")
