"""
Common Parliamentary Enums
=========================

Shared enums used across multiple translator modules to avoid duplication.
Based on official Parliament documentation.
"""

from enum import Enum


class TipoParticipante(Enum):
    """
    Participant type codes from Portuguese Parliament documentation
    
    Used in models:
    - DelegacaoEventualParticipante (tipo_participante field)
    - DelegacaoPermanente participant records (tipo field)
    
    Documentation Reference:
    - Tipo: "Tipo de participante (D=Deputado)"
    - Based on official DelegacoesEventuais and DelegacoesPermanentes documentation (December 2017)
    
    Note: Single-letter codes as documented in official reference.
    """
    
    # Letter code from official documentation
    D = "Deputado"  # D=Deputado