"""
Deputy Activity Translators
==========================

Translators for deputy activity-related coded fields.
Based on official Parliament documentation (December 2017):
"AtividadeDeputado<Legislatura>.xml" documentation.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TipodeAtividade(Enum):
    """
    Activity type codes from Portuguese Parliament documentation

    Used in models:
    - ActividadesParlamentaresOut (actTp field)
    - ActividadesComissaoOut (actTp field)
    - AtividadeParlamentar (activity type fields)
    """

    AGP = "Atividade do grupo parlamentar de amizade"
    AUD = "Audiência"
    AUP = "Audição"
    CER = "Cerimónias"
    CGE = "Conta Geral do Estado"
    DEB = "Debates Diversos"
    DES = "Deslocação"
    DPO = "Declarações Políticas"
    DPR = "Deslocações do Presidente da República"
    EGP = "Eleição do grupo parlamentar de amizade"
    EVN = "Evento"
    GOD = "Grandes Opções do Conceito Estratégico de Defesa Nacional"
    IMU = "Imunidade Parlamentar"
    INI = "Discussão de Iniciativas"
    ITG = "Interpelação ao Governo"
    MOC = "Moção"
    OEX = "Eleições e composições de órgãos"
    PEC = "Programa de Estabilidade e Crescimento/Documento de Estratégia Orçamental"
    PEG = "Perguntas ao Governo"
    PET = "Discussão de Petições"
    PII = "Parecer de Incompatibilidade / Levantamento de Imunidade"
    POR = "Orientação da Política Orçamental"
    PRC = "Relatórios Externos"
    PRG = "Programa do Governo"
    PUE = "Participação de Portugal na União Europeia"
    REP = "Representações e Delegações"
    RSI = "Relatório de Segurança Interna"
    SES = "Cerimónia"
    VOT = "Voto"


class TipodeRequerimento(Enum):
    """
    Request type codes from Portuguese Parliament documentation

    Used in models:
    - RequerimentosOut (reqTp field)
    - PerguntaRequerimento (request type fields)
    """

    AC = "Administração Central"
    AL = "Administração Local"
    AR = "Assembleia da República"
    EI = "Entidades Independentes"
    RA = "Regiões Autónomas"


@dataclass
class ActivityTranslation:
    """Container for activity field translation results"""

    code: str
    description: str
    category: str
    is_valid: bool = True

    def __str__(self) -> str:
        return self.description


class DeputyActivityTranslator:
    """
    Translator for deputy activity-related coded fields

    Usage:
        translator = DeputyActivityTranslator()

        # Activity types
        activity_desc = translator.activity_type("AUD")  # "Audiência"

        # Request types
        request_desc = translator.request_type("AR")  # "Assembleia da República"

        # Committee status
        status_desc = translator.committee_status("efetivo")  # "Effective member"
    """

    def activity_type(self, code: str) -> Optional[str]:
        """Get readable description for activity type code"""
        translation = self.get_activity_type(code)
        return translation.description if translation else None

    def get_activity_type(self, code: str) -> Optional[ActivityTranslation]:
        """Get full translation metadata for activity type code"""
        if not code:
            return None

        try:
            enum_value = TipodeAtividade[code.upper()]
            return ActivityTranslation(
                code=code,
                description=enum_value.value,
                category="activity_type",
                is_valid=True,
            )
        except KeyError:
            return ActivityTranslation(
                code=code,
                description=f"Unknown activity type: {code}",
                category="activity_type",
                is_valid=False,
            )

    def request_type(self, code: str) -> Optional[str]:
        """Get readable description for request type code"""
        translation = self.get_request_type(code)
        return translation.description if translation else None

    def get_request_type(self, code: str) -> Optional[ActivityTranslation]:
        """Get full translation metadata for request type code"""
        if not code:
            return None

        try:
            enum_value = TipodeRequerimento[code.upper()]
            return ActivityTranslation(
                code=code,
                description=enum_value.value,
                category="request_type",
                is_valid=True,
            )
        except KeyError:
            return ActivityTranslation(
                code=code,
                description=f"Unknown request type: {code}",
                category="request_type",
                is_valid=False,
            )

    def committee_status(self, status: str) -> Optional[str]:
        """Get readable description for committee status"""
        translation = self.get_committee_status(status)
        return translation.description if translation else None

    def get_committee_status(self, status: str) -> Optional[ActivityTranslation]:
        """
        Get full translation metadata for committee status

        Documentation Reference:
        - cmsSituacao: "Situação perante a subcomissão/grupo de trabalho (suplente/efetivo)"
        - gtarSituacao: "Situação no grupo de trabalho AR – suplente/efetivo"
        """
        if not status:
            return None

        status_map = {
            "suplente": "Substitute member",
            "efetivo": "Effective member",
            "Suplente": "Substitute member",
            "Efetivo": "Effective member",
        }

        description = status_map.get(status)
        is_valid = description is not None

        if not description:
            description = f"Unknown status: {status}"

        return ActivityTranslation(
            code=status,
            description=description,
            category="committee_status",
            is_valid=is_valid,
        )

    def delegation_type(self, dev_type: str) -> Optional[str]:
        """Get readable description for delegation type"""
        translation = self.get_delegation_type(dev_type)
        return translation.description if translation else None

    def get_delegation_type(self, dev_type: str) -> Optional[ActivityTranslation]:
        """
        Get full translation metadata for delegation type

        Documentation Reference:
        - devTp: "Nacional ou Internacional" (National or International)
        """
        if not dev_type:
            return None

        type_map = {
            "Nacional": "National delegation",
            "Internacional": "International delegation",
            "nacional": "National delegation",
            "internacional": "International delegation",
        }

        description = type_map.get(dev_type)
        is_valid = description is not None

        if not description:
            description = f"Unknown delegation type: {dev_type}"

        return ActivityTranslation(
            code=dev_type,
            description=description,
            category="delegation_type",
            is_valid=is_valid,
        )

    def document_type(self, req_per_tp: str) -> Optional[str]:
        """Get readable description for document type"""
        translation = self.get_document_type(req_per_tp)
        return translation.description if translation else None

    def get_document_type(self, req_per_tp: str) -> Optional[ActivityTranslation]:
        """
        Get full translation metadata for document type

        Documentation Reference:
        - reqPerTp: "Tipo de documento - requerimento/pergunta"
        """
        if not req_per_tp:
            return None

        type_map = {
            "requerimento": "Request document",
            "pergunta": "Question document",
            "Requerimento": "Request document",
            "Pergunta": "Question document",
        }

        description = type_map.get(req_per_tp)
        is_valid = description is not None

        if not description:
            description = f"Unknown document type: {req_per_tp}"

        return ActivityTranslation(
            code=req_per_tp,
            description=description,
            category="document_type",
            is_valid=is_valid,
        )


# Global instance for convenience
deputy_activity_translator = DeputyActivityTranslator()


def translate_activity_type(code: str) -> Optional[str]:
    """Quick translation of activity type code"""
    return deputy_activity_translator.activity_type(code)


def translate_request_type(code: str) -> Optional[str]:
    """Quick translation of request type code"""
    return deputy_activity_translator.request_type(code)


def translate_committee_status(status: str) -> Optional[str]:
    """Quick translation of committee status"""
    return deputy_activity_translator.committee_status(status)
