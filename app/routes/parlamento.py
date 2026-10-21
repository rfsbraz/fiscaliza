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
