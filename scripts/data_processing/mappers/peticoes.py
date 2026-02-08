"""
Comprehensive Parliamentary Petitions Mapper
============================================

Enhanced schema mapper for parliamentary petition files (Peticoes<Legislatura>.xml).
Based on Peticoes_DetalhePesquisaPeticoesOut specification from official Parliament documentation.

Imports EVERY SINGLE FIELD and structure from the XML including:

Core Petition Data (Peticoes_DetalhePesquisaPeticoesOut):
- petId: Petition identifier and primary key
- petNr: Sequential petition number within legislature
- petLeg: Legislature designation (Roman numeral)
- petSel: Legislative session number
- petAssunto: Petition subject/topic description
- petSituacao: Current processing status
- petNrAssinaturas: Number of petition signatures
- petDataEntrada: Entry date into Parliament system
- petActividadeId: Associated parliamentary activity identifier
- petAutor: Petition author/submitter information
- dataDebate: Date when petition was debated

Committee Processing (Peticoes_ComissoesPetOut):
- Complete committee assignment and workflow tracking
- Admissibility decisions with dates and status
- Committee transfers and transitional handling
- Archive and reactivation lifecycle management
- Multiple committee handling across different legislatures

Related Structures:
- RelatoresOut: Committee reporters with appointment/cessation dates
- RelatoriosFinaisOut: Final reports with voting outcomes using VotacaoOut structure
- DocsOut: Document management with multiple document types
- IntervencoesOut: Parliamentary interventions and debate contributions
- PublicacoesOut: Publications using TipodePublicacao enum for type standardization
- TipodeReuniao: Meeting type enum for committee sessions (8 types: AG, AS, AU, CO, CR, GA, IE, PP)

Maps to comprehensive database schema with full relational structure and complete audit trail.
"""

import xml.etree.ElementTree as ET
import os
import re
import uuid
from datetime import datetime
from typing import Dict, Optional, Set, List
import logging

from .enhanced_base_mapper import EnhancedSchemaMapper, SchemaError

# For backward compatibility
SchemaMapper = EnhancedSchemaMapper

# Import our models
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from database.models import (
    PeticaoParlamentar, PeticaoPublicacao, PeticaoComissao, PeticaoRelator,
    PeticaoRelatorioFinal, PeticaoRelatorioFinalPublicacao, PeticaoDocumento, 
    PeticaoIntervencao, PeticaoOrador, PeticaoOradorPublicacao, PeticaoAudiencia, 
    PeticaoPedidoInformacao, PeticaoPedidoReiteracao, PeticaoPedidoEsclarecimento,
    PeticaoLink, Legislatura
)

logger = logging.getLogger(__name__)


