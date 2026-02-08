"""
Orçamento do Estado (State Budget) Mapper
=========================================

Schema mapper for State Budget files covering both formats:
1. OEPropostasAlteracao<numOE>*.xml (Amendment Proposals - Legislaturas X-XV)
2. OE<numOE>*.xml (Budget Items - Legislatura XVI+)

Based on official Parliament documentation (multiple versions):
- "Significado das Tags dos Ficheiros OEPropostasAlteracao<numOE>Or.xml / OEPropostasAlteracao<numOE>Al.xml"
- "Significado das Tags dos Ficheiros OE<numOE>Or.xml / OE<numOE>Al.xml"

XML Structures:
- Legacy: Complex amendment proposal workflow with nested proponents, voting, regional opinions
- Current: Simplified budget item structure with type-based categorization

Key Features:
- Dual format support with automatic structure detection
- Complex nested data processing (proponents, votes, diplomas, initiatives, maps)
- Regional autonomous regions opinion tracking
"""

import logging
import os
import re
import uuid

# Import our models
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy.dialects.postgresql import insert as pg_insert

from .common_utilities import DataValidationUtils
from .enhanced_base_mapper import SchemaError, SchemaMapper

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from database.models import (
    Legislatura,
    OrcamentoEstado,
    OrcamentoEstadoArtigo,
    OrcamentoEstadoArtigoAlinea,
    OrcamentoEstadoArtigoNumero,
    OrcamentoEstadoDiploma,
    OrcamentoEstadoDiplomaAlinea,
    OrcamentoEstadoDiplomaArtigo,
    OrcamentoEstadoDiplomaMedida,
    OrcamentoEstadoDiplomaMedidaNumero,
    OrcamentoEstadoDiplomaNumero,
    OrcamentoEstadoDiplomaTerceiro,
    OrcamentoEstadoGrupoParlamentarVoto,
    OrcamentoEstadoIniciativa,
    OrcamentoEstadoItem,
    OrcamentoEstadoProponente,
    OrcamentoEstadoPropostaAlteracao,
    OrcamentoEstadoRequerimentoAvocacao,
    OrcamentoEstadoVotacao,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Dataclasses for Level-by-Level Batched Processing
# =============================================================================

# Legacy Format Structures (OEPropostasAlteracao)
@dataclass
class ParsedLegacyAlinea:
    """Parsed alinea within a numero (legacy format)"""
    xml_element: ET.Element
    numero_ref: Any = None  # Reference to parent ParsedLegacyNumero
    data: Dict[str, Any] = field(default_factory=dict)
    db_obj: Any = None


@dataclass
class ParsedLegacyNumero:
    """Parsed numero within an artigo (legacy format)"""
    xml_element: ET.Element
    artigo_ref: Any = None  # Reference to parent ParsedLegacyArtigo
    data: Dict[str, Any] = field(default_factory=dict)
    alineas: List[ParsedLegacyAlinea] = field(default_factory=list)
    db_obj: Any = None


@dataclass
class ParsedLegacyArtigo:
    """Parsed artigo within a proposal (legacy format)"""
    xml_element: ET.Element
    proposal_ref: Any = None  # Reference to parent ParsedLegacyProposal
    data: Dict[str, Any] = field(default_factory=dict)
    numeros: List[ParsedLegacyNumero] = field(default_factory=list)
    db_obj: Any = None


@dataclass
class ParsedLegacyProponente:
    """Parsed proponente (leaf record)"""
    xml_element: ET.Element
    proposal_ref: Any = None
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedLegacyVotacao:
    """Parsed votacao (leaf record)"""
    xml_element: ET.Element
    proposal_ref: Any = None
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedLegacyProposal:
    """Parsed proposal (legacy format)"""
    xml_element: ET.Element
    proposal_id: Optional[int] = None
    data: Dict[str, Any] = field(default_factory=dict)
    proponentes: List[ParsedLegacyProponente] = field(default_factory=list)
    votacoes: List[ParsedLegacyVotacao] = field(default_factory=list)
    artigos: List[ParsedLegacyArtigo] = field(default_factory=list)
    db_obj: Any = None


# Current Format Structures (OE)
@dataclass
class ParsedCurrentDiplomaAlinea:
    """Parsed diploma alinea (leaf record)"""
    xml_element: ET.Element
    numero_ref: Any = None  # Reference to parent ParsedCurrentDiplomaNumero
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedCurrentDiplomaNumero:
    """Parsed diploma numero"""
    xml_element: ET.Element
    artigo_ref: Any = None  # Reference to parent ParsedCurrentDiplomaArtigo
    data: Dict[str, Any] = field(default_factory=dict)
    alineas: List[ParsedCurrentDiplomaAlinea] = field(default_factory=list)
    db_obj: Any = None


@dataclass
class ParsedCurrentDiplomaArtigo:
    """Parsed diploma artigo"""
    xml_element: ET.Element
    diploma_ref: Any = None  # Reference to parent ParsedCurrentDiploma
    data: Dict[str, Any] = field(default_factory=dict)
    numeros: List[ParsedCurrentDiplomaNumero] = field(default_factory=list)
    db_obj: Any = None


@dataclass
class ParsedCurrentDiploma:
    """Parsed diploma"""
    xml_element: ET.Element
    item_ref: Any = None  # Reference to parent ParsedCurrentItem
    data: Dict[str, Any] = field(default_factory=dict)
    artigos: List[ParsedCurrentDiplomaArtigo] = field(default_factory=list)
    db_obj: Any = None


@dataclass
class ParsedCurrentArtigo:
    """Parsed artigo within item (leaf record)"""
    xml_element: ET.Element
    item_ref: Any = None
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedCurrentProposta:
    """Parsed proposta within item (leaf record)"""
    xml_element: ET.Element
    item_ref: Any = None
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedCurrentIniciativa:
    """Parsed iniciativa mapa (leaf record)"""
    xml_element: ET.Element
    item_ref: Any = None
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedCurrentVotacao:
    """Parsed votacao within item (leaf record)"""
    xml_element: ET.Element
    item_ref: Any = None
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedCurrentRequerimento:
    """Parsed requerimento de avocacao (leaf record)"""
    xml_element: ET.Element
    item_ref: Any = None
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedCurrentItem:
    """Parsed item (current format)"""
    xml_element: ET.Element
    item_id: Optional[int] = None
    data: Dict[str, Any] = field(default_factory=dict)
    artigos: List[ParsedCurrentArtigo] = field(default_factory=list)
    propostas: List[ParsedCurrentProposta] = field(default_factory=list)
    diplomas: List[ParsedCurrentDiploma] = field(default_factory=list)
    iniciativas: List[ParsedCurrentIniciativa] = field(default_factory=list)
    votacoes: List[ParsedCurrentVotacao] = field(default_factory=list)
    requerimentos: List[ParsedCurrentRequerimento] = field(default_factory=list)
    db_obj: Any = None


class OrcamentoEstadoMapper(SchemaMapper):
    """
    Schema mapper for State Budget files

    Processes both legacy OEPropostasAlteracao and current OE XML structures
    with comprehensive field mapping based on official specifications.

    Handles:
    - Legacy Format (X-XV Legislaturas): Amendment proposal workflow
    - Current Format (XVI+ Legislaturas): Budget item structure
    - Dual structure support with automatic detection
    - Complex nested data (proponents, voting, regional opinions)
    """

    def __init__(self, session, import_status_record=None):
        super().__init__(session, import_status_record=import_status_record)
        self.processed_proposals = 0
        self.processed_items = 0
        self.processed_proponents = 0
        self.processed_votes = 0
        self.processed_articles = 0
        self.processed_diplomas = 0
        self.processed_initiatives = 0

        # Caches for upsert pattern - avoid duplicate database queries
        self._proposal_cache = {}  # proposta_id -> OrcamentoEstadoPropostaAlteracao
        self._item_cache = {}  # item_id -> OrcamentoEstadoItem

    def get_expected_fields(self) -> Set[str]:
        """
        Define expected XML fields based on both O_E specifications.
        Covers legacy OEPropostasAlteracao and current OE structures.
        """
        return {
            # Legacy structure (OEPropostasAlteracao) - Complex amendment proposal workflow
            "PropostasDeAlteracao",
            "PropostasDeAlteracao.PropostaDeAlteracao",
            "PropostasDeAlteracao.PropostaDeAlteracao.ID",
            "PropostasDeAlteracao.PropostaDeAlteracao.Numero",
            "PropostasDeAlteracao.PropostaDeAlteracao.Data",
            "PropostasDeAlteracao.PropostaDeAlteracao.Titulo",
            "PropostasDeAlteracao.PropostaDeAlteracao.Tema",
            "PropostasDeAlteracao.PropostaDeAlteracao.Apresentada",
            "PropostasDeAlteracao.PropostaDeAlteracao.Incide",
            "PropostasDeAlteracao.PropostaDeAlteracao.Tipo",
            "PropostasDeAlteracao.PropostaDeAlteracao.Estado",
            "PropostasDeAlteracao.PropostaDeAlteracao.NumeroArtigoNovo",
            "PropostasDeAlteracao.PropostaDeAlteracao.Conteudo",
            "PropostasDeAlteracao.PropostaDeAlteracao.Ficheiro",
            "PropostasDeAlteracao.PropostaDeAlteracao.GrupoParlamentar_Partido",
            # Legacy nested structures
            "PropostasDeAlteracao.PropostaDeAlteracao.Proponentes",
            "PropostasDeAlteracao.PropostaDeAlteracao.Proponentes.Proponente",
            "PropostasDeAlteracao.PropostaDeAlteracao.Proponentes.Proponente.GP_Partido",
            "PropostasDeAlteracao.PropostaDeAlteracao.Proponentes.Proponente.Deputado",
            "PropostasDeAlteracao.PropostaDeAlteracao.PedidoParecerRAA",
            "PropostasDeAlteracao.PropostaDeAlteracao.PedidoParecerRAM",
            "PropostasDeAlteracao.PropostaDeAlteracao.SugeridoParecerRAA",
            "PropostasDeAlteracao.PropostaDeAlteracao.SugeridoParecerRAM",
            "PropostasDeAlteracao.PropostaDeAlteracao.ParecerDasRegioesAutonomas",
            "PropostasDeAlteracao.PropostaDeAlteracao.ParecerDasRegioesAutonomas.Parecer",
            "PropostasDeAlteracao.PropostaDeAlteracao.ParecerDasRegioesAutonomas.Parecer.TipoAssociacao",
            "PropostasDeAlteracao.PropostaDeAlteracao.ParecerDasRegioesAutonomas.Parecer.Titulo",
            "PropostasDeAlteracao.PropostaDeAlteracao.ParecerDasRegioesAutonomas.Parecer.Ficheiro",
            "PropostasDeAlteracao.PropostaDeAlteracao.Iniciativas_Artigos",
            "PropostasDeAlteracao.PropostaDeAlteracao.Iniciativas_Artigos.Iniciativa_Artigo",
            "PropostasDeAlteracao.PropostaDeAlteracao.Iniciativas_Artigos.Iniciativa_Artigo.Artigo",
            "PropostasDeAlteracao.PropostaDeAlteracao.Iniciativas_Artigos.Iniciativa_Artigo.Titulo",
            "PropostasDeAlteracao.PropostaDeAlteracao.Iniciativas_Artigos.Iniciativa_Artigo.Texto",
            "PropostasDeAlteracao.PropostaDeAlteracao.Iniciativas_Artigos.Iniciativa_Artigo.Estado",
            # Nested Numeros and Alineas structures within articles
            "PropostasDeAlteracao.PropostaDeAlteracao.Iniciativas_Artigos.Iniciativa_Artigo.Numeros",
            "PropostasDeAlteracao.PropostaDeAlteracao.Iniciativas_Artigos.Iniciativa_Artigo.Numeros.Numero",
            "PropostasDeAlteracao.PropostaDeAlteracao.Iniciativas_Artigos.Iniciativa_Artigo.Numeros.Titulo", 
            "PropostasDeAlteracao.PropostaDeAlteracao.Iniciativas_Artigos.Iniciativa_Artigo.Numeros.Texto",
            "PropostasDeAlteracao.PropostaDeAlteracao.Iniciativas_Artigos.Iniciativa_Artigo.Numeros.Estado",
            "PropostasDeAlteracao.PropostaDeAlteracao.Iniciativas_Artigos.Iniciativa_Artigo.Numeros.Alineas",
            "PropostasDeAlteracao.PropostaDeAlteracao.Iniciativas_Artigos.Iniciativa_Artigo.Numeros.Alineas.Alinea",
            "PropostasDeAlteracao.PropostaDeAlteracao.Iniciativas_Artigos.Iniciativa_Artigo.Numeros.Alineas.Titulo",
            "PropostasDeAlteracao.PropostaDeAlteracao.Iniciativas_Artigos.Iniciativa_Artigo.Numeros.Alineas.Texto",
            "PropostasDeAlteracao.PropostaDeAlteracao.Iniciativas_Artigos.Iniciativa_Artigo.Numeros.Alineas.Estado",
            "PropostasDeAlteracao.PropostaDeAlteracao.ProgramasMedidas",
            "PropostasDeAlteracao.PropostaDeAlteracao.ProgramasMedidas.Nome",
            "PropostasDeAlteracao.PropostaDeAlteracao.ProgramasMedidas.Descricao",
            "PropostasDeAlteracao.PropostaDeAlteracao.DiplomasMedidas",
            "PropostasDeAlteracao.PropostaDeAlteracao.DiplomasMedidas.DiplomaMedida",
            "PropostasDeAlteracao.PropostaDeAlteracao.DiplomasMedidas.DiplomaMedida.Titulo",
            "PropostasDeAlteracao.PropostaDeAlteracao.DiplomasMedidas.DiplomaMedida.NumerosMedidas",
            "PropostasDeAlteracao.PropostaDeAlteracao.DiplomasMedidas.DiplomaMedida.NumerosMedidas.NumeroMedida",
            "PropostasDeAlteracao.PropostaDeAlteracao.DiplomasMedidas.DiplomaMedida.NumerosMedidas.NumeroMedida.Designacao",
            "PropostasDeAlteracao.PropostaDeAlteracao.DiplomasMedidas.DiplomaMedida.Texto",
            "PropostasDeAlteracao.PropostaDeAlteracao.Requerimentos",
            "PropostasDeAlteracao.PropostaDeAlteracao.Requerimentos.Requerimento",
            "PropostasDeAlteracao.PropostaDeAlteracao.Requerimentos.Requerimento.Data",
            "PropostasDeAlteracao.PropostaDeAlteracao.Requerimentos.Requerimento.Titulo",
            "PropostasDeAlteracao.PropostaDeAlteracao.Requerimentos.Requerimento.Observacoes",
            "PropostasDeAlteracao.PropostaDeAlteracao.Requerimentos.Requerimento.Aprovado",
            "PropostasDeAlteracao.PropostaDeAlteracao.Requerimentos.Requerimento.Ficheiro",
            "PropostasDeAlteracao.PropostaDeAlteracao.Ministerio",
            "PropostasDeAlteracao.PropostaDeAlteracao.Medidas_Programas",
            "PropostasDeAlteracao.PropostaDeAlteracao.Medidas_Programas.Descricao",
            "PropostasDeAlteracao.PropostaDeAlteracao.Medidas_Programas.SubDescricao",
            "PropostasDeAlteracao.PropostaDeAlteracao.NUTS",
            "PropostasDeAlteracao.PropostaDeAlteracao.NUTS.Descricao",
            "PropostasDeAlteracao.PropostaDeAlteracao.Votacoes",
            "PropostasDeAlteracao.PropostaDeAlteracao.Votacoes.Votacao",
            "PropostasDeAlteracao.PropostaDeAlteracao.Votacoes.Votacao.Descricoes",
            "PropostasDeAlteracao.PropostaDeAlteracao.Votacoes.Votacao.Descricoes.Descricao",
            "PropostasDeAlteracao.PropostaDeAlteracao.Votacoes.Votacao.DiplomasTerceirosouPropostasDeLeiMapas",
            "PropostasDeAlteracao.PropostaDeAlteracao.Votacoes.Votacao.DiplomasTerceirosouPropostasDeLeiMapas.Diploma",
            "PropostasDeAlteracao.PropostaDeAlteracao.Votacoes.Votacao.SubDescricao",
            "PropostasDeAlteracao.PropostaDeAlteracao.Votacoes.Votacao.Data",
            "PropostasDeAlteracao.PropostaDeAlteracao.Votacoes.Votacao.ResultadoCompleto",
            "PropostasDeAlteracao.PropostaDeAlteracao.Votacoes.Votacao.Resultado",
            "PropostasDeAlteracao.PropostaDeAlteracao.Votacoes.Votacao.GruposParlamentares",
            "PropostasDeAlteracao.PropostaDeAlteracao.Votacoes.Votacao.GruposParlamentares.GrupoParlamentar",
            "PropostasDeAlteracao.PropostaDeAlteracao.Votacoes.Votacao.GruposParlamentares.Voto",
            # Root wrapper structure
            "Itens",
            "Itens.Item",
            "Itens.Item.ID",
            "Itens.Item.ID_Pai",
            "Itens.Item.Tipo",
            "Itens.Item.Numero",
            "Itens.Item.Titulo",
            "Itens.Item.Texto",
            "Itens.Item.Estado",
            # Itens wrapper nested structures
            "Itens.Item.Artigos",
            "Itens.Item.Artigos.Artigo",
            "Itens.Item.Artigos.Artigo.ID_Art",
            "Itens.Item.Artigos.Artigo.ID_Pai",
            "Itens.Item.Artigos.Artigo.Tipo",
            "Itens.Item.Artigos.Artigo.Numero",
            "Itens.Item.Artigos.Artigo.Titulo",
            "Itens.Item.Artigos.Artigo.Texto",
            "Itens.Item.Artigos.Artigo.Estado",
            "Itens.Item.PropostasDeAlteracao",
            "Itens.Item.PropostasDeAlteracao.Proposta",
            "Itens.Item.PropostasDeAlteracao.Proposta.ID_Pai",
            "Itens.Item.PropostasDeAlteracao.Proposta.ID_PA",
            "Itens.Item.PropostasDeAlteracao.Proposta.Objeto",
            "Itens.Item.PropostasDeAlteracao.Proposta.Data",
            "Itens.Item.PropostasDeAlteracao.Proposta.Apresentado",
            "Itens.Item.PropostasDeAlteracao.Proposta.Incide",
            "Itens.Item.PropostasDeAlteracao.Proposta.Tipo",
            "Itens.Item.PropostasDeAlteracao.Proposta.Estado",
            "Itens.Item.PropostasDeAlteracao.Proposta.Ficheiro",
            "Itens.Item.DiplomasaModificar",
            "Itens.Item.DiplomasaModificar.DiplomaModificar",
            "Itens.Item.DiplomasaModificar.DiplomaaModificar",
            "Itens.Item.DiplomasaModificar.DiplomaaModificar.TextoOuEstado",
            "Itens.Item.DiplomasaModificar.DiplomaaModificar.ID_Dip",
            "Itens.Item.DiplomasaModificar.DiplomaaModificar.DiplomaTitulo",
            "Itens.Item.DiplomasaModificar.DiplomaaModificar.DiplomaSubTitulo",
            "Itens.Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos",
            "Itens.Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo",
            "Itens.Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo.ID_Art",
            "Itens.Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo.Numero",
            "Itens.Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo.Titulo",
            "Itens.Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo.Texto",
            "Itens.Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo.Estado",
            "Itens.Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaArtigoEstado",
            "Itens.Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaArtigoID",
            "Itens.Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaArtigoTituto",
            "Itens.Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaArtigoSubTitulo",
            "Itens.Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaArtigoTexto",
            "Itens.Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaNumeros",
            "Itens.Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaNumeros.DiplomaNumero",
            "Itens.Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaNumeros.DiplomaNumero.DiplomaNumeroTitulo",
            "Itens.Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaNumeros.DiplomaNumero.DiplomaNumeroEstado",
            "Itens.Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaNumeros.DiplomaNumero.DiplomaNumeroID",
            "Itens.Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaNumeros.DiplomaNumero.DiplomaAlineas",
            "Itens.Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaNumeros.DiplomaNumero.DiplomaAlineas.DiplomaAlinea",
            "Itens.Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaNumeros.DiplomaNumero.DiplomaAlineas.DiplomaAlinea.DiplomaAlineaTitulo",
            "Itens.Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaNumeros.DiplomaNumero.DiplomaAlineas.DiplomaAlinea.DiplomaAlineaEstado",
            "Itens.Item.DiplomasaModificar.DiplomaModificar.ID_Dip",
            "Itens.Item.DiplomasaModificar.DiplomaModificar.DiplomaTitulo",
            "Itens.Item.DiplomasaModificar.DiplomaModificar.DiplomaSubTitulo",
            "Itens.Item.DiplomasaModificar.DiplomaModificar.DiplomasArtigos",
            "Itens.Item.DiplomasaModificar.DiplomaModificar.DiplomasArtigos.DiplomaArtigo",
            "Itens.Item.DiplomasaModificar.DiplomaModificar.DiplomasArtigos.DiplomaArtigo.ID_Art",
            "Itens.Item.DiplomasaModificar.DiplomaModificar.DiplomasArtigos.DiplomaArtigo.Numero",
            "Itens.Item.DiplomasaModificar.DiplomaModificar.DiplomasArtigos.DiplomaArtigo.Titulo",
            "Itens.Item.DiplomasaModificar.DiplomaModificar.DiplomasArtigos.DiplomaArtigo.Texto",
            "Itens.Item.DiplomasaModificar.DiplomaModificar.DiplomasArtigos.DiplomaArtigo.Estado",
            "Itens.Item.DiplomasaModificar.DiplomaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaNumeros",
            "Itens.Item.DiplomasaModificar.DiplomaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaNumeros.DiplomaNumero",
            "Itens.Item.DiplomasaModificar.DiplomaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaNumeros.DiplomaNumero.DiplomaNumeroTitulo",
            "Itens.Item.DiplomasaModificar.DiplomaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaNumeros.DiplomaNumero.DiplomaNumeroEstado",
            "Itens.Item.DiplomasaModificar.DiplomaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaNumeros.DiplomaNumero.DiplomaAlineas",
            "Itens.Item.DiplomasaModificar.DiplomaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaNumeros.DiplomaNumero.DiplomaAlineas.DiplomaAlinea",
            "Itens.Item.DiplomasaModificar.DiplomaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaNumeros.DiplomaNumero.DiplomaAlineas.DiplomaAlinea.DiplomaAlineaTitulo",
            "Itens.Item.IniciativasMapas",
            "Itens.Item.IniciativasMapas.IniciativaMapa",
            "Itens.Item.IniciativasMapas.IniciativaMapa.MapasNumero",
            "Itens.Item.IniciativasMapas.IniciativaMapa.MapasTitulo",
            "Itens.Item.IniciativasMapas.IniciativaMapa.MapasEstado",
            "Itens.Item.IniciativasMapas.IniciativaMapa.MapasLink",
            "Itens.Item.Votacoes",
            "Itens.Item.Votacoes.Votacao",
            "Itens.Item.Votacoes.Votacao.Descricoes",
            "Itens.Item.Votacoes.Votacao.Descricoes.Descricao",
            "Itens.Item.Votacoes.Votacao.DiplomasTerceiros",
            "Itens.Item.Votacoes.Votacao.DiplomasTerceirosouPropostasDeLeiMapas",
            "Itens.Item.Votacoes.Votacao.DiplomasTerceirosouPropostasDeLeiMapas.Diploma",
            "Itens.Item.Votacoes.Votacao.Data",
            "Itens.Item.Votacoes.Votacao.Resultado",
            "Itens.Item.Votacoes.Votacao.ResultadoCompleto",
            "Itens.Item.Votacoes.Votacao.SubDescricao",
            "Itens.Item.Votacoes.Votacao.GruposParlamentares",
            "Itens.Item.Votacoes.Votacao.GruposParlamentares.GrupoParlamentar",
            "Itens.Item.Votacoes.Votacao.GruposParlamentares.Voto",
            "Itens.Item.RequerimentosDeAvocacao",
            "Itens.Item.RequerimentosDeAvocacao.RequerimentoDeAvocacao",
            "Itens.Item.RequerimentosDeAvocacao.RequerimentoDeAvocacao.AvocacaoDescricao",
            "Itens.Item.RequerimentosDeAvocacao.RequerimentoDeAvocacao.AvocacaoData",
            "Itens.Item.RequerimentosDeAvocacao.RequerimentoDeAvocacao.AvocacaoTitulo",
            "Itens.Item.RequerimentosDeAvocacao.RequerimentoDeAvocacao.AvocacaoEstado",
            "Itens.Item.RequerimentosDeAvocacao.RequerimentoDeAvocacao.AvocacaoFicheiro",
            # Current structure (OE) - Simplified budget item structure
            "Item",
            "Item.ID",
            "Item.ID_Pai",
            "Item.Tipo",
            "Item.Numero",
            "Item.Titulo",
            "Item.Texto",
            "Item.Estado",
            "Item.Artigos",
            "Item.Artigos.Artigo",
            "Item.Artigos.Artigo.ID_Art",
            "Item.Artigos.Artigo.ID_Pai",
            "Item.Artigos.Artigo.Tipo",
            "Item.Artigos.Artigo.Numero",
            "Item.Artigos.Artigo.Titulo",
            "Item.Artigos.Artigo.Texto",
            "Item.Artigos.Artigo.Estado",
            "Item.PropostasDeAlteracao",
            "Item.PropostasDeAlteracao.Proposta",
            "Item.PropostasDeAlteracao.Proposta.ID_Pai",
            "Item.PropostasDeAlteracao.Proposta.ID_PA",
            "Item.PropostasDeAlteracao.Proposta.Objeto",
            "Item.PropostasDeAlteracao.Proposta.Data",
            "Item.PropostasDeAlteracao.Proposta.Apresentado",
            "Item.PropostasDeAlteracao.Proposta.Incide",
            "Item.PropostasDeAlteracao.Proposta.Tipo",
            "Item.PropostasDeAlteracao.Proposta.Estado",
            "Item.PropostasDeAlteracao.Proposta.Ficheiro",
            "Item.DiplomasaModificar",
            "Item.DiplomasaModificar.DiplomaModificar",
            "Item.DiplomasaModificar.DiplomaaModificar",
            "Item.DiplomasaModificar.DiplomaaModificar.TextoOuEstado",
            "Item.DiplomasaModificar.DiplomaaModificar.ID_Dip",
            "Item.DiplomasaModificar.DiplomaaModificar.DiplomaTitulo",
            "Item.DiplomasaModificar.DiplomaaModificar.DiplomaSubTitulo",
            "Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos",
            "Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo",
            "Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo.ID_Art",
            "Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo.Numero",
            "Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo.Titulo",
            "Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo.Texto",
            "Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo.Estado",
            "Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaNumeros",
            "Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaNumeros.DiplomaNumero",
            "Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaNumeros.DiplomaNumero.DiplomaNumeroTitulo",
            "Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaNumeros.DiplomaNumero.DiplomaNumeroEstado",
            "Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaNumeros.DiplomaNumero.DiplomaAlineas",
            "Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaNumeros.DiplomaNumero.DiplomaAlineas.DiplomaAlinea",
            "Item.DiplomasaModificar.DiplomaaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaNumeros.DiplomaNumero.DiplomaAlineas.DiplomaAlinea.DiplomaAlineaTitulo",
            "Item.DiplomasaModificar.DiplomaModificar.ID_Dip",
            "Item.DiplomasaModificar.DiplomaModificar.DiplomaTitulo",
            "Item.DiplomasaModificar.DiplomaModificar.DiplomaSubTitulo",
            "Item.DiplomasaModificar.DiplomaModificar.DiplomasArtigos",
            "Item.DiplomasaModificar.DiplomaModificar.DiplomasArtigos.DiplomaArtigo",
            "Item.DiplomasaModificar.DiplomaModificar.DiplomasArtigos.DiplomaArtigo.ID_Art",
            "Item.DiplomasaModificar.DiplomaModificar.DiplomasArtigos.DiplomaArtigo.Numero",
            "Item.DiplomasaModificar.DiplomaModificar.DiplomasArtigos.DiplomaArtigo.Titulo",
            "Item.DiplomasaModificar.DiplomaModificar.DiplomasArtigos.DiplomaArtigo.Texto",
            "Item.DiplomasaModificar.DiplomaModificar.DiplomasArtigos.DiplomaArtigo.Estado",
            "Item.DiplomasaModificar.DiplomaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaNumeros",
            "Item.DiplomasaModificar.DiplomaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaNumeros.DiplomaNumero",
            "Item.DiplomasaModificar.DiplomaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaNumeros.DiplomaNumero.DiplomaNumeroTitulo",
            "Item.DiplomasaModificar.DiplomaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaNumeros.DiplomaNumero.DiplomaNumeroEstado",
            "Item.DiplomasaModificar.DiplomaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaNumeros.DiplomaNumero.DiplomaAlineas",
            "Item.DiplomasaModificar.DiplomaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaNumeros.DiplomaNumero.DiplomaAlineas.DiplomaAlinea",
            "Item.DiplomasaModificar.DiplomaModificar.DiplomasArtigos.DiplomaArtigo.DiplomaNumeros.DiplomaNumero.DiplomaAlineas.DiplomaAlinea.DiplomaAlineaTitulo",
            "Item.IniciativasMapas",
            "Item.IniciativasMapas.IniciativaMapa",
            "Item.IniciativasMapas.IniciativaMapa.MapasNumero",
            "Item.IniciativasMapas.IniciativaMapa.MapasTitulo",
            "Item.IniciativasMapas.IniciativaMapa.MapasEstado",
            "Item.IniciativasMapas.IniciativaMapa.MapasLink",
            "Item.Votacoes",
            "Item.Votacoes.Votacao",
            "Item.Votacoes.Votacao.Descricoes",
            "Item.Votacoes.Votacao.Descricoes.Descricao",
            "Item.Votacoes.Votacao.DiplomasTerceiros",
            "Item.Votacoes.Votacao.DiplomasTerceirosouPropostasDeLeiMapas",
            "Item.Votacoes.Votacao.Data",
            "Item.Votacoes.Votacao.Resultado",
            "Item.RequerimentosDeAvocacao",
            "Item.RequerimentosDeAvocacao.RequerimentoDeAvocacao",
            "Item.RequerimentosDeAvocacao.RequerimentoDeAvocacao.AvocacaoDescricao",
            "Item.RequerimentosDeAvocacao.RequerimentoDeAvocacao.AvocacaoData",
            "Item.RequerimentosDeAvocacao.RequerimentoDeAvocacao.AvocacaoTitulo",
            "Item.RequerimentosDeAvocacao.RequerimentoDeAvocacao.AvocacaoEstado",
            "Item.RequerimentosDeAvocacao.RequerimentoDeAvocacao.AvocacaoFicheiro",
        }

    def validate_and_map(
        self, xml_root: ET.Element, file_info: Dict, strict_mode: bool = False
    ) -> Dict:
        """
        Map State Budget data to database with level-by-level batched processing.

        Uses batched database operations to minimize flush calls:

        Legacy Format (OEPropostasAlteracao):
        - Phase 1: Parse all proposals into memory
        - Phase 2: Batch create proposals (1 flush)
        - Phase 3: Batch create proponentes, votacoes (leaf records)
        - Phase 4: Batch create artigos (1 flush)
        - Phase 5: Batch create numeros (1 flush)
        - Phase 6: Batch create alineas (leaf)

        Current Format (OE):
        - Phase 1: Parse all items into memory
        - Phase 2: Batch create items (1 flush)
        - Phase 3: Batch create leaf records (artigos, propostas, iniciativas, votacoes, requerimentos)
        - Phase 4: Batch create diplomas (1 flush)
        - Phase 5: Batch create diploma_artigos (1 flush)
        - Phase 6: Batch create diploma_numeros (1 flush)
        - Phase 7: Batch create diploma_alineas (leaf)

        This reduces potentially thousands of flushes to ~6-7 flushes per file.

        Args:
            xml_root: Root XML element
            file_info: Dictionary containing file metadata
            strict_mode: Whether to exit on unmapped fields

        Returns:
            Dictionary with processing results
        """
        # Store for use in nested methods
        self.file_info = file_info

        results = {"records_processed": 0, "records_imported": 0, "errors": []}
        file_path = file_info["file_path"]
        filename = os.path.basename(file_path)

        try:
            logger.info(f"Processing Orçamento do Estado file: {file_path}")

            # Validate schema coverage according to strict mode
            self.validate_schema_coverage(xml_root, file_info, strict_mode)

            # Extract legislatura - prioritize ImportStatus data, then path fallback
            legislatura = None

            # First try: Use legislature data from ImportStatus (most reliable)
            if 'legislatura' in file_info and file_info['legislatura']:
                legislatura_sigla = file_info['legislatura']
                logger.debug(f"Using legislature from ImportStatus: {legislatura_sigla}")

                # Get or create legislatura using the enhanced base mapper method
                legislatura = self._get_or_create_legislatura(legislatura_sigla)

            # Fallback: Extract from filename or path (legacy behavior)
            if not legislatura:
                logger.debug("No legislature in ImportStatus, falling back to path extraction")
                legislatura = self._extract_legislatura_from_path(file_path)

            # Determine format type based on root element and filename
            format_type = self._detect_format_type(xml_root, filename)
            logger.info(f"Detected format type: {format_type} for file {filename}")

            if format_type == "legacy":
                results = self._process_legacy_format_batched(
                    xml_root, legislatura, filename, results, strict_mode
                )

            elif format_type == "current":
                results = self._process_current_format_batched(
                    xml_root, legislatura, filename, results, strict_mode
                )
            else:
                error_msg = f"Unknown format type detected for {filename}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
                return results

            logger.info(f"Successfully processed Orçamento do Estado file: {file_path}")
            logger.info(
                f"Statistics: {self.processed_proposals} proposals (legacy), "
                f"{self.processed_items} items (current), {self.processed_proponents} proponents, "
                f"{self.processed_votes} votes, {self.processed_articles} articles, "
                f"{self.processed_diplomas} diplomas, {self.processed_initiatives} initiatives"
            )

            return results

        except Exception as e:
            error_msg = f"Critical error processing Orçamento do Estado: {str(e)}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
            if strict_mode:
                raise
            return results

    # =========================================================================
    # Legacy Format Batched Processing
    # =========================================================================

    def _process_legacy_format_batched(
        self,
        xml_root: ET.Element,
        legislatura: Legislatura,
        filename: str,
        results: Dict,
        strict_mode: bool,
    ) -> Dict:
        """
        Process legacy OEPropostasAlteracao format with batched database operations.

        Reduces flushes from O(proposals * artigos * numeros) to ~4 flushes total.
        """
        proposal_elements = xml_root.findall(".//PropostaDeAlteracao")
        logger.info(f"Found {len(proposal_elements)} amendment proposals in legacy format")

        # Phase 1: Parse all proposals into memory
        parsed_proposals: List[ParsedLegacyProposal] = []
        for proposta_elem in proposal_elements:
            try:
                parsed = self._parse_legacy_proposal(proposta_elem)
                if parsed:
                    parsed_proposals.append(parsed)
                    results["records_processed"] += 1
            except Exception as e:
                error_msg = f"Legacy proposal parsing error in {filename}: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
                if strict_mode:
                    raise

        # Phase 2: Batch create proposals (1 flush)
        # Flush session first to ensure legislatura is in database for raw SQL upsert
        self.session.flush()
        for parsed in parsed_proposals:
            self._create_legacy_proposal_record(parsed, legislatura)
        logger.debug(f"Created {len(parsed_proposals)} proposal records")

        # Phase 3: Batch create proponentes and votacoes (leaf records, no flush needed)
        for parsed in parsed_proposals:
            self._create_legacy_proponentes(parsed)
            self._create_legacy_votacoes(parsed)

        # Phase 4: Batch create artigos (1 flush)
        all_artigos: List[ParsedLegacyArtigo] = []
        for parsed in parsed_proposals:
            all_artigos.extend(parsed.artigos)

        for artigo in all_artigos:
            self._create_legacy_artigo_record(artigo)
        if all_artigos:
            # No flush needed - UUID ids are generated client-side
            logger.debug(f"Created {len(all_artigos)} artigo records")

        # Phase 5: Batch create numeros (1 flush)
        all_numeros: List[ParsedLegacyNumero] = []
        for artigo in all_artigos:
            all_numeros.extend(artigo.numeros)

        for numero in all_numeros:
            self._create_legacy_numero_record(numero)
        if all_numeros:
            # No flush needed - UUID ids are generated client-side
            logger.debug(f"Created {len(all_numeros)} numero records")

        # Phase 6: Batch create alineas (leaf records, no flush needed)
        all_alineas: List[ParsedLegacyAlinea] = []
        for numero in all_numeros:
            all_alineas.extend(numero.alineas)

        for alinea in all_alineas:
            self._create_legacy_alinea_record(alinea)
        logger.debug(f"Created {len(all_alineas)} alinea records")

        results["records_imported"] = len(parsed_proposals)
        self.processed_proposals += len(parsed_proposals)

        return results

    def _parse_legacy_proposal(self, proposta: ET.Element) -> Optional[ParsedLegacyProposal]:
        """Parse a legacy proposal element into memory structure."""
        proposal_id = DataValidationUtils.safe_float_convert(
            self._get_text_value(proposta, "ID")
        )

        if not proposal_id:
            logger.warning("Legacy proposal missing ID, skipping")
            return None

        data_str = self._get_text_value(proposta, "Data")
        data_proposta = None
        if data_str:
            data_proposta = DataValidationUtils.parse_date_flexible(data_str)

        parsed = ParsedLegacyProposal(
            xml_element=proposta,
            proposal_id=int(proposal_id),
            data={
                "numero": self._get_text_value(proposta, "Numero"),
                "data_proposta": data_proposta,
                "titulo": self._get_text_value(proposta, "Titulo"),
                "tema": self._get_text_value(proposta, "Tema"),
                "apresentada": self._get_text_value(proposta, "Apresentada"),
                "incide": self._get_text_value(proposta, "Incide"),
                "tipo": self._get_text_value(proposta, "Tipo"),
                "estado": self._get_text_value(proposta, "Estado"),
                "numero_artigo_novo": self._get_text_value(proposta, "NumeroArtigoNovo"),
                "conteudo": self._get_text_value(proposta, "Conteudo"),
                "ficheiro": self._get_text_value(proposta, "Ficheiro"),
                "grupo_parlamentar": self._get_text_value(proposta, "GrupoParlamentar_Partido"),
            }
        )

        # Parse proponentes
        proponentes_elem = proposta.find("Proponentes")
        if proponentes_elem is not None:
            for proponente_elem in proponentes_elem.findall("Proponente"):
                gp_partido = self._get_text_value(proponente_elem, "GP_Partido")
                deputado = self._get_text_value(proponente_elem, "Deputado")
                if gp_partido or deputado:
                    parsed.proponentes.append(ParsedLegacyProponente(
                        xml_element=proponente_elem,
                        proposal_ref=parsed,
                        data={"gp_partido": gp_partido, "deputado": deputado}
                    ))

        # Parse votacoes
        votacoes_elem = proposta.find("Votacoes")
        if votacoes_elem is not None:
            for votacao_elem in votacoes_elem.findall("Votacao"):
                parsed.votacoes.append(self._parse_legacy_votacao(votacao_elem, parsed))

        # Parse artigos
        artigos_elem = proposta.find("Iniciativas_Artigos")
        if artigos_elem is not None:
            for artigo_elem in artigos_elem.findall("Iniciativa_Artigo"):
                parsed.artigos.append(self._parse_legacy_artigo(artigo_elem, parsed))

        return parsed

    def _parse_legacy_votacao(
        self, votacao_elem: ET.Element, proposal_ref: ParsedLegacyProposal
    ) -> ParsedLegacyVotacao:
        """Parse a legacy votacao element."""
        data_str = self._get_text_value(votacao_elem, "Data")

        # Process multiple Descricao elements within Descricoes
        descricoes_list = []
        descricoes_elem = votacao_elem.find("Descricoes")
        if descricoes_elem is not None:
            for desc_elem in descricoes_elem.findall("Descricao"):
                desc_text = desc_elem.text
                if desc_text and desc_text.strip():
                    descricoes_list.append(desc_text.strip())

        descricoes = "; ".join(descricoes_list) if descricoes_list else None

        resultado = self._get_text_value(votacao_elem, "ResultadoCompleto")
        if not resultado:
            resultado = self._get_text_value(votacao_elem, "Resultado")

        return ParsedLegacyVotacao(
            xml_element=votacao_elem,
            proposal_ref=proposal_ref,
            data={
                "data_votacao": DataValidationUtils.parse_date_flexible(data_str) if data_str else None,
                "descricao": descricoes,
                "sub_descricao": self._get_text_value(votacao_elem, "SubDescricao"),
                "resultado": resultado,
                "diplomas_terceiros": self._get_text_value(votacao_elem, "DiplomasTerceiros"),
                "grupos_parlamentares": self._get_text_value(votacao_elem, "GruposParlamentares"),
            }
        )

    def _parse_legacy_artigo(
        self, artigo_elem: ET.Element, proposal_ref: ParsedLegacyProposal
    ) -> ParsedLegacyArtigo:
        """Parse a legacy artigo element with nested numeros."""
        parsed = ParsedLegacyArtigo(
            xml_element=artigo_elem,
            proposal_ref=proposal_ref,
            data={
                "numero": self._get_text_value(artigo_elem, "Artigo"),
                "titulo": self._get_text_value(artigo_elem, "Titulo"),
                "texto": self._get_text_value(artigo_elem, "Texto"),
                "estado": self._get_text_value(artigo_elem, "Estado"),
            }
        )

        # Parse nested numeros
        numeros_elem = artigo_elem.find("Numeros")
        if numeros_elem is not None:
            for numero_elem in numeros_elem.findall("Numero"):
                parsed.numeros.append(self._parse_legacy_numero(numero_elem, parsed))

        return parsed

    def _parse_legacy_numero(
        self, numero_elem: ET.Element, artigo_ref: ParsedLegacyArtigo
    ) -> ParsedLegacyNumero:
        """Parse a legacy numero element with nested alineas."""
        parsed = ParsedLegacyNumero(
            xml_element=numero_elem,
            artigo_ref=artigo_ref,
            data={
                "numero": self._get_text_value(numero_elem, "Numero"),
                "titulo": self._get_text_value(numero_elem, "Titulo"),
                "texto": self._get_text_value(numero_elem, "Texto"),
                "estado": self._get_text_value(numero_elem, "Estado"),
            }
        )

        # Parse nested alineas
        alineas_elem = numero_elem.find("Alineas")
        if alineas_elem is not None:
            for alinea_elem in alineas_elem.findall("Alinea"):
                parsed.alineas.append(ParsedLegacyAlinea(
                    xml_element=alinea_elem,
                    numero_ref=parsed,  # Set reference to parent numero
                    data={
                        "alinea": self._get_text_value(alinea_elem, "Alinea"),
                        "titulo": self._get_text_value(alinea_elem, "Titulo"),
                        "texto": self._get_text_value(alinea_elem, "Texto"),
                        "estado": self._get_text_value(alinea_elem, "Estado"),
                    }
                ))

        return parsed

    def _create_legacy_proposal_record(
        self, parsed: ParsedLegacyProposal, legislatura: Legislatura
    ):
        """Create or update a proposal database record using upsert for parallel safety."""
        # Check cache first
        existing = self._proposal_cache.get(parsed.proposal_id)

        if not existing:
            # Check database
            existing = (
                self.session.query(OrcamentoEstadoPropostaAlteracao)
                .filter_by(proposta_id=parsed.proposal_id)
                .first()
            )
            if existing:
                self._proposal_cache[parsed.proposal_id] = existing

        if existing:
            existing.numero = parsed.data["numero"]
            existing.data_proposta = parsed.data["data_proposta"]
            existing.titulo = parsed.data["titulo"]
            existing.tema = parsed.data["tema"]
            existing.apresentada = parsed.data["apresentada"]
            existing.incide = parsed.data["incide"]
            existing.tipo = parsed.data["tipo"]
            existing.estado = parsed.data["estado"]
            existing.numero_artigo_novo = parsed.data["numero_artigo_novo"]
            existing.conteudo = parsed.data["conteudo"]
            existing.ficheiro_url = parsed.data["ficheiro"]
            existing.grupo_parlamentar = parsed.data["grupo_parlamentar"]
            existing.legislatura_id = legislatura.id
            parsed.db_obj = existing
        else:
            # Use upsert for parallel-safe insert (handles race conditions)
            new_id = uuid.uuid4()
            stmt = pg_insert(OrcamentoEstadoPropostaAlteracao).values(
                id=new_id,
                proposta_id=parsed.proposal_id,
                numero=parsed.data["numero"],
                data_proposta=parsed.data["data_proposta"],
                titulo=parsed.data["titulo"],
                tema=parsed.data["tema"],
                apresentada=parsed.data["apresentada"],
                incide=parsed.data["incide"],
                tipo=parsed.data["tipo"],
                estado=parsed.data["estado"],
                numero_artigo_novo=parsed.data["numero_artigo_novo"],
                conteudo=parsed.data["conteudo"],
                ficheiro_url=parsed.data["ficheiro"],
                grupo_parlamentar=parsed.data["grupo_parlamentar"],
                legislatura_id=legislatura.id,
                format_type="legacy",
            ).on_conflict_do_update(
                index_elements=['proposta_id'],
                set_={
                    'numero': parsed.data["numero"],
                    'data_proposta': parsed.data["data_proposta"],
                    'titulo': parsed.data["titulo"],
                    'tema': parsed.data["tema"],
                    'apresentada': parsed.data["apresentada"],
                    'incide': parsed.data["incide"],
                    'tipo': parsed.data["tipo"],
                    'estado': parsed.data["estado"],
                    'numero_artigo_novo': parsed.data["numero_artigo_novo"],
                    'conteudo': parsed.data["conteudo"],
                    'ficheiro_url': parsed.data["ficheiro"],
                    'grupo_parlamentar': parsed.data["grupo_parlamentar"],
                    'legislatura_id': legislatura.id,
                }
            ).returning(OrcamentoEstadoPropostaAlteracao.id)

            result = self.session.execute(stmt)
            returned_id = result.scalar()

            # Get the inserted/updated record for relationships
            proposal_obj = self.session.query(OrcamentoEstadoPropostaAlteracao).filter_by(
                id=returned_id if returned_id else new_id
            ).first()
            if not proposal_obj:
                # Fallback to proposta_id lookup
                proposal_obj = self.session.query(OrcamentoEstadoPropostaAlteracao).filter_by(
                    proposta_id=parsed.proposal_id
                ).first()

            parsed.db_obj = proposal_obj
            self._proposal_cache[parsed.proposal_id] = proposal_obj

    def _create_legacy_proponentes(self, parsed: ParsedLegacyProposal):
        """Create proponente records for a proposal."""
        for proponente in parsed.proponentes:
            proponente_obj = OrcamentoEstadoProponente(
                id=uuid.uuid4(),
                proposta_id=parsed.db_obj.id,
                grupo_parlamentar=proponente.data["gp_partido"],
                deputado_nome=proponente.data["deputado"],
                tipo_proponente="deputado" if proponente.data["deputado"] else "grupo",
            )
            self._add_with_tracking(proponente_obj)
            self.processed_proponents += 1

    def _create_legacy_votacoes(self, parsed: ParsedLegacyProposal):
        """Create votacao records for a proposal."""
        for votacao in parsed.votacoes:
            votacao_obj = OrcamentoEstadoVotacao(
                id=uuid.uuid4(),
                proposta_id=parsed.db_obj.id,
                data_votacao=votacao.data["data_votacao"],
                descricao=votacao.data["descricao"],
                sub_descricao=votacao.data["sub_descricao"],
                resultado=votacao.data["resultado"],
                diplomas_terceiros_texto=votacao.data["diplomas_terceiros"],
                grupos_parlamentares_texto=votacao.data["grupos_parlamentares"],
            )
            self._add_with_tracking(votacao_obj)
            self.processed_votes += 1

    def _create_legacy_artigo_record(self, parsed: ParsedLegacyArtigo):
        """Create an artigo database record."""
        artigo_obj = OrcamentoEstadoArtigo(
            id=uuid.uuid4(),
            proposta_id=parsed.proposal_ref.db_obj.id,
            numero=parsed.data["numero"],
            titulo=parsed.data["titulo"],
            texto=parsed.data["texto"],
            estado=parsed.data["estado"],
        )
        self._add_with_tracking(artigo_obj)
        parsed.db_obj = artigo_obj
        self.processed_articles += 1

    def _create_legacy_numero_record(self, parsed: ParsedLegacyNumero):
        """Create a numero database record."""
        numero_obj = OrcamentoEstadoArtigoNumero(
            id=uuid.uuid4(),
            artigo_id=parsed.artigo_ref.db_obj.id,
            numero=parsed.data["numero"],
            titulo=parsed.data["titulo"],
            texto=parsed.data["texto"],
            estado=parsed.data["estado"],
        )
        self._add_with_tracking(numero_obj)
        parsed.db_obj = numero_obj

    def _create_legacy_alinea_record(self, parsed: ParsedLegacyAlinea):
        """Create an alinea database record."""
        alinea_obj = OrcamentoEstadoArtigoAlinea(
            id=uuid.uuid4(),
            numero_id=parsed.numero_ref.db_obj.id,
            alinea=parsed.data["alinea"],
            titulo=parsed.data["titulo"],
            texto=parsed.data["texto"],
            estado=parsed.data["estado"],
        )
        self._add_with_tracking(alinea_obj)

    # =========================================================================
    # Current Format Batched Processing
    # =========================================================================

    def _process_current_format_batched(
        self,
        xml_root: ET.Element,
        legislatura: Legislatura,
        filename: str,
        results: Dict,
        strict_mode: bool,
    ) -> Dict:
        """
        Process current OE format with batched database operations.

        Reduces flushes from O(items * diplomas * artigos * numeros) to ~5 flushes total.
        """
        item_elements = xml_root.findall(".//Item")
        logger.info(f"Found {len(item_elements)} budget items in current format")

        # Phase 1: Parse all items into memory
        parsed_items: List[ParsedCurrentItem] = []
        for item_elem in item_elements:
            try:
                parsed = self._parse_current_item(item_elem)
                if parsed:
                    parsed_items.append(parsed)
                    results["records_processed"] += 1
            except Exception as e:
                error_msg = f"Current item parsing error in {filename}: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
                if strict_mode:
                    raise

        # Phase 2: Batch create items (1 flush)
        # Flush session first to ensure legislatura is in database for raw SQL upsert
        self.session.flush()
        for parsed in parsed_items:
            self._create_current_item_record(parsed, legislatura)
        logger.debug(f"Created {len(parsed_items)} item records")

        # Phase 3: Batch create leaf records (no flush needed)
        for parsed in parsed_items:
            self._create_current_artigos(parsed)
            self._create_current_propostas(parsed, legislatura)
            self._create_current_iniciativas(parsed)
            self._create_current_votacoes(parsed)
            self._create_current_requerimentos(parsed)

        # Phase 4: Batch create diplomas (1 flush)
        all_diplomas: List[ParsedCurrentDiploma] = []
        for parsed in parsed_items:
            all_diplomas.extend(parsed.diplomas)

        for diploma in all_diplomas:
            self._create_current_diploma_record(diploma)
        if all_diplomas:
            # No flush needed - UUID ids are generated client-side
            logger.debug(f"Created {len(all_diplomas)} diploma records")

        # Phase 5: Batch create diploma_artigos (1 flush)
        all_diploma_artigos: List[ParsedCurrentDiplomaArtigo] = []
        for diploma in all_diplomas:
            all_diploma_artigos.extend(diploma.artigos)

        for artigo in all_diploma_artigos:
            self._create_current_diploma_artigo_record(artigo)
        if all_diploma_artigos:
            # No flush needed - UUID ids are generated client-side
            logger.debug(f"Created {len(all_diploma_artigos)} diploma artigo records")

        # Phase 6: Batch create diploma_numeros (1 flush)
        all_diploma_numeros: List[ParsedCurrentDiplomaNumero] = []
        for artigo in all_diploma_artigos:
            all_diploma_numeros.extend(artigo.numeros)

        for numero in all_diploma_numeros:
            self._create_current_diploma_numero_record(numero)
        if all_diploma_numeros:
            # No flush needed - UUID ids are generated client-side
            logger.debug(f"Created {len(all_diploma_numeros)} diploma numero records")

        # Phase 7: Batch create diploma_alineas (leaf records, no flush needed)
        all_diploma_alineas: List[ParsedCurrentDiplomaAlinea] = []
        for numero in all_diploma_numeros:
            all_diploma_alineas.extend(numero.alineas)

        for alinea in all_diploma_alineas:
            self._create_current_diploma_alinea_record(alinea)
        logger.debug(f"Created {len(all_diploma_alineas)} diploma alinea records")

        results["records_imported"] = len(parsed_items)
        self.processed_items += len(parsed_items)

        return results

    def _parse_current_item(self, item: ET.Element) -> Optional[ParsedCurrentItem]:
        """Parse a current format item element into memory structure."""
        item_id = DataValidationUtils.safe_float_convert(
            self._get_text_value(item, "ID")
        )

        if not item_id:
            logger.warning("Current item missing ID, skipping")
            return None

        id_pai = DataValidationUtils.safe_float_convert(
            self._get_text_value(item, "ID_Pai")
        )

        parsed = ParsedCurrentItem(
            xml_element=item,
            item_id=int(item_id),
            data={
                "id_pai": int(id_pai) if id_pai else None,
                "tipo": self._get_text_value(item, "Tipo"),
                "numero": self._get_text_value(item, "Numero"),
                "titulo": self._get_text_value(item, "Titulo"),
                "texto": self._get_text_value(item, "Texto"),
                "estado": self._get_text_value(item, "Estado"),
            }
        )

        # Parse artigos (leaf records)
        artigos_elem = item.find("Artigos")
        if artigos_elem is not None:
            for artigo_elem in artigos_elem.findall("Artigo"):
                parsed.artigos.append(self._parse_current_artigo(artigo_elem, parsed))

        # Parse propostas (leaf records)
        propostas_elem = item.find("PropostasDeAlteracao")
        if propostas_elem is not None:
            for proposta_elem in propostas_elem.findall("Proposta"):
                parsed.propostas.append(self._parse_current_proposta(proposta_elem, parsed))

        # Parse diplomas (nested structure)
        diplomas_elem = item.find("DiplomasaModificar")
        if diplomas_elem is not None:
            diploma_elements = diplomas_elem.findall("DiplomaModificar") + diplomas_elem.findall("DiplomaaModificar")
            for diploma_elem in diploma_elements:
                parsed.diplomas.append(self._parse_current_diploma(diploma_elem, parsed))

        # Parse iniciativas (leaf records)
        iniciativas_elem = item.find("IniciativasMapas")
        if iniciativas_elem is not None:
            for iniciativa_elem in iniciativas_elem.findall("IniciativaMapa"):
                parsed.iniciativas.append(self._parse_current_iniciativa(iniciativa_elem, parsed))

        # Parse votacoes (leaf records)
        votacoes_elem = item.find("Votacoes")
        if votacoes_elem is not None:
            for votacao_elem in votacoes_elem.findall("Votacao"):
                parsed.votacoes.append(self._parse_current_votacao(votacao_elem, parsed))

        # Parse requerimentos (leaf records)
        requerimentos_elem = item.find("RequerimentosDeAvocacao")
        if requerimentos_elem is not None:
            for requerimento_elem in requerimentos_elem.findall("RequerimentoDeAvocacao"):
                parsed.requerimentos.append(self._parse_current_requerimento(requerimento_elem, parsed))

        return parsed

    def _parse_current_artigo(
        self, artigo_elem: ET.Element, item_ref: ParsedCurrentItem
    ) -> ParsedCurrentArtigo:
        """Parse a current format artigo element (leaf record)."""
        artigo_id = DataValidationUtils.safe_float_convert(
            self._get_text_value(artigo_elem, "ID_Art")
        )
        id_pai = DataValidationUtils.safe_float_convert(
            self._get_text_value(artigo_elem, "ID_Pai")
        )

        return ParsedCurrentArtigo(
            xml_element=artigo_elem,
            item_ref=item_ref,
            data={
                "artigo_id": int(artigo_id) if artigo_id else None,
                "id_pai": int(id_pai) if id_pai else None,
                "tipo": self._get_text_value(artigo_elem, "Tipo"),
                "numero": self._get_text_value(artigo_elem, "Numero"),
                "titulo": self._get_text_value(artigo_elem, "Titulo"),
                "texto": self._get_text_value(artigo_elem, "Texto"),
                "estado": self._get_text_value(artigo_elem, "Estado"),
            }
        )

    def _parse_current_proposta(
        self, proposta_elem: ET.Element, item_ref: ParsedCurrentItem
    ) -> ParsedCurrentProposta:
        """Parse a current format proposta element (leaf record)."""
        proposta_id = DataValidationUtils.safe_float_convert(
            self._get_text_value(proposta_elem, "ID_PA")
        )
        id_pai = DataValidationUtils.safe_float_convert(
            self._get_text_value(proposta_elem, "ID_Pai")
        )
        data_str = self._get_text_value(proposta_elem, "Data")

        return ParsedCurrentProposta(
            xml_element=proposta_elem,
            item_ref=item_ref,
            data={
                "proposta_id": int(proposta_id) if proposta_id else None,
                "id_pai": int(id_pai) if id_pai else None,
                "objeto": self._get_text_value(proposta_elem, "Objeto"),
                "data_proposta": DataValidationUtils.parse_date_flexible(data_str) if data_str else None,
                "apresentado": self._get_text_value(proposta_elem, "Apresentado"),
                "incide": self._get_text_value(proposta_elem, "Incide"),
                "tipo": self._get_text_value(proposta_elem, "Tipo"),
                "estado": self._get_text_value(proposta_elem, "Estado"),
                "ficheiro": self._get_text_value(proposta_elem, "Ficheiro"),
            }
        )

    def _parse_current_diploma(
        self, diploma_elem: ET.Element, item_ref: ParsedCurrentItem
    ) -> ParsedCurrentDiploma:
        """Parse a current format diploma element with nested artigos."""
        diploma_id = DataValidationUtils.safe_float_convert(
            self._get_text_value(diploma_elem, "ID_Dip")
        )

        parsed = ParsedCurrentDiploma(
            xml_element=diploma_elem,
            item_ref=item_ref,
            data={
                "diploma_id": int(diploma_id) if diploma_id else None,
                "titulo": self._get_text_value(diploma_elem, "DiplomaTitulo"),
                "sub_titulo": self._get_text_value(diploma_elem, "DiplomaSubTitulo"),
                "artigos_texto": self._get_text_value(diploma_elem, "DiplomasArtigos"),
                "texto_ou_estado": self._get_text_value(diploma_elem, "TextoOuEstado"),
            }
        )

        # Parse nested diploma artigos
        diplomas_artigos = diploma_elem.find("DiplomasArtigos")
        if diplomas_artigos is not None:
            for diploma_artigo_elem in diplomas_artigos.findall("DiplomaArtigo"):
                parsed.artigos.append(self._parse_current_diploma_artigo(diploma_artigo_elem, parsed))

        return parsed

    def _parse_current_diploma_artigo(
        self, diploma_artigo_elem: ET.Element, diploma_ref: ParsedCurrentDiploma
    ) -> ParsedCurrentDiplomaArtigo:
        """Parse a current format diploma artigo element with nested numeros."""
        parsed = ParsedCurrentDiplomaArtigo(
            xml_element=diploma_artigo_elem,
            diploma_ref=diploma_ref,
            data={
                "artigo_id": self._get_int_value(diploma_artigo_elem, "ID_Art"),
                "diploma_artigo_id_alt": self._get_int_value(diploma_artigo_elem, "DiplomaArtigoID"),
                "numero": self._get_text_value(diploma_artigo_elem, "Numero"),
                "titulo": self._get_text_value(diploma_artigo_elem, "Titulo"),
                "diploma_artigo_titulo_alt": self._get_text_value(diploma_artigo_elem, "DiplomaArtigoTituto"),
                "diploma_artigo_subtitulo": self._get_text_value(diploma_artigo_elem, "DiplomaArtigoSubTitulo"),
                "texto": self._get_text_value(diploma_artigo_elem, "Texto"),
                "diploma_artigo_texto": self._get_text_value(diploma_artigo_elem, "DiplomaArtigoTexto"),
                "estado": self._get_text_value(diploma_artigo_elem, "Estado"),
                "diploma_artigo_estado": self._get_text_value(diploma_artigo_elem, "DiplomaArtigoEstado"),
            }
        )

        # Parse nested diploma numeros
        diploma_numeros = diploma_artigo_elem.find("DiplomaNumeros")
        if diploma_numeros is not None:
            for diploma_numero_elem in diploma_numeros.findall("DiplomaNumero"):
                parsed.numeros.append(self._parse_current_diploma_numero(diploma_numero_elem, parsed))

        return parsed

    def _parse_current_diploma_numero(
        self, diploma_numero_elem: ET.Element, artigo_ref: ParsedCurrentDiplomaArtigo
    ) -> ParsedCurrentDiplomaNumero:
        """Parse a current format diploma numero element with nested alineas."""
        parsed = ParsedCurrentDiplomaNumero(
            xml_element=diploma_numero_elem,
            artigo_ref=artigo_ref,
            data={
                "diploma_numero_id": self._get_int_value(diploma_numero_elem, "DiplomaNumeroID"),
                "titulo": self._get_text_value(diploma_numero_elem, "DiplomaNumeroTitulo"),
                "estado": self._get_text_value(diploma_numero_elem, "DiplomaNumeroEstado"),
            }
        )

        # Parse nested diploma alineas
        diploma_alineas = diploma_numero_elem.find("DiplomaAlineas")
        if diploma_alineas is not None:
            for diploma_alinea_elem in diploma_alineas.findall("DiplomaAlinea"):
                parsed.alineas.append(ParsedCurrentDiplomaAlinea(
                    xml_element=diploma_alinea_elem,
                    numero_ref=parsed,
                    data={
                        "titulo": self._get_text_value(diploma_alinea_elem, "DiplomaAlineaTitulo"),
                        "estado": self._get_text_value(diploma_alinea_elem, "DiplomaAlineaEstado"),
                    }
                ))

        return parsed

    def _parse_current_iniciativa(
        self, iniciativa_elem: ET.Element, item_ref: ParsedCurrentItem
    ) -> ParsedCurrentIniciativa:
        """Parse a current format iniciativa mapa element (leaf record)."""
        return ParsedCurrentIniciativa(
            xml_element=iniciativa_elem,
            item_ref=item_ref,
            data={
                "numero": self._get_text_value(iniciativa_elem, "MapasNumero"),
                "titulo": self._get_text_value(iniciativa_elem, "MapasTitulo"),
                "estado": self._get_text_value(iniciativa_elem, "MapasEstado"),
                "link_url": self._get_text_value(iniciativa_elem, "MapasLink"),
            }
        )

    def _parse_current_votacao(
        self, votacao_elem: ET.Element, item_ref: ParsedCurrentItem
    ) -> ParsedCurrentVotacao:
        """Parse a current format votacao element (leaf record)."""
        data_str = self._get_text_value(votacao_elem, "Data")
        descricoes = self._get_text_value(votacao_elem, "Descricoes")

        # Handle nested Descricoes.Descricao structure
        if not descricoes:
            descricoes_elem = votacao_elem.find("Descricoes")
            if descricoes_elem is not None:
                descricao_elem = descricoes_elem.find("Descricao")
                if descricao_elem is not None and descricao_elem.text:
                    descricoes = descricao_elem.text.strip()

        diplomas_terceiros = self._get_text_value(votacao_elem, "DiplomasTerceiros")

        # Handle DiplomasTerceirosouPropostasDeLeiMapas
        diplomas_terceiros_alt = self._get_text_value(votacao_elem, "DiplomasTerceirosouPropostasDeLeiMapas")
        if not diplomas_terceiros and diplomas_terceiros_alt:
            diplomas_terceiros = diplomas_terceiros_alt
        elif diplomas_terceiros_alt:
            diplomas_elem = votacao_elem.find("DiplomasTerceirosouPropostasDeLeiMapas")
            if diplomas_elem is not None:
                diploma_elems = diplomas_elem.findall("Diploma")
                if diploma_elems:
                    diploma_texts = [d.text.strip() for d in diploma_elems if d.text]
                    if diploma_texts:
                        diplomas_terceiros = (diplomas_terceiros or "") + "; " + "; ".join(diploma_texts)

        resultado = self._get_text_value(votacao_elem, "Resultado")
        resultado_completo = self._get_text_value(votacao_elem, "ResultadoCompleto")
        if not resultado and resultado_completo:
            resultado = resultado_completo

        # Handle GruposParlamentares structure
        grupos_parlamentares = self._get_text_value(votacao_elem, "GruposParlamentares")
        grupos_elem = votacao_elem.find("GruposParlamentares")
        if grupos_elem is not None and not grupos_parlamentares:
            grupo_texts = []
            for grupo_elem in grupos_elem.findall("GrupoParlamentar"):
                if grupo_elem.text:
                    grupo_texts.append(grupo_elem.text.strip())
            for voto_elem in grupos_elem.findall("Voto"):
                if voto_elem.text:
                    grupo_texts.append(f"Voto: {voto_elem.text.strip()}")
            if grupo_texts:
                grupos_parlamentares = "; ".join(grupo_texts)

        return ParsedCurrentVotacao(
            xml_element=votacao_elem,
            item_ref=item_ref,
            data={
                "data_votacao": DataValidationUtils.parse_date_flexible(data_str) if data_str else None,
                "descricao": descricoes,
                "sub_descricao": self._get_text_value(votacao_elem, "SubDescricao"),
                "resultado": resultado,
                "diplomas_terceiros": diplomas_terceiros,
                "grupos_parlamentares": grupos_parlamentares,
            }
        )

    def _parse_current_requerimento(
        self, requerimento_elem: ET.Element, item_ref: ParsedCurrentItem
    ) -> ParsedCurrentRequerimento:
        """Parse a current format requerimento de avocacao element (leaf record)."""
        data_str = self._get_text_value(requerimento_elem, "AvocacaoData")

        return ParsedCurrentRequerimento(
            xml_element=requerimento_elem,
            item_ref=item_ref,
            data={
                "descricao": self._get_text_value(requerimento_elem, "AvocacaoDescricao"),
                "data_avocacao": DataValidationUtils.parse_date_flexible(data_str) if data_str else None,
                "titulo": self._get_text_value(requerimento_elem, "AvocacaoTitulo"),
                "estado": self._get_text_value(requerimento_elem, "AvocacaoEstado"),
                "ficheiro_url": self._get_text_value(requerimento_elem, "AvocacaoFicheiro"),
            }
        )

    def _create_current_item_record(
        self, parsed: ParsedCurrentItem, legislatura: Legislatura
    ):
        """Create or update an item database record using upsert for parallel safety."""
        # Check cache first
        existing = self._item_cache.get(parsed.item_id)

        if not existing:
            # Check database
            existing = (
                self.session.query(OrcamentoEstadoItem)
                .filter_by(item_id=parsed.item_id)
                .first()
            )
            if existing:
                self._item_cache[parsed.item_id] = existing

        if existing:
            existing.id_pai = parsed.data["id_pai"]
            existing.tipo = parsed.data["tipo"]
            existing.numero = parsed.data["numero"]
            existing.titulo = parsed.data["titulo"]
            existing.texto = parsed.data["texto"]
            existing.estado = parsed.data["estado"]
            existing.legislatura_id = legislatura.id
            parsed.db_obj = existing
        else:
            # Use upsert for parallel-safe insert (handles race conditions)
            new_id = uuid.uuid4()
            stmt = pg_insert(OrcamentoEstadoItem).values(
                id=new_id,
                item_id=parsed.item_id,
                id_pai=parsed.data["id_pai"],
                tipo=parsed.data["tipo"],
                numero=parsed.data["numero"],
                titulo=parsed.data["titulo"],
                texto=parsed.data["texto"],
                estado=parsed.data["estado"],
                legislatura_id=legislatura.id,
                format_type="current",
            ).on_conflict_do_update(
                index_elements=['item_id'],
                set_={
                    'id_pai': parsed.data["id_pai"],
                    'tipo': parsed.data["tipo"],
                    'numero': parsed.data["numero"],
                    'titulo': parsed.data["titulo"],
                    'texto': parsed.data["texto"],
                    'estado': parsed.data["estado"],
                    'legislatura_id': legislatura.id,
                }
            ).returning(OrcamentoEstadoItem.id)

            result = self.session.execute(stmt)
            returned_id = result.scalar()

            # Get the inserted/updated record for relationships
            item_obj = self.session.query(OrcamentoEstadoItem).filter_by(
                id=returned_id if returned_id else new_id
            ).first()
            if not item_obj:
                # Fallback to item_id lookup
                item_obj = self.session.query(OrcamentoEstadoItem).filter_by(
                    item_id=parsed.item_id
                ).first()

            parsed.db_obj = item_obj
            self._item_cache[parsed.item_id] = item_obj

    def _create_current_artigos(self, parsed: ParsedCurrentItem):
        """Create artigo records for an item."""
        for artigo in parsed.artigos:
            artigo_obj = OrcamentoEstadoArtigo(
                id=uuid.uuid4(),
                item_id=parsed.db_obj.id,
                artigo_id=artigo.data["artigo_id"],
                id_pai=artigo.data["id_pai"],
                tipo=artigo.data["tipo"],
                numero=artigo.data["numero"],
                titulo=artigo.data["titulo"],
                texto=artigo.data["texto"],
                estado=artigo.data["estado"],
            )
            self._add_with_tracking(artigo_obj)
            self.processed_articles += 1

    def _create_current_propostas(self, parsed: ParsedCurrentItem, legislatura: Legislatura):
        """Create proposta records for an item using upsert for parallel safety."""
        for proposta in parsed.propostas:
            if proposta.data["proposta_id"]:
                # Check cache first
                existing = self._proposal_cache.get(proposta.data["proposta_id"])

                if not existing:
                    # Check database
                    existing = (
                        self.session.query(OrcamentoEstadoPropostaAlteracao)
                        .filter_by(proposta_id=proposta.data["proposta_id"])
                        .first()
                    )
                    if existing:
                        self._proposal_cache[proposta.data["proposta_id"]] = existing

                if existing:
                    # Update existing record
                    existing.id_pai = proposta.data["id_pai"]
                    existing.titulo = proposta.data["objeto"]
                    existing.data_proposta = proposta.data["data_proposta"]
                    existing.apresentado = proposta.data["apresentado"]
                    existing.incide = proposta.data["incide"]
                    existing.tipo = proposta.data["tipo"]
                    existing.estado = proposta.data["estado"]
                    existing.ficheiro_url = proposta.data["ficheiro"]
                    existing.legislatura_id = legislatura.id
                else:
                    # Use upsert for parallel-safe insert
                    new_id = uuid.uuid4()
                    stmt = pg_insert(OrcamentoEstadoPropostaAlteracao).values(
                        id=new_id,
                        proposta_id=proposta.data["proposta_id"],
                        id_pai=proposta.data["id_pai"],
                        titulo=proposta.data["objeto"],
                        data_proposta=proposta.data["data_proposta"],
                        apresentado=proposta.data["apresentado"],
                        incide=proposta.data["incide"],
                        tipo=proposta.data["tipo"],
                        estado=proposta.data["estado"],
                        ficheiro_url=proposta.data["ficheiro"],
                        legislatura_id=legislatura.id,
                        format_type="current",
                    ).on_conflict_do_update(
                        index_elements=['proposta_id'],
                        set_={
                            'id_pai': proposta.data["id_pai"],
                            'titulo': proposta.data["objeto"],
                            'data_proposta': proposta.data["data_proposta"],
                            'apresentado': proposta.data["apresentado"],
                            'incide': proposta.data["incide"],
                            'tipo': proposta.data["tipo"],
                            'estado': proposta.data["estado"],
                            'ficheiro_url': proposta.data["ficheiro"],
                            'legislatura_id': legislatura.id,
                        }
                    )
                    self.session.execute(stmt)
                    self._proposal_cache[proposta.data["proposta_id"]] = None  # Mark as processed
                self.processed_proposals += 1

    def _create_current_iniciativas(self, parsed: ParsedCurrentItem):
        """Create iniciativa records for an item."""
        for iniciativa in parsed.iniciativas:
            iniciativa_obj = OrcamentoEstadoIniciativa(
                id=uuid.uuid4(),
                item_id=parsed.db_obj.id,
                numero=iniciativa.data["numero"],
                titulo=iniciativa.data["titulo"],
                estado=iniciativa.data["estado"],
                link_url=iniciativa.data["link_url"],
            )
            self._add_with_tracking(iniciativa_obj)
            self.processed_initiatives += 1

    def _create_current_votacoes(self, parsed: ParsedCurrentItem):
        """Create votacao records for an item."""
        for votacao in parsed.votacoes:
            votacao_obj = OrcamentoEstadoVotacao(
                id=uuid.uuid4(),
                item_id=parsed.db_obj.id,
                data_votacao=votacao.data["data_votacao"],
                descricao=votacao.data["descricao"],
                sub_descricao=votacao.data["sub_descricao"],
                resultado=votacao.data["resultado"],
                diplomas_terceiros_texto=votacao.data["diplomas_terceiros"],
                grupos_parlamentares_texto=votacao.data["grupos_parlamentares"],
            )
            self._add_with_tracking(votacao_obj)
            self.processed_votes += 1

    def _create_current_requerimentos(self, parsed: ParsedCurrentItem):
        """Create requerimento records for an item."""
        for requerimento in parsed.requerimentos:
            requerimento_obj = OrcamentoEstadoRequerimentoAvocacao(
                id=uuid.uuid4(),
                item_id=parsed.db_obj.id,
                descricao=requerimento.data["descricao"],
                data_avocacao=requerimento.data["data_avocacao"],
                titulo=requerimento.data["titulo"],
                estado=requerimento.data["estado"],
                ficheiro_url=requerimento.data["ficheiro_url"],
            )
            self._add_with_tracking(requerimento_obj)

    def _create_current_diploma_record(self, parsed: ParsedCurrentDiploma):
        """Create a diploma database record."""
        artigos_texto = parsed.data["artigos_texto"]
        texto_ou_estado = parsed.data["texto_ou_estado"]

        # Handle TextoOuEstado field
        if texto_ou_estado:
            if not artigos_texto:
                artigos_texto = texto_ou_estado
            else:
                artigos_texto += f" | {texto_ou_estado}"

        diploma_obj = OrcamentoEstadoDiploma(
            id=uuid.uuid4(),
            item_id=parsed.item_ref.db_obj.id,
            diploma_id=parsed.data["diploma_id"],
            titulo=parsed.data["titulo"],
            sub_titulo=parsed.data["sub_titulo"],
            artigos_texto=artigos_texto,
        )
        self._add_with_tracking(diploma_obj)
        parsed.db_obj = diploma_obj
        self.processed_diplomas += 1

    def _create_current_diploma_artigo_record(self, parsed: ParsedCurrentDiplomaArtigo):
        """Create a diploma artigo database record."""
        diploma_artigo_obj = OrcamentoEstadoDiplomaArtigo(
            id=uuid.uuid4(),
            diploma_id=parsed.diploma_ref.db_obj.id,
            artigo_id=parsed.data["artigo_id"],
            diploma_artigo_id_alt=parsed.data["diploma_artigo_id_alt"],
            numero=parsed.data["numero"],
            titulo=parsed.data["titulo"],
            diploma_artigo_titulo_alt=parsed.data["diploma_artigo_titulo_alt"],
            diploma_artigo_subtitulo=parsed.data["diploma_artigo_subtitulo"],
            texto=parsed.data["texto"],
            diploma_artigo_texto=parsed.data["diploma_artigo_texto"],
            estado=parsed.data["estado"],
            diploma_artigo_estado=parsed.data["diploma_artigo_estado"],
        )
        self._add_with_tracking(diploma_artigo_obj)
        parsed.db_obj = diploma_artigo_obj

    def _create_current_diploma_numero_record(self, parsed: ParsedCurrentDiplomaNumero):
        """Create a diploma numero database record."""
        diploma_numero_obj = OrcamentoEstadoDiplomaNumero(
            id=uuid.uuid4(),
            diploma_artigo_id=parsed.artigo_ref.db_obj.id,
            diploma_numero_id=parsed.data["diploma_numero_id"],
            titulo=parsed.data["titulo"],
            estado=parsed.data["estado"],
        )
        self._add_with_tracking(diploma_numero_obj)
        parsed.db_obj = diploma_numero_obj

    def _create_current_diploma_alinea_record(self, parsed: ParsedCurrentDiplomaAlinea):
        """Create a diploma alinea database record."""
        diploma_alinea_obj = OrcamentoEstadoDiplomaAlinea(
            id=uuid.uuid4(),
            diploma_numero_id=parsed.numero_ref.db_obj.id,
            titulo=parsed.data["titulo"],
            estado=parsed.data["estado"],
        )
        self._add_with_tracking(diploma_alinea_obj)

    def _detect_format_type(self, xml_root: ET.Element, filename: str) -> str:
        """
        Detect whether this is legacy or current format

        Args:
            xml_root: Root XML element
            filename: Filename for additional context

        Returns:
            'legacy' for OEPropostasAlteracao format, 'current' for OE format
        """
        # Check filename patterns first
        if "OEPropostasAlteracao" in filename:
            return "legacy"
        elif re.match(r"OE\d+.*\.xml", filename):
            return "current"

        # Check root element structure
        if xml_root.find(".//PropostaDeAlteracao") is not None:
            return "legacy"
        elif xml_root.find(".//Item") is not None:
            return "current"

        # Default to current if uncertain
        logger.warning(
            f"Could not definitively determine format type for {filename}, defaulting to current"
        )
        return "current"

    def _extract_legislatura_from_path(self, file_path: str) -> Optional[Legislatura]:
        """
        Extract and get/create legislatura from file path.

        Maps OE budget years to their corresponding legislature Roman numerals.
        Uses the parent class's _get_or_create_legislatura which has upsert pattern.

        Args:
            file_path: Full file path

        Returns:
            Legislatura instance or None
        """
        # Map budget years to legislaturas (approximate - budgets span legislature terms)
        # Each legislature term is ~4 years, budget years roughly correspond to:
        year_to_legislatura = {
            "2026": "XVII", "2025": "XVI", "2024": "XV", "2023": "XV",
            "2022": "XV", "2021": "XIV", "2020": "XIV", "2019": "XIV",
            "2018": "XIII", "2017": "XIII", "2016": "XIII", "2015": "XIII",
            "2014": "XII", "2013": "XII", "2012": "XII", "2011": "XII",
            "2010": "XI", "2009": "XI", "2008": "XI", "2007": "X",
            "2006": "X", "2005": "X", "2004": "IX", "2003": "IX",
            "2002": "IX", "2001": "VIII", "2000": "VIII", "1999": "VIII",
        }

        # Extract legislatura from path patterns
        patterns = [
            r"[/\\]([XVII]+)_Legislatura[/\\]",  # Direct Roman numeral in path
            r"[/\\](\d+)_Legislatura[/\\]",       # Numeric in path
            r"OEPropostasAlteracao(\d{4})",       # Year from proposal filename
            r"OE(\d{4})",                          # Year from OE filename
        ]

        legislatura_sigla = None

        for pattern in patterns:
            match = re.search(pattern, file_path)
            if match:
                leg_str = match.group(1)

                # If it's already a Roman numeral, use it directly
                if leg_str in self.ROMAN_TO_NUMBER:
                    legislatura_sigla = leg_str
                    break

                # If it's a year, map it to legislatura
                if leg_str in year_to_legislatura:
                    legislatura_sigla = year_to_legislatura[leg_str]
                    logger.debug(f"Mapped budget year {leg_str} to legislature {legislatura_sigla}")
                    break

                # If it's a numeric legislatura number, convert to Roman
                if leg_str.isdigit() and int(leg_str) <= 20:
                    num = int(leg_str)
                    legislatura_sigla = self.NUMBER_TO_ROMAN.get(num)
                    if legislatura_sigla:
                        break

        if not legislatura_sigla:
            logger.warning(f"Could not extract legislatura from path: {file_path}, defaulting to XVII")
            legislatura_sigla = "XVII"

        # Use the parent's _get_or_create_legislatura which has upsert pattern
        return self._get_or_create_legislatura(legislatura_sigla)

    def _get_text_value(self, element: ET.Element, tag: str) -> Optional[str]:
        """Safely extract text value from XML element"""
        child = element.find(tag)
        if child is not None and child.text:
            return child.text.strip()
        return None

    def _get_int_value(self, element: ET.Element, tag: str) -> Optional[int]:
        """Safely extract integer value from XML element"""
        text_val = self._get_text_value(element, tag)
        if text_val:
            try:
                return int(text_val)
            except ValueError:
                logger.warning(
                    f"Could not convert '{text_val}' to integer for tag '{tag}'"
                )
                return None
        return None

    def get_processing_stats(self) -> Dict[str, int]:
        """Return processing statistics"""
        return {
            "processed_proposals": self.processed_proposals,
            "processed_items": self.processed_items,
            "processed_proponents": self.processed_proponents,
            "processed_votes": self.processed_votes,
            "processed_articles": self.processed_articles,
            "processed_diplomas": self.processed_diplomas,
            "processed_initiatives": self.processed_initiatives,
        }
