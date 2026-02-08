#!/usr/bin/env python3
"""
Script para analisar todos os schemas XML dos dados abertos do parlamento
e mapear as relações entre as diferentes entidades.
"""

import xml.etree.ElementTree as ET
import os
from collections import defaultdict
import json

def analisar_xml(caminho_arquivo, nome_categoria):
    """Analisa um arquivo XML e extrai sua estrutura."""
    print(f"\n=== Analisando {nome_categoria} ===")
    print(f"Arquivo: {caminho_arquivo}")
    
    if not os.path.exists(caminho_arquivo):
        print(f"❌ Arquivo não encontrado: {caminho_arquivo}")
        return None
    
    try:
        tree = ET.parse(caminho_arquivo)
        root = tree.getroot()
        
        print(f"✅ Root element: {root.tag}")
        print(f"✅ Namespace: {root.tag.split('}')[0] + '}' if '}' in root.tag else 'None'}")
        
        # Contar elementos filhos
        children = list(root)
        print(f"✅ Número de registros: {len(children)}")
        
        if children:
            primeiro_registro = children[0]
            print(f"✅ Tipo de registro: {primeiro_registro.tag}")
            
            # Analisar estrutura do primeiro registro
            campos = {}
            for child in primeiro_registro:
                tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                
                if child.text and child.text.strip():
                    campos[tag_name] = {
                        'tipo': 'texto',
                        'exemplo': child.text.strip()[:100] + ('...' if len(child.text.strip()) > 100 else ''),
                        'tem_filhos': len(list(child)) > 0
                    }
                elif len(list(child)) > 0:
                    # Elemento com filhos
                    sub_campos = []
                    for subchild in child:
                        sub_tag = subchild.tag.split('}')[-1] if '}' in subchild.tag else subchild.tag
                        sub_campos.append(sub_tag)
                    
                    campos[tag_name] = {
                        'tipo': 'objeto',
                        'sub_campos': sub_campos,
                        'tem_filhos': True
                    }
                else:
                    campos[tag_name] = {
                        'tipo': 'vazio',
                        'exemplo': '',
                        'tem_filhos': False
                    }
            
            print(f"\n📋 Campos encontrados ({len(campos)}):")
            for campo, info in campos.items():
                if info['tipo'] == 'objeto':
                    print(f"  • {campo} (objeto): {', '.join(info['sub_campos'])}")
                else:
                    exemplo = info['exemplo'][:50] + ('...' if len(info['exemplo']) > 50 else '')
                    print(f"  • {campo} ({info['tipo']}): {exemplo}")
            
            return {
                'categoria': nome_categoria,
                'arquivo': caminho_arquivo,
                'root_tag': root.tag,
                'num_registros': len(children),
                'tipo_registro': primeiro_registro.tag,
                'campos': campos
            }
    
    except ET.ParseError as e:
        print(f"❌ Erro ao parsear XML: {e}")
        return None
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return None

def identificar_relacoes(schemas):
    """Identifica possíveis relações entre os schemas."""
    print(f"\n🔗 === ANÁLISE DE RELAÇÕES ===")
    
    relacoes = []
    
    # Campos que indicam relações
    campos_relacao = {
        'id', 'idcadastro', 'deputadoid', 'partidoid', 'circuloid', 
        'actividadeid', 'iniciativaid', 'votacaoid', 'legislatura',
        'sessao', 'gp', 'grupo_parlamentar'
    }
    
    for schema in schemas:
        if not schema:
            continue
            
        categoria = schema['categoria']
        campos = schema['campos']
        
        print(f"\n📊 {categoria}:")
        
        # Identificar campos de relação
        campos_encontrados = []
        for campo, info in campos.items():
            campo_lower = campo.lower()
            
            # Verificar se é um campo de relação
            for campo_rel in campos_relacao:
                if campo_rel in campo_lower:
                    campos_encontrados.append(f"{campo} ({info['tipo']})")
                    
                    # Determinar tipo de relação
                    if 'deputado' in campo_lower:
                        relacoes.append({
                            'origem': categoria,
                            'destino': 'Deputados',
                            'campo': campo,
                            'tipo': 'many-to-one'
                        })
                    elif 'partido' in campo_lower or 'gp' in campo_lower:
                        relacoes.append({
                            'origem': categoria,
                            'destino': 'Partidos',
                            'campo': campo,
                            'tipo': 'many-to-one'
                        })
                    elif 'circulo' in campo_lower:
                        relacoes.append({
                            'origem': categoria,
                            'destino': 'Círculos',
                            'campo': campo,
                            'tipo': 'many-to-one'
                        })
                    elif 'atividade' in campo_lower:
                        relacoes.append({
                            'origem': categoria,
                            'destino': 'Atividades',
                            'campo': campo,
                            'tipo': 'many-to-one'
                        })
                    elif 'iniciativa' in campo_lower:
                        relacoes.append({
                            'origem': categoria,
                            'destino': 'Iniciativas',
                            'campo': campo,
                            'tipo': 'many-to-one'
                        })
        
        if campos_encontrados:
            print(f"  🔗 Campos de relação: {', '.join(campos_encontrados)}")
        else:
            print(f"  ❌ Nenhum campo de relação óbvio encontrado")
    
    return relacoes