class PeticoesMapper(SchemaMapper):
    """
    Comprehensive schema mapper for parliamentary petition files
    
    Processes Peticoes<Legislatura>.xml files using the Peticoes_DetalhePesquisaPeticoesOut
    specification learned from official Parliament documentation.
    
    Key Features:
    - Complete petition lifecycle tracking from entry to final resolution
    - Multi-committee handling with admissibility workflow
    - Integration with existing TipodeReuniao and TipodePublicacao enums
    - Comprehensive document and intervention management
    - Full audit trail with dates and status transitions
    
    Inherits from EnhancedSchemaMapper for:
    - Standardized XML processing methods (_get_text_value, _get_int_value, _get_boolean_value)
    - Legislature extraction and management
    - Database session handling with integrity controls
    - Schema validation and error handling
    """
    
    def __init__(self, session, import_status_record=None):
        # Accept SQLAlchemy session directly (passed by unified importer)
        super().__init__(session, import_status_record=import_status_record)
    
    def get_expected_fields(self) -> Set[str]:
        """
        Complete field list based on Peticoes_DetalhePesquisaPeticoesOut specification
        from official Parliament documentation.
        
        Uses full XML hierarchy paths to avoid field name conflicts across different
        nested structures (committees, documents, interventions, voting).
        """
        return {
            # Root elements (both legacy and current format support)
            'ArrayOfPeticaoOut',
            'ArrayOfPeticaoOut.PeticaoOut',
            'Peticoes_DetalhePesquisaPeticoesOut',
            
            # Core petition fields from Peticoes_DetalhePesquisaPeticoesOut
            'ArrayOfPeticaoOut.PeticaoOut.PetId',           # petId: Petition identifier
            'ArrayOfPeticaoOut.PeticaoOut.PetNr',           # petNr: Petition number
            'ArrayOfPeticaoOut.PeticaoOut.PetLeg',          # petLeg: Legislature designation
            'ArrayOfPeticaoOut.PeticaoOut.PetSel',          # petSel: Legislative session
            'ArrayOfPeticaoOut.PeticaoOut.PetAssunto',      # petAssunto: Petition subject
            'ArrayOfPeticaoOut.PeticaoOut.PetSituacao',     # petSituacao: Current status
            'ArrayOfPeticaoOut.PeticaoOut.PetNrAssinaturas', # petNrAssinaturas: Signature count
            'ArrayOfPeticaoOut.PeticaoOut.PetDataEntrada',  # petDataEntrada: Entry date
            'ArrayOfPeticaoOut.PeticaoOut.PetActividadeId', # petActividadeId: Activity ID
            'ArrayOfPeticaoOut.PeticaoOut.PetAutor',        # petAutor: Petition author
            'ArrayOfPeticaoOut.PeticaoOut.DataDebate',      # dataDebate: Debate date
            
            # Publications - with full hierarchy
            'ArrayOfPeticaoOut.PeticaoOut.PublicacaoPeticao',
            'ArrayOfPeticaoOut.PeticaoOut.PublicacaoPeticao.pt_gov_ar_objectos_PublicacoesOut',
            'ArrayOfPeticaoOut.PeticaoOut.PublicacaoPeticao.pt_gov_ar_objectos_PublicacoesOut.pubNr',
            'ArrayOfPeticaoOut.PeticaoOut.PublicacaoPeticao.pt_gov_ar_objectos_PublicacoesOut.pubTipo',
            'ArrayOfPeticaoOut.PeticaoOut.PublicacaoPeticao.pt_gov_ar_objectos_PublicacoesOut.pubTp',
            'ArrayOfPeticaoOut.PeticaoOut.PublicacaoPeticao.pt_gov_ar_objectos_PublicacoesOut.pubLeg',
            'ArrayOfPeticaoOut.PeticaoOut.PublicacaoPeticao.pt_gov_ar_objectos_PublicacoesOut.pubSL',
            'ArrayOfPeticaoOut.PeticaoOut.PublicacaoPeticao.pt_gov_ar_objectos_PublicacoesOut.pubdt',
            'ArrayOfPeticaoOut.PeticaoOut.PublicacaoPeticao.pt_gov_ar_objectos_PublicacoesOut.pag',
            'ArrayOfPeticaoOut.PeticaoOut.PublicacaoPeticao.pt_gov_ar_objectos_PublicacoesOut.pag.string',
            'ArrayOfPeticaoOut.PeticaoOut.PublicacaoPeticao.pt_gov_ar_objectos_PublicacoesOut.idPag',
            'ArrayOfPeticaoOut.PeticaoOut.PublicacaoPeticao.pt_gov_ar_objectos_PublicacoesOut.URLDiario',
            
            'ArrayOfPeticaoOut.PeticaoOut.PublicacaoDebate',
            'ArrayOfPeticaoOut.PeticaoOut.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut',
            'ArrayOfPeticaoOut.PeticaoOut.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.pubNr',
            'ArrayOfPeticaoOut.PeticaoOut.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.pubTipo',
            'ArrayOfPeticaoOut.PeticaoOut.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.pubTp',
            'ArrayOfPeticaoOut.PeticaoOut.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.pubLeg',
            'ArrayOfPeticaoOut.PeticaoOut.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.pubSL',
            'ArrayOfPeticaoOut.PeticaoOut.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.pubdt',
            'ArrayOfPeticaoOut.PeticaoOut.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.pag',
            'ArrayOfPeticaoOut.PeticaoOut.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.pag.string',
            'ArrayOfPeticaoOut.PeticaoOut.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.idPag',
            'ArrayOfPeticaoOut.PeticaoOut.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.URLDiario',
            
            # Committee data - with full hierarchy
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.Legislatura',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.Numero',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.IdComissao',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.Nome',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.Admissibilidade',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DataAdmissibilidade',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DataEnvioPAR',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DataArquivo',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.Situacao',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DataReaberta',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DataBaixaComissao',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.Transitada',
            
            # Reporters - with full hierarchy
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.Relatores',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.Relatores.pt_gov_ar_objectos_RelatoresOut',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.Relatores.pt_gov_ar_objectos_RelatoresOut.id',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.Relatores.pt_gov_ar_objectos_RelatoresOut.nome',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.Relatores.pt_gov_ar_objectos_RelatoresOut.gp',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.Relatores.pt_gov_ar_objectos_RelatoresOut.dataNomeacao',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.Relatores.pt_gov_ar_objectos_RelatoresOut.dataCessacao',
            
            # Final reports - with full hierarchy
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosRelatorioFinal',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosRelatorioFinal.pt_gov_ar_objectos_peticoes_DadosRelatorioFinalOut',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosRelatorioFinal.pt_gov_ar_objectos_peticoes_DadosRelatorioFinalOut.data',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosRelatorioFinal.pt_gov_ar_objectos_peticoes_DadosRelatorioFinalOut.votacao',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.RelatorioFinal',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.RelatorioFinal.string',
            
            # Documents - with full hierarchy
            'ArrayOfPeticaoOut.PeticaoOut.Documentos',
            'ArrayOfPeticaoOut.PeticaoOut.Documentos.PeticaoDocsOut',
            'ArrayOfPeticaoOut.PeticaoOut.Documentos.PeticaoDocsOut.TituloDocumento',
            'ArrayOfPeticaoOut.PeticaoOut.Documentos.PeticaoDocsOut.DataDocumento',
            'ArrayOfPeticaoOut.PeticaoOut.Documentos.PeticaoDocsOut.TipoDocumento',
            'ArrayOfPeticaoOut.PeticaoOut.Documentos.PeticaoDocsOut.URL',
            
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DocumentosPeticao',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DocumentosPeticao.DocsRelatorioFinal',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DocumentosPeticao.DocsRelatorioFinal.PeticaoDocsRelatorioFinal',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DocumentosPeticao.DocsRelatorioFinal.PeticaoDocsRelatorioFinal.TituloDocumento',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DocumentosPeticao.DocsRelatorioFinal.PeticaoDocsRelatorioFinal.DataDocumento',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DocumentosPeticao.DocsRelatorioFinal.PeticaoDocsRelatorioFinal.TipoDocumento',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DocumentosPeticao.DocsRelatorioFinal.PeticaoDocsRelatorioFinal.URL',
            
            # Interventions - with full hierarchy
            'ArrayOfPeticaoOut.PeticaoOut.Intervencoes',
            'ArrayOfPeticaoOut.PeticaoOut.Intervencoes.PeticaoIntervencoesOut',
            'ArrayOfPeticaoOut.PeticaoOut.Intervencoes.PeticaoIntervencoesOut.DataReuniaoPlenaria',
            'ArrayOfPeticaoOut.PeticaoOut.Intervencoes.PeticaoIntervencoesOut.Oradores',
            'ArrayOfPeticaoOut.PeticaoOut.Intervencoes.PeticaoIntervencoesOut.Oradores.PeticaoOradoresOut',
            'ArrayOfPeticaoOut.PeticaoOut.Intervencoes.PeticaoIntervencoesOut.Oradores.PeticaoOradoresOut.FaseSessao',
            'ArrayOfPeticaoOut.PeticaoOut.Intervencoes.PeticaoIntervencoesOut.Oradores.PeticaoOradoresOut.Sumario',
            'ArrayOfPeticaoOut.PeticaoOut.Intervencoes.PeticaoIntervencoesOut.Oradores.PeticaoOradoresOut.Convidados',
            'ArrayOfPeticaoOut.PeticaoOut.Intervencoes.PeticaoIntervencoesOut.Oradores.PeticaoOradoresOut.MembrosGoverno',
            'ArrayOfPeticaoOut.PeticaoOut.Intervencoes.PeticaoIntervencoesOut.Oradores.PeticaoOradoresOut.Publicacao',
            'ArrayOfPeticaoOut.PeticaoOut.Intervencoes.PeticaoIntervencoesOut.Oradores.PeticaoOradoresOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut',
            'ArrayOfPeticaoOut.PeticaoOut.Intervencoes.PeticaoIntervencoesOut.Oradores.PeticaoOradoresOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubNr',
            'ArrayOfPeticaoOut.PeticaoOut.Intervencoes.PeticaoIntervencoesOut.Oradores.PeticaoOradoresOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubTipo',
            'ArrayOfPeticaoOut.PeticaoOut.Intervencoes.PeticaoIntervencoesOut.Oradores.PeticaoOradoresOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubTp',
            'ArrayOfPeticaoOut.PeticaoOut.Intervencoes.PeticaoIntervencoesOut.Oradores.PeticaoOradoresOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubLeg',
            'ArrayOfPeticaoOut.PeticaoOut.Intervencoes.PeticaoIntervencoesOut.Oradores.PeticaoOradoresOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubSL',
            'ArrayOfPeticaoOut.PeticaoOut.Intervencoes.PeticaoIntervencoesOut.Oradores.PeticaoOradoresOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubdt',
            'ArrayOfPeticaoOut.PeticaoOut.Intervencoes.PeticaoIntervencoesOut.Oradores.PeticaoOradoresOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.idInt',
            'ArrayOfPeticaoOut.PeticaoOut.Intervencoes.PeticaoIntervencoesOut.Oradores.PeticaoOradoresOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.URLDiario',
            'ArrayOfPeticaoOut.PeticaoOut.Intervencoes.PeticaoIntervencoesOut.Oradores.PeticaoOradoresOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pag',
            'ArrayOfPeticaoOut.PeticaoOut.Intervencoes.PeticaoIntervencoesOut.Oradores.PeticaoOradoresOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pag.string',
            
            # IX Legislature additional fields
            'ArrayOfPeticaoOut.PeticaoOut.Intervencoes.PeticaoIntervencoesOut.Oradores.PeticaoOradoresOut.Teor',
            'ArrayOfPeticaoOut.PeticaoOut.Intervencoes.PeticaoIntervencoesOut.Oradores.PeticaoOradoresOut.MembrosGoverno.governo',
            
            # Audiencias (Hearings)
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.Audiencias',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.Audiencias.pt_gov_ar_objectos_peticoes_AudienciasDiligenciasOut',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.Audiencias.pt_gov_ar_objectos_peticoes_AudienciasDiligenciasOut.data',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.Audiencias.pt_gov_ar_objectos_peticoes_AudienciasDiligenciasOut.titulo',
            
            # Audicoes (Auditions - similar to Audiencias)
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.Audicoes',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.Audicoes.pt_gov_ar_objectos_peticoes_AudienciasDiligenciasOut',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.Audicoes.pt_gov_ar_objectos_peticoes_AudienciasDiligenciasOut.data',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.Audicoes.pt_gov_ar_objectos_peticoes_AudienciasDiligenciasOut.titulo',
            
            # Pedidos de Informacao (Information Requests)
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosPedidosInformacao',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosPedidosInformacao.pt_gov_ar_objectos_peticoes_PedidosInformacaoOut',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosPedidosInformacao.pt_gov_ar_objectos_peticoes_PedidosInformacaoOut.nrOficio',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosPedidosInformacao.pt_gov_ar_objectos_peticoes_PedidosInformacaoOut.entidades',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosPedidosInformacao.pt_gov_ar_objectos_peticoes_PedidosInformacaoOut.entidades.string',
            
            # idPag field in publications
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosRelatorioFinal.pt_gov_ar_objectos_peticoes_DadosRelatorioFinalOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.idPag',
            
            # Additional IX Legislature fields found in error
            'ArrayOfPeticaoOut.PeticaoOut.PublicacaoPeticao.pt_gov_ar_objectos_PublicacoesOut.supl',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosPedidosInformacao.pt_gov_ar_objectos_peticoes_PedidosInformacaoOut.relatorioIntercalar',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosRelatorioFinal.pt_gov_ar_objectos_peticoes_DadosRelatorioFinalOut.publicacao',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosRelatorioFinal.pt_gov_ar_objectos_peticoes_DadosRelatorioFinalOut.publicacao.pt_gov_ar_objectos_PublicacoesOut',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosRelatorioFinal.pt_gov_ar_objectos_peticoes_DadosRelatorioFinalOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubTp',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosRelatorioFinal.pt_gov_ar_objectos_peticoes_DadosRelatorioFinalOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubTipo',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosRelatorioFinal.pt_gov_ar_objectos_peticoes_DadosRelatorioFinalOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.URLDiario',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosRelatorioFinal.pt_gov_ar_objectos_peticoes_DadosRelatorioFinalOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubNr',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosRelatorioFinal.pt_gov_ar_objectos_peticoes_DadosRelatorioFinalOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubLeg',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosRelatorioFinal.pt_gov_ar_objectos_peticoes_DadosRelatorioFinalOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubSL',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosRelatorioFinal.pt_gov_ar_objectos_peticoes_DadosRelatorioFinalOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pubdt',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosPedidosInformacao.pt_gov_ar_objectos_peticoes_PedidosInformacaoOut.dataResposta',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DocumentosPeticao.DocsOutros',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DocumentosPeticao.DocsOutros.PeticaoDocsOutros',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DocumentosPeticao.DocsOutros.PeticaoDocsOutros.TituloDocumento',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DocumentosPeticao.DocsOutros.PeticaoDocsOutros.DataDocumento',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DocumentosPeticao.DocsOutros.PeticaoDocsOutros.TipoDocumento',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DocumentosPeticao.DocsOutros.PeticaoDocsOutros.URL',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosPedidosInformacao.pt_gov_ar_objectos_peticoes_PedidosInformacaoOut.pedidosReiteracao',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosPedidosInformacao.pt_gov_ar_objectos_peticoes_PedidosInformacaoOut.pedidosReiteracao.pt_gov_ar_objectos_peticoes_PedidosReiteracaoOut',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosPedidosInformacao.pt_gov_ar_objectos_peticoes_PedidosInformacaoOut.pedidosReiteracao.pt_gov_ar_objectos_peticoes_PedidosReiteracaoOut.dataResposta',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosPedidosInformacao.pt_gov_ar_objectos_peticoes_PedidosInformacaoOut.pedidosReiteracao.pt_gov_ar_objectos_peticoes_PedidosReiteracaoOut.data',
            'ArrayOfPeticaoOut.PeticaoOut.PublicacaoDebate.pt_gov_ar_objectos_PublicacoesOut.supl',
            
            # Additional missing fields from second run
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosRelatorioFinal.pt_gov_ar_objectos_peticoes_DadosRelatorioFinalOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pag',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosRelatorioFinal.pt_gov_ar_objectos_peticoes_DadosRelatorioFinalOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.pag.string',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosPedidosInformacao.pt_gov_ar_objectos_peticoes_PedidosInformacaoOut.pedidosReiteracao.pt_gov_ar_objectos_peticoes_PedidosReiteracaoOut.nrOficio',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.Audiencias.pt_gov_ar_objectos_peticoes_AudienciasDiligenciasOut.id',
            'ArrayOfPeticaoOut.PeticaoOut.PetObs',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.Audicoes.pt_gov_ar_objectos_peticoes_AudienciasDiligenciasOut.id',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosPedidosInformacao.pt_gov_ar_objectos_peticoes_PedidosInformacaoOut.dataOficio',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosPedidosInformacao.pt_gov_ar_objectos_peticoes_PedidosInformacaoOut.pedidosReiteracao.pt_gov_ar_objectos_peticoes_PedidosReiteracaoOut.oficioResposta',
            'ArrayOfPeticaoOut.PeticaoOut.Intervencoes.PeticaoIntervencoesOut.Oradores.PeticaoOradoresOut.MembrosGoverno.cargo',
            'ArrayOfPeticaoOut.PeticaoOut.Intervencoes.PeticaoIntervencoesOut.Oradores.PeticaoOradoresOut.MembrosGoverno.nome',
            'ArrayOfPeticaoOut.PeticaoOut.Intervencoes.PeticaoIntervencoesOut.Oradores.PeticaoOradoresOut.Deputados',
            'ArrayOfPeticaoOut.PeticaoOut.Intervencoes.PeticaoIntervencoesOut.Oradores.PeticaoOradoresOut.Deputados.idCadastro',
            'ArrayOfPeticaoOut.PeticaoOut.Intervencoes.PeticaoIntervencoesOut.Oradores.PeticaoOradoresOut.Deputados.nome',
            
            # Final missing fields
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosPedidosInformacao.pt_gov_ar_objectos_peticoes_PedidosInformacaoOut.pedidosReiteracao.pt_gov_ar_objectos_peticoes_PedidosReiteracaoOut.dataOficio',
            'ArrayOfPeticaoOut.PeticaoOut.PublicacaoPeticao.pt_gov_ar_objectos_PublicacoesOut.pagFinalDiarioSupl',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.Relatores.pt_gov_ar_objectos_RelatoresOut.motivoCessacao',
            
            # VIII Legislature field
            'ArrayOfPeticaoOut.PeticaoOut.Intervencoes.PeticaoIntervencoesOut.Oradores.PeticaoOradoresOut.FaseDebate',
            
            # VI Legislature fields - PedidosEsclarecimento (Clarification Requests)
            'ArrayOfPeticaoOut.PeticaoOut.PedidosEsclarecimento',
            'ArrayOfPeticaoOut.PeticaoOut.PedidosEsclarecimento.pt_gov_ar_objectos_peticoes_PedidosEsclarecimentoOut',
            'ArrayOfPeticaoOut.PeticaoOut.PedidosEsclarecimento.pt_gov_ar_objectos_peticoes_PedidosEsclarecimentoOut.nrOficio',
            'ArrayOfPeticaoOut.PeticaoOut.PedidosEsclarecimento.pt_gov_ar_objectos_peticoes_PedidosEsclarecimentoOut.dataResposta',
            
            # XIII Legislature fields
            # Links
            'ArrayOfPeticaoOut.PeticaoOut.Links',
            'ArrayOfPeticaoOut.PeticaoOut.Links.PeticaoDocsOut',
            'ArrayOfPeticaoOut.PeticaoOut.Links.PeticaoDocsOut.TipoDocumento',
            'ArrayOfPeticaoOut.PeticaoOut.Links.PeticaoDocsOut.TituloDocumento',
            'ArrayOfPeticaoOut.PeticaoOut.Links.PeticaoDocsOut.DataDocumento',
            'ArrayOfPeticaoOut.PeticaoOut.Links.PeticaoDocsOut.URL',
            
            # Joint Initiatives
            'ArrayOfPeticaoOut.PeticaoOut.IniciativasConjuntas',
            'ArrayOfPeticaoOut.PeticaoOut.IniciativasConjuntas.string',
            
            # Associated Petitions
            'ArrayOfPeticaoOut.PeticaoOut.PeticoesAssociadas',
            'ArrayOfPeticaoOut.PeticaoOut.PeticoesAssociadas.string',
            
            # LinkVideo for speakers (complex structure)
            'ArrayOfPeticaoOut.PeticaoOut.Intervencoes.PeticaoIntervencoesOut.Oradores.PeticaoOradoresOut.LinkVideo',
            'ArrayOfPeticaoOut.PeticaoOut.Intervencoes.PeticaoIntervencoesOut.Oradores.PeticaoOradoresOut.LinkVideo.pt_gov_ar_objectos_peticoes_LinksVideos',
            'ArrayOfPeticaoOut.PeticaoOut.Intervencoes.PeticaoIntervencoesOut.Oradores.PeticaoOradoresOut.LinkVideo.pt_gov_ar_objectos_peticoes_LinksVideos.link',
            
            # Additional document types for committees
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DocumentosPeticao.DocsPedidoInformacoes',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DocumentosPeticao.DocsPedidoInformacoes.PeticaoDocsPedidoInformacoes',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DocumentosPeticao.DocsPedidoInformacoes.PeticaoDocsPedidoInformacoes.TituloDocumento',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DocumentosPeticao.DocsPedidoInformacoes.PeticaoDocsPedidoInformacoes.DataDocumento',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DocumentosPeticao.DocsPedidoInformacoes.PeticaoDocsPedidoInformacoes.TipoDocumento',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DocumentosPeticao.DocsPedidoInformacoes.PeticaoDocsPedidoInformacoes.URL',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DocumentosPeticao.DocsRespostaPedidoInformacoes',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DocumentosPeticao.DocsRespostaPedidoInformacoes.PeticaoDocsRespostaPedidoInformacoes',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DocumentosPeticao.DocsRespostaPedidoInformacoes.PeticaoDocsRespostaPedidoInformacoes.TituloDocumento',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DocumentosPeticao.DocsRespostaPedidoInformacoes.PeticaoDocsRespostaPedidoInformacoes.DataDocumento',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DocumentosPeticao.DocsRespostaPedidoInformacoes.PeticaoDocsRespostaPedidoInformacoes.TipoDocumento',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DocumentosPeticao.DocsRespostaPedidoInformacoes.PeticaoDocsRespostaPedidoInformacoes.URL',
            
            # Additional publication field
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosRelatorioFinal.pt_gov_ar_objectos_peticoes_DadosRelatorioFinalOut.publicacao.pt_gov_ar_objectos_PublicacoesOut.obs',
            
            # Additional XIII Legislature petition fields
            'ArrayOfPeticaoOut.PeticaoOut.PetNrAssinaturasInicial',  # Initial number of signatures
            'ArrayOfPeticaoOut.PeticaoOut.Iniciativasoriginadas',  # Originated initiatives
            'ArrayOfPeticaoOut.PeticaoOut.Iniciativasoriginadas.string',
            
            # XII Legislature fields - Voting data in final reports
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosRelatorioFinal.pt_gov_ar_objectos_peticoes_DadosRelatorioFinalOut.votacao',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosRelatorioFinal.pt_gov_ar_objectos_peticoes_DadosRelatorioFinalOut.votacao.id',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosRelatorioFinal.pt_gov_ar_objectos_peticoes_DadosRelatorioFinalOut.votacao.data',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosRelatorioFinal.pt_gov_ar_objectos_peticoes_DadosRelatorioFinalOut.votacao.unanime',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosRelatorioFinal.pt_gov_ar_objectos_peticoes_DadosRelatorioFinalOut.votacao.resultado',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosRelatorioFinal.pt_gov_ar_objectos_peticoes_DadosRelatorioFinalOut.votacao.reuniao',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosRelatorioFinal.pt_gov_ar_objectos_peticoes_DadosRelatorioFinalOut.votacao.tipoReuniao',
            
            # XIV Legislature additional voting fields
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosRelatorioFinal.pt_gov_ar_objectos_peticoes_DadosRelatorioFinalOut.votacao.ausencias',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosRelatorioFinal.pt_gov_ar_objectos_peticoes_DadosRelatorioFinalOut.votacao.ausencias.string',
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosRelatorioFinal.pt_gov_ar_objectos_peticoes_DadosRelatorioFinalOut.votacao.detalhe',
            
            # XV Legislature additional voting field
            'ArrayOfPeticaoOut.PeticaoOut.DadosComissao.ComissoesPetOut.DadosRelatorioFinal.pt_gov_ar_objectos_peticoes_DadosRelatorioFinalOut.votacao.descricao',
            
            # XIV Legislature publication obs field
            'ArrayOfPeticaoOut.PeticaoOut.PublicacaoPeticao.pt_gov_ar_objectos_PublicacoesOut.obs'
        }
    
    def validate_and_map(self, xml_root: ET.Element, file_info: Dict, strict_mode: bool = False) -> Dict:
        """Map parliamentary petitions with complete structure to database"""
        results = {'records_processed': 0, 'records_imported': 0, 'errors': []}
        
        try:
            # Validate schema coverage with strict mode support
            self.validate_schema_coverage(xml_root, file_info, strict_mode)
            
            # Extract legislatura from filename or XML
            legislatura_sigla = self._extract_legislatura(file_info['file_path'], xml_root)
            legislatura = self._get_or_create_legislatura(legislatura_sigla)
            
            # Process petitions
            for petition in xml_root.findall('.//PeticaoOut'):
                try:
                    success = self._process_petition_complete(petition, legislatura)
                    results['records_processed'] += 1
                    if success:
                        results['records_imported'] += 1
                except Exception as e:
                    error_msg = f"Petition processing error: {str(e)}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
                    results['records_processed'] += 1
                    self.session.rollback()
                    if strict_mode:
                        logger.error("STRICT MODE: Exiting due to petition processing error")
                        raise SchemaError(f"Petition processing failed in strict mode: {e}")
                    continue  # Continue processing other petitions in non-strict mode
            
            # Commit all changes
            return results
            
        except Exception as e:
            error_msg = f"Critical error processing petitions: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            self.session.rollback()
            if strict_mode:
                logger.error("STRICT MODE: Exiting due to critical processing error")
                raise SchemaError(f"Critical petition processing error in strict mode: {e}")
            return results
    
    
    def _extract_string_array(self, parent: ET.Element, tag_name: str) -> Optional[str]:
        """Extract string array from XML element and return as comma-separated string"""
        element = parent.find(tag_name)
        if element is not None:
            strings = element.findall('string')
            if strings:
                return ', '.join([s.text for s in strings if s.text])
            elif element.text:
                return element.text
        return None
    
    
    def _process_petition_complete(self, petition: ET.Element, legislatura: Legislatura) -> bool:
        """Process complete petition with all structures"""
        try:
            # Extract core petition data
            pet_id = self._get_int_value(petition, 'PetId')
            pet_nr = self._get_int_value(petition, 'PetNr')
            pet_leg = self._get_text_value(petition, 'PetLeg')
            pet_sel = self._get_int_value(petition, 'PetSel')
            pet_assunto = self._get_text_value(petition, 'PetAssunto')
            pet_situacao = self._get_text_value(petition, 'PetSituacao')
            pet_nr_assinaturas = self._get_int_value(petition, 'PetNrAssinaturas')
            pet_data_entrada = self._parse_date(self._get_text_value(petition, 'PetDataEntrada'))
            pet_atividade_id = self._get_int_value(petition, 'PetActividadeId')
            pet_autor = self._get_text_value(petition, 'PetAutor')
            data_debate = self._parse_date(self._get_text_value(petition, 'DataDebate'))
            pet_obs = self._get_text_value(petition, 'PetObs')
            
            # XIII Legislature fields
            iniciativas_conjuntas = self._extract_string_array(petition, 'IniciativasConjuntas')
            peticoes_associadas = self._extract_string_array(petition, 'PeticoesAssociadas')
            pet_nr_assinaturas_inicial = self._get_int_value(petition, 'PetNrAssinaturasInicial')
            iniciativas_originadas = self._extract_string_array(petition, 'Iniciativasoriginadas')
            
            # No validation - let the import proceed and fail naturally if there are real structural issues
            # This allows us to identify and fix specific record structure problems
            
            # Check if petition already exists
            existing = None
            if pet_id:
                existing = self.session.query(PeticaoParlamentar).filter_by(pet_id=pet_id).first()
            
            if existing:
                # Update existing petition
                existing.pet_nr = pet_nr
                existing.pet_leg = pet_leg
                existing.pet_sel = pet_sel
                existing.pet_assunto = pet_assunto
                existing.pet_situacao = pet_situacao
                existing.pet_nr_assinaturas = pet_nr_assinaturas
                existing.pet_data_entrada = pet_data_entrada
                existing.pet_atividade_id = pet_atividade_id
                existing.pet_autor = pet_autor
                existing.data_debate = data_debate
                existing.pet_obs = pet_obs
                existing.iniciativas_conjuntas = iniciativas_conjuntas
                existing.peticoes_associadas = peticoes_associadas
                existing.pet_nr_assinaturas_inicial = pet_nr_assinaturas_inicial
                existing.iniciativas_originadas = iniciativas_originadas
                existing.legislatura_id = legislatura.id
                existing.updated_at = datetime.now()
            else:
                # Create new petition record
                existing = PeticaoParlamentar(
                    id=uuid.uuid4(),
                    pet_id=pet_id,
                    pet_nr=pet_nr,
                    pet_leg=pet_leg,
                    pet_sel=pet_sel,
                    pet_assunto=pet_assunto,
                    pet_situacao=pet_situacao,
                    pet_nr_assinaturas=pet_nr_assinaturas,
                    pet_data_entrada=pet_data_entrada,
                    pet_atividade_id=pet_atividade_id,
                    pet_autor=pet_autor,
                    data_debate=data_debate,
                    pet_obs=pet_obs,
                    iniciativas_conjuntas=iniciativas_conjuntas,
                    peticoes_associadas=peticoes_associadas,
                    pet_nr_assinaturas_inicial=pet_nr_assinaturas_inicial,
                    iniciativas_originadas=iniciativas_originadas,
                    legislatura_id=legislatura.id,
                    updated_at=datetime.now()
                )
                self._add_with_tracking(existing)
            
            # Process all related structures
            self._process_publicacoes(petition, existing)
            self._process_dados_comissao(petition, existing)
            self._process_documentos(petition, existing)
            self._process_intervencoes(petition, existing)
            self._process_pedidos_esclarecimento(petition, existing)
            self._process_links(petition, existing)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing petition {pet_id}: {e}")
            return False
    
    
    def _process_publicacoes(self, petition: ET.Element, peticao_obj: PeticaoParlamentar):
        """Process all publication types for petition"""
        # Clear existing publications
        for publicacao in peticao_obj.publicacoes:
            self.session.delete(publicacao)
        
        # PublicacaoPeticao
        pub_peticao = petition.find('PublicacaoPeticao')
        if pub_peticao is not None:
            for pub in pub_peticao.findall('pt_gov_ar_objectos_PublicacoesOut'):
                self._insert_publicacao(peticao_obj, pub, 'PublicacaoPeticao')
        
        # PublicacaoDebate
        pub_debate = petition.find('PublicacaoDebate')
        if pub_debate is not None:
            for pub in pub_debate.findall('pt_gov_ar_objectos_PublicacoesOut'):
                self._insert_publicacao(peticao_obj, pub, 'PublicacaoDebate')
    
    def _insert_publicacao(self, peticao_obj: PeticaoParlamentar, pub: ET.Element, tipo: str):
        """Insert publication data"""
        pub_nr = self._get_int_value(pub, 'pubNr')
        pub_tipo = self._get_text_value(pub, 'pubTipo')
        pub_tp = self._get_text_value(pub, 'pubTp')
        pub_leg = self._get_text_value(pub, 'pubLeg')
        pub_sl = self._get_int_value(pub, 'pubSL')
        pub_dt = self._parse_date(self._get_text_value(pub, 'pubdt'))
        id_pag = self._get_int_value(pub, 'idPag')
        url_diario = self._get_text_value(pub, 'URLDiario')
        supl = self._get_text_value(pub, 'supl')
        pag_final_diario_supl = self._get_text_value(pub, 'pagFinalDiarioSupl')
        obs = self._get_text_value(pub, 'obs')
        
        # Handle page numbers
        pag_text = None
        pag_elem = pub.find('pag')
        if pag_elem is not None:
            string_elems = pag_elem.findall('string')
            if string_elems:
                pag_text = ', '.join([s.text for s in string_elems if s.text])
        
        publicacao = PeticaoPublicacao(
            peticao_id=peticao_obj.id,
            tipo=tipo,
            pub_nr=pub_nr,
            pub_tipo=pub_tipo,
            pub_tp=pub_tp,
            pub_leg=pub_leg,
            pub_sl=pub_sl,
            pub_dt=pub_dt,
            pag=pag_text,
            id_pag=id_pag,
            url_diario=url_diario,
            supl=supl,
            pag_final_diario_supl=pag_final_diario_supl,
            obs=obs
        )
        self._add_with_tracking(publicacao)
    
    def _process_dados_comissao(self, petition: ET.Element, peticao_obj: PeticaoParlamentar):
        """Process committee data (can be multiple across legislaturas)"""
        # Clear existing committee data
        for comissao in peticao_obj.comissoes:
            self.session.delete(comissao)
        
        dados_comissao = petition.find('DadosComissao')
        if dados_comissao is not None:
            for comissao in dados_comissao.findall('ComissoesPetOut'):
                comissao_obj = self._process_single_comissao(comissao, peticao_obj)
                if comissao_obj:
                    self._process_comissao_details(comissao, comissao_obj)
    
    def _process_single_comissao(self, comissao: ET.Element, peticao_obj: PeticaoParlamentar) -> Optional[PeticaoComissao]:
        """Process single committee record"""
        legislatura = self._get_text_value(comissao, 'Legislatura')
        numero = self._get_int_value(comissao, 'Numero')
        id_comissao = self._get_int_value(comissao, 'IdComissao')
        nome = self._get_text_value(comissao, 'Nome')
        admissibilidade = self._get_text_value(comissao, 'Admissibilidade')
        data_admissibilidade = self._parse_date(self._get_text_value(comissao, 'DataAdmissibilidade'))
        data_envio_par = self._parse_date(self._get_text_value(comissao, 'DataEnvioPAR'))
        data_arquivo = self._parse_date(self._get_text_value(comissao, 'DataArquivo'))
        situacao = self._get_text_value(comissao, 'Situacao')
        data_reaberta = self._parse_date(self._get_text_value(comissao, 'DataReaberta'))
        data_baixa_comissao = self._parse_date(self._get_text_value(comissao, 'DataBaixaComissao'))
        transitada = self._get_text_value(comissao, 'Transitada')
        
        comissao_obj = PeticaoComissao(
            id=uuid.uuid4(),
            peticao_id=peticao_obj.id,
            legislatura=legislatura,
            numero=numero,
            id_comissao=id_comissao,
            nome=nome,
            admissibilidade=admissibilidade,
            data_admissibilidade=data_admissibilidade,
            data_envio_par=data_envio_par,
            data_arquivo=data_arquivo,
            situacao=situacao,
            data_reaberta=data_reaberta,
            data_baixa_comissao=data_baixa_comissao,
            transitada=transitada
        )

        self._add_with_tracking(comissao_obj)
        return comissao_obj
    
    def _process_comissao_details(self, comissao: ET.Element, comissao_obj: PeticaoComissao):
        """Process detailed committee structures"""
        # Reporters
        self._process_relatores(comissao, comissao_obj)
        
        # Final reports
        self._process_dados_relatorio_final(comissao, comissao_obj)
        
        # Committee documents
        self._process_documentos_comissao(comissao, comissao_obj)
        
        # Audiencias (Hearings)
        self._process_audiencias(comissao, comissao_obj)
        
        # Information requests
        self._process_pedidos_informacao(comissao, comissao_obj)
    
    def _process_relatores(self, comissao: ET.Element, comissao_obj: PeticaoComissao):
        """Process reporters for committee"""
        relatores = comissao.find('Relatores')
        if relatores is not None:
            for relator in relatores.findall('pt_gov_ar_objectos_RelatoresOut'):
                relator_id = self._get_int_value(relator, 'id')
                nome = self._get_text_value(relator, 'nome')
                gp = self._get_text_value(relator, 'gp')
                data_nomeacao = self._parse_date(self._get_text_value(relator, 'dataNomeacao'))
                data_cessacao = self._parse_date(self._get_text_value(relator, 'dataCessacao'))
                motivo_cessacao = self._get_text_value(relator, 'motivoCessacao')
                
                relator_obj = PeticaoRelator(
                    comissao_peticao_id=comissao_obj.id,
                    relator_id=relator_id,
                    nome=nome,
                    gp=gp,
                    data_nomeacao=data_nomeacao,
                    data_cessacao=data_cessacao,
                    motivo_cessacao=motivo_cessacao
                )
                self._add_with_tracking(relator_obj)
    
    def _process_dados_relatorio_final(self, comissao: ET.Element, comissao_obj: PeticaoComissao):
        """Process final report data"""
        dados_relatorio = comissao.find('DadosRelatorioFinal')
        if dados_relatorio is not None:
            for relatorio in dados_relatorio.findall('pt_gov_ar_objectos_peticoes_DadosRelatorioFinalOut'):
                data_relatorio = self._parse_date(self._get_text_value(relatorio, 'data'))
                votacao = self._get_text_value(relatorio, 'votacao')
                
                # XII/XIV Legislature voting fields
                votacao_id = None
                votacao_data = None
                votacao_unanime = None
                votacao_resultado = None
                votacao_reuniao = None
                votacao_tipo_reuniao = None
                votacao_ausencias = None
                votacao_detalhe = None
                votacao_descricao = None
                
                votacao_elem = relatorio.find('votacao')
                if votacao_elem is not None:
                    votacao_id = self._get_int_value(votacao_elem, 'id')
                    votacao_data = self._parse_date(self._get_text_value(votacao_elem, 'data'))
                    unanime_text = self._get_text_value(votacao_elem, 'unanime')
                    if unanime_text:
                        votacao_unanime = unanime_text.lower() in ('true', '1', 'yes', 'sim')
                    votacao_resultado = self._get_text_value(votacao_elem, 'resultado')
                    votacao_reuniao = self._get_int_value(votacao_elem, 'reuniao')
                    votacao_tipo_reuniao = self._get_text_value(votacao_elem, 'tipoReuniao')
                    
                    # XIV/XV Legislature additional voting fields
                    votacao_ausencias = self._extract_string_array(votacao_elem, 'ausencias')
                    votacao_detalhe = self._get_text_value(votacao_elem, 'detalhe')
                    votacao_descricao = self._get_text_value(votacao_elem, 'descricao')
                
                relatorio_obj = PeticaoRelatorioFinal(
                    id=uuid.uuid4(),
                    comissao_peticao_id=comissao_obj.id,
                    data_relatorio=data_relatorio,
                    votacao=votacao,
                    votacao_id=votacao_id,
                    votacao_data=votacao_data,
                    votacao_unanime=votacao_unanime,
                    votacao_resultado=votacao_resultado,
                    votacao_reuniao=votacao_reuniao,
                    votacao_tipo_reuniao=votacao_tipo_reuniao,
                    votacao_ausencias=votacao_ausencias,
                    votacao_detalhe=votacao_detalhe,
                    votacao_descricao=votacao_descricao
                )
                self._add_with_tracking(relatorio_obj)
                
                # Process publicacao (IX Legislature)
                publicacao = relatorio.find('publicacao')
                if publicacao is not None:
                    pub_elem = publicacao.find('pt_gov_ar_objectos_PublicacoesOut')
                    if pub_elem is not None:
                        self._insert_relatorio_final_publicacao(relatorio_obj, pub_elem)
        
        # Process RelatorioFinal string elements
        relatorio_final = comissao.find('RelatorioFinal')
        if relatorio_final is not None:
            for string_elem in relatorio_final.findall('string'):
                relatorio_id = string_elem.text
                if relatorio_id:
                    relatorio_obj = PeticaoRelatorioFinal(
                        comissao_peticao_id=comissao_obj.id,
                        relatorio_final_id=relatorio_id
                    )
                    self._add_with_tracking(relatorio_obj)
    
    def _insert_relatorio_final_publicacao(self, relatorio_obj: PeticaoRelatorioFinal, pub: ET.Element):
        """Insert final report publication data"""
        pub_nr = self._get_int_value(pub, 'pubNr')
        pub_tipo = self._get_text_value(pub, 'pubTipo')
        pub_tp = self._get_text_value(pub, 'pubTp')
        pub_leg = self._get_text_value(pub, 'pubLeg')
        pub_sl = self._get_int_value(pub, 'pubSL')
        pub_dt = self._parse_date(self._get_text_value(pub, 'pubdt'))
        id_pag = self._get_int_value(pub, 'idPag')
        url_diario = self._get_text_value(pub, 'URLDiario')
        obs = self._get_text_value(pub, 'obs')
        
        # Handle page numbers
        pag_text = None
        pag_elem = pub.find('pag')
        if pag_elem is not None:
            string_elems = pag_elem.findall('string')
            if string_elems:
                pag_text = ', '.join([s.text for s in string_elems if s.text])
            elif pag_elem.text:
                pag_text = pag_elem.text
        
        publicacao = PeticaoRelatorioFinalPublicacao(
            relatorio_final_id=relatorio_obj.id,
            pub_nr=pub_nr,
            pub_tipo=pub_tipo,
            pub_tp=pub_tp,
            pub_leg=pub_leg,
            pub_sl=pub_sl,
            pub_dt=pub_dt,
            pag=pag_text,
            id_pag=id_pag,
            url_diario=url_diario,
            obs=obs
        )
        self._add_with_tracking(publicacao)
    
    def _process_documentos_comissao(self, comissao: ET.Element, comissao_obj: PeticaoComissao):
        """Process committee-specific documents"""
        documentos_peticao = comissao.find('DocumentosPeticao')
        if documentos_peticao is not None:
            # DocsRelatorioFinal
            docs_relatorio = documentos_peticao.find('DocsRelatorioFinal')
            if docs_relatorio is not None:
                for doc in docs_relatorio.findall('PeticaoDocsRelatorioFinal'):
                    self._insert_documento(None, comissao_obj, doc, 'DocsRelatorioFinal')
            
            # DocsOutros (IX Legislature)
            docs_outros = documentos_peticao.find('DocsOutros')
            if docs_outros is not None:
                for doc in docs_outros.findall('PeticaoDocsOutros'):
                    self._insert_documento(None, comissao_obj, doc, 'DocsOutros')
            
            # DocsPedidoInformacoes (XIII Legislature)
            docs_pedido_info = documentos_peticao.find('DocsPedidoInformacoes')
            if docs_pedido_info is not None:
                for doc in docs_pedido_info.findall('PeticaoDocsPedidoInformacoes'):
                    self._insert_documento(None, comissao_obj, doc, 'DocsPedidoInformacoes')
            
            # DocsRespostaPedidoInformacoes (XIII Legislature)
            docs_resposta_pedido = documentos_peticao.find('DocsRespostaPedidoInformacoes')
            if docs_resposta_pedido is not None:
                for doc in docs_resposta_pedido.findall('PeticaoDocsRespostaPedidoInformacoes'):
                    self._insert_documento(None, comissao_obj, doc, 'DocsRespostaPedidoInformacoes')
    
    def _process_audiencias(self, comissao: ET.Element, comissao_obj: PeticaoComissao):
        """Process hearings/audiencias and audicoes"""
        # Process Audiencias
        audiencias = comissao.find('Audiencias')
        if audiencias is not None:
            for audiencia in audiencias.findall('pt_gov_ar_objectos_peticoes_AudienciasDiligenciasOut'):
                audiencia_id = self._get_int_value(audiencia, 'id')
                data = self._parse_date(self._get_text_value(audiencia, 'data'))
                titulo = self._get_text_value(audiencia, 'titulo')
                
                if audiencia_id or data or titulo:
                    audiencia_obj = PeticaoAudiencia(
                        comissao_peticao_id=comissao_obj.id,
                        audiencia_id=audiencia_id,
                        data=data,
                        titulo=titulo,
                        tipo='audiencia'
                    )
                    self._add_with_tracking(audiencia_obj)
        
        # Process Audicoes (same structure as audiencias)
        audicoes = comissao.find('Audicoes')
        if audicoes is not None:
            for audicao in audicoes.findall('pt_gov_ar_objectos_peticoes_AudienciasDiligenciasOut'):
                audicao_id = self._get_int_value(audicao, 'id')
                data = self._parse_date(self._get_text_value(audicao, 'data'))
                titulo = self._get_text_value(audicao, 'titulo')
                
                if audicao_id or data or titulo:
                    audicao_obj = PeticaoAudiencia(
                        comissao_peticao_id=comissao_obj.id,
                        audiencia_id=audicao_id,
                        data=data,
                        titulo=titulo,
                        tipo='audicao'
                    )
                    self._add_with_tracking(audicao_obj)
    
    def _process_pedidos_informacao(self, comissao: ET.Element, comissao_obj: PeticaoComissao):
        """Process information requests"""
        dados_pedidos = comissao.find('DadosPedidosInformacao')
        if dados_pedidos is not None:
            for pedido in dados_pedidos.findall('pt_gov_ar_objectos_peticoes_PedidosInformacaoOut'):
                nr_oficio = self._get_text_value(pedido, 'nrOficio')
                relatorio_intercalar = self._get_text_value(pedido, 'relatorioIntercalar')
                data_resposta = self._parse_date(self._get_text_value(pedido, 'dataResposta'))
                data_oficio = self._parse_date(self._get_text_value(pedido, 'dataOficio'))
                
                # Handle entidades (can be a complex structure with strings)
                entidades_text = None
                entidades = pedido.find('entidades')
                if entidades is not None:
                    string_elems = entidades.findall('string')
                    if string_elems:
                        entidades_text = ', '.join([s.text for s in string_elems if s.text])
                    elif entidades.text:
                        entidades_text = entidades.text
                
                if nr_oficio or entidades_text or relatorio_intercalar or data_resposta or data_oficio:
                    pedido_obj = PeticaoPedidoInformacao(
                        id=uuid.uuid4(),
                        comissao_peticao_id=comissao_obj.id,
                        nr_oficio=nr_oficio,
                        entidades=entidades_text,
                        relatorio_intercalar=relatorio_intercalar,
                        data_resposta=data_resposta,
                        data_oficio=data_oficio
                    )
                    self._add_with_tracking(pedido_obj)

                    # Process pedidos de reiteracao
                    self._process_pedidos_reiteracao(pedido, pedido_obj)
    
    def _process_pedidos_reiteracao(self, pedido: ET.Element, pedido_obj: PeticaoPedidoInformacao):
        """Process reiteration requests"""
        pedidos_reiteracao = pedido.find('pedidosReiteracao')
        if pedidos_reiteracao is not None:
            for reiteracao in pedidos_reiteracao.findall('pt_gov_ar_objectos_peticoes_PedidosReiteracaoOut'):
                data = self._parse_date(self._get_text_value(reiteracao, 'data'))
                data_resposta = self._parse_date(self._get_text_value(reiteracao, 'dataResposta'))
                nr_oficio = self._get_text_value(reiteracao, 'nrOficio')
                oficio_resposta = self._get_text_value(reiteracao, 'oficioResposta')
                data_oficio = self._parse_date(self._get_text_value(reiteracao, 'dataOficio'))
                
                if data or data_resposta or nr_oficio or oficio_resposta or data_oficio:
                    reiteracao_obj = PeticaoPedidoReiteracao(
                        pedido_informacao_id=pedido_obj.id,
                        data=data,
                        data_resposta=data_resposta,
                        nr_oficio=nr_oficio,
                        oficio_resposta=oficio_resposta,
                        data_oficio=data_oficio
                    )
                    self._add_with_tracking(reiteracao_obj)
    
    def _process_documentos(self, petition: ET.Element, peticao_obj: PeticaoParlamentar):
        """Process main petition documents"""
        documentos = petition.find('Documentos')
        if documentos is not None:
            for doc in documentos.findall('PeticaoDocsOut'):
                self._insert_documento(peticao_obj, None, doc, 'Documentos')
    
    def _insert_documento(self, peticao_obj: Optional[PeticaoParlamentar], comissao_obj: Optional[PeticaoComissao], 
                         doc: ET.Element, categoria: str):
        """Insert document data"""
        titulo_documento = self._get_text_value(doc, 'TituloDocumento')
        data_documento = self._parse_date(self._get_text_value(doc, 'DataDocumento'))
        tipo_documento = self._get_text_value(doc, 'TipoDocumento')
        url = self._get_text_value(doc, 'URL')
        
        documento_obj = PeticaoDocumento(
            peticao_id=peticao_obj.id if peticao_obj else None,
            comissao_peticao_id=comissao_obj.id if comissao_obj else None,
            tipo_documento_categoria=categoria,
            titulo_documento=titulo_documento,
            data_documento=data_documento,
            tipo_documento=tipo_documento,
            url=url
        )
        self._add_with_tracking(documento_obj)
    
    def _process_intervencoes(self, petition: ET.Element, peticao_obj: PeticaoParlamentar):
        """Process interventions/debates"""
        # Clear existing interventions
        for intervencao in peticao_obj.intervencoes:
            self.session.delete(intervencao)
        
        intervencoes = petition.find('Intervencoes')
        if intervencoes is not None:
            for intervencao in intervencoes.findall('PeticaoIntervencoesOut'):
                intervencao_obj = self._process_single_intervencao(intervencao, peticao_obj)
                if intervencao_obj:
                    self._process_oradores(intervencao, intervencao_obj)
    
    def _process_single_intervencao(self, intervencao: ET.Element, peticao_obj: PeticaoParlamentar) -> Optional[PeticaoIntervencao]:
        """Process single intervention"""
        data_reuniao_plenaria = self._parse_date(self._get_text_value(intervencao, 'DataReuniaoPlenaria'))
        
        intervencao_obj = PeticaoIntervencao(
            id=uuid.uuid4(),
            peticao_id=peticao_obj.id,
            data_reuniao_plenaria=data_reuniao_plenaria
        )
        self._add_with_tracking(intervencao_obj)
        return intervencao_obj
    
    def _process_oradores(self, intervencao: ET.Element, intervencao_obj: PeticaoIntervencao):
        """Process speakers in intervention"""
        oradores = intervencao.find('Oradores')
        if oradores is not None:
            for orador in oradores.findall('PeticaoOradoresOut'):
                orador_obj = self._process_single_orador(orador, intervencao_obj)
                if orador_obj:
                    self._process_orador_publicacoes(orador, orador_obj)
    
    def _process_single_orador(self, orador: ET.Element, intervencao_obj: PeticaoIntervencao) -> Optional[PeticaoOrador]:
        """Process single speaker"""
        fase_sessao = self._get_text_value(orador, 'FaseSessao')
        sumario = self._get_text_value(orador, 'Sumario')
        convidados = self._get_text_value(orador, 'Convidados')
        membros_governo = self._get_text_value(orador, 'MembrosGoverno')
        teor = self._get_text_value(orador, 'Teor')
        fase_debate = self._get_text_value(orador, 'FaseDebate')
        
        # Handle LinkVideo complex structure (XIII Legislature)
        link_video = None
        link_video_elem = orador.find('LinkVideo')
        if link_video_elem is not None:
            # Try complex structure first
            links_videos = link_video_elem.find('pt_gov_ar_objectos_peticoes_LinksVideos')
            if links_videos is not None:
                link_video = self._get_text_value(links_videos, 'link')
            else:
                # Fallback to simple text value
                link_video = link_video_elem.text
        
        # Handle MembrosGoverno fields (IX Legislature specific)
        governo = None
        membro_governo_nome = None
        membro_governo_cargo = None
        membros_governo_elem = orador.find('MembrosGoverno')
        if membros_governo_elem is not None:
            governo = self._get_text_value(membros_governo_elem, 'governo')
            membro_governo_nome = self._get_text_value(membros_governo_elem, 'nome')
            membro_governo_cargo = self._get_text_value(membros_governo_elem, 'cargo')
        
        # Handle Deputados fields (IX Legislature specific)
        deputado_id_cadastro = None
        deputado_nome = None
        deputados_elem = orador.find('Deputados')
        if deputados_elem is not None:
            deputado_id_cadastro = self._get_int_value(deputados_elem, 'idCadastro')
            deputado_nome = self._get_text_value(deputados_elem, 'nome')
        
        orador_obj = PeticaoOrador(
            id=uuid.uuid4(),
            intervencao_id=intervencao_obj.id,
            fase_sessao=fase_sessao,
            sumario=sumario,
            convidados=convidados,
            membros_governo=membros_governo,
            governo=governo,
            membro_governo_nome=membro_governo_nome,
            membro_governo_cargo=membro_governo_cargo,
            deputado_id_cadastro=deputado_id_cadastro,
            deputado_nome=deputado_nome,
            teor=teor,
            fase_debate=fase_debate,
            link_video=link_video
        )
        self._add_with_tracking(orador_obj)
        return orador_obj
    
    def _process_pedidos_esclarecimento(self, petition: ET.Element, peticao_obj: PeticaoParlamentar):
        """Process clarification requests (VI Legislature)"""
        # Clear existing clarification requests
        for pedido in peticao_obj.pedidos_esclarecimento:
            self.session.delete(pedido)
        
        pedidos_esclarecimento = petition.find('PedidosEsclarecimento')
        if pedidos_esclarecimento is not None:
            for pedido in pedidos_esclarecimento.findall('pt_gov_ar_objectos_peticoes_PedidosEsclarecimentoOut'):
                nr_oficio = self._get_text_value(pedido, 'nrOficio')
                data_resposta = self._parse_date(self._get_text_value(pedido, 'dataResposta'))
                
                # Create clarification request if there's data
                if nr_oficio or data_resposta:
                    pedido_obj = PeticaoPedidoEsclarecimento(
                        peticao_id=peticao_obj.id,
                        nr_oficio=nr_oficio,
                        data_resposta=data_resposta
                    )
                    self._add_with_tracking(pedido_obj)
    
    def _process_links(self, petition: ET.Element, peticao_obj: PeticaoParlamentar):
        """Process links (XIII Legislature)"""
        # Clear existing links
        for link in peticao_obj.links:
            self.session.delete(link)
        
        links = petition.find('Links')
        if links is not None:
            for link in links.findall('PeticaoDocsOut'):
                tipo_documento = self._get_text_value(link, 'TipoDocumento')
                titulo_documento = self._get_text_value(link, 'TituloDocumento')
                data_documento = self._parse_date(self._get_text_value(link, 'DataDocumento'))
                url = self._get_text_value(link, 'URL')
                
                # Create link if there's data
                if any([tipo_documento, titulo_documento, data_documento, url]):
                    link_obj = PeticaoLink(
                        peticao_id=peticao_obj.id,
                        tipo_documento=tipo_documento,
                        titulo_documento=titulo_documento,
                        data_documento=data_documento,
                        url=url
                    )
                    self._add_with_tracking(link_obj)
    
    def _process_orador_publicacoes(self, orador: ET.Element, orador_obj: PeticaoOrador):
        """Process speaker publications"""
        publicacao = orador.find('Publicacao')
        if publicacao is not None:
            for pub in publicacao.findall('pt_gov_ar_objectos_PublicacoesOut'):
                pub_nr = self._get_int_value(pub, 'pubNr')
                pub_tipo = self._get_text_value(pub, 'pubTipo')
                pub_tp = self._get_text_value(pub, 'pubTp')
                pub_leg = self._get_text_value(pub, 'pubLeg')
                pub_sl = self._get_int_value(pub, 'pubSL')
                pub_dt = self._parse_date(self._get_text_value(pub, 'pubdt'))
                id_pag = self._get_int_value(pub, 'idPag')
                id_int = self._get_int_value(pub, 'idInt')
                url_diario = self._get_text_value(pub, 'URLDiario')
                
                # Handle page numbers
                pag_text = None
                pag_elem = pub.find('pag')
                if pag_elem is not None:
                    string_elems = pag_elem.findall('string')
                    if string_elems:
                        pag_text = ', '.join([s.text for s in string_elems if s.text])
                
                publicacao_obj = PeticaoOradorPublicacao(
                    orador_id=orador_obj.id,
                    pub_nr=pub_nr,
                    pub_tipo=pub_tipo,
                    pub_tp=pub_tp,
                    pub_leg=pub_leg,
                    pub_sl=pub_sl,
                    pub_dt=pub_dt,
                    pag=pag_text,
                    id_pag=id_pag,
                    id_int=id_int,
                    url_diario=url_diario
                )
                self._add_with_tracking(publicacao_obj)
    
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to ISO format"""
        if not date_str:
            return None
        
        try:
            # Handle ISO format: YYYY-MM-DD
            if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
                return date_str
            
            # Handle datetime format: DD/MM/YYYY HH:MM:SS or DD/MM/YYYY
            if ' ' in date_str:
                date_part = date_str.split(' ')[0]
            else:
                date_part = date_str
            
            # Try DD/MM/YYYY format
            if '/' in date_part:
                parts = date_part.split('/')
                if len(parts) == 3:
                    day, month, year = parts
                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            
        except (ValueError, IndexError):
            logger.warning(f"Could not parse date: {date_str}")
        
        return None
    
    # NOTE: _get_or_create_legislatura is inherited from EnhancedSchemaMapper (with caching)
    # NOTE: Roman numeral conversion uses ROMAN_TO_NUMBER from LegislatureHandlerMixin

    def close(self):
        """Close the database session"""
        if hasattr(self, 'session') and self.session:
            self.session.close()