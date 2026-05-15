"""limit subject field to 200 chars

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-15 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Truncate existing long subjects and limit column to 200 chars."""
    # First truncate any existing data that exceeds 200 chars
    op.execute(
        "UPDATE interactions SET subject = LEFT(subject, 200) "
        "WHERE LENGTH(subject) > 200"
    )
    # Then alter the column
    op.alter_column(
        "interactions",
        "subject",
        existing_type=sa.String(length=500),
        type_=sa.String(length=200),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Revert subject column back to 500 chars."""
    op.alter_column(
        "interactions",
        "subject",
        existing_type=sa.String(length=200),
        type_=sa.String(length=500),
        existing_nullable=False,
    )
