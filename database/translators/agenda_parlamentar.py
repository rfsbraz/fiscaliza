"""
Parliamentary Agenda Translators
================================

Translators for parliamentary agenda-related coded fields.
Based on official Parliament documentation (June 2023):
"AgendaParlamentar.xml/.json" structure from XV_Legislatura documentation.
"""

from enum import Enum
from typing import Optional
from dataclasses import dataclass


class SectionType(Enum):
    """
    Section type codes from Portuguese Parliament documentation
    
    Used in models:
    - AgendaParlamentar (secao_id field)
    
    Documentation Reference:
    - SectionId: "Identificador único da secção da reunião/evento"
    - Based on official XV_Legislatura reference table (page 2)
    
    Note: Uses numeric identifiers as documented in official reference table.
    """
    # Numeric codes from official Section table (XV_Legislatura doc, page 2)
    S_1 = "Comissão Permanente"
    S_2 = "Agenda do Presidente da Assembleia da República"
    S_3 = "Subcomissão"
    S_4 = "Plenário"
    S_5 = "Grupo de Trabalho AR"
    S_6 = "Conferência dos Presidentes das Comissões Parlamentares"
    S_7 = "Comissões Parlamentares"
    S_8 = "Conferência de Líderes"
    S_9 = "Conselho de Administração"
    S_10 = "Grupo de Trabalho"
    S_11 = "Comissão Permanente - Agendamentos Futuros"
    S_12 = "Comissão Permanente - Agenda do Dia"
    S_13 = "Eventos"
    S_14 = "Plenário - Agendamentos Futuros"
    S_15 = "Plenário - Agenda do Dia"
    S_16 = "Agenda da Vice-Presidência da Assembleia da República"
    S_17 = "Outras Informações"
    S_18 = "Plenário - Agenda do Dia (carregamento manual)"
    S_19 = "Relações Internacionais"
    S_20 = "Visitas ao Palácio de S. Bento"
    S_21 = "Assistências ao Plenário"
    S_22 = "Grupos Parlamentares / Partidos / Ninsc"
    S_23 = "Resumo da Calendarização"
    S_24 = "Grelhas de Tempos"


class ThemeType(Enum):
    """
    Theme type codes from Portuguese Parliament documentation
    
    Used in models:
    - AgendaParlamentar (tema_id field)
    
    Documentation Reference:
    - ThemeId: "Identificador único do tema da reunião/evento"
    - Based on official XV_Legislatura reference table (pages 2-3)
    
    Note: Uses numeric identifiers as documented in official reference table.
    """
    # Numeric codes from official Theme table (XV_Legislatura doc, pages 2-3)
    T_1 = "Conferência dos Presidentes das Comissões Parlamentares"
    T_2 = "Comissões Parlamentares"
    T_3 = "Comissão Permanente"
    T_4 = "Conselho de Administração"
    T_5 = "Conferência de Líderes"
    T_6 = "Grupo de Trabalho AR"
    T_7 = "Plenário"
    T_8 = "Agenda do Presidente da Assembleia da República"
    T_9 = "CALENDARIZAÇÃO DOS TRABALHOS PARLAMENTARES"
    T_10 = "PRESIDÊNCIA DA ASSEMBLEIA DA REPÚBLICA"
    T_11 = "ACTIVIDADES PARLAMENTARES EXTERNAS"
    T_12 = "OUTRAS ACTIVIDADES"
    T_13 = "Resumo da Calendarização"
    T_14 = "Grupos Parlamentares / Partidos / Ninsc"
    T_15 = "Visitas ao Palácio de S. Bento"
    T_16 = "Assistências ao Plenário"


@dataclass
class AgendaTranslation:
    """Container for agenda field translation results"""
    code: str
    description: str
    category: str = "agenda"
    is_valid: bool = True
    
    def __str__(self) -> str:
        return self.description


class AgendaTranslator:
    """
    Translator for parliamentary agenda-related coded fields
    
    Usage:
        translator = AgendaTranslator()
        
        # Section types
        section_desc = translator.section_type("4")  # "Plenário"
        
        # Theme types
        theme_desc = translator.theme_type("7")  # "Plenário"
    """
    
    def section_type(self, code: str) -> Optional[str]:
        """Get readable description for section type code"""
        translation = self.get_section_type(code)
        return translation.description if translation else None
    
    def get_section_type(self, code: str) -> Optional[AgendaTranslation]:
        """
        Get full translation metadata for section type code
        
        Documentation Reference:
        - Maps SectionId codes to their descriptions
        - Used in AgendaParlamentar.secao_id field
        - Based on XV_Legislatura doc Section table (page 2)
        """
        if not code:
            return None
            
        # Handle numeric codes by creating enum key
        try:
            enum_key = f"S_{code}" if code.isdigit() else code.upper()
            enum_value = SectionType[enum_key]
            return AgendaTranslation(
                code=code,
                description=enum_value.value,
                category="section_type",
                is_valid=True
            )
        except KeyError:
            return AgendaTranslation(
                code=code,
                description=f"Unknown section type: {code}",
                category="section_type",
                is_valid=False
            )
    
    def theme_type(self, code: str) -> Optional[str]:
        """Get readable description for theme type code"""
        translation = self.get_theme_type(code)
        return translation.description if translation else None
    
    def get_theme_type(self, code: str) -> Optional[AgendaTranslation]:
        """
        Get full translation metadata for theme type code
        
        Documentation Reference:
        - Maps ThemeId codes to their descriptions
        - Used in AgendaParlamentar.tema_id field
        - Based on XV_Legislatura doc Theme table (pages 2-3)
        """
        if not code:
            return None
            
        # Handle numeric codes by creating enum key
        try:
            enum_key = f"T_{code}" if code.isdigit() else code.upper()
            enum_value = ThemeType[enum_key]
            return AgendaTranslation(
                code=code,
                description=enum_value.value,
                category="theme_type",
                is_valid=True
            )
        except KeyError:
            return AgendaTranslation(
                code=code,
                description=f"Unknown theme type: {code}",
                category="theme_type",
                is_valid=False
            )


# Global instance for convenience
agenda_translator = AgendaTranslator()


def translate_section_type(code: str) -> Optional[str]:
    """Quick translation of section type code"""
    return agenda_translator.section_type(code)


def translate_theme_type(code: str) -> Optional[str]:
    """Quick translation of theme type code"""
    return agenda_translator.theme_type(code)