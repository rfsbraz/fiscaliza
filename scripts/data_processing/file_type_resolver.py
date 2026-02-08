#!/usr/bin/env python3
"""
File Type Resolver for Parliament Data
=====================================

Resolves file types based on filename, path, and content patterns.
Extracted from unified_importer.py to avoid logging configuration conflicts.
"""

import re
from typing import Optional


class FileTypeResolver:
    """Resolves file types based on filename, path, and content patterns"""

    # File type patterns - ordered by priority
    FILE_TYPE_PATTERNS = {
        "registo_biografico": [
            r"RegistoBiografico.*\.xml",
            r".*[/\\]RegistoBiogr[aá]fico[/\\].*\.xml",
            r".*RegistoBiografico.*\.xml",
        ],
        "registo_interesses": [
            r"RegistoInteresses.*\.xml",
            r".*[/\\]RegistoBiogr[aá]fico[/\\].*RegistoInteresses.*\.xml",
        ],
        "composicao_orgaos": [
            r"OrgaoComposicao.*\.xml",
            r".*[/\\]Composi[cç][aã]o.*[Óó]rg[aã]os[/\\].*\.xml",
            r".*[/\\]Composição de Órgãos[/\\].*\.xml",
        ],
        "atividade_deputados": [
            r"AtividadeDeputado.*\.xml",
            r".*[/\\]Atividade dos Deputados[/\\].*\.xml",
        ],
        "atividades": [r"Atividades.*\.xml", r".*[/\\]Atividades[/\\].*\.xml"],
        "agenda_parlamentar": [
            r"AgendaParlamentar.*\.xml",
            r".*[/\\]Agenda Parlamentar[/\\].*\.xml",
        ],
        "cooperacao": [
            r"Cooperacao.*\.xml",
            r".*[/\\]Coopera[cç][aã]o Parlamentar[/\\].*\.xml",
        ],
        "delegacao_eventual": [
            r"DelegacaoEventual.*\.xml",
            r".*[/\\]Delega[cç][oõ]es Eventuais[/\\].*\.xml",
        ],
        "delegacao_permanente": [
            r"DelegacaoPermanente.*\.xml",
            r".*[/\\]Delega[cç][oõ]es Permanentes[/\\].*\.xml",
        ],
        "iniciativas": [r"Iniciativas.*\.xml", r".*[/\\]Iniciativas[/\\].*\.xml"],
        "intervencoes": [
            r"Intervencoes.*\.xml",
            r".*[/\\]Interven[cç][oõ]es[/\\].*\.xml",
        ],
        "peticoes": [r"Peticoes.*\.xml", r".*[/\\]Peti[cç][oõ]es[/\\].*\.xml"],
        "perguntas_requerimentos": [
            r"PerguntasRequerimentos.*\.xml",
            r".*[/\\]Perguntas e Requerimentos[/\\].*\.xml",
        ],
        "diplomas_aprovados": [
            r"Diplomas.*\.xml",
            r".*[/\\]Diplomas Aprovados[/\\].*\.xml",
            r".*_Diplomas.*\.xml",
            r".*Diplomas.*\.xml\.xml",
        ],
        "orcamento_estado": [
            r"OE20\d{2}.*\.xml",  # OE followed by year (OE2016, OE2017, etc.)
            r"OEPropostasAlteracao.*\.xml",
            r".*[/\\]O_E[/\\].*\.xml",  # Files in O_E directory
            r".*[/\\]Orçamento do Estado[/\\].*\.xml",
            r".*OE20\d{2}.*\.xml\.xml",
            r".*OEPropostasAlteracao.*\.xml\.xml",
        ],
        "informacao_base": [
            r"InformacaoBase.*\.xml",
            r".*[/\\]Informação base[/\\].*\.xml",
            r".*[/\\]Informao base[/\\].*\.xml",
            r".*InformacaoBase.*\.xml\.xml",
        ],
        "reunioes_visitas": [
            r"Reunioes.*\.xml",
            r"ReuniaoNacional.*\.xml",
            r".*[/\\]Reunioes_Visitas[/\\].*\.xml",
            r".*[/\\]Reuniões.*Visitas[/\\].*\.xml",
            r".*[/\\]Reunies.*Visitas[/\\].*\.xml",
            r".*Reunioe.*\.xml",
            r".*ReunioesVisitas.*\.xml",
        ],
        "grupos_amizade": [
            r"GrupoDeAmizade.*\.xml",
            r".*[/\\]Grupos Parlamentares de Amizade[/\\].*\.xml",
            r".*GrupoDeAmizade.*\.xml\.xml",
        ],
        "diario_assembleia": [
            r"Número_.*\.xml",
            r".*[/\\]Dirioda Assembleia da República[/\\].*\.xml",
            r".*[/\\]Dirioda Assembleia da Repblica[/\\].*\.xml",
            r".*_Nmero_.*\.xml",
            r".*Nmero_.*\.xml\.xml",
        ],
    }

    @classmethod
    def resolve_file_type(cls, file_path: str) -> Optional[str]:
        """Resolve file type based on path patterns"""
        normalized_path = file_path.replace("\\\\", "/").replace("\\", "/")

        for file_type, patterns in cls.FILE_TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, normalized_path, re.IGNORECASE):
                    return file_type

        # Check if it's JSON equivalent
        if file_path.endswith("_json.txt"):
            xml_equivalent = file_path.replace("_json.txt", ".xml")
            xml_type = cls.resolve_file_type(xml_equivalent)
            if xml_type:
                return f"{xml_type}_json"

        return None

    @classmethod
    def extract_legislatura(cls, file_path: str) -> Optional[str]:
        """Extract legislatura from file path"""
        
        # Try different patterns
        patterns = [
            r"Legislatura_([A-Z]+|\\d+)",
            r"[/\\\\]([XVII]+)[/\\\\]",
            r"([XVII]+)\\.xml",
            r"(\\d+)\\.xml",
        ]

        for pattern in patterns:
            match = re.search(pattern, file_path, re.IGNORECASE)
            if match:
                leg = match.group(1).upper()
                
                # Convert roman numerals to numbers if needed
                roman_map = {
                    "XVII": "17",
                    "XVI": "16",
                    "XV": "15",
                    "XIV": "14",
                    "XIII": "13",
                    "XII": "12",
                    "XI": "11",
                    "X": "10",
                    "IX": "9",
                    "VIII": "8",
                    "VII": "7",
                    "VI": "6",
                    "V": "5",
                    "IV": "4",
                    "III": "3",
                    "II": "2",
                    "I": "1",
                    "CONSTITUINTE": "0",
                }
                result = roman_map.get(leg, leg)
                return result

        return None