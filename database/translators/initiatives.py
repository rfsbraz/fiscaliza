"""
Initiative Translators
=====================

Translators for parliamentary initiative-related coded fields.
Based on official Parliament documentation (December 2017):
"IniciativasOut" structure from AtividadeDeputado documentation.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .publications import PublicationTranslator


class TipodeIniciativa(Enum):
    """
    Initiative type codes from Portuguese Parliament documentation

    Used in models:
    - IniciativasOut (iniTp field)
    - IniciativaParlamentar (initiative type fields)
    - InitiativeProposal (proposal type fields)

    Documentation Reference:
    - iniTp: "Tipo de iniciativa, campo tipo em TipodeIniciativa"
    - iniTpdesc: "Descrição do tipo de iniciativa, campo descrição em TipodeIniciativa"
    """

    A = "Apreciação Parlamentar"
    C = "Projeto de Revisão Constitucional"
    D = "Projeto de Deliberação"
    F = "Ratificação"
    G = "Projeto de Regimento"
    I = "Inquérito Parlamentar"
    J = "Projeto de Lei"
    P = "Proposta de Lei"
    R = "Projeto de Resolução"
    S = "Proposta de Resolução"
    U = "Iniciativa Popular"


class ProposalAmendmentType(Enum):
    """
    Amendment proposal type codes that need translation
    
    Used in models:
    - Iniciativas_PropostasAlteracaoOut (tipo field)
    - IniciativaPropostaAlteracao (proposal type fields)
    
    Documentation Reference:
    - tipo: "Tipo da proposta de alteração"
    
    Only coded values that require translation from abbreviations.
    """
    
    # Add actual coded values found in data - these are examples
    PA = "Proposta de Alteração"
    PS = "Proposta de Substituição"
    PE = "Proposta de Eliminação"


@dataclass
class InitiativeTranslation:
    """Container for initiative field translation results"""

    code: str
    description: str
    category: str = "initiative"
    is_valid: bool = True

    def __str__(self) -> str:
        return self.description


class InitiativeTranslator:
    """
    Translator for initiative-related coded fields that require enum translation
    
    Only handles abbreviated codes that need expansion, not obvious strings.

    Usage:
        translator = InitiativeTranslator()

        # Initiative types (coded abbreviations)
        init_desc = translator.initiative_type("J")  # "Projeto de Lei"
        
        # Proposal amendment types (coded abbreviations) 
        amend_desc = translator.proposal_amendment_type("PA")  # "Proposta de Alteração"
        
        # Publication types (coded abbreviations) 
        pub_desc = translator.publication_type("A")  # "DAR II série A"

        # With metadata
        translation = translator.get_initiative_type("J")
        print(f"Code: {translation.code}, Valid: {translation.is_valid}")
    """
    
    def __init__(self):
        # Use publication translator for shared publication type codes
        self.publication_translator = PublicationTranslator()

    def initiative_type(self, code: str) -> Optional[str]:
        """Get readable description for initiative type code"""
        translation = self.get_initiative_type(code)
        return translation.description if translation else None

    def get_initiative_type(self, code: str) -> Optional[InitiativeTranslation]:
        """
        Get full translation metadata for initiative type code

        Documentation Reference:
        - Maps iniTp codes to their iniTpdesc descriptions
        - Used across multiple initiative-related models
        """
        if not code:
            return None

        try:
            enum_value = TipodeIniciativa[code.upper()]
            return InitiativeTranslation(
                code=code, description=enum_value.value, is_valid=True
            )
        except KeyError:
            return InitiativeTranslation(
                code=code,
                description=f"Unknown initiative type: {code}",
                is_valid=False,
            )

    def proposal_amendment_type(self, code: str) -> Optional[str]:
        """
        Get readable description for proposal amendment type code
        
        Documentation Reference:
        - tipo: "Tipo da proposta de alteração"
        """
        if not code:
            return None
            
        try:
            enum_value = ProposalAmendmentType[code.upper()]
            return enum_value.value
        except KeyError:
            return f"Unknown amendment type: {code}"
    
    def get_proposal_amendment_type(self, code: str) -> Optional[InitiativeTranslation]:
        """Get full translation metadata for proposal amendment type code"""
        if not code:
            return None
            
        description = self.proposal_amendment_type(code)
        is_valid = code.upper() in [e.name for e in ProposalAmendmentType]
        
        return InitiativeTranslation(
            code=code,
            description=description or f"Unknown amendment type: {code}",
            category="proposal_amendment_type",
            is_valid=is_valid
        )
    
    def publication_type(self, code: str) -> Optional[str]:
        """
        Get readable description for publication type code
        
        Documentation Reference:
        - pubTp: "Abreviatura do Tipo de Publicação"
        - pubTipo: "Descrição do Tipo de Publicação"
        
        Delegates to shared PublicationTranslator for consistency.
        """
        return self.publication_translator.publication_type(code)
    
    def get_publication_type(self, code: str):
        """Get full publication type translation metadata"""
        return self.publication_translator.get_publication_type(code)


# Global instance for convenience
initiative_translator = InitiativeTranslator()


def translate_initiative_type(code: str) -> Optional[str]:
    """Quick translation of initiative type code"""
    return initiative_translator.initiative_type(code)


def translate_proposal_amendment_type(code: str) -> Optional[str]:
    """Quick translation of proposal amendment type code"""
    return initiative_translator.proposal_amendment_type(code)


def translate_initiative_publication_type(code: str) -> Optional[str]:
    """Quick translation of initiative publication type code"""
    return initiative_translator.publication_type(code)
