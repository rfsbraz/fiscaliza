"""
Deputy Status Utilities
========================

Provides functions for determining deputy mandate status (seated vs not seated).

The status is determined from the DadosSituacaoDeputado table which contains
situational information with dates and descriptions.

Status Values:
- Seated (Efetivo*): Efetivo, Efetivo Temporário, Efetivo Definitivo
- Not Seated: Suspenso(Eleito), Suspenso(Não Eleito), Renunciou, Suplente, Impedido, Desistência

Usage:
    from app.utils.deputy_status import get_deputy_current_status, is_seated_status

    # Get the current status for a deputy
    status = get_deputy_current_status(deputado_id, legislatura_id, session)

    # Check if a status indicates the deputy is seated
    if is_seated_status(status):
        print("Deputy is currently seated")
"""

from typing import Optional
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

# Status values that indicate deputy is currently seated
SEATED_STATUSES = frozenset([
    'Efetivo',
    'Efetivo Temporário',
    'Efetivo Definitivo',
])

# Status values that indicate deputy is not currently seated
NOT_SEATED_STATUSES = frozenset([
    'Suspenso(Eleito)',
    'Suspenso(Não Eleito)',
    'Renunciou',
    'Suplente',
    'Impedido',
    'Desistência',
])


def is_seated_status(status: Optional[str]) -> bool:
    """
    Check if a status indicates the deputy is currently seated.

    Args:
        status: The sio_des value from DadosSituacaoDeputado

    Returns:
        True if the status indicates deputy is seated, False otherwise
    """
    if not status:
        return False
    # Check if status starts with 'Efetivo' to handle any variations
    return status.startswith('Efetivo')


def get_deputy_current_status(
    deputado_id: str,
    legislatura_id: str,
    session
) -> Optional[str]:
    """
    Get the current mandate status for a deputy in a specific legislature.

    Queries the latest DadosSituacaoDeputado record based on:
    1. Most recent sio_dt_inicio date
    2. NULL sio_dt_fim (or latest end date)

    Args:
        deputado_id: The Deputado.id (GUID)
        legislatura_id: The Legislatura.id (GUID)
        session: SQLAlchemy database session

    Returns:
        The sio_des status string (e.g., 'Efetivo', 'Suspenso(Eleito)') or None
    """
    query = text("""
        WITH latest_status AS (
            SELECT
                dsd.sio_des,
                dsd.sio_dt_inicio,
                dsd.sio_dt_fim,
                ROW_NUMBER() OVER (
                    ORDER BY dsd.sio_dt_inicio DESC, dsd.sio_dt_fim DESC NULLS FIRST
                ) as rn
            FROM deputados d
            JOIN atividade_deputados ad ON ad.deputado_id = d.id
            JOIN deputado_situacoes ds ON ds.atividade_deputado_id = ad.id
            JOIN dados_situacao_deputados dsd ON dsd.deputado_situacao_id = ds.id
            WHERE d.id = :deputado_id
              AND d.legislatura_id = :legislatura_id
        )
        SELECT sio_des
        FROM latest_status
        WHERE rn = 1
    """)

    try:
        result = session.execute(query, {
            'deputado_id': str(deputado_id),
            'legislatura_id': str(legislatura_id)
        }).fetchone()

        if result:
            return result[0]
        return None
    except Exception as e:
        logger.warning(f"Failed to get deputy status for {deputado_id}: {e}")
        return None


def get_deputy_status_by_cadastro(
    id_cadastro: int,
    legislature: str,
    session
) -> Optional[str]:
    """
    Get the current mandate status for a deputy by their cadastro ID and legislature.

    Args:
        id_cadastro: The deputy's cadastro ID (unique across legislatures)
        legislature: The legislature designation (e.g., 'XVII')
        session: SQLAlchemy database session

    Returns:
        The sio_des status string or None
    """
    query = text("""
        WITH latest_status AS (
            SELECT
                dsd.sio_des,
                ROW_NUMBER() OVER (
                    PARTITION BY d.id_cadastro
                    ORDER BY dsd.sio_dt_inicio DESC, dsd.sio_dt_fim DESC NULLS FIRST
                ) as rn
            FROM deputados d
            JOIN legislaturas l ON d.legislatura_id = l.id
            JOIN atividade_deputados ad ON ad.deputado_id = d.id
            JOIN deputado_situacoes ds ON ds.atividade_deputado_id = ad.id
            JOIN dados_situacao_deputados dsd ON dsd.deputado_situacao_id = ds.id
            WHERE d.id_cadastro = :id_cadastro
              AND l.numero = :legislature
        )
        SELECT sio_des
        FROM latest_status
        WHERE rn = 1
    """)

    try:
        result = session.execute(query, {
            'id_cadastro': id_cadastro,
            'legislature': legislature
        }).fetchone()

        if result:
            return result[0]
        return None
    except Exception as e:
        logger.warning(f"Failed to get deputy status for cadastro {id_cadastro}: {e}")
        return None


