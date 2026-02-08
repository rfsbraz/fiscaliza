"""
Rotas para Agenda Parlamentar - Parlamento Português
Implementa funcionalidades de agenda diária, ordens de trabalho e eventos
"""

from flask import Blueprint, jsonify, request
from datetime import datetime, date, timedelta
import sqlite3
import os

agenda_bp = Blueprint('agenda', __name__)

def get_db_connection():
    """Obtém conexão com a base de dados."""
    db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'parlamento.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@agenda_bp.route('/agenda/hoje', methods=['GET'])
def get_agenda_hoje():
    """Obtém agenda parlamentar para hoje."""
    try:
        hoje = date.today()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Buscar eventos da agenda para hoje (simulado por agora)
        eventos = [
            {
                'id': 1,
                'titulo': 'Sessão Plenária',
                'hora_inicio': '14:30',
                'hora_fim': '18:00',
                'tipo': 'plenario',
                'descricao': 'Ordem do dia com votações de iniciativas legislativas',
                'local': 'Hemiciclo',
                'estado': 'agendado'
            },
            {
                'id': 2,
                'titulo': 'Comissão de Assuntos Constitucionais',
                'hora_inicio': '10:00',
                'hora_fim': '12:00',
                'tipo': 'comissao',
                'descricao': 'Audição de especialistas sobre reforma constitucional',
                'local': 'Sala 1.1',
                'estado': 'em_curso'
            }
        ]
        
        conn.close()
        
        return jsonify({
            'data': hoje.isoformat(),
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
    """Obtém agenda parlamentar para a semana atual."""
    try:
        hoje = date.today()
        inicio_semana = hoje - timedelta(days=hoje.weekday())
        fim_semana = inicio_semana + timedelta(days=6)
        
        # Simular agenda da semana
        agenda_semana = []
        for i in range(7):
            data_dia = inicio_semana + timedelta(days=i)
            eventos_dia = []
            
            # Simular alguns eventos
            if data_dia.weekday() < 5:  # Segunda a sexta
                if data_dia.weekday() in [1, 3]:  # Terça e quinta
                    eventos_dia.append({
                        'id': f'plen_{i}',
                        'titulo': 'Sessão Plenária',
                        'hora_inicio': '14:30',
                        'tipo': 'plenario',
                        'estado': 'agendado' if data_dia >= hoje else 'concluido'
                    })
                
                eventos_dia.append({
                    'id': f'com_{i}',
                    'titulo': f'Reunião de Comissão',
                    'hora_inicio': '10:00',
                    'tipo': 'comissao',
                    'estado': 'agendado' if data_dia >= hoje else 'concluido'
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

@agenda_bp.route('/agenda/mes', methods=['GET'])
def get_agenda_mes():
    """Obtém agenda parlamentar para o mês atual."""
    try:
        hoje = date.today()
        ano = request.args.get('ano', hoje.year, type=int)
        mes = request.args.get('mes', hoje.month, type=int)
        
        # Primeiro dia do mês
        primeiro_dia = date(ano, mes, 1)
        
        # Último dia do mês
        if mes == 12:
            ultimo_dia = date(ano + 1, 1, 1) - timedelta(days=1)
        else:
            ultimo_dia = date(ano, mes + 1, 1) - timedelta(days=1)
        
        # Simular eventos do mês
        eventos_mes = []
        data_atual = primeiro_dia
        
        while data_atual <= ultimo_dia:
            if data_atual.weekday() < 5:  # Segunda a sexta
                num_eventos = 0
                
                # Simular padrão de eventos
                if data_atual.weekday() in [1, 3]:  # Terça e quinta - sessões plenárias
                    num_eventos += 1
                
                if data_atual.day % 3 == 0:  # A cada 3 dias - comissões
                    num_eventos += 1
                
                if num_eventos > 0:
                    eventos_mes.append({
                        'data': data_atual.isoformat(),
                        'dia': data_atual.day,
                        'dia_semana': data_atual.strftime('%A'),
                        'num_eventos': num_eventos,
                        'tem_plenario': data_atual.weekday() in [1, 3],
                        'tem_comissoes': data_atual.day % 3 == 0
                    })
            
            data_atual += timedelta(days=1)
        
        return jsonify({
            'periodo': {
                'ano': ano,
                'mes': mes,
                'nome_mes': primeiro_dia.strftime('%B'),
                'primeiro_dia': primeiro_dia.isoformat(),
                'ultimo_dia': ultimo_dia.isoformat()
            },
            'eventos': eventos_mes,
            'resumo': {
                'total_dias_atividade': len(eventos_mes),
                'total_eventos': sum(e['num_eventos'] for e in eventos_mes),
                'sessoes_plenarias': len([e for e in eventos_mes if e['tem_plenario']]),
                'reunioes_comissoes': len([e for e in eventos_mes if e['tem_comissoes']])
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@agenda_bp.route('/agenda/<data_evento>', methods=['GET'])
def get_agenda_data(data_evento):
    """Obtém agenda parlamentar para uma data específica."""
    try:
        # Validar formato da data
        try:
            data_obj = datetime.strptime(data_evento, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Formato de data inválido. Use YYYY-MM-DD'}), 400
        
        # Simular eventos para a data específica
        eventos = []
        
        # Se for dia útil, simular alguns eventos
        if data_obj.weekday() < 5:
            if data_obj.weekday() in [1, 3]:  # Terça e quinta
                eventos.append({
                    'id': f'plen_{data_evento}',
                    'titulo': 'Sessão Plenária',
                    'hora_inicio': '14:30',
                    'hora_fim': '18:00',
                    'tipo': 'plenario',
                    'descricao': 'Ordem do dia com debate e votação de iniciativas',
                    'local': 'Hemiciclo',
                    'estado': 'agendado',
                    'ordem_trabalhos': [
                        'Projeto de Lei n.º 123/XVII - Alteração ao Código Civil',
                        'Proposta de Lei n.º 45/XVII - Orçamento do Estado',
                        'Requerimento n.º 67/XVII - Audição do Ministro da Justiça'
                    ]
                })
            
            if data_obj.day % 2 == 0:  # Dias pares
                eventos.append({
                    'id': f'com_{data_evento}',
                    'titulo': 'Comissão de Assuntos Constitucionais',
                    'hora_inicio': '10:00',
                    'hora_fim': '12:00',
                    'tipo': 'comissao',
                    'descricao': 'Análise de propostas legislativas',
                    'local': 'Sala 1.1',
                    'estado': 'agendado'
                })
        
        return jsonify({
            'data': data_evento,
            'dia_semana': data_obj.strftime('%A'),
            'eventos': eventos,
            'total': len(eventos),
            'resumo': {
                'tem_atividade': len(eventos) > 0,
                'tipos_eventos': list(set(e['tipo'] for e in eventos))
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@agenda_bp.route('/votacoes/recentes', methods=['GET'])
def get_votacoes_recentes():
    """Obtém votações recentes (simuladas)."""
    try:
        limite = request.args.get('limite', 10, type=int)
        
        # Simular votações recentes
        votacoes = []
        for i in range(limite):
            data_votacao = date.today() - timedelta(days=i)
            votacoes.append({
                'id': f'vot_{i}',
                'data': data_votacao.isoformat(),
                'titulo': f'Projeto de Lei n.º {100 + i}/XVII',
                'descricao': f'Alteração à legislação sobre tema {i + 1}',
                'resultado': 'aprovado' if i % 3 != 0 else 'rejeitado',
                'votos_favor': 130 + (i * 5),
                'votos_contra': 80 - (i * 2),
                'abstencoes': 39 + i,
                'ausencias': 0,
                'tipo_votacao': 'nominal'
            })
        
        return jsonify({
            'votacoes': votacoes,
            'total': len(votacoes),
            'resumo': {
                'aprovadas': len([v for v in votacoes if v['resultado'] == 'aprovado']),
                'rejeitadas': len([v for v in votacoes if v['resultado'] == 'rejeitado']),
                'periodo': f'Últimos {limite} dias'
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@agenda_bp.route('/ordem-trabalhos/<data_evento>', methods=['GET'])
def get_ordem_trabalhos(data_evento):
    """Obtém ordem de trabalhos para uma data específica."""
    try:
        # Validar formato da data
        try:
            data_obj = datetime.strptime(data_evento, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Formato de data inválido. Use YYYY-MM-DD'}), 400
        
        # Simular ordem de trabalhos
        ordem_trabalhos = []
        
        if data_obj.weekday() in [1, 3]:  # Terça e quinta - sessões plenárias
            ordem_trabalhos = [
                {
                    'numero': 1,
                    'tipo': 'projeto_lei',
                    'titulo': 'Projeto de Lei n.º 123/XVII',
                    'descricao': 'Alteração ao Código Civil - regime de bens',
                    'autor': 'Grupo Parlamentar do PSD',
                    'fase': 'votacao_final_global',
                    'tempo_estimado': '30 minutos',
                    'urgente': False
                },
                {
                    'numero': 2,
                    'tipo': 'proposta_lei',
                    'titulo': 'Proposta de Lei n.º 45/XVII',
                    'descricao': 'Orçamento do Estado para 2025',
                    'autor': 'Governo',
                    'fase': 'discussao_generalidade',
                    'tempo_estimado': '120 minutos',
                    'urgente': True
                },
                {
                    'numero': 3,
                    'tipo': 'requerimento',
                    'titulo': 'Requerimento n.º 67/XVII',
                    'descricao': 'Audição do Ministro da Justiça',
                    'autor': 'Grupo Parlamentar do PS',
                    'fase': 'votacao',
                    'tempo_estimado': '15 minutos',
                    'urgente': False
                },
                {
                    'numero': 4,
                    'tipo': 'interpelacao',
                    'titulo': 'Interpelação ao Governo n.º 12/XVII',
                    'descricao': 'Política de habitação',
                    'autor': 'Grupo Parlamentar do Chega',
                    'fase': 'discussao',
                    'tempo_estimado': '45 minutos',
                    'urgente': False
                }
            ]
        
        return jsonify({
            'data': data_evento,
            'ordem_trabalhos': ordem_trabalhos,
            'total_itens': len(ordem_trabalhos),
            'tempo_total_estimado': sum(
                int(item['tempo_estimado'].split()[0]) 
                for item in ordem_trabalhos
            ),
            'itens_urgentes': len([item for item in ordem_trabalhos if item['urgente']]),
            'resumo_tipos': {
                tipo: len([item for item in ordem_trabalhos if item['tipo'] == tipo])
                for tipo in set(item['tipo'] for item in ordem_trabalhos)
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@agenda_bp.route('/estatisticas/atividade', methods=['GET'])
def get_estatisticas_atividade():
    """Obtém estatísticas de atividade parlamentar."""
    try:
        # Simular estatísticas
        estatisticas = {
            'sessoes_plenarias': {
                'total_ano': 45,
                'media_mensal': 3.8,
                'ultima_sessao': '2025-07-23',
                'proxima_sessao': '2025-07-25'
            },
            'votacoes': {
                'total_ano': 234,
                'aprovadas': 156,
                'rejeitadas': 78,
                'taxa_aprovacao': 66.7
            },
            'iniciativas': {
                'apresentadas': 456,
                'em_discussao': 123,
                'aprovadas': 89,
                'rejeitadas': 67
            },
            'comissoes': {
                'reunioes_mes': 28,
                'audiencias_mes': 12,
                'pareceres_emitidos': 45
            },
            'assiduidade': {
                'media_presencas': 89.2,
                'deputados_100_pct': 23,
                'deputados_acima_90_pct': 187
            }
        }
        
        return jsonify({
            'periodo': 'Ano 2025',
            'ultima_atualizacao': datetime.now().isoformat(),
            'estatisticas': estatisticas
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

