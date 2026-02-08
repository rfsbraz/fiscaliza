"""
Parliamentary Transparency Dashboard API Routes

Provides comprehensive transparency data for Portuguese Parliament operations
using complex analytical queries on existing database structure.
"""

from flask import Blueprint, jsonify, request
from datetime import datetime, date, timedelta
from sqlalchemy import func, text, and_, or_, desc
from sqlalchemy.orm import aliased
import logging

# Add project root to path for imports
import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from database.connection import get_session
from database.models import (
    AgendaParlamentar, IniciativaParlamentar, IniciativaEventoVotacao, 
    IniciativaEvento, Deputado, DeputadoMandatoLegislativo, Legislatura,
    PerguntaRequerimento, PerguntaRequerimentoResposta, PerguntaRequerimentoDestinatario, PeticaoParlamentar, 
    Partido
)

# Optional models that might not exist in all setups
try:
    from database.models import AttendanceAnalytics, InitiativeAnalytics, AtividadeDeputado, IntervencaoParlamentar
except ImportError:
    AttendanceAnalytics = None
    InitiativeAnalytics = None
    AtividadeDeputado = None
    IntervencaoParlamentar = None

transparency_bp = Blueprint('transparency', __name__)
logger = logging.getLogger(__name__)

def get_current_legislature():
    """Get current legislature (XVII)"""
    session = get_session()
    try:
        current_leg = session.query(Legislatura).filter(
            Legislatura.numero == 'XVII'
        ).first()
        return current_leg
    finally:
        session.close()

