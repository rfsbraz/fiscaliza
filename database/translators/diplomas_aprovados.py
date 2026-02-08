"""
Diplomas Aprovados Translation Module
=====================================

Code-to-value translations for approved diplomas (Diplomas*.xml).

Based on official Portuguese Parliament documentation from December 2017:
"Significado das Tags do Ficheiro Diplomas<Legislatura>.xml"

This module provides ONLY translations for coded field values that need conversion
to their meaningful representations. Fields with already meaningful data 
(like titles, names, IDs) do not need translation.
"""

from enum import Enum
from typing import Dict, Optional


# Code Value Translations - Only for actual coded values found in XML data

# Diploma Type Codes (Tp field)
DIPLOMA_TYPE_CODES = {
    'A': 'Aprovado',  # Approved
    'D': 'Decreto da Assembleia da República', # Assembly Decree
    'L': 'Lei',  # Law
    'R': 'Resolução'  # Resolution
}

# Initiative Type Codes (IniTipo field)
INITIATIVE_TYPE_CODES = {
    'R': 'Resolução',  # Resolution
    'S': 'Solicitação',  # Solicitation 
    'J': 'Projeto de Lei'  # Bill/Law Project
}

# Publication Type Codes (pubTp field)
PUBLICATION_TYPE_CODES = {
    'M': 'Mensal',  # Monthly
    'A': 'Anual',   # Annual
    'D': 'Diário',  # Daily
    'K': 'Semanal', # Weekly
    'B': 'Bimensal' # Bimonthly
}

def convert_field_value(field_name: str, value: str) -> Optional[str]:
    """
    Convert coded field value to its meaningful representation
    
    Args:
        field_name: Name of the field containing the coded value
        value: The coded value to convert
        
    Returns:
        Meaningful representation of the coded value, or None if no translation exists
    """
    if not value or value == '':
        return None
    
    # Map field names to their corresponding code dictionaries
    field_mappings = {
        'tp': DIPLOMA_TYPE_CODES,
        'Tp': DIPLOMA_TYPE_CODES,
        'ini_tipo': INITIATIVE_TYPE_CODES, 
        'IniTipo': INITIATIVE_TYPE_CODES,
        'pub_tp': PUBLICATION_TYPE_CODES,
        'pubTp': PUBLICATION_TYPE_CODES
    }
    
    code_dict = field_mappings.get(field_name)
    if code_dict:
        return code_dict.get(value, value)  # Return original value if no mapping found
    
    return value  # Return original value if field doesn't need translation

def get_diploma_type_description(code: str) -> Optional[str]:
    """Get full description for diploma type code"""
    return DIPLOMA_TYPE_CODES.get(code)

def get_initiative_type_description(code: str) -> Optional[str]:
    """Get full description for initiative type code"""
    return INITIATIVE_TYPE_CODES.get(code)

def get_publication_type_description(code: str) -> Optional[str]:
    """Get full description for publication type code"""
    return PUBLICATION_TYPE_CODES.get(code)