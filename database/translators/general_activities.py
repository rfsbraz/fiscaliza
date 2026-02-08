"""
General Activities Translators
==============================

Translators for general parliamentary activity-related coded fields.
Based on official Parliament documentation (December 2017):
"AtividadesGerais" structure from VI_Legislatura Atividades documentation.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TipodeAutor(Enum):
    """
    Author type codes from Portuguese Parliament documentation

    Used in models:
    - AtividadeParlamentar (tipo_autor field)
    - Activity authorship classification

    Documentation Reference:
    - TipoAutor: "Campo Tipo na estrutura TipodeAutor"
    - Based on official VI_Legislatura reference table (pages 12-13)

    Note: Single-letter codes as documented in official reference table.
    """

    # Letter codes from official TipodeAutor table (VI_Legislatura doc, pages 12-13)
    A = "Assembleia Legislativa da Região Autónoma dos Açores"
    C = "Comissões"
    D = "Deputados"
    G = "Grupos Parlamentares"
    I = "Pessoa singular"
    M = "Assembleia legislativa da região autónoma da Madeira"
    P = "Mesa da assembleia"
    R = "PAR"
    U = "Assembleia legislativa de Macau"
    V = "Governo"
    Z = "Iniciativa legislativa de cidadãos"


class TipodeReuniao(Enum):
    """
    Meeting type codes from Portuguese Parliament documentation

    Used in models:
    - VotacaoOut (TipoReuniao field)

    Documentation Reference:
    - TipoReuniao: "Descrição do tipo de reunião em TipodeReuniao"
    - Based on official VI_Legislatura reference table (page 13)

    Note: Text-based codes as documented in official reference table.
    """

    # Text codes from official TipodeReuniao table (VI_Legislatura doc, page 13)
    AG = "Audiência com grupos parlamentares"
    AS = "Audiência com o Secretário-geral"
    AU = "Audiência como PAR"
    CO = "Reunião com a comissão"
    CR = "Reunião corrente"
    GA = "Reunião com o grupo de amizade AR"
    IE = "Reunião com individualidades externas"
    PP = "Reunião preparatória"


class TipodeEvento(Enum):
    """
    Event type codes from Portuguese Parliament documentation

    Used in models:
    - EventoParlamentar (tipo_evento field)
    - DadosEventosComissaoOut structure

    Documentation Reference:
    - TipoEvento: "Tipo de evento na estrutura TipodeEvento"
    - Based on official VI_Legislatura reference table (page 16)

    Note: Uses numeric identifiers as documented in official reference table.
    """

    # Numeric codes from official TipodeEvento table (VI_Legislatura doc, page 16)
    E_2 = "Conferência"  # Code 2
    E_3 = "Colóquio"  # Code 3
    E_4 = "Seminário"  # Code 4
    E_5 = "Audição pública"  # Code 5
    E_42 = "Exposições"  # Code 42
    E_61 = "Debate"  # Code 61
    E_81 = "Cerimónia"  # Code 81
    E_101 = "Congresso"  # Code 101
    E_121 = "Sessão solene"  # Code 121
    E_141 = "Jornadas"  # Code 141
    E_161 = "Outros"  # Code 161


class TipodeDeslocacoes(Enum):
    """
    Displacement type codes from Portuguese Parliament documentation

    Used in models:
    - DeslocacaoParlamentar (displacement type classification)
    - DadosDeslocacoesComissaoOut structure

    Documentation Reference:
    - Tipo: "Tipo de deslocações na estrutura TipodeDeslocacoes"
    - Based on official VI_Legislatura reference table (page 15)

    Note: Text-based codes as documented in official reference table.
    """

    # Text codes from official TipodeDeslocacoes table (VI_Legislatura doc, page 15)
    CO = "Conferência"
    DV = "Diversos"
    MI = "Missões"
    PR = "Participação em reunião"
    SM = "Seminário"
    VO = "Visita Oficial"


@dataclass
class GeneralActivityTranslation:
    """Container for general activity field translation results"""

    code: str
    description: str
    category: str = "general_activity"
    is_valid: bool = True

    def __str__(self) -> str:
        return self.description


class GeneralActivityTranslator:
    """
    Translator for general parliamentary activity-related coded fields

    Usage:
        translator = GeneralActivityTranslator()

        # Author types
        author_desc = translator.author_type("DEPUTADO")  # "Deputado"

        # Event types
        event_desc = translator.event_type("REUNIAO")  # "Reunião"

        # Displacement types
        disp_desc = translator.displacement_type("MISSAO_OFICIAL")  # "Missão Oficial"
    """

    def author_type(self, code: str) -> Optional[str]:
        """Get readable description for author type code"""
        translation = self.get_author_type(code)
        return translation.description if translation else None

    def get_author_type(self, code: str) -> Optional[GeneralActivityTranslation]:
        """
        Get full translation metadata for author type code

        Documentation Reference:
        - Maps TipoAutor codes to their descriptions
        - Used in AtividadeParlamentar.tipo_autor field
        """
        if not code:
            return None

        try:
            enum_value = TipodeAutor[code.upper()]
            return GeneralActivityTranslation(
                code=code,
                description=enum_value.value,
                category="author_type",
                is_valid=True,
            )
        except KeyError:
            return GeneralActivityTranslation(
                code=code,
                description=f"Unknown author type: {code}",
                category="author_type",
                is_valid=False,
            )

    def event_type(self, code: str) -> Optional[str]:
        """Get readable description for event type code"""
        translation = self.get_event_type(code)
        return translation.description if translation else None

    def get_event_type(self, code: str) -> Optional[GeneralActivityTranslation]:
        """
        Get full translation metadata for event type code

        Documentation Reference:
        - Maps TipoEvento numeric codes to their descriptions
        - Used in EventoParlamentar.tipo_evento field
        - Based on VI_Legislatura doc TipodeEvento table (page 16)
        """
        if not code:
            return None

        # Handle numeric codes by creating enum key
        try:
            enum_key = f"E_{code}" if code.isdigit() else code.upper()
            enum_value = TipodeEvento[enum_key]
            return GeneralActivityTranslation(
                code=code,
                description=enum_value.value,
                category="event_type",
                is_valid=True,
            )
        except KeyError:
            return GeneralActivityTranslation(
                code=code,
                description=f"Unknown event type: {code}",
                category="event_type",
                is_valid=False,
            )

    def displacement_type(self, code: str) -> Optional[str]:
        """Get readable description for displacement type code"""
        translation = self.get_displacement_type(code)
        return translation.description if translation else None

    def get_displacement_type(self, code: str) -> Optional[GeneralActivityTranslation]:
        """
        Get full translation metadata for displacement type code

        Documentation Reference:
        - Maps TipodeDeslocacoes codes to their descriptions
        - Used for parliamentary displacement classification
        """
        if not code:
            return None

        try:
            enum_value = TipodeDeslocacoes[code.upper()]
            return GeneralActivityTranslation(
                code=code,
                description=enum_value.value,
                category="displacement_type",
                is_valid=True,
            )
        except KeyError:
            return GeneralActivityTranslation(
                code=code,
                description=f"Unknown displacement type: {code}",
                category="displacement_type",
                is_valid=False,
            )

    def meeting_type(self, code: str) -> Optional[str]:
        """Get readable description for meeting type code"""
        translation = self.get_meeting_type(code)
        return translation.description if translation else None

    def get_meeting_type(self, code: str) -> Optional[GeneralActivityTranslation]:
        """
        Get full translation metadata for meeting type code

        Documentation Reference:
        - Maps TipodeReuniao codes to their descriptions
        - Used in VotacaoOut.TipoReuniao field
        - Based on VI_Legislatura doc TipodeReuniao table (page 13)
        """
        if not code:
            return None

        try:
            enum_value = TipodeReuniao[code.upper()]
            return GeneralActivityTranslation(
                code=code,
                description=enum_value.value,
                category="meeting_type",
                is_valid=True,
            )
        except KeyError:
            return GeneralActivityTranslation(
                code=code,
                description=f"Unknown meeting type: {code}",
                category="meeting_type",
                is_valid=False,
            )


# Global instance for convenience
general_activity_translator = GeneralActivityTranslator()


def translate_author_type(code: str) -> Optional[str]:
    """Quick translation of author type code"""
    return general_activity_translator.author_type(code)


def translate_event_type(code: str) -> Optional[str]:
    """Quick translation of event type code"""
    return general_activity_translator.event_type(code)


def translate_displacement_type(code: str) -> Optional[str]:
    """Quick translation of displacement type code"""
    return general_activity_translator.displacement_type(code)


def translate_meeting_type(code: str) -> Optional[str]:
    """Quick translation of meeting type code"""
    return general_activity_translator.meeting_type(code)
