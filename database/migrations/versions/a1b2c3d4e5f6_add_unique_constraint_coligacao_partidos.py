"""add_unique_constraint_coligacao_partidos

Revision ID: a1b2c3d4e5f6
Revises: e4430eef9468
Create Date: 2026-01-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'e4430eef9468'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add unique constraint to coligacao_partidos table.

    This constraint is required for the ON CONFLICT upsert pattern used
    when inserting coalition-party relationships.
    """
    op.create_unique_constraint(
        'uq_coligacao_partido',
        'coligacao_partidos',
        ['coligacao_id', 'partido_sigla']
    )


def downgrade() -> None:
    """Remove the unique constraint."""
    op.drop_constraint('uq_coligacao_partido', 'coligacao_partidos', type_='unique')
