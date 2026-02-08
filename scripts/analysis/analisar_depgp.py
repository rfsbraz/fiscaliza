#!/usr/bin/env python3
import xml.etree.ElementTree as ET

def analisar_depgp():
    """Analisa especificamente a estrutura do elemento DepGP"""
    try:
        tree = ET.parse('/home/ubuntu/InformacaoBaseXVII.xml')
        root = tree.getroot()
        
        print("=== Análise do elemento DepGP ===\n")
        
        # Encontrar todos os deputados
        deputados = root.findall('.//DadosDeputadoOrgaoPlenario')
        print(f"Total de deputados encontrados: {len(deputados)}")
        
        # Analisar os primeiros 5 deputados
        for i, deputado in enumerate(deputados[:5]):
            nome = deputado.findtext('DepNomeParlamentar', 'N/A')
            print(f"\n--- Deputado {i+1}: {nome} ---")
            
            # Analisar DepGP
            depgp = deputado.find('DepGP')
            if depgp is not None:
                print(f"DepGP encontrado:")
                print(f"  Tag: {depgp.tag}")
                print(f"  Atributos: {depgp.attrib}")
                print(f"  Texto: {depgp.text}")
                
                # Listar todos os filhos
                for filho in depgp:
                    tag_limpo = filho.tag.split('}')[-1] if '}' in filho.tag else filho.tag
                    print(f"  Filho: {tag_limpo} = {filho.text}")
            else:
                print("DepGP não encontrado")
            
            # Analisar DepSituacao também
            depsit = deputado.find('DepSituacao')
            if depsit is not None:
                print(f"DepSituacao encontrado:")
                for filho in depsit:
                    tag_limpo = filho.tag.split('}')[-1] if '}' in filho.tag else filho.tag
                    print(f"  Filho: {tag_limpo} = {filho.text}")
        
        # Procurar por padrões de sigla
        print(f"\n=== Procura por elementos com 'sigla' ===")
        for elem in root.iter():
            tag_limpo = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if 'sigla' in tag_limpo.lower() and elem.text:
                print(f"  {tag_limpo}: {elem.text}")
        
    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analisar_depgp()

