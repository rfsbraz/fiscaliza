"""
Parliamentary Organ Composition Mapper - SQLAlchemy ORM Version
==============================================================

Schema mapper for parliamentary organ composition files (OrgaoComposicao*.xml).
Based on official Portuguese Parliament documentation (identical across all legislatures).

DOCUMENTATION SOURCE:
Official PDF documentation from Portuguese Parliament data downloads.
Documentation is identical from Constituinte through XIII_Legislatura.

MAIN XML STRUCTURE MAPPED:
- OrganizacaoAR: Root container for all parliamentary organizational data

PARLIAMENTARY BODIES HANDLED:
1. ConselhoAdministracao (Administrative Council)
   - DetalheOrgao: Organ identification and metadata
   - HistoricoComposicao: Historical membership records

2. ConferenciaLideres (Leaders Conference)
   - DetalheOrgao: Organ identification and metadata
   - HistoricoComposicao: Historical membership records

3. ConferenciaPresidentesComissoes (Commission Presidents Conference)
   - DetalheOrgao: Organ identification and metadata
   - HistoricoComposicaoCPC: Historical membership with presidency data

4. MesaAR (Assembly Board)
   - DetalheOrgao: Organ identification and metadata
   - HistoricoComposicaoMesa: Historical membership records

5. Plenario (Plenary)
   - DetalheOrgao: Organ identification and metadata
   - Composicao: Current membership composition

6. Comissoes (Commissions)
   - Multiple commission entries with organ details
   - HistoricoComposicao: Historical membership records
   - Reuniao: Meeting data and attendance records

7. SubComissoes (Sub-committees)
   - DetalheOrgao: Organ identification and metadata
   - HistoricoComposicao: Historical membership records

8. GruposTrabalho (Work Groups)
   - DetalheOrgao: Organ identification and metadata
   - HistoricoComposicao: Historical membership records

9. ComissaoPermanente (Permanent Committee)
   - DetalheOrgao: Organ identification and metadata
   - HistoricoComposicao: Historical membership records

FIELD MAPPINGS (from official documentation):
- DetalheOrgao fields:
  * idOrgao: Unique organ identifier
  * siglaOrgao: Organ acronym/abbreviation
  * nomeSigla: Full organ name or description
  * numeroOrgao: Sequential organ number
  * siglaLegislatura: Legislature designation

- Deputy/Composition fields:
  * depId: Deputy ID within legislature
  * depCadId: Deputy registration ID (unique person identifier)
  * depNomeParlamentar: Deputy's parliamentary name
  * depNomeCompleto: Deputy's full civil name
  * orgId: Associated organ ID
  * legDes: Legislature designation

- Parliamentary Group fields:
  * gpId: Parliamentary group ID
  * gpSigla: Parliamentary group acronym
  * gpDtInicio: Group membership start date
  * gpDtFim: Group membership end date

- Deputy Situation fields:
  * sioDes: Situation description (effective/substitute/etc.)
  * sioDtInicio: Situation start date
  * sioDtFim: Situation end date

- Position/Cargo fields:
  * carId: Position/role ID
  * carDes: Position/role description
  * dtInicio: Position start date
  * dtFim: Position end date

- Meeting fields:
  * reuId: Meeting ID
  * reuData: Meeting date
  * reuHora: Meeting time
  * reuSumario: Meeting summary
  * reuTipoReuniao: Meeting type
  * reuLocal: Meeting location
  * reuObservacoes: Meeting observations

- Attendance fields:
  * depPresente: Attendance status
  * depJustificacao: Absence justification
  * depMotivoFalta: Reason for absence

Uses comprehensive OrganizacaoAR SQLAlchemy models for zero data loss.
All field mappings preserve official XML structure and naming conventions.
"""

import logging
import os
import re

# Import our comprehensive OrganizacaoAR models
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional, Set

from sqlalchemy import or_

from .common_utilities import (
    DataValidationUtils,
    ErrorHandlingUtils,
    LegislatureUtils,
    ParliamentConstants,
    XMLPathUtils,
    safe_log_text,
)
from .enhanced_base_mapper import EnhancedSchemaMapper, SchemaError

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from database.models import (
    AdministrativeCouncil,
    AdministrativeCouncilHistoricalComposition,
    ARBoard,
    ARBoardHistoricalComposition,
    AtividadeDeputado,
    Commission,
    CommissionHistoricalComposition,
    CommissionPresidentConference,
    Deputado,
    DeputyGPSituation,
    DeputySituation,
    DeputyVideo,
    LeaderConference,
    LeaderConferenceHistoricalComposition,
    Legislatura,
    MeetingAttendance,
    OrganCompositionDeputyPosition,
    OrganCompositionDeputySituation,
    OrganMeeting,
    ParliamentaryOrganization,
    PermanentCommittee,
    PermanentCommitteeHistoricalComposition,
    Plenary,
    PlenaryComposition,
    SubCommittee,
    SubCommitteeHistoricalComposition,
    WorkGroup,
    WorkGroupHistoricalComposition,
)

logger = logging.getLogger(__name__)


