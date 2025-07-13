"""Add default roles

Revision ID: 0005
Revises: 0004
Create Date: 2025-07-13 12:00:00.000000

"""

from uuid import uuid4

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    """Add default roles to the roles table."""
    # Create a connection to execute SQL
    connection = op.get_bind()

    # Define the default roles
    roles = [
        {"id": str(uuid4()), "name": "USER"},
        {"id": str(uuid4()), "name": "MAINTAINER"},
        {"id": str(uuid4()), "name": "ADMIN"},
    ]

    # Insert the roles
    for role in roles:
        connection.execute(
            sa.text(
                "INSERT INTO roles (id, name, created_at, updated_at) VALUES (:id, :name, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            role,
        )


def downgrade():
    """Remove default roles from the roles table."""
    connection = op.get_bind()

    # Remove the default roles
    connection.execute(
        sa.text("DELETE FROM roles WHERE name IN ('USER', 'MAINTAINER', 'ADMIN')")
    )
