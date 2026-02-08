"""
Reuniões e Visitas (Meetings and Visits) Translators
====================================================

Translators for meetings and visits-related coded fields from ReunioesNacionais.xml files.
Based on official Parliament documentation (December 2017):
"Significado das Tags do Ficheiro ReunioesNacionais.xml" specification.

Handles external relations meetings and visits outside the scope of other parliamentary categories,
including international meetings, national meetings, and foreign entity visits.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TipoReuniaoVisita(Enum):
    """
    Meeting and Visit type codes from ReunioesNacionais.xml
    
    Used in models:
    - ReuniaoNacional (tipo field)
    
    Documentation Reference:
    - Tipo: "Tipo de Reunião" field in Reuniao structure
    - Based on ReunioesNacionais.xml specification (December 2017)
    
    Meeting/Visit Categories:
    - International meetings with foreign entities
    - National meetings within Portuguese institutions
    - Visits from foreign entities to Portuguese Parliament
    """
    
    RNI = "Reunião Internacional"           # International Meeting
    RNN = "Reunião Nacional"               # National Meeting  
    VEE = "Visita de entidade estrangeira"  # Foreign Entity Visit


class TipoParticipanteReuniao(Enum):
    """
    Meeting participant type codes from ReunioesNacionais.xml
    
    Used in models:
    - ParticipanteReuniao (tipo field)
    
    Documentation Reference:
    - Tipo: "Tipo de participante" field in Participante structure
    - Based on ReunioesNacionais.xml specification (December 2017)
    
    Note: Only includes officially documented types. Unknown codes are handled
    gracefully at runtime with is_valid=False in translation objects.
    """
    
    D = "Deputado"  # Deputy


@dataclass
class MeetingVisitTranslation:
    """Container for meetings and visits field translation results"""
    
    code: str
    description: str
    category: str = "meeting_visit"
    is_valid: bool = True

    def __str__(self) -> str:
        return self.description


class MeetingVisitTranslator:
    """
    Translator for meetings and visits-related coded fields
    
    Handles all enum translations for ReunioesNacionais.xml structures
    including meeting types and participant classifications.
    
    Usage:
        translator = MeetingVisitTranslator()
        
        # Meeting type translation
        meeting_type = translator.meeting_type("RNI")  # "Reunião Internacional"
        
        # Participant type translation  
        participant_type = translator.participant_type("D")  # "Deputado"
        
        # Full translation with metadata
        translation = translator.get_meeting_type("VEE")
        if translation.is_valid:
            print(f"Meeting type: {translation.description}")
    """

    def meeting_type(self, code: str) -> Optional[str]:
        """Get readable description for meeting/visit type code"""
        translation = self.get_meeting_type(code)
        return translation.description if translation else None

    def get_meeting_type(self, code: str) -> Optional[MeetingVisitTranslation]:
        """
        Get full translation metadata for meeting/visit type code
        
        Documentation Reference:
        - Maps Reuniao.Tipo codes to their descriptions
        - Used in ReuniaoNacional.tipo field
        - Based on ReunioesNacionais.xml specification
        """
        if not code:
            return None

        try:
            enum_value = TipoReuniaoVisita[code.upper()]
            return MeetingVisitTranslation(
                code=code,
                description=enum_value.value,
                category="meeting_type",
                is_valid=True,
            )
        except KeyError:
            return MeetingVisitTranslation(
                code=code,
                description=f"Tipo de reunião desconhecido: {code}",
                category="meeting_type",
                is_valid=False,
            )

    def participant_type(self, code: str) -> Optional[str]:
        """Get readable description for participant type code"""
        translation = self.get_participant_type(code)
        return translation.description if translation else None

    def get_participant_type(self, code: str) -> Optional[MeetingVisitTranslation]:
        """
        Get full translation metadata for participant type code
        
        Documentation Reference:
        - Maps Participante.Tipo codes to their descriptions
        - Used in ParticipanteReuniao.tipo field
        - Based on ReunioesNacionais.xml Participante structure
        """
        if not code:
            return None

        try:
            enum_value = TipoParticipanteReuniao[code.upper()]
            return MeetingVisitTranslation(
                code=code,
                description=enum_value.value,
                category="participant_type",
                is_valid=True,
            )
        except KeyError:
            return MeetingVisitTranslation(
                code=code,
                description=f"Tipo de participante desconhecido: {code}",
                category="participant_type",
                is_valid=False,
            )


# Global instance for convenience
meeting_visit_translator = MeetingVisitTranslator()


def translate_meeting_type(code: str) -> Optional[str]:
    """Quick translation of meeting/visit type code"""
    return meeting_visit_translator.meeting_type(code)


def translate_participant_type(code: str) -> Optional[str]:
    """Quick translation of participant type code"""
    return meeting_visit_translator.participant_type(code)