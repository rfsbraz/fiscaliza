"""
Rotas para Navegação Relacional - Parlamento Português
Implementa navegação hierárquica: Partido → Deputados → Deputado → Atividades
"""

from flask import Blueprint, jsonify, request
from ..models.parlamento import db, Deputado, Partido, CirculoEleitoral, Mandato
import sqlite3
import os

navegacao_bp = Blueprint('navegacao', __name__)

def get_db_connection():
    """Obtém conexão com a base de dados."""
    # Caminho relativo ao diretório raiz do projeto
    db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'parlamento.db')
    db_path = os.path.abspath(db_path)
    print(f"Tentando conectar à BD em: {db_path}")
    print(f"BD existe? {os.path.exists(db_path)}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@navegacao_bp.route('/partidos/<int:partido_id>/deputados', methods=['GET'])
def get_deputados_por_partido(partido_id):
    """Obtém lista de deputados de um partido específico."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Buscar deputados do partido
        cursor.execute("""
            SELECT 
                d.id,
                d.id_cadastro,
                d.nome,
                d.profissao,
                ce.designacao as circulo,
                m.ativo as mandato_ativo
            FROM deputados d
            JOIN mandatos m ON d.id = m.deputado_id
            JOIN circulos_eleitorais ce ON m.circulo_id = ce.id
            WHERE m.partido_id = ? AND m.ativo = 1
            ORDER BY d.nome
        """, (partido_id,))
        
        deputados = []
        for row in cursor.fetchall():
            deputados.append({
                'id': row['id'],
                'id_cadastro': row['id_cadastro'],
                'nome': row['nome'],
                'profissao': row['profissao'],
                'circulo': row['circulo'],
                'mandato_ativo': bool(row['mandato_ativo'])
            })
        
        # Buscar informação do partido
        cursor.execute("SELECT sigla, nome FROM partidos WHERE id = ?", (partido_id,))
        partido_info = cursor.fetchone()
        
        conn.close()
        
        return jsonify({
            'partido': {
                'id': partido_id,
                'sigla': partido_info['sigla'],
                'nome': partido_info['nome']
            },
            'deputados': deputados,
            'total': len(deputados)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@navegacao_bp.route('/deputados/<int:deputado_id>/detalhes', methods=['GET'])
def get_detalhes_deputado(deputado_id):
    """Obtém detalhes completos de um deputado específico."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Informação básica do deputado
        cursor.execute("""
            SELECT 
                d.id,
                d.id_cadastro,
                d.nome,
                d.profissao,
                p.sigla as partido_sigla,
                p.nome as partido_nome,
                ce.designacao as circulo,
                m.data_inicio as mandato_inicio,
                m.ativo as mandato_ativo
            FROM deputados d
            JOIN mandatos m ON d.id = m.deputado_id
            JOIN partidos p ON m.partido_id = p.id
            JOIN circulos_eleitorais ce ON m.circulo_id = ce.id
            WHERE d.id = ? AND m.ativo = 1
        """, (deputado_id,))
        
        deputado_info = cursor.fetchone()
        if not deputado_info:
            conn.close()
            return jsonify({'error': 'Deputado não encontrado'}), 404
        
        # Estatísticas de atividade (simuladas por agora)
        cursor.execute("""
            SELECT COUNT(*) as total_mandatos
            FROM mandatos 
            WHERE deputado_id = ?
        """, (deputado_id,))
        
        stats = cursor.fetchone()
        
        conn.close()
        
        deputado = {
            'id': deputado_info['id'],
            'id_cadastro': deputado_info['id_cadastro'],
            'nome': deputado_info['nome'],
            'profissao': deputado_info['profissao'],
            'partido': {
                'sigla': deputado_info['partido_sigla'],
                'nome': deputado_info['partido_nome']
            },
            'circulo': deputado_info['circulo'],
            'mandato': {
                'inicio': deputado_info['mandato_inicio'],
                'ativo': bool(deputado_info['mandato_ativo'])
            },
            'estatisticas': {
                'total_mandatos': stats['total_mandatos'],
                'total_intervencoes': 0,  # Será implementado quando tivermos os dados
                'total_iniciativas': 0,
                'taxa_assiduidade': 0.0
            }
        }
        
        return jsonify(deputado)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@navegacao_bp.route('/deputados/<int:deputado_id>/atividades', methods=['GET'])
def get_atividades_deputado(deputado_id):
    """Obtém atividades de um deputado específico."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar se o deputado existe
        cursor.execute("SELECT nome FROM deputados WHERE id = ?", (deputado_id,))
        deputado = cursor.fetchone()
        if not deputado:
            conn.close()
            return jsonify({'error': 'Deputado não encontrado'}), 404
        
        # Por agora, retornar estrutura vazia preparada para dados futuros
        atividades = {
            'deputado': {
                'id': deputado_id,
                'nome': deputado['nome']
            },
            'intervencoes': [],
            'iniciativas': [],
            'votacoes': [],
            'resumo': {
                'total_intervencoes': 0,
                'total_iniciativas': 0,
                'total_votacoes': 0,
                'ultima_atividade': None
            }
        }
        
        conn.close()
        return jsonify(atividades)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@navegacao_bp.route('/circulos/<int:circulo_id>/deputados', methods=['GET'])
def get_deputados_por_circulo(circulo_id):
    """Obtém deputados de um círculo eleitoral específico."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Buscar deputados do círculo
        cursor.execute("""
            SELECT 
                d.id,
                d.id_cadastro,
                d.nome,
                d.profissao,
                p.sigla as partido_sigla,
                p.nome as partido_nome,
                m.ativo as mandato_ativo
            FROM deputados d
            JOIN mandatos m ON d.id = m.deputado_id
            JOIN partidos p ON m.partido_id = p.id
            WHERE m.circulo_id = ? AND m.ativo = 1
            ORDER BY p.sigla, d.nome
        """, (circulo_id,))
        
        deputados = []
        for row in cursor.fetchall():
            deputados.append({
                'id': row['id'],
                'id_cadastro': row['id_cadastro'],
                'nome': row['nome'],
                'profissao': row['profissao'],
                'partido': {
                    'sigla': row['partido_sigla'],
                    'nome': row['partido_nome']
                },
                'mandato_ativo': bool(row['mandato_ativo'])
            })
        
        # Buscar informação do círculo
        cursor.execute("SELECT designacao FROM circulos_eleitorais WHERE id = ?", (circulo_id,))
        circulo_info = cursor.fetchone()
        
        conn.close()
        
        return jsonify({
            'circulo': {
                'id': circulo_id,
                'designacao': circulo_info['designacao']
            },
            'deputados': deputados,
            'total': len(deputados)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@navegacao_bp.route('/navegacao/hierarquia', methods=['GET'])
def get_hierarquia_completa():
    """Obtém hierarquia completa para navegação."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Buscar partidos com contagem de deputados
        cursor.execute("""
            SELECT 
                p.id,
                p.sigla,
                p.nome,
                COUNT(m.deputado_id) as num_deputados
            FROM partidos p
            LEFT JOIN mandatos m ON p.id = m.partido_id AND m.ativo = 1
            GROUP BY p.id, p.sigla, p.nome
            HAVING num_deputados > 0
            ORDER BY num_deputados DESC, p.sigla
        """)
        
        partidos = []
        for row in cursor.fetchall():
            partidos.append({
                'id': row['id'],
                'sigla': row['sigla'],
                'nome': row['nome'],
                'num_deputados': row['num_deputados']
            })
        
        # Buscar círculos com contagem de deputados
        cursor.execute("""
            SELECT 
                ce.id,
                ce.designacao,
                COUNT(m.deputado_id) as num_deputados
            FROM circulos_eleitorais ce
            LEFT JOIN mandatos m ON ce.id = m.circulo_id AND m.ativo = 1
            GROUP BY ce.id, ce.designacao
            HAVING num_deputados > 0
            ORDER BY num_deputados DESC, ce.designacao
        """)
        
        circulos = []
        for row in cursor.fetchall():
            circulos.append({
                'id': row['id'],
                'designacao': row['designacao'],
                'num_deputados': row['num_deputados']
            })
        
        conn.close()
        
        return jsonify({
            'partidos': partidos,
            'circulos': circulos,
            'total_partidos': len(partidos),
            'total_circulos': len(circulos)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@navegacao_bp.route('/pesquisa/deputados', methods=['GET'])
def pesquisar_deputados():
    """Pesquisa deputados por nome ou outros critérios."""
    try:
        query = request.args.get('q', '').strip()
        partido_id = request.args.get('partido_id')
        circulo_id = request.args.get('circulo_id')
        
        if not query and not partido_id and not circulo_id:
            return jsonify({'error': 'Parâmetros de pesquisa necessários'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Construir query dinâmica
        sql = """
            SELECT 
                d.id,
                d.id_cadastro,
                d.nome,
                d.profissao,
                p.sigla as partido_sigla,
                p.nome as partido_nome,
                ce.designacao as circulo,
                m.ativo as mandato_ativo
            FROM deputados d
            JOIN mandatos m ON d.id = m.deputado_id AND m.ativo = 1
            JOIN partidos p ON m.partido_id = p.id
            JOIN circulos_eleitorais ce ON m.circulo_id = ce.id
            WHERE 1=1
        """
        
        params = []
        
        if query:
            sql += " AND (d.nome LIKE ? OR d.profissao LIKE ?)"
            params.extend([f'%{query}%', f'%{query}%'])
        
        if partido_id:
            sql += " AND p.id = ?"
            params.append(partido_id)
        
        if circulo_id:
            sql += " AND ce.id = ?"
            params.append(circulo_id)
        
        sql += " ORDER BY d.nome LIMIT 50"
        
        cursor.execute(sql, params)
        
        deputados = []
        for row in cursor.fetchall():
            deputados.append({
                'id': row['id'],
                'id_cadastro': row['id_cadastro'],
                'nome': row['nome'],
                'profissao': row['profissao'],
                'partido': {
                    'sigla': row['partido_sigla'],
                    'nome': row['partido_nome']
                },
                'circulo': row['circulo'],
                'mandato_ativo': bool(row['mandato_ativo'])
            })
        
        conn.close()
        
        return jsonify({
            'deputados': deputados,
            'total': len(deputados),
            'query': query,
            'filtros': {
                'partido_id': partido_id,
                'circulo_id': circulo_id
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

