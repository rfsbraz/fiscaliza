#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import sys

def analisar_estrutura_xml(ficheiro):
    """Analisa a estrutura real do ficheiro XML"""
    try:
        tree = ET.parse(ficheiro)
        root = tree.getroot()
        
        print(f"=== Análise do ficheiro: {ficheiro} ===")
        print(f"Root element: {root.tag}")
        print(f"Root attributes: {root.attrib}")
        print(f"Root namespace: {root.tag.split('}')[0] + '}' if '}' in root.tag else 'None'}")
        print()
        
        # Função recursiva para explorar a árvore
        def explorar_elemento(elem, nivel=0, max_nivel=3):
            indent = "  " * nivel
            
            # Mostrar tag e atributos
            tag_limpo = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            print(f"{indent}{tag_limpo}")
            
            if elem.attrib:
                for attr, valor in elem.attrib.items():
                    print(f"{indent}  @{attr}: {valor}")
            
            if elem.text and elem.text.strip():
                texto = elem.text.strip()[:100] + "..." if len(elem.text.strip()) > 100 else elem.text.strip()
                print(f"{indent}  TEXT: {texto}")
            
            # Explorar filhos se não excedeu o nível máximo
            if nivel < max_nivel:
                filhos_unicos = {}
                for filho in elem:
                    tag_filho = filho.tag.split('}')[-1] if '}' in filho.tag else filho.tag
                    if tag_filho not in filhos_unicos:
                        filhos_unicos[tag_filho] = filho
                
                for tag_filho, filho in filhos_unicos.items():
                    explorar_elemento(filho, nivel + 1, max_nivel)
            elif len(list(elem)) > 0:
                print(f"{indent}  ... ({len(list(elem))} filhos)")
        
        explorar_elemento(root)
        
        # Procurar por padrões específicos
        print("\n=== Procura por padrões específicos ===")
        
        # Procurar deputados
        padroes_deputado = [
            './/Deputado', './/deputado', './/*[contains(local-name(), "Deputado")]',
            './/*[contains(local-name(), "deputado")]', './/*[contains(local-name(), "Pessoa")]'
        ]
        
        for padrao in padroes_deputado:
            try:
                elementos = root.findall(padrao)
                if elementos:
                    print(f"Encontrados {len(elementos)} elementos com padrão: {padrao}")
                    if len(elementos) > 0:
                        elem = elementos[0]
                        print(f"  Exemplo: {elem.tag}")
                        for filho in elem[:3]:  # Mostrar primeiros 3 filhos
                            tag_limpo = filho.tag.split('}')[-1] if '}' in filho.tag else filho.tag
                            print(f"    {tag_limpo}: {filho.text}")
                        break
            except Exception as e:
                continue
        
        # Procurar partidos/grupos
        padroes_partido = [
            './/Partido', './/partido', './/Grupo', './/grupo',
            './/*[contains(local-name(), "Partido")]', './/*[contains(local-name(), "Grupo")]'
        ]
        
        for padrao in padroes_partido:
            try:
                elementos = root.findall(padrao)
                if elementos:
                    print(f"Encontrados {len(elementos)} elementos com padrão: {padrao}")
                    if len(elementos) > 0:
                        elem = elementos[0]
                        print(f"  Exemplo: {elem.tag}")
                        for filho in elem[:3]:
                            tag_limpo = filho.tag.split('}')[-1] if '}' in filho.tag else filho.tag
                            print(f"    {tag_limpo}: {filho.text}")
                        break
            except Exception as e:
                continue
        
        # Listar todos os elementos únicos no documento
        print("\n=== Todos os elementos únicos (primeiros 20) ===")
        elementos_unicos = set()
        for elem in root.iter():
            tag_limpo = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            elementos_unicos.add(tag_limpo)
        
        for i, tag in enumerate(sorted(elementos_unicos)):
            if i >= 20:
                print("...")
                break
            print(f"  {tag}")
        
        print(f"\nTotal de elementos únicos: {len(elementos_unicos)}")
        
    except Exception as e:
        print(f"Erro ao analisar XML: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        analisar_estrutura_xml(sys.argv[1])
    else:
        print("Uso: python3 analisar_xml_real.py <ficheiro.xml>")

