"""initial – interactions and interaction_audit tables

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-03-02 04:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "interactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("internal_notes", sa.Text(), nullable=True),
        sa.Column("outcome", sa.String(length=255), nullable=True),
        sa.Column(
            "interaction_date",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("follow_up_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("last_edited_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_interactions_type", "interactions", ["type"])
    op.create_index("idx_interactions_status", "interactions", ["status"])
    op.create_index(
        "idx_interactions_date",
        "interactions",
        [sa.text("interaction_date DESC")],
    )
    op.create_index(
        "idx_interactions_client_date",
        "interactions",
        ["client_id", sa.text("interaction_date DESC")],
    )

    op.create_table(
        "interaction_audit",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("interaction_id", sa.Uuid(), nullable=False),
        sa.Column("edited_by", sa.Uuid(), nullable=False),
        sa.Column(
            "edited_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("field_name", sa.String(length=50), nullable=False),
        sa.Column("previous_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["interaction_id"],
            ["interactions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_audit_interaction_id",
        "interaction_audit",
        ["interaction_id"],
    )
    op.create_index(
        "idx_audit_edited_by",
        "interaction_audit",
        ["edited_by"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_audit_edited_by", table_name="interaction_audit")
    op.drop_index("idx_audit_interaction_id", table_name="interaction_audit")
    op.drop_table("interaction_audit")
    op.drop_index("idx_interactions_client_date", table_name="interactions")
    op.drop_index("idx_interactions_date", table_name="interactions")
    op.drop_index("idx_interactions_status", table_name="interactions")
    op.drop_index("idx_interactions_type", table_name="interactions")
    op.drop_table("interactions")
