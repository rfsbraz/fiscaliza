"""
Publication Type Translators
===========================

Translators for Portuguese Parliament publication-related coded fields.
Based on official Parliament documentation (December 2017).
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TipodePublicacao(Enum):
    """
    Publication type codes from Portuguese Parliament documentation

    Used across multiple models:
    - IntervencaoParlamentar (pubTp field)
    - IniciativaPublicacao (publication type fields)
    - RequerimentoPublicacao (publication type fields)
    """

    A = "DAR II série A"
    B = "DAR II série B"
    C = "DAR II série C"
    D = "DAR I série"
    E = "DR I série B"
    G = "DAR II série D"
    H = "DAR II série E"
    I = "DAR II série C-RC"
    K = "DAR II série"
    L = "DR II série B"
    M = "DR I série"
    N = "DAR"
    O = "DAR II série C GOP-OE"
    P = "Suplemento"
    Q = "DAR II S C-OE"
    R = "DR I série A"
    S = "Separata"
    T = "DAR II série C CEI"
    U = "DR II série A"
    V = "DAR II S –OE"


@dataclass
class PublicationTranslation:
    """Container for publication field translation results"""

    code: str
    description: str
    category: str = "publication"
    is_valid: bool = True

    def __str__(self) -> str:
        return self.description


class PublicationTranslator:
    """
    Translator for publication-related coded fields

    Usage:
        translator = PublicationTranslator()
        description = translator.publication_type("A")  # "DAR II série A"

        # With metadata
        translation = translator.get_publication_type("A")
        print(f"Valid: {translation.is_valid}")
    """

    def publication_type(self, code: str) -> Optional[str]:
        """Get readable description for publication type code"""
        translation = self.get_publication_type(code)
        return translation.description if translation else None

    def get_publication_type(self, code: str) -> Optional[PublicationTranslation]:
        """Get full translation metadata for publication type code"""
        if not code:
            return None

        try:
            enum_value = TipodePublicacao[code.upper()]
            return PublicationTranslation(
                code=code, description=enum_value.value, is_valid=True
            )
        except KeyError:
            return PublicationTranslation(
                code=code,
                description=f"Unknown publication type: {code}",
                is_valid=False,
            )


# Global instance for convenience
publication_translator = PublicationTranslator()


def translate_publication_type(code: str) -> Optional[str]:
    """Quick translation of publication type code"""
    return publication_translator.publication_type(code)
