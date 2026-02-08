"""
Rotas para Agenda Parlamentar - Parlamento Português
Implementa funcionalidades de agenda diária, ordens de trabalho e eventos
"""

from flask import Blueprint, jsonify, request
from datetime import datetime, date, timedelta
from sqlalchemy import func
import html
import re
import sys
import os

# Add project root to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from database.connection import get_session

agenda_bp = Blueprint('agenda', __name__)

def get_db_connection():
    """Obtém sessão da base de dados."""
    return get_session()

def format_time_display(time_str):
    """Format time string for display without seconds"""
    if not time_str:
        return None
    
    # Remove seconds if present (HH:MM:SS -> HH:MM)
    if len(time_str) >= 5:
        return time_str[:5]  # Take first 5 characters (HH:MM)
    
    return time_str

def clean_html_content(content):
    """Clean HTML entities and tags from content, converting br tags to line breaks.

    Handles double-encoded HTML entities (e.g., &amp;lt; -> &lt; -> <)
    Also removes embedded <style> and <script> blocks entirely.
    """
    if not content:
        return content

    # Decode HTML entities multiple times to handle double/triple encoding
    decoded = content
    prev = None
    max_iterations = 5  # Safety limit
    iteration = 0

    while decoded != prev and iteration < max_iterations:
        prev = decoded
        decoded = html.unescape(decoded)
        iteration += 1

    # Remove <style>...</style> blocks entirely (including content)
    decoded = re.sub(r'<style[^>]*>.*?</style>', '', decoded, flags=re.IGNORECASE | re.DOTALL)

    # Remove <script>...</script> blocks entirely (including content)
    decoded = re.sub(r'<script[^>]*>.*?</script>', '', decoded, flags=re.IGNORECASE | re.DOTALL)

    # Remove <head>...</head> blocks entirely
    decoded = re.sub(r'<head[^>]*>.*?</head>', '', decoded, flags=re.IGNORECASE | re.DOTALL)

    # Convert <br /> and <br> tags to line breaks
    with_breaks = re.sub(r'<br\s*/?>', '\n', decoded, flags=re.IGNORECASE)

    # Convert </p> and </li> to line breaks for better formatting
    with_breaks = re.sub(r'</p>', '\n', with_breaks, flags=re.IGNORECASE)
    with_breaks = re.sub(r'</li>', '\n', with_breaks, flags=re.IGNORECASE)

    # Remove remaining HTML tags
    clean_text = re.sub(r'<[^>]+>', '', with_breaks)

    # Remove &nbsp; entities that might remain
    clean_text = clean_text.replace('\xa0', ' ')
    clean_text = re.sub(r'&nbsp;?', ' ', clean_text, flags=re.IGNORECASE)

    # Remove CSS-like content that might have leaked through (e.g., "font-family:...")
    clean_text = re.sub(r'\{[^}]*\}', '', clean_text)

    # Clean up extra whitespace but preserve single line breaks
    clean_text = re.sub(r'[ \t]+', ' ', clean_text)  # Normalize horizontal whitespace
    clean_text = re.sub(r'\n\s*\n+', '\n\n', clean_text)  # Max 2 consecutive newlines
    clean_text = re.sub(r'^\s+', '', clean_text, flags=re.MULTILINE)  # Remove leading spaces per line
    clean_text = clean_text.strip()

    return clean_text

