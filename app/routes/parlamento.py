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
    OrcamentoEstadoGrupoParlamentarVoto, Coligacao, ColigacaoPartido,
    RegistoInteressesUnified
)
from app.utils.attribution import AttributionBuilder, format_attribution_response

parlamento_bp = Blueprint('parlamento', __name__)


def calculate_party_demographics(deputados, session=None):
    """Calculate comprehensive demographic statistics for a list of deputies"""
    if not deputados:
        return {
            'genero': {},
            'profissoes': {'categorias': {}, 'total_especificadas': 0},
            'idades': {'cohorts_geracionais': {}, 'idade_media': 0, 'idade_mediana': 0},
            'educacao': {'niveis': {}, 'areas': {}},
            'geografia': {'regional': {}, 'circulos': {}},
            'renovacao': {'novos_deputados': 0, 'veteranos': 0, 'percentual_renovacao': 0},
            'experiencia_politica': {'categorias': {}, 'mandatos_anteriores': {}}
        }
    
    # Initialize counters
    gender_count = {}
    profession_count = {}
    age_groups = {}
    education_levels = {}
    education_areas = {}
    regional_count = {}
    circles_count = {}
    renewal_data = {'novos': 0, 'veteranos': 0}
    political_experience = {}
    mandate_counts = {}
    
    # Age tracking for statistics
    ages = []
    
    from datetime import datetime
    current_year = datetime.now().year
    
    for deputado in deputados:
        # Gender analysis
        if deputado.sexo:
            gender_map = {'M': 'Masculino', 'F': 'Feminino'}
            gender_label = gender_map.get(deputado.sexo, deputado.sexo)
            gender_count[gender_label] = gender_count.get(gender_label, 0) + 1
        
        # Age analysis with detailed statistics
        if deputado.data_nascimento:
            try:
                birth_year = deputado.data_nascimento.year
                age = current_year - birth_year
                ages.append(age)
                
                if age < 35:
                    age_group = '< 35 anos'
                elif age < 45:
                    age_group = '35-44 anos'
                elif age < 55:
                    age_group = '45-54 anos'
                elif age < 65:
                    age_group = '55-64 anos'
                else:
                    age_group = '65+ anos'
                
                age_groups[age_group] = age_groups.get(age_group, 0) + 1
            except:
                pass
        
        # Profession analysis with education inference
        if deputado.profissao:
            prof = deputado.profissao.strip()
            prof_lower = prof.lower()
            
            # Professional categories
            if any(word in prof_lower for word in ['advogado', 'jurista', 'direito']):
                category = 'Direito'
                education_areas['Direito'] = education_areas.get('Direito', 0) + 1
                education_levels['Superior'] = education_levels.get('Superior', 0) + 1
            elif any(word in prof_lower for word in ['professor', 'docente', 'educação']):
                category = 'Educação'
                education_areas['Educação'] = education_areas.get('Educação', 0) + 1
                education_levels['Superior'] = education_levels.get('Superior', 0) + 1
            elif any(word in prof_lower for word in ['médico', 'enfermeiro', 'saúde', 'farmacêutic']):
                category = 'Saúde'
                education_areas['Saúde'] = education_areas.get('Saúde', 0) + 1
                education_levels['Superior'] = education_levels.get('Superior', 0) + 1
            elif any(word in prof_lower for word in ['engenheiro', 'engenharia']):
                category = 'Engenharia/Técnico'
                education_areas['Engenharia'] = education_areas.get('Engenharia', 0) + 1
                education_levels['Superior'] = education_levels.get('Superior', 0) + 1
            elif any(word in prof_lower for word in ['técnico']):
                category = 'Engenharia/Técnico' 
                education_levels['Técnico'] = education_levels.get('Técnico', 0) + 1
            elif any(word in prof_lower for word in ['economista', 'gestor', 'empresário', 'gestão']):
                category = 'Economia/Gestão'
                education_areas['Economia/Gestão'] = education_areas.get('Economia/Gestão', 0) + 1
                education_levels['Superior'] = education_levels.get('Superior', 0) + 1
            elif any(word in prof_lower for word in ['político', 'deputado', 'autarca', 'vereador', 'presidente']):
                category = 'Política'
            else:
                category = 'Outras'
                education_levels['Não Especificado'] = education_levels.get('Não Especificado', 0) + 1
            
            profession_count[category] = profession_count.get(category, 0) + 1
        
        # Political experience analysis based on actual mandate data from database
        if session and deputado.id_cadastro:
            try:
                # Get all mandates for this deputy across all legislatures
                all_mandates = session.query(Deputado, Legislatura).join(
                    Legislatura, Deputado.legislatura_id == Legislatura.id
                ).filter(
                    Deputado.id_cadastro == deputado.id_cadastro
                ).count()
                
                total_mandates = max(1, all_mandates)  # At least 1 mandate
                
                if total_mandates == 1:
                    renewal_data['novos'] += 1
                    political_experience['Primeiro Mandato'] = political_experience.get('Primeiro Mandato', 0) + 1
                else:
                    renewal_data['veteranos'] += 1
                    if total_mandates >= 4:
                        political_experience['Muito Experiente (4+ mandatos)'] = political_experience.get('Muito Experiente (4+ mandatos)', 0) + 1
                    elif total_mandates >= 2:
                        political_experience['Experiente (2-3 mandatos)'] = political_experience.get('Experiente (2-3 mandatos)', 0) + 1
                
                mandate_counts[str(total_mandates)] = mandate_counts.get(str(total_mandates), 0) + 1
                
            except Exception as e:
                # Fallback: assume first mandate if we can't get mandate data
                renewal_data['novos'] += 1
                political_experience['Primeiro Mandato'] = political_experience.get('Primeiro Mandato', 0) + 1
                mandate_counts['1'] = mandate_counts.get('1', 0) + 1
        else:
            # Fallback: assume first mandate if no session or id_cadastro
            renewal_data['novos'] += 1
            political_experience['Primeiro Mandato'] = political_experience.get('Primeiro Mandato', 0) + 1
            mandate_counts['1'] = mandate_counts.get('1', 0) + 1
    
    # Get geographic data from mandate info if session available
    if session:
        try:
            # Get electoral circles distribution
            mandate_query = session.query(
                DeputadoMandatoLegislativo.ce_des,
                func.count(DeputadoMandatoLegislativo.ce_des)
            ).filter(
                DeputadoMandatoLegislativo.deputado_id.in_([d.id for d in deputados])
            ).group_by(DeputadoMandatoLegislativo.ce_des).all()
            
            for circle, count in mandate_query:
                if circle:
                    circles_count[circle] = count
                    
                    # Regional mapping
                    if circle in ['Lisboa']:
                        region = 'Lisboa e Vale do Tejo'
                    elif circle in ['Porto', 'Braga', 'Viana do Castelo']:
                        region = 'Norte'
                    elif circle in ['Coimbra', 'Leiria', 'Aveiro']:
                        region = 'Centro'
                    elif circle in ['Faro']:
                        region = 'Algarve'
                    elif circle in ['Setúbal', 'Santarém']:
                        region = 'Lisboa e Vale do Tejo'
                    elif circle in ['Évora', 'Beja']:
                        region = 'Alentejo'
                    elif circle in ['Açores']:
                        region = 'Açores'
                    elif circle in ['Madeira']:
                        region = 'Madeira'
                    elif circle in ['Europa', 'Fora da Europa']:
                        region = 'Emigração'
                    else:
                        region = 'Outros'
                    
                    regional_count[region] = regional_count.get(region, 0) + count
        except Exception as e:
            print(f"Error getting geographic data: {e}")
    
    # Calculate age statistics
    idade_media = round(sum(ages) / len(ages), 1) if ages else 0
    idade_mediana = round(sorted(ages)[len(ages)//2], 1) if ages else 0
    idade_min = min(ages) if ages else 0
    idade_max = max(ages) if ages else 0
    
    # Calculate renewal percentage
    total_deputies = len(deputados)
    percentual_renovacao = round((renewal_data['novos'] / total_deputies * 100), 1) if total_deputies > 0 else 0
    
    return {
        'genero': gender_count,
        'profissoes': {
            'categorias': profession_count,
            'total_especificadas': sum(profession_count.values())
        },
        'idades': {
            'cohorts_geracionais': age_groups,
            'idade_media': idade_media,
            'idade_mediana': idade_mediana,
            'min': idade_min,
            'max': idade_max,
            'total_com_idade': len(ages)
        },
        'educacao': {
            'niveis': education_levels,
            'areas': education_areas
        },
        'geografia': {
            'regional': regional_count,
            'circulos': circles_count
        },
        'renovacao': {
            'novos_deputados': renewal_data['novos'],
            'veteranos': renewal_data['veteranos'],
            'percentual_renovacao': percentual_renovacao
        },
        'experiencia_politica': {
            'categorias': political_experience,
            'mandatos_anteriores': mandate_counts
        }
    }


def deputado_to_dict(deputado, session=None):
    """Convert Deputado object to dictionary for JSON serialization with related data"""
    
    # Get related data if session is provided
    if session:
        # Get mandate info
        mandato = session.query(DeputadoMandatoLegislativo).filter_by(
            deputado_id=deputado.id
        ).first()
        
        # Get legislature info
        legislatura = session.query(Legislatura).filter_by(
            id=deputado.legislatura_id
        ).first()
    else:
        mandato = None
        legislatura = None
    
    return {
        'deputado_id': deputado.id,  # Frontend expects deputado_id
        'id': deputado.id,
        'id_cadastro': deputado.id_cadastro,
        'nome': deputado.nome,
        'nome_completo': deputado.nome_completo,
        'data_nascimento': deputado.data_nascimento.isoformat() if deputado.data_nascimento else None,
        'naturalidade': deputado.naturalidade,
        'profissao': deputado.profissao,
        'legislatura_id': deputado.legislatura_id,
        'foto_url': deputado.foto_url,  # Deprecated - kept for backward compatibility
        'picture_url': f'https://app.parlamento.pt/webutils/getimage.aspx?id={deputado.id_cadastro}&type=deputado' if deputado.id_cadastro else None,
        'sexo': deputado.sexo,
        'ativo': deputado.is_active,

        # Seat status - derived from DadosSituacaoDeputado
        'is_seated': deputado.is_seated,  # True if currently occupying a seat (Efetivo*)
        'mandate_status': deputado.mandate_status,  # Efetivo, Suspenso(Eleito), Renunciou, etc.

        # Mandate related data - use individual party sigla
        'partido_sigla': (
            mandato.gp_sigla if mandato and mandato.eh_coligacao and mandato.gp_sigla 
            else mandato.par_sigla if mandato 
            else None
        ),
        'circulo': mandato.ce_des if mandato else None,
        
        # Legislature data
        'legislatura_nome': legislatura.designacao if legislatura else None,
        'legislatura_numero': legislatura.numero if legislatura else None,
        
        # Fields expected by party page frontend
        'mandato_ativo': True if legislatura and legislatura.numero == 'XVII' else deputado.is_active,  # Party page expects this field name
        'ultima_legislatura': legislatura.numero if legislatura else None,  # Party page expects this field name
        
        # Basic career info placeholder (frontend expects this structure)
        'career_info': {
            'is_currently_active': deputado.is_active,
            'is_seated': deputado.is_seated,  # Currently occupying a seat
            'mandate_status': deputado.mandate_status,  # Current status description
            'is_multi_term': False,  # Would need complex query to determine
            'total_mandates': 1,  # Simplified for now
            'first_mandate': legislatura.numero if legislatura else None,
            'latest_mandate': legislatura.numero if legislatura else None,
            'parties_served': [(
                mandato.gp_sigla if mandato.eh_coligacao and mandato.gp_sigla
                else mandato.par_sigla
            )] if mandato and (mandato.par_sigla or mandato.gp_sigla) else []
        }
    }


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

@parlamento_bp.route('/deputados/<int:cad_id>/detalhes', methods=['GET'])
def get_deputado_detalhes(cad_id):
    """Retorna detalhes completos de um deputado com informações do mandato

    Query Parameters:
        attribution: Include data source attribution (true/false/detailed)
            - false (default): No attribution data
            - true: Include source summary
            - detailed: Include full query traces
    """
    # Parse attribution query parameter
    attribution_param = request.args.get('attribution', 'false').lower()
    include_attribution = attribution_param in ('true', 'detailed')
    detailed_attribution = attribution_param == 'detailed'

    try:
        with DatabaseSession() as session:
            # Initialize attribution builder if requested
            attribution = AttributionBuilder(session, detailed=detailed_attribution) if include_attribution else None

            # Find deputado by cad_id (unique across all legislatures)
            # Get their most recent legislature entry using proper ordering
            deputado = get_most_recent_deputy(session, cad_id)
            
            if not deputado:
                return jsonify({'error': 'Deputado not found'}), 404

            # Track deputy query for attribution
            if attribution:
                attribution.track_query(Deputado, [deputado], purpose="get_deputy_info")

            # Get mandate information from DeputadoMandatoLegislativo table
            mandato_info = session.query(DeputadoMandatoLegislativo).filter_by(
                deputado_id=deputado.id
            ).first()

            # Track mandate query for attribution
            if attribution and mandato_info:
                attribution.track_query(DeputadoMandatoLegislativo, [mandato_info], purpose="get_mandate_info")
            
            # Get legislature information
            legislatura = session.query(Legislatura).filter_by(
                id=deputado.legislatura_id
            ).first()
            
            # Build response with deputy details and mandate info
            response = deputado_to_dict(deputado, session)
            
            # Always provide mandato structure, even if mandate info is missing
            if mandato_info:
                response['mandato'] = {
                    'partido_sigla': mandato_info.par_sigla,
                    'partido_nome': mandato_info.par_des,
                    'circulo_eleitoral': mandato_info.ce_des,
                    'inicio': legislatura.data_inicio.isoformat() if legislatura and legislatura.data_inicio else None,
                    'fim': legislatura.data_fim.isoformat() if legislatura and legislatura.data_fim else None
                }
            else:
                # Provide empty mandato structure with dates from legislature
                response['mandato'] = {
                    'partido_sigla': None,
                    'partido_nome': None,
                    'circulo_eleitoral': None,
                    'inicio': legislatura.data_inicio.isoformat() if legislatura and legislatura.data_inicio else None,
                    'fim': legislatura.data_fim.isoformat() if legislatura and legislatura.data_fim else None
                }
            
            if legislatura:
                response['legislatura'] = {
                    'numero': legislatura.numero,
                    'designacao': legislatura.designacao,
                    'ativa': legislatura.numero == 'XVII'  # Only XVII is the current active legislature
                }
            
            # Calculate statistics for this deputy
            # Count interventions using id_cadastro
            total_intervencoes = session.query(func.count(IntervencaoParlamentar.id)).join(
                IntervencaoDeputado, IntervencaoParlamentar.id == IntervencaoDeputado.intervencao_id
            ).filter(
                IntervencaoDeputado.id_cadastro == deputado.id_cadastro
            ).scalar() or 0
            
            # Count initiatives authored using id_cadastro
            total_iniciativas = session.query(func.count(IniciativaParlamentar.id)).join(
                IniciativaAutorDeputado, IniciativaParlamentar.id == IniciativaAutorDeputado.iniciativa_id
            ).filter(
                IniciativaAutorDeputado.id_cadastro == deputado.id_cadastro
            ).scalar() or 0

            # Count approved initiatives - those that reached promulgation or publication
            # Approval phases: 380 (Promulgação), 526/532/537 (Promulgação versions),
            # 580 (Lei Publicação DR), 600 (Resolução AR Publicação DR)
            approval_phases = [380, 526, 532, 537, 580, 600]
            iniciativas_aprovadas = session.query(
                func.count(func.distinct(IniciativaParlamentar.id))
            ).join(
                IniciativaAutorDeputado, IniciativaParlamentar.id == IniciativaAutorDeputado.iniciativa_id
            ).join(
                IniciativaEvento, IniciativaParlamentar.id == IniciativaEvento.iniciativa_id
            ).filter(
                IniciativaAutorDeputado.id_cadastro == deputado.id_cadastro,
                IniciativaEvento.codigo_fase.in_(approval_phases)
            ).scalar() or 0

            # Calculate approval rate
            taxa_aprovacao = round((iniciativas_aprovadas / total_iniciativas * 100), 1) if total_iniciativas > 0 else 0.0

            # Count total mandates for this person using DeputadoMandatoLegislativo (actual mandates)
            total_mandatos = session.query(func.count(DeputadoMandatoLegislativo.id)).join(
                Deputado, DeputadoMandatoLegislativo.deputado_id == Deputado.id
            ).filter(
                Deputado.id_cadastro == deputado.id_cadastro
            ).scalar() or 1

            # Get all legislatures actually served by this person (based on actual mandates)
            legislaturas_servidas_query = session.query(Legislatura).join(
                DeputadoMandatoLegislativo, DeputadoMandatoLegislativo.leg_des == Legislatura.numero
            ).join(
                Deputado, DeputadoMandatoLegislativo.deputado_id == Deputado.id
            ).filter(
                Deputado.id_cadastro == deputado.id_cadastro
            ).distinct().all()
            
            legislaturas_list = [leg.numero for leg in legislaturas_servidas_query]
            legislaturas_servidas = ', '.join(sorted(legislaturas_list)) if legislaturas_list else legislatura.numero
            
            # Calculate actual years of service based on legislature dates
            anos_servico = 0
            if legislaturas_servidas_query:
                from datetime import datetime
                today = datetime.now().date()
                
                for leg in legislaturas_servidas_query:
                    if leg.data_inicio:
                        # If legislature has ended, use full duration
                        if leg.data_fim and leg.data_fim < today:
                            years = (leg.data_fim - leg.data_inicio).days / 365.25
                        # If legislature is ongoing, calculate from start to today
                        else:
                            years = (today - leg.data_inicio).days / 365.25
                        anos_servico += years
                
                # Round to 1 decimal place
                anos_servico = round(anos_servico, 1)
            
            # Calculate real attendance rate based on actual session attendance records
            taxa_assiduidade = 0.85  # Default value if no attendance data available
            
            if deputado.nome:
                # Query the meeting_attendances table for this deputy's session attendance
                from sqlalchemy import text
                
                attendance_query = text("""
                    SELECT 
                        sigla_falta,
                        COUNT(*) as session_count
                    FROM meeting_attendances 
                    WHERE dep_nome_parlamentar = :deputy_name
                    AND dt_reuniao IS NOT NULL
                    GROUP BY sigla_falta
                """)
                
                attendance_records = session.execute(attendance_query, {'deputy_name': deputado.nome}).fetchall()
                
                if attendance_records:
                    # Count different types of attendance
                    present_sessions = 0  # PR = Present
                    justified_absences = 0  # FJ, ME, QVJ, MP = Justified absences
                    unjustified_absences = 0  # FI = Unjustified absences  
                    total_sessions = 0
                    
                    for record in attendance_records:
                        sigla_falta, count = record
                        total_sessions += count
                        
                        if sigla_falta == 'PR':  # Present
                            present_sessions += count
                        elif sigla_falta in ['FJ', 'ME', 'QVJ', 'MP']:  # Justified absences
                            justified_absences += count
                        elif sigla_falta in ['FI', 'FA']:  # Unjustified absences
                            unjustified_absences += count
                        else:
                            # For unknown codes, treat as justified absence
                            justified_absences += count
                    
                    if total_sessions > 0:
                        # Calculate attendance rate:
                        # Present sessions count as 100% attendance
                        # Justified absences count as neutral (don't hurt attendance)
                        # Unjustified absences hurt attendance
                        
                        # Method 1: Simple presence rate (only count actual presence)
                        simple_attendance = present_sessions / total_sessions
                        
                        # Method 2: Adjusted rate (justify absences don't count against)
                        # Only penalize for unjustified absences
                        attendance_eligible_sessions = present_sessions + justified_absences
                        adjusted_attendance = attendance_eligible_sessions / total_sessions
                        
                        # Use the adjusted method for fairer calculation
                        taxa_assiduidade = round(adjusted_attendance, 3)
                        
                        # Cap at reasonable maximum (95%) to account for some expected absences
                        if taxa_assiduidade > 0.95:
                            taxa_assiduidade = 0.95
            
            # Calculate meaningful metrics based on political analyst recommendations
            
            # Legislative Effectiveness Metrics
            activity_rate = 0
            if anos_servico > 0:
                activity_rate = round((total_iniciativas + total_intervencoes) / anos_servico, 1)
            
            # Cross-party collaboration analysis - simplified approach
            # Count initiatives with multiple authors from different parties
            cross_party_initiatives = None  # TODO: Implement cross-party initiative counting
            
            # Experience level assessment
            experience_level = "Novato"
            if total_mandatos >= 4:
                experience_level = "Veterano"
            elif total_mandatos >= 2:
                experience_level = "Experiente"
            
            # Electoral consistency check
            electoral_circles = session.query(distinct(DeputadoMandatoLegislativo.ce_des)).join(
                Deputado, DeputadoMandatoLegislativo.deputado_id == Deputado.id
            ).filter(
                Deputado.id_cadastro == deputado.id_cadastro,
                DeputadoMandatoLegislativo.ce_des.isnot(None)
            ).all()
            
            electoral_consistency = len(electoral_circles) == 1 if electoral_circles else False
            main_electoral_circle = electoral_circles[0][0] if electoral_circles else None
            
            # Get current party for comparison metrics
            current_party = mandato_info.par_sigla if mandato_info else None
            
            # Comparative metrics - get party averages for context
            party_avg_initiatives = 0
            party_avg_interventions = 0
            national_percentile = 0
            
            if current_party:
                # Calculate party averages
                party_deputies = session.query(func.count(distinct(Deputado.id_cadastro))).join(
                    DeputadoMandatoLegislativo, Deputado.id == DeputadoMandatoLegislativo.deputado_id
                ).filter(
                    DeputadoMandatoLegislativo.par_sigla == current_party,
                    DeputadoMandatoLegislativo.leg_des == 'XVII'  # Current legislature
                ).scalar() or 1
                
                # Party total initiatives
                party_total_initiatives = session.query(func.count(distinct(IniciativaParlamentar.id))).join(
                    IniciativaAutorDeputado, IniciativaParlamentar.id == IniciativaAutorDeputado.iniciativa_id
                ).filter(
                    IniciativaAutorDeputado.gp == current_party
                ).scalar() or 0
                
                party_avg_initiatives = round(party_total_initiatives / party_deputies, 1) if party_deputies > 0 else 0
                
                # Calculate national percentile - simplified approach
                total_active_deputies = session.query(func.count(distinct(Deputado.id_cadastro))).join(
                    DeputadoMandatoLegislativo, Deputado.id == DeputadoMandatoLegislativo.deputado_id
                ).filter(
                    DeputadoMandatoLegislativo.leg_des == 'XVII'
                ).scalar() or 1
                
                # Simple percentile based on initiative count (could be enhanced)
                if total_iniciativas > party_avg_initiatives:
                    national_percentile = 75  # Above party average
                elif total_iniciativas > 0:
                    national_percentile = 50  # Has some initiatives
                else:
                    national_percentile = 25  # Below average activity
            
            # Get initiative types breakdown for this deputy
            initiative_types_query = session.query(
                IniciativaParlamentar.ini_tipo,
                IniciativaParlamentar.ini_desc_tipo,
                func.count(IniciativaParlamentar.id).label('count')
            ).join(
                IniciativaAutorDeputado,
                IniciativaParlamentar.id == IniciativaAutorDeputado.iniciativa_id
            ).filter(
                IniciativaAutorDeputado.id_cadastro == deputado.id_cadastro
            ).group_by(
                IniciativaParlamentar.ini_tipo,
                IniciativaParlamentar.ini_desc_tipo
            ).order_by(func.count(IniciativaParlamentar.id).desc()).all()

            iniciativas_por_tipo = []
            for ini_type in initiative_types_query:
                iniciativas_por_tipo.append({
                    'codigo': ini_type.ini_tipo,
                    'descricao': ini_type.ini_desc_tipo or ini_type.ini_tipo,
                    'total': ini_type.count
                })

            # Get per-legislature initiative counts for evolution tracking
            evolucao_legislaturas = []
            for leg in legislaturas_servidas_query:
                leg_initiatives = session.query(func.count(IniciativaParlamentar.id)).join(
                    IniciativaAutorDeputado,
                    IniciativaParlamentar.id == IniciativaAutorDeputado.iniciativa_id
                ).filter(
                    IniciativaAutorDeputado.id_cadastro == deputado.id_cadastro,
                    IniciativaParlamentar.ini_leg == leg.numero
                ).scalar() or 0

                leg_interventions = session.query(func.count(IntervencaoParlamentar.id)).join(
                    IntervencaoDeputado,
                    IntervencaoParlamentar.id == IntervencaoDeputado.intervencao_id
                ).join(
                    Legislatura,
                    IntervencaoParlamentar.legislatura_id == Legislatura.id
                ).filter(
                    IntervencaoDeputado.id_cadastro == deputado.id_cadastro,
                    Legislatura.numero == leg.numero
                ).scalar() or 0

                evolucao_legislaturas.append({
                    'legislatura': leg.numero,
                    'iniciativas': leg_initiatives,
                    'intervencoes': leg_interventions
                })

            # Sort by legislature number (most recent first for display)
            leg_order = {'XVII': 1, 'XVI': 2, 'XV': 3, 'XIV': 4, 'XIII': 5, 'XII': 6}
            evolucao_legislaturas.sort(key=lambda x: leg_order.get(x['legislatura'], 99))

            # Determine if deputy is in opposition (simplified check)
            # Government parties in XVII: PS (minority government)
            governo_partidos = ['PS']  # Update as needed for current government
            is_oposicao = current_party not in governo_partidos if current_party else True

            # Calculate opposition context for approval rates
            oposicao_context = {
                'is_oposicao': is_oposicao,
                'media_aprovacao_oposicao': 8,  # ~8% typical opposition approval
                'media_aprovacao_governo': 60,  # ~60% typical government approval
                'nota_metodologica': 'Deputados da oposição têm taxas de aprovação estruturalmente mais baixas devido à dinâmica parlamentar.'
            }

            # Replace simple statistics with meaningful political metrics
            response['estatisticas'] = {
                # Legislative Effectiveness
                'iniciativas_propostas': total_iniciativas,
                'iniciativas_aprovadas': iniciativas_aprovadas,
                'taxa_aprovacao': taxa_aprovacao,
                'iniciativas_por_tipo': iniciativas_por_tipo,
                'taxa_atividade_anual': activity_rate,
                'colaboracao_inter_partidaria': cross_party_initiatives,

                # Parliamentary Engagement
                'intervencoes_parlamentares': total_intervencoes,
                'taxa_assiduidade': taxa_assiduidade,
                'tempo_servico_anos': anos_servico,

                # Political Profile
                'nivel_experiencia': experience_level,
                'total_mandatos': total_mandatos,
                'legislaturas_servidas': legislaturas_servidas,
                'consistencia_eleitoral': electoral_consistency,
                'circulo_principal': main_electoral_circle,

                # Evolution & Trends
                'evolucao_legislaturas': evolucao_legislaturas,

                # Comparative Context
                'percentil_nacional': national_percentile,
                'media_partido_iniciativas': party_avg_initiatives,
                'partido_atual': current_party,
                'contexto_oposicao': oposicao_context
            }
            
            # Get all mandates for this person across all legislatures
            # IMPORTANT: Only include records that have actual mandate data (DeputadoMandatoLegislativo)
            # to avoid showing orphan Deputado records from incorrect data imports
            mandatos_historico = []
            if deputado.id_cadastro:
                # Query only deputies that have actual mandate records
                all_mandates = session.query(
                    Deputado, Legislatura, DeputadoMandatoLegislativo
                ).join(
                    Legislatura, Deputado.legislatura_id == Legislatura.id
                ).join(
                    DeputadoMandatoLegislativo, DeputadoMandatoLegislativo.deputado_id == Deputado.id
                ).filter(
                    Deputado.id_cadastro == deputado.id_cadastro
                ).order_by(desc(Legislatura.data_inicio)).all()

                # Process each unique mandate (deduplicate by legislature)
                seen_legislatures = set()
                for dep, leg, mand in all_mandates:
                    # Skip if we've already processed this legislature
                    if leg.numero in seen_legislatures:
                        continue
                    seen_legislatures.add(leg.numero)

                    mandato_data = {
                        'deputado_id': dep.id,
                        'legislatura_numero': leg.numero,
                        'legislatura_nome': leg.designacao,
                        'mandato_inicio': leg.data_inicio.isoformat() if leg.data_inicio else None,
                        'mandato_fim': leg.data_fim.isoformat() if leg.data_fim else None,
                        'circulo': mand.ce_des,
                        'partido_sigla': mand.par_sigla,
                        'partido_nome': mand.par_des,
                        'is_current': leg.numero == 'XVII'
                    }
                    mandatos_historico.append(mandato_data)

            response['mandatos_historico'] = mandatos_historico

            # Add attribution data if requested
            if include_attribution and attribution:
                response = format_attribution_response(
                    response,
                    attribution,
                    include_attribution=True,
                    deputy_id=deputado.id_cadastro
                )

            return jsonify(response)

    except Exception as e:
        return log_and_return_error(e, '/api/deputados/<id>/detalhes')


@parlamento_bp.route('/partidos/<path:partido_sigla>/deputados', methods=['GET'])
def get_partido_deputados(partido_sigla):
    """Retorna deputados de um partido usando nova estrutura de dados.

    Returns unique people (by id_cadastro) with their most recent mandate info,
    showing only one entry per person instead of one per legislature.
    """
    try:
        # URL decode the party sigla to handle special characters like slashes
        from urllib.parse import unquote
        partido_sigla = unquote(partido_sigla)

        legislatura = request.args.get('legislatura', None, type=str)

        with DatabaseSession() as session:
            # First try to get the party information from the partidos table
            partido = session.query(Partido).filter_by(sigla=partido_sigla).first()

            # If not found in partidos table, check if it exists in mandate table
            if not partido:
                mandate_exists = session.query(DeputadoMandatoLegislativo).filter(
                    DeputadoMandatoLegislativo.par_sigla == partido_sigla
                ).first()

                if not mandate_exists:
                    return jsonify({'error': 'Party not found'}), 404

                # Create a mock party object with data from mandate table
                class MockParty:
                    def __init__(self, sigla, nome):
                        self.sigla = sigla
                        self.nome = nome
                        self.designacao_completa = nome
                        self.cor_hex = None
                        self.is_active = True

                partido = MockParty(partido_sigla, mandate_exists.par_des or partido_sigla)

            # Build party filter (exact match or pattern for coalitions)
            def get_party_filter(use_pattern=False):
                if use_pattern:
                    return DeputadoMandatoLegislativo.par_sigla.like(f'%{partido_sigla}%')
                return DeputadoMandatoLegislativo.par_sigla == partido_sigla

            # Get unique id_cadastro values for people who served in this party
            # with their most recent legislature for this party
            def get_unique_deputies(use_pattern=False):
                party_filter = get_party_filter(use_pattern)

                if legislatura:
                    # For specific legislature, get deputies from that legislature
                    deputy_mandates = session.query(
                        DeputadoMandatoLegislativo.deputado_id,
                        Deputado.id_cadastro,
                        DeputadoMandatoLegislativo.leg_des,
                        DeputadoMandatoLegislativo.ce_des,
                        DeputadoMandatoLegislativo.par_sigla,
                        DeputadoMandatoLegislativo.gp_sigla,
                        DeputadoMandatoLegislativo.eh_coligacao
                    ).join(
                        Deputado, DeputadoMandatoLegislativo.deputado_id == Deputado.id
                    ).filter(
                        party_filter,
                        DeputadoMandatoLegislativo.leg_des == legislatura
                    ).all()
                else:
                    # Get all unique people who ever served for this party
                    # First, get the most recent mandate for each person with this party
                    deputy_mandates = session.query(
                        DeputadoMandatoLegislativo.deputado_id,
                        Deputado.id_cadastro,
                        DeputadoMandatoLegislativo.leg_des,
                        DeputadoMandatoLegislativo.ce_des,
                        DeputadoMandatoLegislativo.par_sigla,
                        DeputadoMandatoLegislativo.gp_sigla,
                        DeputadoMandatoLegislativo.eh_coligacao,
                        Legislatura.data_inicio
                    ).join(
                        Deputado, DeputadoMandatoLegislativo.deputado_id == Deputado.id
                    ).join(
                        Legislatura, Deputado.legislatura_id == Legislatura.id
                    ).filter(
                        party_filter
                    ).order_by(
                        desc(Legislatura.data_inicio)
                    ).all()

                return deputy_mandates

            # Get deputies with exact match first (historical party members)
            deputy_mandates = get_unique_deputies(use_pattern=False)

            # If no results, try pattern matching for coalitions
            if not deputy_mandates:
                deputy_mandates = get_unique_deputies(use_pattern=True)

            # Also include current XVII coalition deputies who sit with this party (gp_sigla)
            # This ensures deputies like Paulo (only coalition mandates, but gp_sigla=CDS-PP) are included
            current_gp_members = session.query(
                DeputadoMandatoLegislativo.deputado_id,
                Deputado.id_cadastro,
                DeputadoMandatoLegislativo.leg_des,
                DeputadoMandatoLegislativo.ce_des,
                DeputadoMandatoLegislativo.par_sigla,
                DeputadoMandatoLegislativo.gp_sigla,
                DeputadoMandatoLegislativo.eh_coligacao,
                Legislatura.data_inicio
            ).join(
                Deputado, DeputadoMandatoLegislativo.deputado_id == Deputado.id
            ).join(
                Legislatura, Deputado.legislatura_id == Legislatura.id
            ).filter(
                DeputadoMandatoLegislativo.gp_sigla == partido_sigla,
                DeputadoMandatoLegislativo.leg_des == 'XVII'
            ).all()

            # Get existing id_cadastros from deputy_mandates
            existing_cadastros = {m.id_cadastro for m in deputy_mandates}

            # Add any XVII gp_sigla members not already in the list
            for gp_member in current_gp_members:
                if gp_member.id_cadastro not in existing_cadastros:
                    deputy_mandates.append(gp_member)
                    existing_cadastros.add(gp_member.id_cadastro)

            # Group by id_cadastro to get unique people
            # Keep track of most recent mandate per person
            unique_people = {}
            for mandate in deputy_mandates:
                id_cadastro = mandate.id_cadastro
                if id_cadastro not in unique_people:
                    unique_people[id_cadastro] = {
                        'deputado_id': mandate.deputado_id,
                        'id_cadastro': id_cadastro,
                        'leg_des': mandate.leg_des,
                        'ce_des': mandate.ce_des,
                        'par_sigla': mandate.par_sigla,
                        'gp_sigla': mandate.gp_sigla,
                        'eh_coligacao': mandate.eh_coligacao
                    }
                # If not filtered by legislature, keep the most recent (first in desc order)

            # Check which people have active mandates in XVII with this party
            # Include both direct party members (par_sigla) AND parliamentary group members (gp_sigla)
            active_id_cadastros = set()

            # First check exact par_sigla match
            party_filter = get_party_filter(use_pattern=False)
            active_query = session.query(
                Deputado.id_cadastro
            ).join(
                DeputadoMandatoLegislativo, Deputado.id == DeputadoMandatoLegislativo.deputado_id
            ).filter(
                party_filter,
                DeputadoMandatoLegislativo.leg_des == 'XVII'
            ).distinct()

            for row in active_query:
                active_id_cadastros.add(row.id_cadastro)

            # If no active with exact match, try pattern matching on par_sigla
            if not active_id_cadastros:
                party_filter = get_party_filter(use_pattern=True)
                active_query = session.query(
                    Deputado.id_cadastro
                ).join(
                    DeputadoMandatoLegislativo, Deputado.id == DeputadoMandatoLegislativo.deputado_id
                ).filter(
                    party_filter,
                    DeputadoMandatoLegislativo.leg_des == 'XVII'
                ).distinct()

                for row in active_query:
                    active_id_cadastros.add(row.id_cadastro)

            # Also include XVII deputies with gp_sigla matching this party (parliamentary group)
            # This correctly identifies CDS-PP members who are part of a coalition
            gp_active_query = session.query(
                Deputado.id_cadastro
            ).join(
                DeputadoMandatoLegislativo, Deputado.id == DeputadoMandatoLegislativo.deputado_id
            ).filter(
                DeputadoMandatoLegislativo.gp_sigla == partido_sigla,
                DeputadoMandatoLegislativo.leg_des == 'XVII'
            ).distinct()

            for row in gp_active_query:
                active_id_cadastros.add(row.id_cadastro)

            # Build result list with proper active status
            result_deputies = []
            for id_cadastro, mandate_info in unique_people.items():
                # Determine if this person is currently active with this party
                is_active = id_cadastro in active_id_cadastros

                # For ACTIVE deputies, ALWAYS use their XVII legislature data
                if is_active:
                    # Get the XVII Deputado record for this person
                    xvii_deputado = session.query(Deputado).join(
                        DeputadoMandatoLegislativo, Deputado.id == DeputadoMandatoLegislativo.deputado_id
                    ).filter(
                        Deputado.id_cadastro == id_cadastro,
                        DeputadoMandatoLegislativo.leg_des == 'XVII'
                    ).first()

                    if xvii_deputado:
                        deputado = xvii_deputado
                        legislatura_obj = session.query(Legislatura).filter_by(numero='XVII').first()
                        # Update mandate_info to reflect XVII data
                        xvii_mandate = session.query(DeputadoMandatoLegislativo).filter_by(
                            deputado_id=xvii_deputado.id
                        ).first()
                        if xvii_mandate:
                            mandate_info = {
                                'deputado_id': xvii_deputado.id,
                                'id_cadastro': id_cadastro,
                                'leg_des': 'XVII',
                                'ce_des': xvii_mandate.ce_des,
                                'par_sigla': xvii_mandate.par_sigla,
                                'gp_sigla': xvii_mandate.gp_sigla,
                                'eh_coligacao': xvii_mandate.eh_coligacao
                            }
                    else:
                        # Fallback to stored mandate_info if XVII not found
                        deputado = session.query(Deputado).filter_by(id=mandate_info['deputado_id']).first()
                        legislatura_obj = session.query(Legislatura).filter_by(id=deputado.legislatura_id).first() if deputado else None
                else:
                    # For inactive deputies, use the stored mandate info (most recent mandate)
                    deputado = session.query(Deputado).filter_by(id=mandate_info['deputado_id']).first()
                    legislatura_obj = session.query(Legislatura).filter_by(id=deputado.legislatura_id).first() if deputado else None

                if not deputado:
                    continue

                result_deputies.append({
                    'deputado_id': deputado.id,
                    'id': deputado.id,
                    'id_cadastro': deputado.id_cadastro,
                    'nome': deputado.nome,
                    'nome_completo': deputado.nome_completo,
                    'data_nascimento': deputado.data_nascimento.isoformat() if deputado.data_nascimento else None,
                    'naturalidade': deputado.naturalidade,
                    'profissao': deputado.profissao,
                    'legislatura_id': deputado.legislatura_id,
                    'foto_url': deputado.foto_url,
                    'picture_url': f'https://app.parlamento.pt/webutils/getimage.aspx?id={deputado.id_cadastro}&type=deputado' if deputado.id_cadastro else None,
                    'sexo': deputado.sexo,
                    'ativo': deputado.is_active,
                    'partido_sigla': (
                        mandate_info['gp_sigla'] if mandate_info.get('eh_coligacao') and mandate_info.get('gp_sigla')
                        else mandate_info['par_sigla']
                    ),
                    'circulo': mandate_info['ce_des'],
                    'legislatura_nome': legislatura_obj.designacao if legislatura_obj else None,
                    'legislatura_numero': legislatura_obj.numero if legislatura_obj else None,
                    # CRITICAL: mandato_ativo is True ONLY if they have XVII mandate with this party
                    'mandato_ativo': is_active,
                    'ultima_legislatura': mandate_info['leg_des'],
                    'career_info': {
                        'is_currently_active': is_active,
                        'is_multi_term': False,
                        'total_mandates': 1,
                        'first_mandate': mandate_info['leg_des'],
                        'latest_mandate': mandate_info['leg_des'],
                        'parties_served': [mandate_info['gp_sigla'] if mandate_info.get('eh_coligacao') and mandate_info.get('gp_sigla') else mandate_info['par_sigla']] if mandate_info.get('par_sigla') or mandate_info.get('gp_sigla') else []
                    }
                })

            # Sort: active first, then by name
            result_deputies.sort(key=lambda x: (not x['mandato_ativo'], x['nome'] or ''))

            # Check if this party is part of any coalition
            coalition_query = session.query(
                DeputadoMandatoLegislativo.coligacao_id,
                DeputadoMandatoLegislativo.eh_coligacao
            ).filter(
                DeputadoMandatoLegislativo.par_sigla == partido_sigla,
                DeputadoMandatoLegislativo.eh_coligacao == True
            )

            if legislatura:
                coalition_query = coalition_query.filter(DeputadoMandatoLegislativo.leg_des == legislatura)

            coalition_info = coalition_query.first()

            coalition_data = None
            if coalition_info and coalition_info.coligacao_id:
                # Get coalition information
                coalition = session.query(Coligacao).filter_by(id=coalition_info.coligacao_id).first()
                if coalition:
                    coalition_data = {
                        'sigla': coalition.sigla,
                        'nome': coalition.nome,
                        'id': coalition.id
                    }

            # Calculate demographic data using Deputado objects for compatibility
            deputado_objs = [session.query(Deputado).filter_by(id=d['deputado_id']).first() for d in result_deputies]
            deputado_objs = [d for d in deputado_objs if d]  # Filter None
            demographic_data = calculate_party_demographics(deputado_objs, session)

            # Count active mandates (only historical party members who are currently active)
            # This is the intersection of our unique people and those with XVII mandate
            mandatos_ativos = sum(1 for d in result_deputies if d['mandato_ativo'])

            return jsonify({
                'deputados': result_deputies,
                'total': len(result_deputies),
                'mandatos_ativos': mandatos_ativos,
                'partido': {
                    'sigla': partido.sigla,
                    'nome': partido.nome,
                    'designacao_completa': partido.designacao_completa,
                    'cor_hex': partido.cor_hex,
                    'ativo': partido.is_active
                },
                'coligacao': coalition_data,
                'legislatura': legislatura,
                'demografia': demographic_data
            })

    except Exception as e:
        return log_and_return_error(e, '/api/partidos/<id>/deputados')


# =============================================================================
# PHASE 3: COMPLEX FEATURES
# =============================================================================

@parlamento_bp.route('/deputados/<int:cad_id>/atividades', methods=['GET'])
def get_deputado_atividades(cad_id):
    """Retorna atividades parlamentares de um deputado"""
    try:
        # Get legislature parameter (defaults to current/latest)
        requested_legislature = request.args.get('legislatura', None, type=str)
        
        with DatabaseSession() as session:
            # Find deputado by cad_id (unique across all legislatures)
            if requested_legislature:
                # Get specific legislature
                leg = session.query(Legislatura).filter_by(numero=requested_legislature).first()
                if not leg:
                    return jsonify({'error': f'Legislature {requested_legislature} not found'}), 404
                
                # Find deputado in that specific legislature
                deputado = session.query(Deputado).filter(
                    Deputado.id_cadastro == cad_id,
                    Deputado.legislatura_id == leg.id
                ).first()
                
                # If deputy didn't serve in that legislature, return empty results
                if not deputado:
                    return jsonify({
                        'deputado': {'id_cadastro': cad_id, 'served_in_legislature': False},
                        'intervencoes': [],
                        'iniciativas': [],
                        'votacoes': [],
                        'legislatura': leg.numero,
                        'message': f'Deputy did not serve in legislature {requested_legislature}'
                    })
            else:
                # Get their most recent legislature entry (default behavior)
                deputado = get_most_recent_deputy(session, cad_id)
                
                if not deputado:
                    return jsonify({'error': 'Deputado not found'}), 404
                
                # Use the deputy's actual legislature for filtering
                leg = session.query(Legislatura).filter_by(id=deputado.legislatura_id).first()
                if not leg:
                    return jsonify({
                        'intervencoes': [],
                        'iniciativas': [],
                        'votacoes': []
                    })
            
            # Get interventions for this deputy using id_cadastro
            intervencoes_query = session.query(IntervencaoParlamentar).join(
                IntervencaoDeputado, IntervencaoParlamentar.id == IntervencaoDeputado.intervencao_id
            ).filter(
                IntervencaoDeputado.id_cadastro == deputado.id_cadastro,
                IntervencaoParlamentar.legislatura_id == leg.id
            ).limit(50).all()
            
            intervencoes = []
            for interv in intervencoes_query:
                # Get publication data from related publications
                publicacao = None
                if interv.publicacoes:
                    pub = interv.publicacoes[0]  # Get first publication
                    publicacao = {
                        'pub_tipo': pub.pub_tp if hasattr(pub, 'pub_tp') else None,
                        'pub_data': pub.pub_dt.isoformat() if hasattr(pub, 'pub_dt') and pub.pub_dt else None,
                        'pub_numero': pub.pub_nr if hasattr(pub, 'pub_nr') else None,
                        'paginas': pub.pag if hasattr(pub, 'pag') else None,
                        'url_diario': pub.url_diario if hasattr(pub, 'url_diario') else None
                    }
                
                intervencoes.append({
                    'id': interv.intervencao_id or interv.id,
                    'tipo': interv.tipo_intervencao,
                    'qualidade': interv.qualidade,
                    'sessao_numero': interv.sessao_numero,
                    'data': interv.data_reuniao_plenaria.isoformat() if interv.data_reuniao_plenaria else None,
                    'assunto': interv.debate,  # Use debate as subject
                    'resumo': interv.resumo,
                    'sumario': interv.sumario,
                    'fase_sessao': interv.fase_sessao,
                    'publicacao': publicacao,
                    # Video fields - not available in current model, set to None
                    'url_video': None,
                    'thumbnail_url': None,
                    'duracao_video': None
                })
            
            # Get initiatives authored by this deputy using id_cadastro
            iniciativas_query = session.query(IniciativaParlamentar).join(
                IniciativaAutorDeputado, IniciativaParlamentar.id == IniciativaAutorDeputado.iniciativa_id
            ).filter(
                IniciativaAutorDeputado.id_cadastro == deputado.id_cadastro,
                IniciativaParlamentar.legislatura_id == leg.id
            ).limit(50).all()

            # Phase codes for status determination
            approval_phases = {380, 526, 532, 537, 580, 600}  # Promulgação and publication phases
            rejection_phases = {30}  # Não admissão
            withdrawn_phases = {648}  # Retirada da iniciativa
            expired_phases = {649, 650}  # Caducada, Prejudicada
            voting_phases = {250, 310, 320, 330}  # Votação phases

            def get_initiative_status(eventos):
                """Determine initiative status from its events"""
                if not eventos:
                    return 'Em tramitação', False

                # Get all phase codes from events
                phase_codes = {e.codigo_fase for e in eventos if e.codigo_fase}

                # Check status in priority order
                if phase_codes & approval_phases:
                    return 'Aprovado', True
                if phase_codes & rejection_phases:
                    return 'Rejeitado', False
                if phase_codes & withdrawn_phases:
                    return 'Retirado', False
                if phase_codes & expired_phases:
                    return 'Caducado', False
                if phase_codes & voting_phases:
                    return 'Em votação', False

                return 'Em tramitação', False

            iniciativas = []
            for inic in iniciativas_query:
                # Get the latest event to determine current status/phase
                latest_event = None
                if inic.eventos:
                    # Sort events by date_fase to get the most recent
                    sorted_events = sorted(
                        [e for e in inic.eventos if e.data_fase],
                        key=lambda x: x.data_fase,
                        reverse=True
                    )
                    if sorted_events:
                        latest_event = sorted_events[0]

                # Get voting result from latest event if available
                resultado = None
                if latest_event and latest_event.votacoes:
                    # Get the latest voting result
                    latest_voting = sorted(
                        [v for v in latest_event.votacoes if v.data_votacao],
                        key=lambda x: x.data_votacao,
                        reverse=True
                    )
                    if latest_voting:
                        resultado = latest_voting[0].resultado

                # Determine initiative status based on all events
                estado, aprovada = get_initiative_status(inic.eventos)

                # Build URLs object for parliamentary links
                urls = {}
                if inic.ini_link_texto:
                    urls['documento'] = inic.ini_link_texto

                # Build parliamentary search URLs as fallbacks
                search_title = inic.ini_titulo or f"Iniciativa {inic.ini_nr}"
                urls['debates'] = f"https://www.parlamento.pt/site/search/Pages/pesquisa.aspx?sq={search_title}"
                urls['oficial'] = f"https://www.parlamento.pt/ActividadeParlamentar/Paginas/Iniciativas.aspx?txt={search_title}"

                iniciativas.append({
                    'id': inic.ini_id if hasattr(inic, 'ini_id') else inic.id,
                    'numero': inic.ini_nr if hasattr(inic, 'ini_nr') else None,
                    'titulo': inic.ini_titulo if hasattr(inic, 'ini_titulo') else None,
                    'tipo': inic.ini_tipo if hasattr(inic, 'ini_tipo') else None,
                    'tipo_descricao': inic.ini_desc_tipo if hasattr(inic, 'ini_desc_tipo') else None,
                    'estado': estado,
                    'aprovada': aprovada,
                    'fase_atual': latest_event.fase if latest_event else None,
                    'data_apresentacao': latest_event.data_fase.isoformat() if latest_event and latest_event.data_fase else None,
                    'data': latest_event.data_fase.isoformat() if latest_event and latest_event.data_fase else None,
                    'resultado': resultado,
                    'urls': urls,
                    'link_texto': inic.ini_link_texto if hasattr(inic, 'ini_link_texto') else None,
                    'observacoes': inic.ini_obs if hasattr(inic, 'ini_obs') else None
                })
            
            # Get total counts across all legislatures for this deputy
            total_intervencoes_count = session.query(func.count(IntervencaoParlamentar.id)).join(
                IntervencaoDeputado, IntervencaoParlamentar.id == IntervencaoDeputado.intervencao_id
            ).filter(
                IntervencaoDeputado.id_cadastro == deputado.id_cadastro
            ).scalar()
            
            total_iniciativas_count = session.query(func.count(IniciativaParlamentar.id)).join(
                IniciativaAutorDeputado, IniciativaParlamentar.id == IniciativaAutorDeputado.iniciativa_id
            ).filter(
                IniciativaAutorDeputado.id_cadastro == deputado.id_cadastro
            ).scalar()
            
            # Current legislature counts
            current_intervencoes_count = len(intervencoes)
            current_iniciativas_count = len(iniciativas)
            
            # Get attendance statistics
            attendance_stats = {'current_legislature': {'attendance_rate': 0}, 'total_career': {'attendance_rate': 0}}
            try:
                # Query attendance records for current legislature
                from sqlalchemy import text
                attendance_query = text("""
                    SELECT 
                        sigla_falta,
                        COUNT(*) as count
                    FROM meeting_attendances 
                    WHERE dep_nome_parlamentar = :deputy_name
                    AND dt_reuniao IS NOT NULL
                    GROUP BY sigla_falta
                """)
                
                attendance_records = session.execute(attendance_query, {'deputy_name': deputado.nome}).fetchall()
                
                # Attendance code meanings
                attendance_codes = {
                    'PR': 'present',
                    'FJ': 'justified', 'ME': 'justified', 'QVJ': 'justified', 'MP': 'justified', 'FIJ': 'justified',
                    'FI': 'unjustified', 'FA': 'unjustified'
                }
                
                total_sessions = 0
                present_sessions = 0
                justified_sessions = 0
                
                for record in attendance_records:
                    sigla_falta, count = record
                    total_sessions += count
                    
                    attendance_type = attendance_codes.get(sigla_falta, 'other')
                    if attendance_type == 'present':
                        present_sessions += count
                    elif attendance_type == 'justified':
                        justified_sessions += count
                
                # Calculate attendance rate (present + justified / total)
                if total_sessions > 0:
                    good_attendance = present_sessions + justified_sessions
                    attendance_rate = round(good_attendance / total_sessions, 3)
                    
                    # For now, use the same rate for both current and total (since we don't have legislature-specific attendance data)
                    attendance_stats = {
                        'current_legislature': {'attendance_rate': attendance_rate, 'total_sessions': total_sessions},
                        'total_career': {'attendance_rate': attendance_rate, 'total_sessions': total_sessions}
                    }
            except Exception as e:
                print(f"Warning: Could not get attendance data: {e}")
            
            return jsonify({
                'deputado': {
                    'id': deputado.id,
                    'nome': deputado.nome,
                    'id_cadastro': deputado.id_cadastro
                },
                'legislatura': {
                    'numero': leg.numero,
                    'designacao': leg.designacao
                },
                'statistics': {
                    'current_legislature': {
                        'intervencoes_count': current_intervencoes_count,
                        'iniciativas_count': current_iniciativas_count,
                        'attendance_rate': attendance_stats['current_legislature']['attendance_rate'],
                        'total_sessions': attendance_stats['current_legislature'].get('total_sessions', 0)
                    },
                    'total_career': {
                        'intervencoes_count': total_intervencoes_count,
                        'iniciativas_count': total_iniciativas_count,
                        'attendance_rate': attendance_stats['total_career']['attendance_rate'],
                        'total_sessions': attendance_stats['total_career'].get('total_sessions', 0)
                    }
                },
                'intervencoes': intervencoes,
                'iniciativas': iniciativas,
                'votacoes': []  # Voting data would need separate implementation
            })
        
    except Exception as e:
        return log_and_return_error(e, '/api/deputados/<id>/atividades')


@parlamento_bp.route('/deputados/<int:cad_id>/conflitos-interesse', methods=['GET'])
def get_deputado_conflitos_interesse(cad_id):
    """Retorna declarações de conflitos de interesse de um deputado"""
    try:
        with DatabaseSession() as session:
            # Find deputado by cad_id (unique across all legislatures)
            # Get their most recent legislature entry using proper ordering
            deputado = get_most_recent_deputy(session, cad_id)
            
            if not deputado:
                return jsonify({'error': 'Deputado não encontrado'}), 404
            
            # Get all deputado records with this cad_id (may be multiple across legislatures)
            all_deputados = session.query(Deputado).filter(
                Deputado.id_cadastro == cad_id
            ).all()
            
            deputado_ids = [d.id for d in all_deputados]
            
            # Get interest declarations for any of these deputy records
            interesse_records = session.query(RegistoInteressesUnified).filter(
                RegistoInteressesUnified.deputado_id.in_(deputado_ids)
            ).all()
            
            # Process the records to match frontend expectations
            conflitos_interesse = None
            if interesse_records:
                # Take the most recent record (or first one if only one exists)
                record = interesse_records[0]
                
                # Check if deputy's spouse is also a deputy
                spouse_deputy = None
                if record.spouse_name:
                    # Search for spouse by name in deputados table
                    spouse_dep = session.query(Deputado).filter(
                        func.lower(Deputado.nome_completo).contains(func.lower(record.spouse_name.strip()))
                    ).first()
                    
                    if spouse_dep:
                        # Get spouse's party info
                        spouse_mandato = session.query(DeputadoMandatoLegislativo).filter_by(
                            deputado_id=spouse_dep.id
                        ).order_by(DeputadoMandatoLegislativo.id.desc()).first()
                        
                        spouse_deputy = {
                            'cad_id': spouse_dep.id_cadastro,
                            'id': spouse_dep.id,
                            'partido_sigla': spouse_mandato.par_sigla if spouse_mandato else None
                        }
                
                # Determine if there's conflict potential
                has_conflict_potential = bool(
                    record.spouse_name or  # Has spouse
                    (record.exclusivity and record.exclusivity.lower() == 'n') or  # Not exclusive
                    record.professional_activity  # Has other professional activities
                )
                
                conflitos_interesse = {
                    'has_conflict_potential': has_conflict_potential,
                    'exclusivity_description': 'Exclusivo' if record.exclusivity == 'S' else 'Não exclusivo' if record.exclusivity == 'N' else None,
                    'full_name': record.full_name,
                    'dgf_number': record.dgf_number,
                    'marital_status': record.marital_status_desc,
                    'matrimonial_regime': record.matrimonial_regime,
                    'spouse_name': record.spouse_name,
                    'spouse_deputy': spouse_deputy,
                    'professional_activity': record.professional_activity
                }
            
            # Return the data in the format the frontend expects
            if conflitos_interesse:
                # Return the conflict data directly with some metadata
                result = conflitos_interesse.copy()
                result['deputado_id'] = cad_id
                result['total_declaracoes'] = len(interesse_records)
                return jsonify(result)
            else:
                # No conflict data found
                return jsonify({
                    'deputado_id': cad_id,
                    'has_conflict_potential': False,
                    'total_declaracoes': 0,
                    'message': 'Nenhuma declaração de interesses encontrada'
                })
        
    except Exception as e:
        import traceback
        return log_and_return_error(e, '/api/deputados/<id>/conflitos-interesse', 500)


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
