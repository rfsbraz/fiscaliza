"""
Deputy Activities Mapper - Enhanced with Official Documentation
==============================================================

Schema mapper for deputy activity files (AtividadeDeputado*.xml).
Updated with comprehensive understanding from official Parliament documentation.

This mapper handles deputy activities including:
- Initiatives presented (ini) - IniciativasOut structure
- Questions and Requirements submitted (req) - RequerimentosOut structure
- Subcommittees and working groups (scgt) - SubComissoesGruposTrabalhoOut structure
- Parliamentary interventions (Intev) - IntervencoesOut structure
- Parliamentary activities (actP) - ActividadesParlamentaresOut structure
- Parliamentary friendship groups (Gpa) - GruposParlamentaresAmizadeOut structure
- Permanent delegations (dlP) - DelegacoesPermanentesOut structure
- Occasional delegations (dlE) - DelegacoesEventuaisOut structure
- Rapporteur assignments (Rel) - RelatoresOut structure
- Committee events (eventos) - ActividadesComissaoOut structure
- Displacements (deslocações) - ActividadesComissaoOut structure
- Committees (cms) - ComissoesOut structure
- Legislative data (dadosLegisDeputado) - DadosLegisDeputado structure
- Hearings (audiências) - ActividadesComissaoOut structure
- Auditions (audicoes) - ActividadesComissaoOut structure
- Youth Parliament activities (parlamentoJovens) - DadosDeputado structure
- Deputy biography videos (vídeos) - VideosOut structure
- AR working groups (gtar) - GruposTrabalhoAROut structure

Based on official documentation: 'Significado das Tags do Ficheiro AtividadeDeputado<Legislatura>.xml'
**IMPORTANT FINDING**: Documentation compared between Constituinte and Legislature I shows
**IDENTICAL FIELD DEFINITIONS**. This suggests the XML structure and field meanings are
consistent across legislatures, contrary to initial concerns.

**VERIFIED LEGISLATURES**: Constituinte, I Legislature, II Legislature, III Legislature, IV Legislature, V Legislature, VI Legislature, VII Legislature, VIII Legislature, IX Legislature, X Legislature, XI Legislature, XII Legislature, XIII Legislature (ALL IDENTICAL documentation)
**PENDING VERIFICATION**: XIV, XV, XVI, XVII

"""

import logging
import os
import re
import uuid

# Import our models
import sys
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Set

from .enhanced_base_mapper import EnhancedSchemaMapper, SchemaError

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from database.models import (  # IX Legislature models; I Legislature models
    ActividadeAudicao,
    ActividadeAudiencia,
    ActividadeIntervencao,
    ActividadeIntervencaoOut,
    ActividadeOut,
    ActividadesComissaoOut,
    ActividadesParlamentares,
    ActividadesParlamentaresOut,
    AtividadeDeputado,
    AtividadeDeputadoList,
    AutoresPareceresIncImu,
    AutoresPareceresIncImuOut,
    Comissoes,
    ComissoesOut,
    DadosCargoDeputado,
    DadosDeputadoParlamentoJovens,
    DadosLegisDeputado,
    DadosSituacaoDeputado,
    DelegacoesEventuais,
    DelegacoesEventuaisOut,
    DelegacoesPermanentes,
    DelegacoesPermanentesOut,
    DepCargo,
    Deputado,
    DeputadoSituacao,
    Deslocacoes,
    Eventos,
    GruposParlamentaresAmizade,
    GruposParlamentaresAmizadeOut,
    ParlamentoJovens,
    RelatoresContasPublicas,
    RelatoresContasPublicasOut,
    RelatoresIniciativas,
    RelatoresIniciativasOut,
    RelatoresIniEuropeias,
    RelatoresIniEuropeiasOut,
    RelatoresPeticoes,
    RelatoresPeticoesOut,
    RequerimentosAtivDep,
    RequerimentosAtivDepOut,
    ReunioesDelegacoesPermanentes,
    SubComissoesGruposTrabalho,
    SubComissoesGruposTrabalhoOut,
)

logger = logging.getLogger(__name__)


