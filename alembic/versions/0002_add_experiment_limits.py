"""Add AutoML limits to experiments table

Revision ID: 0002
Revises: 0001
Create Date: 2025-07-11 12:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add AutoML limit columns to experiments table."""
    # Add new columns to experiments table
    op.add_column(
        "experiments",
        sa.Column("enable_early_termination", sa.String(10), nullable=True),
    )
    op.add_column("experiments", sa.Column("exit_score", sa.Float(), nullable=True))
    op.add_column(
        "experiments",
        sa.Column("max_concurrent_trials", sa.Integer(), nullable=True, default=20),
    )
    op.add_column(
        "experiments", sa.Column("max_cores_per_trial", sa.Integer(), nullable=True)
    )
    op.add_column(
        "experiments", sa.Column("max_nodes", sa.Integer(), nullable=True, default=10)
    )
    op.add_column(
        "experiments", sa.Column("max_trials", sa.Integer(), nullable=True, default=300)
    )
    op.add_column(
        "experiments", sa.Column("timeout_minutes", sa.Integer(), nullable=True)
    )
    op.add_column(
        "experiments",
        sa.Column("trial_timeout_minutes", sa.Integer(), nullable=True, default=15),
    )


def downgrade() -> None:
    """Remove AutoML limit columns from experiments table."""
    op.drop_column("experiments", "trial_timeout_minutes")
    op.drop_column("experiments", "timeout_minutes")
    op.drop_column("experiments", "max_trials")
    op.drop_column("experiments", "max_nodes")
    op.drop_column("experiments", "max_cores_per_trial")
    op.drop_column("experiments", "max_concurrent_trials")
    op.drop_column("experiments", "exit_score")
    op.drop_column("experiments", "enable_early_termination")
