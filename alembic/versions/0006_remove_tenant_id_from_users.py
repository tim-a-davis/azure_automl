"""Remove tenant_id from users table

Revision ID: 0006
Revises: 0005
Create Date: 2025-07-13 14:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    """Remove tenant_id from users table and update index."""
    # Drop the existing index that includes tenant_id
    op.drop_index("ix_user_tenant_name", table_name="users")

    # Drop the tenant_id column
    op.drop_column("users", "tenant_id")

    # Create a new simple index on user id
    op.create_index("ix_user_id", "users", ["id"])


def downgrade():
    """Add tenant_id back to users table."""
    # Drop the new index
    op.drop_index("ix_user_id", table_name="users")

    # Add the tenant_id column back
    op.add_column(
        "users",
        sa.Column(
            "tenant_id", sa.String(255), nullable=False, server_default="default"
        ),
    )

    # Recreate the original index
    op.create_index("ix_user_tenant_name", "users", ["tenant_id", "id"])
    op.create_index("ix_user_tenant_name", "users", ["tenant_id", "id"])
