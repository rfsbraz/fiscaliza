"""
Eventual Delegation Translators
===============================

Translators for eventual delegation-related coded fields.
Based on official Parliament documentation (December 2017):
"DelegacoesEventuais.xml" structure - identical across IX through XIII legislatures.
"""

from enum import Enum
from typing import Optional
from dataclasses import dataclass

from .common_enums import TipoParticipante


@dataclass
class DelegacaoEventualTranslation:
    """Container for delegation field translation results"""
    code: str
    description: str
    category: str = "delegacao_eventual"
    is_valid: bool = True
    
    def __str__(self) -> str:
        return self.description


class DelegacaoEventualTranslator:
    """
    Translator for eventual delegation-related coded fields
    
    Usage:
        translator = DelegacaoEventualTranslator()
        
        # Participant types
        participant_desc = translator.participant_type("D")  # "Deputado"
    """
    
    def participant_type(self, code: str) -> Optional[str]:
        """Get readable description for participant type code"""
        translation = self.get_participant_type(code)
        return translation.description if translation else None
    
    def get_participant_type(self, code: str) -> Optional[DelegacaoEventualTranslation]:
        """
        Get full translation metadata for participant type code
        
        Documentation Reference:
        - Maps Tipo codes to their descriptions
        - Used in DelegacaoEventualParticipante.tipo_participante field
        - Based on DelegacoesEventuais documentation (December 2017)
        """
        if not code:
            return None
            
        try:
            enum_value = TipoParticipante[code.upper()]
            return DelegacaoEventualTranslation(
                code=code,
                description=enum_value.value,
                category="participant_type",
                is_valid=True
            )
        except KeyError:
            return DelegacaoEventualTranslation(
                code=code,
                description=f"Unknown participant type: {code}",
                category="participant_type",
                is_valid=False
            )


# Global instance for convenience
delegacao_eventual_translator = DelegacaoEventualTranslator()


def translate_participant_type(code: str) -> Optional[str]:
    """Quick translation of participant type code"""
    return delegacao_eventual_translator.participant_type(code)