"""
Parliamentary Activities Mapper
===============================

Schema mapper for parliamentary activities files (Atividades*.xml).
Based on official Portuguese Parliament documentation (December 2017):
"VI_Legislatura Atividades.xml" structure documentation.

MAJOR SECTIONS MAPPED (from official documentation):

1. **AtividadesGerais** - General parliamentary activities
   - Contains main parliamentary activities, reports, and debates
   - Maps activity types via TipodeAtividade translator
   - Maps author types via TipodeAutor translator
   - Includes publication details via TipodePublicacao translator

2. **Debates** - Parliamentary debates
   - DadosPesquisaDebatesOut: Structured debate information
   - Includes interventions, publications, and debate metadata
   - Maps debate types and author classifications

3. **Deslocacoes** - Parliamentary displacements
   - DadosDeslocacoesComissaoOut: Committee displacement data
   - Maps displacement types via TipodeDeslocacoes translator
   - Includes dates, locations, and purposes

4. **Audicoes** - Parliamentary auditions (hearings)
   - Committee hearing data and participants
   - Links to committee work and external presentations

5. **Audiencias** - Parliamentary audiences (formal hearings)
   - DadosAudienciasComissaoOut: Formal audience structure
   - External entity presentations to committees
   - Grant status and entity information

6. **Eventos** - Parliamentary events
   - DadosEventosComissaoOut: Event information
   - Maps event types via TipodeEvento translator
   - Includes locations, dates, and event classifications

REFERENCE TABLES USED:
- TipodeAtividade: 24 activity type codes (AUD, AUDI, etc.)
- TipodeAutor: Author type classifications
- TipodePublicacao: 21 publication type codes (A, B, C, etc.)
- TipodeDeslocacoes: Displacement type codes
- TipodeEvento: Event type codes
- TipodeIniciativa: 11 initiative type codes (A, C, D, etc.)

Translation Support:
- All coded fields mapped to appropriate translator modules
- Maintains consistency with AtividadeDeputado translations
- Cross-references with shared TipodePublicacao enums
"""

import logging
import os
import re
import uuid

# Import our models
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional, Set

from .enhanced_base_mapper import SchemaError, SchemaMapper

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from database.models import (
    AtividadeParlamentar,
    AtividadeParlamentarConvidado,
    AtividadeParlamentarEleito,
    AtividadeParlamentarPublicacao,
    AtividadeParlamentarVotacao,
    DebateParlamentar,
    Legislatura,
    OrcamentoContasGerencia,
    RelatorioParlamentar,
)

logger = logging.getLogger(__name__)


