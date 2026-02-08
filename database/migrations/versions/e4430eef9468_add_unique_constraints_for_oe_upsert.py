"""add_unique_constraints_for_oe_upsert

Revision ID: e4430eef9468
Revises: 7932db127bd9
Create Date: 2026-01-02 14:48:16.975245

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4430eef9468'
down_revision: Union[str, Sequence[str], None] = '7932db127bd9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Adds unique constraints for upsert pattern support.
    First cleans up any existing duplicate records including their dependent records.
    """
    # Get IDs of duplicate proposta records to delete (keep only first by min id)
    # First, delete dependent records from child tables

    # Delete dependent artigo_alineas for artigos of duplicate proposals
    op.execute("""
        DELETE FROM orcamento_estado_artigo_alineas
        WHERE numero_id IN (
            SELECT an.id FROM orcamento_estado_artigo_numeros an
            INNER JOIN orcamento_estado_artigos a ON an.artigo_id = a.id
            INNER JOIN orcamento_estado_propostas_alteracao p ON a.proposta_id = p.id
            WHERE p.id NOT IN (
                SELECT MIN(id::text)::uuid
                FROM orcamento_estado_propostas_alteracao
                GROUP BY proposta_id
            )
        )
    """)

    # Delete dependent artigo_numeros for artigos of duplicate proposals
    op.execute("""
        DELETE FROM orcamento_estado_artigo_numeros
        WHERE artigo_id IN (
            SELECT a.id FROM orcamento_estado_artigos a
            INNER JOIN orcamento_estado_propostas_alteracao p ON a.proposta_id = p.id
            WHERE p.id NOT IN (
                SELECT MIN(id::text)::uuid
                FROM orcamento_estado_propostas_alteracao
                GROUP BY proposta_id
            )
        )
    """)

    # Delete dependent artigos
    op.execute("""
        DELETE FROM orcamento_estado_artigos
        WHERE proposta_id IN (
            SELECT id FROM orcamento_estado_propostas_alteracao
            WHERE id NOT IN (
                SELECT MIN(id::text)::uuid
                FROM orcamento_estado_propostas_alteracao
                GROUP BY proposta_id
            )
        )
    """)

    # Delete dependent proponentes
    op.execute("""
        DELETE FROM orcamento_estado_proponentes
        WHERE proposta_id IN (
            SELECT id FROM orcamento_estado_propostas_alteracao
            WHERE id NOT IN (
                SELECT MIN(id::text)::uuid
                FROM orcamento_estado_propostas_alteracao
                GROUP BY proposta_id
            )
        )
    """)

    # Delete dependent votacoes
    op.execute("""
        DELETE FROM orcamento_estado_votacoes
        WHERE proposta_id IN (
            SELECT id FROM orcamento_estado_propostas_alteracao
            WHERE id NOT IN (
                SELECT MIN(id::text)::uuid
                FROM orcamento_estado_propostas_alteracao
                GROUP BY proposta_id
            )
        )
    """)

    # Delete dependent diploma_medidas
    op.execute("""
        DELETE FROM orcamento_estado_diploma_medidas
        WHERE proposta_id IN (
            SELECT id FROM orcamento_estado_propostas_alteracao
            WHERE id NOT IN (
                SELECT MIN(id::text)::uuid
                FROM orcamento_estado_propostas_alteracao
                GROUP BY proposta_id
            )
        )
    """)

    # Now delete duplicate proposta_id values
    op.execute("""
        DELETE FROM orcamento_estado_propostas_alteracao
        WHERE id NOT IN (
            SELECT MIN(id::text)::uuid
            FROM orcamento_estado_propostas_alteracao
            GROUP BY proposta_id
        )
    """)

    # Clean up duplicate item_id values (if any) before adding unique constraint
    # No dependent tables need cleanup for items - the constraint check above showed no duplicates
    op.execute("""
        DELETE FROM orcamento_estado_items
        WHERE id NOT IN (
            SELECT MIN(id::text)::uuid
            FROM orcamento_estado_items
            GROUP BY item_id
        )
    """)

    # Now create the unique constraints
    op.create_unique_constraint('uq_oe_item_id', 'orcamento_estado_items', ['item_id'])
    op.create_unique_constraint('uq_oe_proposta_id', 'orcamento_estado_propostas_alteracao', ['proposta_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_oe_proposta_id', 'orcamento_estado_propostas_alteracao', type_='unique')
    op.drop_constraint('uq_oe_item_id', 'orcamento_estado_items', type_='unique')
