"""
Permanent Delegations Translators
=================================

Translators for permanent delegation-related coded fields.
Based on official Parliament documentation (December 2017):
"DelegacoesPermanentes.xml" structure - identical across IX through XIII legislatures.
"""

from enum import Enum
from typing import Optional
from dataclasses import dataclass

from .common_enums import TipoParticipante


class TipoReuniao(Enum):
    """
    Meeting type codes from Portuguese Parliament documentation
    
    Used in models:
    - DelegacaoPermanente related meeting records (tipo field)
    
    Documentation Reference:
    - Tipo: "Tipo de reunião (REN- Reunião no estrangeiro / RNI – Reunião Internacional em Portugal)"
    - Based on official DelegacoesPermanentes documentation (December 2017)
    
    Note: Three-letter codes as documented in official reference.
    """
    
    # Meeting type codes from official documentation
    REN = "Reunião no estrangeiro"          # REN - Foreign meeting
    RNI = "Reunião Internacional em Portugal"  # RNI - International meeting in Portugal


@dataclass
class DelegacoesPermanentesTranslation:
    """Container for permanent delegation field translation results"""
    code: str
    description: str
    category: str = "delegacoes_permanentes"
    is_valid: bool = True
    
    def __str__(self) -> str:
        return self.description


class DelegacoesPermanentesTranslator:
    """
    Translator for permanent delegation-related coded fields
    
    Usage:
        translator = DelegacoesPermanentesTranslator()
        
        # Meeting types
        meeting_desc = translator.meeting_type("REN")  # "Reunião no estrangeiro"
        meeting_desc = translator.meeting_type("RNI")  # "Reunião Internacional em Portugal"
        
        # Participant types
        participant_desc = translator.participant_type("D")  # "Deputado"
    """
    
    def meeting_type(self, code: str) -> Optional[str]:
        """Get readable description for meeting type code"""
        translation = self.get_meeting_type(code)
        return translation.description if translation else None
    
    def get_meeting_type(self, code: str) -> Optional[DelegacoesPermanentesTranslation]:
        """
        Get full translation metadata for meeting type code
        
        Documentation Reference:
        - Maps Tipo codes to their descriptions for meetings
        - Used in DelegacaoPermanente meeting records
        - Based on DelegacoesPermanentes documentation (December 2017)
        """
        if not code:
            return None
            
        try:
            enum_value = TipoReuniao[code.upper()]
            return DelegacoesPermanentesTranslation(
                code=code,
                description=enum_value.value,
                category="meeting_type",
                is_valid=True
            )
        except KeyError:
            return DelegacoesPermanentesTranslation(
                code=code,
                description=f"Unknown meeting type: {code}",
                category="meeting_type",
                is_valid=False
            )
    
    def participant_type(self, code: str) -> Optional[str]:
        """Get readable description for participant type code"""
        translation = self.get_participant_type(code)
        return translation.description if translation else None
    
    def get_participant_type(self, code: str) -> Optional[DelegacoesPermanentesTranslation]:
        """
        Get full translation metadata for participant type code
        
        Documentation Reference:
        - Maps Tipo codes to their descriptions for participants
        - Used in DelegacaoPermanente participant records
        - Based on DelegacoesPermanentes documentation (December 2017)
        """
        if not code:
            return None
            
        try:
            enum_value = TipoParticipante[code.upper()]
            return DelegacoesPermanentesTranslation(
                code=code,
                description=enum_value.value,
                category="participant_type",
                is_valid=True
            )
        except KeyError:
            return DelegacoesPermanentesTranslation(
                code=code,
                description=f"Unknown participant type: {code}",
                category="participant_type",
                is_valid=False
            )


# Global instance for convenience
delegacoes_permanentes_translator = DelegacoesPermanentesTranslator()


def translate_meeting_type(code: str) -> Optional[str]:
    """Quick translation of meeting type code"""
    return delegacoes_permanentes_translator.meeting_type(code)


def translate_participant_type(code: str) -> Optional[str]:
    """Quick translation of participant type code"""
    return delegacoes_permanentes_translator.participant_type(code)