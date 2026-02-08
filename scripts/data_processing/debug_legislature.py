#!/usr/bin/env python3
"""
Debug script to test legislature extraction from URLs
"""

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from scripts.data_processing.discovery_service import ParliamentURLExtractor

# Test URLs from the previous discovery run
test_urls = [
    "https://www.parlamento.pt/sites/com/ListaPublicacoes/_vti_bin/Lists.asmx/GetListItems?listname=%7B4A86BE0C%2D0AAF%2D4AF4%2DB067%2D5B3A5F4CF48F%7D&amp;rowlimit=2000&amp;sortField=Created&amp;ascending=false&amp;viewfields=&amp;query=%3CQuery%3E%3CWhere%3E%3CContains%3E%3CFieldRef%20Name%3D%22Title%22%2F%3E%3CValue%20Type%3D%22Text%22%3EAgendaParlamentar%3C%2FValue%3E%3C%2FContains%3E%3C%2FWhere%3E%3C%2FQuery%3E&amp;viewname=%7BD5DD6844%2DA3C5%2D4F6D%2D9F24%2D4C56C4143F5A%7D",
    "https://www.parlamento.pt/DeputadoGP/Paginas/DABoletimInformativo.aspx?BID=110&amp;P=117",
    "https://app.parlamento.pt/webutils/docs/doc.xml?path=6148523063484d364c793968636d356c6443397a6158526c63793959566d68535a57356c59584e6c5a5763765247396a6457316c626e527663304e76626e526c6548527663474e76626d566a644349765156426c6257567564485650636e646c4c6d786a5a6c4a766233526c59577a4d656b3876554770535547355a6447396958326c6159586859556d463161573575616a42444f486c6a6157786a4a54426d4c7a4e48556a4244566c46584e546f304c6a4e49513031444b6c525a54564256617767306146703163526c3762546b334f4756755853633d&amp;fich=AgendaParlamentar.xml&amp;Inline=true",
]

test_filenames = [
    "AgendaParlamentar.xml", 
    "AtividadesXVII.xml",
    "InformacaoBaseXVII.xml"
]

print("Testing legislature extraction...")
print("=" * 50)

for url in test_urls:
    print(f"URL: {url}")
    for filename in test_filenames:
        print(f"  Filename: {filename}")
        metadata = ParliamentURLExtractor.extract_metadata(url, filename)
        print(f"    Legislatura: {repr(metadata['legislatura'])}")
        print(f"    Category: {repr(metadata['category'])}")
        print(f"    File Type: {repr(metadata['file_type'])}")
        print()

# Test the legislature extraction directly
print("Direct legislature extraction test:")
print("=" * 50)

test_cases = [
    "https://something/XVII_Legislatura/file.xml",
    "https://something/XVII Legislatura/file.xml", 
    "https://something/Legislatura_XVII/file.xml",
    "https://something/XVII/file.xml",
    "https://something/Constituinte/file.xml",
    "AtividadesXVII.xml",
    "InformacaoBaseXVI.xml",
    "RegistoBiograficoXV.xml"
]

for test_case in test_cases:
    legislatura = ParliamentURLExtractor._extract_legislatura(test_case)
    print(f"'{test_case}' -> Legislatura: {repr(legislatura)}")