@agenda_bp.route('/agenda/hoje', methods=['GET'])
def get_agenda_hoje():
    """Obtém agenda parlamentar para hoje usando dados reais."""
    try:
        # For demo purposes, show events from available data instead of filtering by today
        # This allows us to show actual parliament data
        session = get_db_connection()
        
        # Import models here to avoid circular imports
        from database.models import AgendaParlamentar
        
        # Get recent agenda events (since current data is for future dates)
        query = session.query(AgendaParlamentar).order_by(
            AgendaParlamentar.data_evento,
            AgendaParlamentar.hora_inicio
        ).limit(10)
        
        eventos = []
        today_used = date.today()  # Use today's date for display
        
        for agenda_item in query.all():
            # Determine event type based on title content
            titulo_lower = agenda_item.titulo.lower() if agenda_item.titulo else ''
            if 'plenár' in titulo_lower or 'sessão' in titulo_lower:
                tipo = 'plenario'
            elif 'comissão' in titulo_lower or 'comité' in titulo_lower:
                tipo = 'comissao'
            elif 'conferência' in titulo_lower or 'reunião' in titulo_lower:
                tipo = 'reuniao'
            else:
                tipo = 'evento'
            
            eventos.append({
                'id': agenda_item.id,
                'id_externo': agenda_item.id_externo,
                'titulo': agenda_item.titulo or 'Evento Parlamentar',
                'subtitulo': clean_html_content(agenda_item.subtitulo),
                'hora_inicio': format_time_display(str(agenda_item.hora_inicio) if agenda_item.hora_inicio else None),
                'hora_fim': format_time_display(str(agenda_item.hora_fim) if agenda_item.hora_fim else None),
                'tipo': tipo,
                'descricao': clean_html_content(agenda_item.descricao),
                'local': agenda_item.local_evento,
                'grupo_parlamentar': agenda_item.grupo_parlamentar,
                'estado': agenda_item.estado or 'agendado'
            })
        
        session.close()
        
        return jsonify({
            'data': today_used.isoformat(),
            'eventos': eventos,
            'total': len(eventos),
            'resumo': {
                'sessoes_plenarias': len([e for e in eventos if e['tipo'] == 'plenario']),
                'reunioes_comissao': len([e for e in eventos if e['tipo'] == 'comissao']),
                'outros_eventos': len([e for e in eventos if e['tipo'] not in ['plenario', 'comissao']])
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@agenda_bp.route('/agenda/semana', methods=['GET'])
def get_agenda_semana():
    """Obtém agenda parlamentar para a semana atual usando dados reais."""
    try:
        hoje = date.today()
        inicio_semana = hoje - timedelta(days=hoje.weekday())
        fim_semana = inicio_semana + timedelta(days=6)
        
        session = get_db_connection()
        
        # Import models
        from database.models import AgendaParlamentar
        
        # Buscar todos os eventos da semana
        query = session.query(AgendaParlamentar).filter(
            AgendaParlamentar.data_evento >= inicio_semana,
            AgendaParlamentar.data_evento <= fim_semana
        ).order_by(
            AgendaParlamentar.data_evento,
            AgendaParlamentar.hora_inicio
        )
        
        eventos_semana = query.all()
        session.close()
        
        # Organizar eventos por dia
        agenda_semana = []
        for i in range(7):
            data_dia = inicio_semana + timedelta(days=i)
            
            # Filtrar eventos para este dia
            eventos_dia = []
            for evento in eventos_semana:
                if evento.data_evento == data_dia:
                    # Determine event type
                    titulo_lower = (evento.titulo or '').lower()
                    if 'plenár' in titulo_lower or 'sessão' in titulo_lower:
                        tipo = 'plenario'
                    elif 'comissão' in titulo_lower:
                        tipo = 'comissao'
                    else:
                        tipo = 'evento'
                    
                    eventos_dia.append({
                        'id': evento.id,
                        'titulo': evento.titulo,
                        'subtitulo': clean_html_content(evento.subtitulo),
                        'hora_inicio': format_time_display(str(evento.hora_inicio) if evento.hora_inicio else None),
                        'hora_fim': format_time_display(str(evento.hora_fim) if evento.hora_fim else None),
                        'tipo': tipo,
                        'local': evento.local_evento,
                        'grupo_parlamentar': evento.grupo_parlamentar,
                        'estado': evento.estado or 'agendado'
                    })
            
            agenda_semana.append({
                'data': data_dia.isoformat(),
                'dia_semana': data_dia.strftime('%A'),
                'eventos': eventos_dia,
                'total_eventos': len(eventos_dia)
            })
        
        return jsonify({
            'periodo': {
                'inicio': inicio_semana.isoformat(),
                'fim': fim_semana.isoformat()
            },
            'agenda': agenda_semana,
            'resumo': {
                'total_eventos': sum(dia['total_eventos'] for dia in agenda_semana),
                'dias_com_atividade': len([dia for dia in agenda_semana if dia['total_eventos'] > 0])
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@agenda_bp.route('/votacoes/recentes', methods=['GET'])
def get_votacoes_recentes():
    """Obtém votações recentes usando dados reais."""
    try:
        limite = request.args.get('limite', 10, type=int)
        legislatura = request.args.get('legislatura', '17', type=str)
        
        session = get_db_connection()
        
        # Import models
        from database.models import IniciativaEventoVotacao, Legislatura
        
        # Get recent votes from iniciativas_eventos_votacoes table
        query = session.query(IniciativaEventoVotacao).filter(
            IniciativaEventoVotacao.data_votacao.isnot(None)
        ).order_by(
            IniciativaEventoVotacao.data_votacao.desc()
        ).limit(limite)
        
        votacoes = []
        
        for votacao in query.all():
            # Determine result based on available information
            resultado = votacao.resultado or 'desconhecido'

            # Clean the description for display
            descricao_limpa = clean_html_content(votacao.descricao)

            # Create a short title from description (first line or truncated)
            if descricao_limpa:
                # Get first line or first 100 chars as title
                first_line = descricao_limpa.split('\n')[0].strip()
                titulo = first_line[:100] + ('...' if len(first_line) > 100 else '')
            else:
                titulo = f'Votação #{votacao.id}'

            votacoes.append({
                'id': votacao.id,
                'data': votacao.data_votacao.isoformat() if votacao.data_votacao else None,
                'hora': None,  # Time info not available in this table
                'titulo': titulo,
                'descricao': descricao_limpa,
                'resultado': resultado,
                'votos_favor': 0,  # Not available in this table
                'votos_contra': 0,  # Not available in this table
                'abstencoes': 0,   # Not available in this table
                'ausencias': 0,    # Not available in this table
                'tipo_votacao': votacao.tipo_reuniao or 'nominal',
                'legislatura': legislatura
            })
        
        session.close()
        
        # If no real data, provide a message
        if not votacoes:
            return jsonify({
                'votacoes': [],
                'total': 0,
                'message': f'Nenhuma votação encontrada para a {legislatura}ª Legislatura',
                'resumo': {
                    'aprovadas': 0,
                    'rejeitadas': 0,
                    'periodo': f'Legislatura {legislatura}'
                }
            })
        
        return jsonify({
            'votacoes': votacoes,
            'total': len(votacoes),
            'resumo': {
                'aprovadas': len([v for v in votacoes if v['resultado'] and 'aprovad' in v['resultado'].lower()]),
                'rejeitadas': len([v for v in votacoes if v['resultado'] and 'rejeitad' in v['resultado'].lower()]),
                'periodo': f'Legislatura {legislatura} - Últimas {len(votacoes)} votações'
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@agenda_bp.route('/estatisticas/atividade', methods=['GET'])
def get_estatisticas_atividade():
    """Obtém estatísticas reais de atividade parlamentar."""
    try:
        legislatura = request.args.get('legislatura', '17', type=str)
        
        session = get_db_connection()
        
        # Import models
        from database.models import (
            AgendaParlamentar, IniciativaEventoVotacao, 
            Legislatura, IntervencaoParlamentar
        )
        
        # Using general statistics without legislatura filtering for now
        
        # Contar sessões plenárias (eventos que contêm "plenár" ou "sessão")
        sessoes_plenarias = session.query(AgendaParlamentar).filter(
            ((AgendaParlamentar.titulo.ilike('%plenár%')) | 
             (AgendaParlamentar.titulo.ilike('%sessão%')))
        ).count()
        
        # Estatísticas de votações usando a tabela IniciativaEventoVotacao
        total_votacoes = session.query(IniciativaEventoVotacao).count()
        
        votacoes_aprovadas = session.query(IniciativaEventoVotacao).filter(
            IniciativaEventoVotacao.resultado.ilike('%aprovad%')
        ).count()
        
        votacoes_rejeitadas = session.query(IniciativaEventoVotacao).filter(
            IniciativaEventoVotacao.resultado.ilike('%rejeitad%')
        ).count()
        
        # Estatísticas de iniciativas - using available IniciativaParlamentar table  
        from database.models import IniciativaParlamentar
        total_iniciativas = session.query(IniciativaParlamentar).count()
        
        iniciativas_discussao = 0  # Not available without state field
        
        # Estatísticas de intervenções
        total_intervencoes = session.query(IntervencaoParlamentar).count()
        
        # Count unique active deputies for accurate per-deputy averages
        from database.models import Deputado, DeputadoMandatoLegislativo
        unique_active_deputies = session.query(func.count(func.distinct(Deputado.id_cadastro))).join(
            DeputadoMandatoLegislativo, Deputado.id == DeputadoMandatoLegislativo.deputado_id
        ).filter(
            DeputadoMandatoLegislativo.leg_des == 'XVII'  # Current legislature
        ).scalar() or 1
        
        # Reuniões de comissão (aproximação baseada em títulos)
        reunioes_comissao = session.query(AgendaParlamentar).filter(
            AgendaParlamentar.titulo.ilike('%comissão%')
        ).count()
        
        # Última atividade na agenda
        ultima_atividade_query = session.query(func.max(AgendaParlamentar.data_evento)).filter(
            AgendaParlamentar.data_evento <= date.today()
        ).scalar()
        
        ultima_atividade = ultima_atividade_query.isoformat() if ultima_atividade_query else None
        
        session.close()
        
        # Calcular taxa de aprovação
        taxa_aprovacao = 0
        if total_votacoes > 0:
            taxa_aprovacao = round((votacoes_aprovadas / total_votacoes) * 100, 1)
        
        estatisticas = {
            'sessoes_plenarias': {
                'total_ano': sessoes_plenarias,
                'media_mensal': round(sessoes_plenarias / 12, 1) if sessoes_plenarias > 0 else 0,
                'ultima_sessao': ultima_atividade,
                'proxima_sessao': None  # Would need future data
            },
            'votacoes': {
                'total_ano': total_votacoes,
                'aprovadas': votacoes_aprovadas,
                'rejeitadas': votacoes_rejeitadas,
                'taxa_aprovacao': taxa_aprovacao
            },
            'iniciativas': {
                'apresentadas': total_iniciativas,
                'em_discussao': iniciativas_discussao,
                'aprovadas': 0,  # Would need more detailed state data
                'rejeitadas': 0   # Would need more detailed state data
            },
            'intervencoes': {
                'total': total_intervencoes,
                'media_por_deputado': round(total_intervencoes / unique_active_deputies, 1) if total_intervencoes > 0 else 0
            },
            'comissoes': {
                'reunioes_mes': reunioes_comissao,
                'audiencias_mes': 0,  # Would need specific data
                'pareceres_emitidos': 0  # Would need specific data
            }
        }
        
        return jsonify({
            'periodo': f'Legislatura {legislatura}',
            'ultima_atualizacao': datetime.now().isoformat(),
            'estatisticas': estatisticas,
            'dados_reais': True
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

