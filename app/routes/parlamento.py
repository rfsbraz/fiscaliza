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

@parlamento_bp.route('/deputados/<int:cad_id>/attendance', methods=['GET'])
def get_deputado_attendance(cad_id):
    """Retorna timeline de presenças/faltas de um deputado"""
    try:
        with DatabaseSession() as session:
            # Find deputado by cad_id (unique across all legislatures)
            # Get their most recent legislature entry using proper ordering
            deputado = get_most_recent_deputy(session, cad_id)
            
            if not deputado:
                return jsonify({'error': 'Deputado não encontrado'}), 404
            
            # Query attendance records from meeting_attendances table
            from sqlalchemy import text
            
            attendance_query = text("""
                SELECT 
                    dt_reuniao,
                    tipo_reuniao,
                    sigla_falta,
                    motivo_falta,
                    pres_justificacao,
                    observacoes,
                    sigla_grupo
                FROM meeting_attendances 
                WHERE dep_nome_parlamentar = :deputy_name
                AND dt_reuniao IS NOT NULL
                ORDER BY dt_reuniao DESC
                LIMIT 200
            """)
            
            attendance_records = session.execute(attendance_query, {'deputy_name': deputado.nome}).fetchall()
            
            # Process attendance records
            timeline = []
            summary = {
                'total_sessions': 0,
                'present': 0,
                'justified_absence': 0,
                'unjustified_absence': 0,
                'other': 0
            }
            
            # Attendance code meanings (based on analysis)
            attendance_codes = {
                'PR': {'type': 'present', 'description': 'Presente', 'status': 'success'},
                'FJ': {'type': 'justified', 'description': 'Falta Justificada', 'status': 'warning'},
                'ME': {'type': 'justified', 'description': 'Missão Especial', 'status': 'info'},
                'QVJ': {'type': 'justified', 'description': 'Questão de Voto Justificada', 'status': 'info'},
                'MP': {'type': 'justified', 'description': 'Missão Parlamentar', 'status': 'info'},
                'FI': {'type': 'unjustified', 'description': 'Falta Injustificada', 'status': 'danger'},
                'FA': {'type': 'unjustified', 'description': 'Falta', 'status': 'danger'},
                'PNO': {'type': 'other', 'description': 'Presente Não Oficial', 'status': 'secondary'},
                'QV': {'type': 'other', 'description': 'Questão de Voto', 'status': 'secondary'},
                'CO': {'type': 'other', 'description': 'Comissão', 'status': 'secondary'},
                'FIJ': {'type': 'justified', 'description': 'Falta Injustificada (Justificada)', 'status': 'warning'}
            }
            
            for record in attendance_records:
                dt_reuniao, tipo_reuniao, sigla_falta, motivo_falta, pres_justificacao, observacoes, sigla_grupo = record
                
                # Get attendance info
                attendance_info = attendance_codes.get(sigla_falta, {
                    'type': 'other', 
                    'description': f'Código: {sigla_falta}', 
                    'status': 'secondary'
                })
                
                # Build timeline entry
                timeline_entry = {
                    'date': dt_reuniao.isoformat() if dt_reuniao else None,
                    'session_type': tipo_reuniao,
                    'attendance_code': sigla_falta,
                    'attendance_type': attendance_info['type'],
                    'attendance_description': attendance_info['description'],
                    'status': attendance_info['status'],
                    'reason': motivo_falta,
                    'justification': pres_justificacao,
                    'observations': observacoes,
                    'parliamentary_group': sigla_grupo
                }
                
                timeline.append(timeline_entry)
                
                # Update summary
                summary['total_sessions'] += 1
                if attendance_info['type'] == 'present':
                    summary['present'] += 1
                elif attendance_info['type'] == 'justified':
                    summary['justified_absence'] += 1
                elif attendance_info['type'] == 'unjustified':
                    summary['unjustified_absence'] += 1
                else:
                    summary['other'] += 1
            
            # Calculate attendance rate
            attendance_rate = 0
            if summary['total_sessions'] > 0:
                # Present + justified absences count as good attendance
                good_attendance = summary['present'] + summary['justified_absence']
                attendance_rate = good_attendance / summary['total_sessions']
            
            return jsonify({
                'deputado': {
                    'id': deputado.id,
                    'nome': deputado.nome,
                    'nome_completo': deputado.nome_completo
                },
                'summary': {
                    **summary,
                    'attendance_rate': round(attendance_rate, 3)
                },
                'timeline': timeline,
                'codes_legend': attendance_codes
            })
            
    except Exception as e:
        return log_and_return_error(e, f'/api/deputados/{cad_id}/attendance')
