"""add_endpoint_azure_fields

Revision ID: 0004_add_endpoint_azure_fields
Revises: 0003_refactor_dataset_relationships
Create Date: 2025-01-12 16:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to endpoints table
    op.add_column("endpoints", sa.Column("name", sa.String(length=255), nullable=True))
    op.add_column(
        "endpoints",
        sa.Column("azure_endpoint_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "endpoints",
        sa.Column("azure_endpoint_url", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "endpoints",
        sa.Column("auth_mode", sa.String(length=50), nullable=True, default="key"),
    )
    op.add_column(
        "endpoints",
        sa.Column("provisioning_state", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "endpoints", sa.Column("description", sa.String(length=1000), nullable=True)
    )
    op.add_column("endpoints", sa.Column("traffic", sa.JSON(), nullable=True))
    op.add_column("endpoints", sa.Column("tags", sa.JSON(), nullable=True))


def downgrade():
    # Remove the columns added in upgrade
    op.drop_column("endpoints", "tags")
    op.drop_column("endpoints", "traffic")
    op.drop_column("endpoints", "description")
    op.drop_column("endpoints", "provisioning_state")
    op.drop_column("endpoints", "auth_mode")
    op.drop_column("endpoints", "azure_endpoint_url")
    op.drop_column("endpoints", "azure_endpoint_name")
    op.drop_column("endpoints", "name")
