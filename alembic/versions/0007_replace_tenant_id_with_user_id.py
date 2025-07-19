"""Replace tenant_id with user_id in experiments, runs, and endpoints

Revision ID: 0007
Revises: 0006
Create Date: 2025-07-13 10:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    """Replace tenant_id with user_id in experiments, runs, and endpoints tables."""
    # For experiments table
    with op.batch_alter_table("experiments", schema=None) as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.String(255), nullable=True))
        batch_op.drop_column("tenant_id")

    # For runs table
    with op.batch_alter_table("runs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.String(255), nullable=True))
        batch_op.drop_column("tenant_id")

    # For endpoints table - need to drop index first
    with op.batch_alter_table("endpoints", schema=None) as batch_op:
        # Drop the index that depends on tenant_id
        try:
            batch_op.drop_index("ix_endpoint_tenant_id")
        except Exception:
            # Index might not exist, continue
            pass
        batch_op.add_column(sa.Column("user_id", sa.String(255), nullable=True))
        batch_op.drop_column("tenant_id")
        # Create new index on user_id
        batch_op.create_index("ix_endpoint_user_id", ["user_id", "id"])


def downgrade():
    """Revert user_id back to tenant_id."""
    # For experiments table
    with op.batch_alter_table("experiments", schema=None) as batch_op:
        batch_op.add_column(sa.Column("tenant_id", sa.String(255), nullable=False))
        batch_op.drop_column("user_id")

    # For runs table
    with op.batch_alter_table("runs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("tenant_id", sa.String(255), nullable=False))
        batch_op.drop_column("user_id")

    # For endpoints table - recreate original index
    with op.batch_alter_table("endpoints", schema=None) as batch_op:
        # Drop the new index
        try:
            batch_op.drop_index("ix_endpoint_user_id")
        except Exception:
            pass
        batch_op.add_column(sa.Column("tenant_id", sa.String(255), nullable=False))
        batch_op.drop_column("user_id")
        # Recreate original index
        batch_op.create_index("ix_endpoint_tenant_id", ["tenant_id", "id"])
        batch_op.drop_column("user_id")
