"""
Intervencoes Translators
=======================

Translators for parliamentary intervention-related coded fields.
Based on official Parliament documentation (December 2017):
"Significado das Tags do Ficheiro Intervenções<Legislatura>.xml"

XML Structure:
- Root: Intervencoes_DadosPesquisaIntervencoesOut
- Multiple coded fields requiring translation to human-readable descriptions
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .publications import PublicationTranslator


class TipodeDebate(Enum):
    """
    Debate type codes from Portuguese Parliament documentation
    
    Used in models:
    - IntervencoesOut (debTp field)
    - IntervencaoParlamentar (debate type fields)
    
    Documentation Reference:
    - debTp: "Tipo de debate, campo tipo em TipodeDebate"
    - debTpdesc: "Descrição do tipo de debate, campo descrição em TipodeDebate"
    """
    
    # Parliamentary debate types (codes 1-37)
    # Note: These are examples based on common Portuguese parliamentary procedures
    # The actual codes should be extracted from the XML data during processing
    D1 = "Debate de Urgência"
    D2 = "Debate Parlamentar"
    D3 = "Discussão na Generalidade"
    D4 = "Discussão na Especialidade"
    D5 = "Votação Final Global"
    D6 = "Interpelação ao Governo"
    D7 = "Período de Intervenções"
    D8 = "Debate de Atualidade"
    D9 = "Debates de Conjuntura"
    D10 = "Tempo de Antena"
    # Additional codes 11-37 to be populated from actual data


class TipodeIntervencao(Enum):
    """
    Intervention type codes from Portuguese Parliament documentation
    
    Used in models:
    - IntervencoesOut (intTp field)
    - IntervencaoParlamentar (intervention type fields)
    
    Documentation Reference:
    - intTp: "Tipo de intervenção, campo tipo em TipodeIntervencao" 
    - intTpdesc: "Descrição do tipo de intervenção, campo descrição em TipodeIntervencao"
    """
    
    # Parliamentary intervention types (codes 2-2396)
    # Note: These are examples based on common Portuguese parliamentary procedures
    # The actual codes should be extracted from the XML data during processing
    I2 = "Intervenção do Deputado"
    I3 = "Intervenção do Presidente"
    I4 = "Intervenção do Governo"
    I5 = "Pergunta"
    I6 = "Resposta"
    I7 = "Esclarecimento"
    I8 = "Declaração de Voto"
    I9 = "Proposta de Alteração"
    I10 = "Requerimento"
    # Additional codes 11-2396 to be populated from actual data


class TipodeAtividade(Enum):
    """
    Activity type codes from Portuguese Parliament documentation
    
    Used in models:
    - AtividadesOut (ativTp field)
    - AtividadeParlamentar (activity type fields)
    
    Documentation Reference:
    - ativTp: "Tipo de atividade, campo tipo em TipodeAtividade"
    - ativTpdesc: "Descrição do tipo de atividade, campo descrição em TipodeAtividade"
    """
    
    AGP = "Audiências em Grupos Parlamentares"
    APG = "Audiências Públicas Gerais" 
    APP = "Audiências Públicas Parlamentares"
    COM = "Comissões"
    CPE = "Comissões Permanentes Especializadas"
    CPI = "Comissões Parlamentares de Inquérito"
    DEB = "Debates"
    DEL = "Delegações"
    EVE = "Eventos"
    LEG = "Legislação"
    PLE = "Plenário"
    REU = "Reuniões"
    SES = "Sessões"
    VOT = "Votações"


@dataclass
class InterventionTranslation:
    """Container for intervention field translation results"""
    
    code: str
    description: str
    category: str = "intervention"
    is_valid: bool = True
    
    def __str__(self) -> str:
        return self.description


class InterventionTranslator:
    """
    Translator for intervention-related coded fields that require enum translation
    
    Only handles abbreviated codes that need expansion, not obvious strings.
    
    Usage:
        translator = InterventionTranslator()
        
        # Debate types (coded numbers)
        debate_desc = translator.debate_type("1")  # "Debate de Urgência"
        
        # Intervention types (coded numbers)
        interv_desc = translator.intervention_type("2")  # "Intervenção do Deputado"
        
        # Activity types (coded abbreviations)
        activ_desc = translator.activity_type("AGP")  # "Audiências em Grupos Parlamentares"
        
        # Publication types (coded abbreviations)
        pub_desc = translator.publication_type("A")  # "DAR II série A"
        
        # With metadata
        translation = translator.get_debate_type("1")
        print(f"Code: {translation.code}, Valid: {translation.is_valid}")
    """
    
    def __init__(self):
        # Use publication translator for shared publication type codes
        self.publication_translator = PublicationTranslator()
    
    def debate_type(self, code: str) -> Optional[str]:
        """Get readable description for debate type code"""
        translation = self.get_debate_type(code)
        return translation.description if translation else None
    
    def get_debate_type(self, code: str) -> Optional[InterventionTranslation]:
        """
        Get full translation metadata for debate type code
        
        Documentation Reference:
        - Maps debTp codes to their debTpdesc descriptions
        - Used across multiple intervention-related models
        """
        if not code:
            return None
        
        # Convert numeric code to enum key
        enum_key = f"D{code}"
        
        try:
            enum_value = TipodeDebate[enum_key]
            return InterventionTranslation(
                code=code, description=enum_value.value, category="debate_type", is_valid=True
            )
        except KeyError:
            return InterventionTranslation(
                code=code,
                description=f"Unknown debate type: {code}",
                category="debate_type",
                is_valid=False,
            )
    
    def intervention_type(self, code: str) -> Optional[str]:
        """Get readable description for intervention type code"""
        translation = self.get_intervention_type(code)
        return translation.description if translation else None
    
    def get_intervention_type(self, code: str) -> Optional[InterventionTranslation]:
        """
        Get full translation metadata for intervention type code
        
        Documentation Reference:
        - Maps intTp codes to their intTpdesc descriptions
        - Used across multiple intervention-related models
        """
        if not code:
            return None
        
        # Convert numeric code to enum key
        enum_key = f"I{code}"
        
        try:
            enum_value = TipodeIntervencao[enum_key]
            return InterventionTranslation(
                code=code, description=enum_value.value, category="intervention_type", is_valid=True
            )
        except KeyError:
            return InterventionTranslation(
                code=code,
                description=f"Unknown intervention type: {code}",
                category="intervention_type",
                is_valid=False,
            )
    
    def activity_type(self, code: str) -> Optional[str]:
        """Get readable description for activity type code"""
        translation = self.get_activity_type(code)
        return translation.description if translation else None
    
    def get_activity_type(self, code: str) -> Optional[InterventionTranslation]:
        """
        Get full translation metadata for activity type code
        
        Documentation Reference:
        - Maps ativTp codes to their ativTpdesc descriptions
        - Used across multiple activity-related models
        """
        if not code:
            return None
        
        try:
            enum_value = TipodeAtividade[code.upper()]
            return InterventionTranslation(
                code=code, description=enum_value.value, category="activity_type", is_valid=True
            )
        except KeyError:
            return InterventionTranslation(
                code=code,
                description=f"Unknown activity type: {code}",
                category="activity_type",
                is_valid=False,
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
intervention_translator = InterventionTranslator()


def translate_debate_type(code: str) -> Optional[str]:
    """Quick translation of debate type code"""
    return intervention_translator.debate_type(code)


def translate_intervention_type(code: str) -> Optional[str]:
    """Quick translation of intervention type code"""
    return intervention_translator.intervention_type(code)


def translate_activity_type(code: str) -> Optional[str]:
    """Quick translation of activity type code"""
    return intervention_translator.activity_type(code)


def translate_intervention_publication_type(code: str) -> Optional[str]:
    """Quick translation of intervention publication type code"""
    return intervention_translator.publication_type(code)