class AtividadesMapper(SchemaMapper):
    """
    Schema mapper for parliamentary activities files

    Processes Atividades*.xml files containing comprehensive parliamentary
    activity data across multiple functional areas:

    - AtividadesGerais: General parliamentary work
    - Debates: Parliamentary debates and discussions
    - Deslocacoes: Parliamentary missions and displacements
    - Audicoes/Audiencias: Committee hearings and audiences
    - Eventos: Parliamentary events and meetings

    All field mappings based on official VI_Legislatura documentation
    with proper translator integration for coded field values.
    """

    def __init__(self, session, import_status_record=None):
        # Accept SQLAlchemy session directly (passed by unified importer)
        super().__init__(session, import_status_record=import_status_record)
        # In-memory caches to track records created in this batch (avoid flush round-trips)
        self._atividade_cache = {}  # (atividade_id, legislatura_id) -> AtividadeParlamentar
        self._debate_cache = {}  # (debate_id, legislatura_id) -> DebateParlamentar
        self._orcamento_cache = {}  # (entry_id, legislatura_id) -> OrcamentoContasGerencia
        self._evento_cache = {}  # (id_evento, legislatura_id) -> EventoParlamentar
        self._deslocacao_cache = {}  # (id_deslocacao, legislatura_id) -> DeslocacaoParlamentar
        self._audicao_cache = {}  # (id_audicao, legislatura_id) -> AudicaoParlamentar
        self._audiencia_cache = {}  # (id_audiencia, legislatura_id) -> AudienciaParlamentar
        self._iniciativa_conjunta_cache = {}  # (relatorio_id, iniciativa_id) -> object
        self._opiniao_cache = {}  # (relatorio_id, sigla) -> object

    def get_expected_fields(self) -> Set[str]:
        return {
            # Root structure
            "Atividades",
            "Atividades.AtividadesGerais",
            # Activities section
            "Atividades.AtividadesGerais.Atividades",
            "Atividades.AtividadesGerais.Atividades.Atividade",
            "Atividades.AtividadesGerais.Atividades.Atividade.Tipo",
            "Atividades.AtividadesGerais.Atividades.Atividade.DescTipo",
            "Atividades.AtividadesGerais.Atividades.Atividade.Assunto",
            "Atividades.AtividadesGerais.Atividades.Atividade.Legislatura",
            "Atividades.AtividadesGerais.Atividades.Atividade.Sessao",
            "Atividades.AtividadesGerais.Atividades.Atividade.DataEntrada",
            "Atividades.AtividadesGerais.Atividades.Atividade.DataAgendamentoDebate",
            "Atividades.AtividadesGerais.Atividades.Atividade.Numero",
            "Atividades.AtividadesGerais.Atividades.Atividade.TipoAutor",
            "Atividades.AtividadesGerais.Atividades.Atividade.AutoresGP",
            "Atividades.AtividadesGerais.Atividades.Atividade.AutoresGP.string",
            "Atividades.AtividadesGerais.Atividades.Atividade.TextosAprovados",
            "Atividades.AtividadesGerais.Atividades.Atividade.TextosAprovados.string",
            "Atividades.AtividadesGerais.Atividades.Atividade.ResultadoVotacaoPontos",
            "Atividades.AtividadesGerais.Atividades.Atividade.OrgaoExterior",
            "Atividades.AtividadesGerais.Atividades.Atividade.Observacoes",
            # Activity Publications
            "Atividades.AtividadesGerais.Atividades.Atividade.Publicacao",
            "Atividades.AtividadesGerais.Atividades.Atividade.Publicacao.pt_gov_ar_objectos_PublicacoesOut",
            "Atividades.AtividadesGerais.Atividades.Atividade.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubNr",
            "Atividades.AtividadesGerais.Atividades.Atividade.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubTipo",
            "Atividades.AtividadesGerais.Atividades.Atividade.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubTp",
            "Atividades.AtividadesGerais.Atividades.Atividade.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubLeg",
            "Atividades.AtividadesGerais.Atividades.Atividade.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubSL",
            "Atividades.AtividadesGerais.Atividades.Atividade.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubdt",
            "Atividades.AtividadesGerais.Atividades.Atividade.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pag",
            "Atividades.AtividadesGerais.Atividades.Atividade.Publicacao.pt_gov_ar_objectos_PublicacoesOut.URLDiario",
            "Atividades.AtividadesGerais.Atividades.Atividade.Publicacao.pt_gov_ar_objectos_PublicacoesOut.idPag",
            "Atividades.AtividadesGerais.Atividades.Atividade.Publicacao.pt_gov_ar_objectos_PublicacoesOut.idDeb",
            "Atividades.AtividadesGerais.Atividades.Atividade.Publicacao.pt_gov_ar_objectos_PublicacoesOut.supl",
            "Atividades.AtividadesGerais.Atividades.Atividade.Publicacao.pt_gov_ar_objectos_PublicacoesOut.obs",
            # Activity Debate Publications
            "Atividades.AtividadesGerais.Atividades.Atividade.PublicacaoDebate",
            "Atividades.AtividadesGerais.Atividades.Atividade.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut",
            "Atividades.AtividadesGerais.Atividades.Atividade.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.pubNr",
            "Atividades.AtividadesGerais.Atividades.Atividade.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.pubTipo",
            "Atividades.AtividadesGerais.Atividades.Atividade.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.pubTp",
            "Atividades.AtividadesGerais.Atividades.Atividade.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.pubLeg",
            "Atividades.AtividadesGerais.Atividades.Atividade.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.pubSL",
            "Atividades.AtividadesGerais.Atividades.Atividade.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.pubdt",
            "Atividades.AtividadesGerais.Atividades.Atividade.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.pag",
            "Atividades.AtividadesGerais.Atividades.Atividade.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.URLDiario",
            "Atividades.AtividadesGerais.Atividades.Atividade.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.idPag",
            "Atividades.AtividadesGerais.Atividades.Atividade.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.idDeb",
            "Atividades.AtividadesGerais.Atividades.Atividade.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.obs",
            # Activity Voting
            "Atividades.AtividadesGerais.Atividades.Atividade.VotacaoDebate",
            "Atividades.AtividadesGerais.Atividades.Atividade.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut",
            "Atividades.AtividadesGerais.Atividades.Atividade.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.id",
            "Atividades.AtividadesGerais.Atividades.Atividade.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.resultado",
            "Atividades.AtividadesGerais.Atividades.Atividade.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.unanime",
            "Atividades.AtividadesGerais.Atividades.Atividade.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.descricao",
            "Atividades.AtividadesGerais.Atividades.Atividade.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.ausencias",
            "Atividades.AtividadesGerais.Atividades.Atividade.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.ausencias.string",
            "Atividades.AtividadesGerais.Atividades.Atividade.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.reuniao",
            "Atividades.AtividadesGerais.Atividades.Atividade.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.data",
            "Atividades.AtividadesGerais.Atividades.Atividade.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.publicacao",
            "Atividades.AtividadesGerais.Atividades.Atividade.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.publicacao.pt_gov_ar_objectos_PublicacoesOut",
            "Atividades.AtividadesGerais.Atividades.Atividade.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubNr",
            "Atividades.AtividadesGerais.Atividades.Atividade.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubTipo",
            "Atividades.AtividadesGerais.Atividades.Atividade.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubTp",
            "Atividades.AtividadesGerais.Atividades.Atividade.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubLeg",
            "Atividades.AtividadesGerais.Atividades.Atividade.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubSL",
            "Atividades.AtividadesGerais.Atividades.Atividade.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubdt",
            "Atividades.AtividadesGerais.Atividades.Atividade.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pag",
            "Atividades.AtividadesGerais.Atividades.Atividade.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.URLDiario",
            "Atividades.AtividadesGerais.Atividades.Atividade.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.idPag",
            "Atividades.AtividadesGerais.Atividades.Atividade.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.idDeb",
            "Atividades.AtividadesGerais.Atividades.Atividade.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.obs",
            # Reports section
            "Atividades.AtividadesGerais.Relatorios",
            "Atividades.AtividadesGerais.Relatorios.Relatorio",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Tipo",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.DescTipo",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Assunto",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Legislatura",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Sessao",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.DataEntrada",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.DataAgendamentoDebate",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Comissao",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.EntidadesExternas",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.EntidadesExternas.string",
            # Report Publications
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Publicacao",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Publicacao.pt_gov_ar_objectos_PublicacoesOut",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubNr",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubTipo",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubTp",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubLeg",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubSL",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubdt",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pag",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Publicacao.pt_gov_ar_objectos_PublicacoesOut.URLDiario",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Publicacao.pt_gov_ar_objectos_PublicacoesOut.idPag",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Publicacao.pt_gov_ar_objectos_PublicacoesOut.idDeb",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Publicacao.pt_gov_ar_objectos_PublicacoesOut.supl",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Publicacao.pt_gov_ar_objectos_PublicacoesOut.obs",
            # Report Debate Publications
            "Atividades.AtividadesGerais.Relatorios.Relatorio.PublicacaoDebate",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.pubNr",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.pubTipo",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.pubTp",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.pubLeg",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.pubSL",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.pubdt",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.pag",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.URLDiario",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.idPag",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.idDeb",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.obs",
            # Debates section
            "Atividades.Debates",
            "Atividades.Debates.DadosPesquisaDebatesOut",
            "Atividades.Debates.DadosPesquisaDebatesOut.DebateId",
            "Atividades.Debates.DadosPesquisaDebatesOut.TipoDebateDesig",
            "Atividades.Debates.DadosPesquisaDebatesOut.TipoDebate",
            "Atividades.Debates.DadosPesquisaDebatesOut.DataDebate",
            "Atividades.Debates.DadosPesquisaDebatesOut.Sessao",
            "Atividades.Debates.DadosPesquisaDebatesOut.Legislatura",
            "Atividades.Debates.DadosPesquisaDebatesOut.Assunto",
            "Atividades.Debates.DadosPesquisaDebatesOut.TipoAutor",
            "Atividades.Debates.DadosPesquisaDebatesOut.AutoresDeputados",
            "Atividades.Debates.DadosPesquisaDebatesOut.AutoresGP",
            "Atividades.Debates.DadosPesquisaDebatesOut.DataEntrada",
            "Atividades.Debates.DadosPesquisaDebatesOut.Intervencoes",
            "Atividades.Debates.DadosPesquisaDebatesOut.Intervencoes.string",
            "Atividades.Debates.DadosPesquisaDebatesOut.Publicacao",
            "Atividades.Debates.DadosPesquisaDebatesOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut",
            "Atividades.Debates.DadosPesquisaDebatesOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubNr",
            "Atividades.Debates.DadosPesquisaDebatesOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubTipo",
            "Atividades.Debates.DadosPesquisaDebatesOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubTp",
            "Atividades.Debates.DadosPesquisaDebatesOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubLeg",
            "Atividades.Debates.DadosPesquisaDebatesOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubSL",
            "Atividades.Debates.DadosPesquisaDebatesOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubdt",
            "Atividades.Debates.DadosPesquisaDebatesOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pag",
            "Atividades.Debates.DadosPesquisaDebatesOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.URLDiario",
            "Atividades.Debates.DadosPesquisaDebatesOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.idPag",
            "Atividades.Debates.DadosPesquisaDebatesOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.idDeb",
            "Atividades.Debates.DadosPesquisaDebatesOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.obs",
            "Atividades.Debates.DadosPesquisaDebatesOut.Observacoes",
            "Atividades.Debates.DadosPesquisaDebatesOut.Artigo",
            # Deslocacoes section
            "Atividades.Deslocacoes",
            # Audicoes section
            "Atividades.Audicoes",
            # Audiencias section
            "Atividades.Audiencias",
            # Eventos section
            "Atividades.Eventos",
            # Eleitos nested structures
            "Atividades.AtividadesGerais.Atividades.Atividade.Eleitos",
            "Atividades.AtividadesGerais.Atividades.Atividade.Eleitos.pt_gov_ar_objectos_EleitosOut",
            "Atividades.AtividadesGerais.Atividades.Atividade.Eleitos.pt_gov_ar_objectos_EleitosOut.nome",
            "Atividades.AtividadesGerais.Atividades.Atividade.Eleitos.pt_gov_ar_objectos_EleitosOut.cargo",
            # Convidados nested structures
            "Atividades.AtividadesGerais.Atividades.Atividade.Convidados",
            "Atividades.AtividadesGerais.Atividades.Atividade.Convidados.pt_gov_ar_objectos_ConvidadosOut",
            "Atividades.AtividadesGerais.Atividades.Atividade.Convidados.pt_gov_ar_objectos_ConvidadosOut.nome",
            "Atividades.AtividadesGerais.Atividades.Atividade.Convidados.pt_gov_ar_objectos_ConvidadosOut.cargo",
            "Atividades.AtividadesGerais.Atividades.Atividade.Convidados.pt_gov_ar_objectos_ConvidadosOut.pais",
            "Atividades.AtividadesGerais.Atividades.Atividade.Convidados.pt_gov_ar_objectos_ConvidadosOut.honra",
            # Nested pag.string structures for all publication types
            "Atividades.AtividadesGerais.Atividades.Atividade.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pag.string",
            "Atividades.AtividadesGerais.Atividades.Atividade.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.pag.string",
            "Atividades.AtividadesGerais.Atividades.Atividade.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pag.string",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pag.string",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.pag.string",
            "Atividades.Debates.DadosPesquisaDebatesOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pag.string",
            # Missing voting detail field
            "Atividades.AtividadesGerais.Atividades.Atividade.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.detalhe",
            # Additional sections that might be present but not mapped yet
            "Atividades.AtividadesGerais.Debates",
            "Atividades.AtividadesGerais.Audicoes",
            "Atividades.AtividadesGerais.Audiencias",
            "Atividades.AtividadesGerais.Deslocacoes",
            "Atividades.AtividadesGerais.Eventos",
            # IX Legislature specific fields - Report Voting and Publications
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoRelatorio",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoRelatorio.resultado",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoRelatorio.descricao",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoRelatorio.reuniao",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoRelatorio.data",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoRelatorio.publicacao",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoRelatorio.publicacao.pt_gov_ar_objectos_PublicacoesOut",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoRelatorio.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubNr",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoRelatorio.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubTipo",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoRelatorio.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubTp",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoRelatorio.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubLeg",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoRelatorio.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubSL",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoRelatorio.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubdt",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoRelatorio.publicacao.pt_gov_ar_objectos_PublicacoesOut.pag",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoRelatorio.publicacao.pt_gov_ar_objectos_PublicacoesOut.URLDiario",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoRelatorio.publicacao.pt_gov_ar_objectos_PublicacoesOut.idPag",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoRelatorio.publicacao.pt_gov_ar_objectos_PublicacoesOut.idDeb",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoRelatorio.publicacao.pt_gov_ar_objectos_PublicacoesOut.obs",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoRelatorio.publicacao.pt_gov_ar_objectos_PublicacoesOut.pag.string",
            # Report voting debate section
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoDebate",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.id",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.resultado",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.reuniao",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.data",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.publicacao",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.publicacao.pt_gov_ar_objectos_PublicacoesOut",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubNr",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubTipo",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubTp",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubLeg",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubSL",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubdt",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pag",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.URLDiario",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.idPag",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.idDeb",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.obs",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pag.string",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.detalhe",
            # Report authors/rapporteurs section
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Relatores",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Relatores.pt_gov_ar_objectos_RelatoresOut",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Relatores.pt_gov_ar_objectos_RelatoresOut.id",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Relatores.pt_gov_ar_objectos_RelatoresOut.nome",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Relatores.pt_gov_ar_objectos_RelatoresOut.gp",
            # Report observations and texts approved
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Observacoes",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.TextosAprovados",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.TextosAprovados.string",
            # Report voting ID field
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoRelatorio.id",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoRelatorio.unanime",
            # Audicoes (Parliamentary Hearings) section
            "Atividades.Audicoes.DadosAudicoesComissaoOut",
            "Atividades.Audicoes.DadosAudicoesComissaoOut.IDAudicao",
            "Atividades.Audicoes.DadosAudicoesComissaoOut.NumeroAudicao",
            "Atividades.Audicoes.DadosAudicoesComissaoOut.SessaoLegislativa",
            "Atividades.Audicoes.DadosAudicoesComissaoOut.Legislatura",
            "Atividades.Audicoes.DadosAudicoesComissaoOut.Assunto",
            "Atividades.Audicoes.DadosAudicoesComissaoOut.DataAudicao",
            "Atividades.Audicoes.DadosAudicoesComissaoOut.Data",
            "Atividades.Audicoes.DadosAudicoesComissaoOut.Comissao",
            "Atividades.Audicoes.DadosAudicoesComissaoOut.TipoAudicao",
            "Atividades.Audicoes.DadosAudicoesComissaoOut.Entidades",
            "Atividades.Audicoes.DadosAudicoesComissaoOut.Observacoes",
            # Audiencias (Parliamentary Audiences) section
            "Atividades.Audiencias.DadosAudienciasComissaoOut",
            "Atividades.Audiencias.DadosAudienciasComissaoOut.IDAudiencia",
            "Atividades.Audiencias.DadosAudienciasComissaoOut.NumeroAudiencia",
            "Atividades.Audiencias.DadosAudienciasComissaoOut.SessaoLegislativa",
            "Atividades.Audiencias.DadosAudienciasComissaoOut.Legislatura",
            "Atividades.Audiencias.DadosAudienciasComissaoOut.Assunto",
            "Atividades.Audiencias.DadosAudienciasComissaoOut.DataAudiencia",
            "Atividades.Audiencias.DadosAudienciasComissaoOut.Data",
            "Atividades.Audiencias.DadosAudienciasComissaoOut.Comissao",
            "Atividades.Audiencias.DadosAudienciasComissaoOut.Concedida",
            "Atividades.Audiencias.DadosAudienciasComissaoOut.TipoAudiencia",
            "Atividades.Audiencias.DadosAudienciasComissaoOut.Entidades",
            "Atividades.Audiencias.DadosAudienciasComissaoOut.Observacoes",
            # Orçamento e Contas de Gerência section
            "Atividades.OrcamentoContasGerencia",
            "Atividades.OrcamentoContasGerencia.pt_gov_ar_objectos_OrcamentoContasGerencia_OrcamentoContasGerenciaOut",
            "Atividades.OrcamentoContasGerencia.pt_gov_ar_objectos_OrcamentoContasGerencia_OrcamentoContasGerenciaOut.id",
            "Atividades.OrcamentoContasGerencia.pt_gov_ar_objectos_OrcamentoContasGerencia_OrcamentoContasGerenciaOut.tipo",
            "Atividades.OrcamentoContasGerencia.pt_gov_ar_objectos_OrcamentoContasGerencia_OrcamentoContasGerenciaOut.tp",
            "Atividades.OrcamentoContasGerencia.pt_gov_ar_objectos_OrcamentoContasGerencia_OrcamentoContasGerenciaOut.titulo",
            "Atividades.OrcamentoContasGerencia.pt_gov_ar_objectos_OrcamentoContasGerencia_OrcamentoContasGerenciaOut.ano",
            "Atividades.OrcamentoContasGerencia.pt_gov_ar_objectos_OrcamentoContasGerencia_OrcamentoContasGerenciaOut.leg",
            "Atividades.OrcamentoContasGerencia.pt_gov_ar_objectos_OrcamentoContasGerencia_OrcamentoContasGerenciaOut.SL",
            "Atividades.OrcamentoContasGerencia.pt_gov_ar_objectos_OrcamentoContasGerencia_OrcamentoContasGerenciaOut.dtAprovacaoCA",
            "Atividades.OrcamentoContasGerencia.pt_gov_ar_objectos_OrcamentoContasGerencia_OrcamentoContasGerenciaOut.dtAgendamento",
            # Additional fields found in XIII Legislature
            # Report Documents
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Documentos",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Documentos.DocsOut",
            # Report Voting with unanime field
            "Atividades.AtividadesGerais.Relatorios.Relatorio.VotacaoDebate.pt_gov_ar_objectos_VotacaoOut.unanime",
            # Events section
            "Atividades.Eventos",
            "Atividades.Eventos.DadosEventosComissaoOut",
            "Atividades.Eventos.DadosEventosComissaoOut.IDEvento",
            "Atividades.Eventos.DadosEventosComissaoOut.Data",
            "Atividades.Eventos.DadosEventosComissaoOut.Legislatura",
            "Atividades.Eventos.DadosEventosComissaoOut.LocalEvento",
            "Atividades.Eventos.DadosEventosComissaoOut.SessaoLegislativa",
            "Atividades.Eventos.DadosEventosComissaoOut.Designacao",
            "Atividades.Eventos.DadosEventosComissaoOut.TipoEvento",
            # Report Commission Opinion
            "Atividades.AtividadesGerais.Relatorios.Relatorio.ParecerComissao",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.ParecerComissao.AtividadeComissoesOut",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.ParecerComissao.AtividadeComissoesOut.Documentos",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.ParecerComissao.AtividadeComissoesOut.Documentos.pt_gov_ar_objectos_DocsOut",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.ParecerComissao.AtividadeComissoesOut.Documentos.pt_gov_ar_objectos_DocsOut.dataDocumento",
            # UTAO Opinion Date
            "Atividades.AtividadesGerais.Relatorios.Relatorio.DataParecerUTAO",
            # Additional XIII Legislature fields discovered in second pass
            # Deslocacoes (Displacements) section
            "Atividades.Deslocacoes",
            "Atividades.Deslocacoes.DadosDeslocacoesComissaoOut",
            "Atividades.Deslocacoes.DadosDeslocacoesComissaoOut.SessaoLegislativa",
            "Atividades.Deslocacoes.DadosDeslocacoesComissaoOut.Legislatura",
            "Atividades.Deslocacoes.DadosDeslocacoesComissaoOut.LocalEvento",
            # Report Commission Opinion - Extended fields
            "Atividades.AtividadesGerais.Relatorios.Relatorio.ParecerComissao.AtividadeComissoesOut.Id",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.ParecerComissao.AtividadeComissoesOut.Relatores",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.ParecerComissao.AtividadeComissoesOut.Relatores.pt_gov_ar_objectos_RelatoresOut",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.ParecerComissao.AtividadeComissoesOut.Relatores.pt_gov_ar_objectos_RelatoresOut.id",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.ParecerComissao.AtividadeComissoesOut.Relatores.pt_gov_ar_objectos_RelatoresOut.nome",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.ParecerComissao.AtividadeComissoesOut.Relatores.pt_gov_ar_objectos_RelatoresOut.gp",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.ParecerComissao.AtividadeComissoesOut.Numero",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.ParecerComissao.AtividadeComissoesOut.Documentos.pt_gov_ar_objectos_DocsOut.publicarInternet",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.ParecerComissao.AtividadeComissoesOut.Documentos.pt_gov_ar_objectos_DocsOut.tipoDocumento",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.ParecerComissao.AtividadeComissoesOut.Documentos.pt_gov_ar_objectos_DocsOut.tituloDocumento",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.ParecerComissao.AtividadeComissoesOut.Documentos.pt_gov_ar_objectos_DocsOut.URL",
            # Report Links and Audicoes
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Links",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Links.DocsOut",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Links.DocsOut.TituloDocumento",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Links.DocsOut.URL",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Audicoes",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Audicoes.string",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.DataPedidoParecer",
            # Third pass - additional XIII Legislature fields
            # Report Commission Opinion - More fields
            "Atividades.AtividadesGerais.Relatorios.Relatorio.ParecerComissao.AtividadeComissoesOut.Sigla",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.ParecerComissao.AtividadeComissoesOut.Nome",
            # Report Documents - Extended fields
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Documentos.DocsOut.DataDocumento",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Documentos.DocsOut.TituloDocumento",
            # Deslocacoes - Additional fields
            "Atividades.Deslocacoes.DadosDeslocacoesComissaoOut.DataIni",
            "Atividades.Deslocacoes.DadosDeslocacoesComissaoOut.Tipo",
            "Atividades.Deslocacoes.DadosDeslocacoesComissaoOut.IDDeslocacao",
            "Atividades.Deslocacoes.DadosDeslocacoesComissaoOut.Designacao",
            "Atividades.Deslocacoes.DadosDeslocacoesComissaoOut.DataFim",
            # Activity - Additional fields
            "Atividades.AtividadesGerais.Atividades.Atividade.OutrosSubscritores",
            "Atividades.AtividadesGerais.Atividades.Atividade.OutrosSubscritores.string",
            # Report - Government Members
            "Atividades.AtividadesGerais.Relatorios.Relatorio.MembrosGoverno",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.MembrosGoverno.string",
            # Report Documents - Additional fields
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Documentos.DocsOut.TipoDocumento",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Documentos.DocsOut.URL",
            # Report Links - Additional fields
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Links.DocsOut.DataDocumento",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.Links.DocsOut.TipoDocumento",
            # Report Joint Initiatives (IniciativasConjuntas) - XIV Legislature
            "Atividades.AtividadesGerais.Relatorios.Relatorio.IniciativasConjuntas",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.IniciativasConjuntas.pt_gov_ar_objectos_iniciativas_DiscussaoConjuntaOut",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.IniciativasConjuntas.pt_gov_ar_objectos_iniciativas_DiscussaoConjuntaOut.id",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.IniciativasConjuntas.pt_gov_ar_objectos_iniciativas_DiscussaoConjuntaOut.tipo",
            "Atividades.AtividadesGerais.Relatorios.Relatorio.IniciativasConjuntas.pt_gov_ar_objectos_iniciativas_DiscussaoConjuntaOut.descTipo",
        }

    def validate_and_map(
        self, xml_root: ET.Element, file_info: Dict, strict_mode: bool = False
    ) -> Dict:
        """Map parliamentary activities to database"""
        results = {"records_processed": 0, "records_imported": 0, "errors": []}

        try:
            # Validate schema coverage according to strict mode
            self.validate_schema_coverage(xml_root, file_info, strict_mode)

            # Extract legislatura from filename or XML
            legislatura_sigla = self._extract_legislatura(
                file_info["file_path"], xml_root
            )
            legislatura = self._get_or_create_legislatura(legislatura_sigla)

            # Process general activities
            atividades_gerais = xml_root.find(".//AtividadesGerais")
            if atividades_gerais is not None:
                for atividade in atividades_gerais.findall(".//Atividade"):
                    try:
                        success = self._process_atividade(atividade, legislatura)
                        results["records_processed"] += 1
                        if success:
                            results["records_imported"] += 1
                        else:
                            error_msg = f"Failed to process activity record"
                            logger.debug(error_msg)  # Downgrade to debug level
                            results["errors"].append(error_msg)
                            # Only fail in strict mode for critical errors, not missing data
                    except Exception as e:
                        error_msg = f"Activity processing error: {str(e)}"
                        logger.error(error_msg)
                        results["errors"].append(error_msg)
                        results["records_processed"] += 1
                        logger.error(
                            "Data integrity issue detected - exiting immediately"
                        )
                        raise RuntimeError("Data integrity issue detected")
                        if strict_mode:
                            logger.error(
                                f"STRICT MODE: Exiting due to activity processing exception"
                            )
                            raise

            # Process debates
            debates = xml_root.find(".//Debates")
            if debates is not None:
                for debate in debates.findall(".//DadosPesquisaDebatesOut"):
                    try:
                        success = self._process_debate(debate, legislatura)
                        results["records_processed"] += 1
                        if success:
                            results["records_imported"] += 1
                        else:
                            error_msg = f"Failed to process debate record"
                            logger.debug(error_msg)  # Downgrade to debug level
                            results["errors"].append(error_msg)
                            # Only fail in strict mode for critical errors, not missing data
                    except Exception as e:
                        error_msg = f"Debate processing error: {str(e)}"
                        logger.error(error_msg)
                        results["errors"].append(error_msg)
                        results["records_processed"] += 1
                        logger.error(
                            "Data integrity issue detected - exiting immediately"
                        )
                        raise RuntimeError("Data integrity issue detected")
                        if strict_mode:
                            logger.error(
                                f"STRICT MODE: Exiting due to debate processing exception"
                            )
                            raise

            # Process reports
            relatorios = xml_root.find(".//Relatorios")
            if relatorios is not None:
                for relatorio in relatorios.findall(".//Relatorio"):
                    try:
                        success = self._process_relatorio(relatorio, legislatura)
                        results["records_processed"] += 1
                        if success:
                            results["records_imported"] += 1
                        else:
                            error_msg = f"Failed to process report record"
                            logger.debug(error_msg)  # Downgrade to debug level
                            results["errors"].append(error_msg)
                            # Only fail in strict mode for critical errors, not missing data
                    except Exception as e:
                        error_msg = f"Report processing error: {str(e)}"
                        logger.error(error_msg)
                        results["errors"].append(error_msg)
                        results["records_processed"] += 1
                        logger.error(
                            "Data integrity issue detected - exiting immediately"
                        )
                        raise RuntimeError("Data integrity issue detected")
                        if strict_mode:
                            logger.error(
                                f"STRICT MODE: Exiting due to report processing exception"
                            )
                            raise

            # Process OrcamentoContasGerencia section
            orcamento_gerencia = xml_root.find(".//OrcamentoContasGerencia")
            if orcamento_gerencia is not None:
                for entry in orcamento_gerencia.findall(
                    ".//pt_gov_ar_objectos_OrcamentoContasGerencia_OrcamentoContasGerenciaOut"
                ):
                    try:
                        success = self._process_orcamento_gerencia(entry, legislatura)
                        results["records_processed"] += 1
                        if success:
                            results["records_imported"] += 1
                        else:
                            error_msg = f"Failed to process budget/account record"
                            logger.debug(error_msg)  # Downgrade to debug level
                            results["errors"].append(error_msg)
                            # Only fail in strict mode for critical errors, not missing data
                    except Exception as e:
                        error_msg = f"Budget/account processing error: {str(e)}"
                        logger.error(error_msg)
                        results["errors"].append(error_msg)
                        results["records_processed"] += 1
                        logger.error(
                            "Data integrity issue detected - exiting immediately"
                        )
                        raise RuntimeError("Data integrity issue detected")
                        if strict_mode:
                            logger.error(
                                f"STRICT MODE: Exiting due to budget/account processing exception"
                            )
                            raise

            # Process XIII Legislature-specific structures
            try:
                # Process events
                self._process_eventos(xml_root, legislatura)

                # Process displacements
                self._process_deslocacoes(xml_root, legislatura)

                # Process auditions (committee hearings)
                self._process_audicoes(xml_root, legislatura)

                # Process audiences
                self._process_audiencias(xml_root, legislatura)

            except Exception as e:
                error_msg = f"XIII Legislature structures processing error: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
                logger.error("Data integrity issue detected during processing")

                import traceback

                logger.error(f"Traceback: {traceback.format_exc()}")

                raise RuntimeError("Data integrity issue detected during processing")
                if strict_mode:
                    logger.error(
                        f"STRICT MODE: Exiting due to XIII Legislature processing exception"
                    )
                    raise

            # Commit all changes
            return results

        except Exception as e:
            error_msg = f"Critical error processing activities: {str(e)}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
            logger.error("Data integrity issue detected during processing")

            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            raise RuntimeError("Data integrity issue detected during processing")

            # In strict mode, re-raise the exception to trigger immediate exit
            if strict_mode:
                logger.error(
                    f"STRICT MODE: Re-raising exception to trigger immediate exit"
                )
                raise

            return results

    def _process_atividade(
        self, atividade: ET.Element, legislatura: Legislatura
    ) -> bool:
        """Process individual parliamentary activity"""
        try:
            # First check if this is an empty/placeholder record
            has_content = any(
                child.text and child.text.strip()
                for child in atividade.iter()
                if child != atividade  # Don't count the parent element itself
            )

            if not has_content:
                logger.debug(
                    "Empty activity record detected - skipping empty <Atividade /> element"
                )
                # Skip empty elements entirely - they provide no value
                return False

            # Extract basic fields
            tipo = self._get_text_value(atividade, "Tipo")
            desc_tipo = self._get_text_value(atividade, "DescTipo")
            assunto = self._get_text_value(atividade, "Assunto")
            numero = self._get_text_value(atividade, "Numero")
            tipo_autor = self._get_text_value(atividade, "TipoAutor")
            autores_gp = self._get_text_value(atividade, "AutoresGP")
            outros_subscritores = self._get_text_value(atividade, "OutrosSubscritores")
            observacoes = self._get_text_value(atividade, "Observacoes")

            # Extract dates with comprehensive fallback strategy
            data_entrada_str = self._get_text_value(atividade, "DataEntrada")
            data_agendamento_str = self._get_text_value(
                atividade, "DataAgendamentoDebate"
            )

            data_entrada = self._parse_date(data_entrada_str)
            data_agendamento_debate = self._parse_date(data_agendamento_str)
            data_atividade = data_entrada or data_agendamento_debate

            # Allow records without dates - they can still be valuable

            # Assunto is optional for activities - some valid activities don't have it
            if not assunto:
                logger.debug(f"Activity {numero or 'without number'} has no Assunto field - proceeding with available data")

            # Create external ID from numero
            id_externo = None
            if numero:
                try:
                    id_externo = int(numero)
                except ValueError:
                    pass

            # Check if activity already exists (unique per legislature)
            # Use cache-first pattern to avoid flush round-trips
            existing = None
            cache_key = (id_externo, legislatura.id) if id_externo else None

            if cache_key:
                # Check in-memory cache first (records created in this batch)
                existing = self._atividade_cache.get(cache_key)

                if not existing:
                    # Check database (records from previous imports)
                    existing = (
                        self.session.query(AtividadeParlamentar)
                        .filter_by(atividade_id=id_externo, legislatura_id=legislatura.id)
                        .first()
                    )

            if existing:
                # Update existing record
                existing.tipo = tipo
                existing.desc_tipo = desc_tipo
                existing.assunto = assunto
                existing.numero = numero
                existing.data_atividade = data_atividade
                existing.data_entrada = data_entrada
                existing.data_agendamento_debate = data_agendamento_debate
                existing.tipo_autor = tipo_autor
                existing.autores_gp = autores_gp
                # Handle new columns gracefully
                if hasattr(existing, "outros_subscritores"):
                    existing.outros_subscritores = outros_subscritores
                existing.observacoes = observacoes
                existing.legislatura_id = legislatura.id
            else:
                # Create new activity record with backward compatibility
                atividade_data = {
                    "id": uuid.uuid4(),
                    "atividade_id": id_externo,
                    "tipo": tipo,
                    "desc_tipo": desc_tipo,
                    "assunto": assunto,
                    "numero": numero,
                    "data_atividade": data_atividade,
                    "data_entrada": data_entrada,
                    "data_agendamento_debate": data_agendamento_debate,
                    "tipo_autor": tipo_autor,
                    "autores_gp": autores_gp,
                    "observacoes": observacoes,
                    "legislatura_id": legislatura.id,
                }

                # Only add outros_subscritores if the column exists
                try:
                    if hasattr(AtividadeParlamentar, "outros_subscritores"):
                        atividade_data["outros_subscritores"] = outros_subscritores
                except Exception:
                    pass  # Skip outros_subscritores if column doesn't exist

                atividade_obj = AtividadeParlamentar(**atividade_data)
                self._add_with_tracking(atividade_obj)
                # Add to cache for deduplication within this batch (no flush needed)
                if cache_key:
                    self._atividade_cache[cache_key] = atividade_obj
                existing = atividade_obj

            # Process related data
            self._process_activity_publications(atividade, existing)
            self._process_activity_votacoes(atividade, existing)
            self._process_activity_eleitos(atividade, existing)
            self._process_activity_convidados(atividade, existing)

            return True

        except Exception as e:
            logger.error(f"Error processing activity: {e}")
            logger.error("Data integrity issue detected during processing")

            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            raise RuntimeError("Data integrity issue detected during processing")
            return False

    def _process_debate(self, debate: ET.Element, legislatura: Legislatura) -> bool:
        """Process debate data"""
        try:
            # First check if this is an empty/placeholder record
            has_content = any(
                child.text and child.text.strip()
                for child in debate.iter()
                if child != debate  # Don't count the parent element itself
            )

            if not has_content:
                logger.debug(
                    "Empty debate record detected - skipping empty <Debate /> element"
                )
                # Skip empty elements entirely - they provide no value
                return False

            debate_id = self._get_text_value(debate, "DebateId")
            tipo_debate_desig = self._get_text_value(debate, "TipoDebateDesig")
            data_debate_str = self._get_text_value(debate, "DataDebate")
            tipo_debate = self._get_text_value(debate, "TipoDebate")
            assunto = self._get_text_value(debate, "Assunto")
            intervencoes = self._get_text_value(debate, "Intervencoes")
            artigo = self._get_text_value(debate, "Artigo")

            # Basic validation - require both debate_id and assunto
            if not debate_id:
                logger.debug("Missing DebateId - importing with generated ID")
                # Generate a unique debate_id based on available data
                import hashlib

                hash_input = f"{assunto or 'no_assunto'}_{data_debate_str}_{tipo_debate}_{self.legislature_number}"
                hash_obj = hashlib.md5(hash_input.encode())
                debate_id = str(abs(int(hash_obj.hexdigest()[:8], 16)))

            # Assunto is optional for debates - some valid debates don't have it
            if not assunto:
                logger.debug(
                    f"Debate {debate_id} has no Assunto field - proceeding with available data"
                )

            data_debate = self._parse_date(data_debate_str)

            debate_id_int = int(debate_id)
            cache_key = debate_id_int

            # Check if debate already exists (cache-first pattern)
            existing = self._debate_cache.get(cache_key)
            if not existing:
                existing = (
                    self.session.query(DebateParlamentar)
                    .filter_by(debate_id=debate_id_int)
                    .first()
                )

            if existing:
                # Update existing debate
                existing.tipo_debate_desig = tipo_debate_desig
                existing.data_debate = data_debate
                existing.tipo_debate = tipo_debate
                existing.assunto = assunto
                existing.intervencoes = intervencoes
                # Handle new columns gracefully
                if hasattr(existing, "artigo"):
                    existing.artigo = artigo
                # Ensure legislatura has an ID
                if hasattr(legislatura, "id") and legislatura.id:
                    existing.legislatura_id = legislatura.id
                else:
                    logger.error(
                        f"Legislatura object missing ID: {type(legislatura)} = {legislatura}"
                    )
                    return False
            else:
                # Create new debate record
                # Ensure legislatura has an ID
                if not hasattr(legislatura, "id") or not legislatura.id:
                    logger.error(
                        f"Legislatura object missing ID: {type(legislatura)} = {legislatura}"
                    )
                    return False

                # Create debate object with backward compatibility
                debate_data = {
                    "id": uuid.uuid4(),
                    "debate_id": debate_id_int,
                    "tipo_debate_desig": tipo_debate_desig,
                    "data_debate": data_debate,
                    "tipo_debate": tipo_debate,
                    "assunto": assunto,
                    "intervencoes": intervencoes,
                    "legislatura_id": legislatura.id,
                }

                # Only add artigo if the column exists
                try:
                    # Test if the column exists by checking the model
                    if hasattr(DebateParlamentar, "artigo"):
                        debate_data["artigo"] = artigo
                except Exception:
                    pass  # Skip artigo if column doesn't exist

                debate_obj = DebateParlamentar(**debate_data)
                self._add_with_tracking(debate_obj)
                # Add to cache for deduplication within this batch (no flush needed)
                self._debate_cache[cache_key] = debate_obj

            return True

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error processing debate: {e}")

            # Handle missing column errors specifically
            if "no such column" in error_msg:
                logger.warning(
                    f"Database schema needs update - missing column detected: {error_msg}"
                )
                logger.warning("Please run database migrations to add missing columns")
                # Exit the process to prevent further errors
                raise SystemExit(f"CRITICAL: Database schema mismatch - {error_msg}")

            logger.error("Data integrity issue detected during processing")


            import traceback


            logger.error(f"Traceback: {traceback.format_exc()}")


            raise RuntimeError("Data integrity issue detected during processing")
            return False

    def _process_relatorio(
        self, relatorio: ET.Element, legislatura: Legislatura
    ) -> bool:
        """Process report data"""
        try:
            # First check if this is an empty/placeholder record
            has_content = any(
                child.text and child.text.strip()
                for child in relatorio.iter()
                if child != relatorio  # Don't count the parent element itself
            )

            if not has_content:
                logger.debug("Empty report record - importing with available metadata")
                # Continue importing even if no text content - there might be valuable structural data

            tipo = self._get_text_value(relatorio, "Tipo")
            assunto = self._get_text_value(relatorio, "Assunto")
            data_entrada_str = self._get_text_value(relatorio, "DataEntrada")
            comissao = self._get_text_value(relatorio, "Comissao")
            entidades_externas = self._get_text_value(relatorio, "EntidadesExternas")

            # XIII Legislature additional fields
            data_parecer_utao_str = self._get_text_value(relatorio, "DataParecerUTAO")
            data_pedido_parecer_str = self._get_text_value(
                relatorio, "DataPedidoParecer"
            )
            membros_governo = self._get_text_value(relatorio, "MembrosGoverno")
            audicoes = self._get_text_value(relatorio, "Audicoes")

            # Assunto is optional for reports - some valid reports don't have it
            if not assunto:
                logger.debug("Report has no Assunto field - proceeding with available data")

            data_entrada = self._parse_date(data_entrada_str)
            # Allow reports without dates - they can still be valuable

            # Parse additional dates
            data_parecer_utao = (
                self._parse_date(data_parecer_utao_str)
                if data_parecer_utao_str
                else None
            )
            data_pedido_parecer = (
                self._parse_date(data_pedido_parecer_str)
                if data_pedido_parecer_str
                else None
            )

            # Create new report record (no external ID available, so always create new)
            relatorio_obj = RelatorioParlamentar(
                id=uuid.uuid4(),
                tipo=tipo,
                assunto=assunto,
                data_entrada=data_entrada,
                comissao=comissao,
                entidades_externas=entidades_externas,
                data_parecer_utao=data_parecer_utao,
                data_pedido_parecer=data_pedido_parecer,
                membros_governo=membros_governo,
                audicoes=audicoes,
                legislatura_id=legislatura.id,
            )
            self._add_with_tracking(relatorio_obj)
            # No flush needed - child records use relatorio_obj.id which is already a UUID

            # Process XIII Legislature related structures
            self._process_relatorio_documentos(relatorio, relatorio_obj.id)
            self._process_relatorio_links(relatorio, relatorio_obj.id)

            # Process XIV Legislature joint initiatives
            self._process_relatorio_iniciativas_conjuntas(relatorio, relatorio_obj.id)

            # Process commission opinions if present
            parecer_comissao = relatorio.find("ParecerComissao")
            if parecer_comissao is not None:
                self._process_comissao_opinioes(parecer_comissao, relatorio_obj.id)

            return True

        except Exception as e:
            logger.error(f"Error processing report: {e}")
            logger.error("Data integrity issue detected during processing")

            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            raise RuntimeError("Data integrity issue detected during processing")
            return False

    def _map_activity_type(self, tipo: str) -> Optional[str]:
        """Map XML activity type to database enum"""
        if not tipo:
            return None

        # Map common activity types
        type_mapping = {
            "ITG": "interpelacao",
            "OEX": "votacao",
            "SES": "debate",
            "PRC": "audiencia",
            "DEBATE": "debate",
            "RELATORIO": "audiencia",
        }

        return type_mapping.get(tipo.upper(), "debate")  # Default to debate

    def _parse_date(self, date_str: str) -> Optional[object]:
        """Parse date string to Python date object"""
        if not date_str:
            return None

        try:
            from datetime import datetime

            # Try ISO format first
            if re.match(r"\d{4}-\d{2}-\d{2}", date_str):
                return datetime.strptime(date_str, "%Y-%m-%d").date()

            # Try DD/MM/YYYY format
            if "/" in date_str:
                parts = date_str.split("/")
                if len(parts) == 3:
                    day, month, year = parts
                    return datetime.strptime(
                        f"{year}-{month.zfill(2)}-{day.zfill(2)}", "%Y-%m-%d"
                    ).date()

        except (ValueError, IndexError) as e:
            logger.warning(f"Could not parse date: {date_str} - {e}")

        return None

    # NOTE: _get_or_create_legislatura is inherited from EnhancedSchemaMapper (with caching)
    # NOTE: Roman numeral conversion uses ROMAN_TO_NUMBER from LegislatureHandlerMixin

    def _process_activity_publications(
        self, atividade: ET.Element, atividade_obj: AtividadeParlamentar
    ):
        """Process publications for activity"""
        publicacao = atividade.find("Publicacao")
        if publicacao is not None:
            for pub in publicacao.findall("pt_gov_ar_objectos_PublicacoesOut"):
                pub_nr = self._get_int_value(pub, "pubNr")
                pub_tipo = self._get_text_value(pub, "pubTipo")
                pub_tp = self._get_text_value(pub, "pubTp")
                pub_leg = self._get_text_value(pub, "pubLeg")
                pub_sl = self._get_int_value(pub, "pubSL")
                pub_dt = self._parse_date(self._get_text_value(pub, "pubdt"))
                url_diario = self._get_text_value(pub, "URLDiario")
                id_pag = self._get_int_value(pub, "idPag")
                id_deb = self._get_int_value(pub, "idDeb")

                # Handle page numbers
                pag_text = None
                pag_elem = pub.find("pag")
                if pag_elem is not None:
                    string_elems = pag_elem.findall("string")
                    if string_elems:
                        pag_text = ", ".join([s.text for s in string_elems if s.text])

                publicacao_record = AtividadeParlamentarPublicacao(
                    id=uuid.uuid4(),
                    atividade_id=atividade_obj.id,
                    pub_nr=pub_nr,
                    pub_tipo=pub_tipo,
                    pub_tp=pub_tp,
                    pub_leg=pub_leg,
                    pub_sl=pub_sl,
                    pub_dt=pub_dt,
                    pag=pag_text,
                    url_diario=url_diario,
                    id_pag=id_pag,
                    id_deb=id_deb,
                )
                self._add_with_tracking(publicacao_record)

    def _process_activity_votacoes(
        self, atividade: ET.Element, atividade_obj: AtividadeParlamentar
    ):
        """Process voting records for activity"""
        votacao_debate = atividade.find("VotacaoDebate")
        if votacao_debate is not None:
            for votacao in votacao_debate.findall("pt_gov_ar_objectos_VotacaoOut"):
                votacao_id = self._get_int_value(votacao, "id")
                resultado = self._get_text_value(votacao, "resultado")
                reuniao = self._get_text_value(votacao, "reuniao")
                publicacao = self._get_text_value(votacao, "publicacao")
                data = self._parse_date(self._get_text_value(votacao, "data"))

                votacao_record = AtividadeParlamentarVotacao(
                    id=uuid.uuid4(),
                    atividade_id=atividade_obj.id,
                    votacao_id=votacao_id,
                    resultado=resultado,
                    reuniao=reuniao,
                    publicacao=publicacao,
                    data=data,
                )
                self._add_with_tracking(votacao_record)

    def _process_activity_eleitos(
        self, atividade: ET.Element, atividade_obj: AtividadeParlamentar
    ):
        """Process elected members for activity"""
        eleitos = atividade.find("Eleitos")
        if eleitos is not None:
            for eleito in eleitos.findall("pt_gov_ar_objectos_EleitosOut"):
                nome = self._get_text_value(eleito, "nome")
                cargo = self._get_text_value(eleito, "cargo")

                if nome:
                    eleito_record = AtividadeParlamentarEleito(
                        id=uuid.uuid4(),
                        atividade_id=atividade_obj.id, nome=nome, cargo=cargo
                    )
                    self._add_with_tracking(eleito_record)

    def _process_activity_convidados(
        self, atividade: ET.Element, atividade_obj: AtividadeParlamentar
    ):
        """Process guests/invitees for activity"""
        convidados = atividade.find("Convidados")
        if convidados is not None:
            for convidado in convidados.findall("pt_gov_ar_objectos_ConvidadosOut"):
                nome = self._get_text_value(convidado, "nome")
                pais = self._get_text_value(convidado, "pais")
                honra = self._get_text_value(convidado, "honra")

                if nome:
                    convidado_record = AtividadeParlamentarConvidado(
                        id=uuid.uuid4(),
                        atividade_id=atividade_obj.id, nome=nome, pais=pais, honra=honra
                    )
                    self._add_with_tracking(convidado_record)

    def _process_orcamento_gerencia(
        self, entry: ET.Element, legislatura: Legislatura
    ) -> bool:
        """Process budget and account management entry"""
        try:
            # First check if this is an empty/placeholder record
            has_content = any(
                child.text and child.text.strip()
                for child in entry.iter()
                if child != entry  # Don't count the parent element itself
            )

            if not has_content:
                logger.debug(
                    "Empty budget/account record - importing with available metadata"
                )
                # Continue importing even if no text content - there might be valuable structural data

            # Extract required fields
            entry_id = self._get_int_value(entry, "id")
            tipo = self._get_text_value(entry, "tipo")
            tp = self._get_text_value(entry, "tp")
            titulo = self._get_text_value(entry, "titulo")
            ano = self._get_int_value(entry, "ano")
            leg = self._get_text_value(entry, "leg")
            sl = self._get_int_value(entry, "SL")

            # No validation - let record creation fail naturally if fields are actually required

            # Extract optional date fields
            dt_aprovacao_str = self._get_text_value(entry, "dtAprovacaoCA")
            dt_agendamento_str = self._get_text_value(entry, "dtAgendamento")

            dt_aprovacao = (
                self._parse_date(dt_aprovacao_str) if dt_aprovacao_str else None
            )
            dt_agendamento = (
                self._parse_date(dt_agendamento_str) if dt_agendamento_str else None
            )

            # Check if record already exists (cache-first pattern)
            cache_key = (entry_id, legislatura.id)
            existing = self._orcamento_cache.get(cache_key)
            if not existing:
                existing = (
                    self.session.query(OrcamentoContasGerencia)
                    .filter_by(entry_id=entry_id, legislatura_id=legislatura.id)
                    .first()
                )

            if existing:
                logger.debug(
                    f"Budget/account entry {entry_id} already exists, skipping"
                )
                return True

            # Create new budget/account record
            orcamento_obj = OrcamentoContasGerencia(
                id=uuid.uuid4(),
                entry_id=entry_id,
                tipo=tipo,
                tp=tp,
                titulo=titulo,
                ano=ano,
                leg=leg,
                sl=sl,
                dt_aprovacao_ca=dt_aprovacao,
                dt_agendamento=dt_agendamento,
                legislatura_id=legislatura.id,
            )
            self._add_with_tracking(orcamento_obj)
            # Add to cache for deduplication within this batch (no flush needed)
            self._orcamento_cache[cache_key] = orcamento_obj

            logger.debug(
                f"Processed budget/account entry: {entry_id} - {titulo[:50]}..."
            )
            return True

        except Exception as e:
            logger.error(f"Error processing budget/account entry: {e}")
            logger.error("Data integrity issue detected during processing")

            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            raise RuntimeError("Data integrity issue detected during processing")
            return False

    def _process_relatorio_documentos(
        self, relatorio: ET.Element, relatorio_parlamentar_id: int
    ) -> bool:
        """Process report documents for XIII Legislature"""
        try:
            from database.models import RelatorioParlamentarDocumento

            documentos = relatorio.find("Documentos")
            if documentos is None:
                return True

            for documento in documentos.findall("Documento"):
                tipo = self._get_text_value(documento, "Tipo")
                link = self._get_text_value(documento, "Link")

                if not tipo:
                    continue

                # Check if document already exists
                existing = (
                    self.session.query(RelatorioParlamentarDocumento)
                    .filter_by(
                        relatorio_parlamentar_id=relatorio_parlamentar_id,
                        tipo=tipo,
                        link=link,
                    )
                    .first()
                )

                if existing:
                    continue

                doc_obj = RelatorioParlamentarDocumento(
                    relatorio_parlamentar_id=relatorio_parlamentar_id,
                    tipo=tipo,
                    link=link,
                )
                self._add_with_tracking(doc_obj)

            return True
        except Exception as e:
            logger.error(f"Error processing report documents: {e}")
            return False

    def _process_relatorio_links(
        self, relatorio: ET.Element, relatorio_parlamentar_id: int
    ) -> bool:
        """Process report links for XIII Legislature"""
        try:
            from database.models import RelatorioParlamentarLink

            links = relatorio.find("Links")
            if links is None:
                return True

            for link_elem in links.findall("Link"):
                url = self._get_text_value(link_elem, "URL")
                descricao = self._get_text_value(link_elem, "Descricao")

                if not url:
                    continue

                # Check if link already exists
                existing = (
                    self.session.query(RelatorioParlamentarLink)
                    .filter_by(
                        relatorio_parlamentar_id=relatorio_parlamentar_id, url=url
                    )
                    .first()
                )

                if existing:
                    continue

                link_obj = RelatorioParlamentarLink(
                    relatorio_parlamentar_id=relatorio_parlamentar_id,
                    url=url,
                    descricao=descricao,
                )
                self._add_with_tracking(link_obj)

            return True
        except Exception as e:
            logger.error(f"Error processing report links: {e}")
            return False

    def _process_eventos(self, xml_root: ET.Element, legislatura) -> bool:
        """Process parliamentary events for XIII Legislature"""
        try:
            from database.models import EventoParlamentar

            eventos = xml_root.find(".//Eventos")
            if eventos is None:
                return True

            for evento in eventos.findall("DadosEventosComissaoOut"):
                id_evento = self._get_int_value(evento, "IDEvento")
                data_str = self._get_text_value(evento, "Data")
                tipo = self._get_text_value(evento, "Tipo")
                tipo_evento = self._get_text_value(evento, "TipoEvento")
                designacao = self._get_text_value(evento, "Designacao")
                local_evento = self._get_text_value(evento, "LocalEvento")
                sessao_legislativa = self._get_int_value(evento, "SessaoLegislativa")

                if not id_evento:
                    continue

                data = self._parse_date(data_str) if data_str else None

                # Check if event already exists (cache-first pattern)
                cache_key = (id_evento, legislatura.id)
                existing = self._evento_cache.get(cache_key)
                if not existing:
                    existing = (
                        self.session.query(EventoParlamentar)
                        .filter_by(id_evento=id_evento, legislatura_id=legislatura.id)
                        .first()
                    )

                if existing:
                    continue

                evento_obj = EventoParlamentar(
                    id_evento=id_evento,
                    data=data,
                    tipo_evento=tipo_evento,
                    designacao=designacao,
                    local_evento=local_evento,
                    sessao_legislativa=sessao_legislativa,
                    legislatura_id=legislatura.id,
                )
                self._add_with_tracking(evento_obj)
                # Add to cache for deduplication within this batch (no flush needed)
                self._evento_cache[cache_key] = evento_obj

            return True
        except Exception as e:
            logger.error(f"Error processing events: {e}")
            return False

    def _process_deslocacoes(self, xml_root: ET.Element, legislatura) -> bool:
        """Process parliamentary displacements for XIII Legislature"""
        try:
            from database.models import DeslocacaoParlamentar

            deslocacoes = xml_root.find(".//Deslocacoes")
            if deslocacoes is None:
                return True

            for deslocacao in deslocacoes.findall("DadosDeslocacoesComissaoOut"):
                id_deslocacao = self._get_int_value(deslocacao, "IDDeslocacao")
                data_ini_str = self._get_text_value(deslocacao, "DataIni")
                data_fim_str = self._get_text_value(deslocacao, "DataFim")
                tipo = self._get_text_value(deslocacao, "Tipo")
                designacao = self._get_text_value(deslocacao, "Designacao")
                local_evento = self._get_text_value(deslocacao, "LocalEvento")
                sessao_legislativa = self._get_int_value(
                    deslocacao, "SessaoLegislativa"
                )

                if not id_deslocacao:
                    continue

                data_ini = self._parse_date(data_ini_str) if data_ini_str else None
                data_fim = self._parse_date(data_fim_str) if data_fim_str else None

                # Check if displacement already exists (cache-first pattern)
                cache_key = (id_deslocacao, legislatura.id)
                existing = self._deslocacao_cache.get(cache_key)
                if not existing:
                    existing = (
                        self.session.query(DeslocacaoParlamentar)
                        .filter_by(
                            id_deslocacao=id_deslocacao, legislatura_id=legislatura.id
                        )
                        .first()
                    )

                if existing:
                    continue

                deslocacao_obj = DeslocacaoParlamentar(
                    id_deslocacao=id_deslocacao,
                    data_ini=data_ini,
                    data_fim=data_fim,
                    tipo=tipo,
                    designacao=designacao,
                    local_evento=local_evento,
                    sessao_legislativa=sessao_legislativa,
                    legislatura_id=legislatura.id,
                )
                self._add_with_tracking(deslocacao_obj)
                # Add to cache for deduplication within this batch (no flush needed)
                self._deslocacao_cache[cache_key] = deslocacao_obj

            return True
        except Exception as e:
            logger.error(f"Error processing displacements: {e}")
            return False

    def _process_audicoes(self, xml_root: ET.Element, legislatura) -> bool:
        """Process parliamentary auditions (committee hearings)"""
        try:
            from database.models import AudicaoParlamentar

            audicoes = xml_root.find(".//Audicoes")
            if audicoes is None:
                return True

            for audicao in audicoes.findall("DadosAudicoesComissaoOut"):
                id_audicao = self._get_int_value(audicao, "IDAudicao")
                numero_audicao = self._get_text_value(audicao, "NumeroAudicao")
                data_str = self._get_text_value(audicao, "Data")
                assunto = self._get_text_value(audicao, "Assunto")
                entidades = self._get_text_value(audicao, "Entidades")
                sessao_legislativa = self._get_int_value(audicao, "SessaoLegislativa")

                if not id_audicao:
                    continue

                data_audicao = self._parse_date(data_str) if data_str else None

                # Check if audition already exists (cache-first pattern)
                cache_key = (id_audicao, legislatura.id)
                existing = self._audicao_cache.get(cache_key)
                if not existing:
                    existing = (
                        self.session.query(AudicaoParlamentar)
                        .filter_by(id_audicao=id_audicao, legislatura_id=legislatura.id)
                        .first()
                    )

                if existing:
                    continue

                audicao_obj = AudicaoParlamentar(
                    id_audicao=id_audicao,
                    numero_audicao=numero_audicao,
                    data=data_audicao,
                    assunto=assunto,
                    entidades=entidades,
                    sessao_legislativa=sessao_legislativa,
                    legislatura_id=legislatura.id,
                )
                self._add_with_tracking(audicao_obj)
                # Add to cache for deduplication within this batch (no flush needed)
                self._audicao_cache[cache_key] = audicao_obj

            return True
        except Exception as e:
            logger.error(f"Error processing auditions: {e}")
            return False

    def _process_audiencias(self, xml_root: ET.Element, legislatura) -> bool:
        """Process parliamentary audiences"""
        try:
            from database.models import AudienciaParlamentar

            audiencias = xml_root.find(".//Audiencias")
            if audiencias is None:
                return True

            for audiencia in audiencias.findall("DadosAudienciasComissaoOut"):
                id_audiencia = self._get_int_value(audiencia, "IDAudiencia")
                numero_audiencia = self._get_text_value(audiencia, "NumeroAudiencia")
                data_str = self._get_text_value(audiencia, "Data")
                assunto = self._get_text_value(audiencia, "Assunto")
                entidades = self._get_text_value(audiencia, "Entidades")
                sessao_legislativa = self._get_int_value(audiencia, "SessaoLegislativa")
                concedida = self._get_text_value(audiencia, "Concedida")

                if not id_audiencia:
                    continue

                data_audiencia = self._parse_date(data_str) if data_str else None

                # Check if audience already exists (cache-first pattern)
                cache_key = (id_audiencia, legislatura.id)
                existing = self._audiencia_cache.get(cache_key)
                if not existing:
                    existing = (
                        self.session.query(AudienciaParlamentar)
                        .filter_by(id_audiencia=id_audiencia, legislatura_id=legislatura.id)
                        .first()
                    )

                if existing:
                    continue

                audiencia_obj = AudienciaParlamentar(
                    id_audiencia=id_audiencia,
                    numero_audiencia=numero_audiencia,
                    data=data_audiencia,
                    assunto=assunto,
                    entidades=entidades,
                    sessao_legislativa=sessao_legislativa,
                    concedida=concedida,
                    legislatura_id=legislatura.id,
                )
                self._add_with_tracking(audiencia_obj)
                # Add to cache for deduplication within this batch (no flush needed)
                self._audiencia_cache[cache_key] = audiencia_obj

            return True
        except Exception as e:
            logger.error(f"Error processing audiences: {e}")
            return False

    def _process_relatorio_iniciativas_conjuntas(
        self, relatorio: ET.Element, relatorio_parlamentar_id: int
    ) -> bool:
        """Process report joint initiatives for XIV Legislature"""
        try:
            from database.models import RelatorioParlamentarIniciativaConjunta

            iniciativas_conjuntas = relatorio.find("IniciativasConjuntas")
            if iniciativas_conjuntas is None:
                return True

            for iniciativa in iniciativas_conjuntas.findall(
                "pt_gov_ar_objectos_iniciativas_DiscussaoConjuntaOut"
            ):
                iniciativa_id = self._get_int_value(iniciativa, "id")
                tipo = self._get_text_value(iniciativa, "tipo")
                desc_tipo = self._get_text_value(iniciativa, "descTipo")

                if not iniciativa_id:
                    continue

                # Check if joint initiative already exists (cache-first pattern)
                cache_key = (relatorio_parlamentar_id, iniciativa_id)
                existing = self._iniciativa_conjunta_cache.get(cache_key)
                if not existing:
                    existing = (
                        self.session.query(RelatorioParlamentarIniciativaConjunta)
                        .filter_by(
                            relatorio_id=relatorio_parlamentar_id,
                            iniciativa_id=iniciativa_id,
                        )
                        .first()
                    )

                if existing:
                    continue

                iniciativa_obj = RelatorioParlamentarIniciativaConjunta(
                    relatorio_id=relatorio_parlamentar_id,
                    iniciativa_id=iniciativa_id,
                    tipo=tipo,
                    desc_tipo=desc_tipo,
                )
                self._add_with_tracking(iniciativa_obj)
                # Add to cache for deduplication within this batch (no flush needed)
                self._iniciativa_conjunta_cache[cache_key] = iniciativa_obj

            return True
        except Exception as e:
            logger.error(f"Error processing joint initiatives: {e}")
            return False

    def _process_comissao_opinioes(
        self, parecer_element: ET.Element, relatorio_parlamentar_id: int
    ) -> bool:
        """Process commission opinions for XIII Legislature"""
        try:
            from database.models import (
                RelatorioParlamentarComissaoDocumento,
                RelatorioParlamentarComissaoOpiniao,
                RelatorioParlamentarComissaoRelator,
            )

            atividade_comissoes = parecer_element.find("AtividadeComissoesOut")
            if atividade_comissoes is None:
                return True

            sigla = self._get_text_value(atividade_comissoes, "Sigla")
            nome = self._get_text_value(atividade_comissoes, "Nome")

            if not sigla:
                return True

            # Check if opinion already exists (cache-first pattern)
            cache_key = (relatorio_parlamentar_id, sigla)
            existing_opiniao = self._opiniao_cache.get(cache_key)
            if not existing_opiniao:
                existing_opiniao = (
                    self.session.query(RelatorioParlamentarComissaoOpiniao)
                    .filter_by(
                        relatorio_parlamentar_id=relatorio_parlamentar_id, sigla=sigla
                    )
                    .first()
                )

            if existing_opiniao:
                return True

            # Create commission opinion
            opiniao_obj = RelatorioParlamentarComissaoOpiniao(
                id=uuid.uuid4(),
                relatorio_parlamentar_id=relatorio_parlamentar_id,
                sigla=sigla,
                nome=nome,
            )
            self._add_with_tracking(opiniao_obj)
            # Add to cache for deduplication within this batch (no flush needed)
            self._opiniao_cache[cache_key] = opiniao_obj

            # Process documents
            documentos = atividade_comissoes.find("Documentos")
            if documentos is not None:
                for documento in documentos.findall("Documento"):
                    tipo = self._get_text_value(documento, "Tipo")
                    link = self._get_text_value(documento, "Link")

                    if tipo:
                        doc_obj = RelatorioParlamentarComissaoDocumento(
                            comissao_opiniao_id=opiniao_obj.id, tipo=tipo, link=link
                        )
                        self._add_with_tracking(doc_obj)

            # Process relatores
            relatores = atividade_comissoes.find("Relatores")
            if relatores is not None:
                for relator in relatores.findall("Relator"):
                    nome_relator = self._get_text_value(relator, "Nome")
                    partido = self._get_text_value(relator, "Partido")

                    if nome_relator:
                        relator_obj = RelatorioParlamentarComissaoRelator(
                            comissao_opiniao_id=opiniao_obj.id,
                            nome=nome_relator,
                            partido=partido,
                        )
                        self._add_with_tracking(relator_obj)

            return True
        except Exception as e:
            logger.error(f"Error processing commission opinions: {e}")
            return False
