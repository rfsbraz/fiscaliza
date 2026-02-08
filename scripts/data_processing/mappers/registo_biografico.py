"""
Biographical Registry Mapper
============================

Comprehensive schema mapper for biographical registry files (RegistoBiografico<Legislatura>.xml).
Based on official Parliament documentation (December 2017 and May 2023):
"Estruturas de dados do Registo Biográfico dos Deputados" specifications.

Handles complete deputy biographical data with multi-version structure support:
- Basic biographical data (name, birth date, gender, profession, birthplace)
- Academic qualifications with completion status tracking
- Professional career positions with historical/current distinction
- Academic and honorary titles with hierarchical ordering
- State decorations and honors with classification levels
- Published works with comprehensive bibliographic details
- Parliamentary organ activities (committees and working groups)
- Legislative mandates with electoral and party affiliation history
- Interest registry integration across multiple schema versions (V1, V2, V3, V5)

Multi-Legislature Structure Support:
- I Legislature format: RegistoBiograficoList with pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb
- VIII Legislature format: ArrayOfDadosRegistoBiografico with DadosRegistoBiografico structure
- XV Legislature format: Enhanced with modern interest registry (RegistoInteressesV5)
- Cross-format compatibility with automatic structure detection

Data Evolution Tracking:
- V1: Basic biographical and interest registry data
- V2: Enhanced with professional activities (DadosDeputadoRgiWebV2)
- V3: Expanded social positions and professional services
- V5: Modern unified structure with comprehensive interest declarations

Parliamentary Integration:
- Maps to 10 specialized models: Deputado (core) + 9 biographical detail models
- Cross-references with interest registry unified models for complete deputy profiles
- Supports biographical research across all Portuguese legislature periods
"""

import logging
import os

# Import our models
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, Optional, Set

from .common_utilities import DataValidationUtils
from .enhanced_base_mapper import EnhancedSchemaMapper, SchemaError

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from database.models import Deputado, DeputyIdentityMapping

logger = logging.getLogger(__name__)


