"""Enhance model deployment schema

Revision ID: 0008
Revises: 0007
Create Date: 2025-07-19 10:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy import JSON, Integer, String, TypeDecorator
from sqlalchemy import String as SQLString
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER

from alembic import op


class UUID(TypeDecorator):
    """Cross-database UUID type that works with both SQLite and SQL Server."""

    impl = SQLString
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "sqlite":
            return dialect.type_descriptor(SQLString(36))
        elif dialect.name == "mssql":
            return dialect.type_descriptor(UNIQUEIDENTIFIER())
        else:
            return dialect.type_descriptor(SQLString(36))


# revision identifiers, used by Alembic.
revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    """Enhance model deployment schema with comprehensive tracking."""

    # Update Models Table - remove tenant_id and add new fields
    with op.batch_alter_table("models", schema=None) as batch_op:
        # Drop old index
        try:
            batch_op.drop_index("ix_model_tenant_name")
        except Exception:
            # Index might not exist, continue
            pass

        # Remove tenant_id and add user_id
        batch_op.add_column(
            sa.Column(
                "user_id",
                UUID,
                nullable=False,
                server_default="00000000-0000-0000-0000-000000000000",
            )
        )
        batch_op.drop_column("tenant_id")

        # Add new model tracking fields
        batch_op.add_column(sa.Column("experiment_id", UUID, nullable=True))
        batch_op.add_column(sa.Column("run_id", UUID, nullable=True))
        batch_op.add_column(sa.Column("algorithm", String(255), nullable=True))
        batch_op.add_column(sa.Column("azure_model_name", String(255), nullable=True))
        batch_op.add_column(sa.Column("azure_model_version", String(50), nullable=True))
        batch_op.add_column(sa.Column("model_uri", String(1000), nullable=True))
        batch_op.add_column(sa.Column("best_score", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("performance_metrics", JSON, nullable=True))
        batch_op.add_column(sa.Column("model_metadata", JSON, nullable=True))
        batch_op.add_column(
            sa.Column(
                "registration_status",
                String(50),
                nullable=False,
                server_default="pending",
            )
        )
        batch_op.add_column(sa.Column("error_message", String(1000), nullable=True))

        # Create new indexes
        batch_op.create_index("ix_models_user_id", ["user_id"])
        batch_op.create_index("ix_models_run_id", ["run_id"])
        batch_op.create_index("ix_models_experiment_id", ["experiment_id"])
        batch_op.create_index(
            "ix_models_azure_model", ["azure_model_name", "azure_model_version"]
        )

    # Add foreign key constraints (after column creation) - Skip for SQL Server cascade issues
    # Note: Foreign keys will be enforced at application level for now
    # op.create_foreign_key(
    #     "fk_models_experiment_id",
    #     "models", "experiments",
    #     ["experiment_id"], ["id"],
    #     ondelete="SET NULL"
    # )
    #
    # op.create_foreign_key(
    #     "fk_models_run_id",
    #     "models", "runs",
    #     ["run_id"], ["id"],
    #     ondelete="SET NULL"
    # )

    # Update Endpoints Table - add new fields
    with op.batch_alter_table("endpoints", schema=None) as batch_op:
        batch_op.add_column(sa.Column("experiment_id", UUID, nullable=True))
        batch_op.add_column(sa.Column("run_id", UUID, nullable=True))
        batch_op.add_column(
            sa.Column(
                "deployment_status",
                String(50),
                nullable=True,
                server_default="creating",
            )
        )
        batch_op.add_column(sa.Column("deployment_metadata", JSON, nullable=True))
        batch_op.add_column(sa.Column("endpoint_metadata", JSON, nullable=True))

    # Add foreign key constraints for endpoints - Skip for SQL Server cascade issues
    # op.create_foreign_key(
    #     "fk_endpoints_experiment_id",
    #     "endpoints", "experiments",
    #     ["experiment_id"], ["id"],
    #     ondelete="SET NULL"
    # )
    #
    # op.create_foreign_key(
    #     "fk_endpoints_run_id",
    #     "endpoints", "runs",
    #     ["run_id"], ["id"],
    #     ondelete="SET NULL"
    # )

    # Create New Deployments Table
    op.create_table(
        "deployments",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("endpoint_id", UUID, nullable=False),
        sa.Column("model_id", UUID, nullable=False),
        sa.Column("deployment_name", String(255), nullable=False),
        sa.Column("azure_deployment_name", String(255), nullable=True),
        sa.Column(
            "instance_type",
            String(100),
            nullable=False,
            server_default="Standard_DS3_v2",
        ),
        sa.Column("instance_count", Integer, nullable=False, server_default="1"),
        sa.Column("traffic_percentage", Integer, nullable=False, server_default="0"),
        sa.Column(
            "deployment_status", String(50), nullable=False, server_default="creating"
        ),
        sa.Column("provisioning_state", String(50), nullable=True),
        sa.Column("deployment_config", JSON, nullable=True),
        sa.Column("error_message", String(1000), nullable=True),
        sa.Column(
            "created_at", sa.DateTime, nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()
        ),
    )

    # Create indexes for deployments table
    op.create_index("ix_deployments_endpoint_id", "deployments", ["endpoint_id"])
    op.create_index("ix_deployments_model_id", "deployments", ["model_id"])
    op.create_index("ix_deployments_user_id", "deployments", ["user_id"])
    op.create_index(
        "ix_deployment_name_endpoint",
        "deployments",
        ["endpoint_id", "deployment_name"],
        unique=True,
    )

    # Create foreign key constraints for deployments table - Skip for SQL Server cascade issues
    # Foreign keys will be enforced at application level for now
    # op.create_foreign_key(
    #     "fk_deployments_endpoint_id",
    #     "deployments", "endpoints",
    #     ["endpoint_id"], ["id"],
    #     ondelete="CASCADE"
    # )
    #
    # op.create_foreign_key(
    #     "fk_deployments_model_id",
    #     "deployments", "models",
    #     ["model_id"], ["id"],
    #     ondelete="CASCADE"
    # )
    #
    # op.create_foreign_key(
    #     "fk_deployments_user_id",
    #     "deployments", "users",
    #     ["user_id"], ["id"],
    #     ondelete="CASCADE"
    # )


def downgrade():
    """Revert the model deployment schema enhancements."""

    # Drop deployments table
    op.drop_table("deployments")

    # Revert endpoints table changes
    with op.batch_alter_table("endpoints", schema=None) as batch_op:
        batch_op.drop_column("endpoint_metadata")
        batch_op.drop_column("deployment_metadata")
        batch_op.drop_column("deployment_status")
        batch_op.drop_column("run_id")
        batch_op.drop_column("experiment_id")

    # Revert models table changes
    with op.batch_alter_table("models", schema=None) as batch_op:
        # Drop new indexes
        try:
            batch_op.drop_index("ix_models_azure_model")
            batch_op.drop_index("ix_models_experiment_id")
            batch_op.drop_index("ix_models_run_id")
            batch_op.drop_index("ix_models_user_id")
        except Exception:
            pass

        # Drop new columns
        batch_op.drop_column("error_message")
        batch_op.drop_column("registration_status")
        batch_op.drop_column("model_metadata")
        batch_op.drop_column("performance_metrics")
        batch_op.drop_column("best_score")
        batch_op.drop_column("model_uri")
        batch_op.drop_column("azure_model_version")
        batch_op.drop_column("azure_model_name")
        batch_op.drop_column("algorithm")
        batch_op.drop_column("run_id")
        batch_op.drop_column("experiment_id")

        # Add back tenant_id
        batch_op.add_column(
            sa.Column("tenant_id", String(255), nullable=False, server_default="")
        )
        batch_op.drop_column("user_id")

        # Recreate old index
        batch_op.create_index(
            "ix_model_tenant_name", ["tenant_id", "azure_model_id"], unique=True
        )
