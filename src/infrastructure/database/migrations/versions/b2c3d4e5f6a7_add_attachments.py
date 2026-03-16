"""add interaction_attachments table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-03 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create interaction_attachments table."""
    op.create_table(
        "interaction_attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("interaction_id", sa.Uuid(), nullable=False),
        sa.Column("uploaded_by", sa.Uuid(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_key", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column(
            "context",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'internal_note'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["interaction_id"],
            ["interactions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_attachments_interaction_id",
        "interaction_attachments",
        ["interaction_id"],
    )
    op.create_index(
        "idx_attachments_uploaded_by",
        "interaction_attachments",
        ["uploaded_by"],
    )


def downgrade() -> None:
    """Drop interaction_attachments table."""
    op.drop_index("idx_attachments_uploaded_by", table_name="interaction_attachments")
    op.drop_index("idx_attachments_interaction_id", table_name="interaction_attachments")
    op.drop_table("interaction_attachments")
