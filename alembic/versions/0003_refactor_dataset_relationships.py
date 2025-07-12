"""Refactor dataset relationships and add user tracking

Revision ID: 0003
Revises: 0002
Create Date: 2025-07-12 12:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER

from alembic import op

# revision identifiers, used by Alembic.
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Refactor dataset relationships and add user tracking."""

    # Get database dialect
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    # Handle SQLite vs SQL Server differently
    if dialect_name == "sqlite":
        # Use batch operations for SQLite
        with op.batch_alter_table("datasets") as batch_op:
            # Drop existing indexes
            batch_op.drop_index("ix_dataset_tenant_name")
            batch_op.drop_index("ix_dataset_tenant_name_version")

            # Add new columns
            batch_op.add_column(sa.Column("uploaded_by", sa.String(36), nullable=True))
            batch_op.add_column(sa.Column("tags", sa.JSON(), nullable=True))

            # Drop tenant_id column
            batch_op.drop_column("tenant_id")

            # Create new indexes
            batch_op.create_index("ix_dataset_uploaded_by", ["uploaded_by"])
            batch_op.create_index(
                "ix_dataset_name_version", ["name", "version"], unique=True
            )

        # Add dataset_id columns to other tables (without foreign keys for now in SQLite)
        with op.batch_alter_table("models") as batch_op:
            batch_op.add_column(sa.Column("dataset_id", sa.String(36), nullable=True))

        with op.batch_alter_table("endpoints") as batch_op:
            batch_op.add_column(sa.Column("dataset_id", sa.String(36), nullable=True))

    else:
        # SQL Server operations
        # Drop existing indexes that depend on tenant_id
        op.drop_index("ix_dataset_tenant_name", "datasets")
        op.drop_index("ix_dataset_tenant_name_version", "datasets")

        # Add uploaded_by and tags to datasets table
        op.add_column(
            "datasets", sa.Column("uploaded_by", UNIQUEIDENTIFIER(), nullable=True)
        )
        op.add_column("datasets", sa.Column("tags", sa.JSON(), nullable=True))

        # Remove tenant_id from datasets table
        op.drop_column("datasets", "tenant_id")

        # Add dataset_id foreign key to models table - use UNIQUEIDENTIFIER for SQL Server
        op.add_column(
            "models", sa.Column("dataset_id", UNIQUEIDENTIFIER(), nullable=True)
        )
        op.create_foreign_key(
            "fk_models_dataset_id",
            "models",
            "datasets",
            ["dataset_id"],
            ["id"],
            ondelete="SET NULL",
        )

        # Add dataset_id foreign key to endpoints table
        op.add_column(
            "endpoints", sa.Column("dataset_id", UNIQUEIDENTIFIER(), nullable=True)
        )
        op.create_foreign_key(
            "fk_endpoints_dataset_id",
            "endpoints",
            "datasets",
            ["dataset_id"],
            ["id"],
            ondelete="SET NULL",
        )

        # Create new indexes
        op.create_index("ix_dataset_uploaded_by", "datasets", ["uploaded_by"])
        op.create_index(
            "ix_dataset_name_version", "datasets", ["name", "version"], unique=True
        )


def downgrade() -> None:
    """Revert dataset relationship changes."""

    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name == "sqlite":
        # SQLite batch operations
        with op.batch_alter_table("endpoints") as batch_op:
            batch_op.drop_column("dataset_id")

        with op.batch_alter_table("models") as batch_op:
            batch_op.drop_column("dataset_id")

        with op.batch_alter_table("datasets") as batch_op:
            # Drop new indexes
            batch_op.drop_index("ix_dataset_name_version")
            batch_op.drop_index("ix_dataset_uploaded_by")

            # Add tenant_id back
            batch_op.add_column(
                sa.Column(
                    "tenant_id", sa.String(255), nullable=False, server_default=""
                )
            )

            # Remove new columns
            batch_op.drop_column("tags")
            batch_op.drop_column("uploaded_by")

            # Recreate original indexes
            batch_op.create_index("ix_dataset_tenant_name", ["tenant_id", "name"])
            batch_op.create_index(
                "ix_dataset_tenant_name_version",
                ["tenant_id", "name", "version"],
                unique=True,
            )
    else:
        # SQL Server operations
        # Drop new indexes
        op.drop_index("ix_dataset_name_version", "datasets")
        op.drop_index("ix_dataset_uploaded_by", "datasets")

        # Drop foreign keys and columns from endpoints
        op.drop_constraint("fk_endpoints_dataset_id", "endpoints", type_="foreignkey")
        op.drop_column("endpoints", "dataset_id")

        # Drop foreign keys and columns from models
        op.drop_constraint("fk_models_dataset_id", "models", type_="foreignkey")
        op.drop_column("models", "dataset_id")

        # Add tenant_id back to datasets
        op.add_column(
            "datasets",
            sa.Column("tenant_id", sa.String(255), nullable=False, server_default=""),
        )

        # Remove new columns from datasets
        op.drop_column("datasets", "tags")
        op.drop_column("datasets", "uploaded_by")

        # Recreate original indexes
        op.create_index("ix_dataset_tenant_name", "datasets", ["tenant_id", "name"])
        op.create_index(
            "ix_dataset_tenant_name_version",
            "datasets",
            ["tenant_id", "name", "version"],
            unique=True,
        )