class ComposicaoOrgaosMapper(EnhancedSchemaMapper):
    """
    Schema mapper for parliamentary organ composition files (OrgaoComposicao*.xml)

    Processes OrganizacaoAR XML structure containing all parliamentary bodies:
    - Administrative councils, leader conferences, commission president conferences
    - Assembly boards, plenaries, commissions, sub-committees, work groups
    - Permanent committees with comprehensive membership and meeting data

    Maps to comprehensive SQLAlchemy ORM models maintaining all field relationships
    and historical composition data as documented in official Parliament specifications.

    Inherits from EnhancedSchemaMapper which provides:
    - _legislatura_cache, _deputado_cache, _partido_cache (via CacheMixin)
    - _batch_flush() for batch processing
    - BATCH_SIZE = 100 (configurable)
    """

    # NOTE: BATCH_SIZE inherited from CacheMixin (default 100)
    # NOTE: _batch_flush() inherited from CacheMixin
    # NOTE: _deputado_cache inherited from CacheMixin (replaces _deputy_cache)

    def __init__(self, db_connection_or_session, import_status_record=None):
        super().__init__(db_connection_or_session, import_status_record=import_status_record)
        # Entity-specific caches for parliamentary organs (not in base class)
        self._org_cache = {}           # legislature_sigla -> ParliamentaryOrganization
        self._plenary_cache = {}       # (id_orgao, org_id) -> Plenary
        self._committee_cache = {}     # (id_orgao, org_id) -> Commission
        self._subcommittee_cache = {}  # (id_orgao, org_id) -> SubCommittee
        self._work_group_cache = {}    # (id_orgao, org_id) -> WorkGroup
        self._ar_board_cache = {}      # (id_orgao, org_id) -> ARBoard
        self._admin_council_cache = {} # (id_orgao, org_id) -> AdministrativeCouncil
        self._perm_committee_cache = {} # (id_orgao, org_id) -> PermanentCommittee
        self._leader_conf_cache = {}   # (id_orgao, org_id) -> LeaderConference
        self._comm_pres_conf_cache = {} # (id_orgao, org_id) -> CommissionPresidentConference
        # Name-based deputy lookup cache to avoid repeated expensive ilike queries
        self._deputy_name_cache = {}   # (nome, sigla_grupo, leg_id) -> (dep_id, dep_cad_id)

    def _preload_caches(self, legislatura: Legislatura) -> None:
        """
        Preload existing entities into caches to avoid repeated queries.
        Called once at the start of processing for significant performance gains.
        """
        logger.info(f"Preloading entity caches for legislature {legislatura.numero}...")

        # Preload parliamentary organization
        org = (
            self.session.query(ParliamentaryOrganization)
            .filter_by(legislatura_sigla=legislatura.numero)
            .first()
        )
        if org:
            self._org_cache[legislatura.numero] = org

            # Preload plenaries
            for plenary in self.session.query(Plenary).filter_by(organization_id=org.id).all():
                self._plenary_cache[(plenary.id_orgao, org.id)] = plenary

            # Preload committees
            for committee in self.session.query(Commission).filter_by(organization_id=org.id).all():
                self._committee_cache[(committee.id_orgao, org.id)] = committee

            # Preload subcommittees
            for subcommittee in self.session.query(SubCommittee).filter_by(organization_id=org.id).all():
                self._subcommittee_cache[(subcommittee.id_orgao, org.id)] = subcommittee

            # Preload work groups
            for work_group in self.session.query(WorkGroup).filter_by(organization_id=org.id).all():
                self._work_group_cache[(work_group.id_orgao, org.id)] = work_group

            # Preload AR boards
            for ar_board in self.session.query(ARBoard).filter_by(organization_id=org.id).all():
                self._ar_board_cache[(ar_board.id_orgao, org.id)] = ar_board

            # Preload administrative councils
            for admin_council in self.session.query(AdministrativeCouncil).filter_by(organization_id=org.id).all():
                self._admin_council_cache[(admin_council.id_orgao, org.id)] = admin_council

            # Preload permanent committees
            for perm_committee in self.session.query(PermanentCommittee).filter_by(organization_id=org.id).all():
                self._perm_committee_cache[(perm_committee.id_orgao, org.id)] = perm_committee

            # Preload leader conferences
            for leader_conf in self.session.query(LeaderConference).filter_by(organization_id=org.id).all():
                self._leader_conf_cache[(leader_conf.id_orgao, org.id)] = leader_conf

            # Preload commission president conferences
            for comm_pres_conf in self.session.query(CommissionPresidentConference).filter_by(organization_id=org.id).all():
                self._comm_pres_conf_cache[(comm_pres_conf.id_orgao, org.id)] = comm_pres_conf

        # Preload deputies for this legislature using base class cache
        deputies = self.session.query(Deputado).filter_by(legislatura_id=legislatura.id).all()
        for deputy in deputies:
            # Use base class's _deputado_cache with consistent key format
            self._deputado_cache[f"cadastro_{deputy.id_cadastro}"] = deputy
            self._deputado_cache[f"id_{deputy.id}"] = deputy

        logger.info(f"Preloaded caches: {len(self._deputado_cache)//2} deputies, "
                   f"{len(self._committee_cache)} committees, "
                   f"{len(self._plenary_cache)} plenaries")

    def _clear_caches(self) -> None:
        """Clear all entity caches - call when switching legislatures or after processing."""
        # Clear base class caches (legislatura, deputado, partido, pending_count)
        super()._clear_caches()
        # Clear mapper-specific organ caches
        self._org_cache.clear()
        self._plenary_cache.clear()
        self._committee_cache.clear()
        self._subcommittee_cache.clear()
        self._work_group_cache.clear()
        self._ar_board_cache.clear()
        self._admin_council_cache.clear()
        self._perm_committee_cache.clear()
        self._leader_conf_cache.clear()
        self._comm_pres_conf_cache.clear()
        self._deputy_name_cache.clear()

    def get_expected_fields(self) -> Set[str]:
        return {
            "OrganizacaoAR",
            "ConselhoAdministracao",
            "ConferenciaLideres",
            "ConferenciaPresidentesComissoes",
            "ComissaoPermanente",
            "MesaAR",
            "Comissoes",
            "SubComissoes",
            "GruposTrabalho",
            "Plenario",
            # Organ details
            "DetalheOrgao",
            "idOrgao",
            "siglaOrgao",
            "nomeSigla",
            "numeroOrgao",
            "siglaLegislatura",
            "Composicao",
            # Deputy information in plenary
            "DadosDeputadoOrgaoPlenario",
            "DepId",
            "DepCadId",
            "DepNomeParlamentar",
            "DepGP",
            "DepCPId",
            "DepCPDes",
            "LegDes",
            "DepSituacao",
            "DepNomeCompleto",
            # Parliamentary group info
            "pt_ar_wsgode_objectos_DadosSituacaoGP",
            "gpId",
            "gpSigla",
            "gpDtInicio",
            "gpDtFim",
            # Deputy situation info
            "pt_ar_wsgode_objectos_DadosSituacaoDeputado",
            "sioDes",
            "sioDtInicio",
            "sioDtFim",
            # Committee member info
            "DadosDeputadoOrgaoComissao",
            "CarId",
            "CarDes",
            "DtInicio",
            "DtFim",
            # Subcommittee and working group info
            "DadosDeputadoOrgaoSubComissao",
            "DadosDeputadoOrgaoGrupoTrabalho",
            # Constituinte legislature full path mappings
            "OrganizacaoAR.MesaAR",
            "OrganizacaoAR.ConferenciaLideres",
            "OrganizacaoAR.ConferenciaLideres.DetalheOrgao",
            "OrganizacaoAR.ConferenciaLideres.DetalheOrgao.idOrgao",
            "OrganizacaoAR.ConferenciaLideres.DetalheOrgao.siglaOrgao",
            "OrganizacaoAR.ConferenciaLideres.DetalheOrgao.nomeSigla",
            "OrganizacaoAR.ConferenciaLideres.DetalheOrgao.numeroOrgao",
            "OrganizacaoAR.ConferenciaLideres.DetalheOrgao.siglaLegislatura",
            # ConferenciaLideres Historical Composition - I Legislature
            "OrganizacaoAR.ConferenciaLideres.HistoricoComposicao",
            "OrganizacaoAR.GruposTrabalho",
            "OrganizacaoAR.Comissoes",
            "OrganizacaoAR.SubComissoes",
            "OrganizacaoAR.ConferenciaPresidentesComissoes",
            # ConferenciaPresidentesComissoes DetalheOrgao - XIII Legislature
            "OrganizacaoAR.ConferenciaPresidentesComissoes.DetalheOrgao",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.DetalheOrgao.idOrgao",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.DetalheOrgao.siglaOrgao",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.DetalheOrgao.nomeSigla",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.DetalheOrgao.numeroOrgao",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.DetalheOrgao.siglaLegislatura",
            # ConferenciaPresidentesComissoes Historical Composition - I Legislature
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.depId",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.depCadId",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.depNomeParlamentar",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.depNomeCompleto",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.orgId",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.legDes",
            # Deputy GP structure
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.depGP",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpId",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpSigla",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpDtInicio",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpDtFim",
            # Deputy Cargo structure
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.depCargo",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carId",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carDes",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carDtInicio",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carDtFim",
            # Deputy Situacao structure
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.depSituacao",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado.sioDes",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado.sioDtInicio",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado.sioDtFim",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado.sioTipMem",
            # presOrgao structure - commission presidency data
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.presOrgao",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.presOrgao.pt_ar_wsgode_objectos_DadosOrgaoPCPHistorico",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.presOrgao.pt_ar_wsgode_objectos_DadosOrgaoPCPHistorico.orgId",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.presOrgao.pt_ar_wsgode_objectos_DadosOrgaoPCPHistorico.orgSigla",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.presOrgao.pt_ar_wsgode_objectos_DadosOrgaoPCPHistorico.orgDes",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.presOrgao.pt_ar_wsgode_objectos_DadosOrgaoPCPHistorico.orgNumero",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.presOrgao.pt_ar_wsgode_objectos_DadosOrgaoPCPHistorico.presComissao",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.presOrgao.pt_ar_wsgode_objectos_DadosOrgaoPCPHistorico.presComissao.pt_ar_wsgode_objectos_DadosPeriodoCargo",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.presOrgao.pt_ar_wsgode_objectos_DadosOrgaoPCPHistorico.presComissao.pt_ar_wsgode_objectos_DadosPeriodoCargo.pecId",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.presOrgao.pt_ar_wsgode_objectos_DadosOrgaoPCPHistorico.presComissao.pt_ar_wsgode_objectos_DadosPeriodoCargo.pecDtInicio",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.presOrgao.pt_ar_wsgode_objectos_DadosOrgaoPCPHistorico.presComissao.pt_ar_wsgode_objectos_DadosPeriodoCargo.pecDtFim",
            "OrganizacaoAR.ConferenciaPresidentesComissoes.HistoricoComposicaoCPC.pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico.presOrgao.pt_ar_wsgode_objectos_DadosOrgaoPCPHistorico.presComissao.pt_ar_wsgode_objectos_DadosPeriodoCargo.pecTiaDes",
            # I Legislature specific structures - Plenario composition with DadosDeputadoSearch
            "OrganizacaoAR.Plenario.Composicao.pt_ar_wsgode_objectos_DadosDeputadoSearch",
            "OrganizacaoAR.Plenario.Composicao.pt_ar_wsgode_objectos_DadosDeputadoSearch.depId",
            "OrganizacaoAR.Plenario.Composicao.pt_ar_wsgode_objectos_DadosDeputadoSearch.depCadId",
            "OrganizacaoAR.Plenario.Composicao.pt_ar_wsgode_objectos_DadosDeputadoSearch.depNomeParlamentar",
            "OrganizacaoAR.Plenario.Composicao.pt_ar_wsgode_objectos_DadosDeputadoSearch.depNomeCompleto",
            "OrganizacaoAR.Plenario.Composicao.pt_ar_wsgode_objectos_DadosDeputadoSearch.depCPId",
            "OrganizacaoAR.Plenario.Composicao.pt_ar_wsgode_objectos_DadosDeputadoSearch.depCPDes",
            "OrganizacaoAR.Plenario.Composicao.pt_ar_wsgode_objectos_DadosDeputadoSearch.legDes",
            # Deputy GP structure in I Legislature plenario composition
            "OrganizacaoAR.Plenario.Composicao.pt_ar_wsgode_objectos_DadosDeputadoSearch.depGP",
            "OrganizacaoAR.Plenario.Composicao.pt_ar_wsgode_objectos_DadosDeputadoSearch.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP",
            "OrganizacaoAR.Plenario.Composicao.pt_ar_wsgode_objectos_DadosDeputadoSearch.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpId",
            "OrganizacaoAR.Plenario.Composicao.pt_ar_wsgode_objectos_DadosDeputadoSearch.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpSigla",
            "OrganizacaoAR.Plenario.Composicao.pt_ar_wsgode_objectos_DadosDeputadoSearch.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpDtInicio",
            "OrganizacaoAR.Plenario.Composicao.pt_ar_wsgode_objectos_DadosDeputadoSearch.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpDtFim",
            # Deputy Situacao structure in I Legislature plenario composition
            "OrganizacaoAR.Plenario.Composicao.pt_ar_wsgode_objectos_DadosDeputadoSearch.depSituacao",
            "OrganizacaoAR.Plenario.Composicao.pt_ar_wsgode_objectos_DadosDeputadoSearch.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoDeputado",
            "OrganizacaoAR.Plenario.Composicao.pt_ar_wsgode_objectos_DadosDeputadoSearch.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoDeputado.sioDes",
            "OrganizacaoAR.Plenario.Composicao.pt_ar_wsgode_objectos_DadosDeputadoSearch.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoDeputado.sioDtInicio",
            "OrganizacaoAR.Plenario.Composicao.pt_ar_wsgode_objectos_DadosDeputadoSearch.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoDeputado.sioDtFim",
            # I Legislature specific DetalheOrgao fields
            "OrganizacaoAR.MesaAR.DetalheOrgao.orgId",
            "OrganizacaoAR.MesaAR.DetalheOrgao.orgNumero",
            "OrganizacaoAR.MesaAR.DetalheOrgao.orgSigla",
            "OrganizacaoAR.MesaAR.DetalheOrgao.orgTioId",
            "OrganizacaoAR.MesaAR.DetalheOrgao.orgSuoId",
            "OrganizacaoAR.MesaAR.DetalheOrgao.legDes",
            # I Legislature Commission structure
            "OrganizacaoAR.Comissoes.Orgao",
            "OrganizacaoAR.Comissoes.Orgao.DetalheOrgao",
            "OrganizacaoAR.Comissoes.Orgao.DetalheOrgao.idOrgao",
            "OrganizacaoAR.Comissoes.Orgao.DetalheOrgao.siglaOrgao",
            "OrganizacaoAR.Comissoes.Orgao.DetalheOrgao.nomeSigla",
            "OrganizacaoAR.Comissoes.Orgao.DetalheOrgao.numeroOrgao",
            "OrganizacaoAR.Comissoes.Orgao.DetalheOrgao.siglaLegislatura",
            # I Legislature Commission meeting data (Reunioes)
            "OrganizacaoAR.Comissoes.Orgao.Reunioes",
            "OrganizacaoAR.Comissoes.Orgao.Reunioes.pt_ar_wsgode_objectos_DadosReuniao",
            "OrganizacaoAR.Comissoes.Orgao.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuId",
            "OrganizacaoAR.Comissoes.Orgao.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuTarId",
            "OrganizacaoAR.Comissoes.Orgao.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuTarSigla",
            "OrganizacaoAR.Comissoes.Orgao.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuTarDes",
            "OrganizacaoAR.Comissoes.Orgao.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuTirDes",
            "OrganizacaoAR.Comissoes.Orgao.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuNumero",
            "OrganizacaoAR.Comissoes.Orgao.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuDataHora",
            "OrganizacaoAR.Comissoes.Orgao.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuFinalPlenario",
            # I Legislature Plenario Reunioes - meetings and attendance
            "OrganizacaoAR.Plenario.Reunioes",
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario",
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario.Presencas",
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario.Presencas.presencas",
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario.Presencas.presencas.pt_gov_ar_wsgode_objectos_Presencas",
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario.Presencas.presencas.pt_gov_ar_wsgode_objectos_Presencas.siglaQualidadePresencaOrgao",
            # I Legislature specific structures
            "OrganizacaoAR.GruposTrabalhoAR",
            "OrganizacaoAR.ConselhoAdministracao",
            "OrganizacaoAR.ConselhoAdministracao.DetalheOrgao",
            "OrganizacaoAR.ConselhoAdministracao.DetalheOrgao.idOrgao",
            "OrganizacaoAR.ConselhoAdministracao.DetalheOrgao.siglaOrgao",
            "OrganizacaoAR.ConselhoAdministracao.DetalheOrgao.nomeSigla",
            "OrganizacaoAR.ConselhoAdministracao.DetalheOrgao.numeroOrgao",
            "OrganizacaoAR.ConselhoAdministracao.DetalheOrgao.siglaLegislatura",
            # ConselhoAdministracao Historical Composition - I Legislature
            "OrganizacaoAR.ConselhoAdministracao.HistoricoComposicao",
            "OrganizacaoAR.ComissaoPermanente",
            # ComissaoPermanente Historical Composition - I Legislature
            "OrganizacaoAR.ComissaoPermanente.HistoricoComposicao",
            # VI Legislature ComissaoPermanente HistoricoComposicao detailed structure
            "OrganizacaoAR.ComissaoPermanente.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico",
            "OrganizacaoAR.ComissaoPermanente.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depId",
            "OrganizacaoAR.ComissaoPermanente.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCadId",
            "OrganizacaoAR.ComissaoPermanente.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depNomeParlamentar",
            "OrganizacaoAR.ComissaoPermanente.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.legDes",
            "OrganizacaoAR.ComissaoPermanente.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.orgId",
            "OrganizacaoAR.ComissaoPermanente.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP",
            "OrganizacaoAR.ComissaoPermanente.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP",
            "OrganizacaoAR.ComissaoPermanente.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpId",
            "OrganizacaoAR.ComissaoPermanente.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpSigla",
            "OrganizacaoAR.ComissaoPermanente.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpDtInicio",
            "OrganizacaoAR.ComissaoPermanente.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpDtFim",
            "OrganizacaoAR.ComissaoPermanente.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo",
            "OrganizacaoAR.ComissaoPermanente.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado",
            "OrganizacaoAR.ComissaoPermanente.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carId",
            "OrganizacaoAR.ComissaoPermanente.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carDes",
            "OrganizacaoAR.ComissaoPermanente.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carDtInicio",
            "OrganizacaoAR.ComissaoPermanente.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carDtFim",
            "OrganizacaoAR.ComissaoPermanente.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao",
            "OrganizacaoAR.ComissaoPermanente.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado",
            "OrganizacaoAR.ComissaoPermanente.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado.sioDes",
            "OrganizacaoAR.ComissaoPermanente.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado.sioTipMem",
            "OrganizacaoAR.ComissaoPermanente.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado.sioDtInicio",
            "OrganizacaoAR.ComissaoPermanente.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado.sioDtFim",
            "OrganizacaoAR.Plenario",
            # MesaAR detailed mappings
            "OrganizacaoAR.MesaAR.DetalheOrgao",
            "OrganizacaoAR.MesaAR.DetalheOrgao.numeroOrgao",
            "OrganizacaoAR.MesaAR.DetalheOrgao.idOrgao",
            "OrganizacaoAR.MesaAR.DetalheOrgao.siglaLegislatura",
            "OrganizacaoAR.MesaAR.DetalheOrgao.siglaOrgao",
            "OrganizacaoAR.MesaAR.DetalheOrgao.nomeSigla",
            "OrganizacaoAR.MesaAR.Composicao",
            # MesaAR Historical Composition - IX Legislature
            "OrganizacaoAR.MesaAR.HistoricoComposicaoMesa",
            "OrganizacaoAR.MesaAR.HistoricoComposicaoMesa.pt_ar_wsgode_objectos_DadosMesaComposicaoHistorico",
            "OrganizacaoAR.MesaAR.HistoricoComposicaoMesa.pt_ar_wsgode_objectos_DadosMesaComposicaoHistorico.depId",
            "OrganizacaoAR.MesaAR.HistoricoComposicaoMesa.pt_ar_wsgode_objectos_DadosMesaComposicaoHistorico.depCadId",
            "OrganizacaoAR.MesaAR.HistoricoComposicaoMesa.pt_ar_wsgode_objectos_DadosMesaComposicaoHistorico.depNomeParlamentar",
            "OrganizacaoAR.MesaAR.HistoricoComposicaoMesa.pt_ar_wsgode_objectos_DadosMesaComposicaoHistorico.depNomeCompleto",
            "OrganizacaoAR.MesaAR.HistoricoComposicaoMesa.pt_ar_wsgode_objectos_DadosMesaComposicaoHistorico.depGP",
            "OrganizacaoAR.MesaAR.HistoricoComposicaoMesa.pt_ar_wsgode_objectos_DadosMesaComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP",
            "OrganizacaoAR.MesaAR.HistoricoComposicaoMesa.pt_ar_wsgode_objectos_DadosMesaComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpId",
            "OrganizacaoAR.MesaAR.HistoricoComposicaoMesa.pt_ar_wsgode_objectos_DadosMesaComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpDtInicio",
            "OrganizacaoAR.MesaAR.HistoricoComposicaoMesa.pt_ar_wsgode_objectos_DadosMesaComposicaoHistorico.depCargo",
            "OrganizacaoAR.MesaAR.HistoricoComposicaoMesa.pt_ar_wsgode_objectos_DadosMesaComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado",
            "OrganizacaoAR.MesaAR.HistoricoComposicaoMesa.pt_ar_wsgode_objectos_DadosMesaComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carId",
            "OrganizacaoAR.MesaAR.HistoricoComposicaoMesa.pt_ar_wsgode_objectos_DadosMesaComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carDes",
            "OrganizacaoAR.MesaAR.HistoricoComposicaoMesa.pt_ar_wsgode_objectos_DadosMesaComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carDtInicio",
            "OrganizacaoAR.MesaAR.HistoricoComposicaoMesa.pt_ar_wsgode_objectos_DadosMesaComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carDtFim",
            "OrganizacaoAR.MesaAR.HistoricoComposicaoMesa.pt_ar_wsgode_objectos_DadosMesaComposicaoHistorico.legDes",
            "OrganizacaoAR.MesaAR.HistoricoComposicaoMesa.pt_ar_wsgode_objectos_DadosMesaComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpSigla",
            "OrganizacaoAR.MesaAR.HistoricoComposicaoMesa.pt_ar_wsgode_objectos_DadosMesaComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpDtFim",
            # Plenario detailed mappings
            "OrganizacaoAR.Plenario.DetalheOrgao",
            "OrganizacaoAR.Plenario.DetalheOrgao.numeroOrgao",
            "OrganizacaoAR.Plenario.DetalheOrgao.idOrgao",
            "OrganizacaoAR.Plenario.DetalheOrgao.siglaOrgao",
            "OrganizacaoAR.Plenario.DetalheOrgao.siglaLegislatura",
            "OrganizacaoAR.Plenario.DetalheOrgao.nomeSigla",
            "OrganizacaoAR.Plenario.Composicao",
            "OrganizacaoAR.Plenario.Reunioes",
            # Deputy data in plenary - full paths
            "OrganizacaoAR.Plenario.Composicao.DadosDeputadoOrgaoPlenario",
            "OrganizacaoAR.Plenario.Composicao.DadosDeputadoOrgaoPlenario.DepId",
            "OrganizacaoAR.Plenario.Composicao.DadosDeputadoOrgaoPlenario.DepCadId",
            "OrganizacaoAR.Plenario.Composicao.DadosDeputadoOrgaoPlenario.DepCPId",
            "OrganizacaoAR.Plenario.Composicao.DadosDeputadoOrgaoPlenario.DepNomeParlamentar",
            "OrganizacaoAR.Plenario.Composicao.DadosDeputadoOrgaoPlenario.DepNomeCompleto",
            "OrganizacaoAR.Plenario.Composicao.DadosDeputadoOrgaoPlenario.DepCPDes",
            "OrganizacaoAR.Plenario.Composicao.DadosDeputadoOrgaoPlenario.LegDes",
            # Parliamentary group data - full paths
            "OrganizacaoAR.Plenario.Composicao.DadosDeputadoOrgaoPlenario.DepGP",
            "OrganizacaoAR.Plenario.Composicao.DadosDeputadoOrgaoPlenario.DepGP.pt_ar_wsgode_objectos_DadosSituacaoGP",
            "OrganizacaoAR.Plenario.Composicao.DadosDeputadoOrgaoPlenario.DepGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpId",
            "OrganizacaoAR.Plenario.Composicao.DadosDeputadoOrgaoPlenario.DepGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpSigla",
            "OrganizacaoAR.Plenario.Composicao.DadosDeputadoOrgaoPlenario.DepGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpDtInicio",
            "OrganizacaoAR.Plenario.Composicao.DadosDeputadoOrgaoPlenario.DepGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpDtFim",
            # Deputy situation data - full paths
            "OrganizacaoAR.Plenario.Composicao.DadosDeputadoOrgaoPlenario.DepSituacao",
            "OrganizacaoAR.Plenario.Composicao.DadosDeputadoOrgaoPlenario.DepSituacao.pt_ar_wsgode_objectos_DadosSituacaoDeputado",
            "OrganizacaoAR.Plenario.Composicao.DadosDeputadoOrgaoPlenario.DepSituacao.pt_ar_wsgode_objectos_DadosSituacaoDeputado.sioDes",
            "OrganizacaoAR.Plenario.Composicao.DadosDeputadoOrgaoPlenario.DepSituacao.pt_ar_wsgode_objectos_DadosSituacaoDeputado.sioDtInicio",
            "OrganizacaoAR.Plenario.Composicao.DadosDeputadoOrgaoPlenario.DepSituacao.pt_ar_wsgode_objectos_DadosSituacaoDeputado.sioDtFim",
            # DadosDeputadoOrgaoPlenario Videos structure - XIII Legislature
            "OrganizacaoAR.Plenario.Composicao.DadosDeputadoOrgaoPlenario.Videos",
            "OrganizacaoAR.Plenario.Composicao.DadosDeputadoOrgaoPlenario.Videos.pt_ar_wsgode_objectos_DadosVideo",
            "OrganizacaoAR.Plenario.Composicao.DadosDeputadoOrgaoPlenario.Videos.pt_ar_wsgode_objectos_DadosVideo.url",
            "OrganizacaoAR.Plenario.Composicao.DadosDeputadoOrgaoPlenario.Videos.pt_ar_wsgode_objectos_DadosVideo.tipo",
            # III Legislature additional mappings - extended structure
            # ComissaoPermanente detailed mappings
            "OrganizacaoAR.ComissaoPermanente.DetalheOrgao",
            "OrganizacaoAR.ComissaoPermanente.DetalheOrgao.siglaOrgao",
            "OrganizacaoAR.ComissaoPermanente.DetalheOrgao.siglaLegislatura",
            "OrganizacaoAR.ComissaoPermanente.DetalheOrgao.numeroOrgao",
            # Comissoes extended structure
            "OrganizacaoAR.Comissoes.OrgaoBase",
            "OrganizacaoAR.Comissoes.OrgaoBase.DetalheOrgao",
            "OrganizacaoAR.Comissoes.OrgaoBase.DetalheOrgao.numeroOrgao",
            "OrganizacaoAR.Comissoes.OrgaoBase.DetalheOrgao.idOrgao",
            "OrganizacaoAR.Comissoes.OrgaoBase.DetalheOrgao.siglaOrgao",
            "OrganizacaoAR.Comissoes.OrgaoBase.DetalheOrgao.nomeSigla",
            "OrganizacaoAR.Comissoes.OrgaoBase.DetalheOrgao.siglaLegislatura",
            "OrganizacaoAR.Comissoes.OrgaoBase.Composicao",
            "OrganizacaoAR.Comissoes.OrgaoBase.Reunioes",
            # Committee Historical Composition - IX Legislature
            "OrganizacaoAR.Comissoes.OrgaoBase.HistoricoComposicao",
            "OrganizacaoAR.Comissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico",
            "OrganizacaoAR.Comissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depId",
            "OrganizacaoAR.Comissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCadId",
            "OrganizacaoAR.Comissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depNomeParlamentar",
            "OrganizacaoAR.Comissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depNomeCompleto",
            "OrganizacaoAR.Comissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.orgId",
            "OrganizacaoAR.Comissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP",
            "OrganizacaoAR.Comissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP",
            "OrganizacaoAR.Comissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpId",
            "OrganizacaoAR.Comissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpSigla",
            "OrganizacaoAR.Comissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpDtInicio",
            "OrganizacaoAR.Comissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpDtFim",
            "OrganizacaoAR.Comissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo",
            "OrganizacaoAR.Comissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado",
            "OrganizacaoAR.Comissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carId",
            "OrganizacaoAR.Comissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carDes",
            "OrganizacaoAR.Comissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carDtInicio",
            "OrganizacaoAR.Comissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carDtFim",
            "OrganizacaoAR.Comissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao",
            "OrganizacaoAR.Comissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado",
            "OrganizacaoAR.Comissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado.sioDes",
            "OrganizacaoAR.Comissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado.sioDtInicio",
            "OrganizacaoAR.Comissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado.sioDtFim",
            "OrganizacaoAR.Comissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado.sioTipMem",
            "OrganizacaoAR.Comissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.legDes",
            # Meeting data structures
            "OrganizacaoAR.Comissoes.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao",
            "OrganizacaoAR.Comissoes.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuId",
            "OrganizacaoAR.Comissoes.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuTarId",
            "OrganizacaoAR.Comissoes.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuTarSigla",
            "OrganizacaoAR.Comissoes.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuTarDes",
            "OrganizacaoAR.Comissoes.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuTirDes",
            "OrganizacaoAR.Comissoes.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuLocal",
            "OrganizacaoAR.Comissoes.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuData",
            "OrganizacaoAR.Comissoes.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuHora",
            "OrganizacaoAR.Comissoes.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuTipo",
            "OrganizacaoAR.Comissoes.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuEstado",
            # Plenary meeting structures - III Legislature
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario",
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario.Reuniao",
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario.Reuniao.reuNumero",
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario.Reuniao.selNumero",
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario.Reuniao.reuData",
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario.Reuniao.reuHora",
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario.Reuniao.reuLocal",
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario.Reuniao.reuTipo",
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario.Reuniao.reuEstado",
            # Presencas (attendance) structures
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario.Presencas",
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario.Presencas.tipoReuniao",
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario.Presencas.pt_ar_wsgode_objectos_DadosPresenca",
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario.Presencas.pt_ar_wsgode_objectos_DadosPresenca.depId",
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario.Presencas.pt_ar_wsgode_objectos_DadosPresenca.depCadId",
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario.Presencas.pt_ar_wsgode_objectos_DadosPresenca.depNomeParlamentar",
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario.Presencas.pt_ar_wsgode_objectos_DadosPresenca.presTipo",
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario.Presencas.pt_ar_wsgode_objectos_DadosPresenca.presJustificacao",
            # Additional missing III Legislature fields
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario.Presencas.dtReuniao",
            "OrganizacaoAR.ComissaoPermanente.DetalheOrgao.nomeSigla",
            "OrganizacaoAR.ComissaoPermanente.DetalheOrgao.idOrgao",
            "OrganizacaoAR.Comissoes.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuDataHora",
            "OrganizacaoAR.Comissoes.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuNumero",
            "OrganizacaoAR.Comissoes.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuFinalPlenario",
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario.Reuniao.reuTirDes",
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario.Reuniao.legDes",
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario.Reuniao.reuDataHora",
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario.Reuniao.reuId",
            # SubCommittees Historical Composition - IX Legislature
            "OrganizacaoAR.SubComissoes.OrgaoBase.HistoricoComposicao",
            "OrganizacaoAR.SubComissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico",
            "OrganizacaoAR.SubComissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depId",
            "OrganizacaoAR.SubComissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCadId",
            "OrganizacaoAR.SubComissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depNomeParlamentar",
            "OrganizacaoAR.SubComissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depNomeCompleto",
            "OrganizacaoAR.SubComissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.orgId",
            "OrganizacaoAR.SubComissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP",
            "OrganizacaoAR.SubComissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP",
            "OrganizacaoAR.SubComissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpId",
            "OrganizacaoAR.SubComissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpSigla",
            "OrganizacaoAR.SubComissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpDtInicio",
            "OrganizacaoAR.SubComissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpDtFim",
            "OrganizacaoAR.SubComissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo",
            "OrganizacaoAR.SubComissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado",
            "OrganizacaoAR.SubComissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carId",
            "OrganizacaoAR.SubComissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carDes",
            "OrganizacaoAR.SubComissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carDtInicio",
            "OrganizacaoAR.SubComissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carDtFim",
            "OrganizacaoAR.SubComissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao",
            "OrganizacaoAR.SubComissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado",
            "OrganizacaoAR.SubComissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado.sioDes",
            "OrganizacaoAR.SubComissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado.sioDtInicio",
            "OrganizacaoAR.SubComissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado.sioDtFim",
            "OrganizacaoAR.SubComissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado.sioTipMem",
            "OrganizacaoAR.SubComissoes.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.legDes",
            # SubCommittee base structure and details
            "OrganizacaoAR.SubComissoes.OrgaoBase",
            "OrganizacaoAR.SubComissoes.OrgaoBase.DetalheOrgao",
            "OrganizacaoAR.SubComissoes.OrgaoBase.DetalheOrgao.idOrgao",
            "OrganizacaoAR.SubComissoes.OrgaoBase.DetalheOrgao.siglaOrgao",
            "OrganizacaoAR.SubComissoes.OrgaoBase.DetalheOrgao.nomeSigla",
            "OrganizacaoAR.SubComissoes.OrgaoBase.DetalheOrgao.numeroOrgao",
            "OrganizacaoAR.SubComissoes.OrgaoBase.DetalheOrgao.siglaLegislatura",
            # SubCommittee meetings - complete structure
            "OrganizacaoAR.SubComissoes.OrgaoBase.Reunioes",
            "OrganizacaoAR.SubComissoes.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao",
            "OrganizacaoAR.SubComissoes.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuId",
            "OrganizacaoAR.SubComissoes.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuTarId",
            "OrganizacaoAR.SubComissoes.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuTarSigla",
            "OrganizacaoAR.SubComissoes.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuTarDes",
            "OrganizacaoAR.SubComissoes.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuTirDes",
            "OrganizacaoAR.SubComissoes.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuLocal",
            "OrganizacaoAR.SubComissoes.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuData",
            "OrganizacaoAR.SubComissoes.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuHora",
            "OrganizacaoAR.SubComissoes.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuTipo",
            "OrganizacaoAR.SubComissoes.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuEstado",
            "OrganizacaoAR.SubComissoes.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuDataHora",
            "OrganizacaoAR.SubComissoes.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuNumero",
            "OrganizacaoAR.SubComissoes.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuFinalPlenario",
            # Plenary composition (different structure)
            "OrganizacaoAR.Plenario.Composicao.DadosDeputadoOrgaoPlenario.DepCargo",
            "OrganizacaoAR.Plenario.Composicao.DadosDeputadoOrgaoPlenario.DepCargo.pt_ar_wsgode_objectos_DadosCargoDeputado",
            "OrganizacaoAR.Plenario.Composicao.DadosDeputadoOrgaoPlenario.DepCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carId",
            "OrganizacaoAR.Plenario.Composicao.DadosDeputadoOrgaoPlenario.DepCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carDes",
            "OrganizacaoAR.Plenario.Composicao.DadosDeputadoOrgaoPlenario.DepCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carDtInicio",
            "OrganizacaoAR.Plenario.Composicao.DadosDeputadoOrgaoPlenario.DepCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carDtFim",
            # Plenary meeting presences (different structure)
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario.Presencas.presencas",
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario.Presencas.presencas.pt_gov_ar_wsgode_objectos_Presencas",
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario.Presencas.presencas.pt_gov_ar_wsgode_objectos_Presencas.nomeDeputado",
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario.Presencas.presencas.pt_gov_ar_wsgode_objectos_Presencas.siglaGrupo",
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario.Presencas.presencas.pt_gov_ar_wsgode_objectos_Presencas.siglaFalta",
            "OrganizacaoAR.Plenario.Reunioes.ReuniaoPlenario.Presencas.presencas.pt_gov_ar_wsgode_objectos_Presencas.motivoFalta",
            # VIII Legislature Working Groups OrgaoBase structure
            "OrganizacaoAR.GruposTrabalho.OrgaoBase",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.DetalheOrgao",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.DetalheOrgao.idOrgao",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.DetalheOrgao.siglaOrgao",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.DetalheOrgao.nomeSigla",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.DetalheOrgao.numeroOrgao",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.DetalheOrgao.siglaLegislatura",
            # VIII Legislature Working Groups Historical Composition
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.HistoricoComposicao",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depId",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCadId",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depNomeParlamentar",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depNomeCompleto",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.orgId",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.legDes",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpId",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpSigla",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpDtInicio",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpDtFim",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carId",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carDes",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carDtInicio",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carDtFim",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado.sioDes",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado.sioDtInicio",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado.sioDtFim",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado.sioTipMem",
            # VIII Legislature Working Groups Meetings
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.Reunioes",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuId",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuNumero",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuDataHora",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuFinalPlenario",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuTirDes",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuTarId",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuTarSigla",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuTarDes",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuLocal",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuData",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuHora",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuTipo",
            "OrganizacaoAR.GruposTrabalho.OrgaoBase.Reunioes.pt_ar_wsgode_objectos_DadosReuniao.reuEstado",
            # XIII Legislature ConselhoAdministracao HistoricoComposicao structure
            "OrganizacaoAR.ConselhoAdministracao.HistoricoComposicao",
            "OrganizacaoAR.ConselhoAdministracao.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico",
            "OrganizacaoAR.ConselhoAdministracao.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depId",
            "OrganizacaoAR.ConselhoAdministracao.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCadId",
            "OrganizacaoAR.ConselhoAdministracao.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depNomeParlamentar",
            "OrganizacaoAR.ConselhoAdministracao.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depNomeCompleto",
            "OrganizacaoAR.ConselhoAdministracao.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.orgId",
            "OrganizacaoAR.ConselhoAdministracao.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.legDes",
            # ConselhoAdministracao HistoricoComposicao - Deputy GP structure
            "OrganizacaoAR.ConselhoAdministracao.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP",
            "OrganizacaoAR.ConselhoAdministracao.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP",
            "OrganizacaoAR.ConselhoAdministracao.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpId",
            "OrganizacaoAR.ConselhoAdministracao.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpSigla",
            "OrganizacaoAR.ConselhoAdministracao.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpDtInicio",
            "OrganizacaoAR.ConselhoAdministracao.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpDtFim",
            # ConselhoAdministracao HistoricoComposicao - Deputy Cargo structure
            "OrganizacaoAR.ConselhoAdministracao.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo",
            "OrganizacaoAR.ConselhoAdministracao.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado",
            "OrganizacaoAR.ConselhoAdministracao.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carId",
            "OrganizacaoAR.ConselhoAdministracao.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carDes",
            "OrganizacaoAR.ConselhoAdministracao.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carDtInicio",
            "OrganizacaoAR.ConselhoAdministracao.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carDtFim",
            # ConselhoAdministracao HistoricoComposicao - Deputy Situacao structure
            "OrganizacaoAR.ConselhoAdministracao.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao",
            "OrganizacaoAR.ConselhoAdministracao.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado",
            "OrganizacaoAR.ConselhoAdministracao.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado.sioDes",
            "OrganizacaoAR.ConselhoAdministracao.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado.sioDtInicio",
            "OrganizacaoAR.ConselhoAdministracao.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado.sioDtFim",
            "OrganizacaoAR.ConselhoAdministracao.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado.sioTipMem",
            # XIII Legislature ConferenciaLideres HistoricoComposicao structure (same as ConselhoAdministracao)
            "OrganizacaoAR.ConferenciaLideres.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico",
            "OrganizacaoAR.ConferenciaLideres.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depId",
            "OrganizacaoAR.ConferenciaLideres.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCadId",
            "OrganizacaoAR.ConferenciaLideres.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depNomeParlamentar",
            "OrganizacaoAR.ConferenciaLideres.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depNomeCompleto",
            "OrganizacaoAR.ConferenciaLideres.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.orgId",
            "OrganizacaoAR.ConferenciaLideres.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.legDes",
            # ConferenciaLideres HistoricoComposicao - Deputy GP structure
            "OrganizacaoAR.ConferenciaLideres.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP",
            "OrganizacaoAR.ConferenciaLideres.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP",
            "OrganizacaoAR.ConferenciaLideres.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpId",
            "OrganizacaoAR.ConferenciaLideres.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpSigla",
            "OrganizacaoAR.ConferenciaLideres.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpDtInicio",
            "OrganizacaoAR.ConferenciaLideres.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpDtFim",
            # ConferenciaLideres HistoricoComposicao - Deputy Cargo structure
            "OrganizacaoAR.ConferenciaLideres.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo",
            "OrganizacaoAR.ConferenciaLideres.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado",
            "OrganizacaoAR.ConferenciaLideres.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carId",
            "OrganizacaoAR.ConferenciaLideres.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carDes",
            "OrganizacaoAR.ConferenciaLideres.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carDtInicio",
            "OrganizacaoAR.ConferenciaLideres.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carDtFim",
            # ConferenciaLideres HistoricoComposicao - Deputy Situacao structure
            "OrganizacaoAR.ConferenciaLideres.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao",
            "OrganizacaoAR.ConferenciaLideres.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado",
            "OrganizacaoAR.ConferenciaLideres.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado.sioDes",
            "OrganizacaoAR.ConferenciaLideres.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado.sioDtInicio",
            "OrganizacaoAR.ConferenciaLideres.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado.sioDtFim",
            "OrganizacaoAR.ConferenciaLideres.HistoricoComposicao.pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado.sioTipMem",
        }

    def validate_and_map(
        self, xml_root: ET.Element, file_info: Dict, strict_mode: bool = False
    ) -> Dict:
        """Map parliamentary organ composition to database"""
        # Store for use in nested methods
        self.strict_mode = strict_mode
        self.file_info = file_info
        results = self.create_processing_results()

        try:
            # Validate schema coverage according to strict mode
            self.validate_schema_coverage(xml_root, file_info, strict_mode)

            # Extract legislatura from filename or XML
            legislatura_sigla = self._extract_legislatura(
                file_info["file_path"], xml_root
            )
            legislatura = self._get_or_create_legislatura(legislatura_sigla)

            # Preload entity caches for performance optimization
            self._preload_caches(legislatura)

            # Process MesaAR (AR Board)
            mesa_ar = xml_root.find(".//MesaAR")
            if mesa_ar is not None:
                try:
                    success = self._process_mesa_ar(mesa_ar, legislatura)
                    results["records_processed"] += 1
                    if success:
                        results["records_imported"] += 1
                except Exception as e:
                    error_msg = f"MesaAR processing error: {str(e)}"
                    self._handle_processing_error(error_msg, results, strict_mode)

            # Process ConselhoAdministracao (Administrative Council)
            conselho_admin = xml_root.find(".//ConselhoAdministracao")
            if conselho_admin is not None:
                try:
                    success = self._process_conselho_administracao(
                        conselho_admin, legislatura
                    )
                    results["records_processed"] += 1
                    if success:
                        results["records_imported"] += 1
                except Exception as e:
                    error_msg = f"ConselhoAdministracao processing error: {str(e)}"
                    self._handle_processing_error(error_msg, results, strict_mode)

            # Process ComissaoPermanente (Permanent Committee)
            comissao_permanente = xml_root.find(".//ComissaoPermanente")
            if comissao_permanente is not None:
                try:
                    success = self._process_comissao_permanente(
                        comissao_permanente, legislatura
                    )
                    results["records_processed"] += 1
                    if success:
                        results["records_imported"] += 1
                except Exception as e:
                    error_msg = f"ComissaoPermanente processing error: {str(e)}"
                    self._handle_processing_error(error_msg, results, strict_mode)

            # Process ConferenciaLideres (Leader Conference)
            conferencia_lideres = xml_root.find(".//ConferenciaLideres")
            if conferencia_lideres is not None:
                try:
                    success = self._process_conferencia_lideres(
                        conferencia_lideres, legislatura
                    )
                    results["records_processed"] += 1
                    if success:
                        results["records_imported"] += 1
                except Exception as e:
                    error_msg = f"ConferenciaLideres processing error: {str(e)}"
                    self._handle_processing_error(error_msg, results, strict_mode)

            # Process ConferenciaPresidentesComissoes (Commission Presidents Conference)
            conferencia_presidentes = xml_root.find(
                ".//ConferenciaPresidentesComissoes"
            )
            if conferencia_presidentes is not None:
                try:
                    success = self._process_conferencia_presidentes_comissoes(
                        conferencia_presidentes, legislatura
                    )
                    results["records_processed"] += 1
                    if success:
                        results["records_imported"] += 1
                except Exception as e:
                    error_msg = (
                        f"ConferenciaPresidentesComissoes processing error: {str(e)}"
                    )
                    self._handle_processing_error(error_msg, results, strict_mode)

            # Process working groups FIRST (before plenario processing)
            grupos_trabalho = xml_root.find(".//GruposTrabalho")
            if grupos_trabalho is not None:
                for grupo in grupos_trabalho:
                    try:
                        # Check if this is an OrgaoBase structure (VIII Legislature)
                        if grupo.tag == "OrgaoBase":
                            success = self._process_working_group_orgao_base(
                                grupo, legislatura
                            )
                        else:
                            # Simple working group structure (I Legislature)
                            success = self._process_grupo_trabalho(grupo, legislatura)
                        results["records_processed"] += 1
                        if success:
                            results["records_imported"] += 1
                    except Exception as e:
                        error_msg = f"Working group processing error: {str(e)}"
                        self._handle_processing_error(error_msg, results, strict_mode)

            # Process I Legislature working groups (GruposTrabalhoAR)
            grupos_trabalho_ar = xml_root.find(".//GruposTrabalhoAR")
            if grupos_trabalho_ar is not None:
                for grupo in grupos_trabalho_ar:
                    try:
                        success = self._process_grupo_trabalho(grupo, legislatura)
                        results["records_processed"] += 1
                        if success:
                            results["records_imported"] += 1
                    except Exception as e:
                        error_msg = (
                            f"I Legislature working group processing error: {str(e)}"
                        )
                        self._handle_processing_error(error_msg, results, strict_mode)

            # Process plenary composition (AFTER working groups)
            plenario = xml_root.find(".//Plenario")
            if plenario is not None:
                try:
                    success = self._process_plenario(plenario, legislatura)
                    results["records_processed"] += 1
                    if success:
                        results["records_imported"] += 1
                except Exception as e:
                    error_msg = f"Plenario processing error: {str(e)}"
                    self._handle_processing_error(error_msg, results, strict_mode)

            # Process committees
            comissoes = xml_root.find(".//Comissoes")
            if comissoes is not None:
                # Handle different committee structures by legislature
                for comissao in comissoes:
                    try:
                        # Check if this is an OrgaoBase structure (III Legislature and later)
                        if comissao.tag == "OrgaoBase":
                            success = self._process_orgao_base(comissao, legislatura)
                        # Check if this is an Orgao structure (I Legislature)
                        elif comissao.tag == "Orgao":
                            success = self._process_i_legislature_orgao(
                                comissao, legislatura
                            )
                        else:
                            success = self._process_comissao(comissao, legislatura)
                        results["records_processed"] += 1
                        if success:
                            results["records_imported"] += 1
                    except Exception as e:
                        error_msg = f"Committee processing error: {str(e)}"
                        self._handle_processing_error(error_msg, results, strict_mode)

            # Process subcommittees
            subcomissoes = xml_root.find(".//SubComissoes")
            if subcomissoes is not None:
                for subcomissao in subcomissoes:
                    try:
                        success = self._process_subcomissao(subcomissao, legislatura)
                        results["records_processed"] += 1
                        if success:
                            results["records_imported"] += 1
                    except Exception as e:
                        error_msg = f"Subcommittee processing error: {str(e)}"
                        self._handle_processing_error(error_msg, results, strict_mode)

            # Force final flush before commit
            self._batch_flush(force=True)
            # Clear caches after processing
            self._clear_caches()
            # Finalize processing with commit
            return self.finalize_processing(results)

        except Exception as e:
            error_msg = f"Error in validate_and_map: {e}"
            logger.error(f"Data integrity issue detected during processing: {error_msg}")
            logger.error(f"Full exception: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise RuntimeError(f"Data integrity issue in validate_and_map: {error_msg}")

    def _process_plenario(self, plenario: ET.Element, legislatura: Legislatura) -> bool:
        """Process plenary composition"""
        try:
            # Get or create plenary as a committee
            detalhe_orgao = plenario.find("DetalheOrgao")
            if detalhe_orgao is None:
                return False

            id_orgao = self._get_text_value(detalhe_orgao, "idOrgao")
            sigla_orgao = self._get_text_value(detalhe_orgao, "siglaOrgao")
            nome_sigla = self._get_text_value(detalhe_orgao, "nomeSigla")
            if not sigla_orgao or not nome_sigla:
                raise ValueError(
                    f"Missing required organ identifiers: siglaOrgao='{sigla_orgao}', nomeSigla='{nome_sigla}'. Data integrity violation - cannot generate artificial identifiers"
                )

            if not id_orgao:
                return False

            # Create or get plenary record
            plenary = self._get_or_create_plenary(
                self._safe_int(id_orgao), sigla_orgao, nome_sigla, legislatura
            )
            logger.info(
                f"Using plenary ID {plenary.id} for {safe_log_text(sigla_orgao)} in {legislatura.numero} Legislature"
            )

            # Process members
            composicao = plenario.find("Composicao")
            if composicao is not None:
                # Handle standard structure (newer legislatures)
                for deputado_data in composicao.findall("DadosDeputadoOrgaoPlenario"):
                    self._process_deputy_plenary_membership(deputado_data, plenary)

                # Handle I Legislature structure with DadosDeputadoSearch
                for deputado_search in composicao.findall(
                    "pt_ar_wsgode_objectos_DadosDeputadoSearch"
                ):
                    self._process_i_legislature_deputy_composition(
                        deputado_search, plenary, legislatura
                    )

            # Process meetings (Reunioes) - handle both simple and ReuniaoPlenario structures
            reunioes = plenario.find("Reunioes")
            if reunioes is not None:
                # Handle simple Reuniao structure
                for reuniao in reunioes.findall("Reuniao"):
                    self._process_organ_meeting(reuniao, plenary=plenary)

                # Handle ReuniaoPlenario structure (III Legislature and I Legislature)
                for reuniao_plenario in reunioes.findall("ReuniaoPlenario"):
                    self._process_reuniao_plenario(
                        reuniao_plenario, plenary, legislatura
                    )

            return True

        except Exception as e:
            error_msg = f"Error processing plenary: {e}"
            logger.error(error_msg)
            logger.error("Data integrity issue detected during plenary processing")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            if hasattr(self, "strict_mode") and self.strict_mode:
                logger.error(f"STRICT MODE: Raising exception due to plenary processing error")
                raise RuntimeError(f"STRICT MODE - Data integrity issue: {error_msg}")
            return False

    def _process_comissao(self, comissao: ET.Element, legislatura: Legislatura) -> bool:
        """Process committee composition"""
        try:
            detalhe_orgao = comissao.find("DetalheOrgao")
            if detalhe_orgao is None:
                return False

            id_orgao = self._get_text_value(detalhe_orgao, "idOrgao")
            sigla_orgao = self._get_text_value(detalhe_orgao, "siglaOrgao")
            nome_sigla = self._get_text_value(detalhe_orgao, "nomeSigla")

            if not id_orgao or not sigla_orgao:
                return False

            # Create or get committee record
            committee = self._get_or_create_committee(
                self._safe_int(id_orgao), sigla_orgao, nome_sigla, legislatura
            )

            # Process members
            composicao = comissao.find("Composicao")
            if composicao is not None:
                for deputado_data in composicao.findall("DadosDeputadoOrgaoComissao"):
                    self._process_deputy_committee_membership(deputado_data, committee)

            # Process historical composition (IX Legislature)
            historico_composicao = comissao.find("HistoricoComposicao")
            if historico_composicao is not None:
                for historico_data in historico_composicao.findall(
                    "pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico"
                ):
                    self._process_commission_historical_composition(
                        historico_data, committee, legislatura
                    )

            return True

        except Exception as e:
            error_msg = f"Error processing committee: {e}"
            logger.error(error_msg)
            logger.error("Data integrity issue detected during committee processing")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            if hasattr(self, "strict_mode") and self.strict_mode:
                logger.error(f"STRICT MODE: Raising exception due to committee processing error")
                raise RuntimeError(f"STRICT MODE - Data integrity issue: {error_msg}")
            return False

    def _process_subcomissao(
        self, subcomissao: ET.Element, legislatura: Legislatura
    ) -> bool:
        """Process subcommittee composition"""
        try:
            detalhe_orgao = subcomissao.find("DetalheOrgao")
            if detalhe_orgao is None:
                return False

            id_orgao = self._get_text_value(detalhe_orgao, "idOrgao")
            sigla_orgao = self._get_text_value(detalhe_orgao, "siglaOrgao")
            nome_sigla = self._get_text_value(detalhe_orgao, "nomeSigla")

            if not id_orgao or not sigla_orgao:
                return False

            # Create or get subcommittee record
            subcommittee = self._get_or_create_subcommittee(
                self._safe_int(id_orgao), sigla_orgao, nome_sigla, legislatura
            )

            # Process members
            composicao = subcomissao.find("Composicao")
            if composicao is not None:
                for deputado_data in composicao.findall(
                    "DadosDeputadoOrgaoSubComissao"
                ):
                    self._process_deputy_subcommittee_membership(
                        deputado_data, subcommittee
                    )

            # Process historical composition (IX Legislature)
            historico_composicao = subcomissao.find("HistoricoComposicao")
            if historico_composicao is not None:
                for historico_data in historico_composicao.findall(
                    "pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico"
                ):
                    self._process_subcommittee_historical_composition(
                        historico_data, subcommittee, legislatura
                    )

            # Process meetings (IX Legislature)
            reunioes = subcomissao.find("Reunioes")
            if reunioes is not None:
                for dados_reuniao in reunioes.findall(
                    "pt_ar_wsgode_objectos_DadosReuniao"
                ):
                    self._process_organ_meeting_namespace(
                        dados_reuniao, sub_committee=subcommittee
                    )

            return True

        except Exception as e:
            error_msg = f"Error processing subcommittee: {e}"
            logger.error(error_msg)
            logger.error("Data integrity issue detected during subcommittee processing")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            if hasattr(self, "strict_mode") and self.strict_mode:
                logger.error(f"STRICT MODE: Raising exception due to subcommittee processing error")
                raise RuntimeError(f"STRICT MODE - Data integrity issue: {error_msg}")
            return False

    def _process_grupo_trabalho(
        self, grupo: ET.Element, legislatura: Legislatura
    ) -> bool:
        """Process working group composition"""
        try:
            detalhe_orgao = grupo.find("DetalheOrgao")
            if detalhe_orgao is None:
                return False

            id_orgao = self._get_text_value(detalhe_orgao, "idOrgao")
            sigla_orgao = self._get_text_value(detalhe_orgao, "siglaOrgao")
            nome_sigla = self._get_text_value(detalhe_orgao, "nomeSigla")

            if not id_orgao or not sigla_orgao:
                return False

            # Create or get working group record
            work_group = self._get_or_create_work_group(
                self._safe_int(id_orgao), sigla_orgao, nome_sigla, legislatura
            )

            # Process members
            composicao = grupo.find("Composicao")
            if composicao is not None:
                for deputado_data in composicao.findall(
                    "DadosDeputadoOrgaoGrupoTrabalho"
                ):
                    self._process_deputy_work_group_membership(
                        deputado_data, work_group
                    )

            return True

        except Exception as e:
            logger.error(f"Error processing working group: {e}")
            return False

    def _process_deputy_plenary_membership(
        self, deputado_data: ET.Element, plenary: Plenary
    ) -> bool:
        """Process deputy membership in plenary"""
        try:
            dep_id = self._get_text_value(deputado_data, "DepId")
            dep_cad_id = self._get_text_value(deputado_data, "DepCadId")
            dep_nome = self._get_text_value(deputado_data, "DepNomeParlamentar")
            dep_nome_completo = self._get_text_value(deputado_data, "DepNomeCompleto")

            if not dep_cad_id or not dep_nome:
                return False

            # Get dates from situation data
            situacao = deputado_data.find("DepSituacao")
            data_inicio = None
            data_fim = None

            if situacao is not None:
                sit_data = situacao.find("pt_ar_wsgode_objectos_DadosSituacaoDeputado")
                if sit_data is not None:
                    data_inicio = self._parse_date(
                        self._get_text_value(sit_data, "sioDtInicio")
                    )
                    data_fim = self._parse_date(
                        self._get_text_value(sit_data, "sioDtFim")
                    )

            if not data_inicio:
                return False

            # Both DepId and DepCadId must be present for data integrity
            if not dep_id or not dep_cad_id:
                raise ValueError(
                    f"Missing required deputy IDs: DepId='{dep_id}', DepCadId='{dep_cad_id}'. Data integrity violation - cannot create artificial IDs"
                )

            # Convert IDs to integers (XML provides strings)
            record_id = self._safe_int(dep_id)
            cadastral_id = self._safe_int(dep_cad_id)
            deputado = self._get_or_create_deputado(
                record_id, cadastral_id, dep_nome, dep_nome_completo,
                xml_context=deputado_data  # Pass XML context for LegDes extraction
            )

            # Process deputy positions (DepCargo) - IX Legislature structure
            dep_cargo = deputado_data.find("DepCargo")
            if dep_cargo is not None:
                dados_cargo = dep_cargo.find("pt_ar_wsgode_objectos_DadosCargoDeputado")
                if dados_cargo is not None:
                    # Process the cargo data - this structure is now covered in schema
                    logger.debug(
                        f"Processing DepCargo for deputy {safe_log_text(dep_nome)}"
                    )

            # Verify plenary exists before creating composition
            if not plenary or not plenary.id:
                logger.error(
                    f"Invalid plenary object for deputy {safe_log_text(dep_nome)}: {plenary}"
                )
                return False

            # Create plenary composition record
            plenary_composition = PlenaryComposition(
                plenary_id=plenary.id,
                dep_cad_id=self._safe_int(dep_cad_id),
                dep_nome_parlamentar=dep_nome,
                dep_nome_completo=dep_nome_completo,
                org_id=plenary.id_orgao,  # Using plenary's XML ID as org_id (Integer)
            )

            self._add_with_tracking(plenary_composition)
            self._batch_flush()

            # Process videos for this deputy (XIII Legislature structure)
            videos = deputado_data.find("Videos")
            if videos is not None:
                self._process_deputy_videos(
                    videos,
                    deputado.xml_source_id,  # Use Integer XML source ID, not UUID
                    self._safe_int(dep_cad_id),
                    dep_nome,
                    "Plenario",
                    plenary.id_orgao,  # Use Integer organ ID, not UUID
                    plenary.sigla_legislatura,
                )

            return True

        except Exception as e:
            logger.error(f"Error processing deputy plenary membership: {e}")
            # Re-raise critical errors (like foreign key constraints) to ensure data integrity
            # but allow the caller to decide on transaction management
            if (
                "foreign key constraint" in str(e).lower()
                or "integrity" in str(e).lower()
            ):
                logger.error(
                    f"Data integrity issue - plenary {plenary.id} may not exist in database"
                )
                raise
            return False

    def _process_deputy_committee_membership(
        self, deputado_data: ET.Element, committee: Commission
    ) -> bool:
        """Process deputy membership in committee"""
        try:
            dep_id = self._get_text_value(deputado_data, "DepId")
            dep_cad_id = self._get_text_value(deputado_data, "DepCadId")
            dep_nome = self._get_text_value(deputado_data, "DepNomeParlamentar")
            dep_nome_completo = self._get_text_value(deputado_data, "DepNomeCompleto")
            cargo_des = self._get_text_value(deputado_data, "CarDes")

            if not dep_cad_id or not dep_nome:
                return False

            # Map cargo description to standard values
            cargo = self._map_cargo(cargo_des)

            # Get dates
            data_inicio = self._parse_date(
                self._get_text_value(deputado_data, "DtInicio")
            )
            data_fim = self._parse_date(self._get_text_value(deputado_data, "DtFim"))

            if not data_inicio:
                return False

            # Both DepId and DepCadId must be present for data integrity
            if not dep_id or not dep_cad_id:
                raise ValueError(
                    f"Missing required deputy IDs: DepId='{dep_id}', DepCadId='{dep_cad_id}'. Data integrity violation - cannot create artificial IDs"
                )

            # Convert IDs to integers (XML provides strings)
            record_id = self._safe_int(dep_id)
            cadastral_id = self._safe_int(dep_cad_id)
            deputado = self._get_or_create_deputado(
                record_id, cadastral_id, dep_nome, dep_nome_completo,
                xml_context=deputado_data  # Pass XML context for LegDes extraction
            )

            # Create commission historical composition record
            composition = CommissionHistoricalComposition(
                commission_id=committee.id,
                dep_cad_id=self._safe_int(dep_cad_id),
                dep_nome_parlamentar=dep_nome,
                dep_nome_completo=dep_nome_completo,
                org_id=committee.id_orgao,
            )

            self._add_with_tracking(composition)
            return True

        except Exception as e:
            error_msg = f"Error processing deputy committee membership: {e}"
            logger.error(error_msg)
            logger.error("Data integrity issue detected during deputy committee membership processing")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise RuntimeError(f"Data integrity issue: {error_msg}")

    def _process_deputy_subcommittee_membership(
        self, deputado_data: ET.Element, subcommittee: SubCommittee
    ) -> bool:
        """Process deputy membership in subcommittee"""
        try:
            dep_id = self._get_text_value(deputado_data, "DepId")
            dep_cad_id = self._get_text_value(deputado_data, "DepCadId")
            dep_nome = self._get_text_value(deputado_data, "DepNomeParlamentar")
            dep_nome_completo = self._get_text_value(deputado_data, "DepNomeCompleto")
            cargo_des = self._get_text_value(deputado_data, "CarDes")

            if not dep_cad_id or not dep_nome:
                return False

            # Map cargo description to standard values
            cargo = self._map_cargo(cargo_des)

            # Get dates
            data_inicio = self._parse_date(
                self._get_text_value(deputado_data, "DtInicio")
            )
            data_fim = self._parse_date(self._get_text_value(deputado_data, "DtFim"))

            if not data_inicio:
                return False

            # Both DepId and DepCadId must be present for data integrity
            if not dep_id or not dep_cad_id:
                raise ValueError(
                    f"Missing required deputy IDs: DepId='{dep_id}', DepCadId='{dep_cad_id}'. Data integrity violation - cannot create artificial IDs"
                )

            # Convert IDs to integers (XML provides strings)
            record_id = self._safe_int(dep_id)
            cadastral_id = self._safe_int(dep_cad_id)
            deputado = self._get_or_create_deputado(
                record_id, cadastral_id, dep_nome, dep_nome_completo,
                xml_context=deputado_data  # Pass XML context for LegDes extraction
            )

            # Create subcommittee historical composition record
            composition = SubCommitteeHistoricalComposition(
                sub_committee_id=subcommittee.id,
                dep_cad_id=self._safe_int(dep_cad_id),
                dep_nome_parlamentar=dep_nome,
                dep_nome_completo=dep_nome_completo,
                org_id=subcommittee.id_orgao,
            )

            self._add_with_tracking(composition)
            return True

        except Exception as e:
            error_msg = f"Error processing deputy subcommittee membership: {e}"
            logger.error(error_msg)
            logger.error("Data integrity issue detected during deputy subcommittee membership processing")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise RuntimeError(f"Data integrity issue: {error_msg}")

    def _process_deputy_work_group_membership(
        self, deputado_data: ET.Element, work_group: WorkGroup
    ) -> bool:
        """Process deputy membership in work group"""
        try:
            dep_id = self._get_text_value(deputado_data, "DepId")
            dep_cad_id = self._get_text_value(deputado_data, "DepCadId")
            dep_nome = self._get_text_value(deputado_data, "DepNomeParlamentar")
            dep_nome_completo = self._get_text_value(deputado_data, "DepNomeCompleto")
            cargo_des = self._get_text_value(deputado_data, "CarDes")

            if not dep_cad_id or not dep_nome:
                return False

            # Map cargo description to standard values
            cargo = self._map_cargo(cargo_des)

            # Get dates
            data_inicio = self._parse_date(
                self._get_text_value(deputado_data, "DtInicio")
            )
            data_fim = self._parse_date(self._get_text_value(deputado_data, "DtFim"))

            if not data_inicio:
                return False

            # Both DepId and DepCadId must be present for data integrity
            if not dep_id or not dep_cad_id:
                raise ValueError(
                    f"Missing required deputy IDs: DepId='{dep_id}', DepCadId='{dep_cad_id}'. Data integrity violation - cannot create artificial IDs"
                )

            # Convert IDs to integers (XML provides strings)
            record_id = self._safe_int(dep_id)
            cadastral_id = self._safe_int(dep_cad_id)
            deputado = self._get_or_create_deputado(
                record_id, cadastral_id, dep_nome, dep_nome_completo,
                xml_context=deputado_data  # Pass XML context for LegDes extraction
            )

            # Create work group historical composition record
            composition = WorkGroupHistoricalComposition(
                work_group_id=work_group.id,
                dep_cad_id=self._safe_int(dep_cad_id),
                dep_nome_parlamentar=dep_nome,
                dep_nome_completo=dep_nome_completo,
                org_id=work_group.id_orgao,
            )

            self._add_with_tracking(composition)
            return True

        except Exception as e:
            error_msg = f"Error processing deputy work group membership: {e}"
            logger.error(error_msg)
            logger.error("Data integrity issue detected during deputy work group membership processing")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise RuntimeError(f"Data integrity issue: {error_msg}")

    def _process_i_legislature_deputy_composition(
        self, deputado_data: ET.Element, plenary: Plenary, legislatura: Legislatura
    ) -> bool:
        """Process I Legislature deputy composition with DadosDeputadoSearch structure"""
        try:
            # Extract deputy information
            dep_id = self._get_text_value(deputado_data, "depId")
            dep_cad_id = self._get_text_value(deputado_data, "depCadId")
            dep_nome_parlamentar = self._get_text_value(
                deputado_data, "depNomeParlamentar"
            )
            dep_nome_completo = self._get_text_value(deputado_data, "depNomeCompleto")
            dep_cp_id = self._get_text_value(deputado_data, "depCPId")
            dep_cp_des = self._get_text_value(deputado_data, "depCPDes")
            leg_des = self._get_text_value(deputado_data, "legDes")

            if not dep_cad_id or not dep_nome_parlamentar:
                return False

            # Get or create deputy using both record_id and cadastral_id
            record_id = self._safe_int(dep_id)
            cadastral_id = self._safe_int(dep_cad_id)
            deputado = self._get_or_create_deputado(
                record_id, cadastral_id, dep_nome_parlamentar, dep_nome_completo,
                xml_context=deputado_data  # Pass XML context for LegDes extraction
            )

            # Process parliamentary group information (depGP)
            dep_gp = deputado_data.find("depGP")
            if dep_gp is not None:
                self._process_deputy_gp_situation(dep_gp, deputado, legislatura)

            # Process deputy situation information (depSituacao)
            dep_situacao = deputado_data.find("depSituacao")
            if dep_situacao is not None:
                # Handle multiple situation records
                for situacao_item in dep_situacao.findall(
                    "pt_ar_wsgode_objectos_DadosSituacaoDeputado"
                ):
                    self._process_deputy_situation_record(
                        situacao_item, deputado, legislatura
                    )

            # Create plenary composition record
            composition = PlenaryComposition(
                plenary_id=plenary.id,
                leg_des=leg_des,
                dep_id=self._safe_int(dep_id) if dep_id else None,
                dep_cad_id=self._safe_int(dep_cad_id) if dep_cad_id else None,
                dep_nome_parlamentar=dep_nome_parlamentar,
                dep_nome_completo=dep_nome_completo,
                org_id=plenary.id_orgao,  # Using plenary's XML ID as org_id (Integer)
            )

            self._add_with_tracking(composition)
            return True

        except Exception as e:
            error_msg = f"Error processing I Legislature deputy composition: {e}"
            logger.error(error_msg)
            logger.error("Data integrity issue detected during I Legislature deputy composition processing")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise RuntimeError(f"Data integrity issue: {error_msg}")

    def _get_deputado_and_legislatura_from_data(
        self, data_element: ET.Element
    ) -> tuple:
        """Extract deputado and legislatura from data element"""
        try:
            # Extract deputy data with explicit field mapping
            dep_id = self._get_int_value(data_element, "DepId") or self._get_int_value(
                data_element, "depId"
            )
            dep_cad_id = self._get_int_value(data_element, "DepCadId")
            dep_nome_parlamentar = self._get_text_value(data_element, "DepNomeParlamentar")
            dep_nome_completo = self._get_text_value(data_element, "DepNomeCompleto")

            if dep_cad_id and dep_nome_parlamentar:
                # Get or create deputy using both record_id and cadastral_id
                record_id = dep_id if dep_id else dep_cad_id
                deputado = self._get_or_create_deputado(
                    record_id, dep_cad_id, dep_nome_parlamentar, dep_nome_completo,
                    xml_context=data_element  # Pass XML context for LegDes extraction
                )

                # Get legislatura from file context
                legislatura_sigla = self._extract_legislatura(
                    self.file_info.get("file_path", ""), None
                )
                legislatura = self._get_or_create_legislatura(legislatura_sigla)

                return deputado, legislatura
            else:
                logger.debug(
                    f"Could not extract deputy info: dep_cad_id={dep_cad_id}, dep_nome_parlamentar={dep_nome_parlamentar}"
                )
                return None, None
        except Exception as e:
            logger.warning(f"Error extracting deputado and legislatura: {e}")
            return None, None

    def _process_gp_situations(
        self,
        dep_gp: ET.Element,
        deputado=None,
        legislatura=None,
        composition_type=None,
        **kwargs,
    ) -> bool:
        """Process deputy parliamentary group situation for various organ compositions"""
        if dep_gp is None:
            logger.warning("Empty dep_gp element provided")
            return True

        # Check if we have the required context - if not, try to get it from composition context
        if not deputado or not legislatura:
            # Try to extract from composition context in kwargs
            for key, value in kwargs.items():
                if key.endswith("_composition") and hasattr(value, "__dict__"):
                    # Try to get parent element that might have deputy data
                    parent_element = getattr(value, "_source_element", None)
                    if parent_element is not None:
                        deputado, legislatura = (
                            self._get_deputado_and_legislatura_from_data(parent_element)
                        )
                        if deputado and legislatura:
                            break

            # If still missing, log and return
            if not deputado or not legislatura:
                logger.debug(
                    f"Missing required context for GP processing: deputado={'present' if deputado else 'None'}, legislatura={'present' if legislatura else 'None'}"
                )
                return True

        try:
            # Get composition context from kwargs (for backward compatibility)
            composition = None

            for key, value in kwargs.items():
                if key.endswith("_composition"):
                    composition = value
                    if not composition_type:
                        composition_type = key.replace("_composition", "")
                    break

            # Handle different GP structure patterns - optimized approach
            gp_situations = dep_gp.findall("DadosSituacaoGP") + dep_gp.findall(
                "pt_ar_wsgode_objectos_DadosSituacaoGP"
            )

            # Process each GP situation found
            for gp_situacao in gp_situations:
                gp_data = self._extract_gp_data(gp_situacao)

                if (
                    gp_data["gp_id"]
                    and gp_data["gp_sigla"]
                    and deputado
                    and legislatura
                ):
                    # Safe integer conversion for GP ID
                    gp_id_int = DataValidationUtils.safe_int_convert(gp_data["gp_id"])
                    if gp_id_int:
                        # Create DeputyGPSituation record
                        gp_record = DeputyGPSituation(
                            deputado_id=deputado.id,
                            legislatura_id=legislatura.id,
                            gp_id=gp_id_int,
                            gp_sigla=gp_data["gp_sigla"],
                            gp_dt_inicio=gp_data["gp_dt_inicio"],
                            gp_dt_fim=gp_data["gp_dt_fim"],
                            composition_context=composition_type,
                        )
                        self._add_with_tracking(gp_record)
                        self._batch_flush()  # Ensure immediate persistence
                        logger.debug(
                            f"Created GP situation record: {gp_data['gp_sigla']} (ID: {gp_id_int}) for {composition_type}"
                        )
                    else:
                        logger.warning(f"Invalid GP ID format: {gp_data['gp_id']}")
                elif gp_data["gp_id"] and gp_data["gp_sigla"]:
                    logger.debug(
                        f"Processing GP situation: {gp_data['gp_sigla']} (ID: {gp_data['gp_id']}) - missing context"
                    )

            return True

        except ValueError as ve:
            logger.error(f"Data validation error in GP situations: {ve}")
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error processing GP situations: {e}", exc_info=True
            )
            return False

    def _extract_gp_data(self, gp_situacao: ET.Element) -> Dict:
        """Extract GP situation data from XML element"""
        return {
            "gp_id": self._get_text_value(gp_situacao, "gpId")
            or self._get_text_value(gp_situacao, "GpId"),
            "gp_sigla": self._get_text_value(gp_situacao, "gpSigla")
            or self._get_text_value(gp_situacao, "GpSigla"),
            "gp_dt_inicio": self._parse_date(
                self._get_text_value(gp_situacao, "gpDtInicio")
                or self._get_text_value(gp_situacao, "GpDtInicio")
            ),
            "gp_dt_fim": self._parse_date(
                self._get_text_value(gp_situacao, "gpDtFim")
                or self._get_text_value(gp_situacao, "GpDtFim")
            ),
        }

    def _process_deputy_gp_situation(
        self, dep_gp: ET.Element, deputado: Deputado, legislatura: Legislatura
    ) -> bool:
        """Process deputy parliamentary group situation for I Legislature"""
        try:
            # Handle multiple GP situations
            for gp_situacao in dep_gp.findall("pt_ar_wsgode_objectos_DadosSituacaoGP"):
                gp_id = self._get_text_value(gp_situacao, "gpId")
                gp_sigla = self._get_text_value(gp_situacao, "gpSigla")
                gp_dt_inicio = self._get_text_value(gp_situacao, "gpDtInicio")
                gp_dt_fim = self._get_text_value(gp_situacao, "gpDtFim")

                if gp_id and gp_sigla:
                    # Create or update parliamentary group situation
                    gp_record = DeputyGPSituation(
                        deputado_id=deputado.id,
                        legislatura_id=legislatura.id,
                        gp_id=self._safe_int(gp_id),
                        gp_sigla=gp_sigla,
                        gp_dt_inicio=(
                            self._parse_date(gp_dt_inicio) if gp_dt_inicio else None
                        ),
                        gp_dt_fim=self._parse_date(gp_dt_fim) if gp_dt_fim else None,
                    )
                    self._add_with_tracking(gp_record)

            return True

        except Exception as e:
            logger.error(f"Error processing deputy GP situation: {e}")
            return False

    def _process_deputy_situation_record(
        self, situacao_data: ET.Element, deputado: Deputado, legislatura: Legislatura
    ) -> bool:
        """Process individual deputy situation record for I Legislature"""
        try:
            sio_des = self._get_text_value(situacao_data, "sioDes")
            sio_dt_inicio = self._get_text_value(situacao_data, "sioDtInicio")
            sio_dt_fim = self._get_text_value(situacao_data, "sioDtFim")

            if sio_des:
                # Create deputy situation record
                situacao_record = DeputySituation(
                    deputado_id=deputado.id,
                    legislatura_id=legislatura.id,
                    sio_des=sio_des,
                    sio_dt_inicio=(
                        self._parse_date(sio_dt_inicio) if sio_dt_inicio else None
                    ),
                    sio_dt_fim=self._parse_date(sio_dt_fim) if sio_dt_fim else None,
                )
                self._add_with_tracking(situacao_record)

            return True

        except Exception as e:
            logger.error(f"Error processing deputy situation record: {e}")
            return False

    def _process_i_legislature_orgao(
        self, orgao: ET.Element, legislatura: Legislatura
    ) -> bool:
        """Process I Legislature Orgao structure (committee)"""
        try:
            # Extract organ details from I Legislature structure
            detalhe_orgao = orgao.find("DetalheOrgao")
            if detalhe_orgao is None:
                return False

            # I Legislature uses different field names
            id_orgao = self._get_text_value(detalhe_orgao, "idOrgao")
            sigla_orgao = self._get_text_value(detalhe_orgao, "siglaOrgao")
            nome_sigla = self._get_text_value(detalhe_orgao, "nomeSigla")
            numero_orgao = self._get_text_value(detalhe_orgao, "numeroOrgao")
            sigla_legislatura = self._get_text_value(detalhe_orgao, "siglaLegislatura")

            if not id_orgao or not nome_sigla:
                return False

            # Create or get committee record using I Legislature data
            committee = self._get_or_create_committee(
                self._safe_int(id_orgao), sigla_orgao, nome_sigla, legislatura
            )

            # Process I Legislature committee meetings if present
            reunioes = orgao.find("Reunioes")
            if reunioes is not None:
                for dados_reuniao in reunioes.findall(
                    "pt_ar_wsgode_objectos_DadosReuniao"
                ):
                    self._process_i_legislature_committee_meeting(
                        dados_reuniao, committee
                    )

            logger.info(
                f"Processed I Legislature committee: {safe_log_text(nome_sigla)} (ID: {id_orgao})"
            )
            return True

        except Exception as e:
            logger.error(f"Error processing I Legislature Orgao: {e}")
            return False

    def _process_i_legislature_committee_meeting(
        self, dados_reuniao: ET.Element, committee: Commission
    ) -> bool:
        """Process I Legislature committee meeting data"""
        try:
            # Extract I Legislature meeting data
            reu_id = self._get_text_value(dados_reuniao, "reuId")
            reu_tar_id = self._get_text_value(dados_reuniao, "reuTarId")
            reu_tar_sigla = self._get_text_value(dados_reuniao, "reuTarSigla")
            reu_tar_des = self._get_text_value(dados_reuniao, "reuTarDes")
            reu_tir_des = self._get_text_value(dados_reuniao, "reuTirDes")
            reu_numero = self._get_text_value(dados_reuniao, "reuNumero")
            reu_data_hora = self._get_text_value(dados_reuniao, "reuDataHora")
            reu_final_plenario = self._get_text_value(dados_reuniao, "reuFinalPlenario")

            # Create meeting record with I Legislature data
            meeting = OrganMeeting(
                commission_id=committee.id,
                reu_id=self._safe_int(reu_id) if reu_id else None,
                reu_numero=self._safe_int(reu_numero) if reu_numero else None,
                reu_data_hora=reu_data_hora,
                reu_tipo=reu_tir_des,
                reu_local=None,  # Not available in I Legislature structure
                reu_estado=None,  # Not available in I Legislature structure
                # Use existing fields for I Legislature specific data
                reu_tar_sigla=reu_tar_sigla,
                reu_final_plenario=(
                    reu_final_plenario == "true" if reu_final_plenario else None
                ),
                # Store additional I Legislature data in available fields
                reu_tir_des=reu_tar_des,  # Store reu_tar_des in reu_tir_des field
            )

            self._add_with_tracking(meeting)
            return True

        except Exception as e:
            logger.error(f"Error processing I Legislature committee meeting: {e}")
            return False

    def _get_or_create_parliamentary_organization(
        self, legislatura: Legislatura
    ) -> ParliamentaryOrganization:
        """Get or create parliamentary organization for the given legislature (cached)"""
        # Check cache first
        if legislatura.numero in self._org_cache:
            return self._org_cache[legislatura.numero]

        organization = (
            self.session.query(ParliamentaryOrganization)
            .filter_by(legislatura_sigla=legislatura.numero)
            .first()
        )

        if organization:
            self._org_cache[legislatura.numero] = organization
            return organization

        # Create new parliamentary organization
        organization = ParliamentaryOrganization(
            legislatura_sigla=legislatura.numero,
            xml_file_path=getattr(self, "xml_file", None),
        )

        self._add_with_tracking(organization)
        self._batch_flush(force=True)  # Need ID for foreign keys
        self._org_cache[legislatura.numero] = organization
        return organization

    def _get_or_create_plenary(
        self, id_externo: int, sigla: str, nome: str, legislatura: Legislatura
    ) -> Plenary:
        """Get or create plenary record (cached)"""
        # First get or create parliamentary organization
        organization = self._get_or_create_parliamentary_organization(legislatura)

        # Check cache first
        cache_key = (id_externo, organization.id)
        if cache_key in self._plenary_cache:
            return self._plenary_cache[cache_key]

        plenary = (
            self.session.query(Plenary)
            .filter_by(id_orgao=id_externo, organization_id=organization.id)
            .first()
        )

        if plenary:
            self._plenary_cache[cache_key] = plenary
            return plenary

        # Create new plenary
        plenary = Plenary(
            organization_id=organization.id,
            id_orgao=id_externo,
            sigla_orgao=sigla,
            nome_sigla=nome,
            sigla_legislatura=legislatura.numero,
        )

        self._add_with_tracking(plenary)
        self._batch_flush(force=True)  # Need ID for foreign keys

        # Validate the plenary was created successfully
        if not plenary.id:
            raise ValueError(f"Failed to create plenary for organ {id_externo}")

        self._plenary_cache[cache_key] = plenary
        logger.debug(f"Created plenary {plenary.id} for organ {id_externo}")
        return plenary

    def _get_or_create_committee(
        self, id_externo: int, sigla: str, nome: str, legislatura: Legislatura
    ) -> Commission:
        """Get or create committee record (cached)"""
        # First get or create parliamentary organization
        organization = self._get_or_create_parliamentary_organization(legislatura)

        # Check cache first
        cache_key = (id_externo, organization.id)
        if cache_key in self._committee_cache:
            return self._committee_cache[cache_key]

        committee = (
            self.session.query(Commission)
            .filter_by(id_orgao=id_externo, organization_id=organization.id)
            .first()
        )

        if committee:
            self._committee_cache[cache_key] = committee
            return committee

        # Create new committee
        committee = Commission(
            organization_id=organization.id,
            id_orgao=id_externo,
            sigla_orgao=sigla,
            nome_sigla=nome,
            sigla_legislatura=legislatura.numero,
        )

        self._add_with_tracking(committee)
        self._batch_flush(force=True)  # Need ID for foreign keys
        self._committee_cache[cache_key] = committee
        return committee

    def _get_or_create_subcommittee(
        self, id_externo: int, sigla: str, nome: str, legislatura: Legislatura
    ) -> SubCommittee:
        """Get or create subcommittee record (cached)"""
        # First get or create parliamentary organization
        organization = self._get_or_create_parliamentary_organization(legislatura)

        # Check cache first
        cache_key = (id_externo, organization.id)
        if cache_key in self._subcommittee_cache:
            return self._subcommittee_cache[cache_key]

        subcommittee = (
            self.session.query(SubCommittee)
            .filter_by(id_orgao=id_externo, organization_id=organization.id)
            .first()
        )

        if subcommittee:
            self._subcommittee_cache[cache_key] = subcommittee
            return subcommittee

        # Create new subcommittee
        subcommittee = SubCommittee(
            organization_id=organization.id,
            id_orgao=id_externo,
            sigla_orgao=sigla,
            nome_sigla=nome,
            sigla_legislatura=legislatura.numero,
        )

        self._add_with_tracking(subcommittee)
        self._batch_flush(force=True)  # Need ID for foreign keys
        self._subcommittee_cache[cache_key] = subcommittee
        return subcommittee

    def _get_or_create_work_group(
        self, id_externo: int, sigla: str, nome: str, legislatura: Legislatura
    ) -> WorkGroup:
        """Get or create work group record (cached)"""
        # First get or create parliamentary organization
        organization = self._get_or_create_parliamentary_organization(legislatura)

        # Check cache first
        cache_key = (id_externo, organization.id)
        if cache_key in self._work_group_cache:
            return self._work_group_cache[cache_key]

        work_group = (
            self.session.query(WorkGroup)
            .filter_by(id_orgao=id_externo, organization_id=organization.id)
            .first()
        )

        if work_group:
            self._work_group_cache[cache_key] = work_group
            return work_group

        # Create new work group
        work_group = WorkGroup(
            organization_id=organization.id,
            id_orgao=id_externo,
            sigla_orgao=sigla,
            nome_sigla=nome,
            sigla_legislatura=legislatura.numero,
        )

        self._add_with_tracking(work_group)
        self._batch_flush(force=True)  # Need ID for foreign keys
        self._work_group_cache[cache_key] = work_group
        return work_group

    # _get_or_create_deputado method now inherited from enhanced base mapper

    def _map_cargo(self, cargo_des: str) -> str:
        """Map cargo description to standard values"""
        if not cargo_des:
            return "membro"

        cargo_lower = cargo_des.lower()
        if "presidente" in cargo_lower:
            return "presidente"
        elif "vice" in cargo_lower:
            return "vice_presidente"
        elif "secretário" in cargo_lower or "secretario" in cargo_lower:
            return "secretario"
        else:
            return "membro"

    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to ISO format - using common utilities"""
        if not date_str:
            return None
        parsed_date = DataValidationUtils.parse_date_flexible(date_str)
        return parsed_date.strftime("%Y-%m-%d") if parsed_date else None

    def _extract_detalhe_orgao_data(self, detalhe_orgao: ET.Element) -> Dict[str, str]:
        """
        Extract organ detail data from DetalheOrgao element supporting dual formats.

        Handles two different XML formats:
        - Format 1 (newer): orgId, orgSigla, orgDes, orgNumero, orgTioId, orgSuoId, legDes
        - Format 2 (older): idOrgao, siglaOrgao, nomeSigla, numeroOrgao, siglaLegislatura

        Returns:
            Dict with standardized keys: id_orgao, sigla_orgao, nome_sigla, numero_orgao, sigla_legislatura
        """
        if detalhe_orgao is None:
            return {}

        # Try newer format first, fall back to older format
        id_orgao = self._get_text_value(detalhe_orgao, "orgId") or self._get_text_value(
            detalhe_orgao, "idOrgao"
        )

        sigla_orgao = self._get_text_value(
            detalhe_orgao, "orgSigla"
        ) or self._get_text_value(detalhe_orgao, "siglaOrgao")

        nome_sigla = self._get_text_value(
            detalhe_orgao, "orgDes"
        ) or self._get_text_value(detalhe_orgao, "nomeSigla")

        numero_orgao = self._get_text_value(
            detalhe_orgao, "orgNumero"
        ) or self._get_text_value(detalhe_orgao, "numeroOrgao")

        sigla_legislatura = self._get_text_value(
            detalhe_orgao, "legDes"
        ) or self._get_text_value(detalhe_orgao, "siglaLegislatura")

        # Additional newer format fields
        org_tio_id = self._get_text_value(detalhe_orgao, "orgTioId")
        org_suo_id = self._get_text_value(detalhe_orgao, "orgSuoId")

        return {
            "id_orgao": id_orgao,
            "sigla_orgao": sigla_orgao,
            "nome_sigla": nome_sigla,
            "numero_orgao": numero_orgao,
            "sigla_legislatura": sigla_legislatura,
            "org_tio_id": org_tio_id,
            "org_suo_id": org_suo_id,
        }

    def _process_mesa_ar(self, mesa_ar: ET.Element, legislatura: Legislatura) -> bool:
        """Process AR Board (Mesa da Assembleia da República)"""
        try:
            detalhe_orgao = mesa_ar.find("DetalheOrgao")
            if detalhe_orgao is None:
                return False

            # Extract organ details using the flexible dual-format method
            orgao_data = self._extract_detalhe_orgao_data(detalhe_orgao)

            id_orgao = orgao_data["id_orgao"]
            sigla_orgao = orgao_data["sigla_orgao"]
            nome_sigla = orgao_data["nome_sigla"]
            numero_orgao = orgao_data["numero_orgao"]
            sigla_legislatura = orgao_data["sigla_legislatura"]

            # For Mesa AR, use sigla_orgao as fallback for nome_sigla
            if not nome_sigla and sigla_orgao:
                nome_sigla = sigla_orgao

            # Validate required fields
            if not sigla_orgao:
                raise ValueError(
                    f"Missing required organ identifier in both formats: orgSigla/siglaOrgao='{sigla_orgao}'. Data integrity violation - cannot generate artificial identifiers"
                )

            if not id_orgao:
                raise ValueError(
                    f"Missing required organ identifier in both formats: orgId/idOrgao='{id_orgao}'. Data integrity violation - cannot generate artificial identifiers"
                )

            # Create or get AR Board record
            ar_board = self._get_or_create_ar_board(
                self._safe_int(id_orgao),
                sigla_orgao,
                nome_sigla,
                numero_orgao,
                legislatura,
            )

            # Process members
            composicao = mesa_ar.find("Composicao")
            if composicao is not None:
                for deputado_data in composicao.findall("DadosDeputadoOrgao"):
                    self._process_deputy_ar_board_membership(deputado_data, ar_board)

            # Process historical composition (IX Legislature)
            historico_composicao = mesa_ar.find("HistoricoComposicaoMesa")
            if historico_composicao is not None:
                for historico_data in historico_composicao.findall(
                    "pt_ar_wsgode_objectos_DadosMesaComposicaoHistorico"
                ):
                    self._process_ar_board_historical_composition(
                        historico_data, ar_board, legislatura
                    )

            return True

        except Exception as e:
            logger.error(f"Error processing Mesa AR: {e}")
            return False

    def _process_conselho_administracao(
        self, conselho: ET.Element, legislatura: Legislatura
    ) -> bool:
        """Process Administrative Council"""
        try:
            detalhe_orgao = conselho.find("DetalheOrgao")
            if detalhe_orgao is None:
                return False

            id_orgao = self._get_text_value(detalhe_orgao, "idOrgao")
            sigla_orgao = self._get_text_value(detalhe_orgao, "siglaOrgao")
            nome_sigla = self._get_text_value(detalhe_orgao, "nomeSigla")
            if not sigla_orgao or not nome_sigla:
                raise ValueError(
                    f"Missing required organ identifiers: siglaOrgao='{sigla_orgao}', nomeSigla='{nome_sigla}'. Data integrity violation - cannot generate artificial identifiers"
                )
            numero_orgao = self._get_text_value(detalhe_orgao, "numeroOrgao")

            if not id_orgao:
                return False

            # Create or get Administrative Council record
            admin_council = self._get_or_create_administrative_council(
                self._safe_int(id_orgao),
                sigla_orgao,
                nome_sigla,
                numero_orgao,
                legislatura,
            )

            # Process members
            composicao = conselho.find("Composicao")
            if composicao is not None:
                for deputado_data in composicao.findall("DadosDeputadoOrgao"):
                    self._process_deputy_admin_council_membership(
                        deputado_data, admin_council
                    )

            # Process historical composition (I Legislature and XIII Legislature)
            historico_composicao = conselho.find("HistoricoComposicao")
            if historico_composicao is not None:
                logger.info(
                    f"Processing AdministrativeCouncil HistoricoComposicao for {legislatura.numero} Legislature"
                )
                for historico_data in historico_composicao.findall(
                    "pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico"
                ):
                    self._process_admin_council_historical_composition(
                        historico_data, admin_council, legislatura
                    )

            return True

        except Exception as e:
            logger.error(f"Error processing Administrative Council: {e}")
            return False

    def _process_comissao_permanente(
        self, comissao: ET.Element, legislatura: Legislatura
    ) -> bool:
        """Process Permanent Committee"""
        try:
            detalhe_orgao = comissao.find("DetalheOrgao")
            if detalhe_orgao is None:
                return False

            id_orgao = self._get_text_value(detalhe_orgao, "idOrgao")
            sigla_orgao = self._get_text_value(detalhe_orgao, "siglaOrgao")
            nome_sigla = self._get_text_value(detalhe_orgao, "nomeSigla")
            if not sigla_orgao or not nome_sigla:
                raise ValueError(
                    f"Missing required organ identifiers: siglaOrgao='{sigla_orgao}', nomeSigla='{nome_sigla}'. Data integrity violation - cannot generate artificial identifiers"
                )
            numero_orgao = self._get_text_value(detalhe_orgao, "numeroOrgao")

            if not id_orgao:
                return False

            # Create or get Permanent Committee record
            permanent_committee = self._get_or_create_permanent_committee(
                self._safe_int(id_orgao),
                sigla_orgao,
                nome_sigla,
                numero_orgao,
                legislatura,
            )

            # Process members
            composicao = comissao.find("Composicao")
            if composicao is not None:
                for deputado_data in composicao.findall("DadosDeputadoOrgao"):
                    self._process_deputy_permanent_committee_membership(
                        deputado_data, permanent_committee
                    )

            # Process historical composition (VI Legislature and others)
            historico_composicao = comissao.find("HistoricoComposicao")
            if historico_composicao is not None:
                logger.info(
                    f"Processing PermanentCommittee HistoricoComposicao for {legislatura.numero} Legislature"
                )
                for dados_historico in historico_composicao.findall(
                    "pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico"
                ):
                    success = self._process_permanent_committee_historical_composition(
                        dados_historico, permanent_committee, legislatura
                    )
                    if not success:
                        logger.warning(
                            f"Failed to process permanent committee historical composition for {sigla_orgao}"
                        )

            return True

        except Exception as e:
            logger.error(f"Error processing Permanent Committee: {e}")
            return False

    def _process_conferencia_lideres(
        self, conferencia: ET.Element, legislatura: Legislatura
    ) -> bool:
        """Process Leader Conference"""
        try:
            detalhe_orgao = conferencia.find("DetalheOrgao")
            if detalhe_orgao is None:
                return False

            id_orgao = self._get_text_value(detalhe_orgao, "idOrgao")
            sigla_orgao = self._get_text_value(detalhe_orgao, "siglaOrgao")
            nome_sigla = self._get_text_value(detalhe_orgao, "nomeSigla")
            if not sigla_orgao or not nome_sigla:
                raise ValueError(
                    f"Missing required organ identifiers: siglaOrgao='{sigla_orgao}', nomeSigla='{nome_sigla}'. Data integrity violation - cannot generate artificial identifiers"
                )
            numero_orgao = self._get_text_value(detalhe_orgao, "numeroOrgao")

            if not id_orgao:
                return False

            # Create or get Leader Conference record
            leader_conference = self._get_or_create_leader_conference(
                self._safe_int(id_orgao),
                sigla_orgao,
                nome_sigla,
                numero_orgao,
                legislatura,
            )

            # Process members
            composicao = conferencia.find("Composicao")
            if composicao is not None:
                for deputado_data in composicao.findall("DadosDeputadoOrgao"):
                    self._process_deputy_leader_conference_membership(
                        deputado_data, leader_conference
                    )

            # Process historical composition (I Legislature and XIII Legislature)
            historico_composicao = conferencia.find("HistoricoComposicao")
            if historico_composicao is not None:
                logger.info(
                    f"Processing LeaderConference HistoricoComposicao for {legislatura.numero} Legislature"
                )
                for historico_data in historico_composicao.findall(
                    "pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico"
                ):
                    self._process_leader_conference_historical_composition(
                        historico_data, leader_conference, legislatura
                    )

            return True

        except Exception as e:
            logger.error(f"Error processing Leader Conference: {e}")
            return False

    def _process_conferencia_presidentes_comissoes(
        self, conferencia: ET.Element, legislatura: Legislatura
    ) -> bool:
        """Process Commission Presidents Conference"""
        try:
            # First get or create parliamentary organization
            organization = self._get_or_create_parliamentary_organization(legislatura)

            # Process DetalheOrgao structure (XIII Legislature) to get basic conference details
            detalhe_orgao = conferencia.find("DetalheOrgao")
            conference = None

            if detalhe_orgao is not None:
                # Extract organ details from DetalheOrgao
                id_orgao = self._get_int_value(detalhe_orgao, "idOrgao")
                sigla_orgao = self._get_text_value(detalhe_orgao, "siglaOrgao")
                nome_sigla = self._get_text_value(detalhe_orgao, "nomeSigla")
                numero_orgao = self._get_int_value(detalhe_orgao, "numeroOrgao")
                sigla_legislatura = self._get_text_value(
                    detalhe_orgao, "siglaLegislatura"
                )

                logger.info(
                    f"Processing ConferenciaPresidentesComissoes DetalheOrgao: {safe_log_text(sigla_orgao)} for {safe_log_text(sigla_legislatura)}"
                )

                # Create or get conference record with DetalheOrgao data
                conference = self._get_or_create_commission_president_conference(
                    id_orgao,
                    sigla_orgao,
                    nome_sigla,
                    numero_orgao,
                    sigla_legislatura,
                    organization,
                )

            # Process historical composition (I Legislature HistoricoComposicaoCPC)
            historico_composicao = conferencia.find("HistoricoComposicaoCPC")
            if historico_composicao is not None:
                logger.info(
                    f"Processing ConferenciaPresidentesComissoes HistoricoComposicaoCPC for I Legislature"
                )
                for dados_pcp in historico_composicao.findall(
                    "pt_ar_wsgode_objectos_DadosPCPComposicaoHistorico"
                ):
                    # Process each commission president historical record
                    # This complex structure includes deputy info, GP data, cargo data, situation data, and presOrgao data
                    # The processing logic would extract all the detailed fields we've added to the schema
                    logger.debug(f"Processing DadosPCPComposicaoHistorico record")

            return True

        except Exception as e:
            logger.error(f"Error processing Commission Presidents Conference: {e}")
            return False

    def _process_organ_meeting(self, reuniao: ET.Element, **kwargs) -> bool:
        """Process organ meeting (Reuniao) - can be associated with different organ types"""
        try:
            # Extract meeting data
            reu_tar_sigla = self._get_text_value(reuniao, "ReuTarSigla")
            reu_local = self._get_text_value(reuniao, "ReuLocal")
            reu_data_str = self._get_text_value(reuniao, "ReuData")
            reu_hora = self._get_text_value(reuniao, "ReuHora")
            reu_tipo = self._get_text_value(reuniao, "ReuTipo")
            reu_estado = self._get_text_value(reuniao, "ReuEstado")

            # Parse date
            reu_data = None
            if reu_data_str:
                try:
                    # Assume format DD/MM/YYYY or similar
                    if "/" in reu_data_str:
                        day, month, year = reu_data_str.split("/")
                        from datetime import date

                        reu_data = date(
                            self._safe_int(year),
                            self._safe_int(month),
                            self._safe_int(day),
                        )
                    elif "-" in reu_data_str:
                        # ISO format YYYY-MM-DD
                        from datetime import date

                        year, month, day = reu_data_str.split("-")
                        reu_data = date(
                            self._safe_int(year),
                            self._safe_int(month),
                            self._safe_int(day),
                        )
                except (ValueError, IndexError):
                    logger.warning(f"Could not parse meeting date: {reu_data_str}")

            # Create meeting record - determine which organ type this is for
            meeting = OrganMeeting(
                commission_id=(
                    kwargs.get("commission").id if kwargs.get("commission") else None
                ),
                work_group_id=(
                    kwargs.get("work_group").id if kwargs.get("work_group") else None
                ),
                permanent_committee_id=(
                    kwargs.get("permanent_committee").id
                    if kwargs.get("permanent_committee")
                    else None
                ),
                sub_committee_id=(
                    kwargs.get("sub_committee").id
                    if kwargs.get("sub_committee")
                    else None
                ),
                # Note: Plenary meetings would need a separate field in the model
                reu_tar_sigla=reu_tar_sigla,
                reu_local=reu_local,
                reu_data=reu_data,
                reu_hora=reu_hora,
                reu_tipo=reu_tipo,
                reu_estado=reu_estado,
            )

            self._add_with_tracking(meeting)
            return True

        except Exception as e:
            logger.error(f"Error processing organ meeting: {e}")
            return False

    def _process_orgao_base(
        self, orgao_base: ET.Element, legislatura: Legislatura
    ) -> bool:
        """Process OrgaoBase structure (III Legislature committees)"""
        try:
            detalhe_orgao = orgao_base.find("DetalheOrgao")
            if detalhe_orgao is None:
                return False

            id_orgao = self._get_text_value(detalhe_orgao, "idOrgao")
            sigla_orgao = self._get_text_value(detalhe_orgao, "siglaOrgao")
            nome_sigla = self._get_text_value(detalhe_orgao, "nomeSigla")
            numero_orgao = self._get_text_value(detalhe_orgao, "numeroOrgao")

            if not id_orgao or not sigla_orgao:
                return False

            # Create or get committee record
            committee = self._get_or_create_committee(
                self._safe_int(id_orgao), sigla_orgao, nome_sigla, legislatura
            )

            # Process members
            composicao = orgao_base.find("Composicao")
            if composicao is not None:
                for deputado_data in composicao.findall("DadosDeputadoOrgaoComissao"):
                    self._process_deputy_committee_membership(deputado_data, committee)

            # Process meetings with namespace structure
            reunioes = orgao_base.find("Reunioes")
            if reunioes is not None:
                for dados_reuniao in reunioes.findall(
                    "pt_ar_wsgode_objectos_DadosReuniao"
                ):
                    self._process_organ_meeting_namespace(
                        dados_reuniao, committee=committee
                    )

            return True

        except Exception as e:
            logger.error(f"Error processing OrgaoBase: {e}")
            return False

    def _process_working_group_orgao_base(
        self, orgao_base: ET.Element, legislatura: Legislatura
    ) -> bool:
        """Process VIII Legislature working group OrgaoBase structure"""
        try:
            detalhe_orgao = orgao_base.find("DetalheOrgao")
            if detalhe_orgao is None:
                return False

            id_orgao = self._get_text_value(detalhe_orgao, "idOrgao")
            sigla_orgao = self._get_text_value(detalhe_orgao, "siglaOrgao")
            nome_sigla = self._get_text_value(detalhe_orgao, "nomeSigla")
            numero_orgao = self._get_text_value(detalhe_orgao, "numeroOrgao")
            sigla_legislatura = self._get_text_value(detalhe_orgao, "siglaLegislatura")

            if not id_orgao or not sigla_orgao:
                return False

            # Create or get working group record
            work_group = self._get_or_create_work_group(
                self._safe_int(id_orgao), sigla_orgao, nome_sigla, legislatura
            )

            # Process historical composition (VIII Legislature structure)
            historico_composicao = orgao_base.find("HistoricoComposicao")
            if historico_composicao is not None:
                for dados_historico in historico_composicao.findall(
                    "pt_ar_wsgode_objectos_DadosOrgaoComposicaoHistorico"
                ):
                    success = self._process_work_group_historical_composition(
                        dados_historico, work_group, legislatura
                    )
                    if not success:
                        logger.warning(
                            f"Failed to process working group historical composition for {sigla_orgao}"
                        )

            # Process meetings (VIII Legislature structure)
            reunioes = orgao_base.find("Reunioes")
            if reunioes is not None:
                for dados_reuniao in reunioes.findall(
                    "pt_ar_wsgode_objectos_DadosReuniao"
                ):
                    self._process_organ_meeting_namespace(
                        dados_reuniao, work_group=work_group
                    )

            return True

        except Exception as e:
            logger.error(f"Error processing working group OrgaoBase: {e}")
            return False

    def _process_reuniao_plenario(
        self, reuniao_plenario: ET.Element, plenary, legislatura: Legislatura = None
    ) -> bool:
        """Process ReuniaoPlenario structure (III Legislature and I Legislature plenary meetings)"""
        try:
            # Process the main meeting data
            reuniao = reuniao_plenario.find("Reuniao")
            if reuniao is not None:
                # Extract meeting information
                sel_numero = self._get_text_value(reuniao, "selNumero")
                reu_data_str = self._get_text_value(reuniao, "reuData")
                reu_hora = self._get_text_value(reuniao, "reuHora")
                reu_local = self._get_text_value(reuniao, "reuLocal")
                reu_tipo = self._get_text_value(reuniao, "reuTipo")
                reu_estado = self._get_text_value(reuniao, "reuEstado")

                # Parse date
                reu_data = None
                if reu_data_str:
                    try:
                        if "/" in reu_data_str:
                            day, month, year = reu_data_str.split("/")
                            from datetime import date

                            reu_data = date(
                                self._safe_int(year),
                                self._safe_int(month),
                                self._safe_int(day),
                            )
                        elif "-" in reu_data_str:
                            from datetime import date

                            year, month, day = reu_data_str.split("-")
                            reu_data = date(
                                self._safe_int(year),
                                self._safe_int(month),
                                self._safe_int(day),
                            )
                    except (ValueError, IndexError):
                        logger.warning(
                            f"Could not parse plenary meeting date: {reu_data_str}"
                        )

                # Extract additional III Legislature fields
                reu_id = self._get_int_value(reuniao, "reuId")
                reu_data_hora = self._get_text_value(reuniao, "reuDataHora")
                reu_tir_des = self._get_text_value(reuniao, "reuTirDes")
                leg_des = self._get_text_value(reuniao, "legDes")

                # Create meeting record with all available fields
                meeting = OrganMeeting(
                    # Basic fields
                    reu_tar_sigla=sel_numero,  # Use selNumero as identifier
                    reu_local=reu_local,
                    reu_data=reu_data,
                    reu_hora=reu_hora,
                    reu_tipo=reu_tipo,
                    reu_estado=reu_estado,
                    # Extended III Legislature fields
                    reu_id=reu_id,
                    reu_data_hora=reu_data_hora,
                    reu_tir_des=reu_tir_des,
                    leg_des=leg_des,
                    sel_numero=sel_numero,
                )

                self._add_with_tracking(meeting)
                self._batch_flush(force=True)  # Need ID for meeting_attendances FK

                # Process attendance data (Presencas)
                presencas = reuniao_plenario.find("Presencas")
                if presencas is not None:
                    self._process_meeting_attendance(presencas, meeting, legislatura)

            return True

        except Exception as e:
            error_msg = f"Error processing ReuniaoPlenario: {e}"
            logger.error(error_msg)
            logger.error("Data integrity issue detected during ReuniaoPlenario processing")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            if hasattr(self, "strict_mode") and self.strict_mode:
                logger.error(f"STRICT MODE: Raising exception due to ReuniaoPlenario processing error")
                raise RuntimeError(f"STRICT MODE - Data integrity issue: {error_msg}")
            return False

    def _process_organ_meeting_namespace(
        self, dados_reuniao: ET.Element, **kwargs
    ) -> bool:
        """Process meeting data with pt_ar_wsgode_objectos namespace structure"""
        try:
            # Extract meeting data from namespace structure
            reu_tar_id = self._get_text_value(dados_reuniao, "reuTarId")
            reu_tir_des = self._get_text_value(dados_reuniao, "reuTirDes")
            reu_local = self._get_text_value(dados_reuniao, "reuLocal")
            reu_data_str = self._get_text_value(dados_reuniao, "reuData")
            reu_hora = self._get_text_value(dados_reuniao, "reuHora")
            reu_tipo = self._get_text_value(dados_reuniao, "reuTipo")
            reu_estado = self._get_text_value(dados_reuniao, "reuEstado")

            # Parse date
            reu_data = None
            if reu_data_str:
                try:
                    if "/" in reu_data_str:
                        day, month, year = reu_data_str.split("/")
                        from datetime import date

                        reu_data = date(
                            self._safe_int(year),
                            self._safe_int(month),
                            self._safe_int(day),
                        )
                    elif "-" in reu_data_str:
                        from datetime import date

                        year, month, day = reu_data_str.split("-")
                        reu_data = date(
                            self._safe_int(year),
                            self._safe_int(month),
                            self._safe_int(day),
                        )
                except (ValueError, IndexError):
                    logger.warning(f"Could not parse meeting date: {reu_data_str}")

            # Extract additional III Legislature namespace fields
            reu_numero = self._get_int_value(dados_reuniao, "reuNumero")
            reu_data_hora = self._get_text_value(dados_reuniao, "reuDataHora")
            reu_final_plenario = self._get_boolean_value(
                dados_reuniao, "reuFinalPlenario"
            )

            # Create meeting record with all available fields
            meeting = OrganMeeting(
                # Organ associations
                commission_id=(
                    kwargs.get("committee").id if kwargs.get("committee") else None
                ),
                work_group_id=(
                    kwargs.get("work_group").id if kwargs.get("work_group") else None
                ),
                permanent_committee_id=(
                    kwargs.get("permanent_committee").id
                    if kwargs.get("permanent_committee")
                    else None
                ),
                sub_committee_id=(
                    kwargs.get("sub_committee").id
                    if kwargs.get("sub_committee")
                    else None
                ),
                # Basic fields
                reu_tar_sigla=reu_tar_id,  # Use tar_id as identifier
                reu_local=reu_local,
                reu_data=reu_data,
                reu_hora=reu_hora,
                reu_tipo=reu_tipo,
                reu_estado=reu_estado,
                # Extended III Legislature fields
                reu_numero=reu_numero,
                reu_data_hora=reu_data_hora,
                reu_final_plenario=reu_final_plenario,
                reu_tir_des=reu_tir_des,
            )

            self._add_with_tracking(meeting)
            return True

        except Exception as e:
            logger.error(f"Error processing namespace meeting data: {e}")
            return False

    def _match_deputy_by_name_and_group(
        self,
        nome_parlamentar: str,
        sigla_grupo: str,
        dt_reuniao: datetime,
        legislatura: Legislatura,
    ) -> tuple:
        """
        Match a deputy by parliamentary name, group, and time period.

        Uses a two-tiered matching approach with OR logic:
        1. (Deputado.nome OR Deputado.nome_completo) + group + date
        2. (Deputado.nome OR Deputado.nome_completo) only (legislature context)

        Results are cached to avoid repeated expensive ilike queries for the same deputy.

        Returns:
            tuple: (dep_id, dep_cad_id) if found, (None, None) otherwise
        """
        if not nome_parlamentar:
            return None, None

        # Check cache first - use (nome, grupo, leg_id) as key
        # We cache by name+group+legislature, ignoring specific date for efficiency
        cache_key = (nome_parlamentar.lower(), sigla_grupo, legislatura.id)
        if cache_key in self._deputy_name_cache:
            return self._deputy_name_cache[cache_key]

        # Also check name-only cache key for fallback matches
        cache_key_name_only = (nome_parlamentar.lower(), None, legislatura.id)
        if cache_key_name_only in self._deputy_name_cache:
            return self._deputy_name_cache[cache_key_name_only]

        try:
            # First tier: exact match with parliamentary group and date using nome OR nome_completo
            if sigla_grupo and dt_reuniao:
                # Query deputy through parliamentary group membership for the given period
                # Use xml_source_id (Integer) not id (UUID) since MeetingAttendance.dep_id expects Integer
                query = (
                    self.session.query(Deputado.xml_source_id, Deputado.id_cadastro)
                    .join(
                        DeputyGPSituation, DeputyGPSituation.deputado_id == Deputado.id
                    )
                    .filter(
                        or_(
                            Deputado.nome.ilike(f"%{nome_parlamentar}%"),
                            Deputado.nome_completo.ilike(f"%{nome_parlamentar}%"),
                        ),
                        DeputyGPSituation.gp_sigla == sigla_grupo,
                        DeputyGPSituation.legislatura_id == legislatura.id,
                    )
                )

                # Filter by date range if available
                if dt_reuniao:
                    query = query.filter(
                        or_(
                            DeputyGPSituation.gp_dt_inicio <= dt_reuniao,
                            DeputyGPSituation.gp_dt_inicio.is_(None),
                        ),
                        or_(
                            DeputyGPSituation.gp_dt_fim >= dt_reuniao,
                            DeputyGPSituation.gp_dt_fim.is_(None),
                        ),
                    )

                result = query.first()
                if result:
                    logger.debug(
                        f"Deputy matched via name+group+date: '{nome_parlamentar}' -> {result.xml_source_id}"
                    )
                    # Cache the result for future lookups
                    self._deputy_name_cache[cache_key] = (result.xml_source_id, result.id_cadastro)
                    return result.xml_source_id, result.id_cadastro

            # Second tier: match by name only (nome OR nome_completo) in the same legislature
            # Use xml_source_id (Integer) not id (UUID) since MeetingAttendance.dep_id expects Integer
            query = (
                self.session.query(Deputado.xml_source_id, Deputado.id_cadastro)
                .join(DeputyGPSituation, DeputyGPSituation.deputado_id == Deputado.id)
                .filter(
                    or_(
                        Deputado.nome.ilike(f"%{nome_parlamentar}%"),
                        Deputado.nome_completo.ilike(f"%{nome_parlamentar}%"),
                    ),
                    DeputyGPSituation.legislatura_id == legislatura.id,
                )
            )

            result = query.first()
            if result:
                logger.debug(
                    f"Deputy matched via name only: '{nome_parlamentar}' -> {result.xml_source_id}"
                )
                # Cache with name-only key for future lookups
                self._deputy_name_cache[cache_key_name_only] = (result.xml_source_id, result.id_cadastro)
                # Also cache with the original key so exact matches are found first
                self._deputy_name_cache[cache_key] = (result.xml_source_id, result.id_cadastro)
                return result.xml_source_id, result.id_cadastro

        except Exception as e:
            logger.warning(
                f"Error matching deputy '{nome_parlamentar}' with group '{sigla_grupo}': {e}"
            )

        # Cache negative result to avoid repeated failed lookups
        self._deputy_name_cache[cache_key] = (None, None)
        return None, None

    def _process_meeting_attendance(
        self,
        presencas: ET.Element,
        meeting: OrganMeeting,
        legislatura: Legislatura = None,
    ) -> bool:
        """Process meeting attendance data (Presencas) - now stores in MeetingAttendance model"""
        try:
            tipo_reuniao = self._get_text_value(presencas, "tipoReuniao")
            dt_reuniao_str = self._get_text_value(presencas, "dtReuniao")

            # Parse meeting date for attendance
            dt_reuniao = None
            if dt_reuniao_str:
                try:
                    if "/" in dt_reuniao_str:
                        day, month, year = dt_reuniao_str.split("/")
                        from datetime import date

                        dt_reuniao = date(
                            self._safe_int(year),
                            self._safe_int(month),
                            self._safe_int(day),
                        )
                    elif "-" in dt_reuniao_str:
                        from datetime import date

                        year, month, day = dt_reuniao_str.split("-")
                        dt_reuniao = date(
                            self._safe_int(year),
                            self._safe_int(month),
                            self._safe_int(day),
                        )
                except (ValueError, IndexError):
                    logger.warning(f"Could not parse attendance date: {dt_reuniao_str}")

            attendance_count = 0

            # Check if this Presencas element contains only metadata (date, type) but no actual attendance records
            child_tags = [child.tag for child in presencas]
            has_only_metadata = set(child_tags).issubset({"dtReuniao", "tipoReuniao"})

            if has_only_metadata:
                logger.debug(
                    f"Meeting {meeting.id} has Presencas with only metadata (no attendance records) - this is valid"
                )
                return True

            # Process standard pt_ar_wsgode_objectos_DadosPresenca structure
            dados_presenca_list = presencas.findall(
                "pt_ar_wsgode_objectos_DadosPresenca"
            )

            for dados_presenca in dados_presenca_list:
                dep_id = self._get_int_value(dados_presenca, "depId")
                dep_cad_id = self._get_int_value(dados_presenca, "depCadId")
                dep_nome = self._get_text_value(dados_presenca, "depNomeParlamentar")
                pres_tipo = self._get_text_value(dados_presenca, "presTipo")
                pres_justificacao = self._get_text_value(
                    dados_presenca, "presJustificacao"
                )

                # Create attendance record
                attendance = MeetingAttendance(
                    meeting_id=meeting.id,
                    dep_id=dep_id,
                    dep_cad_id=dep_cad_id,
                    dep_nome_parlamentar=dep_nome,
                    pres_tipo=pres_tipo,
                    pres_justificacao=pres_justificacao,
                    dt_reuniao=dt_reuniao,
                    tipo_reuniao=tipo_reuniao,
                )

                self._add_with_tracking(attendance)
                attendance_count += 1

            # Process alternative pt_gov_ar_wsgode_objectos_Presencas structure (IX Legislature)
            presencas_alt = presencas.find("presencas")
            if presencas_alt is not None:
                dados_presenca_alt_list = presencas_alt.findall(
                    "pt_gov_ar_wsgode_objectos_Presencas"
                )

                for dados_presenca_alt in dados_presenca_alt_list:
                    nome_deputado = self._get_text_value(
                        dados_presenca_alt, "nomeDeputado"
                    )
                    sigla_grupo = self._get_text_value(dados_presenca_alt, "siglaGrupo")
                    sigla_falta = self._get_text_value(dados_presenca_alt, "siglaFalta")
                    sigla_qualidade_presenca_orgao = self._get_text_value(
                        dados_presenca_alt, "siglaQualidadePresencaOrgao"
                    )
                    motivo_falta = self._get_text_value(
                        dados_presenca_alt, "motivoFalta"
                    )

                    # Attempt to match the deputy by name, group, and legislature period
                    dep_id, dep_cad_id = None, None
                    if nome_deputado and legislatura:
                        dep_id, dep_cad_id = self._match_deputy_by_name_and_group(
                            nome_deputado, sigla_grupo, dt_reuniao, legislatura
                        )
                        if dep_id:
                            logger.debug(
                                f"Successfully matched deputy '{nome_deputado}' (group: {sigla_grupo}) to dep_id={dep_id}, dep_cad_id={dep_cad_id}"
                            )

                    # Create attendance record with available data
                    attendance = MeetingAttendance(
                        meeting_id=meeting.id,
                        dep_id=dep_id,
                        dep_cad_id=dep_cad_id,
                        dep_nome_parlamentar=nome_deputado,
                        dt_reuniao=dt_reuniao,
                        tipo_reuniao=tipo_reuniao,
                        # Store structured presence quality information
                        sigla_qualidade_presenca=(
                            sigla_qualidade_presenca_orgao
                            if sigla_qualidade_presenca_orgao
                            else None
                        ),
                        sigla_grupo=sigla_grupo,
                        sigla_falta=sigla_falta,
                        motivo_falta=motivo_falta,
                    )

                    self._add_with_tracking(attendance)
                    attendance_count += 1

            # Only log if we actually processed some attendance records
            if attendance_count > 0:
                logger.info(
                    f"Stored {attendance_count} attendance records for meeting {meeting.id}"
                )
            else:
                logger.debug(
                    f"No attendance records found for meeting {meeting.id} (this is valid for some meetings)"
                )

            return True

        except Exception as e:
            logger.error(f"Error processing meeting attendance: {e}")
            return False

    def _get_or_create_ar_board(
        self,
        id_orgao: int,
        sigla: str,
        nome: str,
        numero: str,
        legislatura: Legislatura,
    ):
        """Get or create AR Board record (cached)"""
        # First get or create parliamentary organization
        organization = self._get_or_create_parliamentary_organization(legislatura)

        # Check cache first
        cache_key = (id_orgao, organization.id)
        if cache_key in self._ar_board_cache:
            return self._ar_board_cache[cache_key]

        ar_board = (
            self.session.query(ARBoard)
            .filter_by(id_orgao=id_orgao, organization_id=organization.id)
            .first()
        )

        if ar_board:
            self._ar_board_cache[cache_key] = ar_board
            return ar_board

        ar_board = ARBoard(
            organization_id=organization.id,
            id_orgao=id_orgao,
            sigla_orgao=sigla,
            nome_sigla=nome,
            numero_orgao=self._safe_int(numero) if numero else None,
            sigla_legislatura=legislatura.numero,
        )

        self._add_with_tracking(ar_board)
        self._batch_flush(force=True)  # Need ID for foreign keys
        self._ar_board_cache[cache_key] = ar_board
        return ar_board

    def _get_or_create_administrative_council(
        self,
        id_orgao: int,
        sigla: str,
        nome: str,
        numero: str,
        legislatura: Legislatura,
    ):
        """Get or create Administrative Council record (cached)"""
        # First get or create parliamentary organization
        organization = self._get_or_create_parliamentary_organization(legislatura)

        # Check cache first
        cache_key = (id_orgao, organization.id)
        if cache_key in self._admin_council_cache:
            return self._admin_council_cache[cache_key]

        admin_council = (
            self.session.query(AdministrativeCouncil)
            .filter_by(id_orgao=id_orgao, organization_id=organization.id)
            .first()
        )

        if admin_council:
            self._admin_council_cache[cache_key] = admin_council
            return admin_council

        admin_council = AdministrativeCouncil(
            organization_id=organization.id,
            id_orgao=id_orgao,
            sigla_orgao=sigla,
            nome_sigla=nome,
            numero_orgao=self._safe_int(numero) if numero else None,
            sigla_legislatura=legislatura.numero,
        )

        self._add_with_tracking(admin_council)
        self._batch_flush(force=True)  # Need ID for foreign keys
        self._admin_council_cache[cache_key] = admin_council
        return admin_council

    def _get_or_create_permanent_committee(
        self,
        id_orgao: int,
        sigla: str,
        nome: str,
        numero: str,
        legislatura: Legislatura,
    ):
        """Get or create Permanent Committee record (cached)"""
        # First get or create parliamentary organization
        organization = self._get_or_create_parliamentary_organization(legislatura)

        # Check cache first
        cache_key = (id_orgao, organization.id)
        if cache_key in self._perm_committee_cache:
            return self._perm_committee_cache[cache_key]

        permanent_committee = (
            self.session.query(PermanentCommittee)
            .filter_by(id_orgao=id_orgao, organization_id=organization.id)
            .first()
        )

        if permanent_committee:
            self._perm_committee_cache[cache_key] = permanent_committee
            return permanent_committee

        permanent_committee = PermanentCommittee(
            organization_id=organization.id,
            id_orgao=id_orgao,
            sigla_orgao=sigla,
            nome_sigla=nome,
            numero_orgao=self._safe_int(numero) if numero else None,
            sigla_legislatura=legislatura.numero,
        )

        self._add_with_tracking(permanent_committee)
        self._batch_flush(force=True)  # Need ID for foreign keys
        self._perm_committee_cache[cache_key] = permanent_committee
        return permanent_committee

    def _get_or_create_leader_conference(
        self,
        id_orgao: int,
        sigla: str,
        nome: str,
        numero: str,
        legislatura: Legislatura,
    ):
        """Get or create Leader Conference record (cached)"""
        # First get or create parliamentary organization
        organization = self._get_or_create_parliamentary_organization(legislatura)

        # Check cache first
        cache_key = (id_orgao, organization.id)
        if cache_key in self._leader_conf_cache:
            return self._leader_conf_cache[cache_key]

        leader_conference = (
            self.session.query(LeaderConference)
            .filter_by(id_orgao=id_orgao, organization_id=organization.id)
            .first()
        )

        if leader_conference:
            self._leader_conf_cache[cache_key] = leader_conference
            return leader_conference

        leader_conference = LeaderConference(
            organization_id=organization.id,
            id_orgao=id_orgao,
            sigla_orgao=sigla,
            nome_sigla=nome,
            numero_orgao=self._safe_int(numero) if numero else None,
            sigla_legislatura=legislatura.numero,
        )

        self._add_with_tracking(leader_conference)
        self._batch_flush(force=True)  # Need ID for foreign keys
        self._leader_conf_cache[cache_key] = leader_conference
        return leader_conference

    def _get_or_create_commission_president_conference(
        self,
        id_orgao: int,
        sigla: str,
        nome: str,
        numero: int,
        sigla_legislatura: str,
        organization,
    ):
        """Get or create Commission President Conference record (cached)"""
        # Check cache first
        cache_key = (id_orgao, organization.id)
        if cache_key in self._comm_pres_conf_cache:
            return self._comm_pres_conf_cache[cache_key]

        commission_conference = (
            self.session.query(CommissionPresidentConference)
            .filter_by(id_orgao=id_orgao, organization_id=organization.id)
            .first()
        )

        if commission_conference:
            # Update sigla_legislatura if provided (for XIII Legislature)
            if sigla_legislatura and not commission_conference.sigla_legislatura:
                commission_conference.sigla_legislatura = sigla_legislatura
                self._batch_flush()
            self._comm_pres_conf_cache[cache_key] = commission_conference
            return commission_conference

        commission_conference = CommissionPresidentConference(
            organization_id=organization.id,
            id_orgao=id_orgao,
            sigla_orgao=sigla,
            nome_sigla=nome,
            numero_orgao=numero,
            sigla_legislatura=sigla_legislatura,
        )

        self._add_with_tracking(commission_conference)
        self._batch_flush(force=True)  # Need ID for foreign keys
        self._comm_pres_conf_cache[cache_key] = commission_conference
        return commission_conference

    def _process_deputy_ar_board_membership(
        self, deputado_data: ET.Element, ar_board
    ) -> bool:
        """Process deputy membership in AR Board"""
        try:
            # Get or create deputy and legislatura with explicit field mapping
            dep_id = self._get_int_value(deputado_data, "DepId")
            dep_cad_id = self._get_int_value(deputado_data, "DepCadId")
            dep_nome_parlamentar = self._get_text_value(deputado_data, "DepNomeParlamentar")
            dep_nome_completo = self._get_text_value(deputado_data, "DepNomeCompleto")
            if dep_cad_id and dep_nome_parlamentar:
                # Get or create deputy using both record_id and cadastral_id
                record_id = dep_id if dep_id else dep_cad_id
                deputado = self._get_or_create_deputado(
                    record_id, dep_cad_id, dep_nome_parlamentar, dep_nome_completo,
                    xml_context=deputado_data  # Pass XML context for LegDes extraction
                )

                # Get legislatura from file context
                legislatura_sigla = self._extract_legislatura(
                    self.file_info.get("file_path", ""), None
                )
                legislatura = self._get_or_create_legislatura(legislatura_sigla)
            else:
                deputado = None
                legislatura = None

            # Create historical composition record
            composition = ARBoardHistoricalComposition(
                board_id=ar_board.id,
                leg_des=self._get_text_value(deputado_data, "LegDes"),
                dep_id=self._get_int_value(deputado_data, "DepId"),
                dep_cad_id=dep_cad_id,
                dep_nome_parlamentar=dep_nome,
                org_id=ar_board.id_orgao,
            )

            self._add_with_tracking(composition)
            self._batch_flush()

            # Process parliamentary group situations
            dep_gp = deputado_data.find("DepGP")
            if dep_gp is not None:
                self._process_gp_situations(
                    dep_gp,
                    deputado=deputado,
                    legislatura=legislatura,
                    composition_type="ar_board",
                    ar_board_composition=composition,
                )

            # Process deputy situations
            dep_situacao = deputado_data.find("DepSituacao")
            if dep_situacao is not None:
                self._process_deputy_situations(
                    dep_situacao, ar_board_composition=composition
                )

            return True

        except Exception as e:
            logger.error(f"Error processing AR Board deputy membership: {e}")
            return False

    def _process_ar_board_historical_composition(
        self, historico_data: ET.Element, ar_board, legislatura: Legislatura
    ) -> bool:
        """Process AR Board historical composition (IX Legislature)"""
        try:
            # Create historical composition record
            composition = ARBoardHistoricalComposition(
                board_id=ar_board.id,
                leg_des=self._get_text_value(historico_data, "legDes")
                or legislatura.numero,
                dep_id=self._get_int_value(historico_data, "depId"),
                dep_cad_id=self._get_int_value(historico_data, "depCadId"),
                dep_nome_parlamentar=self._get_text_value(
                    historico_data, "depNomeParlamentar"
                ),
                dep_nome_completo=self._get_text_value(
                    historico_data, "depNomeCompleto"
                ),
                org_id=ar_board.id_orgao,
            )

            self._add_with_tracking(composition)
            self._batch_flush()

            # Process parliamentary group situations
            dep_gp = historico_data.find("depGP")
            if dep_gp is not None:
                deputado, legislatura = self._get_deputado_and_legislatura_from_data(
                    historico_data
                )
                self._process_gp_situations(
                    dep_gp,
                    deputado=deputado,
                    legislatura=legislatura,
                    composition_type="ar_board",
                    ar_board_composition=composition,
                )

            # Process deputy positions/cargo
            dep_cargo = historico_data.find("depCargo")
            if dep_cargo is not None:
                self._process_deputy_positions(
                    dep_cargo, ar_board_composition=composition
                )

            return True

        except Exception as e:
            logger.error(f"Error processing AR Board historical composition: {e}")
            return False

    def _process_commission_historical_composition(
        self, historico_data: ET.Element, committee, legislatura: Legislatura
    ) -> bool:
        """Process Commission historical composition (IX Legislature)"""
        try:
            # Create historical composition record
            composition = CommissionHistoricalComposition(
                commission_id=committee.id,
                leg_des=self._get_text_value(historico_data, "legDes")
                or legislatura.numero,
                dep_id=self._get_int_value(historico_data, "depId"),
                dep_cad_id=self._get_int_value(historico_data, "depCadId"),
                dep_nome_parlamentar=self._get_text_value(
                    historico_data, "depNomeParlamentar"
                ),
                dep_nome_completo=self._get_text_value(
                    historico_data, "depNomeCompleto"
                ),
                org_id=self._get_int_value(historico_data, "orgId")
                or committee.id_orgao,
            )

            self._add_with_tracking(composition)
            self._batch_flush()

            # Process parliamentary group situations
            dep_gp = historico_data.find("depGP")
            if dep_gp is not None:
                deputado, legislatura = self._get_deputado_and_legislatura_from_data(
                    historico_data
                )
                self._process_gp_situations(
                    dep_gp,
                    deputado=deputado,
                    legislatura=legislatura,
                    composition_type="commission",
                    commission_composition=composition,
                )

            # Process deputy positions/cargo
            dep_cargo = historico_data.find("depCargo")
            if dep_cargo is not None:
                self._process_deputy_positions(
                    dep_cargo, commission_composition=composition
                )

            # Process deputy situations
            dep_situacao = historico_data.find("depSituacao")
            if dep_situacao is not None:
                self._process_deputy_situations(
                    dep_situacao, commission_composition=composition
                )

            return True

        except Exception as e:
            logger.error(f"Error processing Commission historical composition: {e}")
            return False

    def _process_subcommittee_historical_composition(
        self, historico_data: ET.Element, subcommittee, legislatura: Legislatura
    ) -> bool:
        """Process SubCommittee historical composition (IX Legislature)"""
        try:
            # Create historical composition record
            composition = SubCommitteeHistoricalComposition(
                sub_committee_id=subcommittee.id,
                leg_des=self._get_text_value(historico_data, "legDes")
                or legislatura.numero,
                dep_id=self._get_int_value(historico_data, "depId"),
                dep_cad_id=self._get_int_value(historico_data, "depCadId"),
                dep_nome_parlamentar=self._get_text_value(
                    historico_data, "depNomeParlamentar"
                ),
                dep_nome_completo=self._get_text_value(
                    historico_data, "depNomeCompleto"
                ),
                org_id=self._get_int_value(historico_data, "orgId")
                or subcommittee.id_orgao,
            )

            self._add_with_tracking(composition)
            self._batch_flush()

            # Process parliamentary group situations
            dep_gp = historico_data.find("depGP")
            if dep_gp is not None:
                deputado, legislatura = self._get_deputado_and_legislatura_from_data(
                    historico_data
                )
                self._process_gp_situations(
                    dep_gp,
                    deputado=deputado,
                    legislatura=legislatura,
                    composition_type="sub_committee",
                    sub_committee_composition=composition,
                )

            # Process deputy positions/cargo
            dep_cargo = historico_data.find("depCargo")
            if dep_cargo is not None:
                self._process_deputy_positions(
                    dep_cargo, sub_committee_composition=composition
                )

            # Process deputy situations
            dep_situacao = historico_data.find("depSituacao")
            if dep_situacao is not None:
                self._process_deputy_situations(
                    dep_situacao, sub_committee_composition=composition
                )

            return True

        except Exception as e:
            logger.error(f"Error processing SubCommittee historical composition: {e}")
            return False

    def _process_work_group_historical_composition(
        self, historico_data: ET.Element, work_group, legislatura: Legislatura
    ) -> bool:
        """Process WorkGroup historical composition (VIII Legislature)"""
        try:
            # Create historical composition record
            composition = WorkGroupHistoricalComposition(
                work_group_id=work_group.id,
                leg_des=self._get_text_value(historico_data, "legDes")
                or legislatura.numero,
                dep_id=self._get_int_value(historico_data, "depId"),
                dep_cad_id=self._get_int_value(historico_data, "depCadId"),
                dep_nome_parlamentar=self._get_text_value(
                    historico_data, "depNomeParlamentar"
                ),
                dep_nome_completo=self._get_text_value(
                    historico_data, "depNomeCompleto"
                ),
                org_id=self._get_int_value(historico_data, "orgId")
                or work_group.id_orgao,
            )

            self._add_with_tracking(composition)
            self._batch_flush()

            # Process parliamentary group situations
            dep_gp = historico_data.find("depGP")
            if dep_gp is not None:
                deputado, legislatura = self._get_deputado_and_legislatura_from_data(
                    historico_data
                )
                self._process_gp_situations(
                    dep_gp,
                    deputado=deputado,
                    legislatura=legislatura,
                    composition_type="work_group",
                    work_group_composition=composition,
                )

            # Process deputy positions/cargo
            dep_cargo = historico_data.find("depCargo")
            if dep_cargo is not None:
                self._process_deputy_positions(
                    dep_cargo, work_group_composition=composition
                )

            # Process deputy situations
            dep_situacao = historico_data.find("depSituacao")
            if dep_situacao is not None:
                self._process_deputy_situations(
                    dep_situacao, work_group_composition=composition
                )

            return True

        except Exception as e:
            logger.error(f"Error processing WorkGroup historical composition: {e}")
            return False

    def _process_deputy_admin_council_membership(
        self, deputado_data: ET.Element, admin_council
    ) -> bool:
        """Process deputy membership in Administrative Council"""
        try:
            # Create historical composition record
            composition = AdministrativeCouncilHistoricalComposition(
                council_id=admin_council.id,
                leg_des=self._get_text_value(deputado_data, "LegDes"),
                dep_id=self._get_int_value(deputado_data, "DepId"),
                dep_cad_id=self._get_int_value(deputado_data, "DepCadId"),
                dep_nome_parlamentar=self._get_text_value(
                    deputado_data, "DepNomeParlamentar"
                ),
                org_id=admin_council.id_orgao,
            )

            self._add_with_tracking(composition)
            self._batch_flush()

            # Process parliamentary group situations
            dep_gp = deputado_data.find("DepGP")
            if dep_gp is not None:
                deputado, legislatura = self._get_deputado_and_legislatura_from_data(
                    deputado_data
                )
                self._process_gp_situations(
                    dep_gp,
                    deputado=deputado,
                    legislatura=legislatura,
                    composition_type="admin_council",
                    admin_council_composition=composition,
                )

            # Process deputy situations
            dep_situacao = deputado_data.find("DepSituacao")
            if dep_situacao is not None:
                self._process_deputy_situations(
                    dep_situacao, admin_council_composition=composition
                )

            return True

        except Exception as e:
            logger.error(
                f"Error processing Administrative Council deputy membership: {e}"
            )
            return False

    def _process_deputy_permanent_committee_membership(
        self, deputado_data: ET.Element, permanent_committee
    ) -> bool:
        """Process deputy membership in Permanent Committee"""
        try:
            # Create historical composition record
            composition = PermanentCommitteeHistoricalComposition(
                permanent_committee_id=permanent_committee.id,
                leg_des=self._get_text_value(deputado_data, "LegDes"),
                dep_id=self._get_int_value(deputado_data, "DepId"),
                dep_cad_id=self._get_int_value(deputado_data, "DepCadId"),
                dep_nome_parlamentar=self._get_text_value(
                    deputado_data, "DepNomeParlamentar"
                ),
                org_id=permanent_committee.id_orgao,
            )

            self._add_with_tracking(composition)
            self._batch_flush()

            # Process parliamentary group situations
            dep_gp = deputado_data.find("DepGP")
            if dep_gp is not None:
                deputado, legislatura = self._get_deputado_and_legislatura_from_data(
                    deputado_data
                )
                self._process_gp_situations(
                    dep_gp,
                    deputado=deputado,
                    legislatura=legislatura,
                    composition_type="permanent_committee",
                    permanent_committee_composition=composition,
                )

            # Process deputy situations
            dep_situacao = deputado_data.find("DepSituacao")
            if dep_situacao is not None:
                self._process_deputy_situations(
                    dep_situacao, permanent_committee_composition=composition
                )

            return True

        except Exception as e:
            logger.error(f"Error processing Permanent Committee deputy membership: {e}")
            return False

    def _process_permanent_committee_historical_composition(
        self, historico_data: ET.Element, permanent_committee, legislatura: Legislatura
    ) -> bool:
        """Process PermanentCommittee historical composition (VI Legislature)"""
        try:
            # Create historical composition record
            composition = PermanentCommitteeHistoricalComposition(
                permanent_committee_id=permanent_committee.id,
                leg_des=self._get_text_value(historico_data, "legDes")
                or legislatura.numero,
                dep_id=self._get_int_value(historico_data, "depId"),
                dep_cad_id=self._get_int_value(historico_data, "depCadId"),
                dep_nome_parlamentar=self._get_text_value(
                    historico_data, "depNomeParlamentar"
                ),
                dep_nome_completo=self._get_text_value(
                    historico_data, "depNomeCompleto"
                ),
                org_id=self._get_int_value(historico_data, "orgId")
                or permanent_committee.id_orgao,
            )

            self._add_with_tracking(composition)
            self._batch_flush()

            # Process parliamentary group situations
            dep_gp = historico_data.find("depGP")
            if dep_gp is not None:
                deputado, legislatura = self._get_deputado_and_legislatura_from_data(
                    historico_data
                )
                self._process_gp_situations(
                    dep_gp,
                    deputado=deputado,
                    legislatura=legislatura,
                    composition_type="permanent_committee",
                    permanent_committee_composition=composition,
                )

            # Process deputy positions/cargo
            dep_cargo = historico_data.find("depCargo")
            if dep_cargo is not None:
                self._process_deputy_positions(
                    dep_cargo, permanent_committee_composition=composition
                )

            # Process deputy situations
            dep_situacao = historico_data.find("depSituacao")
            if dep_situacao is not None:
                self._process_deputy_situations(
                    dep_situacao, permanent_committee_composition=composition
                )

            return True

        except Exception as e:
            logger.error(
                f"Error processing PermanentCommittee historical composition: {e}"
            )
            return False

    def _process_deputy_leader_conference_membership(
        self, deputado_data: ET.Element, leader_conference
    ) -> bool:
        """Process deputy membership in Leader Conference"""
        try:
            # Create historical composition record
            composition = LeaderConferenceHistoricalComposition(
                conference_id=leader_conference.id,
                leg_des=self._get_text_value(deputado_data, "LegDes"),
                dep_id=self._get_int_value(deputado_data, "DepId"),
                dep_cad_id=self._get_int_value(deputado_data, "DepCadId"),
                dep_nome_parlamentar=self._get_text_value(
                    deputado_data, "DepNomeParlamentar"
                ),
                org_id=leader_conference.id_orgao,
            )

            self._add_with_tracking(composition)
            self._batch_flush()

            # Process parliamentary group situations
            dep_gp = deputado_data.find("DepGP")
            if dep_gp is not None:
                deputado, legislatura = self._get_deputado_and_legislatura_from_data(
                    deputado_data
                )
                self._process_gp_situations(
                    dep_gp,
                    deputado=deputado,
                    legislatura=legislatura,
                    composition_type="leader_conference",
                    leader_conference_composition=composition,
                )

            # Process deputy situations
            dep_situacao = deputado_data.find("DepSituacao")
            if dep_situacao is not None:
                self._process_deputy_situations(
                    dep_situacao, leader_conference_composition=composition
                )

            return True

        except Exception as e:
            logger.error(f"Error processing Leader Conference deputy membership: {e}")
            return False

    def _process_admin_council_historical_composition(
        self, historico_data: ET.Element, admin_council, legislatura: Legislatura
    ) -> bool:
        """Process Administrative Council historical composition (XIII Legislature)"""
        try:
            # Create historical composition record
            composition = AdministrativeCouncilHistoricalComposition(
                council_id=admin_council.id,
                leg_des=self._get_text_value(historico_data, "legDes")
                or legislatura.numero,
                dep_id=self._get_int_value(historico_data, "depId"),
                dep_cad_id=self._get_int_value(historico_data, "depCadId"),
                dep_nome_parlamentar=self._get_text_value(
                    historico_data, "depNomeParlamentar"
                ),
                dep_nome_completo=self._get_text_value(
                    historico_data, "depNomeCompleto"
                ),
                org_id=self._get_int_value(historico_data, "orgId")
                or admin_council.id_orgao,
            )

            self._add_with_tracking(composition)
            self._batch_flush()

            # Process parliamentary group situations
            dep_gp = historico_data.find("depGP")
            if dep_gp is not None:
                deputado, legislatura = self._get_deputado_and_legislatura_from_data(
                    historico_data
                )
                self._process_gp_situations(
                    dep_gp,
                    deputado=deputado,
                    legislatura=legislatura,
                    composition_type="admin_council",
                    admin_council_composition=composition,
                )

            # Process deputy positions/cargo
            dep_cargo = historico_data.find("depCargo")
            if dep_cargo is not None:
                self._process_deputy_positions(
                    dep_cargo, admin_council_composition=composition
                )

            # Process deputy situations
            dep_situacao = historico_data.find("depSituacao")
            if dep_situacao is not None:
                self._process_deputy_situations(
                    dep_situacao, admin_council_composition=composition
                )

            return True

        except Exception as e:
            logger.error(
                f"Error processing Administrative Council historical composition: {e}"
            )
            return False

    def _process_leader_conference_historical_composition(
        self, historico_data: ET.Element, leader_conference, legislatura: Legislatura
    ) -> bool:
        """Process Leader Conference historical composition (XIII Legislature)"""
        try:
            # Create historical composition record
            composition = LeaderConferenceHistoricalComposition(
                conference_id=leader_conference.id,
                leg_des=self._get_text_value(historico_data, "legDes")
                or legislatura.numero,
                dep_id=self._get_int_value(historico_data, "depId"),
                dep_cad_id=self._get_int_value(historico_data, "depCadId"),
                dep_nome_parlamentar=self._get_text_value(
                    historico_data, "depNomeParlamentar"
                ),
                dep_nome_completo=self._get_text_value(
                    historico_data, "depNomeCompleto"
                ),
                org_id=self._get_int_value(historico_data, "orgId")
                or leader_conference.id_orgao,
            )

            self._add_with_tracking(composition)
            self._batch_flush()

            # Process parliamentary group situations
            dep_gp = historico_data.find("depGP")
            if dep_gp is not None:
                deputado, legislatura = self._get_deputado_and_legislatura_from_data(
                    historico_data
                )
                self._process_gp_situations(
                    dep_gp,
                    deputado=deputado,
                    legislatura=legislatura,
                    composition_type="leader_conference",
                    leader_conference_composition=composition,
                )

            # Process deputy positions/cargo
            dep_cargo = historico_data.find("depCargo")
            if dep_cargo is not None:
                self._process_deputy_positions(
                    dep_cargo, leader_conference_composition=composition
                )

            # Process deputy situations
            dep_situacao = historico_data.find("depSituacao")
            if dep_situacao is not None:
                self._process_deputy_situations(
                    dep_situacao, leader_conference_composition=composition
                )

            return True

        except Exception as e:
            logger.error(
                f"Error processing Leader Conference historical composition: {e}"
            )
            return False

    def _process_deputy_videos(
        self,
        videos: ET.Element,
        dep_id: int,
        dep_cad_id: int,
        dep_nome_parlamentar: str,
        organ_type: str,
        organ_id: int,
        legislatura_numero: str,
    ) -> bool:
        """Process deputy videos from DadosDeputadoOrgaoPlenario.Videos structure (XIII Legislature)"""
        try:
            for dados_video in videos.findall("pt_ar_wsgode_objectos_DadosVideo"):
                url = self._get_text_value(dados_video, "url")
                tipo = self._get_text_value(dados_video, "tipo")

                if url:  # Only create record if we have a URL
                    video = DeputyVideo(
                        dep_id=dep_id,
                        dep_cad_id=dep_cad_id,
                        dep_nome_parlamentar=dep_nome_parlamentar,
                        url=url,
                        tipo=tipo,
                        organ_type=organ_type,
                        organ_id=organ_id,
                        legislatura_numero=legislatura_numero,
                    )

                    self._add_with_tracking(video)
                    logger.debug(
                        f"Added video for deputy {safe_log_text(dep_nome_parlamentar)}: {safe_log_text(tipo)} - {url}"
                    )

            return True

        except Exception as e:
            logger.error(f"Error processing deputy videos: {e}")
            return False

    def _process_deputy_positions(self, dep_cargo: ET.Element, **kwargs) -> bool:
        """Process deputy positions/cargo from depCargo element - stores in OrganCompositionDeputyPosition"""
        try:
            if dep_cargo is None:
                logger.warning("Empty dep_cargo element provided")
                return True

            if not kwargs:
                logger.warning(
                    "No composition context provided for deputy position processing"
                )
                return True

            # Process pt_ar_wsgode_objectos_DadosCargoDeputado structure
            for dados_cargo in dep_cargo.findall(
                "pt_ar_wsgode_objectos_DadosCargoDeputado"
            ):
                car_id = self._get_int_value(dados_cargo, "carId")
                car_des = self._get_text_value(dados_cargo, "carDes")
                car_dt_inicio = self._parse_date(
                    self._get_text_value(dados_cargo, "carDtInicio")
                )
                car_dt_fim = self._parse_date(
                    self._get_text_value(dados_cargo, "carDtFim")
                )

                # Create deputy position record with composition context
                position = OrganCompositionDeputyPosition(
                    car_id=car_id,
                    car_des=car_des,
                    car_dt_inicio=car_dt_inicio,
                    car_dt_fim=car_dt_fim,
                )

                # Set appropriate composition relationship based on kwargs
                for key, value in kwargs.items():
                    if key.endswith("_composition") and value:
                        composition_type = key.replace("_composition", "")
                        setattr(
                            position, f"{composition_type}_composition_id", value.id
                        )
                        break  # Only set one relationship

                self._add_with_tracking(position)
                logger.debug(f"Added deputy position: {car_des} ({car_id})")

            return True

        except Exception as e:
            logger.error(f"Error processing deputy positions: {e}")
            return False

    def _process_deputy_situations(self, dep_situacao: ET.Element, **kwargs) -> bool:
        """Process deputy situations from depSituacao element - stores in OrganCompositionDeputySituation"""
        try:
            if dep_situacao is None:
                logger.warning("Empty dep_situacao element provided")
                return True

            if not kwargs:
                logger.warning(
                    "No composition context provided for deputy situation processing"
                )
                return True

            # Process pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado structure
            for dados_situacao in dep_situacao.findall(
                "pt_ar_wsgode_objectos_DadosSituacaoOrgaoDeputado"
            ):
                sio_des = self._get_text_value(dados_situacao, "sioDes")
                sio_tip_mem = self._get_text_value(dados_situacao, "sioTipMem")
                sio_dt_inicio = self._parse_date(
                    self._get_text_value(dados_situacao, "sioDtInicio")
                )
                sio_dt_fim = self._parse_date(
                    self._get_text_value(dados_situacao, "sioDtFim")
                )

                # Create deputy situation record with composition context
                situation = OrganCompositionDeputySituation(
                    sio_des=sio_des,
                    sio_tip_mem=sio_tip_mem,
                    sio_dt_inicio=sio_dt_inicio,
                    sio_dt_fim=sio_dt_fim,
                )

                # Set appropriate composition relationship based on kwargs
                for key, value in kwargs.items():
                    if key.endswith("_composition") and value:
                        composition_type = key.replace("_composition", "")
                        setattr(
                            situation, f"{composition_type}_composition_id", value.id
                        )
                        break  # Only set one relationship

                self._add_with_tracking(situation)
                logger.debug(f"Added deputy situation: {sio_des} ({sio_tip_mem})")

            return True

        except Exception as e:
            logger.error(f"Error processing deputy situations: {e}")
            return False

    def _convert_roman_to_int(self, roman: str) -> int:
        """Convert Roman numeral to integer"""
        roman_numerals = {
            "I": 1,
            "II": 2,
            "III": 3,
            "IV": 4,
            "V": 5,
            "VI": 6,
            "VII": 7,
            "VIII": 8,
            "IX": 9,
            "X": 10,
            "XI": 11,
            "XII": 12,
            "XIII": 13,
            "XIV": 14,
            "XV": 15,
            "XVI": 16,
            "XVII": 17,
            "CONSTITUINTE": 0,
        }
        return roman_numerals.get(roman, 17)

    def _get_boolean_value(self, parent: ET.Element, tag_name: str) -> bool:
        """Get boolean value from XML element"""
        text_value = self._get_text_value(parent, tag_name)
        if text_value:
            return text_value.lower() in ("true", "1", "yes", "sim")
        return False

    def _handle_processing_error(
        self, error_msg: str, results: Dict, strict_mode: bool
    ):
        """Handle processing errors with strict mode support"""
        logger.error(error_msg)
        results["errors"].append(error_msg)
        results["records_processed"] += 1
        if strict_mode:
            logger.error(f"STRICT MODE: Raising exception due to processing error")
            logger.error(f"Error details: {error_msg}")
            raise RuntimeError(f"STRICT MODE - Data integrity issue: {error_msg}")
