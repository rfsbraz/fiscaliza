"""
Parliament API Routes
Clean implementation with SQLAlchemy/PostgreSQL patterns
"""
from flask import Blueprint, request, jsonify
from sqlalchemy import func, desc, distinct, or_, and_, case, exists, select
from sqlalchemy.orm import aliased
from database.connection import DatabaseSession
from database.models import (
    Deputado, Partido, Legislatura, CirculoEleitoral,
    DeputadoMandatoLegislativo, IntervencaoParlamentar, IntervencaoDeputado,
    IniciativaParlamentar, IniciativaAutorDeputado, IniciativaEvento, IniciativaEventoVotacao,
    AtividadeParlamentar, AtividadeParlamentarVotacao, OrcamentoEstadoVotacao,
    OrcamentoEstadoGrupoParlamentarVoto, Coligacao, ColigacaoPartido
)

parlamento_bp = Blueprint('parlamento', __name__)


def log_and_return_error(e, endpoint_info="", status_code=500):
    """Helper function to log errors to console and return JSON error response"""
    import traceback
    import logging
    
    error_msg = f'Error in {endpoint_info}: {str(e)}'
    traceback_msg = f'Traceback: {traceback.format_exc()}'
    full_error = f"\n{'='*50}\n{error_msg}\n{traceback_msg}\n{'='*50}"
    
    # Use proper logging for CloudWatch compatibility
    logger = logging.getLogger(__name__)
    logger.error(full_error)
    
    # Also print to console directly (for local debugging)
    print(full_error)
    
    # SECURITY: Only expose traceback in debug mode
    from flask import current_app
    if current_app.debug:
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), status_code
    else:
        return jsonify({
            'error': 'Internal server error'
        }), status_code


def get_most_recent_deputy(session, cad_id):
    """
    Get the most recent deputy record for a given cadastro ID.

    Selection Priority:
    1. Current legislature (XVII) if deputy has a record there
    2. Most recent legislature by data_inicio (handling NULLs properly)
    3. Last resort: any record for this person

    Args:
        session: SQLAlchemy session
        cad_id: Deputy cadastro ID (unique person identifier)

    Returns:
        Deputado object or None if not found
    """
    try:
        # Primary method: Find deputy in the current legislature (XVII)
        deputado = session.query(Deputado).filter(
            Deputado.id_cadastro == cad_id
        ).join(Legislatura).filter(
            Legislatura.numero == 'XVII'
        ).first()

        if deputado:
            return deputado

        # Secondary method: Order by legislature start date (most recent first)
        # Use NULLS LAST to ensure records with NULL dates don't appear first
        from sqlalchemy import nullslast
        deputado = session.query(Deputado).filter(
            Deputado.id_cadastro == cad_id
        ).join(Legislatura).order_by(
            nullslast(Legislatura.data_inicio.desc()),
            Legislatura.numero.desc()  # Secondary sort for same dates
        ).first()

        if deputado:
            return deputado

        # Fallback: Try without join (in case of missing legislature data)
        deputado = session.query(Deputado).filter(
            Deputado.id_cadastro == cad_id
        ).order_by(Deputado.legislatura_id.desc()).first()

        return deputado

    except Exception as e:
        print(f"Error in get_most_recent_deputy for cad_id {cad_id}: {e}")
        # Last resort fallback
        return session.query(Deputado).filter(
            Deputado.id_cadastro == cad_id
        ).first()


# =============================================================================
# PHASE 1: CORE API ENDPOINTS
# =============================================================================

# =============================================================================
# PHASE 3: COMPLEX FEATURES
# =============================================================================