@transparency_bp.route('/transparency/live-activity', methods=['GET'])
def get_live_parliamentary_activity():
    """
    Real-Time Parliamentary Activity Panel
    =====================================
    
    Provides live status of parliamentary sessions, recent votes, and active initiatives
    Based on AgendaParlamentar, IniciativaEventoVotacao, and IniciativaParlamentar data
    """
    session = get_session()
    
    try:
        current_leg = get_current_legislature()
        if not current_leg:
            return jsonify({'error': 'Current legislature not found'}), 404
            
        today = date.today()
        yesterday = today - timedelta(days=1)
        two_days_ago = today - timedelta(days=2)
        
        # 1. TODAY'S PARLIAMENTARY AGENDA
        todays_agenda = session.query(AgendaParlamentar).filter(
            AgendaParlamentar.legislatura_id == current_leg.id,
            AgendaParlamentar.data_evento == today
        ).order_by(AgendaParlamentar.hora_inicio).all()
        
        agenda_events = []
        for event in todays_agenda:
            # Determine session type and status
            titulo_lower = (event.titulo or '').lower()
            if 'plenár' in titulo_lower or 'sessão' in titulo_lower:
                session_type = 'plenario'
                priority = 'high'
            elif 'comissão' in titulo_lower or 'comité' in titulo_lower:
                session_type = 'comissao'
                priority = 'medium'
            else:
                session_type = 'evento'
                priority = 'low'
                
            # Estimate session status based on time
            now = datetime.now().time()
            status = 'scheduled'
            if event.hora_inicio:
                try:
                    start_time = datetime.strptime(event.hora_inicio, '%H:%M:%S').time()
                    if now >= start_time:
                        if event.hora_fim:
                            end_time = datetime.strptime(event.hora_fim, '%H:%M:%S').time()
                            status = 'completed' if now > end_time else 'in_progress'
                        else:
                            status = 'in_progress'
                except ValueError:
                    status = 'scheduled'
            
            agenda_events.append({
                'id': event.id,
                'title': event.titulo,
                'subtitle': event.subtitulo,
                'type': session_type,
                'status': status,
                'priority': priority,
                'start_time': event.hora_inicio,
                'end_time': event.hora_fim,
                'location': event.local_evento,
                'parliamentary_group': event.grupo_parlamentar,
                'description': event.descricao
            })
        
        # 2. RECENT VOTING RESULTS (Last 48 hours) - simplified query
        recent_votes_query = session.query(IniciativaEventoVotacao).filter(
            IniciativaEventoVotacao.data_votacao >= two_days_ago,
            IniciativaEventoVotacao.resultado.isnot(None)
        ).order_by(
            desc(IniciativaEventoVotacao.data_votacao)
        ).limit(20).all()
        
        recent_votes = []
        for vote_data in recent_votes_query:
            # Analyze result
            resultado = vote_data.resultado.lower() if vote_data.resultado else ''
            if 'aprovad' in resultado or 'aproveit' in resultado:
                result_status = 'approved'
                result_class = 'success'
            elif 'rejeitad' in resultado or 'chumbad' in resultado:
                result_status = 'rejected'
                result_class = 'danger'
            elif 'retirad' in resultado:
                result_status = 'withdrawn'
                result_class = 'warning'
            else:
                result_status = 'other'
                result_class = 'info'
            
            recent_votes.append({
                'id': vote_data.id,
                'voting_date': vote_data.data_votacao.isoformat() if vote_data.data_votacao else None,
                'result': vote_data.resultado,
                'result_status': result_status,
                'result_class': result_class,
                'unanimous': vote_data.unanime,
                'meeting_type': vote_data.tipo_reuniao,
                'description': vote_data.descricao
            })
        
        # 3. ACTIVE INITIATIVES BY STAGE
        # Complex query to get initiative counts by type and estimated stage
        active_initiatives_query = session.query(
            IniciativaParlamentar.ini_desc_tipo,
            func.count(IniciativaParlamentar.id).label('total_count')
        ).filter(
            IniciativaParlamentar.legislatura_id == current_leg.id
        ).group_by(
            IniciativaParlamentar.ini_desc_tipo
        ).order_by(
            desc('total_count')
        ).all()
        
        # Get recent initiatives (last 30 days) for progress indication
        thirty_days_ago = today - timedelta(days=30)
        recent_initiatives_query = session.query(
            IniciativaParlamentar.ini_desc_tipo,
            func.count(IniciativaParlamentar.id).label('recent_count')
        ).join(
            IniciativaEvento, IniciativaParlamentar.id == IniciativaEvento.iniciativa_id
        ).filter(
            IniciativaParlamentar.legislatura_id == current_leg.id,
            IniciativaEvento.data_fase >= thirty_days_ago
        ).group_by(
            IniciativaParlamentar.ini_desc_tipo
        ).all()
        
        # Create lookup for recent activity
        recent_activity_lookup = {item[0]: item[1] for item in recent_initiatives_query}
        
        active_initiatives = []
        for ini_type, total in active_initiatives_query:
            recent_activity = recent_activity_lookup.get(ini_type, 0)
            activity_trend = 'high' if recent_activity > 5 else 'medium' if recent_activity > 2 else 'low'
            
            active_initiatives.append({
                'initiative_type': ini_type,
                'total_count': total,
                'recent_activity_count': recent_activity,
                'activity_trend': activity_trend
            })
        
        # 4. SESSION SUMMARY STATISTICS
        sessions_today = len([e for e in agenda_events if e['type'] == 'plenario'])
        committees_today = len([e for e in agenda_events if e['type'] == 'comissao'])
        events_today = len(agenda_events)
        
        votes_last_48h = len(recent_votes)
        approved_votes = len([v for v in recent_votes if v['result_status'] == 'approved'])
        
        return jsonify({
            'date': today.isoformat(),
            'legislature': current_leg.numero,
            'last_updated': datetime.now().isoformat(),
            
            # Today's Parliamentary Schedule
            'todays_agenda': {
                'events': agenda_events,
                'summary': {
                    'total_events': events_today,
                    'plenary_sessions': sessions_today,
                    'committee_meetings': committees_today,
                    'other_events': events_today - sessions_today - committees_today,
                    'in_progress': len([e for e in agenda_events if e['status'] == 'in_progress']),
                    'completed': len([e for e in agenda_events if e['status'] == 'completed'])
                }
            },
            
            # Recent Voting Activity
            'recent_votes': {
                'votes': recent_votes,
                'summary': {
                    'total_votes_48h': votes_last_48h,
                    'approved': approved_votes,
                    'rejected': len([v for v in recent_votes if v['result_status'] == 'rejected']),
                    'approval_rate': round((approved_votes / votes_last_48h * 100), 1) if votes_last_48h > 0 else 0
                }
            },
            
            # Active Legislative Work
            'active_initiatives': {
                'by_type': active_initiatives,
                'summary': {
                    'total_active': sum([item['total_count'] for item in active_initiatives]),
                    'high_activity_types': len([item for item in active_initiatives if item['activity_trend'] == 'high']),
                    'most_active_type': active_initiatives[0]['initiative_type'] if active_initiatives else None
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error in live parliamentary activity: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500
        
    finally:
        session.close()

@transparency_bp.route('/transparency/legislative-progress', methods=['GET'])
def get_legislative_progress():
    """
    Legislative Progress Tracker
    ===========================
    
    Tracks progress of government program implementation, budget execution,
    priority bills timeline, and committee work status
    """
    session = get_session()
    
    try:
        current_leg = get_current_legislature()
        if not current_leg:
            return jsonify({'error': 'Current legislature not found'}), 404
            
        # 1. INITIATIVE PROGRESS PIPELINE
        # Complex query to analyze initiative stages and timeline
        initiative_progress_query = text("""
            SELECT 
                ip.ini_desc_tipo as initiative_type,
                COUNT(DISTINCT ip.id) as total_initiatives,
                COUNT(DISTINCT CASE WHEN ie.fase LIKE '%Discussão na generalidade%' THEN ip.id END) as in_general_discussion,
                COUNT(DISTINCT CASE WHEN ie.fase LIKE '%especialidade%' THEN ip.id END) as in_specialty_discussion,
                COUNT(DISTINCT CASE WHEN ie.fase LIKE '%votação final%' THEN ip.id END) as final_voting,
                COUNT(DISTINCT CASE WHEN iev.resultado LIKE '%aprovad%' THEN ip.id END) as approved,
                COUNT(DISTINCT CASE WHEN iev.resultado LIKE '%rejeitad%' THEN ip.id END) as rejected,
                AVG(CURRENT_DATE - ip.updated_at::date) as avg_days_in_process
            FROM iniciativas_detalhadas ip
            LEFT JOIN iniciativas_eventos ie ON ip.id = ie.iniciativa_id
            LEFT JOIN iniciativas_eventos_votacoes iev ON ie.id = iev.evento_id
            WHERE ip.legislatura_id = :legislature_id
            AND ip.ini_desc_tipo IN ('Projeto de Lei', 'Proposta de Lei', 'Projeto de Resolução', 'Proposta de Resolução')
            GROUP BY ip.ini_desc_tipo
            ORDER BY total_initiatives DESC
        """)
        
        progress_results = session.execute(
            initiative_progress_query, 
            {'legislature_id': current_leg.id}
        ).fetchall()
        
        legislative_pipeline = []
        total_initiatives = 0
        total_approved = 0
        
        for row in progress_results:
            total_initiatives += row.total_initiatives or 0
            total_approved += row.approved or 0
            
            # Calculate efficiency metrics
            completion_rate = round((row.approved or 0) / (row.total_initiatives or 1) * 100, 1)
            avg_processing_time = round(row.avg_days_in_process or 0)
            
            legislative_pipeline.append({
                'initiative_type': row.initiative_type,
                'total_count': row.total_initiatives or 0,
                'stages': {
                    'general_discussion': row.in_general_discussion or 0,
                    'specialty_discussion': row.in_specialty_discussion or 0,
                    'final_voting': row.final_voting or 0,
                    'approved': row.approved or 0,
                    'rejected': row.rejected or 0
                },
                'metrics': {
                    'completion_rate': completion_rate,
                    'avg_processing_days': avg_processing_time,
                    'efficiency_rating': 'high' if completion_rate > 60 else 'medium' if completion_rate > 30 else 'low'
                }
            })
        
        # 2. GOVERNMENT RESPONSIVENESS TO PARLIAMENT
        # Analyze question response times and patterns
        thirty_days_ago = date.today() - timedelta(days=30)
        
        govt_responsiveness_query = text("""
            SELECT 
                COUNT(DISTINCT pr.id) as total_questions,
                COUNT(DISTINCT prr.id) as total_responses,
                AVG(prr.data_resposta - pr.dt_entrada) as avg_response_days,
                COUNT(DISTINCT CASE
                    WHEN (CURRENT_DATE - pr.dt_entrada) > 30 AND prr.data_resposta IS NULL
                    THEN pr.id
                END) as overdue_responses,
                COUNT(DISTINCT CASE 
                    WHEN pr.dt_entrada >= :thirty_days_ago 
                    THEN pr.id 
                END) as recent_questions,
                COUNT(DISTINCT CASE 
                    WHEN prr.data_resposta >= :thirty_days_ago 
                    THEN prr.id 
                END) as recent_responses
            FROM perguntas_requerimentos pr
            LEFT JOIN pergunta_requerimento_destinatarios prd ON pr.id = prd.pergunta_requerimento_id
            LEFT JOIN pergunta_requerimento_respostas prr ON prd.id = prr.destinatario_id
            WHERE pr.legislatura_id = :legislature_id
            AND pr.tipo LIKE '%Pergunta%'
        """)
        
        responsiveness_result = session.execute(
            govt_responsiveness_query, 
            {
                'legislature_id': current_leg.id,
                'thirty_days_ago': thirty_days_ago
            }
        ).fetchone()
        
        # Calculate response rate and efficiency
        response_rate = round(
            (responsiveness_result.total_responses or 0) / 
            (responsiveness_result.total_questions or 1) * 100, 1
        )
        
        govt_responsiveness = {
            'total_questions': responsiveness_result.total_questions or 0,
            'total_responses': responsiveness_result.total_responses or 0,
            'response_rate': response_rate,
            'avg_response_days': round(responsiveness_result.avg_response_days or 0, 1),
            'overdue_responses': responsiveness_result.overdue_responses or 0,
            'recent_activity': {
                'questions_30_days': responsiveness_result.recent_questions or 0,
                'responses_30_days': responsiveness_result.recent_responses or 0
            },
            'efficiency_rating': 'excellent' if response_rate > 80 and (responsiveness_result.avg_response_days or 0) < 15
                               else 'good' if response_rate > 60 and (responsiveness_result.avg_response_days or 0) < 30
                               else 'needs_improvement'
        }
        
        # 3. COMMITTEE WORK STATUS
        # Analyze committee productivity and current workload
        committee_work_query = text("""
            SELECT 
                ap.secao_nome as committee_name,
                COUNT(DISTINCT ap.id) as total_meetings,
                COUNT(DISTINCT CASE WHEN ap.data_evento >= :thirty_days_ago THEN ap.id END) as recent_meetings,
                COUNT(DISTINCT CASE WHEN ap.data_evento = CURRENT_DATE THEN ap.id END) as today_meetings,
                COUNT(DISTINCT CASE WHEN ap.data_evento > CURRENT_DATE THEN ap.id END) as scheduled_meetings
            FROM agenda_parlamentar ap
            WHERE ap.legislatura_id = :legislature_id
            AND ap.secao_nome LIKE '%omiss%'
            AND ap.data_evento >= :legislature_start
            GROUP BY ap.secao_nome
            HAVING COUNT(DISTINCT ap.id) > 0
            ORDER BY recent_meetings DESC, total_meetings DESC
            LIMIT 15
        """)
        
        legislature_start = current_leg.data_inicio or date(2024, 3, 1)  # Fallback date
        
        committee_results = session.execute(
            committee_work_query,
            {
                'legislature_id': current_leg.id,
                'thirty_days_ago': thirty_days_ago,
                'legislature_start': legislature_start
            }
        ).fetchall()
        
        committee_work = []
        for row in committee_results:
            activity_level = 'high' if (row.recent_meetings or 0) > 4 else 'medium' if (row.recent_meetings or 0) > 1 else 'low'
            
            committee_work.append({
                'name': row.committee_name,
                'total_meetings': row.total_meetings or 0,
                'recent_meetings': row.recent_meetings or 0,
                'today_meetings': row.today_meetings or 0,
                'scheduled_meetings': row.scheduled_meetings or 0,
                'activity_level': activity_level
            })
        
        # 4. OVERALL LEGISLATIVE EFFICIENCY
        overall_efficiency = {
            'total_initiatives': total_initiatives,
            'total_approved': total_approved,
            'overall_approval_rate': round((total_approved / total_initiatives * 100), 1) if total_initiatives > 0 else 0,
            'committees_active': len([c for c in committee_work if c['activity_level'] in ['high', 'medium']]),
            'government_response_efficiency': govt_responsiveness['efficiency_rating'],
            'legislative_momentum': 'strong' if total_approved > 50 and response_rate > 70
                                  else 'moderate' if total_approved > 20 and response_rate > 50
                                  else 'slow'
        }
        
        return jsonify({
            'legislature': current_leg.numero,
            'period': {
                'start_date': current_leg.data_inicio.isoformat() if current_leg.data_inicio else None,
                'end_date': current_leg.data_fim.isoformat() if current_leg.data_fim else None
            },
            'last_updated': datetime.now().isoformat(),
            
            'legislative_pipeline': legislative_pipeline,
            'government_responsiveness': govt_responsiveness,
            'committee_work': committee_work,
            'overall_efficiency': overall_efficiency
        })
        
    except Exception as e:
        logger.error(f"Error in legislative progress: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500
        
    finally:
        session.close()

@transparency_bp.route('/transparency/deputy-performance', methods=['GET'])
def get_deputy_performance():
    """
    Deputy Performance Scorecard
    ============================
    
    Analyzes individual deputy performance including attendance, voting patterns,
    initiative submissions, and parliamentary participation
    """
    session = get_session()
    
    try:
        current_leg = get_current_legislature()
        if not current_leg:
            return jsonify({'error': 'Current legislature not found'}), 404
            
        # 1. DEPUTY ATTENDANCE AND PARTICIPATION ANALYSIS
        deputy_performance_query = text("""
            SELECT 
                d.id as deputy_id,
                d.nome_completo as deputy_name,
                d.nome as parliamentary_name,
                dml.par_sigla as party,
                dml.leg_des as legislature,
                
                -- Attendance metrics
                AVG(CASE WHEN aa.attendance_rate IS NOT NULL THEN aa.attendance_rate ELSE 0 END) as avg_attendance_rate,
                COUNT(DISTINCT aa.id) as attendance_records,
                
                -- Initiative metrics  
                0 as initiatives_authored,  -- Cannot link without author field
                0 as initiatives_approved,  -- Cannot link without author field
                
                -- Participation metrics
                COUNT(DISTINCT ad.id) as parliamentary_activities,
                0 as initiatives_participated,  -- Cannot link without participant field
                0 as interventions_made,  -- Cannot link without deputy field
                
                -- Recent activity (last 90 days)
                COUNT(DISTINCT CASE
                    WHEN ad.created_at >= CURRENT_DATE - INTERVAL '90 days'
                    THEN ad.id
                END) as recent_activities,

                -- Use created_at as proxy for mandate duration
                (CURRENT_DATE - dml.created_at::date) as days_since_mandate_created
                
            FROM deputados d
            JOIN deputado_mandatos_legislativos dml ON d.id = dml.deputado_id
            LEFT JOIN partidos p ON dml.par_sigla = p.sigla
            LEFT JOIN attendance_analytics aa ON d.id = aa.deputado_id
            LEFT JOIN atividade_deputados ad ON d.id = ad.deputado_id
            WHERE dml.leg_des LIKE '%XVII%'  -- Current legislature
            GROUP BY d.id, d.nome_completo, d.nome, dml.par_sigla, dml.leg_des, dml.created_at
            HAVING (CURRENT_DATE - dml.created_at::date) > 0
            ORDER BY 
                avg_attendance_rate DESC, 
                parliamentary_activities DESC
            LIMIT 50
        """)
        
        deputy_results = session.execute(
            deputy_performance_query
        ).fetchall()
        
        deputy_performance = []
        total_deputies = 0
        total_attendance = 0
        total_initiatives = 0
        
        for row in deputy_results:
            total_deputies += 1
            attendance_rate = round(row.avg_attendance_rate or 0, 1)
            total_attendance += attendance_rate
            
            initiatives_count = row.initiatives_authored or 0
            total_initiatives += initiatives_count
            
            # Calculate performance scores
            initiative_success_rate = round(
                (row.initiatives_approved or 0) / max(initiatives_count, 1) * 100, 1
            )
            
            activity_score = min(100, round(
                ((row.parliamentary_activities or 0) * 0.4 + 
                 (row.initiatives_participated or 0) * 0.3 + 
                 (row.interventions_made or 0) * 0.2 +
                 (row.recent_activities or 0) * 0.1) * 2, 1
            ))
            
            # Overall performance rating
            overall_score = round(
                (attendance_rate * 0.3 + 
                 activity_score * 0.4 + 
                 initiative_success_rate * 0.2 + 
                 min(initiatives_count * 5, 50) * 0.1), 1
            )
            
            performance_rating = (
                'excellent' if overall_score >= 80 else
                'good' if overall_score >= 65 else
                'average' if overall_score >= 50 else
                'needs_improvement'
            )
            
            deputy_performance.append({
                'deputy_id': row.deputy_id,
                'name': row.deputy_name,
                'parliamentary_name': row.parliamentary_name,
                'party': row.party,
                'mandate_period': {
                    'legislature': row.legislature,
                    'days_since_created': row.days_since_mandate_created or 0
                },
                'attendance': {
                    'rate': attendance_rate,
                    'records_count': row.attendance_records or 0
                },
                'initiatives': {
                    'authored': initiatives_count,
                    'approved': row.initiatives_approved or 0,
                    'success_rate': initiative_success_rate,
                    'participated_in': row.initiatives_participated or 0
                },
                'participation': {
                    'total_activities': row.parliamentary_activities or 0,
                    'interventions': row.interventions_made or 0,
                    'recent_activities_90d': row.recent_activities or 0,
                    'activity_score': activity_score
                },
                'performance': {
                    'overall_score': overall_score,
                    'rating': performance_rating
                }
            })
        
        # 2. PARTY PERFORMANCE COMPARISON
        party_performance_query = text("""
            SELECT 
                p.sigla as party_acronym,
                p.designacao_completa as party_name,
                COUNT(DISTINCT d.id) as total_deputies,
                AVG(CASE WHEN aa.attendance_rate IS NOT NULL THEN aa.attendance_rate ELSE 0 END) as avg_party_attendance,
                COUNT(DISTINCT ip.id) as total_party_initiatives,
                COUNT(DISTINCT CASE WHEN iev.resultado LIKE '%aprovad%' THEN ip.id END) as approved_party_initiatives,
                AVG(
                    CASE WHEN ad.created_at >= CURRENT_DATE - INTERVAL '90 days'
                    THEN 1 ELSE 0 END
                ) as recent_activity_ratio
            FROM partidos p
            JOIN deputado_mandatos_legislativos dml ON p.sigla = dml.par_sigla
            JOIN deputados d ON dml.deputado_id = d.id
            LEFT JOIN attendance_analytics aa ON d.id = aa.deputado_id
            LEFT JOIN iniciativas_detalhadas ip ON ip.legislatura_id = :legislature_id
            LEFT JOIN iniciativas_eventos ie ON ip.id = ie.iniciativa_id
            LEFT JOIN iniciativas_eventos_votacoes iev ON ie.id = iev.evento_id
            LEFT JOIN atividade_deputados ad ON d.id = ad.deputado_id
            WHERE dml.leg_des LIKE '%XVII%'  -- Current legislature
            GROUP BY p.id, p.sigla, p.designacao_completa
            HAVING COUNT(DISTINCT d.id) > 0
            ORDER BY total_deputies DESC, avg_party_attendance DESC
        """)
        
        party_results = session.execute(
            party_performance_query,
            {'legislature_id': current_leg.id}
        ).fetchall()
        
        party_performance = []
        for row in party_results:
            initiative_success_rate = round(
                (row.approved_party_initiatives or 0) / max(row.total_party_initiatives or 1, 1) * 100, 1
            )
            
            party_performance.append({
                'party_acronym': row.party_acronym,
                'party_name': row.party_name,
                'deputies_count': row.total_deputies or 0,
                'avg_attendance': round(row.avg_party_attendance or 0, 1),
                'initiatives': {
                    'total': row.total_party_initiatives or 0,
                    'approved': row.approved_party_initiatives or 0,
                    'success_rate': initiative_success_rate
                },
                'recent_activity_score': round((row.recent_activity_ratio or 0) * 100, 1)
            })
        
        # 3. PERFORMANCE STATISTICS
        avg_attendance = round(total_attendance / max(total_deputies, 1), 1)
        avg_initiatives_per_deputy = round(total_initiatives / max(total_deputies, 1), 1)
        
        high_performers = len([d for d in deputy_performance if d['performance']['rating'] == 'excellent'])
        active_deputies = len([d for d in deputy_performance if d['participation']['recent_activities_90d'] > 5])
        
        return jsonify({
            'legislature': current_leg.numero,
            'last_updated': datetime.now().isoformat(),
            'analysis_period': {
                'total_deputies_analyzed': total_deputies,
                'avg_attendance_rate': avg_attendance,
                'avg_initiatives_per_deputy': avg_initiatives_per_deputy
            },
            
            'deputy_performance': deputy_performance,
            'party_performance': party_performance,
            
            'summary_statistics': {
                'high_performers': high_performers,
                'active_deputies_90d': active_deputies,
                'most_active_party': party_performance[0]['party_acronym'] if party_performance else None,
                'highest_attendance_party': max(party_performance, key=lambda x: x['avg_attendance'])['party_acronym'] if party_performance else None
            }
        })
        
    except Exception as e:
        logger.error(f"Error in deputy performance: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500
        
    finally:
        session.close()

@transparency_bp.route('/transparency/accountability-metrics', methods=['GET'])
def get_accountability_metrics():
    """
    Transparency & Accountability Metrics
    ====================================
    
    Provides comprehensive transparency metrics including government accountability,
    parliamentary efficiency, and citizen engagement indicators
    """
    session = get_session()
    
    try:
        current_leg = get_current_legislature()
        if not current_leg:
            return jsonify({'error': 'Current legislature not found'}), 404
            
        today = date.today()
        thirty_days_ago = today - timedelta(days=30)
        legislature_start = current_leg.data_inicio or date(2024, 3, 1)
        
        # 1. OVERALL ACCOUNTABILITY SCORE CALCULATION
        accountability_query = text("""
            SELECT 
                -- Government responsiveness metrics
                COUNT(DISTINCT pr.id) as total_questions,
                COUNT(DISTINCT prr.id) as answered_questions,
                AVG(prr.data_resposta - pr.dt_entrada) as avg_response_days,
                
                -- Legislative efficiency metrics
                COUNT(DISTINCT ip.id) as total_initiatives,
                COUNT(DISTINCT CASE WHEN iev.resultado LIKE '%aprovad%' THEN ip.id END) as approved_initiatives,
                COUNT(DISTINCT CASE WHEN ip.updated_at >= :thirty_days_ago THEN ip.id END) as recent_initiatives,
                
                -- Transparency metrics
                COUNT(DISTINCT ap.id) as total_meetings,
                COUNT(DISTINCT CASE WHEN ap.secao_nome LIKE '%público%' OR ap.tema_nome LIKE '%público%' THEN ap.id END) as public_meetings,
                COUNT(DISTINCT CASE WHEN ap.data_evento >= :thirty_days_ago THEN ap.id END) as recent_meetings,
                
                -- Citizen engagement metrics
                COUNT(DISTINCT pp.id) as total_petitions,
                COUNT(DISTINCT CASE WHEN pp.pet_situacao LIKE '%aprovad%' OR pp.pet_situacao LIKE '%aceite%' THEN pp.id END) as processed_petitions,
                AVG(pp.pet_nr_assinaturas) as avg_petition_support
                
            FROM legislaturas l
            LEFT JOIN perguntas_requerimentos pr ON l.id = pr.legislatura_id
            LEFT JOIN pergunta_requerimento_destinatarios prd ON pr.id = prd.pergunta_requerimento_id
            LEFT JOIN pergunta_requerimento_respostas prr ON prd.id = prr.destinatario_id
            LEFT JOIN iniciativas_detalhadas ip ON l.id = ip.legislatura_id
            LEFT JOIN iniciativas_eventos ie ON ip.id = ie.iniciativa_id
            LEFT JOIN iniciativas_eventos_votacoes iev ON ie.id = iev.evento_id
            LEFT JOIN agenda_parlamentar ap ON l.id = ap.legislatura_id
            LEFT JOIN peticoes_detalhadas pp ON l.id = pp.legislatura_id
            WHERE l.id = :legislature_id
            AND l.data_inicio >= :legislature_start
        """)
        
        metrics_result = session.execute(
            accountability_query,
            {
                'legislature_id': current_leg.id,
                'thirty_days_ago': thirty_days_ago,
                'legislature_start': legislature_start
            }
        ).fetchone()
        
        # Calculate core accountability metrics
        response_rate = round(
            (metrics_result.answered_questions or 0) / max(metrics_result.total_questions or 1, 1) * 100, 1
        )
        
        approval_rate = round(
            (metrics_result.approved_initiatives or 0) / max(metrics_result.total_initiatives or 1, 1) * 100, 1
        )
        
        transparency_rate = round(
            (metrics_result.public_meetings or 0) / max(metrics_result.total_meetings or 1, 1) * 100, 1
        )
        
        petition_processing_rate = round(
            (metrics_result.processed_petitions or 0) / max(metrics_result.total_petitions or 1, 1) * 100, 1
        )
        
        # 2. ACCOUNTABILITY SCORE CALCULATION
        # Weight different aspects: responsiveness (30%), efficiency (25%), transparency (25%), engagement (20%)
        accountability_score = round(
            (response_rate * 0.30 + 
             approval_rate * 0.25 + 
             transparency_rate * 0.25 + 
             petition_processing_rate * 0.20), 1
        )
        
        accountability_rating = (
            'excellent' if accountability_score >= 80 else
            'good' if accountability_score >= 65 else
            'satisfactory' if accountability_score >= 50 else
            'needs_improvement'
        )
        
        # 3. TREND ANALYSIS - Compare with previous periods
        trend_query = text("""
            SELECT 
                EXTRACT(MONTH FROM ap.data_evento) as month_num,
                EXTRACT(YEAR FROM ap.data_evento) as year_num,
                COUNT(DISTINCT ap.id) as monthly_meetings,
                COUNT(DISTINCT CASE WHEN ap.secao_nome LIKE '%público%' OR ap.tema_nome LIKE '%público%' THEN ap.id END) as monthly_public_meetings,
                COUNT(DISTINCT ip.id) as monthly_initiatives,
                COUNT(DISTINCT pr.id) as monthly_questions
            FROM agenda_parlamentar ap
            LEFT JOIN iniciativas_detalhadas ip ON ap.legislatura_id = ip.legislatura_id
                AND EXTRACT(MONTH FROM ip.updated_at) = EXTRACT(MONTH FROM ap.data_evento)
                AND EXTRACT(YEAR FROM ip.updated_at) = EXTRACT(YEAR FROM ap.data_evento)
            LEFT JOIN perguntas_requerimentos pr ON ap.legislatura_id = pr.legislatura_id
                AND EXTRACT(MONTH FROM pr.dt_entrada) = EXTRACT(MONTH FROM ap.data_evento)
                AND EXTRACT(YEAR FROM pr.dt_entrada) = EXTRACT(YEAR FROM ap.data_evento)
            WHERE ap.legislatura_id = :legislature_id
            AND ap.data_evento >= CURRENT_DATE - INTERVAL '6 months'
            GROUP BY EXTRACT(YEAR FROM ap.data_evento), EXTRACT(MONTH FROM ap.data_evento)
            ORDER BY year_num DESC, month_num DESC
            LIMIT 6
        """)
        
        trend_results = session.execute(
            trend_query,
            {'legislature_id': current_leg.id}
        ).fetchall()
        
        monthly_trends = []
        for row in trend_results:
            monthly_transparency = round(
                (row.monthly_public_meetings or 0) / max(row.monthly_meetings or 1, 1) * 100, 1
            )
            
            monthly_trends.append({
                'month': f"{row.year_num}-{row.month_num:02d}",
                'meetings': row.monthly_meetings or 0,
                'public_meetings': row.monthly_public_meetings or 0,
                'transparency_rate': monthly_transparency,
                'initiatives': row.monthly_initiatives or 0,
                'questions': row.monthly_questions or 0
            })
        
        # 4. KEY PERFORMANCE INDICATORS
        kpis = {
            'government_responsiveness': {
                'score': response_rate,
                'rating': 'excellent' if response_rate > 80 else 'good' if response_rate > 60 else 'needs_improvement',
                'avg_response_days': round(metrics_result.avg_response_days or 0, 1),
                'benchmark': 'Target: >75% response rate, <20 days average'
            },
            'legislative_efficiency': {
                'score': approval_rate,
                'rating': 'excellent' if approval_rate > 60 else 'good' if approval_rate > 40 else 'needs_improvement',
                'total_initiatives': metrics_result.total_initiatives or 0,
                'recent_activity': metrics_result.recent_initiatives or 0,
                'benchmark': 'Target: >50% approval rate, steady initiative flow'
            },
            'meeting_transparency': {
                'score': transparency_rate,
                'rating': 'excellent' if transparency_rate > 70 else 'good' if transparency_rate > 50 else 'needs_improvement',
                'total_meetings': metrics_result.total_meetings or 0,
                'recent_meetings': metrics_result.recent_meetings or 0,
                'benchmark': 'Target: >60% public meetings'
            },
            'citizen_engagement': {
                'score': petition_processing_rate,
                'rating': 'excellent' if petition_processing_rate > 70 else 'good' if petition_processing_rate > 50 else 'needs_improvement',
                'total_petitions': metrics_result.total_petitions or 0,
                'avg_support': round(metrics_result.avg_petition_support or 0, 0),
                'benchmark': 'Target: >60% petition processing rate'
            }
        }
        
        # 5. RECOMMENDATIONS BASED ON PERFORMANCE
        recommendations = []
        
        if response_rate < 60:
            recommendations.append({
                'area': 'Government Responsiveness',
                'priority': 'high',
                'recommendation': 'Establish mandatory response timeframes for parliamentary questions',
                'expected_impact': 'Improve government accountability and democratic dialogue'
            })
            
        if approval_rate < 40:
            recommendations.append({
                'area': 'Legislative Efficiency',
                'priority': 'medium',
                'recommendation': 'Review legislative process bottlenecks and committee workflows',
                'expected_impact': 'Increase successful completion rate of legislative initiatives'
            })
            
        if transparency_rate < 50:
            recommendations.append({
                'area': 'Meeting Transparency',
                'priority': 'high',
                'recommendation': 'Increase public access to committee meetings and parliamentary sessions',
                'expected_impact': 'Enhance democratic participation and public oversight'
            })
            
        if petition_processing_rate < 50:
            recommendations.append({
                'area': 'Citizen Engagement',
                'priority': 'medium',
                'recommendation': 'Streamline petition review process and provide regular status updates',
                'expected_impact': 'Strengthen citizen participation in democratic processes'
            })
        
        return jsonify({
            'legislature': current_leg.numero,
            'assessment_date': today.isoformat(),
            'analysis_period': {
                'start': legislature_start.isoformat(),
                'end': today.isoformat(),
                'days_analyzed': (today - legislature_start).days
            },
            
            'accountability_summary': {
                'overall_score': accountability_score,
                'overall_rating': accountability_rating,
                'score_breakdown': {
                    'responsiveness_weight': 30,
                    'efficiency_weight': 25,
                    'transparency_weight': 25,
                    'engagement_weight': 20
                }
            },
            
            'key_performance_indicators': kpis,
            'monthly_trends': monthly_trends,
            'improvement_recommendations': recommendations,
            
            'benchmark_comparison': {
                'meets_international_standards': accountability_score >= 70,
                'areas_above_benchmark': len([k for k in kpis.values() if k['score'] >= 60]),
                'areas_needing_attention': len([k for k in kpis.values() if k['score'] < 50]),
                'overall_democratic_health': 'strong' if accountability_score >= 75 else 'moderate' if accountability_score >= 60 else 'concerning'
            }
        })
        
    except Exception as e:
        logger.error(f"Error in accountability metrics: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500
        
    finally:
        session.close()

@transparency_bp.route('/transparency/citizen-participation', methods=['GET'])
def get_citizen_participation():
    """
    Citizen Participation Hub
    =========================
    
    Tracks citizen engagement through petitions, public consultations,
    and parliamentary openness indicators
    """
    session = get_session()
    
    try:
        current_leg = get_current_legislature()
        if not current_leg:
            return jsonify({'error': 'Current legislature not found'}), 404
            
        today = date.today()
        thirty_days_ago = today - timedelta(days=30)
        ninety_days_ago = today - timedelta(days=90)
        
        # 1. PETITION ANALYSIS
        petition_analysis_query = text("""
            SELECT 
                COUNT(DISTINCT pp.id) as total_petitions,
                COUNT(DISTINCT CASE WHEN pp.pet_data_entrada >= :thirty_days_ago THEN pp.id END) as recent_petitions,
                COUNT(DISTINCT CASE WHEN pp.pet_data_entrada >= :ninety_days_ago THEN pp.id END) as quarterly_petitions,
                AVG(pp.pet_nr_assinaturas) as avg_subscribers,
                COUNT(DISTINCT CASE WHEN pp.pet_nr_assinaturas > 500 THEN pp.id END) as high_support_petitions,
                COUNT(DISTINCT CASE WHEN pp.pet_situacao LIKE '%aprovad%' OR pp.pet_situacao LIKE '%aceite%' THEN pp.id END) as accepted_petitions,
                COUNT(DISTINCT CASE WHEN pp.pet_situacao LIKE '%rejeitad%' OR pp.pet_situacao LIKE '%recusad%' THEN pp.id END) as rejected_petitions,
                COUNT(DISTINCT CASE WHEN pp.pet_situacao LIKE '%anális%' OR pp.pet_situacao LIKE '%processo%' THEN pp.id END) as processing_petitions
            FROM peticoes_detalhadas pp
            WHERE pp.legislatura_id = :legislature_id
            AND pp.pet_data_entrada IS NOT NULL
        """)
        
        petition_result = session.execute(
            petition_analysis_query,
            {
                'legislature_id': current_leg.id,
                'thirty_days_ago': thirty_days_ago,
                'ninety_days_ago': ninety_days_ago
            }
        ).fetchone()
        
        # Calculate petition metrics
        total_petitions = petition_result.total_petitions or 0
        acceptance_rate = round(
            (petition_result.accepted_petitions or 0) / max(total_petitions, 1) * 100, 1
        ) if total_petitions > 0 else 0
        
        citizen_engagement_score = min(100, round(
            ((petition_result.recent_petitions or 0) * 3 + 
             (petition_result.high_support_petitions or 0) * 5 +
             acceptance_rate * 0.5), 1
        ))
        
        petition_data = {
            'total_petitions': total_petitions,
            'recent_activity': {
                'last_30_days': petition_result.recent_petitions or 0,
                'last_90_days': petition_result.quarterly_petitions or 0
            },
            'engagement_metrics': {
                'avg_subscribers': round(petition_result.avg_subscribers or 0, 0),
                'high_support_count': petition_result.high_support_petitions or 0,
                'citizen_engagement_score': citizen_engagement_score
            },
            'processing_status': {
                'accepted': petition_result.accepted_petitions or 0,
                'rejected': petition_result.rejected_petitions or 0,
                'processing': petition_result.processing_petitions or 0,
                'acceptance_rate': acceptance_rate
            }
        }
        
        # 2. RECENT HIGH-IMPACT PETITIONS
        recent_petitions_query = session.query(PeticaoParlamentar).filter(
            PeticaoParlamentar.legislatura_id == current_leg.id,
            PeticaoParlamentar.pet_data_entrada >= ninety_days_ago
        ).order_by(
            desc(PeticaoParlamentar.pet_nr_assinaturas)
        ).limit(10).all()
        
        recent_petitions = []
        for petition in recent_petitions_query:
            # Determine impact level
            subscribers = petition.pet_nr_assinaturas or 0
            impact_level = (
                'high' if subscribers > 1000 else
                'medium' if subscribers > 200 else
                'low'
            )
            
            recent_petitions.append({
                'id': petition.id,
                'title': petition.pet_assunto,  # petition subject
                'summary': petition.pet_assunto,  # use same for summary
                'subscribers': subscribers,
                'submission_date': petition.pet_data_entrada.isoformat() if petition.pet_data_entrada else None,
                'status': petition.pet_situacao,
                'impact_level': impact_level,
                'main_petitioner': petition.pet_autor  # petition author
            })
        
        # 3. PARLIAMENTARY OPENNESS INDICATORS
        openness_query = text("""
            SELECT 
                -- Meeting transparency
                COUNT(DISTINCT ap.id) as total_meetings,
                COUNT(DISTINCT CASE WHEN ap.secao_nome LIKE '%público%' OR ap.tema_nome LIKE '%público%' THEN ap.id END) as public_meetings,
                
                -- Information accessibility  
                COUNT(DISTINCT pr.id) as total_questions_to_govt,
                COUNT(DISTINCT prr.id) as total_govt_responses,
                
                -- Recent parliamentary activity visibility
                COUNT(DISTINCT CASE WHEN ap.data_evento >= :thirty_days_ago THEN ap.id END) as recent_meetings,
                COUNT(DISTINCT CASE WHEN ap.data_evento >= :thirty_days_ago AND (ap.secao_nome LIKE '%público%' OR ap.tema_nome LIKE '%público%') THEN ap.id END) as recent_public_meetings
                
            FROM agenda_parlamentar ap
            LEFT JOIN perguntas_requerimentos pr ON ap.legislatura_id = pr.legislatura_id
            LEFT JOIN pergunta_requerimento_destinatarios prd ON pr.id = prd.pergunta_requerimento_id
            LEFT JOIN pergunta_requerimento_respostas prr ON prd.id = prr.destinatario_id
            WHERE ap.legislatura_id = :legislature_id
            AND ap.data_evento >= :legislature_start
        """)
        
        legislature_start = current_leg.data_inicio or date(2024, 3, 1)
        
        openness_result = session.execute(
            openness_query,
            {
                'legislature_id': current_leg.id,
                'thirty_days_ago': thirty_days_ago,
                'legislature_start': legislature_start
            }
        ).fetchone()
        
        # Calculate openness metrics
        public_meeting_rate = round(
            (openness_result.public_meetings or 0) / max(openness_result.total_meetings or 1, 1) * 100, 1
        )
        
        govt_response_rate = round(
            (openness_result.total_govt_responses or 0) / max(openness_result.total_questions_to_govt or 1, 1) * 100, 1
        )
        
        recent_transparency_score = round(
            (openness_result.recent_public_meetings or 0) / max(openness_result.recent_meetings or 1, 1) * 100, 1
        )
        
        openness_indicators = {
            'meeting_transparency': {
                'total_meetings': openness_result.total_meetings or 0,
                'public_meetings': openness_result.public_meetings or 0,
                'public_meeting_rate': public_meeting_rate
            },
            'information_accessibility': {
                'questions_to_government': openness_result.total_questions_to_govt or 0,
                'government_responses': openness_result.total_govt_responses or 0,
                'response_rate': govt_response_rate
            },
            'recent_transparency': {
                'meetings_last_30d': openness_result.recent_meetings or 0,
                'public_meetings_last_30d': openness_result.recent_public_meetings or 0,
                'recent_transparency_score': recent_transparency_score
            }
        }
        
        # 4. OVERALL PARTICIPATION ASSESSMENT
        participation_rating = (
            'excellent' if citizen_engagement_score > 75 and acceptance_rate > 60 else
            'good' if citizen_engagement_score > 50 and acceptance_rate > 40 else
            'moderate' if citizen_engagement_score > 25 or acceptance_rate > 20 else
            'needs_improvement'
        )
        
        # Filter None values from lists
        key_strengths = [s for s in [
            'High petition acceptance rate' if acceptance_rate > 50 else None,
            'Strong citizen engagement' if citizen_engagement_score > 60 else None,
            'Good government responsiveness' if govt_response_rate > 70 else None,
            'High meeting transparency' if public_meeting_rate > 60 else None
        ] if s is not None]
        
        improvement_areas = [a for a in [
            'Petition processing speed' if acceptance_rate < 30 else None,
            'Citizen engagement' if citizen_engagement_score < 40 else None,
            'Government responsiveness' if govt_response_rate < 50 else None,
            'Meeting accessibility' if public_meeting_rate < 40 else None
        ] if a is not None]
        
        return jsonify({
            'legislature': current_leg.numero,
            'last_updated': datetime.now().isoformat(),
            'analysis_period': {
                'start_date': legislature_start.isoformat(),
                'current_date': today.isoformat()
            },
            
            'petition_data': petition_data,
            'recent_high_impact_petitions': recent_petitions,
            'openness_indicators': openness_indicators,
            
            'participation_summary': {
                'overall_rating': participation_rating,
                'citizen_engagement_score': citizen_engagement_score,
                'transparency_score': round((public_meeting_rate + govt_response_rate) / 2, 1),
                'key_strengths': key_strengths,
                'improvement_areas': improvement_areas
            }
        })
        
    except Exception as e:
        logger.error(f"Error in citizen participation: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500
        
    finally:
        session.close()