class AtividadeDeputadosMapper(EnhancedSchemaMapper):
    """
    Deputy Activity Data Mapper - Cross-Legislature Validated
    ========================================================

    Maps Portuguese Parliament deputy activity XML files to database models.
    Based on official Parliament documentation (December 2017):
    "Significado das Tags do Ficheiro AtividadeDeputado<Legislatura>.xml"

    DOCUMENTATION STATUS:
    ✓ Constituinte Legislature - Documented and validated
    ✓ I Legislature - Documented and validated (IDENTICAL to Constituinte)
    ✓ II Legislature - Documented and validated (IDENTICAL to Constituinte & I)
    ✓ III Legislature - Documented and validated (IDENTICAL to all previous)
    ✓ IV Legislature - Documented and validated (IDENTICAL to all previous)
    ✓ V Legislature - Documented and validated (IDENTICAL to all previous)
    ✓ VI Legislature - Documented and validated (IDENTICAL to all previous)
    ✓ VII Legislature - Documented and validated (IDENTICAL to all previous)
    ✓ VIII Legislature - Documented and validated (IDENTICAL to all previous)
    ✓ IX Legislature - Documented and validated (IDENTICAL to all previous)
    ✓ X Legislature - Documented and validated (IDENTICAL to all previous)
    ? XI-XVII Legislatures - Pending documentation analysis

    FINDING: Field definitions are IDENTICAL across all validated legislatures,
    proving consistent XML structure across Portuguese Parliament legislatures.

    MAPPED STRUCTURES (from official documentation):

    1. **IniciativasOut** - Deputy initiatives presented
       - iniId: Initiative identifier
       - iniNr: Initiative number
       - iniTp: Initiative type (requires TipodeIniciativa translator)
       - iniTpdesc: Initiative type description
       - iniSelLg: Initiative legislature
       - iniSelNr: Legislative session
       - iniTi: Initiative title

    2. **RequerimentosOut** - Questions and requirements submitted
       - reqId: Requirement identifier
       - reqNr: Requirement number
       - reqTp: Requirement type (requires TipodeRequerimento translator)
       - reqLg: Requirement legislature
       - reqSl: Legislative session
       - reqAs: Requirement subject
       - reqDt: Requirement date
       - reqPerTp: Document type (requerimento/pergunta)

    3. **IntervencoesOut** - Parliamentary interventions
       - intId: Intervention identifier
       - intTe: Intervention summary
       - intSu: Intervention summary
       - pubTp: Publication type (requires TipodePublicacao translator)
       - pubDar: Assembly Diary number
       - tinDs: Intervention type

    4. **ActividadesParlamentaresOut** - Parliamentary activities
       - actId: Activity identifier
       - actNr: Activity number
       - actTp: Activity type (requires TipodeAtividade translator)
       - actTpdesc: Activity type description
       - actSelLg: Activity legislature
       - actSelNr: Legislative session
       - actAs: Activity subject

    5. **ComissoesOut** - Committee memberships
       - cmsNo: Committee name
       - cmsCd: Committee code
       - cmsCargo: Committee position
       - cmsSituacao: Member status (suplente/efetivo - requires translator)

    TRANSLATION REQUIREMENTS:
    - Use database.translators.deputy_activities for activity/request types
    - Use database.translators.publications for publication types
    - Use database.translators.initiatives for initiative types
    - Use database.translators.parliamentary_interventions for intervention types

    DATA INTEGRITY PRINCIPLES:
    - Map XML to SQL directly without artificial data generation
    - Preserve all original field values and relationships
    - Document every field mapping with official documentation reference
    - Handle coded fields through application-level translators (not in mapper)
    """

    def __init__(self, session, import_status_record=None):
        super().__init__(session, import_status_record=import_status_record)
        # Use the passed SQLAlchemy session
        self.session = session

    def get_expected_fields(self) -> Set[str]:
        """Return actual XML paths for complete coverage of AtividadeDeputado files"""
        return {
            # Root structure - ACTUAL XML FORMAT
            "ArrayOfAtividadeDeputado",
            "ArrayOfAtividadeDeputado.AtividadeDeputado",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Audiencias",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Audiencias.ActividadesComissaoOut",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Audicoes",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Audicoes.ActividadesComissaoOut",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.DadosLegisDeputado",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.DadosLegisDeputado.DadosLegisDeputado",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.DadosLegisDeputado.DadosLegisDeputado.Nome",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.DadosLegisDeputado.DadosLegisDeputado.Dpl_grpar",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.DadosLegisDeputado.DadosLegisDeputado.Dpl_lg",
            # Deputy information - ACTUAL XML FORMAT
            "ArrayOfAtividadeDeputado.AtividadeDeputado.Deputado",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.Deputado.DepId",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.Deputado.DepCadId",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.Deputado.DepNomeParlamentar",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.Deputado.DepNomeCompleto",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.Deputado.DepCPId",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.Deputado.DepCPDes",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.Deputado.LegDes",
            # Deputy parliamentary group - ACTUAL XML FORMAT
            "ArrayOfAtividadeDeputado.AtividadeDeputado.Deputado.DepGP",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.Deputado.DepGP.DadosSituacaoGP",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.Deputado.DepGP.DadosSituacaoGP.GpId",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.Deputado.DepGP.DadosSituacaoGP.GpSigla",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.Deputado.DepGP.DadosSituacaoGP.GpDtInicio",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.Deputado.DepGP.DadosSituacaoGP.GpDtFim",
            # Deputy situations - ACTUAL XML FORMAT
            "ArrayOfAtividadeDeputado.AtividadeDeputado.Deputado.DepSituacao",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.Deputado.DepSituacao.DadosSituacaoDeputado",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.Deputado.DepSituacao.DadosSituacaoDeputado.SioDes",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.Deputado.DepSituacao.DadosSituacaoDeputado.SioDtInicio",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.Deputado.DepSituacao.DadosSituacaoDeputado.SioDtFim",
            # Deputy cargo - ACTUAL XML FORMAT
            "ArrayOfAtividadeDeputado.AtividadeDeputado.Deputado.DepCargo",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.Deputado.DepCargo.pt_ar_wsgode_objectos_DadosCargoDeputado",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.Deputado.DepCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carDes",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.Deputado.DepCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carId",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.Deputado.DepCargo.pt_ar_wsgode_objectos_DadosCargoDeputado.carDtInicio",
            # Deputy initiatives - III Legislature and others
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Ini",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Ini.IniciativasOut",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Ini.IniciativasOut.IniId",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Ini.IniciativasOut.IniNr",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Ini.IniciativasOut.IniSelLg",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Ini.IniciativasOut.IniSelNr",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Ini.IniciativasOut.IniTi",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Ini.IniciativasOut.IniTp",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Ini.IniciativasOut.IniTpdesc",
            # Deputy interventions - IV Legislature and others
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Intev",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Intev.IntervencoesOut",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Intev.IntervencoesOut.IntId",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Intev.IntervencoesOut.IntSu",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Intev.IntervencoesOut.PubDar",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Intev.IntervencoesOut.PubDtreu",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Intev.IntervencoesOut.PubLg",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Intev.IntervencoesOut.PubNr",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Intev.IntervencoesOut.PubSl",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Intev.IntervencoesOut.PubTp",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Intev.IntervencoesOut.TinDs",
            # IX Legislature - Parliamentary Activities (ActP)
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.ActP",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.ActP.ActividadesParlamentaresOut",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.ActP.ActividadesParlamentaresOut.ActId",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.ActP.ActividadesParlamentaresOut.ActNr",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.ActP.ActividadesParlamentaresOut.ActTp",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.ActP.ActividadesParlamentaresOut.ActTpdesc",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.ActP.ActividadesParlamentaresOut.ActSelLg",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.ActP.ActividadesParlamentaresOut.ActSelNr",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.ActP.ActividadesParlamentaresOut.ActDtent",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.ActP.ActividadesParlamentaresOut.ActDtdeb",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.ActP.ActividadesParlamentaresOut.ActAs",
            # IX Legislature - Friendship Groups (Gpa)
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Gpa",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Gpa.GruposParlamentaresAmizadeOut",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Gpa.GruposParlamentaresAmizadeOut.CgaCrg",
            # IX Legislature - Permanent Delegations (DlP)
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.DlP",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.DlP.DelegacoesPermanentesOut",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.DlP.DelegacoesPermanentesOut.DepId",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.DlP.DelegacoesPermanentesOut.DepNo",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.DlP.DelegacoesPermanentesOut.CdeCrg",
            # IX Legislature - Occasional Delegations (DlE)
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.DlE",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.DlE.DelegacoesEventuaisOut",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.DlE.DelegacoesEventuaisOut.DevDtini",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.DlE.DelegacoesEventuaisOut.DevDtfim",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.DlE.DelegacoesEventuaisOut.DevSelNr",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.DlE.DelegacoesEventuaisOut.DevLoc",
            # IX Legislature - Requirements (Req)
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Req",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Req.RequerimentosAtivDepOut",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Req.RequerimentosAtivDepOut.ReqId",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Req.RequerimentosAtivDepOut.ReqNr",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Req.RequerimentosAtivDepOut.ReqTp",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Req.RequerimentosAtivDepOut.ReqLg",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Req.RequerimentosAtivDepOut.ReqSl",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Req.RequerimentosAtivDepOut.ReqAs",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Req.RequerimentosAtivDepOut.ReqDt",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Req.RequerimentosAtivDepOut.ReqPerTp",
            # IX Legislature - Sub-committees/Working Groups (Scgt)
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Scgt",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Scgt.SubComissoesGruposTrabalhoOut",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Scgt.SubComissoesGruposTrabalhoOut.ScmCd",
            # IX Legislature - Petition Rapporteurs
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.RelatoresPeticoes",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.RelatoresPeticoes.RelatoresPeticoesOut",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.RelatoresPeticoes.RelatoresPeticoesOut.PecDtrelf",
            # IX Legislature - Enhanced Committee Activities
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Audiencias.ActividadesComissaoOut.ActId",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Audiencias.ActividadesComissaoOut.ActAs",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Audiencias.ActividadesComissaoOut.ActDtent",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Audiencias.ActividadesComissaoOut.AccDtaud",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Audiencias.ActividadesComissaoOut.ActTp",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Audiencias.ActividadesComissaoOut.ActTpdesc",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Audiencias.ActividadesComissaoOut.ActNr",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Audiencias.ActividadesComissaoOut.ActLg",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Audiencias.ActividadesComissaoOut.NomeEntidadeExterna",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Audiencias.ActividadesComissaoOut.CmsNo",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Audiencias.ActividadesComissaoOut.CmsAb",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Audicoes.ActividadesComissaoOut.ActId",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Audicoes.ActividadesComissaoOut.ActAs",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Audicoes.ActividadesComissaoOut.AccDtaud",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Audicoes.ActividadesComissaoOut.ActTp",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Audicoes.ActividadesComissaoOut.ActDtent",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Audicoes.ActividadesComissaoOut.ActNr",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Audicoes.ActividadesComissaoOut.ActTpdesc",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Audicoes.ActividadesComissaoOut.NomeEntidadeExterna",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Audicoes.ActividadesComissaoOut.CmsNo",
            # IX Legislature - Committees (Cms)
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Cms",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Cms.ComissoesOut",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Cms.ComissoesOut.CmsNo",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Cms.ComissoesOut.CmsCd",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Cms.ComissoesOut.CmsLg",
            # IX Legislature - Enhanced Sub-committees/Working Groups fields
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Scgt.SubComissoesGruposTrabalhoOut.CmsCargo",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Scgt.SubComissoesGruposTrabalhoOut.ScmComLg",
            # IX Legislature - Enhanced Petition Rapporteurs fields
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.RelatoresPeticoes.RelatoresPeticoesOut.PetSelLgPk",
            # IX Legislature - Initiative Rapporteurs fields
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.RelatoresIniciativas",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.RelatoresIniciativas.RelatoresIniciativasOut",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.RelatoresIniciativas.RelatoresIniciativasOut.IniNr",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.RelatoresIniciativas.RelatoresIniciativasOut.AccDtrel",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.RelatoresIniciativas.RelatoresIniciativasOut.IniTi",
            # IX Legislature - Additional missing fields
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.DlE.DelegacoesEventuaisOut.DevSelLg",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Scgt.SubComissoesGruposTrabalhoOut.ScmComCd",
            # IX Legislature - Permanent Delegation Meetings fields
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.DlP.DelegacoesPermanentesOut.DepReunioes",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.DlP.DelegacoesPermanentesOut.DepReunioes.ReunioesDelegacoesPermanentes",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.DlP.DelegacoesPermanentesOut.DepReunioes.ReunioesDelegacoesPermanentes.RenDtIni",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.DlP.DelegacoesPermanentesOut.DepReunioes.ReunioesDelegacoesPermanentes.RenLoc",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.DlP.DelegacoesPermanentesOut.DepReunioes.ReunioesDelegacoesPermanentes.RenDtFim",
            # IX Legislature - Additional missing fields from final validation
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.DlE.DelegacoesEventuaisOut.DevId",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.DlE.DelegacoesEventuaisOut.DevNo",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.RelatoresPeticoes.RelatoresPeticoesOut.PetAspet",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.RelatoresPeticoes.RelatoresPeticoesOut.PetSelNrPk",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.DlP.DelegacoesPermanentesOut.DepReunioes.ReunioesDelegacoesPermanentes.RenTi",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Gpa.GruposParlamentaresAmizadeOut.GplNo",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Gpa.GruposParlamentaresAmizadeOut.GplId",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.DlP.DelegacoesPermanentesOut.DepSelLg",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.RelatoresIniciativas.RelatoresIniciativasOut.IniId",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Audicoes.ActividadesComissaoOut.CmsAb",
            # IX Legislature - Final missing fields for complete coverage
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.RelatoresPeticoes.RelatoresPeticoesOut.PetNr",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.RelatoresPeticoes.RelatoresPeticoesOut.PetId",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Intev.IntervencoesOut.IntTe",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Audicoes.ActividadesComissaoOut.ActLg",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Scgt.SubComissoesGruposTrabalhoOut.CcmDscom",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.RelatoresIniciativas.RelatoresIniciativasOut.RelFase",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.RelatoresIniciativas.RelatoresIniciativasOut.IniSelLg",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Gpa.GruposParlamentaresAmizadeOut.GplSelLg",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Gpa.GruposParlamentaresAmizadeOut.CgaDtini",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Cms.ComissoesOut.CmsCargo",
            # IX Legislature - Final 2 fields for absolute complete coverage
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.RelatoresIniciativas.RelatoresIniciativasOut.IniTp",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.DlP.DelegacoesPermanentesOut.DepSelNr",
            # I Legislature - Specific fields for First Legislature
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.AutoresPareceresIncImu",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.AutoresPareceresIncImu.AutoresPareceresIncImuOut",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.AutoresPareceresIncImu.AutoresPareceresIncImuOut.ActTpDesc",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.RelatoresIniEuropeias",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.RelatoresIniEuropeias.RelatoresIniEuropeiasOut",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.RelatoresIniEuropeias.RelatoresIniEuropeiasOut.IneId",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.ParlamentoJovens",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.ParlamentoJovens.DadosDeputado",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.ParlamentoJovens.DadosDeputado.TipoReuniao",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.ParlamentoJovens.DadosDeputado.CirculoEleitoral",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Eventos",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Eventos.ActividadesComissaoOut",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Eventos.ActividadesComissaoOut.ActLoc",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Eventos.ActividadesComissaoOut.CmsNo",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Eventos.ActividadesComissaoOut.ActLg",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.DlE.DelegacoesEventuaisOut.DevTp",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Scgt.SubComissoesGruposTrabalhoOut.CmsSituacao",
            # I Legislature - Additional unmapped fields from second validation
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Cms.ComissoesOut.CmsSubCargo",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Deslocacoes.ActividadesComissaoOut.CmsAb",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.AutoresPareceresIncImu.AutoresPareceresIncImuOut.ActId",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Eventos.ActividadesComissaoOut.CmsAb",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Deslocacoes",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Deslocacoes.ActividadesComissaoOut.ActDtdes2",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Eventos.ActividadesComissaoOut.ActId",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.RelatoresContasPublicas",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Eventos.ActividadesComissaoOut.ActDtent",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Gpa.GruposParlamentaresAmizadeOut.CgaDtfim",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.RelatoresContasPublicas.RelatoresContasPublicasOut",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.RelatoresContasPublicas.RelatoresContasPublicasOut.CtaId",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.RelatoresContasPublicas.RelatoresContasPublicasOut.CtaNo",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Deslocacoes.ActividadesComissaoOut.ActId",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Deslocacoes.ActividadesComissaoOut.ActAs",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Deslocacoes.ActividadesComissaoOut.AccDtaud",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Deslocacoes.ActividadesComissaoOut.ActTp",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Deslocacoes.ActividadesComissaoOut.ActDtent",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Deslocacoes.ActividadesComissaoOut.ActNr",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Deslocacoes.ActividadesComissaoOut.ActTpdesc",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Deslocacoes.ActividadesComissaoOut.NomeEntidadeExterna",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Deslocacoes.ActividadesComissaoOut.CmsNo",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Deslocacoes.ActividadesComissaoOut.ActLg",
            # I Legislature - Third validation additional unmapped fields
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.RelatoresIniEuropeias.RelatoresIniEuropeiasOut.IneDataRelatorio",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Deslocacoes.ActividadesComissaoOut.ActDtdes1",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Eventos.ActividadesComissaoOut.ActTpdesc",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Eventos.ActividadesComissaoOut.TevTp",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Deslocacoes.ActividadesComissaoOut.ActLoc",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.ParlamentoJovens.DadosDeputado.Legislatura",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Eventos.ActividadesComissaoOut.ActSl",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Cms.ComissoesOut.CmsSituacao",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.RelatoresIniEuropeias.RelatoresIniEuropeiasOut.Leg",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Deslocacoes.ActividadesComissaoOut",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Eventos.ActividadesComissaoOut.AccDtaud",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Eventos.ActividadesComissaoOut.ActNr",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Eventos.ActividadesComissaoOut.ActTp",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Eventos.ActividadesComissaoOut.ActAs",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Eventos.ActividadesComissaoOut.NomeEntidadeExterna",
            # I Legislature - Fourth validation final unmapped fields
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.RelatoresIniEuropeias.RelatoresIniEuropeiasOut.IneReferencia",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.ParlamentoJovens.DadosDeputado.Data",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.RelatoresContasPublicas.RelatoresContasPublicasOut.ActId",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.RelatoresIniEuropeias.RelatoresIniEuropeiasOut.IneTitulo",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.RelatoresContasPublicas.RelatoresContasPublicasOut.ActAs",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.AutoresPareceresIncImu.AutoresPareceresIncImuOut.ActAs",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.ParlamentoJovens.DadosDeputado.Sessao",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.RelatoresContasPublicas.RelatoresContasPublicasOut.ActTp",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.ParlamentoJovens.DadosDeputado.Estabelecimento",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.ActividadeOut.Rel.AutoresPareceresIncImu.AutoresPareceresIncImuOut.ActSelLg",
            # I Legislature - AtividadeDeputadoIA.xml namespace variant (same data, different XML format)
            "ArrayOfAtividadeDeputado.AtividadeDeputado.deputado",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.deputado.depId",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.deputado.depCadId",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.deputado.depNomeParlamentar",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.deputado.depNomeCompleto",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.deputado.depCPId",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.deputado.depCPDes",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.deputado.legDes",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.deputado.depGP",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.deputado.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.deputado.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpId",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.deputado.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpSigla",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.deputado.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpDtInicio",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.deputado.depGP.pt_ar_wsgode_objectos_DadosSituacaoGP.gpDtFim",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.deputado.depSituacao",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.deputado.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoDeputado",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.deputado.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoDeputado.sioDes",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.deputado.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoDeputado.sioDtInicio",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.deputado.depSituacao.pt_ar_wsgode_objectos_DadosSituacaoDeputado.sioDtFim",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.rel",
            # I Legislature - AtividadeDeputadoIA.xml comprehensive namespace variants for all activity sections
            # Initiatives (Ini) - namespace variant
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.ini",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.ini.pt_gov_ar_wsar_objectos_IniciativasOut",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.ini.pt_gov_ar_wsar_objectos_IniciativasOut.iniId",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.ini.pt_gov_ar_wsar_objectos_IniciativasOut.iniNr",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.ini.pt_gov_ar_wsar_objectos_IniciativasOut.iniSelLg",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.ini.pt_gov_ar_wsar_objectos_IniciativasOut.iniSelNr",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.ini.pt_gov_ar_wsar_objectos_IniciativasOut.iniTi",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.ini.pt_gov_ar_wsar_objectos_IniciativasOut.iniTp",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.ini.pt_gov_ar_wsar_objectos_IniciativasOut.iniTpdesc",
            # Interventions (Intev) - namespace variant
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.intev",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.intev.pt_gov_ar_wsar_objectos_IntervencoesOut",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.intev.pt_gov_ar_wsar_objectos_IntervencoesOut.intId",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.intev.pt_gov_ar_wsar_objectos_IntervencoesOut.intSu",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.intev.pt_gov_ar_wsar_objectos_IntervencoesOut.pubDar",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.intev.pt_gov_ar_wsar_objectos_IntervencoesOut.pubDtreu",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.intev.pt_gov_ar_wsar_objectos_IntervencoesOut.pubLg",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.intev.pt_gov_ar_wsar_objectos_IntervencoesOut.pubNr",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.intev.pt_gov_ar_wsar_objectos_IntervencoesOut.pubSl",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.intev.pt_gov_ar_wsar_objectos_IntervencoesOut.pubTp",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.intev.pt_gov_ar_wsar_objectos_IntervencoesOut.tinDs",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.intev.pt_gov_ar_wsar_objectos_IntervencoesOut.intTe",
            # Parliamentary Activities (ActP) - namespace variant
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.actP",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.actP.pt_gov_ar_wsar_objectos_ActividadesParlamentaresOut",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.actP.pt_gov_ar_wsar_objectos_ActividadesParlamentaresOut.actId",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.actP.pt_gov_ar_wsar_objectos_ActividadesParlamentaresOut.actNr",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.actP.pt_gov_ar_wsar_objectos_ActividadesParlamentaresOut.actTp",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.actP.pt_gov_ar_wsar_objectos_ActividadesParlamentaresOut.actTpdesc",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.actP.pt_gov_ar_wsar_objectos_ActividadesParlamentaresOut.actSelLg",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.actP.pt_gov_ar_wsar_objectos_ActividadesParlamentaresOut.actSelNr",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.actP.pt_gov_ar_wsar_objectos_ActividadesParlamentaresOut.actDtent",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.actP.pt_gov_ar_wsar_objectos_ActividadesParlamentaresOut.actDtdeb",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.actP.pt_gov_ar_wsar_objectos_ActividadesParlamentaresOut.actAs",
            # Rapporteurs (Rel) - namespace variant
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.rel.relatoresIniciativas",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.rel.relatoresIniciativas.pt_gov_ar_wsar_objectos_RelatoresIniciativasOut",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.rel.relatoresIniciativas.pt_gov_ar_wsar_objectos_RelatoresIniciativasOut.iniId",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.rel.relatoresIniciativas.pt_gov_ar_wsar_objectos_RelatoresIniciativasOut.iniNr",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.rel.relatoresIniciativas.pt_gov_ar_wsar_objectos_RelatoresIniciativasOut.accDtrel",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.rel.relatoresIniciativas.pt_gov_ar_wsar_objectos_RelatoresIniciativasOut.iniTi",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.rel.relatoresIniciativas.pt_gov_ar_wsar_objectos_RelatoresIniciativasOut.iniSelLg",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.rel.relatoresIniciativas.pt_gov_ar_wsar_objectos_RelatoresIniciativasOut.relFase",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.rel.relatoresIniciativas.pt_gov_ar_wsar_objectos_RelatoresIniciativasOut.iniTp",
            # I Legislature - AtividadeDeputadoII.xml additional namespace variants
            # Legislative Deputy Data (DadosLegisDeputado) - namespace variant
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.dadosLegisDeputado",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.dadosLegisDeputado.pt_gov_ar_wsar_objectos_DadosLegisDeputado",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.dadosLegisDeputado.pt_gov_ar_wsar_objectos_DadosLegisDeputado.nome",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.dadosLegisDeputado.pt_gov_ar_wsar_objectos_DadosLegisDeputado.dpl_grpar",
            "ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList.pt_gov_ar_wsar_objectos_ActividadeOut.dadosLegisDeputado.pt_gov_ar_wsar_objectos_DadosLegisDeputado.dpl_lg",
        }

    def validate_and_map(
        self, xml_root: ET.Element, file_info: Dict, strict_mode: bool = False
    ) -> Dict:
        """Map deputy activities to database with ACTUAL XML structure - STORES REAL DATA"""
        # Store for use in nested methods
        self.file_info = file_info

        results = {"records_processed": 0, "records_imported": 0, "errors": []}

        # Validate schema coverage according to strict mode
        self.validate_schema_coverage(xml_root, file_info, strict_mode)

        # Extract legislatura from filename using comprehensive pattern
        filename = os.path.basename(file_info["file_path"])
        
        # Use same comprehensive list as enhanced_base_mapper.py - includes IA, IB sub-periods
        sorted_legislatures = [
            "CONSTITUINTE", "Cons", "XVII", "XVI", "XV", "XIV", "XIII", "XII", "XI", 
            "VIII", "VII", "VI", "IV", "III", "IB", "IA", "II", "IX", "X", "V", "I"
        ]
        
        legislatura_sigla = None
        for legislature in sorted_legislatures:
            pattern = rf"AtividadeDeputado{legislature}\.xml$"
            if re.search(pattern, filename, re.IGNORECASE):
                legislatura_sigla = legislature
                break
        
        # Normalize "Cons" abbreviation to full "CONSTITUINTE" for database consistency
        if legislatura_sigla == "Cons":
            legislatura_sigla = "CONSTITUINTE"
                
        if not legislatura_sigla:
            raise ValueError(
                f"Cannot extract legislature from filename: {filename}. Data integrity violation - cannot generate artificial legislature"
            )

        # Process each deputy's activities - ACTUAL XML STRUCTURE
        for atividade_deputado in xml_root.findall(".//AtividadeDeputado"):
            try:
                success = self._process_deputy_real_structure(
                    atividade_deputado,
                    legislatura_sigla,
                    file_info["file_path"],
                    strict_mode,
                )
                results["records_processed"] += 1
                if success:
                    results["records_imported"] += 1
            except Exception as e:
                error_msg = f"Deputy activity processing error: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
                results["records_processed"] += 1
                if strict_mode:
                    raise SchemaError(f"Processing failed in strict mode: {error_msg}")

        return results

    def _process_deputy_real_structure(
        self,
        atividade_deputado: ET.Element,
        legislatura_sigla: str,
        xml_file_path: str,
        strict_mode: bool = False,
    ) -> bool:
        """Process deputy activities with REAL XML structure and store in our new models"""
        try:
            # Get deputy information from ACTUAL XML structure
            # Handle both capitalized (Deputado) and lowercase (deputado) variants
            deputado = atividade_deputado.find("Deputado")
            if deputado is None:
                deputado = atividade_deputado.find(
                    "deputado"
                )  # AtividadeDeputadoIA.xml variant
            if deputado is None:
                logger.warning("No Deputado/deputado section found")
                return False

            # Extract deputy basic information - ACTUAL field names
            dep_id_text = self._get_text_value(
                deputado, "DepId"
            ) or self._get_text_value(deputado, "depId")
            dep_cad_id_text = self._get_text_value(
                deputado, "DepCadId"
            ) or self._get_text_value(deputado, "depCadId")
            dep_nome = self._get_text_value(
                deputado, "DepNomeParlamentar"
            ) or self._get_text_value(deputado, "depNomeParlamentar")

            # Convert deputy IDs to integers (handles "16572.0" -> 16572)
            dep_id = self._safe_int(dep_id_text)
            dep_cad_id = self._safe_int(dep_cad_id_text)

            # Find or create deputado record in our database using base class method
            dep_nome_completo = self._get_text_value(
                deputado, "DepNomeCompleto"
            ) or self._get_text_value(deputado, "depNomeCompleto")
            deputado_record = self._get_or_create_deputado(
                dep_id, dep_cad_id, dep_nome, dep_nome_completo,
                xml_context=deputado  # CRITICAL: Pass XML context for LegDes extraction
            )
            if not deputado_record:
                logger.warning("Could not create/find deputado record")
                return False

            # Create AtividadeDeputado record using our new models
            # Pass the Deputado's UUID (deputado_record.id), not the XML integer ID (dep_id)
            atividade_deputado_id = self._create_atividade_deputado(
                deputado_record.id, dep_cad_id, legislatura_sigla, deputado
            )

            if not atividade_deputado_id:
                return False

            # Process AtividadeDeputadoList - REAL XML structure
            atividade_list = atividade_deputado.find("AtividadeDeputadoList")
            if atividade_list is not None:
                atividade_list_id = self._create_atividade_deputado_list(
                    atividade_deputado_id
                )

                # Process ActividadeOut - REAL XML structure
                actividade_out = atividade_list.find("ActividadeOut")
                if actividade_out is not None:
                    actividade_out_id = self._create_actividade_out(
                        atividade_list_id, actividade_out
                    )

                    # Process nested elements
                    self._process_dados_legis_deputado(
                        actividade_out, actividade_out_id
                    )
                    self._process_audiencias(actividade_out, actividade_out_id)
                    self._process_audicoes(actividade_out, actividade_out_id)
                    self._process_initiatives(actividade_out, atividade_deputado_id)
                    self._process_interventions(actividade_out, actividade_out_id)

                    # Process IX Legislature features
                    self._process_parliamentary_activities(
                        actividade_out, actividade_out_id
                    )
                    self._process_friendship_groups(actividade_out, actividade_out_id)
                    self._process_permanent_delegations(
                        actividade_out, actividade_out_id
                    )
                    self._process_occasional_delegations(
                        actividade_out, actividade_out_id
                    )
                    self._process_requirements(actividade_out, actividade_out_id)
                    self._process_subcommittees_working_groups(
                        actividade_out, actividade_out_id
                    )
                    self._process_petition_rapporteurs(
                        actividade_out, actividade_out_id
                    )
                    self._process_initiative_rapporteurs(
                        actividade_out, actividade_out_id
                    )
                    self._process_committees(actividade_out, actividade_out_id)

                    # I Legislature specific processing
                    self._process_autores_pareceres_inc_imu(
                        actividade_out, actividade_out_id
                    )
                    self._process_relatores_ini_europeias(
                        actividade_out, actividade_out_id
                    )
                    self._process_parlamento_jovens(actividade_out, actividade_out_id)
                    self._process_eventos(actividade_out, actividade_out_id)
                    self._process_deslocacoes(actividade_out, actividade_out_id)
                    self._process_relatores_contas_publicas(
                        actividade_out, actividade_out_id
                    )

            # Process deputy situations - REAL XML structure
            self._process_deputy_situacoes_real(
                deputado, atividade_deputado_id, strict_mode
            )

            return True

        except Exception as e:
            logger.error(f"Error in real structure deputy processing: {e}")
            return False

    # _get_or_create_deputado method now inherited from enhanced base mapper

    def _create_atividade_deputado(
        self,
        deputado_id,  # UUID from Deputado record
        dep_cad_id: int,
        legislatura_sigla: str,
        deputado_elem: ET.Element,
    ):
        """Create AtividadeDeputado record using SQLAlchemy ORM"""
        try:
            leg_des = self._get_text_value(deputado_elem, "LegDes")

            atividade_deputado = AtividadeDeputado(
                id=uuid.uuid4(),
                deputado_id=deputado_id, dep_cad_id=dep_cad_id, leg_des=leg_des
            )

            self._add_with_tracking(atividade_deputado)
            # UUID id is generated client-side for immediate availability

            return atividade_deputado.id

        except Exception as e:
            logger.error(f"Error creating atividade deputado record: {e}")
            logger.error("Data integrity issue detected during processing")

            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            raise RuntimeError("Data integrity issue detected during processing")
            return None

    def _create_atividade_deputado_list(
        self, atividade_deputado_id: int
    ) -> Optional[int]:
        """Create AtividadeDeputadoList record using SQLAlchemy ORM"""
        try:
            atividade_list = AtividadeDeputadoList(
                id=uuid.uuid4(),
                atividade_deputado_id=atividade_deputado_id
            )

            self._add_with_tracking(atividade_list)
            # UUID id is generated client-side for immediate availability

            return atividade_list.id

        except Exception as e:
            logger.error(f"Error creating atividade deputado list record: {e}")
            logger.error("Data integrity issue detected during processing")

            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            raise RuntimeError("Data integrity issue detected during processing")
            return None

    def _create_actividade_out(
        self, atividade_list_id: int, actividade_out_elem: ET.Element
    ) -> Optional[int]:
        """Create ActividadeOut record using SQLAlchemy ORM"""
        try:
            rel_text = self._get_text_value(actividade_out_elem, "Rel")

            actividade_out = ActividadeOut(
                id=uuid.uuid4(),
                atividade_list_id=atividade_list_id, rel=rel_text
            )

            self._add_with_tracking(actividade_out)
            # UUID id is generated client-side for immediate availability

            return actividade_out.id

        except Exception as e:
            logger.error(f"Error creating actividade out record: {e}")
            logger.error("Data integrity issue detected during processing")

            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            raise RuntimeError("Data integrity issue detected during processing")
            return None

    def _process_dados_legis_deputado(
        self, actividade_out: ET.Element, actividade_out_id: int
    ):
        """Process DadosLegisDeputado using SQLAlchemy ORM"""
        try:
            dados_legis_section = actividade_out.find("DadosLegisDeputado")
            if dados_legis_section is not None:
                for dados_legis in dados_legis_section.findall("DadosLegisDeputado"):
                    nome = self._get_text_value(dados_legis, "Nome")
                    dpl_grpar = self._get_text_value(dados_legis, "Dpl_grpar")
                    dpl_lg = self._get_text_value(dados_legis, "Dpl_lg")

                    dados_legis_obj = DadosLegisDeputado(
                        actividade_out_id=actividade_out_id,
                        nome=nome,
                        dpl_grpar=dpl_grpar,
                        dpl_lg=dpl_lg,
                    )

                    self._add_with_tracking(dados_legis_obj)


        except Exception as e:
            logger.error(f"Error processing dados legis deputado: {e}")
            logger.error("Data integrity issue detected during processing")

            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            raise RuntimeError("Data integrity issue detected during processing")

    def _process_audiencias(self, actividade_out: ET.Element, actividade_out_id: int):
        """Process Audiencias using SQLAlchemy ORM"""
        try:
            audiencias_section = actividade_out.find("Audiencias")
            if audiencias_section is not None:
                # Create audiencia record
                audiencia = ActividadeAudiencia(
                    id=uuid.uuid4(),
                    actividade_out_id=actividade_out_id
                )

                self._add_with_tracking(audiencia)
                # UUID id is generated client-side for immediate availability

                # Process ActividadesComissaoOut within Audiencias
                for comissao_out in audiencias_section.findall(
                    "ActividadesComissaoOut"
                ):
                    # Extract IX Legislature fields
                    act_id = self._safe_int(self._get_text_value(comissao_out, "ActId"))
                    act_as = self._get_text_value(comissao_out, "ActAs")
                    act_dtent = self._get_text_value(comissao_out, "ActDtent")
                    acc_dtaud = self._get_text_value(comissao_out, "AccDtaud")
                    act_tp = self._get_text_value(comissao_out, "ActTp")
                    act_tpdesc = self._get_text_value(comissao_out, "ActTpdesc")
                    act_nr = self._get_text_value(comissao_out, "ActNr")
                    act_lg = self._get_text_value(comissao_out, "ActLg")
                    nome_entidade_externa = self._get_text_value(
                        comissao_out, "NomeEntidadeExterna"
                    )
                    cms_no = self._get_text_value(comissao_out, "CmsNo")
                    cms_ab = self._get_text_value(comissao_out, "CmsAb")

                    comissao_out_obj = ActividadesComissaoOut(
                        id=uuid.uuid4(),
                        audiencia_id=audiencia.id,
                        act_id=act_id,
                        act_as=act_as,
                        act_dtent=act_dtent,
                        acc_dtaud=acc_dtaud,
                        act_tp=act_tp,
                        act_tpdesc=act_tpdesc,
                        act_nr=act_nr,
                        act_lg=act_lg,
                        nome_entidade_externa=nome_entidade_externa,
                        cms_no=cms_no,
                        cms_ab=cms_ab,
                    )
                    self._add_with_tracking(comissao_out_obj)


        except Exception as e:
            logger.error(f"Error processing audiencias: {e}")
            logger.error("Data integrity issue detected during processing")

            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            raise RuntimeError("Data integrity issue detected during processing")

    def _process_audicoes(self, actividade_out: ET.Element, actividade_out_id: int):
        """Process Audicoes using SQLAlchemy ORM"""
        try:
            audicoes_section = actividade_out.find("Audicoes")
            if audicoes_section is not None:
                # Create audicao record
                audicao = ActividadeAudicao(
                    id=uuid.uuid4(),
                    actividade_out_id=actividade_out_id
                )

                self._add_with_tracking(audicao)
                # UUID id is generated client-side for immediate availability

                # Process ActividadesComissaoOut within Audicoes
                for comissao_out in audicoes_section.findall("ActividadesComissaoOut"):
                    # Extract IX Legislature fields
                    act_id = self._safe_int(self._get_text_value(comissao_out, "ActId"))
                    act_as = self._get_text_value(comissao_out, "ActAs")
                    act_dtent = self._get_text_value(comissao_out, "ActDtent")
                    acc_dtaud = self._get_text_value(comissao_out, "AccDtaud")
                    act_tp = self._get_text_value(comissao_out, "ActTp")
                    act_tpdesc = self._get_text_value(comissao_out, "ActTpdesc")
                    act_nr = self._get_text_value(comissao_out, "ActNr")
                    nome_entidade_externa = self._get_text_value(
                        comissao_out, "NomeEntidadeExterna"
                    )
                    cms_no = self._get_text_value(comissao_out, "CmsNo")

                    comissao_out_obj = ActividadesComissaoOut(
                        id=uuid.uuid4(),
                        audicao_id=audicao.id,
                        act_id=act_id,
                        act_as=act_as,
                        act_dtent=act_dtent,
                        acc_dtaud=acc_dtaud,
                        act_tp=act_tp,
                        act_tpdesc=act_tpdesc,
                        act_nr=act_nr,
                        nome_entidade_externa=nome_entidade_externa,
                        cms_no=cms_no,
                    )
                    self._add_with_tracking(comissao_out_obj)


        except Exception as e:
            logger.error(f"Error processing audicoes: {e}")
            logger.error("Data integrity issue detected during processing")

            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            raise RuntimeError("Data integrity issue detected during processing")

    def _process_initiatives(
        self, actividade_out: ET.Element, atividade_deputado_id: int
    ):
        """Process deputy initiatives (IniciativasOut structure)

        Fields processed (VALIDATED: Constituinte, I Legislature - identical definitions):
        - iniId: Initiative identifier
        - iniNr: Initiative number
        - iniTp: Initiative type (references TipodeIniciativa)
        - iniTpdesc: Initiative type description
        - iniSelLg: Initiative legislature
        - iniSelNr: Legislative session
        - iniTi: Initiative title

        Field definitions confirmed consistent across validated legislatures.
        """
        try:
            # Import the model here to avoid circular imports
            from database.models import DeputyInitiative

            ini_section = actividade_out.find("Ini")
            if ini_section is not None:
                # Process each IniciativasOut within Ini
                for iniciativa in ini_section.findall("IniciativasOut"):
                    # Extract initiative fields
                    ini_id = self._safe_int(self._get_text_value(iniciativa, "IniId"))
                    ini_nr = self._get_text_value(iniciativa, "IniNr")
                    ini_sel_lg = self._get_text_value(iniciativa, "IniSelLg")
                    ini_sel_nr = self._get_text_value(iniciativa, "IniSelNr")
                    ini_ti = self._get_text_value(iniciativa, "IniTi")
                    ini_tp = self._get_text_value(iniciativa, "IniTp")
                    ini_tpdesc = self._get_text_value(iniciativa, "IniTpdesc")

                    # Import even without ID or number - use placeholders
                    if not ini_id and not ini_nr:
                        logger.debug(
                            "Missing initiative ID and number - importing with placeholders"
                        )
                        if not ini_id or not ini_nr:
                            raise ValueError(
                                f"Missing required initiative fields: IniId='{ini_id}', IniNr='{ini_nr}'. Data integrity violation - cannot generate artificial IDs"
                            )

                    # Create DeputyInitiative record
                    initiative = DeputyInitiative(
                        id=uuid.uuid4(),
                        deputy_activity_id=atividade_deputado_id,
                        id_iniciativa=ini_id,
                        numero=ini_nr,
                        tipo=ini_ti,
                        desc_tipo=ini_tpdesc,
                        legislatura=ini_sel_lg,
                        sessao=ini_sel_nr,
                    )

                    self._add_with_tracking(initiative)


        except Exception as e:
            logger.error(f"Error processing initiatives: {e}")
            logger.error("Data integrity issue detected during processing")

            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            raise RuntimeError("Data integrity issue detected during processing")

    def _process_interventions(
        self, actividade_out: ET.Element, actividade_out_id: int
    ):
        """Process deputy interventions (IntervencoesOut structure)

        Fields processed (VALIDATED: Constituinte, I Legislature - identical definitions):
        - intId: Intervention identifier
        - intTe: Intervention summary
        - intSu: Intervention summary
        - pubDtreu: Meeting publication date
        - pubTp: Publication type (references TipodePublicacao)
        - pubSup: Publication supplement
        - pubLg: Legislature
        - pubSl: Legislative session
        - pubNr: Publication number
        - tinDs: Intervention type
        - pubDar: Assembly of the Republic Diary number

        Field definitions confirmed consistent across validated legislatures.
        """
        try:
            intev_section = actividade_out.find("Intev")
            if intev_section is not None:
                # Create ActividadeIntervencao record
                actividade_intervencao = ActividadeIntervencao(
                    id=uuid.uuid4(),
                    actividade_out_id=actividade_out_id
                )

                self._add_with_tracking(actividade_intervencao)
                # UUID id is generated client-side for immediate availability

                # Process each IntervencoesOut within Intev
                for intervencao in intev_section.findall("IntervencoesOut"):
                    # Extract intervention fields
                    int_id = self._safe_int(self._get_text_value(intervencao, "IntId"))
                    int_su = self._get_text_value(intervencao, "IntSu")
                    int_te = self._get_text_value(intervencao, "IntTe")
                    pub_dar = self._get_text_value(intervencao, "PubDar")
                    pub_dtreu_str = self._get_text_value(intervencao, "PubDtreu")
                    pub_dtreu = (
                        self._parse_date(pub_dtreu_str) if pub_dtreu_str else None
                    )
                    pub_lg = self._get_text_value(intervencao, "PubLg")
                    pub_nr = self._safe_int(self._get_text_value(intervencao, "PubNr"))
                    pub_sl = self._get_text_value(intervencao, "PubSl")
                    pub_tp = self._get_text_value(intervencao, "PubTp")
                    tin_ds = self._get_text_value(intervencao, "TinDs")

                    # Create ActividadeIntervencaoOut record
                    intervencao_out = ActividadeIntervencaoOut(
                        id=uuid.uuid4(),
                        actividade_intervencao_id=actividade_intervencao.id,
                        int_id=int_id,
                        int_su=int_su,
                        int_te=int_te,
                        pub_dar=pub_dar,
                        pub_dtreu=pub_dtreu,
                        pub_lg=pub_lg,
                        pub_nr=pub_nr,
                        pub_sl=pub_sl,
                        pub_tp=pub_tp,
                        tin_ds=tin_ds,
                    )

                    self._add_with_tracking(intervencao_out)


        except Exception as e:
            logger.error(f"Error processing interventions: {e}")
            logger.error("Data integrity issue detected during processing")

            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            raise RuntimeError("Data integrity issue detected during processing")

    def _process_deputy_situacoes_real(
        self,
        deputado: ET.Element,
        atividade_deputado_id: int,
        strict_mode: bool = False,
    ):
        """Process deputy situations using SQLAlchemy ORM"""
        try:
            # Handle both DepSituacao and depSituacao variants
            dep_situacao = deputado.find("DepSituacao")
            if dep_situacao is None:
                dep_situacao = deputado.find(
                    "depSituacao"
                )  # AtividadeDeputadoIA.xml variant

            if dep_situacao is not None:
                # Create deputado_situacao record
                deputado_situacao = DeputadoSituacao(
                    id=uuid.uuid4(),
                    atividade_deputado_id=atividade_deputado_id
                )

                self._add_with_tracking(deputado_situacao)
                # UUID id is generated client-side for immediate availability

                # Process each DadosSituacaoDeputado (regular format)
                for situacao in dep_situacao.findall("DadosSituacaoDeputado"):
                    sio_des = self._get_text_value(situacao, "SioDes")
                    sio_dt_inicio = self._parse_date(
                        self._get_text_value(situacao, "SioDtInicio")
                    )
                    sio_dt_fim = self._parse_date(
                        self._get_text_value(situacao, "SioDtFim")
                    )

                    dados_situacao = DadosSituacaoDeputado(
                        id=uuid.uuid4(),
                        deputado_situacao_id=deputado_situacao.id,
                        sio_des=sio_des,
                        sio_dt_inicio=sio_dt_inicio,
                        sio_dt_fim=sio_dt_fim,
                    )

                    self._add_with_tracking(dados_situacao)

                # Also handle namespace variant pt_ar_wsgode_objectos_DadosSituacaoDeputado
                for situacao in dep_situacao.findall(
                    "pt_ar_wsgode_objectos_DadosSituacaoDeputado"
                ):
                    sio_des = self._get_text_value(
                        situacao, "sioDes"
                    )  # lowercase in namespace variant
                    sio_dt_inicio = self._parse_date(
                        self._get_text_value(situacao, "sioDtInicio")
                    )
                    sio_dt_fim = self._parse_date(
                        self._get_text_value(situacao, "sioDtFim")
                    )

                    dados_situacao = DadosSituacaoDeputado(
                        id=uuid.uuid4(),
                        deputado_situacao_id=deputado_situacao.id,
                        sio_des=sio_des,
                        sio_dt_inicio=sio_dt_inicio,
                        sio_dt_fim=sio_dt_fim,
                    )

                    self._add_with_tracking(dados_situacao)


        except Exception as e:
            logger.error(f"Error processing deputy situacoes: {e}")
            logger.error("Data integrity issue detected during processing")

            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            raise RuntimeError("Data integrity issue detected during processing")
            if strict_mode:
                raise SchemaError(
                    f"Deputy situations processing failed in strict mode: {e}"
                )

    def _process_parliamentary_activities(
        self, actividade_out: ET.Element, actividade_out_id: int
    ):
        """Process IX Legislature Parliamentary Activities (ActP)"""
        try:
            actp_section = actividade_out.find("ActP")
            if actp_section is not None:
                # Create parliamentary activities record
                atividades_parlamentares = ActividadesParlamentares(
                    id=uuid.uuid4(),
                    actividade_out_id=actividade_out_id
                )

                self._add_with_tracking(atividades_parlamentares)
                # UUID id is generated client-side for immediate availability

                # Process each ActividadesParlamentaresOut
                for atividade in actp_section.findall("ActividadesParlamentaresOut"):
                    act_id = self._safe_int(self._get_text_value(atividade, "ActId"))
                    act_nr = self._get_text_value(atividade, "ActNr")
                    act_tp = self._get_text_value(atividade, "ActTp")
                    act_tpdesc = self._get_text_value(atividade, "ActTpdesc")
                    act_sel_lg = self._get_text_value(atividade, "ActSelLg")
                    act_sel_nr = self._get_text_value(atividade, "ActSelNr")
                    act_dtent = self._get_text_value(atividade, "ActDtent")
                    act_dtdeb_str = self._get_text_value(atividade, "ActDtdeb")
                    act_dtdeb = (
                        self._parse_datetime(act_dtdeb_str) if act_dtdeb_str else None
                    )
                    act_as = self._get_text_value(atividade, "ActAs")

                    atividade_out_obj = ActividadesParlamentaresOut(
                        id=uuid.uuid4(),
                        atividades_parlamentares_id=atividades_parlamentares.id,
                        act_id=act_id,
                        act_nr=act_nr,
                        act_tp=act_tp,
                        act_tpdesc=act_tpdesc,
                        act_sel_lg=act_sel_lg,
                        act_sel_nr=act_sel_nr,
                        act_dtent=act_dtent,
                        act_dtdeb=act_dtdeb,
                        act_as=act_as,
                    )

                    self._add_with_tracking(atividade_out_obj)


        except Exception as e:
            logger.error(f"Error processing parliamentary activities: {e}")
            logger.error("Data integrity issue detected during processing")

            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            raise RuntimeError("Data integrity issue detected during processing")

    def _process_friendship_groups(
        self, actividade_out: ET.Element, actividade_out_id: int
    ):
        """Process IX Legislature Friendship Groups (Gpa)"""
        try:
            gpa_section = actividade_out.find("Gpa")
            if gpa_section is not None:
                # Create friendship groups record
                grupos_parlamentares_amizade = GruposParlamentaresAmizade(
                    id=uuid.uuid4(),
                    actividade_out_id=actividade_out_id
                )

                self._add_with_tracking(grupos_parlamentares_amizade)
                # UUID id is generated client-side for immediate availability

                # Process each GruposParlamentaresAmizadeOut
                for grupo in gpa_section.findall("GruposParlamentaresAmizadeOut"):
                    gpl_id = self._safe_int(self._get_text_value(grupo, "GplId"))
                    gpl_no = self._get_text_value(grupo, "GplNo")
                    gpl_sel_lg = self._get_text_value(grupo, "GplSelLg")
                    cga_crg = self._get_text_value(grupo, "CgaCrg")
                    cga_dtini = self._get_text_value(grupo, "CgaDtini")
                    cga_dtfim = self._get_text_value(grupo, "CgaDtfim")

                    grupo_out = GruposParlamentaresAmizadeOut(
                        id=uuid.uuid4(),
                        grupos_parlamentares_amizade_id=grupos_parlamentares_amizade.id,
                        gpl_id=gpl_id,
                        gpl_no=gpl_no,
                        gpl_sel_lg=gpl_sel_lg,
                        cga_crg=cga_crg,
                        cga_dtini=cga_dtini,
                        cga_dtfim=cga_dtfim,
                    )

                    self._add_with_tracking(grupo_out)


        except Exception as e:
            logger.error(f"Error processing friendship groups: {e}")
            logger.error("Data integrity issue detected during processing")

            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            raise RuntimeError("Data integrity issue detected during processing")

    def _process_permanent_delegations(
        self, actividade_out: ET.Element, actividade_out_id: int
    ):
        """Process IX Legislature Permanent Delegations (DlP)"""
        try:
            dlp_section = actividade_out.find("DlP")
            if dlp_section is not None:
                # Create permanent delegations record
                delegacoes_permanentes = DelegacoesPermanentes(
                    id=uuid.uuid4(),
                    actividade_out_id=actividade_out_id
                )

                self._add_with_tracking(delegacoes_permanentes)
                # UUID id is generated client-side for immediate availability

                # Process each DelegacoesPermanentesOut
                for delegacao in dlp_section.findall("DelegacoesPermanentesOut"):
                    dep_id = self._safe_int(self._get_text_value(delegacao, "DepId"))
                    dep_no = self._get_text_value(delegacao, "DepNo")
                    dep_sel_lg = self._get_text_value(delegacao, "DepSelLg")
                    dep_sel_nr = self._get_text_value(delegacao, "DepSelNr")
                    cde_crg = self._get_text_value(delegacao, "CdeCrg")

                    delegacao_out = DelegacoesPermanentesOut(
                        id=uuid.uuid4(),
                        delegacoes_permanentes_id=delegacoes_permanentes.id,
                        dep_id=dep_id,
                        dep_no=dep_no,
                        dep_sel_lg=dep_sel_lg,
                        dep_sel_nr=dep_sel_nr,
                        cde_crg=cde_crg,
                    )

                    self._add_with_tracking(delegacao_out)
                    # UUID id is generated client-side for immediate availability

                    # Process meetings (DepReunioes.ReunioesDelegacoesPermanentes)
                    reunioes_section = delegacao.find("DepReunioes")
                    if reunioes_section is not None:
                        for reuniao in reunioes_section.findall(
                            "ReunioesDelegacoesPermanentes"
                        ):
                            ren_dt_ini = self._get_text_value(reuniao, "RenDtIni")
                            ren_loc = self._get_text_value(reuniao, "RenLoc")
                            ren_dt_fim = self._get_text_value(reuniao, "RenDtFim")
                            ren_ti = self._get_text_value(reuniao, "RenTi")

                            reuniao_obj = ReunioesDelegacoesPermanentes(
                                id=uuid.uuid4(),
                                delegacoes_permanentes_out_id=delegacao_out.id,
                                ren_dt_ini=ren_dt_ini,
                                ren_loc=ren_loc,
                                ren_dt_fim=ren_dt_fim,
                                ren_ti=ren_ti,
                            )

                            self._add_with_tracking(reuniao_obj)


        except Exception as e:
            logger.error(f"Error processing permanent delegations: {e}")
            logger.error("Data integrity issue detected during processing")

            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            raise RuntimeError("Data integrity issue detected during processing")

    def _process_occasional_delegations(
        self, actividade_out: ET.Element, actividade_out_id: int
    ):
        """Process IX Legislature Occasional Delegations (DlE)"""
        try:
            dle_section = actividade_out.find("DlE")
            if dle_section is not None:
                # Create occasional delegations record
                delegacoes_eventuais = DelegacoesEventuais(
                    id=uuid.uuid4(),
                    actividade_out_id=actividade_out_id
                )

                self._add_with_tracking(delegacoes_eventuais)
                # UUID id is generated client-side for immediate availability

                # Process each DelegacoesEventuaisOut
                for delegacao in dle_section.findall("DelegacoesEventuaisOut"):
                    dev_id = self._safe_int(self._get_text_value(delegacao, "DevId"))
                    dev_no = self._get_text_value(delegacao, "DevNo")
                    dev_tp = self._get_text_value(
                        delegacao, "DevTp"
                    )  # I Legislature field
                    dev_dtini = self._get_text_value(delegacao, "DevDtini")
                    dev_dtfim = self._get_text_value(delegacao, "DevDtfim")
                    dev_sel_nr = self._get_text_value(delegacao, "DevSelNr")
                    dev_sel_lg = self._get_text_value(delegacao, "DevSelLg")
                    dev_loc = self._get_text_value(delegacao, "DevLoc")

                    delegacao_out = DelegacoesEventuaisOut(
                        id=uuid.uuid4(),
                        delegacoes_eventuais_id=delegacoes_eventuais.id,
                        dev_id=dev_id,
                        dev_no=dev_no,
                        dev_tp=dev_tp,
                        dev_dtini=dev_dtini,
                        dev_dtfim=dev_dtfim,
                        dev_sel_nr=dev_sel_nr,
                        dev_sel_lg=dev_sel_lg,
                        dev_loc=dev_loc,
                    )

                    self._add_with_tracking(delegacao_out)


        except Exception as e:
            logger.error(f"Error processing occasional delegations: {e}")
            logger.error("Data integrity issue detected during processing")

            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            raise RuntimeError("Data integrity issue detected during processing")

    def _process_requirements(self, actividade_out: ET.Element, actividade_out_id: int):
        """Process deputy requirements (RequerimentosOut structure)

        Fields processed (VALIDATED: Constituinte, I Legislature - identical definitions):
        - reqId: Requirement identifier
        - reqNr: Requirement number
        - reqTp: Requirement type (references TipodeRequerimento)
        - reqLg: Requirement legislature
        - reqSl: Legislative session
        - reqAs: Requirement subject
        - reqDt: Requirement date
        - reqPerTp: Document type - requirement/question

        Field definitions confirmed consistent across validated legislatures.
        """
        try:
            req_section = actividade_out.find("Req")
            if req_section is not None:
                # Create requirements record
                requerimentos_ativ_dep = RequerimentosAtivDep(
                    id=uuid.uuid4(),
                    actividade_out_id=actividade_out_id
                )

                self._add_with_tracking(requerimentos_ativ_dep)
                # UUID id is generated client-side for immediate availability

                # Process each RequerimentosAtivDepOut
                for requerimento in req_section.findall("RequerimentosAtivDepOut"):
                    req_id = self._safe_int(self._get_text_value(requerimento, "ReqId"))
                    req_nr = self._get_text_value(requerimento, "ReqNr")
                    req_tp = self._get_text_value(requerimento, "ReqTp")
                    req_lg = self._get_text_value(requerimento, "ReqLg")
                    req_sl = self._get_text_value(requerimento, "ReqSl")
                    req_as = self._get_text_value(requerimento, "ReqAs")
                    req_dt_str = self._get_text_value(requerimento, "ReqDt")
                    req_dt = self._parse_datetime(req_dt_str) if req_dt_str else None
                    req_per_tp = self._get_text_value(requerimento, "ReqPerTp")

                    requerimento_out = RequerimentosAtivDepOut(
                        id=uuid.uuid4(),
                        requerimentos_ativ_dep_id=requerimentos_ativ_dep.id,
                        req_id=req_id,
                        req_nr=req_nr,
                        req_tp=req_tp,
                        req_lg=req_lg,
                        req_sl=req_sl,
                        req_as=req_as,
                        req_dt=req_dt,
                        req_per_tp=req_per_tp,
                    )

                    self._add_with_tracking(requerimento_out)


        except Exception as e:
            logger.error(f"Error processing requirements: {e}")
            logger.error("Data integrity issue detected during processing")

            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            raise RuntimeError("Data integrity issue detected during processing")

    def _process_subcommittees_working_groups(
        self, actividade_out: ET.Element, actividade_out_id: int
    ):
        """Process subcommittees and working groups (SubComissoesGruposTrabalhoOut structure)

        Fields processed based on Constituinte legislature documentation:
        - scmComLg: Subcommittee/working group legislature
        - ccmDscom: Subcommittee/working group description
        - scmCd: Committee code
        - scmComCd: Subcommittee/working group code
        - cmsCargo: Position in committee
        - cmsSubCargo: Sub-position in committee
        - cmsSituacao: Status in subcommittee/working group (substitute/effective)

        NOTE: Field meanings may vary for other legislatures
        """
        try:
            scgt_section = actividade_out.find("Scgt")
            if scgt_section is not None:
                # Create sub-committees/working groups record
                subcomissoes_grupos_trabalho = SubComissoesGruposTrabalho(
                    id=uuid.uuid4(),
                    actividade_out_id=actividade_out_id
                )

                self._add_with_tracking(subcomissoes_grupos_trabalho)
                # UUID id is generated client-side for immediate availability

                # Process each SubComissoesGruposTrabalhoOut
                for subcomissao in scgt_section.findall(
                    "SubComissoesGruposTrabalhoOut"
                ):
                    scm_cd = self._get_text_value(subcomissao, "ScmCd")
                    scm_com_cd = self._get_text_value(subcomissao, "ScmComCd")
                    ccm_dscom = self._get_text_value(subcomissao, "CcmDscom")
                    cms_situacao = self._get_text_value(
                        subcomissao, "CmsSituacao"
                    )  # I Legislature field
                    cms_cargo = self._get_text_value(subcomissao, "CmsCargo")
                    scm_com_lg = self._get_text_value(subcomissao, "ScmComLg")

                    subcomissao_out = SubComissoesGruposTrabalhoOut(
                        id=uuid.uuid4(),
                        subcomissoes_grupos_trabalho_id=subcomissoes_grupos_trabalho.id,
                        scm_cd=scm_cd,
                        scm_com_cd=scm_com_cd,
                        ccm_dscom=ccm_dscom,
                        cms_situacao=cms_situacao,
                        cms_cargo=cms_cargo,
                        scm_com_lg=scm_com_lg,
                    )

                    self._add_with_tracking(subcomissao_out)


        except Exception as e:
            logger.error(f"Error processing sub-committees/working groups: {e}")
            logger.error("Data integrity issue detected during processing")

            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            raise RuntimeError("Data integrity issue detected during processing")

    def _process_petition_rapporteurs(
        self, actividade_out: ET.Element, actividade_out_id: int
    ):
        """Process IX Legislature Petition Rapporteurs (Rel.RelatoresPeticoes)"""
        try:
            rel_section = actividade_out.find("Rel")
            if rel_section is not None:
                relatores_peticoes_section = rel_section.find("RelatoresPeticoes")
                if relatores_peticoes_section is not None:
                    # Create petition rapporteurs record
                    relatores_peticoes = RelatoresPeticoes(
                        id=uuid.uuid4(),
                        actividade_out_id=actividade_out_id
                    )

                    self._add_with_tracking(relatores_peticoes)
                    # UUID id is generated client-side for immediate availability

                    # Process each RelatoresPeticoesOut
                    for relator in relatores_peticoes_section.findall(
                        "RelatoresPeticoesOut"
                    ):
                        pec_dtrelf = self._get_text_value(relator, "PecDtrelf")
                        pet_id = self._safe_int(self._get_text_value(relator, "PetId"))
                        pet_nr = self._get_text_value(relator, "PetNr")
                        pet_aspet = self._get_text_value(relator, "PetAspet")
                        pet_sel_lg_pk = self._get_text_value(relator, "PetSelLgPk")
                        pet_sel_nr_pk = self._get_text_value(relator, "PetSelNrPk")

                        relator_out = RelatoresPeticoesOut(
                            id=uuid.uuid4(),
                            relatores_peticoes_id=relatores_peticoes.id,
                            pec_dtrelf=pec_dtrelf,
                            pet_id=pet_id,
                            pet_nr=pet_nr,
                            pet_aspet=pet_aspet,
                            pet_sel_lg_pk=pet_sel_lg_pk,
                            pet_sel_nr_pk=pet_sel_nr_pk,
                        )

                        self._add_with_tracking(relator_out)


        except Exception as e:
            logger.error(f"Error processing petition rapporteurs: {e}")
            logger.error("Data integrity issue detected during processing")

            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            raise RuntimeError("Data integrity issue detected during processing")

    def _process_initiative_rapporteurs(
        self, actividade_out: ET.Element, actividade_out_id: int
    ):
        """Process IX Legislature Initiative Rapporteurs (Rel.RelatoresIniciativas)"""
        try:
            rel_section = actividade_out.find("Rel")
            if rel_section is not None:
                # Look for RelatoresIniciativas
                ini_section = rel_section.find("RelatoresIniciativas")
                if ini_section is not None:
                    # Create initiative rapporteurs record
                    relatores_iniciativas = RelatoresIniciativas(
                        id=uuid.uuid4(),
                        actividade_out_id=actividade_out_id
                    )

                    self._add_with_tracking(relatores_iniciativas)
                    # UUID id is generated client-side for immediate availability

                    # Process each RelatoresIniciativasOut
                    for relator in ini_section.findall("RelatoresIniciativasOut"):
                        ini_id = self._safe_int(self._get_text_value(relator, "IniId"))
                        ini_nr = self._get_text_value(relator, "IniNr")
                        ini_tp = self._get_text_value(relator, "IniTp")
                        ini_sel_lg = self._get_text_value(relator, "IniSelLg")
                        acc_dtrel = self._get_text_value(relator, "AccDtrel")
                        rel_fase = self._get_text_value(relator, "RelFase")
                        ini_ti = self._get_text_value(relator, "IniTi")

                        relator_out = RelatoresIniciativasOut(
                            id=uuid.uuid4(),
                            relatores_iniciativas_id=relatores_iniciativas.id,
                            ini_id=ini_id,
                            ini_nr=ini_nr,
                            ini_tp=ini_tp,
                            ini_sel_lg=ini_sel_lg,
                            acc_dtrel=acc_dtrel,
                            rel_fase=rel_fase,
                            ini_ti=ini_ti,
                        )

                        self._add_with_tracking(relator_out)


        except Exception as e:
            logger.error(f"Error processing initiative rapporteurs: {e}")
            logger.error("Data integrity issue detected during processing")

            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            raise RuntimeError("Data integrity issue detected during processing")

    def _process_committees(self, actividade_out: ET.Element, actividade_out_id: int):
        """Process IX Legislature Committees (Cms)"""
        try:
            cms_section = actividade_out.find("Cms")
            if cms_section is not None:
                # Create committees record
                comissoes = Comissoes(
                    id=uuid.uuid4(),
                    actividade_out_id=actividade_out_id
                )

                self._add_with_tracking(comissoes)
                # UUID id is generated client-side for immediate availability

                # Process each ComissoesOut
                for comissao in cms_section.findall("ComissoesOut"):
                    cms_no = self._get_text_value(comissao, "CmsNo")
                    cms_cd = self._get_text_value(comissao, "CmsCd")
                    cms_lg = self._get_text_value(comissao, "CmsLg")
                    cms_cargo = self._get_text_value(comissao, "CmsCargo")
                    cms_sub_cargo = self._get_text_value(comissao, "CmsSubCargo")
                    cms_situacao = self._get_text_value(comissao, "CmsSituacao")

                    comissao_out = ComissoesOut(
                        id=uuid.uuid4(),
                        comissoes_id=comissoes.id,
                        cms_no=cms_no,
                        cms_cd=cms_cd,
                        cms_lg=cms_lg,
                        cms_cargo=cms_cargo,
                        cms_sub_cargo=cms_sub_cargo,
                        cms_situacao=cms_situacao,
                    )

                    self._add_with_tracking(comissao_out)


        except Exception as e:
            logger.error(f"Error processing committees: {e}")
            logger.error("Data integrity issue detected during processing")

            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            raise RuntimeError("Data integrity issue detected during processing")

    def _process_autores_pareceres_inc_imu(
        self, actividade_out: ET.Element, actividade_out_id: int
    ):
        """Process I Legislature Authors of Incompatibility/Immunity Opinions (Rel.AutoresPareceresIncImu)"""
        try:
            rel_section = actividade_out.find("Rel")
            if rel_section is not None:
                autores_section = rel_section.find("AutoresPareceresIncImu")
                if autores_section is not None:
                    # Create authors record
                    autores_pareceres_inc_imu = AutoresPareceresIncImu(
                        id=uuid.uuid4(),
                        actividade_out_id=actividade_out_id
                    )

                    self._add_with_tracking(autores_pareceres_inc_imu)
                    # UUID id is generated client-side for immediate availability

                    # Process each AutoresPareceresIncImuOut
                    for autor in autores_section.findall("AutoresPareceresIncImuOut"):
                        act_id = self._safe_int(self._get_text_value(autor, "ActId"))
                        act_as = self._get_text_value(autor, "ActAs")
                        act_sel_lg = self._get_text_value(autor, "ActSelLg")
                        act_tp_desc = self._get_text_value(autor, "ActTpDesc")

                        autor_out = AutoresPareceresIncImuOut(
                            id=uuid.uuid4(),
                            autores_pareceres_inc_imu_id=autores_pareceres_inc_imu.id,
                            act_id=act_id,
                            act_as=act_as,
                            act_sel_lg=act_sel_lg,
                            act_tp_desc=act_tp_desc,
                        )

                        self._add_with_tracking(autor_out)


        except Exception as e:
            logger.error(
                f"Error processing authors of incompatibility/immunity opinions: {e}"
            )
            logger.error("Data integrity issue detected during processing")

            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            raise RuntimeError("Data integrity issue detected during processing")

    def _process_relatores_ini_europeias(
        self, actividade_out: ET.Element, actividade_out_id: int
    ):
        """Process I Legislature European Initiative Rapporteurs (Rel.RelatoresIniEuropeias)"""
        try:
            rel_section = actividade_out.find("Rel")
            if rel_section is not None:
                relatores_section = rel_section.find("RelatoresIniEuropeias")
                if relatores_section is not None:
                    # Create European initiative rapporteurs record
                    relatores_ini_europeias = RelatoresIniEuropeias(
                        id=uuid.uuid4(),
                        actividade_out_id=actividade_out_id
                    )

                    self._add_with_tracking(relatores_ini_europeias)
                    # UUID id is generated client-side for immediate availability

                    # Process each RelatoresIniEuropeiasOut
                    for relator in relatores_section.findall(
                        "RelatoresIniEuropeiasOut"
                    ):
                        ine_id = self._safe_int(self._get_text_value(relator, "IneId"))
                        ine_data_relatorio = self._get_text_value(
                            relator, "IneDataRelatorio"
                        )
                        ine_referencia = self._get_text_value(relator, "IneReferencia")
                        ine_titulo = self._get_text_value(relator, "IneTitulo")
                        leg = self._get_text_value(relator, "Leg")

                        relator_out = RelatoresIniEuropeiasOut(
                            id=uuid.uuid4(),
                            relatores_ini_europeias_id=relatores_ini_europeias.id,
                            ine_id=ine_id,
                            ine_data_relatorio=ine_data_relatorio,
                            ine_referencia=ine_referencia,
                            ine_titulo=ine_titulo,
                            leg=leg,
                        )

                        self._add_with_tracking(relator_out)


        except Exception as e:
            logger.error(f"Error processing European initiative rapporteurs: {e}")
            logger.error("Data integrity issue detected during processing")

            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            raise RuntimeError("Data integrity issue detected during processing")

    def _process_parlamento_jovens(
        self, actividade_out: ET.Element, actividade_out_id: int
    ):
        """Process I Legislature Youth Parliament (ParlamentoJovens)"""
        try:
            pj_section = actividade_out.find("ParlamentoJovens")
            if pj_section is not None:
                # Create youth parliament record
                parlamento_jovens = ParlamentoJovens(
                    id=uuid.uuid4(),
                    actividade_out_id=actividade_out_id
                )

                self._add_with_tracking(parlamento_jovens)
                # UUID id is generated client-side for immediate availability

                # Process DadosDeputado
                dados_deputado = pj_section.find("DadosDeputado")
                if dados_deputado is not None:
                    tipo_reuniao = self._get_text_value(dados_deputado, "TipoReuniao")
                    circulo_eleitoral = self._get_text_value(
                        dados_deputado, "CirculoEleitoral"
                    )
                    legislatura = self._get_text_value(dados_deputado, "Legislatura")
                    data = self._get_text_value(dados_deputado, "Data")
                    sessao = self._get_text_value(dados_deputado, "Sessao")
                    estabelecimento = self._get_text_value(
                        dados_deputado, "Estabelecimento"
                    )

                    dados_out = DadosDeputadoParlamentoJovens(
                        id=uuid.uuid4(),
                        parlamento_jovens_id=parlamento_jovens.id,
                        tipo_reuniao=tipo_reuniao,
                        circulo_eleitoral=circulo_eleitoral,
                        legislatura=legislatura,
                        data=data,
                        sessao=sessao,
                        estabelecimento=estabelecimento,
                    )

                    self._add_with_tracking(dados_out)


        except Exception as e:
            logger.error(f"Error processing youth parliament: {e}")
            logger.error("Data integrity issue detected during processing")

            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            raise RuntimeError("Data integrity issue detected during processing")

    def _process_eventos(self, actividade_out: ET.Element, actividade_out_id: int):
        """Process I Legislature Events (Eventos)"""
        try:
            eventos_section = actividade_out.find("Eventos")
            if eventos_section is not None:
                # Create events record
                eventos = Eventos(
                    id=uuid.uuid4(),
                    actividade_out_id=actividade_out_id
                )

                self._add_with_tracking(eventos)
                # UUID id is generated client-side for immediate availability

                # Process each ActividadesComissaoOut within Events
                for actividade_comissao in eventos_section.findall(
                    "ActividadesComissaoOut"
                ):
                    act_id = self._safe_int(
                        self._get_text_value(actividade_comissao, "ActId")
                    )
                    act_as = self._get_text_value(actividade_comissao, "ActAs")
                    act_loc = self._get_text_value(actividade_comissao, "ActLoc")
                    act_dtent = self._get_text_value(actividade_comissao, "ActDtent")
                    act_tpdesc = self._get_text_value(actividade_comissao, "ActTpdesc")
                    act_sl = self._get_text_value(actividade_comissao, "ActSl")
                    act_tp = self._get_text_value(actividade_comissao, "ActTp")
                    act_nr = self._get_text_value(actividade_comissao, "ActNr")
                    acc_dtaud = self._get_text_value(actividade_comissao, "AccDtaud")
                    tev_tp = self._get_text_value(actividade_comissao, "TevTp")
                    nome_entidade_externa = self._get_text_value(
                        actividade_comissao, "NomeEntidadeExterna"
                    )
                    cms_no = self._get_text_value(actividade_comissao, "CmsNo")
                    cms_ab = self._get_text_value(actividade_comissao, "CmsAb")
                    act_lg = self._get_text_value(actividade_comissao, "ActLg")

                    actividade_out = ActividadesComissaoOut(
                        id=uuid.uuid4(),
                        evento_id=eventos.id,
                        act_id=act_id,
                        act_as=act_as,
                        act_loc=act_loc,
                        act_dtent=act_dtent,
                        act_tpdesc=act_tpdesc,
                        act_sl=act_sl,
                        act_tp=act_tp,
                        act_nr=act_nr,
                        acc_dtaud=acc_dtaud,
                        tev_tp=tev_tp,
                        nome_entidade_externa=nome_entidade_externa,
                        cms_no=cms_no,
                        cms_ab=cms_ab,
                        act_lg=act_lg,
                    )

                    self._add_with_tracking(actividade_out)


        except Exception as e:
            logger.error(f"Error processing events: {e}")
            logger.error("Data integrity issue detected during processing")

            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            raise RuntimeError("Data integrity issue detected during processing")

    def _process_deslocacoes(self, actividade_out: ET.Element, actividade_out_id: int):
        """Process I Legislature Displacements (Deslocacoes)"""
        try:
            deslocacoes_section = actividade_out.find("Deslocacoes")
            if deslocacoes_section is not None:
                # Create displacements record
                deslocacoes = Deslocacoes(
                    id=uuid.uuid4(),
                    actividade_out_id=actividade_out_id
                )

                self._add_with_tracking(deslocacoes)
                # UUID id is generated client-side for immediate availability

                # Process each ActividadesComissaoOut within Deslocacoes
                for actividade_comissao in deslocacoes_section.findall(
                    "ActividadesComissaoOut"
                ):
                    act_id = self._safe_int(
                        self._get_text_value(actividade_comissao, "ActId")
                    )
                    act_as = self._get_text_value(actividade_comissao, "ActAs")
                    act_loc = self._get_text_value(actividade_comissao, "ActLoc")
                    act_dtdes1 = self._get_text_value(actividade_comissao, "ActDtdes1")
                    act_dtdes2 = self._get_text_value(actividade_comissao, "ActDtdes2")
                    act_dtent = self._get_text_value(actividade_comissao, "ActDtent")
                    acc_dtaud = self._get_text_value(actividade_comissao, "AccDtaud")
                    act_tp = self._get_text_value(actividade_comissao, "ActTp")
                    act_nr = self._get_text_value(actividade_comissao, "ActNr")
                    act_tpdesc = self._get_text_value(actividade_comissao, "ActTpdesc")
                    nome_entidade_externa = self._get_text_value(
                        actividade_comissao, "NomeEntidadeExterna"
                    )
                    cms_no = self._get_text_value(actividade_comissao, "CmsNo")
                    cms_ab = self._get_text_value(actividade_comissao, "CmsAb")
                    act_lg = self._get_text_value(actividade_comissao, "ActLg")

                    actividade_out = ActividadesComissaoOut(
                        id=uuid.uuid4(),
                        deslocacao_id=deslocacoes.id,
                        act_id=act_id,
                        act_as=act_as,
                        act_loc=act_loc,
                        act_dtdes1=act_dtdes1,
                        act_dtdes2=act_dtdes2,
                        act_dtent=act_dtent,
                        acc_dtaud=acc_dtaud,
                        act_tp=act_tp,
                        act_nr=act_nr,
                        act_tpdesc=act_tpdesc,
                        nome_entidade_externa=nome_entidade_externa,
                        cms_no=cms_no,
                        cms_ab=cms_ab,
                        act_lg=act_lg,
                    )

                    self._add_with_tracking(actividade_out)


        except Exception as e:
            logger.error(f"Error processing displacements: {e}")
            logger.error("Data integrity issue detected during processing")

            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            raise RuntimeError("Data integrity issue detected during processing")

    def _process_relatores_contas_publicas(
        self, actividade_out: ET.Element, actividade_out_id: int
    ):
        """Process I Legislature Public Accounts Rapporteurs (Rel.RelatoresContasPublicas)"""
        try:
            rel_section = actividade_out.find("Rel")
            if rel_section is not None:
                rcp_section = rel_section.find("RelatoresContasPublicas")
                if rcp_section is not None:
                    relatores_contas_publicas = RelatoresContasPublicas(
                        id=uuid.uuid4(),
                        actividade_out_id=actividade_out_id
                    )
                    self._add_with_tracking(relatores_contas_publicas)
                    # UUID id is generated client-side for immediate availability

                    for relator in rcp_section.findall("RelatoresContasPublicasOut"):
                        act_id = self._safe_int(self._get_text_value(relator, "ActId"))
                        act_as = self._get_text_value(relator, "ActAs")
                        act_tp = self._get_text_value(relator, "ActTp")
                        cta_id = self._safe_int(self._get_text_value(relator, "CtaId"))
                        cta_no = self._get_text_value(relator, "CtaNo")

                        relator_out = RelatoresContasPublicasOut(
                            id=uuid.uuid4(),
                            relatores_contas_publicas_id=relatores_contas_publicas.id,
                            act_id=act_id,
                            act_as=act_as,
                            act_tp=act_tp,
                            cta_id=cta_id,
                            cta_no=cta_no,
                        )
                        self._add_with_tracking(relator_out)
        except Exception as e:
            logger.error(f"Error processing public accounts rapporteurs: {e}")
            logger.error("Data integrity issue detected during processing")

            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            raise RuntimeError("Data integrity issue detected during processing")

    def _parse_datetime(self, datetime_str: str) -> Optional[object]:
        """Parse datetime string to Python datetime object"""
        if not datetime_str:
            return None

        try:
            from datetime import datetime

            # Try ISO format with time: 2004-12-09 00:00:00.0
            if re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", datetime_str):
                # Remove milliseconds if present
                clean_str = datetime_str.split(".")[0]
                return datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")

            # Try date-only format
            if re.match(r"\d{4}-\d{2}-\d{2}", datetime_str):
                return datetime.strptime(datetime_str, "%Y-%m-%d")

        except (ValueError, IndexError) as e:
            logger.warning(f"Could not parse datetime: {datetime_str} - {e}")

        return None

    def __del__(self):
        """Cleanup SQLAlchemy session"""
        if hasattr(self, "session"):
            self.session.close()

    # Utility methods

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

    def _process_dep_cargo(self, deputado_elem: ET.Element, deputado_id: int):
        """Process DepCargo (deputy positions) using SQLAlchemy ORM"""
        try:
            dep_cargo_elem = deputado_elem.find("DepCargo")
            if dep_cargo_elem is not None:
                # Create DepCargo record
                dep_cargo = DepCargo(
                    id=uuid.uuid4(),
                    deputado_id=deputado_id
                )
                self._add_with_tracking(dep_cargo)
                # UUID id is generated client-side for immediate availability

                # Process DadosCargoDeputado elements
                dados_cargo_elem = dep_cargo_elem.find(
                    "pt_ar_wsgode_objectos_DadosCargoDeputado"
                )
                if dados_cargo_elem is not None:
                    car_des = self._get_text_value(dados_cargo_elem, "carDes")
                    car_id = self._safe_int(
                        self._get_text_value(dados_cargo_elem, "carId")
                    )
                    car_dt_inicio_str = self._get_text_value(
                        dados_cargo_elem, "carDtInicio"
                    )
                    car_dt_inicio = (
                        self._parse_date(car_dt_inicio_str)
                        if car_dt_inicio_str
                        else None
                    )

                    dados_cargo = DadosCargoDeputado(
                        id=uuid.uuid4(),
                        dep_cargo_id=dep_cargo.id,
                        car_des=car_des,
                        car_id=car_id,
                        car_dt_inicio=car_dt_inicio,
                    )

                    self._add_with_tracking(dados_cargo)


        except Exception as e:
            logger.error(f"Error processing DepCargo: {e}")
            logger.error("Data integrity issue detected during processing")

            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            raise RuntimeError("Data integrity issue detected during processing")