def get_seated_deputies_count(legislature: str, session) -> int:
    """
    Count the number of currently seated deputies in a legislature.

    Args:
        legislature: The legislature designation (e.g., 'XVII')
        session: SQLAlchemy database session

    Returns:
        Count of deputies with Efetivo* status
    """
    query = text("""
        WITH latest_status AS (
            SELECT
                d.id_cadastro,
                dsd.sio_des,
                ROW_NUMBER() OVER (
                    PARTITION BY d.id_cadastro
                    ORDER BY dsd.sio_dt_inicio DESC, dsd.sio_dt_fim DESC NULLS FIRST
                ) as rn
            FROM deputados d
            JOIN legislaturas l ON d.legislatura_id = l.id
            JOIN deputado_mandatos_legislativos dm ON dm.deputado_id = d.id
            JOIN atividade_deputados ad ON ad.deputado_id = d.id
            JOIN deputado_situacoes ds ON ds.atividade_deputado_id = ad.id
            JOIN dados_situacao_deputados dsd ON dsd.deputado_situacao_id = ds.id
            WHERE dm.leg_des = :legislature
              AND l.numero = :legislature
        )
        SELECT COUNT(DISTINCT id_cadastro)
        FROM latest_status
        WHERE rn = 1
          AND sio_des LIKE 'Efetivo%'
    """)

    try:
        result = session.execute(query, {'legislature': legislature}).scalar()
        return result or 0
    except Exception as e:
        logger.warning(f"Failed to count seated deputies for {legislature}: {e}")
        return 0


def get_deputies_status_summary(legislature: str, session) -> dict:
    """
    Get a summary of deputy statuses for a legislature.

    Args:
        legislature: The legislature designation (e.g., 'XVII')
        session: SQLAlchemy database session

    Returns:
        Dictionary with status counts:
        {
            'total_elected': 242,
            'seated': 230,
            'suspended_elected': 4,
            'suspended_not_elected': 2,
            'resigned': 3,
            'substitute': 3,
            'impeded': 0,
            'withdrawn': 0,
            'by_status': {'Efetivo': 196, 'Efetivo Temporário': 27, ...}
        }
    """
    query = text("""
        WITH latest_status AS (
            SELECT
                d.id_cadastro,
                dsd.sio_des,
                ROW_NUMBER() OVER (
                    PARTITION BY d.id_cadastro
                    ORDER BY dsd.sio_dt_inicio DESC, dsd.sio_dt_fim DESC NULLS FIRST
                ) as rn
            FROM deputados d
            JOIN legislaturas l ON d.legislatura_id = l.id
            JOIN deputado_mandatos_legislativos dm ON dm.deputado_id = d.id
            JOIN atividade_deputados ad ON ad.deputado_id = d.id
            JOIN deputado_situacoes ds ON ds.atividade_deputado_id = ad.id
            JOIN dados_situacao_deputados dsd ON dsd.deputado_situacao_id = ds.id
            WHERE dm.leg_des = :legislature
              AND l.numero = :legislature
        )
        SELECT sio_des, COUNT(DISTINCT id_cadastro) as count
        FROM latest_status
        WHERE rn = 1
        GROUP BY sio_des
    """)

    try:
        results = session.execute(query, {'legislature': legislature}).fetchall()

        by_status = {row[0]: row[1] for row in results}

        # Calculate aggregates
        seated = sum(count for status, count in by_status.items()
                    if status and status.startswith('Efetivo'))

        return {
            'total_elected': sum(by_status.values()),
            'seated': seated,
            'suspended_elected': by_status.get('Suspenso(Eleito)', 0),
            'suspended_not_elected': by_status.get('Suspenso(Não Eleito)', 0),
            'resigned': by_status.get('Renunciou', 0),
            'substitute': by_status.get('Suplente', 0),
            'impeded': by_status.get('Impedido', 0),
            'withdrawn': by_status.get('Desistência', 0),
            'by_status': by_status
        }
    except Exception as e:
        logger.warning(f"Failed to get status summary for {legislature}: {e}")
        return {
            'total_elected': 0,
            'seated': 0,
            'suspended_elected': 0,
            'suspended_not_elected': 0,
            'resigned': 0,
            'substitute': 0,
            'impeded': 0,
            'withdrawn': 0,
            'by_status': {}
        }