def main():
    print("🏛️  ANÁLISE COMPLETA DOS SCHEMAS XML DO PARLAMENTO PORTUGUÊS")
    print("=" * 70)
    
    # Arquivos XML para analisar
    arquivos = [
        ('/home/ubuntu/InformacaoBaseXVII.xml', 'Informação Base'),
        ('/home/ubuntu/AgendaParlamentar.xml', 'Agenda Parlamentar'),
        ('/home/ubuntu/IniciativasXVII.xml', 'Iniciativas'),
        ('/home/ubuntu/IntervencoesXVII.xml', 'Intervenções'),
    ]
    
    schemas = []
    
    # Analisar cada arquivo
    for caminho, categoria in arquivos:
        resultado = analisar_xml(caminho, categoria)
        if resultado:
            schemas.append(resultado)
    
    # Identificar relações
    relacoes = identificar_relacoes(schemas)
    
    # Resumo das relações
    print(f"\n📈 === RESUMO DAS RELAÇÕES IDENTIFICADAS ===")
    print(f"Total de relações encontradas: {len(relacoes)}")
    
    relacoes_por_destino = defaultdict(list)
    for rel in relacoes:
        relacoes_por_destino[rel['destino']].append(rel)
    
    for destino, rels in relacoes_por_destino.items():
        print(f"\n🎯 {destino}:")
        for rel in rels:
            print(f"  ← {rel['origem']} (via {rel['campo']})")
    
    # Sugestões de implementação
    print(f"\n💡 === SUGESTÕES DE IMPLEMENTAÇÃO ===")
    
    print("\n1. 🏗️  EXPANSÃO DO ESQUEMA DE BASE DE DADOS:")
    print("   • Tabela 'intervencoes' - Discursos e participações dos deputados")
    print("   • Tabela 'atividades' - Atividades parlamentares gerais")
    print("   • Tabela 'agenda' - Agenda parlamentar diária")
    print("   • Tabela 'votos' - Votos individuais dos deputados")
    print("   • Tabela 'sessoes' - Sessões parlamentares")
    
    print("\n2. 🔗 RELAÇÕES PRINCIPAIS:")
    print("   • deputados → intervencoes (1:N)")
    print("   • deputados → votos (1:N)")
    print("   • iniciativas → votos (1:N)")
    print("   • agenda → atividades (1:N)")
    print("   • atividades → intervencoes (1:N)")
    
    print("\n3. 🎯 FUNCIONALIDADES PRIORITÁRIAS:")
    print("   • Navegação: Partido → Deputados → Deputado → Atividades")
    print("   • Agenda diária com ordens de trabalho")
    print("   • Histórico de votações por deputado/partido")
    print("   • Análise de participação e assiduidade")
    
    # Salvar resultados
    resultado_final = {
        'schemas': schemas,
        'relacoes': relacoes,
        'timestamp': '2025-07-25'
    }
    
    with open('/home/ubuntu/analise_schemas_completa.json', 'w', encoding='utf-8') as f:
        json.dump(resultado_final, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Resultados salvos em: /home/ubuntu/analise_schemas_completa.json")
    print("\n✅ Análise concluída!")

if __name__ == "__main__":
    main()

