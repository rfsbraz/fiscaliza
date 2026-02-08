"""
Parliamentary Intervention Translators
=====================================

Translators for parliamentary intervention-related coded fields.
Based on official Parliament documentation (December 2017):
"IntervencoesOut" structure from AtividadeDeputado documentation.
"""

from dataclasses import dataclass
from typing import Optional

from .publications import PublicationTranslator


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
    Translator for parliamentary intervention-related coded fields

    Combines intervention-specific translations with shared publication types.
    Based on IntervencoesOut documentation structure.

    Usage:
        translator = InterventionTranslator()

        # Publication types (shared with other modules)
        pub_desc = translator.publication_type("A")  # "DAR II série A"

        # Intervention-specific types
        int_desc = translator.intervention_type("DEBATE")  # "Parliamentary Debate"
    """

    def __init__(self):
        # Use publication translator for shared publication type codes
        self.publication_translator = PublicationTranslator()

    def publication_type(self, code: str) -> Optional[str]:
        """
        Get readable description for publication type code

        Documentation Reference:
        - pubTp: "Tipo de publicação da intervenção, campo tipo em TipodePublicacao"

        Delegates to shared PublicationTranslator for consistency.
        """
        return self.publication_translator.publication_type(code)

    def get_publication_type(self, code: str):
        """Get full publication type translation metadata"""
        return self.publication_translator.get_publication_type(code)

    def intervention_type(self, tin_ds: str) -> Optional[str]:
        """
        Get readable description for intervention type

        Documentation Reference:
        - tinDs: "Tipo de intervenção"

        Note: This field appears to contain descriptive text rather than codes,
        so this method primarily provides normalization and validation.
        """
        if not tin_ds:
            return None

        # Common intervention types found in data
        type_map = {
            "DEBATE": "Parliamentary Debate",
            "DISCUSSAO": "Discussion",
            "VOTACAO": "Voting",
            "PERGUNTA": "Question",
            "INTERPELACAO": "Interpellation",
            "DECLARACAO": "Declaration",
            "MOCAO": "Motion",
        }

        # Try exact match first
        normalized = tin_ds.upper().strip()
        if normalized in type_map:
            return type_map[normalized]

        # Return original if no mapping found (likely already descriptive)
        return tin_ds

    def get_intervention_type(self, tin_ds: str) -> Optional[InterventionTranslation]:
        """Get full translation metadata for intervention type"""
        if not tin_ds:
            return None

        description = self.intervention_type(tin_ds)
        is_valid = description is not None

        return InterventionTranslation(
            code=tin_ds,
            description=description or f"Unknown intervention type: {tin_ds}",
            is_valid=is_valid,
        )

    def supplement_type(self, pub_sup: str) -> Optional[str]:
        """
        Get readable description for publication supplement

        Documentation Reference:
        - pubSup: "Suplemento onde foi publicada a intervenção"
        """
        if not pub_sup:
            return None

        # Common supplement patterns
        if pub_sup.isdigit():
            return f"Supplement {pub_sup}"

        return pub_sup  # Return as-is if already descriptive

    def assembly_diary_number(self, pub_dar: str) -> Optional[str]:
        """
        Get readable description for Assembly Diary number

        Documentation Reference:
        - pubDar: "Número do Diário da Assembleia da República da publicação da intervenção"
        """
        if not pub_dar:
            return None

        if pub_dar.isdigit():
            return f"Assembly Diary No. {pub_dar}"

        return f"Assembly Diary {pub_dar}"


# Global instance for convenience
intervention_translator = InterventionTranslator()


def translate_intervention_publication_type(code: str) -> Optional[str]:
    """Quick translation of intervention publication type code"""
    return intervention_translator.publication_type(code)


def translate_intervention_type(tin_ds: str) -> Optional[str]:
    """Quick translation of intervention type"""
    return intervention_translator.intervention_type(tin_ds)
