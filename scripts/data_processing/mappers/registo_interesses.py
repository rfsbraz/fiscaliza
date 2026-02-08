"""
Conflicts of Interest Registry Mapper
=====================================

Schema mapper for conflicts of interest files (RegistoInteresses*.xml).
Handles conflict of interest declarations including marital status, exclusivity, and spouse information.
"""

import logging
import os
import re
import uuid

# Import our models
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, Optional, Set

from .enhanced_base_mapper import EnhancedSchemaMapper, SchemaError

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from database.models import (
    Deputado,
    Legislatura,
    RegistoInteressesApoioUnified,
    RegistoInteressesAtividadeUnified,
    RegistoInteressesFactoDeclaracao,
    RegistoInteressesSocialPositionUnified,
    RegistoInteressesSociedadeUnified,
    RegistoInteressesUnified,
)

logger = logging.getLogger(__name__)


class RegistoInteressesMapper(EnhancedSchemaMapper):
    """Schema mapper for conflicts of interest registry files"""

    def __init__(self, session, import_status_record=None):
        # Accept SQLAlchemy session directly (passed by unified importer)
        super().__init__(session, import_status_record=import_status_record)

    def get_expected_fields(self) -> Set[str]:
        return {
            # Root elements
            "ArrayOfRegistoInteresses",
            "ArrayOfRegistoInteresses.RegistoInteresses",
            # V3 Schema (newer format)
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordId",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.FullName",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.MaritalStatus",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.SpouseName",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.MatrimonialRegime",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.Exclusivity",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.DGFNumber",
            # V3 RecordInterests structure (XIV Legislature)
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.RecordId",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.PositionBeginDate",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.PositionEndDate",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.PositionDesignation",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.ServicesProvided",
            # V3 Activities structure
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.Activities",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.Activities.RecordInterestActivityResponse",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.Activities.RecordInterestActivityResponse.Type",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.Activities.RecordInterestActivityResponse.Entity",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.Activities.RecordInterestActivityResponse.BeginDate",
            # V3 Societies structure
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.Societies",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.Societies.RecordInterestSocietyResponse",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.Societies.RecordInterestSocietyResponse.Entity",
            # V3 Social Positions structure
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.SocialPositions",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.SocialPositions.RecordInterestSocialPositionResponse",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.SocialPositions.RecordInterestSocialPositionResponse.Type",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.SocialPositions.RecordInterestSocialPositionResponse.Position",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.SocialPositions.RecordInterestSocialPositionResponse.Entity",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.SocialPositions.RecordInterestSocialPositionResponse.ActivityArea",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.SocialPositions.RecordInterestSocialPositionResponse.HeadOfficeLocation",
            # V3 Services Provided structure
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.ServicesProvided.RecordInterestServiceProvidedResponse",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.ServicesProvided.RecordInterestServiceProvidedResponse.Service",
            # V2 Schema (XII, XIII) - Basic fields
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadId",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadNomeCompleto",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadActividadeProfissional",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadEstadoCivilCod",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadEstadoCivilDes",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadFamId",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadNomeConjuge",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi",
            # V2 Schema - Detailed nested structure (XIII Legislature)
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiId",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiCargoDes",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiLegDes",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiDataVersao",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiRegimeBensId",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiRegimeBensDes",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiCargoData",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiApoiosBeneficios",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiServicosPrestados",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiCadId",
            # Activities
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiActividades",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiActividades.pt_ar_wsgode_objectos_DadosRgiActividades",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiActividades.pt_ar_wsgode_objectos_DadosRgiActividades.rgaId",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiActividades.pt_ar_wsgode_objectos_DadosRgiActividades.rgaActividade",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiActividades.pt_ar_wsgode_objectos_DadosRgiActividades.rgaDataInicio",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiActividades.pt_ar_wsgode_objectos_DadosRgiActividades.rgaDataFim",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiActividades.pt_ar_wsgode_objectos_DadosRgiActividades.rgaRemunerada",
            # Societies
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiSociedades",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiSociedades.pt_ar_wsgode_objectos_DadosRgiSociedades",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiSociedades.pt_ar_wsgode_objectos_DadosRgiSociedades.rgsId",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiSociedades.pt_ar_wsgode_objectos_DadosRgiSociedades.rgsEntidade",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiSociedades.pt_ar_wsgode_objectos_DadosRgiSociedades.rgsAreaActividade",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiSociedades.pt_ar_wsgode_objectos_DadosRgiSociedades.rgsLocalSede",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiSociedades.pt_ar_wsgode_objectos_DadosRgiSociedades.rgsPartiSocial",
            # Social Positions
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiCargosSociais",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiCargosSociais.pt_ar_wsgode_objectos_DadosRgiCargosSociaisV2",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiCargosSociais.pt_ar_wsgode_objectos_DadosRgiCargosSociaisV2.rgcId",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiCargosSociais.pt_ar_wsgode_objectos_DadosRgiCargosSociaisV2.rgcCargo",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiCargosSociais.pt_ar_wsgode_objectos_DadosRgiCargosSociaisV2.rgcEntidade",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiCargosSociais.pt_ar_wsgode_objectos_DadosRgiCargosSociaisV2.rgcAreaActividade",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiCargosSociais.pt_ar_wsgode_objectos_DadosRgiCargosSociaisV2.rgcLocalSede",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiCargosSociais.pt_ar_wsgode_objectos_DadosRgiCargosSociaisV2.rgcDataInicio",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiCargosSociais.pt_ar_wsgode_objectos_DadosRgiCargosSociaisV2.rgcDataFim",
            # Other Situations - this appears to be a text field, not a nested structure
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV2.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2.rgiOutrasSituacoes",
            # V1 Schema (XI)
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadId",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadNomeCompleto",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadActividadeProfissional",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadEstadoCivilCod",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadEstadoCivilDes",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadFamId",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadNomeConjuge",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi",
            # V5 Schema (XV Legislature) - Complex structure with tempuri namespace
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}Categoria",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}Exclusividade",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}Exclusividade.{http://tempuri.org/}Id",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}Exclusividade.{http://tempuri.org/}Designacao",
            # Personal Data (GenDadosPessoais) - XIV Legislature
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenDadosPessoais",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenDadosPessoais.{http://tempuri.org/}Sexo",
            # Declaration Facts
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}FactoDeclaracao",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}FactoDeclaracao.{http://tempuri.org/}ChkDeclaracao",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}FactoDeclaracao.{http://tempuri.org/}CargoFuncao",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}FactoDeclaracao.{http://tempuri.org/}TxtDeclaracao",
            # Support/Benefits (GenApoios)
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenApoios",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenApoios.{http://tempuri.org/}GenApoio",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenApoios.{http://tempuri.org/}GenApoio.{http://tempuri.org/}Apoio",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenApoios.{http://tempuri.org/}GenApoio.{http://tempuri.org/}Entidade",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenApoios.{http://tempuri.org/}GenApoio.{http://tempuri.org/}NaturezaArea",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenApoios.{http://tempuri.org/}GenApoio.{http://tempuri.org/}Descricao",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenApoios.{http://tempuri.org/}GenApoio.{http://tempuri.org/}Valor",
            # Positions Less Than 3 Years
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenCargosMenosTresAnos",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenCargosMenosTresAnos.{http://tempuri.org/}GenCargo",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenCargosMenosTresAnos.{http://tempuri.org/}GenCargo.{http://tempuri.org/}Entidade",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenCargosMenosTresAnos.{http://tempuri.org/}GenCargo.{http://tempuri.org/}NaturezaArea",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenCargosMenosTresAnos.{http://tempuri.org/}GenCargo.{http://tempuri.org/}Cargo",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenCargosMenosTresAnos.{http://tempuri.org/}GenCargo.{http://tempuri.org/}DataInicio",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenCargosMenosTresAnos.{http://tempuri.org/}GenCargo.{http://tempuri.org/}DataFim",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenCargosMenosTresAnos.{http://tempuri.org/}GenCargo.{http://tempuri.org/}Remuneracao",
            # Positions More Than 3 Years
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenCargosMaisTresAnos",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenCargosMaisTresAnos.{http://tempuri.org/}GenCargo",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenCargosMaisTresAnos.{http://tempuri.org/}GenCargo.{http://tempuri.org/}Entidade",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenCargosMaisTresAnos.{http://tempuri.org/}GenCargo.{http://tempuri.org/}NaturezaArea",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenCargosMaisTresAnos.{http://tempuri.org/}GenCargo.{http://tempuri.org/}Cargo",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenCargosMaisTresAnos.{http://tempuri.org/}GenCargo.{http://tempuri.org/}DataInicio",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenCargosMaisTresAnos.{http://tempuri.org/}GenCargo.{http://tempuri.org/}DataFim",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenCargosMaisTresAnos.{http://tempuri.org/}GenCargo.{http://tempuri.org/}Remuneracao",
            # Services Provided
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenServicoPrestado",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenServicoPrestado.{http://tempuri.org/}GenServicoPrestado",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenServicoPrestado.{http://tempuri.org/}GenServicoPrestado.{http://tempuri.org/}Entidade",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenServicoPrestado.{http://tempuri.org/}GenServicoPrestado.{http://tempuri.org/}NaturezaArea",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenServicoPrestado.{http://tempuri.org/}GenServicoPrestado.{http://tempuri.org/}Natureza",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenServicoPrestado.{http://tempuri.org/}GenServicoPrestado.{http://tempuri.org/}Descricao",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenServicoPrestado.{http://tempuri.org/}GenServicoPrestado.{http://tempuri.org/}Valor",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenServicoPrestado.{http://tempuri.org/}GenServicoPrestado.{http://tempuri.org/}Local",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenServicoPrestado.{http://tempuri.org/}GenServicoPrestado.{http://tempuri.org/}DataInicio",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenServicoPrestado.{http://tempuri.org/}GenServicoPrestado.{http://tempuri.org/}DataFim",
            # Societies/Companies
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenSociedade",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenSociedade.{http://tempuri.org/}GenSociedade",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenSociedade.{http://tempuri.org/}GenSociedade.{http://tempuri.org/}Sociedade",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenSociedade.{http://tempuri.org/}GenSociedade.{http://tempuri.org/}NaturezaArea",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenSociedade.{http://tempuri.org/}GenSociedade.{http://tempuri.org/}ParticipacaoSocial",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenSociedade.{http://tempuri.org/}GenSociedade.{http://tempuri.org/}Participacao",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenSociedade.{http://tempuri.org/}GenSociedade.{http://tempuri.org/}Valor",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenSociedade.{http://tempuri.org/}GenSociedade.{http://tempuri.org/}Observacoes",
            # Professional Activities
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenAtivProfissional",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenAtivProfissional.{http://tempuri.org/}GenAtivProfissional",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenAtivProfissional.{http://tempuri.org/}GenAtivProfissional.{http://tempuri.org/}Atividade",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenAtivProfissional.{http://tempuri.org/}GenAtivProfissional.{http://tempuri.org/}Entidade",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenAtivProfissional.{http://tempuri.org/}GenAtivProfissional.{http://tempuri.org/}NaturezaArea",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenAtivProfissional.{http://tempuri.org/}GenAtivProfissional.{http://tempuri.org/}DataInicio",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenAtivProfissional.{http://tempuri.org/}GenAtivProfissional.{http://tempuri.org/}DataFim",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenAtivProfissional.{http://tempuri.org/}GenAtivProfissional.{http://tempuri.org/}Remuneracao",
            # Additional V5 fields that may appear
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenImoveis",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenImoveis.{http://tempuri.org/}GenImovel",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenInvestimentos",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenInvestimentos.{http://tempuri.org/}GenInvestimento",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenDividas",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenDividas.{http://tempuri.org/}GenDivida",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenPatrimonio",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenPatrimonio.{http://tempuri.org/}GenBem",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenFamiliar",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenFamiliar.{http://tempuri.org/}GenFamiliar",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenEstadoCivil",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenEstadoCivil.{http://tempuri.org/}Id",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenEstadoCivil.{http://tempuri.org/}Designacao",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenRegimeBens",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenRegimeBens.{http://tempuri.org/}Id",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenRegimeBens.{http://tempuri.org/}Designacao",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenConjuge",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenConjuge.{http://tempuri.org/}Nome",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenConjuge.{http://tempuri.org/}Profissao",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenMembrosGoverno",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenMembrosGoverno.{http://tempuri.org/}GenMembro",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenOutrasDeclaracoes",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenOutrasDeclaracoes.{http://tempuri.org/}GenDeclaracao",
            # Missing fields from XV Legislature test (exact patterns from unmapped fields error)
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenCargosMaisTresAnos.{http://tempuri.org/}GenCargo.{http://tempuri.org/}Remunerada",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenServicoPrestado.{http://tempuri.org/}GenServicoPrestado.{http://tempuri.org/}Id",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}FactoDeclaracao.{http://tempuri.org/}DataAlteracaoFuncao",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}Exclusividade.{http://tempuri.org/}Exclusividade",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenSociedade.{http://tempuri.org/}GenSociedade.{http://tempuri.org/}FormularioId",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}Legislatura",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}FactoDeclaracao.{http://tempuri.org/}Id",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}versao",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenCargosMenosTresAnos.{http://tempuri.org/}GenCargo.{http://tempuri.org/}FormularioId",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenOutraSituacao.{http://tempuri.org/}GenOutraSituacao.{http://tempuri.org/}OutraSituacao",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenCargosMaisTresAnos.{http://tempuri.org/}GenCargo.{http://tempuri.org/}Natureza",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenServicoPrestado.{http://tempuri.org/}GenServicoPrestado.{http://tempuri.org/}Servico",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenCargosMenosTresAnos.{http://tempuri.org/}GenCargo.{http://tempuri.org/}Natureza",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenCargosMaisTresAnos.{http://tempuri.org/}GenCargo.{http://tempuri.org/}FormularioId",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenAtivProfissional.{http://tempuri.org/}GenAtivProfissional.{http://tempuri.org/}FormularioId",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenOutraSituacao",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenOutraSituacao.{http://tempuri.org/}GenOutraSituacao",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenCargosMenosTresAnos.{http://tempuri.org/}GenCargo.{http://tempuri.org/}Remunerada",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenAtivProfissional.{http://tempuri.org/}GenAtivProfissional.{http://tempuri.org/}Id",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenServicoPrestado.{http://tempuri.org/}GenServicoPrestado.{http://tempuri.org/}FormularioId",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenCargosMaisTresAnos.{http://tempuri.org/}GenCargo.{http://tempuri.org/}Id",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenOutraSituacao.{http://tempuri.org/}GenOutraSituacao.{http://tempuri.org/}FormularioId",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenCargosMenosTresAnos.{http://tempuri.org/}GenCargo.{http://tempuri.org/}Id",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenAtivProfissional.{http://tempuri.org/}GenAtivProfissional.{http://tempuri.org/}Natureza",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenSociedade.{http://tempuri.org/}GenSociedade.{http://tempuri.org/}Id",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenOutraSituacao.{http://tempuri.org/}GenOutraSituacao.{http://tempuri.org/}Id",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenApoios.{http://tempuri.org/}GenApoio.{http://tempuri.org/}FormularioId",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenApoios.{http://tempuri.org/}GenApoio.{http://tempuri.org/}Id",
            # Additional missing V1 and V3 fields from the error logs (need these for comprehensive coverage)
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb.rgiCargosSociais.pt_ar_wsgode_objectos_DadosRgiCargosSociais.rgcId",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb.rgiCargosSociais.pt_ar_wsgode_objectos_DadosRgiCargosSociais.rgcAreaActividade",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb.rgiOutrasSituacoes",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb.rgiCargosSociais.pt_ar_wsgode_objectos_DadosRgiCargosSociais.rgcCargo",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb.rgiSociedades.pt_ar_wsgode_objectos_DadosRgiSociedades.rgsPartiSocial",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb.rgiSociedades.pt_ar_wsgode_objectos_DadosRgiSociedades.rgsAreaActividade",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb.rgiSociedades.pt_ar_wsgode_objectos_DadosRgiSociedades.rgsId",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb.rgiSociedades",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb.rgiCargoDes",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb.rgiCargosSociais.pt_ar_wsgode_objectos_DadosRgiCargosSociais.rgcLocalSede",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb.rgiCargosSociais",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb.rgiCargosSociais.pt_ar_wsgode_objectos_DadosRgiCargosSociais",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb.rgiCargosSociais.pt_ar_wsgode_objectos_DadosRgiCargosSociais.rgcEntidade",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb.rgiCargosSociais.pt_ar_wsgode_objectos_DadosRgiCargosSociais.rgcDataInicio",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb.rgiCargosSociais.pt_ar_wsgode_objectos_DadosRgiCargosSociais.rgcDataFim",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb.rgiSociedades.pt_ar_wsgode_objectos_DadosRgiSociedades.rgsEntidade",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb.rgiSociedades.pt_ar_wsgode_objectos_DadosRgiSociedades.rgsLocalSede",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb.rgiActividades",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb.rgiActividades.pt_ar_wsgode_objectos_DadosRgiActividades",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb.rgiActividades.pt_ar_wsgode_objectos_DadosRgiActividades.rgaId",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb.rgiActividades.pt_ar_wsgode_objectos_DadosRgiActividades.rgaActividade",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb.rgiActividades.pt_ar_wsgode_objectos_DadosRgiActividades.rgaDataInicio",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb.rgiActividades.pt_ar_wsgode_objectos_DadosRgiActividades.rgaDataFim",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb.rgiActividades.pt_ar_wsgode_objectos_DadosRgiActividades.rgaRemunerada",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb",
            # Additional missing V1 fields from XI Legislature
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb.rgiSociedades.pt_ar_wsgode_objectos_DadosRgiSociedades",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb.rgiApoiosBeneficios",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb.rgiCargoData",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb.rgiId",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb.rgiCadId",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb.rgiDataVersao",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb.rgiLegDes",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV1.cadRgi.pt_ar_wsgode_objectos_DadosRegistoInteressesWeb.rgiServicosPrestados",
            # Additional missing V3 fields from error logs
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.Societies.RecordInterestSocietyResponse.ActivityArea",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.PositionChangedDate",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.OtherSituations",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.OtherSituations.RecordInterestOtherSituationResponse.Situation",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.Societies",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.Societies.RecordInterestSocietyResponse",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.OtherSituations.RecordInterestOtherSituationResponse",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.Supports.RecordInterestSupportResponse.Support",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.Societies.RecordInterestSocietyResponse.HeadOfficeLocation",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.Supports.RecordInterestSupportResponse",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.Activities.RecordInterestActivityResponse.Activity",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.Supports",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.Activities",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.Activities.RecordInterestActivityResponse",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.Activities.RecordInterestActivityResponse.ActivityArea",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.Activities.RecordInterestActivityResponse.StartDate",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.Activities.RecordInterestActivityResponse.EndDate",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.Activities.RecordInterestActivityResponse.Paid",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.Societies.RecordInterestSocietyResponse.Society",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.Societies.RecordInterestSocietyResponse.SocialParticipation",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.Supports.RecordInterestSupportResponse.SupportArea",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV3.RecordInterests.RecordInterestResponse.Supports.RecordInterestSupportResponse.Value",
            # Additional missing V5 XIV and XV Legislature fields from latest error
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenDadosPessoais.{http://tempuri.org/}RegimeBens",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenServicoPrestado.{http://tempuri.org/}GenServicoPrestado.{http://tempuri.org/}Data",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenIncompatibilidade.{http://tempuri.org/}Id",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenCargosMenosTresAnos.{http://tempuri.org/}GenCargo.{http://tempuri.org/}CargoFuncaoAtividade",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}FactoDeclaracao.{http://tempuri.org/}DataCessacaoFuncao",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenApoios.{http://tempuri.org/}GenApoio.{http://tempuri.org/}NaturezaBeneficio",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenDadosPessoais",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenDadosPessoais.{http://tempuri.org/}EstadoCivil",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenDadosPessoais.{http://tempuri.org/}NomeConjuge",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenIncompatibilidade",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenIncompatibilidade.{http://tempuri.org/}Incompatibilidade",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenCargosMaisTresAnos.{http://tempuri.org/}GenCargo.{http://tempuri.org/}CargoFuncaoAtividade",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenAtivProfissional.{http://tempuri.org/}GenAtivProfissional.{http://tempuri.org/}CargoFuncaoAtividade",
            # Final missing fields for XV Legislature V5 schema coverage
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenDadosPessoais.{http://tempuri.org/}Id",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenApoios.{http://tempuri.org/}GenApoio.{http://tempuri.org/}Data",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}FactoDeclaracao.{http://tempuri.org/}DataInicioFuncao",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenCargosMaisTresAnos.{http://tempuri.org/}GenCargo.{http://tempuri.org/}LocalSede",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenCargosMaisTresAnos.{http://tempuri.org/}GenCargo.{http://tempuri.org/}DataTermo",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}NomeIdentificacao",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenDadosPessoais.{http://tempuri.org/}NomeCompleto",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}IdCadastroGODE",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenSociedade.{http://tempuri.org/}GenSociedade.{http://tempuri.org/}Natureza",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}Servico",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenCargosMenosTresAnos.{http://tempuri.org/}GenCargo.{http://tempuri.org/}LocalSede",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenCargosMenosTresAnos.{http://tempuri.org/}GenCargo.{http://tempuri.org/}DataTermo",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenAtivProfissional.{http://tempuri.org/}GenAtivProfissional.{http://tempuri.org/}LocalSede",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenAtivProfissional.{http://tempuri.org/}GenAtivProfissional.{http://tempuri.org/}DataTermo",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenServicoPrestado.{http://tempuri.org/}GenServicoPrestado.{http://tempuri.org/}LocalSede",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenServicoPrestado.{http://tempuri.org/}GenServicoPrestado.{http://tempuri.org/}DataTermo",
            "ArrayOfRegistoInteresses.RegistoInteresses.RegistoInteressesV5.{http://tempuri.org/}GenSociedade.{http://tempuri.org/}GenSociedade.{http://tempuri.org/}LocalSede",
        }

    def validate_and_map(
        self, xml_root: ET.Element, file_info: Dict, strict_mode: bool = False
    ) -> Dict:
        """Validate and map conflicts of interest XML to database"""
        results = {"records_processed": 0, "records_imported": 0, "errors": []}

        # Store file_info for use in other methods
        self.file_info = file_info

        try:
            # Extract legislatura from file path
            legislatura_sigla = self._extract_legislatura(
                file_info["file_path"], xml_root
            )
            if not legislatura_sigla:
                error_msg = f"Could not extract legislatura from file path: {file_info['file_path']}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
                return results

            # Get or create legislatura
            legislatura = self._get_or_create_legislatura(legislatura_sigla)

            # Validate schema coverage according to strict mode
            self.validate_schema_coverage(xml_root, file_info, strict_mode)

            # Process each RegistoInteresses record
            for registo in xml_root.findall(".//RegistoInteresses"):
                # Try different schema versions (newest first)
                registo_v5 = registo.find("RegistoInteressesV5")
                registo_v3 = registo.find("RegistoInteressesV3")
                registo_v2 = registo.find("RegistoInteressesV2")
                registo_v1 = registo.find("RegistoInteressesV1")

                if registo_v5 is not None:
                    # Handle V5 schema (XV Legislature - newest format with comprehensive processing)
                    try:
                        success = self._process_v5_record(registo_v5, legislatura)
                        results["records_processed"] += 1
                        if success:
                            results["records_imported"] += 1

                    except Exception as e:
                        error_msg = f"Error processing V5 conflicts record: {str(e)}"
                        logger.error(error_msg)
                        # FAIL FAST: Let database schema errors bubble up immediately
                        # No rollback recovery to mask underlying issues
                        raise SchemaError(f"V5 conflicts record processing failed - stopping importer: {e}") from e

                elif registo_v3 is not None:
                    # Handle V3 schema (newer format)
                    try:
                        record_id = self._get_text(registo_v3, "RecordId")
                        full_name = self._get_text(registo_v3, "FullName")
                        marital_status = self._get_text(registo_v3, "MaritalStatus")
                        spouse_name = self._get_text(registo_v3, "SpouseName")
                        matrimonial_regime = self._get_text(
                            registo_v3, "MatrimonialRegime"
                        )
                        exclusivity = self._get_text(registo_v3, "Exclusivity")
                        dgf_number = self._get_text(registo_v3, "DGFNumber")

                        success = self._process_v3_record(
                            registo_v3,
                            record_id,
                            full_name,
                            marital_status,
                            spouse_name,
                            matrimonial_regime,
                            exclusivity,
                            dgf_number,
                            legislatura,
                        )
                        if success:
                            results["records_imported"] += 1

                    except Exception as e:
                        error_msg = f"Error processing V3 conflicts record: {str(e)}"
                        logger.error(error_msg)
                        # FAIL FAST: Let database schema errors bubble up immediately
                        # No rollback recovery to mask underlying issues
                        raise SchemaError(f"V3 conflicts record processing failed - stopping importer: {e}") from e

                elif registo_v2 is not None:
                    # Handle V2 schema (XII, XIII)
                    try:
                        record_id = self._get_text(registo_v2, "cadId")
                        full_name = self._get_text(registo_v2, "cadNomeCompleto")
                        marital_status_desc = self._get_text(
                            registo_v2, "cadEstadoCivilDes"
                        )
                        spouse_name = self._get_text(registo_v2, "cadNomeConjuge")

                        # V2 doesn't have direct exclusivity/dgf fields, but we can extract from nested rgi data
                        matrimonial_regime = None
                        exclusivity = None
                        dgf_number = None

                        # Try to extract from nested rgi data if available
                        rgi = registo_v2.find(
                            "cadRgi/pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2"
                        )
                        if rgi is not None:
                            matrimonial_regime = self._get_text(rgi, "rgiRegimeBensDes")

                        success = self._process_v2_record(
                            record_id,
                            full_name,
                            marital_status_desc,
                            spouse_name,
                            matrimonial_regime,
                            exclusivity,
                            dgf_number,
                            legislatura,
                            registo_v2,
                        )
                        if success:
                            results["records_imported"] += 1

                    except Exception as e:
                        error_msg = f"Error processing V2 conflicts record: {str(e)}"
                        logger.error(error_msg)
                        # FAIL FAST: Let database schema errors bubble up immediately
                        # No rollback recovery to mask underlying issues
                        raise SchemaError(f"V2 conflicts record processing failed - stopping importer: {e}") from e

                elif registo_v1 is not None:
                    # Handle V1 schema (XI)
                    try:
                        record_id = self._get_text(registo_v1, "cadId")
                        full_name = self._get_text(registo_v1, "cadNomeCompleto")
                        marital_status_desc = self._get_text(
                            registo_v1, "cadEstadoCivilDes"
                        )
                        spouse_name = self._get_text(registo_v1, "cadNomeConjuge")

                        # V1 doesn't have direct exclusivity/dgf fields
                        matrimonial_regime = None
                        exclusivity = None
                        dgf_number = None

                        success = self._process_v1_record(
                            registo_v1,
                            record_id,
                            full_name,
                            marital_status_desc,
                            spouse_name,
                            matrimonial_regime,
                            exclusivity,
                            dgf_number,
                            legislatura,
                        )
                        if success:
                            results["records_imported"] += 1

                    except Exception as e:
                        error_msg = f"Error processing V1 conflicts record: {str(e)}"
                        logger.error(error_msg)
                        # FAIL FAST: Let database schema errors bubble up immediately
                        # No rollback recovery to mask underlying issues
                        raise SchemaError(f"V1 conflicts record processing failed - stopping importer: {e}") from e

            # Commit all changes
            logger.info(
                f"Imported {results['records_imported']} conflicts of interest records from {file_info['file_path']}"
            )

        except Exception as e:
            error_msg = f"Critical error processing conflicts file {file_info['file_path']}: {str(e)}"
            logger.error(error_msg)
            # FAIL FAST: Let database schema errors bubble up immediately
            # No rollback recovery to mask underlying issues
            raise SchemaError(f"Critical interest registry processing error: {e}") from e

        return results

    def _get_text(self, parent: ET.Element, tag: str) -> Optional[str]:
        """Get text content from child element, return None if not found"""
        element = parent.find(tag)
        if element is not None and element.text:
            return element.text.strip()
        return None

    # Legislatura and roman numeral methods now inherited from base class

    # _get_or_create_deputado method now inherited from enhanced base mapper

    def _get_or_create_deputy_by_cadastro(
        self, record_id: str, full_name: str, legislatura: Legislatura
    ) -> Deputado:
        """
        Get or create deputy by cadastral ID.

        With on-the-fly file processing, files can arrive in any order. Deputies are created
        from whichever source arrives first (Biographical Registry, Interest Registry, etc.)
        and enriched by subsequent imports.

        Args:
            record_id: XML RecordId to use as cadastral ID
            full_name: Deputy's full name
            legislatura: Legislature context

        Returns:
            Deputado: Existing or newly created deputy record

        Raises:
            ValueError: If record_id is not numeric or missing required data
        """
        # Validate cadastral ID
        id_cadastro = self._safe_int(record_id)
        if id_cadastro is None:
            raise ValueError(
                f"Record ID must be numeric: '{record_id}'. Data integrity violation - cannot use non-numeric cadastral ID"
            )

        # Find existing deputy by id_cadastro + legislature combination
        deputado = (
            self.session.query(Deputado)
            .filter_by(id_cadastro=id_cadastro, legislatura_id=legislatura.id)
            .first()
        )

        if not deputado:
            # Create deputy with basic info - will be enriched by Biographical Registry later
            deputado = Deputado(
                id_cadastro=id_cadastro,
                nome=full_name or f"Deputy {id_cadastro}",
                nome_completo=full_name,
                legislatura_id=legislatura.id,
            )
            self._add_with_tracking(deputado)
            self.session.flush()  # Get ID for relationships
            logger.debug(f"Created deputy {id_cadastro} ({full_name}) in legislature {legislatura.numero} from Interest Registry")
        else:
            # Update existing deputy with any new information
            if full_name and deputado.nome != full_name:
                deputado.nome = full_name
            if full_name and not deputado.nome_completo:
                deputado.nome_completo = full_name

        return deputado

    def _process_v3_record(
        self,
        registo_v3_elem: ET.Element,
        record_id: str,
        full_name: str,
        marital_status: str,
        spouse_name: str,
        matrimonial_regime: str,
        exclusivity: str,
        dgf_number: str,
        legislatura: Legislatura,
    ) -> bool:
        """Process V3 schema record with RecordInterests structure"""
        try:
            if not record_id or not full_name:
                logger.debug(
                    "Missing record_id or full_name in V3 record - importing with available data"
                )
                # Both record_id and full_name are required for data integrity
                if not record_id or not full_name:
                    raise ValueError(
                        f"Missing required fields: record_id='{record_id}', full_name='{full_name}'. Data integrity violation - cannot generate artificial data"
                    )

            # FIXED: Use centralized deputy creation logic
            deputado = self._get_or_create_deputy_by_cadastro(
                record_id, full_name, legislatura
            )

            # Check if record already exists in unified model by deputado_id + legislatura_id
            existing = (
                self.session.query(RegistoInteressesUnified)
                .filter_by(deputado_id=deputado.id, legislatura_id=legislatura.id)
                .first()
            )

            if existing:
                # Update existing record
                existing.full_name = full_name
                existing.marital_status_desc = marital_status
                existing.spouse_name = spouse_name
                existing.matrimonial_regime = matrimonial_regime
                existing.exclusivity = exclusivity
                existing.dgf_number = dgf_number
                existing.schema_version = "V3"
                registo = existing
            else:
                # Create new record
                registo = RegistoInteressesUnified(
                    id=uuid.uuid4(),
                    deputado_id=deputado.id,
                    legislatura_id=legislatura.id,
                    full_name=full_name,
                    marital_status_desc=marital_status,
                    spouse_name=spouse_name,
                    matrimonial_regime=matrimonial_regime,
                    exclusivity=exclusivity,
                    dgf_number=dgf_number,
                    schema_version="V3",
                )
                self._add_with_tracking(registo)

            # Process V3 RecordInterests structure
            record_interests = registo_v3_elem.find("RecordInterests")
            if record_interests is not None:
                for record_response in record_interests.findall(
                    "RecordInterestResponse"
                ):
                    self._process_v3_record_interests(
                        record_response, registo, deputado
                    )

            return True

        except ValueError as e:
            # Expected when deputy doesn't exist yet (Biographical Registry not processed)
            logger.warning(f"Skipping V3 record: {e}")
            return False
        except Exception as e:
            logger.error(f"Error processing V3 record: {e}")
            return False

    def _process_v3_record_interests(
        self,
        record_response: ET.Element,
        registo: "RegistoInteressesUnified",
        deputado: "Deputado",
    ):
        """Process V3 RecordInterestResponse structure with Activities, SocialPositions, Societies, ServicesProvided"""
        try:
            # Extract and use only the fields we actually need
            position_begin_date = self._parse_date(
                self._get_text(record_response, "PositionBeginDate")
            )
            position_end_date = self._parse_date(
                self._get_text(record_response, "PositionEndDate")
            )

            # Update unified record with position dates
            if position_begin_date:
                registo.position_begin_date = position_begin_date
            if position_end_date:
                registo.position_end_date = position_end_date

            # Process Activities
            activities = record_response.find("Activities")
            if activities is not None:
                for activity_response in activities.findall(
                    "RecordInterestActivityResponse"
                ):
                    self._process_v3_activity(activity_response, registo, deputado)

            # Process SocialPositions
            social_positions = record_response.find("SocialPositions")
            if social_positions is not None:
                for social_position_response in social_positions.findall(
                    "RecordInterestSocialPositionResponse"
                ):
                    self._process_v3_social_position(
                        social_position_response, registo, deputado
                    )

            # Process Societies
            societies = record_response.find("Societies")
            if societies is not None:
                for society_response in societies.findall(
                    "RecordInterestSocietyResponse"
                ):
                    self._process_v3_society(society_response, registo, deputado)

            # Process ServicesProvided/Supports
            supports = record_response.find("Supports")
            if supports is not None:
                for support_response in supports.findall(
                    "RecordInterestSupportResponse"
                ):
                    self._process_v3_support(support_response, registo, deputado)

            # Process OtherSituations
            other_situations = record_response.find("OtherSituations")
            if other_situations is not None:
                for other_situation_response in other_situations.findall(
                    "RecordInterestOtherSituationResponse"
                ):
                    situation = self._get_text(other_situation_response, "Situation")
                    logger.debug(f"Processing other situation: {situation}")

        except Exception as e:
            logger.error(f"Error processing V3 RecordInterests: {e}")

    def _process_v3_activity(
        self,
        activity_response: ET.Element,
        registo: "RegistoInteressesUnified",
        deputado: "Deputado",
    ):
        """Process V3 RecordInterestActivityResponse"""
        try:
            activity = self._get_text(activity_response, "Activity")
            activity_area = self._get_text(activity_response, "ActivityArea")
            start_date = self._parse_date(
                self._get_text(activity_response, "StartDate")
            )
            end_date = self._parse_date(self._get_text(activity_response, "EndDate"))
            paid_text = self._get_text(activity_response, "Paid")
            paid = (
                paid_text.lower() in ["true", "sim", "yes", "1"] if paid_text else None
            )

            # Create activity record in unified model
            activity_record = RegistoInteressesAtividadeUnified(
                registo_id=registo.id,
                description=activity,
                type_classification=activity_area,
                start_date=start_date,
                end_date=end_date,
                remunerated=paid,
            )
            self._add_with_tracking(activity_record)

        except Exception as e:
            logger.error(f"Error processing V3 activity: {e}")

    def _process_v3_social_position(
        self,
        social_position_response: ET.Element,
        registo: "RegistoInteressesUnified",
        deputado: "Deputado",
    ):
        """Process V3 RecordInterestSocialPositionResponse"""
        try:
            position_text = self._get_text(
                social_position_response, "Position"
            )  # Assuming this field exists
            type_classification = self._get_text(social_position_response, "Type")
            headquarters_location = self._get_text(
                social_position_response, "HeadOfficeLocation"
            )

            # Create social position record in unified model
            social_position_record = RegistoInteressesSocialPositionUnified(
                registo_id=registo.id,
                position=position_text,
                type_classification=type_classification,
                headquarters_location=headquarters_location,
            )
            self._add_with_tracking(social_position_record)

        except Exception as e:
            logger.error(f"Error processing V3 social position: {e}")

    def _process_v3_society(
        self,
        society_response: ET.Element,
        registo: "RegistoInteressesUnified",
        deputado: "Deputado",
    ):
        """Process V3 RecordInterestSocietyResponse"""
        try:
            society = self._get_text(society_response, "Society")
            entity = self._get_text(society_response, "Entity")
            activity_area = self._get_text(society_response, "ActivityArea")
            head_office_location = self._get_text(
                society_response, "HeadOfficeLocation"
            )
            social_participation = self._get_text(
                society_response, "SocialParticipation"
            )

            # Create society record in unified model
            society_record = RegistoInteressesSociedadeUnified(
                registo_id=registo.id,
                entity=entity
                or society,  # Use entity if available, fallback to society
                social_participation=social_participation,
                activity_area=activity_area,
                headquarters=head_office_location,
            )
            self._add_with_tracking(society_record)

        except Exception as e:
            logger.error(f"Error processing V3 society: {e}")

    def _process_v3_support(
        self,
        support_response: ET.Element,
        registo: "RegistoInteressesUnified",
        deputado: "Deputado",
    ):
        """Process V3 RecordInterestSupportResponse (ServicesProvided)"""
        try:
            support = self._get_text(support_response, "Support")
            support_area = self._get_text(support_response, "SupportArea")
            value = self._get_text(support_response, "Value")

            # Create support/service record in unified model
            support_record = RegistoInteressesApoioUnified(
                registo_id=registo.id,
                description=support,
                benefit_type="service",  # V3 supports are services provided
                service_location=support_area,  # Area as location
                value=value,
            )
            self._add_with_tracking(support_record)

        except Exception as e:
            logger.error(f"Error processing V3 support: {e}")

    def _process_v2_record(
        self,
        record_id: str,
        full_name: str,
        marital_status_desc: str,
        spouse_name: str,
        matrimonial_regime: str,
        exclusivity: str,
        dgf_number: str,
        legislatura: Legislatura,
        registo_v2_elem: ET.Element,
    ) -> bool:
        """Process V2 schema record using unified table architecture"""
        try:
            if not record_id or not full_name:
                logger.debug(
                    "Missing record_id or full_name in V2 record - importing with available data"
                )
                # Both record_id and full_name are required for data integrity
                if not record_id or not full_name:
                    raise ValueError(
                        f"Missing required V2 fields: record_id='{record_id}', full_name='{full_name}'. Data integrity violation - cannot generate artificial data"
                    )

            # FIXED: Use centralized deputy creation logic
            deputado = self._get_or_create_deputy_by_cadastro(
                record_id, full_name, legislatura
            )

            # Extract additional V2 fields
            cad_actividade_profissional = self._get_text(
                registo_v2_elem, "cadActividadeProfissional"
            )
            cad_estado_civil_cod = self._get_text(registo_v2_elem, "cadEstadoCivilCod")

            # Check if unified record already exists for this deputy with V2 schema
            existing_unified = (
                self.session.query(RegistoInteressesUnified)
                .filter_by(
                    deputado_id=deputado.id,
                    schema_version='V2'
                )
                .first()
            )

            if existing_unified:
                # Update existing unified record
                existing_unified.full_name = full_name
                existing_unified.marital_status_desc = marital_status_desc
                existing_unified.professional_activity = cad_actividade_profissional
                existing_unified.marital_status_code = cad_estado_civil_cod
                existing_unified.spouse_name = spouse_name
                existing_unified.matrimonial_regime = matrimonial_regime
                existing_unified.exclusivity = exclusivity
                existing_unified.dgf_number = dgf_number
                registo = existing_unified
            else:
                # Create new unified record with V2 schema
                registo = RegistoInteressesUnified(
                    id=uuid.uuid4(),
                    deputado_id=deputado.id,
                    legislatura_id=legislatura.id,
                    cad_id=deputado.id_cadastro,
                    schema_version='V2',
                    full_name=full_name,
                    marital_status_desc=marital_status_desc,
                    marital_status_code=cad_estado_civil_cod,
                    spouse_name=spouse_name,
                    matrimonial_regime=matrimonial_regime,
                    professional_activity=cad_actividade_profissional,
                    exclusivity=exclusivity,
                    dgf_number=dgf_number,
                )
                self._add_with_tracking(registo)

            # Process detailed nested data from cadRgi using unified extension tables
            rgi_elem = registo_v2_elem.find(
                "cadRgi/pt_ar_wsgode_objectos_DadosRegistoInteressesWebV2"
            )
            if rgi_elem is not None:
                self._process_v2_activities_unified(rgi_elem, registo)
                self._process_v2_societies_unified(rgi_elem, registo)
                self._process_v2_social_positions_unified(rgi_elem, registo)

            return True

        except ValueError as e:
            # Expected when deputy doesn't exist yet (Biographical Registry not processed)
            logger.warning(f"Skipping V2 record: {e}")
            return False
        except Exception as e:
            logger.error(f"Error processing V2 record: {e}")
            return False

    def _process_v1_record(
        self,
        registo_v1_elem: ET.Element,
        record_id: str,
        full_name: str,
        marital_status_desc: str,
        spouse_name: str,
        matrimonial_regime: str,
        exclusivity: str,
        dgf_number: str,
        legislatura: Legislatura,
    ) -> bool:
        """Process V1 schema record with detailed nested structures"""
        try:
            if not record_id or not full_name:
                logger.debug(
                    "Missing record_id or full_name in V1 record - importing with available data"
                )
                # Both record_id and full_name are required for data integrity
                if not record_id or not full_name:
                    raise ValueError(
                        f"Missing required V1 fields: record_id='{record_id}', full_name='{full_name}'. Data integrity violation - cannot generate artificial data"
                    )

            # FIXED: Use centralized deputy creation logic
            deputado = self._get_or_create_deputy_by_cadastro(
                record_id, full_name, legislatura
            )

            # Create unified record for V1
            existing = (
                self.session.query(RegistoInteressesUnified)
                .filter_by(deputado_id=deputado.id, legislatura_id=legislatura.id)
                .first()
            )

            if existing:
                # Update existing unified record
                existing.full_name = full_name
                existing.marital_status_desc = marital_status_desc
                existing.spouse_name = spouse_name
                existing.matrimonial_regime = matrimonial_regime
                existing.schema_version = "V1"
                registo = existing
            else:
                # Create new unified record
                registo = RegistoInteressesUnified(
                    id=uuid.uuid4(),
                    deputado_id=deputado.id,
                    legislatura_id=legislatura.id,
                    cad_id=deputado.id_cadastro,  # Store the cadastral ID, not the primary key
                    full_name=full_name,
                    marital_status_desc=marital_status_desc,
                    spouse_name=spouse_name,
                    matrimonial_regime=matrimonial_regime,
                    schema_version="V1",
                )
                self._add_with_tracking(registo)

            # Process V1 detailed structures from cadRgi
            cad_rgi = registo_v1_elem.find(
                "cadRgi/pt_ar_wsgode_objectos_DadosRegistoInteressesWeb"
            )
            if cad_rgi is not None:
                self._process_v1_detailed_structures(cad_rgi, registo, deputado)

            return True

        except ValueError as e:
            # Expected when deputy doesn't exist yet (Biographical Registry not processed)
            logger.warning(f"Skipping V1 record: {e}")
            return False
        except Exception as e:
            logger.error(f"Error processing V1 record: {e}")
            return False

    def _process_v1_detailed_structures(
        self,
        rgi_elem: ET.Element,
        registo: "RegistoInteressesUnified",
        deputado: "Deputado",
    ):
        """Process V1 detailed structures (rgiSociedades, rgiApoiosBeneficios, etc.)"""
        try:
            # Extract and use only the metadata fields we actually need
            rgi_data_versao = self._parse_date(
                self._get_text(rgi_elem, "rgiDataVersao")
            )
            rgi_leg_des = self._get_text(rgi_elem, "rgiLegDes")

            # Update main record with additional metadata
            if rgi_data_versao:
                registo.version_date = rgi_data_versao
            if rgi_leg_des:
                registo.category = rgi_leg_des  # Legislature description as category

            # Process societies (rgiSociedades)
            self._process_v1_societies(rgi_elem, registo, deputado)

            # Process benefits/support (rgiApoiosBeneficios)
            self._process_v1_benefits(rgi_elem, registo, deputado)

            # Process activities (already covered in existing V1 processing)
            self._process_v1_activities(rgi_elem, registo, deputado)

            # Process social positions (rgiCargosSociais)
            self._process_v1_social_positions(rgi_elem, registo, deputado)

        except Exception as e:
            logger.error(f"Error processing V1 detailed structures: {e}")

    def _process_v1_societies(
        self,
        rgi_elem: ET.Element,
        registo: "RegistoInteressesUnified",
        deputado: "Deputado",
    ):
        """Process V1 rgiSociedades structure"""
        try:
            sociedades_elem = rgi_elem.find("rgiSociedades")
            if sociedades_elem is not None:
                for sociedade in sociedades_elem.findall(
                    "pt_ar_wsgode_objectos_DadosRgiSociedades"
                ):
                    rgs_entidade = self._get_text(sociedade, "rgsEntidade")
                    rgs_local_sede = self._get_text(sociedade, "rgsLocalSede")

                    # Create society record
                    society_record = RegistoInteressesSociedadeUnified(
                        registo_id=registo.id,
                        entity=rgs_entidade,
                        headquarters=rgs_local_sede,
                    )
                    self._add_with_tracking(society_record)

        except Exception as e:
            logger.error(f"Error processing V1 societies: {e}")

    def _process_v1_benefits(
        self,
        rgi_elem: ET.Element,
        registo: "RegistoInteressesUnified",
        deputado: "Deputado",
    ):
        """Process V1 rgiApoiosBeneficios structure"""
        try:
            apoios_elem = rgi_elem.find("rgiApoiosBeneficios")
            if apoios_elem is not None:
                # V1 benefits structure may contain different nested elements
                # Process any child elements as benefit records
                for apoio in apoios_elem:
                    apoio_text = apoio.text if apoio.text else apoio.tag

                    # Create support record
                    support_record = RegistoInteressesApoioUnified(
                        registo_id=registo.id,
                        description=apoio_text,
                        benefit_type="benefit",
                    )
                    self._add_with_tracking(support_record)

        except Exception as e:
            logger.error(f"Error processing V1 benefits: {e}")

    def _process_v1_activities(
        self,
        rgi_elem: ET.Element,
        registo: "RegistoInteressesUnified",
        deputado: "Deputado",
    ):
        """Process V1 rgiActividades structure"""
        try:
            atividades_elem = rgi_elem.find("rgiActividades")
            if atividades_elem is not None:
                for atividade in atividades_elem.findall(
                    "pt_ar_wsgode_objectos_DadosRgiActividades"
                ):
                    rga_atividade = self._get_text(atividade, "rgaActividade")
                    rga_data_inicio = self._parse_date(
                        self._get_text(atividade, "rgaDataInicio")
                    )
                    rga_data_fim = self._parse_date(
                        self._get_text(atividade, "rgaDataFim")
                    )
                    rga_remunerada = self._get_text(atividade, "rgaRemunerada")

                    # Convert remuneration flag
                    is_paid = (
                        rga_remunerada.lower() in ["sim", "yes", "true", "1"]
                        if rga_remunerada
                        else None
                    )

                    # Create activity record
                    activity_record = RegistoInteressesAtividadeUnified(
                        registo_id=registo.id,
                        description=rga_atividade,
                        start_date=rga_data_inicio,
                        end_date=rga_data_fim,
                        remunerated=is_paid,
                    )
                    self._add_with_tracking(activity_record)

        except Exception as e:
            logger.error(f"Error processing V1 activities: {e}")

    def _process_v1_social_positions(
        self,
        rgi_elem: ET.Element,
        registo: "RegistoInteressesUnified",
        deputado: "Deputado",
    ):
        """Process V1 rgiCargosSociais structure"""
        try:
            cargos_elem = rgi_elem.find("rgiCargosSociais")
            if cargos_elem is not None:
                for cargo in cargos_elem.findall(
                    "pt_ar_wsgode_objectos_DadosRgiCargosSociais"
                ):
                    rgc_entidade = self._get_text(cargo, "rgcEntidade")
                    rgc_data_inicio = self._parse_date(
                        self._get_text(cargo, "rgcDataInicio")
                    )
                    rgc_data_fim = self._parse_date(self._get_text(cargo, "rgcDataFim"))

                    # Create social position record
                    position_record = RegistoInteressesSocialPositionUnified(
                        registo_id=registo.id,
                        position=rgc_entidade,
                    )
                    self._add_with_tracking(position_record)

        except Exception as e:
            logger.error(f"Error processing V1 social positions: {e}")

    def _process_v2_activities_unified(
        self, rgi_elem: ET.Element, registo: RegistoInteressesUnified
    ):
        """Process activities from V2 detailed structure using unified extension table"""
        atividades_elem = rgi_elem.find("rgiActividades")
        if atividades_elem is not None:
            for atividade in atividades_elem.findall(
                "pt_ar_wsgode_objectos_DadosRgiActividades"
            ):
                rga_atividade = self._get_text(atividade, "rgaActividade")
                rga_data_inicio = self._parse_date(
                    self._get_text(atividade, "rgaDataInicio")
                )
                rga_data_fim = self._parse_date(self._get_text(atividade, "rgaDataFim"))
                rga_remunerada = self._get_text(atividade, "rgaRemunerada")
                rga_entidade = self._get_text(atividade, "rgaEntidade")
                rga_valor = self._get_text(atividade, "rgaValor")
                rga_observacoes = self._get_text(atividade, "rgaObservacoes")

                if any([rga_atividade, rga_entidade, rga_data_inicio, rga_data_fim]):
                    # Create activity record in unified model
                    activity_record = RegistoInteressesAtividadeUnified(
                        registo_id=registo.id,
                        description=rga_atividade,
                        entity=rga_entidade,
                        start_date=rga_data_inicio,
                        end_date=rga_data_fim,
                        remunerated=rga_remunerada,
                        value=rga_valor,
                        observations=rga_observacoes,
                    )
                    self._add_with_tracking(activity_record)

    def _process_v2_societies_unified(
        self, rgi_elem: ET.Element, registo: RegistoInteressesUnified
    ):
        """Process societies from V2 detailed structure using unified extension table"""
        sociedades_elem = rgi_elem.find("rgiSociedades")
        if sociedades_elem is not None:
            for sociedade in sociedades_elem.findall(
                "pt_ar_wsgode_objectos_DadosRgiSociedades"
            ):
                rgs_entidade = self._get_text(sociedade, "rgsEntidade")
                rgs_area_atividade = self._get_text(sociedade, "rgsAreaActividade")
                rgs_local_sede = self._get_text(sociedade, "rgsLocalSede")
                rgs_parti_social = self._get_text(sociedade, "rgsPartiSocial")
                rgs_valor = self._get_text(sociedade, "rgsValor")
                rgs_observacoes = self._get_text(sociedade, "rgsObservacoes")

                if any([rgs_entidade, rgs_area_atividade, rgs_local_sede]):
                    # Create society record in unified model
                    society_record = RegistoInteressesSociedadeUnified(
                        registo_id=registo.id,
                        entity=rgs_entidade,
                        activity_area=rgs_area_atividade,
                        headquarters=rgs_local_sede,
                        social_participation=rgs_parti_social,
                        value=rgs_valor,
                        observations=rgs_observacoes,
                    )
                    self._add_with_tracking(society_record)

    def _process_v2_social_positions_unified(
        self, rgi_elem: ET.Element, registo: RegistoInteressesUnified
    ):
        """Process social positions from V2 detailed structure using unified extension table"""
        cargos_elem = rgi_elem.find("rgiCargosSociais")
        if cargos_elem is not None:
            for cargo in cargos_elem.findall(
                "pt_ar_wsgode_objectos_DadosRgiCargosSociaisV2"
            ):
                rgc_cargo = self._get_text(cargo, "rgcCargo")
                rgc_entidade = self._get_text(cargo, "rgcEntidade")
                rgc_area_atividade = self._get_text(cargo, "rgcAreaActividade")
                rgc_local_sede = self._get_text(cargo, "rgcLocalSede")
                rgc_valor = self._get_text(cargo, "rgcValor")
                rgc_observacoes = self._get_text(cargo, "rgcObservacoes")

                if any([rgc_cargo, rgc_entidade, rgc_area_atividade]):
                    # Create social position record in unified model
                    position_record = RegistoInteressesSocialPositionUnified(
                        registo_id=registo.id,
                        position=rgc_cargo,
                        entity=rgc_entidade,
                        activity_area=rgc_area_atividade,
                        headquarters_location=rgc_local_sede,
                        value=rgc_valor,
                        observations=rgc_observacoes,
                    )
                    self._add_with_tracking(position_record)

    def _get_int_text(self, parent: ET.Element, tag: str) -> Optional[int]:
        """Get integer value from text content, return None if not found or invalid"""
        text = self._get_text(parent, tag)
        # Use _safe_int to properly handle float strings like '8526.0'
        return self._safe_int(text)

    def _process_v5_record(
        self, registo_v5: ET.Element, legislatura: Legislatura
    ) -> bool:
        """Process comprehensive V5 schema record (XV Legislature) with all declared fields"""
        try:
            # Extract basic identification fields
            categoria = self._get_namespaced_text(registo_v5, "tempuri", "Categoria")
            nome_identificacao = self._get_namespaced_text(
                registo_v5, "tempuri", "NomeIdentificacao"
            )
            id_cadastro_gode = self._get_namespaced_text(
                registo_v5, "tempuri", "IdCadastroGODE"
            )
            versao = self._get_namespaced_text(registo_v5, "tempuri", "versao")
            legislatura_v5 = self._get_namespaced_text(
                registo_v5, "tempuri", "Legislatura"
            )
            servico = self._get_namespaced_text(registo_v5, "tempuri", "Servico")

            # Extract personal data
            dados_pessoais = self._get_namespaced_element(
                registo_v5, "tempuri", "GenDadosPessoais"
            )
            full_name = None
            personal_id = None
            estado_civil = None
            nome_conjuge = None
            regime_bens = None

            if dados_pessoais is not None:
                personal_id = self._get_namespaced_text(dados_pessoais, "tempuri", "Id")
                full_name = self._get_namespaced_text(
                    dados_pessoais, "tempuri", "NomeCompleto"
                )
                estado_civil = self._get_namespaced_text(
                    dados_pessoais, "tempuri", "EstadoCivil"
                )
                nome_conjuge = self._get_namespaced_text(
                    dados_pessoais, "tempuri", "NomeConjuge"
                )
                regime_bens = self._get_namespaced_text(
                    dados_pessoais, "tempuri", "RegimeBens"
                )

            # Extract exclusivity info
            exclusividade_elem = self._get_namespaced_element(
                registo_v5, "tempuri", "Exclusividade"
            )
            exclusivity_id = None
            exclusivity_desc = None
            exclusivity_exclusive = None
            if exclusividade_elem is not None:
                exclusivity_id = self._get_namespaced_text(
                    exclusividade_elem, "tempuri", "Id"
                )
                exclusivity_desc = self._get_namespaced_text(
                    exclusividade_elem, "tempuri", "Designacao"
                )
                exclusivity_exclusive = self._get_namespaced_text(
                    exclusividade_elem, "tempuri", "Exclusividade"
                )

            # Extract declaration facts for proper data preservation
            facto_declaracao = self._get_namespaced_element(
                registo_v5, "tempuri", "FactoDeclaracao"
            )
            declaracao_id = None
            chk_declaracao = None
            cargo_funcao = None
            txt_declaracao = None
            data_inicio_funcao = None
            data_alteracao_funcao = None
            data_cessacao_funcao = None

            if facto_declaracao is not None:
                declaracao_id = self._get_namespaced_text(
                    facto_declaracao, "tempuri", "Id"
                )
                chk_declaracao = self._get_namespaced_text(
                    facto_declaracao, "tempuri", "ChkDeclaracao"
                )
                cargo_funcao = self._get_namespaced_text(
                    facto_declaracao, "tempuri", "CargoFuncao"
                )
                txt_declaracao = self._get_namespaced_text(
                    facto_declaracao, "tempuri", "TxtDeclaracao"
                )
                data_inicio_funcao = self._parse_date(
                    self._get_namespaced_text(
                        facto_declaracao, "tempuri", "DataInicioFuncao"
                    )
                )
                data_alteracao_funcao = self._parse_date(
                    self._get_namespaced_text(
                        facto_declaracao, "tempuri", "DataAlteracaoFuncao"
                    )
                )
                data_cessacao_funcao = self._parse_date(
                    self._get_namespaced_text(
                        facto_declaracao, "tempuri", "DataCessacaoFuncao"
                    )
                )

            # Use IdCadastroGODE as the primary identifier for deputy lookup
            if not id_cadastro_gode:
                raise ValueError(
                    f"No IdCadastroGODE found: id_cadastro_gode='{id_cadastro_gode}'. Data integrity violation - required for deputy association"
                )

            display_name = full_name or nome_identificacao
            if not display_name or display_name.strip() == "Unknown":
                raise ValueError(
                    f"V5 record has no identifiable name: '{display_name}'. Data integrity violation - cannot generate artificial names"
                )

            # Create main interest registry record in unified model
            success = self._process_v5_unified_record(
                id_cadastro_gode,
                display_name,
                estado_civil,
                nome_conjuge,
                regime_bens,
                exclusivity_desc or exclusivity_exclusive,
                exclusivity_id,
                legislatura,
                registo_v5,
                # FactoDeclaracao data
                declaracao_id,
                chk_declaracao,
                cargo_funcao,
                txt_declaracao,
                data_inicio_funcao,
                data_alteracao_funcao,
                data_cessacao_funcao,
            )

            if not success:
                return False

            # Process detailed V5 nested structures
            # Note: Since we don't have specialized database tables for V5 detailed data yet,
            # we'll extract and log the information for now

            nested_data = {}

            # Process GenApoios (supports/benefits)
            gen_apoios = self._get_namespaced_element(
                registo_v5, "tempuri", "GenApoios"
            )
            if gen_apoios is not None:
                apoios_list = []
                for apoio in gen_apoios.findall(".//{http://tempuri.org/}GenApoio"):
                    apoio_data = {
                        "id": self._get_namespaced_text(apoio, "tempuri", "Id"),
                        "entidade": self._get_namespaced_text(
                            apoio, "tempuri", "Entidade"
                        ),
                        "natureza_area": self._get_namespaced_text(
                            apoio, "tempuri", "NaturezaArea"
                        ),
                        "descricao": self._get_namespaced_text(
                            apoio, "tempuri", "Descricao"
                        ),
                        "valor": self._get_namespaced_text(apoio, "tempuri", "Valor"),
                        "apoio": self._get_namespaced_text(apoio, "tempuri", "Apoio"),
                        "natureza_beneficio": self._get_namespaced_text(
                            apoio, "tempuri", "NaturezaBeneficio"
                        ),
                        "data": self._get_namespaced_text(apoio, "tempuri", "Data"),
                        "formulario_id": self._get_namespaced_text(
                            apoio, "tempuri", "FormularioId"
                        ),
                    }
                    if any(apoio_data.values()):
                        apoios_list.append(apoio_data)
                if apoios_list:
                    nested_data["apoios"] = apoios_list

            # Process GenCargosMaisTresAnos (positions more than 3 years)
            gen_cargos_mais = self._get_namespaced_element(
                registo_v5, "tempuri", "GenCargosMaisTresAnos"
            )
            if gen_cargos_mais is not None:
                cargos_list = []
                for cargo in gen_cargos_mais.findall(
                    ".//{http://tempuri.org/}GenCargo"
                ):
                    cargo_data = {
                        "id": self._get_namespaced_text(cargo, "tempuri", "Id"),
                        "entidade": self._get_namespaced_text(
                            cargo, "tempuri", "Entidade"
                        ),
                        "natureza_area": self._get_namespaced_text(
                            cargo, "tempuri", "NaturezaArea"
                        ),
                        "cargo": self._get_namespaced_text(cargo, "tempuri", "Cargo"),
                        "data_inicio": self._get_namespaced_text(
                            cargo, "tempuri", "DataInicio"
                        ),
                        "data_fim": self._get_namespaced_text(
                            cargo, "tempuri", "DataFim"
                        ),
                        "remuneracao": self._get_namespaced_text(
                            cargo, "tempuri", "Remuneracao"
                        ),
                        "remunerada": self._get_namespaced_text(
                            cargo, "tempuri", "Remunerada"
                        ),
                        "natureza": self._get_namespaced_text(
                            cargo, "tempuri", "Natureza"
                        ),
                        "cargo_funcao_atividade": self._get_namespaced_text(
                            cargo, "tempuri", "CargoFuncaoAtividade"
                        ),
                        "local_sede": self._get_namespaced_text(
                            cargo, "tempuri", "LocalSede"
                        ),
                        "data_termo": self._get_namespaced_text(
                            cargo, "tempuri", "DataTermo"
                        ),
                        "formulario_id": self._get_namespaced_text(
                            cargo, "tempuri", "FormularioId"
                        ),
                    }
                    if any(cargo_data.values()):
                        cargos_list.append(cargo_data)
                if cargos_list:
                    nested_data["cargos_mais_3_anos"] = cargos_list

            # Process GenCargosMenosTresAnos (positions less than 3 years)
            gen_cargos_menos = self._get_namespaced_element(
                registo_v5, "tempuri", "GenCargosMenosTresAnos"
            )
            if gen_cargos_menos is not None:
                cargos_list = []
                for cargo in gen_cargos_menos.findall(
                    ".//{http://tempuri.org/}GenCargo"
                ):
                    cargo_data = {
                        "id": self._get_namespaced_text(cargo, "tempuri", "Id"),
                        "entidade": self._get_namespaced_text(
                            cargo, "tempuri", "Entidade"
                        ),
                        "natureza_area": self._get_namespaced_text(
                            cargo, "tempuri", "NaturezaArea"
                        ),
                        "cargo": self._get_namespaced_text(cargo, "tempuri", "Cargo"),
                        "data_inicio": self._get_namespaced_text(
                            cargo, "tempuri", "DataInicio"
                        ),
                        "data_fim": self._get_namespaced_text(
                            cargo, "tempuri", "DataFim"
                        ),
                        "remuneracao": self._get_namespaced_text(
                            cargo, "tempuri", "Remuneracao"
                        ),
                        "remunerada": self._get_namespaced_text(
                            cargo, "tempuri", "Remunerada"
                        ),
                        "natureza": self._get_namespaced_text(
                            cargo, "tempuri", "Natureza"
                        ),
                        "cargo_funcao_atividade": self._get_namespaced_text(
                            cargo, "tempuri", "CargoFuncaoAtividade"
                        ),
                        "local_sede": self._get_namespaced_text(
                            cargo, "tempuri", "LocalSede"
                        ),
                        "data_termo": self._get_namespaced_text(
                            cargo, "tempuri", "DataTermo"
                        ),
                        "formulario_id": self._get_namespaced_text(
                            cargo, "tempuri", "FormularioId"
                        ),
                    }
                    if any(cargo_data.values()):
                        cargos_list.append(cargo_data)
                if cargos_list:
                    nested_data["cargos_menos_3_anos"] = cargos_list

            # Process GenSociedade (societies/companies)
            gen_sociedade = self._get_namespaced_element(
                registo_v5, "tempuri", "GenSociedade"
            )
            if gen_sociedade is not None:
                sociedades_list = []
                for sociedade in gen_sociedade.findall(
                    ".//{http://tempuri.org/}GenSociedade"
                ):
                    sociedade_data = {
                        "id": self._get_namespaced_text(sociedade, "tempuri", "Id"),
                        "sociedade": self._get_namespaced_text(
                            sociedade, "tempuri", "Sociedade"
                        ),
                        "natureza_area": self._get_namespaced_text(
                            sociedade, "tempuri", "NaturezaArea"
                        ),
                        "participacao_social": self._get_namespaced_text(
                            sociedade, "tempuri", "ParticipacaoSocial"
                        ),
                        "valor": self._get_namespaced_text(
                            sociedade, "tempuri", "Valor"
                        ),
                        "observacoes": self._get_namespaced_text(
                            sociedade, "tempuri", "Observacoes"
                        ),
                        "natureza": self._get_namespaced_text(
                            sociedade, "tempuri", "Natureza"
                        ),
                        "participacao": self._get_namespaced_text(
                            sociedade, "tempuri", "Participacao"
                        ),
                        "local_sede": self._get_namespaced_text(
                            sociedade, "tempuri", "LocalSede"
                        ),
                        "formulario_id": self._get_namespaced_text(
                            sociedade, "tempuri", "FormularioId"
                        ),
                    }
                    if any(sociedade_data.values()):
                        sociedades_list.append(sociedade_data)
                if sociedades_list:
                    nested_data["sociedades"] = sociedades_list

            # Log comprehensive V5 data extraction (summary only to avoid log spam)
            nested_counts = {
                k: len(v) if isinstance(v, list) else 1 for k, v in nested_data.items()
            }
            if nested_counts:
                logger.info(
                    f"Processed V5 record: {display_name} (Legislatura: {legislatura_v5 or legislatura.numero}) - Nested data: {nested_counts}"
                )
            else:
                logger.info(
                    f"Processed V5 record: {display_name} (Legislatura: {legislatura_v5 or legislatura.numero})"
                )

            return True

        except ValueError as e:
            # Expected when deputy doesn't exist yet (Biographical Registry not processed)
            logger.warning(f"Skipping V5 record: {e}")
            return False
        except Exception as e:
            logger.error(f"Error processing V5 record: {e}")
            return False

    def _process_v5_unified_record(
        self,
        id_cadastro_gode: str,
        display_name: str,
        estado_civil: str,
        nome_conjuge: str,
        regime_bens: str,
        exclusivity: str,
        exclusivity_id: str,
        legislatura: Legislatura,
        registo_v5: ET.Element,
        # FactoDeclaracao parameters
        declaracao_id: str = None,
        chk_declaracao: str = None,
        cargo_funcao: str = None,
        txt_declaracao: str = None,
        data_inicio_funcao=None,
        data_alteracao_funcao=None,
        data_cessacao_funcao=None,
    ) -> bool:
        """Process V5 record in unified model with detailed structures"""
        try:
            if not id_cadastro_gode or not display_name:
                logger.debug(
                    "Missing id_cadastro_gode or display_name in V5 unified record - importing with placeholders"
                )
                # Both id_cadastro_gode and display_name are required for data integrity
                if not id_cadastro_gode or not display_name:
                    raise ValueError(
                        f"Missing required V5 fields: id_cadastro_gode='{id_cadastro_gode}', display_name='{display_name}'. Data integrity violation - cannot generate artificial data"
                    )

            # Use IdCadastroGODE for deputy lookup with robust matching
            cad_id = self._safe_int(id_cadastro_gode)
            if cad_id is None:
                raise ValueError(
                    f"IdCadastroGODE must be numeric: '{id_cadastro_gode}'. Data integrity violation"
                )
            deputado = self._find_deputy_robust(cad_id, display_name, display_name)

            # Extract gender from GenDadosPessoais
            dados_pessoais = self._get_namespaced_element(
                registo_v5, "tempuri", "GenDadosPessoais"
            )
            gender = None
            if dados_pessoais is not None:
                gender = self._get_namespaced_text(dados_pessoais, "tempuri", "Sexo")

            # Check if unified record already exists by deputado_id + legislatura_id
            existing = (
                self.session.query(RegistoInteressesUnified)
                .filter_by(deputado_id=deputado.id, legislatura_id=legislatura.id)
                .first()
            )

            if existing:
                # Update existing record
                existing.full_name = display_name
                existing.marital_status_desc = estado_civil
                existing.spouse_name = nome_conjuge
                existing.matrimonial_regime = regime_bens
                existing.exclusivity = exclusivity
                existing.dgf_number = exclusivity_id
                existing.gender = gender
                existing.schema_version = "V5"
                registo = existing

                # Update FactoDeclaracao for existing record
                if any(
                    [
                        declaracao_id,
                        chk_declaracao,
                        cargo_funcao,
                        txt_declaracao,
                        data_inicio_funcao,
                        data_alteracao_funcao,
                        data_cessacao_funcao,
                    ]
                ):

                    existing_facto = (
                        self.session.query(RegistoInteressesFactoDeclaracao)
                        .filter_by(registo_id=registo.id)
                        .first()
                    )

                    if existing_facto:
                        # Update existing FactoDeclaracao
                        existing_facto.declaracao_id = declaracao_id
                        existing_facto.chk_declaracao = chk_declaracao
                        existing_facto.cargo_funcao = cargo_funcao
                        existing_facto.txt_declaracao = txt_declaracao
                        existing_facto.data_inicio_funcao = data_inicio_funcao
                        existing_facto.data_alteracao_funcao = data_alteracao_funcao
                        existing_facto.data_cessacao_funcao = data_cessacao_funcao
                    else:
                        # Create new FactoDeclaracao for existing registo
                        facto_declaracao_record = RegistoInteressesFactoDeclaracao(
                            registo_id=registo.id,
                            declaracao_id=declaracao_id,
                            chk_declaracao=chk_declaracao,
                            cargo_funcao=cargo_funcao,
                            txt_declaracao=txt_declaracao,
                            data_inicio_funcao=data_inicio_funcao,
                            data_alteracao_funcao=data_alteracao_funcao,
                            data_cessacao_funcao=data_cessacao_funcao,
                        )
                        self._add_with_tracking(facto_declaracao_record)
            else:
                # Create new unified record
                registo = RegistoInteressesUnified(
                    id=uuid.uuid4(),
                    deputado_id=deputado.id,
                    legislatura_id=legislatura.id,
                    full_name=display_name,
                    marital_status_desc=estado_civil,
                    spouse_name=nome_conjuge,
                    matrimonial_regime=regime_bens,
                    exclusivity=exclusivity,
                    dgf_number=exclusivity_id,
                    gender=gender,
                    schema_version="V5",
                )
                self._add_with_tracking(registo)

            # Store FactoDeclaracao data if provided
            if any(
                [
                    declaracao_id,
                    chk_declaracao,
                    cargo_funcao,
                    txt_declaracao,
                    data_inicio_funcao,
                    data_alteracao_funcao,
                    data_cessacao_funcao,
                ]
            ):

                # Check if FactoDeclaracao record already exists
                existing_facto = (
                    self.session.query(RegistoInteressesFactoDeclaracao)
                    .filter_by(registo_id=registo.id)
                    .first()
                )

                if existing_facto:
                    # Update existing record
                    existing_facto.declaracao_id = declaracao_id
                    existing_facto.chk_declaracao = chk_declaracao
                    existing_facto.cargo_funcao = cargo_funcao
                    existing_facto.txt_declaracao = txt_declaracao
                    existing_facto.data_inicio_funcao = data_inicio_funcao
                    existing_facto.data_alteracao_funcao = data_alteracao_funcao
                    existing_facto.data_cessacao_funcao = data_cessacao_funcao
                else:
                    # Create new FactoDeclaracao record
                    facto_declaracao_record = RegistoInteressesFactoDeclaracao(
                        registo_id=registo.id,
                        declaracao_id=declaracao_id,
                        chk_declaracao=chk_declaracao,
                        cargo_funcao=cargo_funcao,
                        txt_declaracao=txt_declaracao,
                        data_inicio_funcao=data_inicio_funcao,
                        data_alteracao_funcao=data_alteracao_funcao,
                        data_cessacao_funcao=data_cessacao_funcao,
                    )
                    self._add_with_tracking(facto_declaracao_record)

                logger.debug(
                    f"Stored FactoDeclaracao for record {id_cadastro_gode}: cargo={cargo_funcao}, inicio={data_inicio_funcao}"
                )

            # Process V5 detailed structures
            self._process_v5_apoios(registo_v5, registo, deputado)
            self._process_v5_atividades_profissionais(registo_v5, registo, deputado)
            self._process_v5_cargos_mais_tres_anos(registo_v5, registo, deputado)
            self._process_v5_cargos_menos_tres_anos(registo_v5, registo, deputado)
            self._process_v5_servicos_prestados(registo_v5, registo, deputado)
            self._process_v5_sociedades(registo_v5, registo, deputado)
            self._process_v5_incompatibilidades(registo_v5, registo, deputado)

            return True

        except ValueError as e:
            # Expected when deputy doesn't exist yet (Biographical Registry not processed)
            logger.warning(f"Skipping V5 unified record: {e}")
            return False
        except Exception as e:
            logger.error(f"Error processing V5 unified record: {e}")
            return False

    def _process_v5_apoios(
        self,
        registo_v5: ET.Element,
        registo: "RegistoInteressesUnified",
        deputado: "Deputado",
    ):
        """Process V5 GenApoios (supports/benefits)"""
        try:
            gen_apoios = self._get_namespaced_element(
                registo_v5, "tempuri", "GenApoios"
            )
            if gen_apoios is not None:
                for apoio in gen_apoios.findall(".//{http://tempuri.org/}GenApoio"):
                    entidade = self._get_namespaced_text(apoio, "tempuri", "Entidade")
                    natureza_area = self._get_namespaced_text(
                        apoio, "tempuri", "NaturezaArea"
                    )
                    descricao = self._get_namespaced_text(apoio, "tempuri", "Descricao")
                    valor = self._get_namespaced_text(apoio, "tempuri", "Valor")
                    apoio_text = self._get_namespaced_text(apoio, "tempuri", "Apoio")
                    natureza_beneficio = self._get_namespaced_text(
                        apoio, "tempuri", "NaturezaBeneficio"
                    )
                    data = self._parse_date(
                        self._get_namespaced_text(apoio, "tempuri", "Data")
                    )

                    # Create support record
                    apoio_record = RegistoInteressesApoioUnified(
                        registo_id=registo.id,
                        entity=entidade,
                        description=apoio_text or descricao,
                        benefit_type=natureza_beneficio,
                        service_location=natureza_area,
                        value=valor,
                        start_date=data,
                    )
                    self._add_with_tracking(apoio_record)

        except Exception as e:
            logger.error(f"Error processing V5 apoios: {e}")

    def _process_v5_atividades_profissionais(
        self,
        registo_v5: ET.Element,
        registo: "RegistoInteressesUnified",
        deputado: "Deputado",
    ):
        """Process V5 GenAtivProfissional (professional activities)"""
        try:
            gen_ativ = self._get_namespaced_element(
                registo_v5, "tempuri", "GenAtivProfissional"
            )
            if gen_ativ is not None:
                for ativ in gen_ativ.findall(
                    ".//{http://tempuri.org/}GenAtivProfissional"
                ):
                    cargo_funcao_atividade = self._get_namespaced_text(
                        ativ, "tempuri", "CargoFuncaoAtividade"
                    )
                    local_sede = self._get_namespaced_text(ativ, "tempuri", "LocalSede")
                    data_termo = self._parse_date(
                        self._get_namespaced_text(ativ, "tempuri", "DataTermo")
                    )

                    # Create activity record
                    activity_record = RegistoInteressesAtividadeUnified(
                        registo_id=registo.id,
                        description=cargo_funcao_atividade,
                        end_date=data_termo,
                    )
                    self._add_with_tracking(activity_record)

        except Exception as e:
            logger.error(f"Error processing V5 professional activities: {e}")

    def _process_v5_cargos_mais_tres_anos(
        self,
        registo_v5: ET.Element,
        registo: "RegistoInteressesUnified",
        deputado: "Deputado",
    ):
        """Process V5 GenCargosMaisTresAnos (positions more than 3 years)"""
        try:
            gen_cargos = self._get_namespaced_element(
                registo_v5, "tempuri", "GenCargosMaisTresAnos"
            )
            if gen_cargos is not None:
                for cargo in gen_cargos.findall(".//{http://tempuri.org/}GenCargo"):
                    cargo_funcao_atividade = self._get_namespaced_text(
                        cargo, "tempuri", "CargoFuncaoAtividade"
                    )
                    local_sede = self._get_namespaced_text(
                        cargo, "tempuri", "LocalSede"
                    )
                    data_termo = self._parse_date(
                        self._get_namespaced_text(cargo, "tempuri", "DataTermo")
                    )

                    # Create social position record (positions are social positions)
                    position_record = RegistoInteressesSocialPositionUnified(
                        registo_id=registo.id,
                        position=cargo_funcao_atividade,
                        headquarters_location=local_sede,
                        type_classification="mais_tres_anos",
                    )
                    self._add_with_tracking(position_record)

        except Exception as e:
            logger.error(f"Error processing V5 positions more than 3 years: {e}")

    def _process_v5_cargos_menos_tres_anos(
        self,
        registo_v5: ET.Element,
        registo: "RegistoInteressesUnified",
        deputado: "Deputado",
    ):
        """Process V5 GenCargosMenosTresAnos (positions less than 3 years)"""
        try:
            gen_cargos = self._get_namespaced_element(
                registo_v5, "tempuri", "GenCargosMenosTresAnos"
            )
            if gen_cargos is not None:
                for cargo in gen_cargos.findall(".//{http://tempuri.org/}GenCargo"):
                    cargo_funcao_atividade = self._get_namespaced_text(
                        cargo, "tempuri", "CargoFuncaoAtividade"
                    )
                    local_sede = self._get_namespaced_text(
                        cargo, "tempuri", "LocalSede"
                    )
                    data_termo = self._parse_date(
                        self._get_namespaced_text(cargo, "tempuri", "DataTermo")
                    )

                    # Create social position record
                    position_record = RegistoInteressesSocialPositionUnified(
                        registo_id=registo.id,
                        position=cargo_funcao_atividade,
                        headquarters_location=local_sede,
                        type_classification="menos_tres_anos",
                    )
                    self._add_with_tracking(position_record)

        except Exception as e:
            logger.error(f"Error processing V5 positions less than 3 years: {e}")

    def _process_v5_servicos_prestados(
        self,
        registo_v5: ET.Element,
        registo: "RegistoInteressesUnified",
        deputado: "Deputado",
    ):
        """Process V5 GenServicoPrestado (services provided)"""
        try:
            gen_servico = self._get_namespaced_element(
                registo_v5, "tempuri", "GenServicoPrestado"
            )
            if gen_servico is not None:
                for servico in gen_servico.findall(
                    ".//{http://tempuri.org/}GenServicoPrestado"
                ):
                    natureza = self._get_namespaced_text(servico, "tempuri", "Natureza")
                    local = self._get_namespaced_text(servico, "tempuri", "Local")
                    local_sede = self._get_namespaced_text(
                        servico, "tempuri", "LocalSede"
                    )
                    data = self._parse_date(
                        self._get_namespaced_text(servico, "tempuri", "Data")
                    )
                    data_termo = self._parse_date(
                        self._get_namespaced_text(servico, "tempuri", "DataTermo")
                    )

                    # Create support record (services are support records)
                    service_record = RegistoInteressesApoioUnified(
                        registo_id=registo.id,
                        description=natureza,
                        benefit_type="service",
                        service_location=local or local_sede,
                        start_date=data,
                        end_date=data_termo,
                    )
                    self._add_with_tracking(service_record)

        except Exception as e:
            logger.error(f"Error processing V5 services provided: {e}")

    def _process_v5_sociedades(
        self,
        registo_v5: ET.Element,
        registo: "RegistoInteressesUnified",
        deputado: "Deputado",
    ):
        """Process V5 GenSociedade (societies)"""
        try:
            gen_sociedade = self._get_namespaced_element(
                registo_v5, "tempuri", "GenSociedade"
            )
            if gen_sociedade is not None:
                for sociedade in gen_sociedade.findall(
                    ".//{http://tempuri.org/}GenSociedade"
                ):
                    natureza = self._get_namespaced_text(
                        sociedade, "tempuri", "Natureza"
                    )
                    local_sede = self._get_namespaced_text(
                        sociedade, "tempuri", "LocalSede"
                    )

                    # Create society record
                    society_record = RegistoInteressesSociedadeUnified(
                        registo_id=registo.id,
                        entity=natureza,  # Nature as entity
                        headquarters=local_sede,
                    )
                    self._add_with_tracking(society_record)

        except Exception as e:
            logger.error(f"Error processing V5 societies: {e}")

    def _process_v5_incompatibilidades(
        self,
        registo_v5: ET.Element,
        registo: "RegistoInteressesUnified",
        deputado: "Deputado",
    ):
        """Process V5 GenIncompatibilidade (incompatibilities)"""
        try:
            gen_incompatibilidade = self._get_namespaced_element(
                registo_v5, "tempuri", "GenIncompatibilidade"
            )
            if gen_incompatibilidade is not None:
                for incomp in gen_incompatibilidade.findall(
                    ".//{http://tempuri.org/}Incompatibilidade"
                ):
                    incompatibilidade = self._get_text(incomp, "")  # Get text content

                    # Log incompatibility (no specific unified model for this yet)
                    if incompatibilidade:
                        logger.debug(f"Processing incompatibility: {incompatibilidade}")

        except Exception as e:
            logger.error(f"Error processing V5 incompatibilities: {e}")

    # Utility methods now inherited from EnhancedSchemaMapper base class