class RegistoBiograficoMapper(EnhancedSchemaMapper):
    """
    Comprehensive Biographical Registry Schema Mapper

    Processes RegistoBiografico<Legislatura>.xml files containing complete deputy biographical
    profiles across all Portuguese legislature periods from Constituinte to XV Legislature.

    Key Capabilities:
    1. Multi-format structure detection and processing
    2. Cross-legislature data consistency and evolution tracking
    3. Comprehensive biographical detail extraction and mapping
    4. Interest registry integration across schema versions
    5. Parliamentary activity history and position tracking

    Data Processing Flow:
    1. Structure Detection: Automatically identifies I vs VIII Legislature XML formats
    2. Core Biography: Maps basic biographical data to Deputado model
    3. Academic Record: Processes qualifications with status tracking (DeputadoHabilitacao)
    4. Career History: Maps professional positions with temporal flags (DeputadoCargoFuncao)
    5. Recognition Record: Processes titles and decorations (DeputadoTitulo, DeputadoCondecoracao)
    6. Publication Record: Maps scholarly and literary works (DeputadoObraPublicada)
    7. Parliamentary History: Tracks committee and working group activities (DeputadoAtividadeOrgao)
    8. Electoral History: Maps legislative mandates and party affiliations (DeputadoMandatoLegislativo)
    9. Interest Registry: Integrates professional interest declarations across versions

    Legislature Format Support:
    - Early Legislatures (I): RegistoBiograficoList format with comprehensive nested structures
    - Middle Legislatures (VIII): ArrayOfDadosRegistoBiografico with flattened hierarchy
    - Modern Legislatures (XV+): Enhanced formats with unified interest registry integration

    Data Quality Features:
    - Duplicate detection and handling across multiple data imports
    - Data consistency validation between biographical and interest registry data
    - Temporal data tracking for career and parliamentary position evolution
    - Cross-reference validation with existing deputy records
    """

    def __init__(self, session, import_status_record=None):
        super().__init__(session, import_status_record=import_status_record)
        # Use the passed SQLAlchemy session
        self.session = session

    def _process_organ_activity(
        self,
        activity_element: ET.Element,
        deputy_id,
        activity_type: str,
    ) -> bool:
        """
        Process a single organ activity element and create DeputadoAtividadeOrgao record.

        This helper method consolidates the common processing logic for committee,
        working group, and subcommittee activities, eliminating code duplication.

        Args:
            activity_element: XML element containing the activity data (actividadeCom, actividadeGT, or actividadeSCom)
            deputy_id: UUID of the deputy
            activity_type: Type of activity ('committee', 'working_group', or 'subcommittee')

        Returns:
            True if activity was processed successfully, False otherwise
        """
        from database.models import DeputadoAtividadeOrgao

        if activity_element is None:
            return False

        dados_orgao = activity_element.find("pt_ar_wsgode_objectos_DadosOrgaos")
        if dados_orgao is None:
            return False

        # Check for position details (cargoDes structure)
        tia_des = None
        try:
            cargo_des_elem = dados_orgao.find("cargoDes")
            if cargo_des_elem is not None:
                cargo_data = cargo_des_elem.find(
                    "pt_ar_wsgode_objectos_DadosCargosOrgao"
                )
                if cargo_data is not None:
                    tia_des = self._get_text_value(cargo_data, "tiaDes")
        except AttributeError:
            logger.debug(
                f"dados_orgao became None during {activity_type} processing"
            )

        atividade = DeputadoAtividadeOrgao(
            deputado_id=deputy_id,
            tipo_atividade=activity_type,
            org_id=self._safe_int(
                self._get_text_value(dados_orgao, "orgId")
            ),
            org_sigla=self._get_text_value(dados_orgao, "orgSigla"),
            org_des=self._get_text_value(dados_orgao, "orgDes"),
            tim_des=self._get_text_value(dados_orgao, "timDes"),
            leg_des=self._get_text_value(dados_orgao, "legDes"),
            tia_des=tia_des,
        )
        self._add_with_tracking(atividade)
        return True

    def get_expected_fields(self) -> Set[str]:
        return {
            # I Legislature XML structure - Complete field coverage
            "RegistoBiografico",
            "RegistoBiografico.RegistoBiograficoList",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb",
            # Basic biographical data
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadId",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadNomeCompleto",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadDtNascimento",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadSexo",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadProfissao",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadNaturalidade",
            # Academic qualifications (cadHabilitacoes)
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadHabilitacoes",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadHabilitacoes.pt_ar_wsgode_objectos_DadosHabilitacoes",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadHabilitacoes.pt_ar_wsgode_objectos_DadosHabilitacoes.habId",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadHabilitacoes.pt_ar_wsgode_objectos_DadosHabilitacoes.habDes",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadHabilitacoes.pt_ar_wsgode_objectos_DadosHabilitacoes.habTipoId",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadHabilitacoes.pt_ar_wsgode_objectos_DadosHabilitacoes.habEstado",
            # Professional roles (cadCargosFuncoes)
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadCargosFuncoes",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadCargosFuncoes.pt_ar_wsgode_objectos_DadosCargosFuncoes",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadCargosFuncoes.pt_ar_wsgode_objectos_DadosCargosFuncoes.funId",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadCargosFuncoes.pt_ar_wsgode_objectos_DadosCargosFuncoes.funDes",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadCargosFuncoes.pt_ar_wsgode_objectos_DadosCargosFuncoes.funOrdem",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadCargosFuncoes.pt_ar_wsgode_objectos_DadosCargosFuncoes.funAntiga",
            # Titles/Awards (cadTitulos)
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadTitulos",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadTitulos.pt_ar_wsgode_objectos_DadosTitulos",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadTitulos.pt_ar_wsgode_objectos_DadosTitulos.titId",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadTitulos.pt_ar_wsgode_objectos_DadosTitulos.titDes",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadTitulos.pt_ar_wsgode_objectos_DadosTitulos.titOrdem",
            # Decorations (cadCondecoracoes)
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadCondecoracoes",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadCondecoracoes.pt_ar_wsgode_objectos_DadosCondecoracoes",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadCondecoracoes.pt_ar_wsgode_objectos_DadosCondecoracoes.codId",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadCondecoracoes.pt_ar_wsgode_objectos_DadosCondecoracoes.codDes",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadCondecoracoes.pt_ar_wsgode_objectos_DadosCondecoracoes.codOrdem",
            # Published Works (cadObrasPublicadas)
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadObrasPublicadas",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadObrasPublicadas.pt_ar_wsgode_objectos_DadosObrasPublicadas",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadObrasPublicadas.pt_ar_wsgode_objectos_DadosObrasPublicadas.pubId",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadObrasPublicadas.pt_ar_wsgode_objectos_DadosObrasPublicadas.pubDes",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadObrasPublicadas.pt_ar_wsgode_objectos_DadosObrasPublicadas.pubOrdem",
            # Organ activities
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadActividadeOrgaos",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadActividadeOrgaos.actividadeCom",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadActividadeOrgaos.actividadeGT",
            # Committee activity details (actividadeCom)
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadActividadeOrgaos.actividadeCom.pt_ar_wsgode_objectos_DadosOrgaos",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadActividadeOrgaos.actividadeCom.pt_ar_wsgode_objectos_DadosOrgaos.orgSigla",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadActividadeOrgaos.actividadeCom.pt_ar_wsgode_objectos_DadosOrgaos.orgDes",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadActividadeOrgaos.actividadeCom.pt_ar_wsgode_objectos_DadosOrgaos.orgId",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadActividadeOrgaos.actividadeCom.pt_ar_wsgode_objectos_DadosOrgaos.legDes",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadActividadeOrgaos.actividadeCom.pt_ar_wsgode_objectos_DadosOrgaos.cargoDes",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadActividadeOrgaos.actividadeCom.pt_ar_wsgode_objectos_DadosOrgaos.cargoDes.pt_ar_wsgode_objectos_DadosCargosOrgao",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadActividadeOrgaos.actividadeCom.pt_ar_wsgode_objectos_DadosOrgaos.cargoDes.pt_ar_wsgode_objectos_DadosCargosOrgao.tiaDes",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadActividadeOrgaos.actividadeCom.pt_ar_wsgode_objectos_DadosOrgaos.timDes",
            # Working group activity details (actividadeGT)
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadActividadeOrgaos.actividadeGT.pt_ar_wsgode_objectos_DadosOrgaos",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadActividadeOrgaos.actividadeGT.pt_ar_wsgode_objectos_DadosOrgaos.orgSigla",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadActividadeOrgaos.actividadeGT.pt_ar_wsgode_objectos_DadosOrgaos.orgDes",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadActividadeOrgaos.actividadeGT.pt_ar_wsgode_objectos_DadosOrgaos.orgId",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadActividadeOrgaos.actividadeGT.pt_ar_wsgode_objectos_DadosOrgaos.timDes",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadActividadeOrgaos.actividadeGT.pt_ar_wsgode_objectos_DadosOrgaos.legDes",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadActividadeOrgaos.actividadeGT.pt_ar_wsgode_objectos_DadosOrgaos.cargoDes",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadActividadeOrgaos.actividadeGT.pt_ar_wsgode_objectos_DadosOrgaos.cargoDes.pt_ar_wsgode_objectos_DadosCargosOrgao",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadActividadeOrgaos.actividadeGT.pt_ar_wsgode_objectos_DadosOrgaos.cargoDes.pt_ar_wsgode_objectos_DadosCargosOrgao.tiaDes",
            # Subcommittee activity details (actividadeSCom)
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadActividadeOrgaos.actividadeSCom",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadActividadeOrgaos.actividadeSCom.pt_ar_wsgode_objectos_DadosOrgaos",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadActividadeOrgaos.actividadeSCom.pt_ar_wsgode_objectos_DadosOrgaos.orgSigla",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadActividadeOrgaos.actividadeSCom.pt_ar_wsgode_objectos_DadosOrgaos.orgDes",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadActividadeOrgaos.actividadeSCom.pt_ar_wsgode_objectos_DadosOrgaos.orgId",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadActividadeOrgaos.actividadeSCom.pt_ar_wsgode_objectos_DadosOrgaos.timDes",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadActividadeOrgaos.actividadeSCom.pt_ar_wsgode_objectos_DadosOrgaos.legDes",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadActividadeOrgaos.actividadeSCom.pt_ar_wsgode_objectos_DadosOrgaos.cargoDes",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadActividadeOrgaos.actividadeSCom.pt_ar_wsgode_objectos_DadosOrgaos.cargoDes.pt_ar_wsgode_objectos_DadosCargosOrgao",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadActividadeOrgaos.actividadeSCom.pt_ar_wsgode_objectos_DadosOrgaos.cargoDes.pt_ar_wsgode_objectos_DadosCargosOrgao.tiaDes",
            # Deputy legislature data with all I Legislature fields
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadDeputadoLegis",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadDeputadoLegis.pt_ar_wsgode_objectos_DadosDeputadoLegis",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadDeputadoLegis.pt_ar_wsgode_objectos_DadosDeputadoLegis.depNomeParlamentar",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadDeputadoLegis.pt_ar_wsgode_objectos_DadosDeputadoLegis.legDes",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadDeputadoLegis.pt_ar_wsgode_objectos_DadosDeputadoLegis.ceDes",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadDeputadoLegis.pt_ar_wsgode_objectos_DadosDeputadoLegis.parSigla",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadDeputadoLegis.pt_ar_wsgode_objectos_DadosDeputadoLegis.parDes",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadDeputadoLegis.pt_ar_wsgode_objectos_DadosDeputadoLegis.gpSigla",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadDeputadoLegis.pt_ar_wsgode_objectos_DadosDeputadoLegis.gpDes",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadDeputadoLegis.pt_ar_wsgode_objectos_DadosDeputadoLegis.indDes",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadDeputadoLegis.pt_ar_wsgode_objectos_DadosDeputadoLegis.urlVideoBiografia",
            "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb.cadDeputadoLegis.pt_ar_wsgode_objectos_DadosDeputadoLegis.indData",
            # Interest Registry V2 (RegistoInteressesV2List)
            "RegistoBiografico.RegistoInteressesV2List",
            "RegistoBiografico.RegistoInteressesV2List.pt_ar_wsgode_objectos_DadosDeputadoRgiWebV2",
            "RegistoBiografico.RegistoInteressesV2List.pt_ar_wsgode_objectos_DadosDeputadoRgiWebV2.cadId",
            "RegistoBiografico.RegistoInteressesV2List.pt_ar_wsgode_objectos_DadosDeputadoRgiWebV2.cadEstadoCivilCod",
            "RegistoBiografico.RegistoInteressesV2List.pt_ar_wsgode_objectos_DadosDeputadoRgiWebV2.cadNomeCompleto",
            "RegistoBiografico.RegistoInteressesV2List.pt_ar_wsgode_objectos_DadosDeputadoRgiWebV2.cadActividadeProfissional",
            "RegistoBiografico.RegistoInteressesV2List.pt_ar_wsgode_objectos_DadosDeputadoRgiWebV2.cadEstadoCivilDes",
            # Interest Registry V1 (RegistoInteressesList)
            "RegistoBiografico.RegistoInteressesList",
            # Additional Interest Registry versions found in I Legislature files
            "RegistoBiografico.RegistoInteressesV1List",
            "RegistoBiografico.RegistoInteressesV3List",
            "RegistoBiografico.RegistoInteressesV5List",
            # VIII Legislature XML structure (ArrayOfDadosRegistoBiografico)
            "ArrayOfDadosRegistoBiografico",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico",
            # Basic biographical data - VIII Legislature
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadId",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadNomeCompleto",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadDtNascimento",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadSexo",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadProfissao",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadNaturalidade",
            # Academic qualifications - VIII Legislature
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadHabilitacoes",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadHabilitacoes.DadosHabilitacoes",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadHabilitacoes.DadosHabilitacoes.HabId",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadHabilitacoes.DadosHabilitacoes.HabDes",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadHabilitacoes.DadosHabilitacoes.HabTipoId",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadHabilitacoes.DadosHabilitacoes.HabEstado",
            # Professional roles - VIII Legislature
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadCargosFuncoes",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadCargosFuncoes.DadosCargosFuncoes",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadCargosFuncoes.DadosCargosFuncoes.FunId",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadCargosFuncoes.DadosCargosFuncoes.FunDes",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadCargosFuncoes.DadosCargosFuncoes.FunOrdem",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadCargosFuncoes.DadosCargosFuncoes.FunAntiga",
            # Titles/Awards - VIII Legislature
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadTitulos",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadTitulos.DadosTitulos",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadTitulos.DadosTitulos.TitId",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadTitulos.DadosTitulos.TitDes",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadTitulos.DadosTitulos.TitOrdem",
            # Decorations - VIII Legislature
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadCondecoracoes",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadCondecoracoes.DadosCondecoracoes",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadCondecoracoes.DadosCondecoracoes.CodId",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadCondecoracoes.DadosCondecoracoes.CodDes",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadCondecoracoes.DadosCondecoracoes.CodOrdem",
            # Published Works - VIII Legislature
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadObrasPublicadas",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadObrasPublicadas.DadosObrasPublicadas",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadObrasPublicadas.DadosObrasPublicadas.PubId",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadObrasPublicadas.DadosObrasPublicadas.PubDes",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadObrasPublicadas.DadosObrasPublicadas.PubOrdem",
            # Deputy legislature data - VIII Legislature
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadDeputadoLegis",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadDeputadoLegis.DadosDeputadoLegis",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadDeputadoLegis.DadosDeputadoLegis.DepNomeParlamentar",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadDeputadoLegis.DadosDeputadoLegis.LegDes",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadDeputadoLegis.DadosDeputadoLegis.CeDes",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadDeputadoLegis.DadosDeputadoLegis.ParSigla",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadDeputadoLegis.DadosDeputadoLegis.ParDes",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadDeputadoLegis.DadosDeputadoLegis.GpSigla",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadDeputadoLegis.DadosDeputadoLegis.GpDes",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadDeputadoLegis.DadosDeputadoLegis.IndDes",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadDeputadoLegis.DadosDeputadoLegis.IndData",
            # Organ activities - VIII Legislature
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadActividadeOrgaos",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadActividadeOrgaos.actividadeCom",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadActividadeOrgaos.actividadeCom.pt_ar_wsgode_objectos_DadosOrgaos",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadActividadeOrgaos.actividadeCom.pt_ar_wsgode_objectos_DadosOrgaos.orgId",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadActividadeOrgaos.actividadeCom.pt_ar_wsgode_objectos_DadosOrgaos.orgDes",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadActividadeOrgaos.actividadeCom.pt_ar_wsgode_objectos_DadosOrgaos.orgSigla",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadActividadeOrgaos.actividadeCom.pt_ar_wsgode_objectos_DadosOrgaos.legDes",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadActividadeOrgaos.actividadeCom.pt_ar_wsgode_objectos_DadosOrgaos.timDes",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadActividadeOrgaos.actividadeCom.pt_ar_wsgode_objectos_DadosOrgaos.cargoDes",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadActividadeOrgaos.actividadeCom.pt_ar_wsgode_objectos_DadosOrgaos.cargoDes.pt_ar_wsgode_objectos_DadosCargosOrgao",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadActividadeOrgaos.actividadeCom.pt_ar_wsgode_objectos_DadosOrgaos.cargoDes.pt_ar_wsgode_objectos_DadosCargosOrgao.tiaDes",
            # Working groups - VIII Legislature
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadActividadeOrgaos.actividadeGT",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadActividadeOrgaos.actividadeGT.pt_ar_wsgode_objectos_DadosOrgaos",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadActividadeOrgaos.actividadeGT.pt_ar_wsgode_objectos_DadosOrgaos.orgId",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadActividadeOrgaos.actividadeGT.pt_ar_wsgode_objectos_DadosOrgaos.orgDes",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadActividadeOrgaos.actividadeGT.pt_ar_wsgode_objectos_DadosOrgaos.orgSigla",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadActividadeOrgaos.actividadeGT.pt_ar_wsgode_objectos_DadosOrgaos.legDes",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadActividadeOrgaos.actividadeGT.pt_ar_wsgode_objectos_DadosOrgaos.timDes",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadActividadeOrgaos.actividadeGT.pt_ar_wsgode_objectos_DadosOrgaos.cargoDes",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadActividadeOrgaos.actividadeGT.pt_ar_wsgode_objectos_DadosOrgaos.cargoDes.pt_ar_wsgode_objectos_DadosCargosOrgao",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadActividadeOrgaos.actividadeGT.pt_ar_wsgode_objectos_DadosOrgaos.cargoDes.pt_ar_wsgode_objectos_DadosCargosOrgao.tiaDes",
            # Subcommittees - VIII Legislature
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadActividadeOrgaos.actividadeSCom",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadActividadeOrgaos.actividadeSCom.pt_ar_wsgode_objectos_DadosOrgaos",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadActividadeOrgaos.actividadeSCom.pt_ar_wsgode_objectos_DadosOrgaos.orgId",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadActividadeOrgaos.actividadeSCom.pt_ar_wsgode_objectos_DadosOrgaos.orgDes",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadActividadeOrgaos.actividadeSCom.pt_ar_wsgode_objectos_DadosOrgaos.orgSigla",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadActividadeOrgaos.actividadeSCom.pt_ar_wsgode_objectos_DadosOrgaos.legDes",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadActividadeOrgaos.actividadeSCom.pt_ar_wsgode_objectos_DadosOrgaos.timDes",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadActividadeOrgaos.actividadeSCom.pt_ar_wsgode_objectos_DadosOrgaos.cargoDes",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadActividadeOrgaos.actividadeSCom.pt_ar_wsgode_objectos_DadosOrgaos.cargoDes.pt_ar_wsgode_objectos_DadosCargosOrgao",
            "ArrayOfDadosRegistoBiografico.DadosRegistoBiografico.CadActividadeOrgaos.actividadeSCom.pt_ar_wsgode_objectos_DadosOrgaos.cargoDes.pt_ar_wsgode_objectos_DadosCargosOrgao.tiaDes",
        }

    def validate_and_map(
        self, xml_root: ET.Element, file_info: Dict, strict_mode: bool = False
    ) -> Dict:
        """Map biographical data to database with comprehensive field processing - supports both I and VIII Legislature structures"""
        # Store for use in nested methods
        self.file_info = file_info

        results = {"records_processed": 0, "records_imported": 0, "errors": []}

        try:
            # Validate schema coverage according to strict mode
            self.validate_schema_coverage(xml_root, file_info, strict_mode)

            # Determine XML structure and process accordingly
            if xml_root.tag == "ArrayOfDadosRegistoBiografico":
                # ArrayOfDadosRegistoBiografico structure (used by multiple legislatures)
                # Extract legislature from file path for accurate logging - use base mapper method
                try:
                    legislature_sigla = self._extract_legislatura(file_info.get("file_path", ""), None)
                    legislature_name = legislature_sigla
                except:
                    # Fallback to local method if base method fails
                    legislature_name = self._extract_legislature_from_path(
                        file_info.get("file_path", "")
                    )
                logger.info(
                    f"Processing {legislature_name} biographical structure (ArrayOfDadosRegistoBiografico format)"
                )
                for record in xml_root.findall("DadosRegistoBiografico"):
                    try:
                        success = self._process_viii_legislature_biographical_record(
                            record, file_info
                        )
                        results["records_processed"] += 1
                        if success:
                            results["records_imported"] += 1
                    except Exception as e:
                        error_msg = f"Error processing {legislature_name} biographical record: {str(e)}"
                        results["errors"].append(error_msg)
                        logger.error(error_msg)
                        if strict_mode:
                            raise
            else:
                # I Legislature structure - check for different possible structures
                legislature_name = self._extract_legislature_from_path(
                    file_info.get("file_path", "")
                )
                logger.info(
                    f"Processing {legislature_name} biographical structure (I Legislature format)"
                )

                # Try I Legislature specific structure first
                biografico_list = xml_root.find("RegistoBiograficoList")
                if biografico_list is not None:
                    for record in biografico_list.findall(
                        "pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb"
                    ):
                        try:
                            success = self._process_i_legislature_biographical_record(
                                record, file_info
                            )
                            results["records_processed"] += 1
                            if success:
                                results["records_imported"] += 1
                        except Exception as e:
                            error_msg = f"Error processing I Legislature biographical record: {str(e)}"
                            results["errors"].append(error_msg)
                            logger.error(error_msg)
                            if strict_mode:
                                raise
                else:
                    # Fallback: Check for ArrayOfDadosRegistoBiografico structure (VIII Legislature format in I directory)
                    logger.info(
                        f"I Legislature directory contains VIII Legislature format, processing accordingly"
                    )
                    for record in xml_root.findall("DadosRegistoBiografico"):
                        try:
                            success = (
                                self._process_viii_legislature_biographical_record(
                                    record, file_info
                                )
                            )
                            results["records_processed"] += 1
                            if success:
                                results["records_imported"] += 1
                        except Exception as e:
                            error_msg = f"Error processing {legislature_name} biographical record: {str(e)}"
                            results["errors"].append(error_msg)
                            logger.error(error_msg)
                            if strict_mode:
                                raise

            # Process Interest Registry V2 if present
            interesses_list = xml_root.find("RegistoInteressesV2List")
            if interesses_list is not None:
                for record in interesses_list.findall(
                    "pt_ar_wsgode_objectos_DadosDeputadoRgiWebV2"
                ):
                    try:
                        success = self._process_registo_interesses_v2(record, file_info)
                        results["records_processed"] += 1
                        if success:
                            results["records_imported"] += 1
                    except Exception as e:
                        error_msg = f"Error processing interest registry V2: {str(e)}"
                        results["errors"].append(error_msg)
                        logger.error(error_msg)
                        if strict_mode:
                            raise

            return results

        except Exception as e:
            error_msg = f"Error in biographical mapping: {str(e)}"
            results["errors"].append(error_msg)
            logger.error(error_msg)
            if strict_mode:
                raise
            return results

    def _process_i_legislature_biographical_record(
        self, record: ET.Element, file_info: Dict
    ) -> bool:
        """Process comprehensive I Legislature biographical record with all fields"""
        try:
            # Safety check - ensure record is not None
            if record is None:
                logger.warning(
                    "Received None record in I Legislature biographical processing"
                )
                return False

            from database.models import (
                Deputado,
                DeputadoAtividadeOrgao,
                DeputadoCargoFuncao,
                DeputadoCondecoracao,
                DeputadoHabilitacao,
                DeputadoMandatoLegislativo,
                DeputadoObraPublicada,
                DeputadoTitulo,
            )

            # Extract basic biographical data
            cad_id = self._get_text_value(record, "cadId")
            if not cad_id:
                raise ValueError(f"Invalid cadId value: {cad_id} in record")

            cad_id = self._safe_int(cad_id)
            if cad_id is None:
                raise ValueError(f"Invalid cadId value: {cad_id} in record")

            # Get or create deputycad using robust matching
            nome_completo = self._normalize_name(self._get_text_value(record, "cadNomeCompleto"))

            # TODO: associate data with cad_id instead of deputy.id
            deputy = None

            # Process Legislative Mandates (cadDeputadoLegis)
            legislaturas = record.find("cadDeputadoLegis")
            if legislaturas is not None:
                for mandato in legislaturas.findall(
                    "pt_ar_wsgode_objectos_DadosDeputadoLegis"
                ):
                    if mandato is None:
                        continue

                    leg_des = self._get_text_value(mandato, "legDes")
                    ce_des = self._get_text_value(mandato, "ceDes")
                    nome_parlamentar = self._get_text_value(
                        mandato, "depNomeParlamentar"
                    )
                    
                    # Log extracted legislature from XML (debug level to avoid UI clutter)
                    logger.debug(f"[LEG_DES_EXTRACT] Extracted leg_des='{leg_des}' from XML mandate record")
                    logger.debug(f"[LEG_DES_EXTRACT]   - nome_parlamentar: {nome_parlamentar}")
                    logger.debug(f"[LEG_DES_EXTRACT]   - ce_des: {ce_des}")
                    logger.debug(f"[LEG_DES_EXTRACT]   - file_path: {self.file_info.get('file_path', 'unknown')}")
                    
                    # REMOVED: _should_create_mandate filter - was a band-aid fix for Interest Registry auto-creation issue
                    # The biographical data is clean and authoritative. Interest Registry mapper now properly
                    # fails when deputies don't exist instead of auto-creating bogus cross-legislature records.
                    
                    # Check if this mandate has a LegDes that overrides the file-level legislature
                    if leg_des:
                        # Use mandate-specific legislature instead of file-level legislature
                        try:
                            mandate_legislatura_sigla = self._extract_legislatura_from_xml_content(leg_des)
                            if mandate_legislatura_sigla:
                                mandate_legislatura = self._get_or_create_legislatura(mandate_legislatura_sigla)
                                legislatura_id = mandate_legislatura.id
                                logger.debug(f"LegDes '{leg_des}' in mandate overrode file-level legislature for deputy {nome_completo} (CadId: {cad_id}) - using legislature ID {legislatura_id}")
                            else:
                                # Fallback to file-level legislature
                                legislatura_id = self._get_legislatura_id(self.file_info)
                        except Exception as e:
                            logger.warning(f"Failed to extract legislature from mandate LegDes '{leg_des}' for deputy {nome_completo}: {e} - using file-level legislature")
                            legislatura_id = self._get_legislatura_id(self.file_info)
                    else:
                        # No LegDes in mandate, use file-level legislature
                        legislatura_id = self._get_legislatura_id(self.file_info)
                    
                    deputy = self._find_deputy_robust(
                        cad_id,
                        nome_completo=nome_completo,
                        nome_parlamentar=nome_parlamentar,
                        legislatura_id=legislatura_id,
                    )

                    # Update existing fields
                    deputy.nome_completo = nome_completo or deputy.nome_completo
                    deputy.sexo = self._get_text_value(record, "cadSexo") or deputy.sexo
                    deputy.profissao = (
                        self._get_text_value(record, "cadProfissao") or deputy.profissao
                    )
                    deputy.data_nascimento = (
                        self._parse_date(
                            self._get_text_value(record, "cadDtNascimento")
                        )
                        or deputy.data_nascimento
                    )
                    deputy.naturalidade = (
                        self._get_text_value(record, "cadNaturalidade")
                        or deputy.naturalidade
                    )

                    if leg_des:
                        # Check if already exists
                        existing = (
                            self.session.query(DeputadoMandatoLegislativo)
                            .filter(
                                DeputadoMandatoLegislativo.deputado_id == deputy.id,
                                DeputadoMandatoLegislativo.leg_des == leg_des,
                                DeputadoMandatoLegislativo.ce_des == ce_des,
                            )
                            .first()
                        )

                        if not existing:
                            # Extract party information
                            par_sigla = self._get_text_value(mandato, "parSigla")
                            par_des = self._get_text_value(mandato, "parDes")
                            
                            # Log mandate creation details (debug level to avoid UI clutter)
                            logger.debug(f"[MANDATE_CREATE] Creating mandate for deputy {deputy.id} ({deputy.nome_completo})")
                            logger.debug(f"[MANDATE_CREATE]   - leg_des: '{leg_des}'")
                            logger.debug(f"[MANDATE_CREATE]   - deputy.legislatura_id: {deputy.legislatura_id}")
                            logger.debug(f"[MANDATE_CREATE]   - file_path: {self.file_info.get('file_path', 'unknown')}")
                            
                            # Create base mandate record
                            mandate = DeputadoMandatoLegislativo(
                                deputado_id=deputy.id,
                                dep_nome_parlamentar=nome_parlamentar,
                                leg_des=leg_des,
                                ce_des=ce_des,  # New I Legislature field
                                par_sigla=par_sigla,
                                par_des=par_des,
                                gp_sigla=self._get_text_value(
                                    mandato, "gpSigla"
                                ),  # New I Legislature field
                                gp_des=self._get_text_value(
                                    mandato, "gpDes"
                                ),  # New I Legislature field
                                ind_des=self._get_text_value(
                                    mandato, "indDes"
                                ),  # New I Legislature field
                                url_video_biografia=self._get_text_value(
                                    mandato, "urlVideoBiografia"
                                ),  # New I Legislature field
                                ind_data=self._parse_date(
                                    self._get_text_value(mandato, "indData")
                                ),  # New I Legislature field
                            )
                            
                            # Update mandate with coalition context
                            if par_sigla:
                                self.update_mandate_coalition_context(mandate, par_sigla)
                            
                            self._add_with_tracking(mandate)

            # Process Academic Qualifications (cadHabilitacoes)
            habilitacoes = record.find("cadHabilitacoes")
            if habilitacoes is not None:
                for hab in habilitacoes.findall(
                    "pt_ar_wsgode_objectos_DadosHabilitacoes"
                ):
                    if hab is None:
                        continue
                    hab_id = self._get_text_value(hab, "habId")
                    if hab_id:
                        # Check if already exists
                        existing = (
                            self.session.query(DeputadoHabilitacao)
                            .filter(
                                DeputadoHabilitacao.deputado_id == deputy.id,
                                DeputadoHabilitacao.hab_id == self._safe_int(hab_id),
                            )
                            .first()
                        )

                        if not existing:
                            qualification = DeputadoHabilitacao(
                                deputado_id=deputy.id,
                                hab_id=self._safe_int(hab_id),
                                hab_des=self._get_text_value(hab, "habDes"),
                                hab_tipo_id=self._safe_int(
                                    self._get_text_value(hab, "habTipoId")
                                ),
                                hab_estado=self._get_text_value(
                                    hab, "habEstado"
                                ),  # New I Legislature field
                            )
                            self._add_with_tracking(qualification)

            # Process Professional Roles (cadCargosFuncoes)
            cargos_funcoes = record.find("cadCargosFuncoes")
            if cargos_funcoes is not None:
                for cargo in cargos_funcoes.findall(
                    "pt_ar_wsgode_objectos_DadosCargosFuncoes"
                ):
                    if cargo is None:
                        continue
                    fun_id = self._get_text_value(cargo, "funId")
                    if fun_id:
                        # Check if already exists
                        existing = (
                            self.session.query(DeputadoCargoFuncao)
                            .filter(
                                DeputadoCargoFuncao.deputado_id == deputy.id,
                                DeputadoCargoFuncao.fun_id == self._safe_int(fun_id),
                            )
                            .first()
                        )

                        if not existing:
                            role = DeputadoCargoFuncao(
                                deputado_id=deputy.id,
                                fun_id=self._safe_int(fun_id),
                                fun_des=self._get_text_value(cargo, "funDes"),
                                fun_ordem=self._safe_int(
                                    self._get_text_value(cargo, "funOrdem")
                                ),  # New I Legislature field
                                fun_antiga=self._get_text_value(
                                    cargo, "funAntiga"
                                ),  # New I Legislature field
                            )
                            self._add_with_tracking(role)

            # Process Titles/Awards (cadTitulos)
            titulos = record.find("cadTitulos")
            if titulos is not None:
                for titulo in titulos.findall("pt_ar_wsgode_objectos_DadosTitulos"):
                    if titulo is None:
                        continue
                    tit_id = self._get_text_value(titulo, "titId")
                    if tit_id:
                        # Check if already exists
                        existing = (
                            self.session.query(DeputadoTitulo)
                            .filter(
                                DeputadoTitulo.deputado_id == deputy.id,
                                DeputadoTitulo.tit_id == self._safe_int(tit_id),
                            )
                            .first()
                        )

                        if not existing:
                            title = DeputadoTitulo(
                                deputado_id=deputy.id,
                                tit_id=self._safe_int(tit_id),
                                tit_des=self._get_text_value(titulo, "titDes"),
                                tit_ordem=self._safe_int(
                                    self._get_text_value(titulo, "titOrdem")
                                ),
                            )
                            self._add_with_tracking(title)

            # Process Decorations (cadCondecoracoes)
            condecoracoes = record.find("cadCondecoracoes")
            if condecoracoes is not None:
                for cond in condecoracoes.findall(
                    "pt_ar_wsgode_objectos_DadosCondecoracoes"
                ):
                    if cond is None:
                        continue
                    cod_id = self._get_text_value(cond, "codId")
                    if cod_id:
                        # Check if already exists
                        existing = (
                            self.session.query(DeputadoCondecoracao)
                            .filter(
                                DeputadoCondecoracao.deputado_id == deputy.id,
                                DeputadoCondecoracao.cod_id == self._safe_int(cod_id),
                            )
                            .first()
                        )

                        if not existing:
                            decoration = DeputadoCondecoracao(
                                deputado_id=deputy.id,
                                cod_id=self._safe_int(cod_id),
                                cod_des=self._get_text_value(cond, "codDes"),
                                cod_ordem=self._safe_int(
                                    self._get_text_value(cond, "codOrdem")
                                ),
                            )
                            self._add_with_tracking(decoration)

            # Process Published Works (cadObrasPublicadas)
            obras = record.find("cadObrasPublicadas")
            if obras is not None:
                for obra in obras.findall("pt_ar_wsgode_objectos_DadosObrasPublicadas"):
                    if obra is None:
                        continue
                    pub_id = self._get_text_value(obra, "pubId")
                    if pub_id:
                        # Check if already exists
                        existing = (
                            self.session.query(DeputadoObraPublicada)
                            .filter(
                                DeputadoObraPublicada.deputado_id == deputy.id,
                                DeputadoObraPublicada.pub_id == self._safe_int(pub_id),
                            )
                            .first()
                        )

                        if not existing:
                            publication = DeputadoObraPublicada(
                                deputado_id=deputy.id,
                                pub_id=self._safe_int(pub_id),
                                pub_des=self._get_text_value(obra, "pubDes"),
                                pub_ordem=self._safe_int(
                                    self._get_text_value(obra, "pubOrdem")
                                ),
                            )
                            self._add_with_tracking(publication)

            # Process Organ Activities (cadActividadeOrgaos)
            atividades_orgaos = record.find("cadActividadeOrgaos")
            if atividades_orgaos is not None:
                # Process Committee Activities (actividadeCom)
                comissoes = atividades_orgaos.findall("actividadeCom")
                for comissao in comissoes:
                    if comissao is None:
                        continue
                    dados_orgao = comissao.find("pt_ar_wsgode_objectos_DadosOrgaos")
                    if dados_orgao is not None:
                        # Check for position details in committee (cargoDes structure)
                        tia_des = None
                        try:
                            cargo_des_elem = dados_orgao.find("cargoDes")
                            if cargo_des_elem is not None:
                                cargo_data = cargo_des_elem.find(
                                    "pt_ar_wsgode_objectos_DadosCargosOrgao"
                                )
                                if cargo_data is not None:
                                    tia_des = self._get_text_value(cargo_data, "tiaDes")
                        except AttributeError:
                            # Handle case where dados_orgao might be None despite check
                            logger.debug("dados_orgao became None during processing")

                        atividade = DeputadoAtividadeOrgao(
                            deputado_id=deputy.id,
                            tipo_atividade="committee",
                            org_id=self._safe_int(
                                self._get_text_value(dados_orgao, "orgId")
                            ),
                            org_sigla=self._get_text_value(dados_orgao, "orgSigla"),
                            org_des=self._get_text_value(dados_orgao, "orgDes"),
                            tim_des=self._get_text_value(dados_orgao, "timDes"),
                            leg_des=self._get_text_value(dados_orgao, "legDes"),
                            tia_des=tia_des,
                        )
                        self._add_with_tracking(atividade)

                # Process Working Group Activities (actividadeGT)
                grupos_trabalho = atividades_orgaos.findall("actividadeGT")
                for grupo in grupos_trabalho:
                    if grupo is None:
                        continue
                    dados_orgao = grupo.find("pt_ar_wsgode_objectos_DadosOrgaos")
                    if dados_orgao is not None:
                        # Check for position details (cargoDes structure)
                        tia_des = None
                        try:
                            cargo_des_elem = dados_orgao.find("cargoDes")
                            if cargo_des_elem is not None:
                                cargo_data = cargo_des_elem.find(
                                    "pt_ar_wsgode_objectos_DadosCargosOrgao"
                                )
                                if cargo_data is not None:
                                    tia_des = self._get_text_value(cargo_data, "tiaDes")
                        except AttributeError:
                            # Handle case where dados_orgao might be None despite check
                            logger.debug(
                                "dados_orgao became None during working group processing"
                            )

                        atividade = DeputadoAtividadeOrgao(
                            deputado_id=deputy.id,
                            tipo_atividade="working_group",
                            org_id=self._safe_int(
                                self._get_text_value(dados_orgao, "orgId")
                            ),
                            org_sigla=self._get_text_value(dados_orgao, "orgSigla"),
                            org_des=self._get_text_value(dados_orgao, "orgDes"),
                            tim_des=self._get_text_value(dados_orgao, "timDes"),
                            leg_des=self._get_text_value(dados_orgao, "legDes"),
                            tia_des=tia_des,
                        )
                        self._add_with_tracking(atividade)

                # Process Subcommittee Activities (actividadeSCom)
                subcomissoes = atividades_orgaos.findall("actividadeSCom")
                for subcomissao in subcomissoes:
                    if subcomissao is None:
                        continue
                    dados_orgao = subcomissao.find("pt_ar_wsgode_objectos_DadosOrgaos")
                    if dados_orgao is not None:
                        # Check for position details (cargoDes structure)
                        tia_des = None
                        try:
                            cargo_des_elem = dados_orgao.find("cargoDes")
                            if cargo_des_elem is not None:
                                cargo_data = cargo_des_elem.find(
                                    "pt_ar_wsgode_objectos_DadosCargosOrgao"
                                )
                                if cargo_data is not None:
                                    tia_des = self._get_text_value(cargo_data, "tiaDes")
                        except AttributeError:
                            # Handle case where dados_orgao might be None despite check
                            logger.debug(
                                "dados_orgao became None during subcommittee processing"
                            )

                        atividade = DeputadoAtividadeOrgao(
                            deputado_id=deputy.id,
                            tipo_atividade="subcommittee",
                            org_id=self._safe_int(
                                self._get_text_value(dados_orgao, "orgId")
                            ),
                            org_sigla=self._get_text_value(dados_orgao, "orgSigla"),
                            org_des=self._get_text_value(dados_orgao, "orgDes"),
                            tim_des=self._get_text_value(dados_orgao, "timDes"),
                            leg_des=self._get_text_value(dados_orgao, "legDes"),
                            tia_des=tia_des,
                        )
                        self._add_with_tracking(atividade)

            return True

        except Exception as e:
            # Enhanced error logging for NoneType debugging
            error_msg = str(e)
            if "'NoneType' object has no attribute 'find'" in error_msg:
                logger.error(
                    f"NoneType 'find' error in I Legislature biographical processing"
                )
                logger.error(
                    f"Record structure: {record.tag if record else 'record is None'}"
                )
                if record is not None:
                    logger.error(f"Record children: {[child.tag for child in record]}")
                import traceback

                logger.error(f"Full traceback: {traceback.format_exc()}")
            else:
                logger.error(
                    f"Error processing I Legislature biographical record: {error_msg}"
                )
            return False

    def _process_viii_legislature_biographical_record(
        self, record: ET.Element, file_info: Dict
    ) -> bool:
        """Process VIII Legislature biographical record (ArrayOfDadosRegistoBiografico structure)"""
        try:
            from database.models import (
                Deputado,
                DeputadoAtividadeOrgao,
                DeputadoCargoFuncao,
                DeputadoCondecoracao,
                DeputadoHabilitacao,
                DeputadoMandatoLegislativo,
                DeputadoObraPublicada,
                DeputadoTitulo,
            )

            # Extract basic biographical data using VIII Legislature structure
            cad_id = self._get_text_value(record, "CadId")
            logger.debug(f"Extracted CadId: '{cad_id}' from record")
            if not cad_id:
                logger.debug(
                    "No CadId found, skipping deputy creation (but still processing record)"
                )
                return False

            logger.debug(f"Processing deputy with CadId: {cad_id}")
            cad_id = self._safe_int(cad_id)
            if cad_id is None:
                logger.warning("Invalid cadId format, skipping record")
                return False

            # Get or create deputy using robust matching
            nome_completo = self._normalize_name(self._get_text_value(record, "CadNomeCompleto"))
            
            # Check if this record has a LegDes that overrides the file-level legislature
            record_leg_des = self._get_text_value(record, "LegDes")
            if record_leg_des:
                # Use record-specific legislature instead of file-level legislature
                try:
                    record_legislatura_sigla = self._extract_legislatura_from_xml_content(record_leg_des)
                    if record_legislatura_sigla:
                        record_legislatura = self._get_or_create_legislatura(record_legislatura_sigla)
                        legislatura_id = record_legislatura.id
                        logger.debug(f"LegDes '{record_leg_des}' in record overrode file-level legislature for deputy {nome_completo} (CadId: {cad_id}) - using legislature ID {legislatura_id}")
                    else:
                        # Fallback to file-level legislature
                        legislatura_id = self._get_legislatura_id(self.file_info)
                except Exception as e:
                    logger.warning(f"Failed to extract legislature from LegDes '{record_leg_des}' for deputy {nome_completo}: {e} - using file-level legislature")
                    legislatura_id = self._get_legislatura_id(self.file_info)
            else:
                # No LegDes in record, use file-level legislature
                legislatura_id = self._get_legislatura_id(self.file_info)
                
            deputy = self._find_deputy_robust(cad_id, nome_completo=nome_completo, legislatura_id=legislatura_id)

            # Update existing fields
            deputy.nome_completo = nome_completo or deputy.nome_completo
            deputy.sexo = self._get_text_value(record, "CadSexo") or deputy.sexo
            deputy.profissao = (
                self._get_text_value(record, "CadProfissao") or deputy.profissao
            )
            deputy.data_nascimento = (
                self._parse_date(self._get_text_value(record, "CadDtNascimento"))
                or deputy.data_nascimento
            )
            deputy.naturalidade = (
                self._get_text_value(record, "CadNaturalidade") or deputy.naturalidade
            )

            # Process Academic Qualifications (CadHabilitacoes)
            habilitacoes = record.find("CadHabilitacoes")
            if habilitacoes is not None:
                for hab in habilitacoes.findall("DadosHabilitacoes"):
                    hab_id = self._get_text_value(hab, "HabId")
                    if hab_id:
                        existing = (
                            self.session.query(DeputadoHabilitacao)
                            .filter(
                                DeputadoHabilitacao.deputado_id == deputy.id,
                                DeputadoHabilitacao.hab_id == self._safe_int(hab_id),
                            )
                            .first()
                        )

                        if not existing:
                            qualification = DeputadoHabilitacao(
                                deputado_id=deputy.id,
                                hab_id=self._safe_int(hab_id),
                                hab_des=self._get_text_value(hab, "HabDes"),
                                hab_tipo_id=self._safe_int(
                                    self._get_text_value(hab, "HabTipoId")
                                ),
                                hab_estado=self._get_text_value(hab, "HabEstado"),
                            )
                            self._add_with_tracking(qualification)

            # Process Professional Roles (CadCargosFuncoes)
            cargos_funcoes = record.find("CadCargosFuncoes")
            if cargos_funcoes is not None:
                for cargo in cargos_funcoes.findall("DadosCargosFuncoes"):
                    fun_id = self._get_text_value(cargo, "FunId")
                    if fun_id:
                        existing = (
                            self.session.query(DeputadoCargoFuncao)
                            .filter(
                                DeputadoCargoFuncao.deputado_id == deputy.id,
                                DeputadoCargoFuncao.fun_id == self._safe_int(fun_id),
                            )
                            .first()
                        )

                        if not existing:
                            role = DeputadoCargoFuncao(
                                deputado_id=deputy.id,
                                fun_id=self._safe_int(fun_id),
                                fun_des=self._get_text_value(cargo, "FunDes"),
                                fun_ordem=self._safe_int(
                                    self._get_text_value(cargo, "FunOrdem")
                                ),
                                fun_antiga=self._get_text_value(cargo, "FunAntiga"),
                            )
                            self._add_with_tracking(role)

            # Process Titles/Awards (CadTitulos)
            titulos = record.find("CadTitulos")
            if titulos is not None:
                for titulo in titulos.findall("DadosTitulos"):
                    tit_id = self._get_text_value(titulo, "TitId")
                    if tit_id:
                        existing = (
                            self.session.query(DeputadoTitulo)
                            .filter(
                                DeputadoTitulo.deputado_id == deputy.id,
                                DeputadoTitulo.tit_id == self._safe_int(tit_id),
                            )
                            .first()
                        )

                        if not existing:
                            title = DeputadoTitulo(
                                deputado_id=deputy.id,
                                tit_id=self._safe_int(tit_id),
                                tit_des=self._get_text_value(titulo, "TitDes"),
                                tit_ordem=self._safe_int(
                                    self._get_text_value(titulo, "TitOrdem")
                                ),
                            )
                            self._add_with_tracking(title)

            # Process Decorations (CadCondecoracoes)
            condecoracoes = record.find("CadCondecoracoes")
            if condecoracoes is not None:
                for cond in condecoracoes.findall("DadosCondecoracoes"):
                    cod_id = self._get_text_value(cond, "CodId")
                    if cod_id:
                        existing = (
                            self.session.query(DeputadoCondecoracao)
                            .filter(
                                DeputadoCondecoracao.deputado_id == deputy.id,
                                DeputadoCondecoracao.cod_id == self._safe_int(cod_id),
                            )
                            .first()
                        )

                        if not existing:
                            decoration = DeputadoCondecoracao(
                                deputado_id=deputy.id,
                                cod_id=self._safe_int(cod_id),
                                cod_des=self._get_text_value(cond, "CodDes"),
                                cod_ordem=self._safe_int(
                                    self._get_text_value(cond, "CodOrdem")
                                ),
                            )
                            self._add_with_tracking(decoration)

            # Process Published Works (CadObrasPublicadas)
            obras = record.find("CadObrasPublicadas")
            if obras is not None:
                for obra in obras.findall("DadosObrasPublicadas"):
                    pub_id = self._get_text_value(obra, "PubId")
                    if pub_id:
                        existing = (
                            self.session.query(DeputadoObraPublicada)
                            .filter(
                                DeputadoObraPublicada.deputado_id == deputy.id,
                                DeputadoObraPublicada.pub_id == self._safe_int(pub_id),
                            )
                            .first()
                        )

                        if not existing:
                            publication = DeputadoObraPublicada(
                                deputado_id=deputy.id,
                                pub_id=self._safe_int(pub_id),
                                pub_des=self._get_text_value(obra, "PubDes"),
                                pub_ordem=self._safe_int(
                                    self._get_text_value(obra, "PubOrdem")
                                ),
                            )
                            self._add_with_tracking(publication)

            # Process Legislative Mandates (CadDeputadoLegis)
            # CRITICAL: Each mandate has its own leg_des and must be linked to the correct deputy
            # for that legislature, not the file-level deputy
            legislaturas = record.find("CadDeputadoLegis")
            if legislaturas is not None:
                for mandato in legislaturas.findall("DadosDeputadoLegis"):
                    leg_des = self._get_text_value(mandato, "LegDes")
                    ce_des = self._get_text_value(mandato, "CeDes")
                    nome_parlamentar = self._get_text_value(mandato, "DepNomeParlamentar")

                    if leg_des:
                        # Find the correct deputy for THIS mandate's legislature
                        # Each mandate belongs to a specific legislature and must link to the
                        # deputy record for that legislature, not the file-level deputy
                        try:
                            mandate_legislatura_sigla = self._extract_legislatura_from_xml_content(leg_des)
                            if mandate_legislatura_sigla:
                                mandate_legislatura = self._get_or_create_legislatura(mandate_legislatura_sigla)
                                mandate_legislatura_id = mandate_legislatura.id
                                logger.debug(f"Mandate leg_des '{leg_des}' resolved to legislature ID {mandate_legislatura_id}")
                            else:
                                # Fallback to file-level legislature (shouldn't happen if leg_des is valid)
                                mandate_legislatura_id = legislatura_id
                                logger.warning(f"Could not extract legislature from leg_des '{leg_des}', using file-level legislature")
                        except Exception as e:
                            logger.warning(f"Failed to extract legislature from mandate leg_des '{leg_des}': {e} - using file-level legislature")
                            mandate_legislatura_id = legislatura_id

                        # Find the correct deputy for this mandate's legislature
                        mandate_deputy = self._find_deputy_robust(
                            cad_id,
                            nome_completo=nome_completo,
                            nome_parlamentar=nome_parlamentar,
                            legislatura_id=mandate_legislatura_id,
                        )

                        existing = (
                            self.session.query(DeputadoMandatoLegislativo)
                            .filter(
                                DeputadoMandatoLegislativo.deputado_id == mandate_deputy.id,
                                DeputadoMandatoLegislativo.leg_des == leg_des,
                                DeputadoMandatoLegislativo.ce_des == ce_des,
                            )
                            .first()
                        )

                        if not existing:
                            # Extract party information
                            par_sigla = self._get_text_value(mandato, "ParSigla")
                            par_des = self._get_text_value(mandato, "ParDes")

                            # Log mandate creation details (debug level to avoid UI clutter)
                            logger.debug(f"[MANDATE_CREATE] Creating mandate for deputy {mandate_deputy.id} ({mandate_deputy.nome_completo})")
                            logger.debug(f"[MANDATE_CREATE]   - leg_des: '{leg_des}'")
                            logger.debug(f"[MANDATE_CREATE]   - mandate_deputy.legislatura_id: {mandate_deputy.legislatura_id}")
                            logger.debug(f"[MANDATE_CREATE]   - file_path: {self.file_info.get('file_path', 'unknown')}")

                            # Create base mandate record
                            mandate = DeputadoMandatoLegislativo(
                                deputado_id=mandate_deputy.id,
                                dep_nome_parlamentar=nome_parlamentar,
                                leg_des=leg_des,
                                ce_des=ce_des,
                                par_sigla=par_sigla,
                                par_des=par_des,
                                gp_sigla=self._get_text_value(mandato, "GpSigla"),
                                gp_des=self._get_text_value(mandato, "GpDes"),
                                ind_des=self._get_text_value(
                                    mandato, "IndDes"
                                ),  # VIII Legislature field
                                ind_data=self._parse_date(
                                    self._get_text_value(mandato, "IndData")
                                ),  # VIII Legislature field
                            )

                            # Update mandate with coalition context
                            if par_sigla:
                                self.update_mandate_coalition_context(mandate, par_sigla)

                            self._add_with_tracking(mandate)

            # Process Organ Activities (CadActividadeOrgaos)
            atividades_orgaos = record.find("CadActividadeOrgaos")
            if atividades_orgaos is not None:
                # Process all organ activity types using consolidated helper method
                organ_activity_types = [
                    ("actividadeCom", "committee"),
                    ("actividadeGT", "working_group"),
                    ("actividadeSCom", "subcommittee"),
                ]
                for xml_tag, activity_type in organ_activity_types:
                    for activity_element in atividades_orgaos.findall(xml_tag):
                        self._process_organ_activity(activity_element, deputy.id, activity_type)

            return True

        except Exception as e:
            # Extract legislature from file path to show correct legislature in error
            try:
                legislature_sigla = self._extract_legislatura(file_info.get("file_path", ""), None)
                error_msg = f"Error processing {legislature_sigla} Legislature biographical record: {e}"
            except:
                error_msg = f"Error processing biographical record: {e}"
            logger.error(error_msg)
            return False

    def _process_registo_interesses_v2(
        self, record: ET.Element, file_info: Dict
    ) -> bool:
        """Process Interest Registry V2 record"""
        try:
            # Safety check - ensure record is not None
            if record is None:
                logger.warning(
                    "Received None record in Interest Registry V2 processing"
                )
                return False

            from database.models import Deputado, RegistoInteressesUnified

            cad_id = self._get_text_value(record, "cadId")
            if not cad_id:
                return False

            cad_id = self._safe_int(cad_id)
            if cad_id is None:
                logger.warning("Invalid cadId format, skipping record")
                return False

            # Find or create the deputy using robust matching
            nome_completo = self._normalize_name(self._get_text_value(record, "cadNomeCompleto"))
            
            # Check if this interest registry record has a LegDes that overrides the file-level legislature
            record_leg_des = self._get_text_value(record, "LegDes")
            if record_leg_des:
                # Use record-specific legislature instead of file-level legislature
                try:
                    record_legislatura_sigla = self._extract_legislatura_from_xml_content(record_leg_des)
                    if record_legislatura_sigla:
                        record_legislatura = self._get_or_create_legislatura(record_legislatura_sigla)
                        legislatura_id = record_legislatura.id
                        logger.debug(f"LegDes '{record_leg_des}' in interest registry record overrode file-level legislature for deputy {nome_completo} (CadId: {cad_id}) - using legislature ID {legislatura_id}")
                    else:
                        # Fallback to file-level legislature
                        legislatura_id = self._get_legislatura_id(self.file_info)
                except Exception as e:
                    logger.warning(f"Failed to extract legislature from interest registry LegDes '{record_leg_des}' for deputy {nome_completo}: {e} - using file-level legislature")
                    legislatura_id = self._get_legislatura_id(self.file_info)
            else:
                # No LegDes in record, use file-level legislature
                legislatura_id = self._get_legislatura_id(self.file_info)
                
            deputy = self._find_deputy_robust(cad_id, nome_completo=nome_completo, legislatura_id=legislatura_id)

            # Check if already exists
            existing = (
                self.session.query(RegistoInteressesUnified)
                .filter(
                    RegistoInteressesUnified.deputado_id == deputy.id,
                    RegistoInteressesUnified.cad_id == cad_id,
                )
                .first()
            )

            if not existing:
                interest_registry = RegistoInteressesUnified(
                    deputado_id=deputy.id,
                    legislatura_id=legislatura_id,
                    cad_id=cad_id,
                    schema_version="V2",  # I Legislature uses V2 schema format
                    marital_status_code=self._get_text_value(
                        record, "cadEstadoCivilCod"
                    ),
                    full_name=self._get_text_value(
                        record, "cadNomeCompleto"
                    ),
                    professional_activity=self._get_text_value(
                        record, "cadActividadeProfissional"
                    ),
                    marital_status_desc=self._get_text_value(
                        record, "cadEstadoCivilDes"
                    ),
                )
                self._add_with_tracking(interest_registry)

                # Also update deputy's marital status
                deputy.estado_civil_cod = (
                    self._get_text_value(record, "cadEstadoCivilCod")
                    or deputy.estado_civil_cod
                )

            return True

        except Exception as e:
            logger.error(f"Error processing Interest Registry V2: {e}")
            return False





# REMOVED: _should_create_mandate method
# This was a band-aid fix for cross-legislature contamination that was actually caused by
# the Interest Registry mapper auto-creating bogus deputy records. Now that the root cause
# is fixed (Interest Registry fails instead of auto-creating), this filtering is unnecessary.
# Biographical data should be trusted as the authoritative source of deputy service periods.

    def _extract_legislature_from_path(self, file_path: str) -> str:
        """Extract legislature name from file path for accurate logging"""
        if not file_path:
            return "Unknown Legislature"

        import re

        # Try to match patterns like "V_Legislatura", "XIII_Legislatura", "RegistoBiograficoXIII.xml", etc.
        legislature_match = re.search(
            r"([IVX]+)_Legislatura|RegistoBiografico([IVX]+)\.xml|Legislatura_([IVX]+)",
            file_path,
            re.IGNORECASE,
        )

        if legislature_match:
            # Get the first non-None group
            legislature_roman = (
                legislature_match.group(1)
                or legislature_match.group(2)
                or legislature_match.group(3)
            )
            return f"{legislature_roman} Legislature"

        # Try to match patterns like "Constituinte"
        if re.search(r"Constituinte", file_path, re.IGNORECASE):
            return "Constituinte"

        return "Unknown Legislature"
