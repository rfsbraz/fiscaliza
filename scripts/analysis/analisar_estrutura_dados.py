#!/usr/bin/env python3
"""
Script para analisar a estrutura dos dados XML do Parlamento Português
"""

import xml.etree.ElementTree as ET
import json
from collections import defaultdict, Counter
import os

def analisar_xml(ficheiro_xml, nome_categoria):
    """Analisa um ficheiro XML e extrai informações sobre a sua estrutura"""
    print(f"\n=== Análise de {nome_categoria} ===")
    
    if not os.path.exists(ficheiro_xml):
        print(f"Ficheiro {ficheiro_xml} não encontrado")
        return {}
    
    try:
        tree = ET.parse(ficheiro_xml)
        root = tree.getroot()
        
        print(f"Root element: {root.tag}")
        print(f"Namespace: {root.attrib}")
        
        # Contar elementos
        elementos = defaultdict(int)
        atributos = defaultdict(set)
        estrutura = {}
        
        def analisar_elemento(elem, caminho=""):
            novo_caminho = f"{caminho}/{elem.tag}" if caminho else elem.tag
            elementos[novo_caminho] += 1
            
            # Guardar atributos
            for attr, valor in elem.attrib.items():
                atributos[novo_caminho].add(attr)
            
            # Analisar filhos
            for child in elem:
                analisar_elemento(child, novo_caminho)
        
        analisar_elemento(root)
        
        print(f"\nElementos encontrados:")
        for elem, count in sorted(elementos.items()):
            print(f"  {elem}: {count} ocorrências")
            if elem in atributos and atributos[elem]:
                print(f"    Atributos: {', '.join(atributos[elem])}")
        
        # Analisar primeiro elemento de dados para ver estrutura detalhada
        primeiro_elemento = None
        for child in root:
            if child.tag != root.tag:
                primeiro_elemento = child
                break
        
        if primeiro_elemento is not None:
            print(f"\nEstrutura detalhada do primeiro elemento ({primeiro_elemento.tag}):")
            for child in primeiro_elemento:
                valor = child.text if child.text else "None"
                if len(valor) > 100:
                    valor = valor[:100] + "..."
                print(f"  {child.tag}: {valor}")
        
        return {
            'root_tag': root.tag,
            'elementos': dict(elementos),
            'atributos': {k: list(v) for k, v in atributos.items()},
            'total_registos': len(list(root))
        }
        
    except Exception as e:
        print(f"Erro ao analisar {ficheiro_xml}: {e}")
        return {}

def main():
    """Função principal"""
    ficheiros = [
        ("/home/ubuntu/InformacaoBaseXVII.xml", "Informação Base"),
        ("/home/ubuntu/AgendaParlamentar.xml", "Agenda Parlamentar"),
        ("/home/ubuntu/IniciativasXVII.xml", "Iniciativas")
    ]
    
    resultados = {}
    
    for ficheiro, categoria in ficheiros:
        resultado = analisar_xml(ficheiro, categoria)
        if resultado:
            resultados[categoria] = resultado
    
    # Guardar resultados em JSON
    with open('/home/ubuntu/analise_estrutura_dados.json', 'w', encoding='utf-8') as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    
    print(f"\n=== Resumo da Análise ===")
    for categoria, dados in resultados.items():
        print(f"\n{categoria}:")
        print(f"  Root element: {dados.get('root_tag', 'N/A')}")
        print(f"  Total de registos: {dados.get('total_registos', 0)}")
        print(f"  Elementos únicos: {len(dados.get('elementos', {}))}")

if __name__ == "__main__":
    main()

