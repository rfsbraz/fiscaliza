"""
Portuguese Parliament Field Translators
======================================

Thematic field translation modules for Portuguese Parliament data.
Each module contains translators for specific functional areas.
"""

from .deputy_activities import DeputyActivityTranslator
from .parliamentary_interventions import InterventionTranslator  
from .initiatives import InitiativeTranslator
from .publications import PublicationTranslator
from .general_activities import GeneralActivityTranslator
from .agenda_parlamentar import AgendaTranslator
from .delegacao_eventual import DelegacaoEventualTranslator
from .delegacoes_permanentes import DelegacoesPermanentesTranslator
from .intervencoes import InterventionTranslator as IntervencoesTranslator
# from .orcamento_estado import OrcamentoEstadoTranslator  # Removed - translation fields no longer used
from .diplomas_aprovados import (DIPLOMA_TYPE_CODES, INITIATIVE_TYPE_CODES, PUBLICATION_TYPE_CODES,
                                convert_field_value, get_diploma_type_description, 
                                get_initiative_type_description, get_publication_type_description)
from .common_enums import TipoParticipante

__all__ = [
    'DeputyActivityTranslator',
    'InterventionTranslator', 
    'InitiativeTranslator',
    'PublicationTranslator',
    'GeneralActivityTranslator',
    'AgendaTranslator',
    'DelegacaoEventualTranslator',
    'DelegacoesPermanentesTranslator',
    'IntervencoesTranslator',
    # 'OrcamentoEstadoTranslator',  # Removed - translation fields no longer used
    'TipoParticipante',
    # Diplomas Aprovados code translations
    'DIPLOMA_TYPE_CODES',
    'INITIATIVE_TYPE_CODES',
    'PUBLICATION_TYPE_CODES',
    'convert_field_value',
    'get_diploma_type_description',
    'get_initiative_type_description',
    'get_publication_type_description',
]