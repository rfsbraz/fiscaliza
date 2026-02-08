"""
Approved Diplomas Mapper
========================

Schema mapper for approved diplomas files (Diplomas*.xml).
Handles parliamentary diplomas including laws, decrees, and resolutions.

Based on official Portuguese Parliament documentation from December 2017:
"Significado das Tags do Ficheiro Diplomas<Legislatura>.xml"

Supports all documented structures:
- Core diploma data (Diplomas_DetalhePesquisaDiplomasOut)
- Publications (PublicacoesOut)
- Initiatives (Iniciativas_DetalhePesquisaIniciativasOut)
- Budget/Management accounts (OrcamentoContasGerencia_OrcamentoContasGerenciaOut)
- Documents and attachments (DocsOut, anexos)

Diploma types covered (as per documentation):
Decretos Constitucionais, Decretos da Assembleia, Deliberações, Leis, 
Leis Constitucionais, Leis Orgânicas, Retificações, Regimentos, 
Regimentos da AR, Resoluções e Resoluções da AR.
"""

import xml.etree.ElementTree as ET
import os
import re
import uuid
from datetime import datetime
from typing import Dict, Optional, Set, List
import logging

from .enhanced_base_mapper import SchemaMapper, SchemaError

# Import our models
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from database.models import DiplomaAprovado, DiplomaPublicacao, DiplomaIniciativa, DiplomaOrcamContasGerencia, Legislatura

logger = logging.getLogger(__name__)


class DiplomasAprovadosMapper(SchemaMapper):
    """Schema mapper for approved diplomas files"""
    
    def __init__(self, session, import_status_record=None):
        # Accept SQLAlchemy session directly (passed by unified importer)
        super().__init__(session, import_status_record=import_status_record)
    
    def get_expected_fields(self) -> Set[str]:
        """
        Expected XML field paths based on December 2017 official documentation.
        
        Covers all documented structures from "Significado das Tags do Ficheiro Diplomas<Legislatura>.xml"
        """
        return {
            # Root elements
            'ArrayOfDiplomaOut',
            'ArrayOfDiplomaOut.DiplomaOut',
            
            # Main diploma fields (Diplomas_DetalhePesquisaDiplomasOut)
            'ArrayOfDiplomaOut.DiplomaOut.id',  # Identificador do Diploma
            'ArrayOfDiplomaOut.DiplomaOut.Id',  # Alternative casing
            'ArrayOfDiplomaOut.DiplomaOut.numero',  # Número de Diploma
            'ArrayOfDiplomaOut.DiplomaOut.Numero',  # Alternative casing
            'ArrayOfDiplomaOut.DiplomaOut.numero2',  # Complemento do Número
            'ArrayOfDiplomaOut.DiplomaOut.Numero2',  # Alternative casing
            'ArrayOfDiplomaOut.DiplomaOut.titulo',  # Título do Diploma
            'ArrayOfDiplomaOut.DiplomaOut.Titulo',  # Alternative casing
            'ArrayOfDiplomaOut.DiplomaOut.tipo',  # Tipo de Diploma
            'ArrayOfDiplomaOut.DiplomaOut.Tipo',  # Alternative casing
            'ArrayOfDiplomaOut.DiplomaOut.tp',  # Tipo de Diploma (abreviado)
            'ArrayOfDiplomaOut.DiplomaOut.Tp',  # Alternative casing
            'ArrayOfDiplomaOut.DiplomaOut.legislatura',  # Legislatura
            'ArrayOfDiplomaOut.DiplomaOut.Legislatura',  # Alternative casing
            'ArrayOfDiplomaOut.DiplomaOut.sessao',  # Sessão legislativa
            'ArrayOfDiplomaOut.DiplomaOut.Sessao',  # Alternative casing
            'ArrayOfDiplomaOut.DiplomaOut.anoCivil',  # Ano a que corresponde o Diploma
            'ArrayOfDiplomaOut.DiplomaOut.AnoCivil',  # Alternative casing
            'ArrayOfDiplomaOut.DiplomaOut.linkTexto',  # Link para o texto do diploma
            'ArrayOfDiplomaOut.DiplomaOut.LinkTexto',  # Alternative casing
            'ArrayOfDiplomaOut.DiplomaOut.observacoes',  # Observações
            'ArrayOfDiplomaOut.DiplomaOut.Observacoes',  # Alternative casing
            'ArrayOfDiplomaOut.DiplomaOut.versao',  # Versão do Diploma
            'ArrayOfDiplomaOut.DiplomaOut.Versao',  # Alternative casing
            
            # Activities (Dados das Atividades associadas)
            'ArrayOfDiplomaOut.DiplomaOut.actividades',  # Dados das Atividades associadas
            'ArrayOfDiplomaOut.DiplomaOut.Actividades',  # Alternative casing
            'ArrayOfDiplomaOut.DiplomaOut.Actividades.string',
            
            # Publication data (PublicacoesOut structure)
            'ArrayOfDiplomaOut.DiplomaOut.publicacao',  # Lista de publicações
            'ArrayOfDiplomaOut.DiplomaOut.Publicacao',  # Alternative casing
            'ArrayOfDiplomaOut.DiplomaOut.Publicacao.PublicacoesOut',
            'ArrayOfDiplomaOut.DiplomaOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut',
            'ArrayOfDiplomaOut.DiplomaOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.debateDtReu',  # Data do debate na reunião plenária
            'ArrayOfDiplomaOut.DiplomaOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.idAct',  # Identificador da Atividade
            'ArrayOfDiplomaOut.DiplomaOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.idDeb',  # Identificador do Debate
            'ArrayOfDiplomaOut.DiplomaOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.idInt',  # Identificador da Intervenção
            'ArrayOfDiplomaOut.DiplomaOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.idPag',  # Identificador da Paginação
            'ArrayOfDiplomaOut.DiplomaOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.obs',  # Observações
            'ArrayOfDiplomaOut.DiplomaOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pag',  # Páginas
            'ArrayOfDiplomaOut.DiplomaOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pag.string',
            'ArrayOfDiplomaOut.DiplomaOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pagFinalDiarioSupl',  # Página final do suplemento
            'ArrayOfDiplomaOut.DiplomaOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubdt',  # Data da Publicação
            'ArrayOfDiplomaOut.DiplomaOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubLeg',  # Legislatura da Publicação
            'ArrayOfDiplomaOut.DiplomaOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubNr',  # Número da Publicação
            'ArrayOfDiplomaOut.DiplomaOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubSL',  # Sessão legislativa da Publicação
            'ArrayOfDiplomaOut.DiplomaOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubTipo',  # Descrição do Tipo de Publicação
            'ArrayOfDiplomaOut.DiplomaOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.pubTp',  # Abreviatura do Tipo de Publicação
            'ArrayOfDiplomaOut.DiplomaOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.supl',  # Suplemento da Publicação
            'ArrayOfDiplomaOut.DiplomaOut.Publicacao.pt_gov_ar_objectos_PublicacoesOut.URLDiario',  # Link para o DAR
            
            # Initiative data (Iniciativas_DetalhePesquisaIniciativasOut structure)
            'ArrayOfDiplomaOut.DiplomaOut.iniciativas',  # Lista de iniciativas
            'ArrayOfDiplomaOut.DiplomaOut.Iniciativas',  # Alternative casing
            'ArrayOfDiplomaOut.DiplomaOut.Iniciativas.DiplomaIniciativaOut',
            'ArrayOfDiplomaOut.DiplomaOut.Iniciativas.Iniciativas_DetalhePesquisaIniciativasOut',
            # Core initiative fields
            'ArrayOfDiplomaOut.DiplomaOut.Iniciativas.DiplomaIniciativaOut.iniId',  # Identificador da Iniciativa
            'ArrayOfDiplomaOut.DiplomaOut.Iniciativas.DiplomaIniciativaOut.IniId',  # Alternative casing
            'ArrayOfDiplomaOut.DiplomaOut.Iniciativas.DiplomaIniciativaOut.iniNr',  # Número da Iniciativa
            'ArrayOfDiplomaOut.DiplomaOut.Iniciativas.DiplomaIniciativaOut.IniNr',  # Alternative casing
            'ArrayOfDiplomaOut.DiplomaOut.Iniciativas.DiplomaIniciativaOut.iniTipo',  # Tipo de Iniciativa
            'ArrayOfDiplomaOut.DiplomaOut.Iniciativas.DiplomaIniciativaOut.IniTipo',  # Alternative casing
            'ArrayOfDiplomaOut.DiplomaOut.Iniciativas.DiplomaIniciativaOut.iniTitulo',  # Título da Iniciativa
            'ArrayOfDiplomaOut.DiplomaOut.Iniciativas.DiplomaIniciativaOut.IniTitulo',  # Alternative casing
            'ArrayOfDiplomaOut.DiplomaOut.Iniciativas.DiplomaIniciativaOut.iniLinkTexto',  # Link para o texto da iniciativa
            'ArrayOfDiplomaOut.DiplomaOut.Iniciativas.DiplomaIniciativaOut.IniLinkTexto',  # Alternative casing
            'ArrayOfDiplomaOut.DiplomaOut.Iniciativas.DiplomaIniciativaOut.iniLeg',  # Legislatura da iniciativa
            'ArrayOfDiplomaOut.DiplomaOut.Iniciativas.DiplomaIniciativaOut.iniSel',  # Sessão legislativa da iniciativa
            'ArrayOfDiplomaOut.DiplomaOut.Iniciativas.DiplomaIniciativaOut.iniObs',  # Observações associadas
            'ArrayOfDiplomaOut.DiplomaOut.Iniciativas.DiplomaIniciativaOut.iniDescTipo',  # Descrição do Tipo de Iniciativa
            'ArrayOfDiplomaOut.DiplomaOut.Iniciativas.DiplomaIniciativaOut.iniEpigrafe',  # Indica se tem texto em epígrafe
            'ArrayOfDiplomaOut.DiplomaOut.Iniciativas.DiplomaIniciativaOut.iniTestaFicheiro',  # Indica se existe ficheiro
            'ArrayOfDiplomaOut.DiplomaOut.Iniciativas.DiplomaIniciativaOut.iniTextoSubst',  # Indica se tem texto de substituição
            'ArrayOfDiplomaOut.DiplomaOut.Iniciativas.DiplomaIniciativaOut.iniTextoSubstCampo',  # Texto de substituição
            
            # Attachments (anexos associados ao Diploma)
            'ArrayOfDiplomaOut.DiplomaOut.anexos',  # Anexos associados ao Diploma
            'ArrayOfDiplomaOut.DiplomaOut.Anexos',  # Alternative casing
            'ArrayOfDiplomaOut.DiplomaOut.Anexos.string',
            
            # Budget/Management Accounts (OrcamentoContasGerencia_OrcamentoContasGerenciaOut)
            'ArrayOfDiplomaOut.DiplomaOut.orcamContasGerencia',  # Lista de dados do Orçamento e Contas de Gerência
            'ArrayOfDiplomaOut.DiplomaOut.OrcamContasGerencia',  # Alternative casing
            'ArrayOfDiplomaOut.DiplomaOut.OrcamContasGerencia.OrcamentoContasGerencia_OrcamentoContasGerenciaOut',
            'ArrayOfDiplomaOut.DiplomaOut.OrcamContasGerencia.pt_gov_ar_objectos_OrcamentoContasGerencia_OrcamentoContasGerenciaOut',
            'ArrayOfDiplomaOut.DiplomaOut.OrcamContasGerencia.pt_gov_ar_objectos_OrcamentoContasGerencia_OrcamentoContasGerenciaOut.id',  # Identificador da conta de gerência
            'ArrayOfDiplomaOut.DiplomaOut.OrcamContasGerencia.pt_gov_ar_objectos_OrcamentoContasGerencia_OrcamentoContasGerenciaOut.tipo',  # Tipo de Conta de Gerência
            'ArrayOfDiplomaOut.DiplomaOut.OrcamContasGerencia.pt_gov_ar_objectos_OrcamentoContasGerencia_OrcamentoContasGerenciaOut.tp',  # Descrição do Orçamento
            'ArrayOfDiplomaOut.DiplomaOut.OrcamContasGerencia.pt_gov_ar_objectos_OrcamentoContasGerencia_OrcamentoContasGerenciaOut.titulo',  # Título da Conta de Gerência
            'ArrayOfDiplomaOut.DiplomaOut.OrcamContasGerencia.pt_gov_ar_objectos_OrcamentoContasGerencia_OrcamentoContasGerenciaOut.ano',  # Ano a que se refere o Orçamento
            'ArrayOfDiplomaOut.DiplomaOut.OrcamContasGerencia.pt_gov_ar_objectos_OrcamentoContasGerencia_OrcamentoContasGerenciaOut.leg',  # Legislatura
            'ArrayOfDiplomaOut.DiplomaOut.OrcamContasGerencia.pt_gov_ar_objectos_OrcamentoContasGerencia_OrcamentoContasGerenciaOut.SL',  # Sessão Legislativa
            'ArrayOfDiplomaOut.DiplomaOut.OrcamContasGerencia.pt_gov_ar_objectos_OrcamentoContasGerencia_OrcamentoContasGerenciaOut.anexos',  # Anexos associados a este Orçamento
            'ArrayOfDiplomaOut.DiplomaOut.OrcamContasGerencia.pt_gov_ar_objectos_OrcamentoContasGerencia_OrcamentoContasGerenciaOut.textosAprovados',  # Textos Aprovados associados
            'ArrayOfDiplomaOut.DiplomaOut.OrcamContasGerencia.pt_gov_ar_objectos_OrcamentoContasGerencia_OrcamentoContasGerenciaOut.votacao',  # Resultado da votação ao Orçamento
            'ArrayOfDiplomaOut.DiplomaOut.OrcamContasGerencia.pt_gov_ar_objectos_OrcamentoContasGerencia_OrcamentoContasGerenciaOut.dtAprovacaoCA',  # Data de aprovação pelo Conselho de Administração
            'ArrayOfDiplomaOut.DiplomaOut.OrcamContasGerencia.pt_gov_ar_objectos_OrcamentoContasGerencia_OrcamentoContasGerenciaOut.dtAgendamento',  # Data de Agendamento do Orçamento
            'ArrayOfDiplomaOut.DiplomaOut.OrcamContasGerencia.pt_gov_ar_objectos_OrcamentoContasGerencia_OrcamentoContasGerenciaOut.obs'  # Campo das observações
        }
    
    def validate_and_map(self, xml_root: ET.Element, file_info: Dict, strict_mode: bool = False) -> Dict:
        """Map approved diplomas to database"""
        results = {'records_processed': 0, 'records_imported': 0, 'errors': []}
        
        try:
            # Validate schema coverage according to strict mode
            self.validate_schema_coverage(xml_root, file_info, strict_mode)
            
            # Extract legislatura from filename or XML
            legislatura_sigla = self._extract_legislatura(file_info['file_path'], xml_root)
            legislatura = self._get_or_create_legislatura(legislatura_sigla)
        
            # Process diplomas
            for diploma in xml_root.findall('.//DiplomaOut'):
                try:
                    success = self._process_diploma(diploma, legislatura)
                    results['records_processed'] += 1
                    if success:
                        results['records_imported'] += 1
                except Exception as e:
                    error_msg = f"Diploma processing error: {str(e)}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
                    results['records_processed'] += 1
                    self.session.rollback()
                    if strict_mode:
                        logger.error("STRICT MODE: Exiting due to diploma processing error")
                        raise SchemaError(f"Diploma processing failed in strict mode: {e}")
                    continue
            
            # Commit all changes
            return results
            
        except Exception as e:
            error_msg = f"Critical error processing diplomas: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            self.session.rollback()
            raise SchemaError(f"Critical diploma processing error: {e}")
    
    
    def _process_diploma(self, diploma: ET.Element, legislatura: Legislatura) -> bool:
        """
        Process individual diploma
        
        Based on December 2017 PDF documentation field specifications:
        - Diplomas_DetalhePesquisaDiplomasOut structure
        - All documented core fields with case-insensitive extraction
        """
        try:
            # Extract basic fields (case-insensitive approach for robustness)
            diploma_id = self._get_int_value(diploma, 'Id') or self._get_int_value(diploma, 'id')
            numero = self._get_int_value(diploma, 'Numero') or self._get_int_value(diploma, 'numero')
            numero2 = self._get_text_value(diploma, 'Numero2') or self._get_text_value(diploma, 'numero2')  # Complemento do Número
            titulo = self._get_text_value(diploma, 'Titulo') or self._get_text_value(diploma, 'titulo')  # Título do Diploma
            tipo = self._get_text_value(diploma, 'Tipo') or self._get_text_value(diploma, 'tipo')  # Tipo de Diploma
            tp = self._get_text_value(diploma, 'Tp') or self._get_text_value(diploma, 'tp')  # Tipo de Diploma (abreviado)
            sessao = self._get_int_value(diploma, 'Sessao') or self._get_int_value(diploma, 'sessao')  # Sessão legislativa
            ano_civil = self._get_int_value(diploma, 'AnoCivil') or self._get_int_value(diploma, 'anoCivil')  # Ano a que corresponde o Diploma
            link_texto = self._get_text_value(diploma, 'LinkTexto') or self._get_text_value(diploma, 'linkTexto')  # Link para o texto do diploma
            observacoes = self._get_text_value(diploma, 'Observacoes') or self._get_text_value(diploma, 'observacoes')  # Observações
            versao = self._get_text_value(diploma, 'Versao') or self._get_text_value(diploma, 'versao')  # Versão do Diploma
            
            # Extract anexos (Anexos associados ao Diploma)
            anexos = self._extract_string_array(diploma, 'Anexos') or self._extract_string_array(diploma, 'anexos')
            
            # No validation - let record creation fail naturally if titulo is actually required
            
            # Check if diploma already exists
            existing = None
            if diploma_id:
                existing = self.session.query(DiplomaAprovado).filter_by(
                    diploma_id=diploma_id
                ).first()
            
            if existing:
                # Update existing record
                existing.numero = numero
                existing.numero2 = numero2
                existing.titulo = titulo
                existing.tipo = tipo
                existing.sessao = sessao
                existing.ano_civil = ano_civil
                existing.link_texto = link_texto
                existing.observacoes = observacoes
                existing.tp = tp
                existing.versao = versao
                existing.anexos = anexos
                existing.legislatura_id = legislatura.id
            else:
                # Create new diploma record
                diploma_record = DiplomaAprovado(
                    id=uuid.uuid4(),
                    diploma_id=diploma_id,
                    numero=numero,
                    numero2=numero2,
                    titulo=titulo,
                    tipo=tipo,
                    sessao=sessao,
                    ano_civil=ano_civil,
                    link_texto=link_texto,
                    observacoes=observacoes,
                    tp=tp,
                    versao=versao,
                    anexos=anexos,
                    legislatura_id=legislatura.id
                )
                self._add_with_tracking(diploma_record)
                existing = diploma_record
            
            # Process publications
            self._process_diploma_publications(diploma, existing)
            
            # Process initiatives
            self._process_diploma_initiatives(diploma, existing)
            
            # Process budget/management accounts (XIII Legislature)
            self._process_orcam_contas_gerencia(diploma, existing)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing diploma: {e}")
            return False
    
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
    
    def _map_diploma_type(self, tipo: str, tp: str) -> str:
        """Map diploma type to standard activity type"""
        if not tipo:
            return 'DIPLOMA'
        
        tipo_upper = tipo.upper()
        
        if 'LEI' in tipo_upper:
            return 'LEI'
        elif 'DECRETO' in tipo_upper:
            return 'DECRETO'
        elif 'RESOLUÇÃO' in tipo_upper or 'RESOLUCAO' in tipo_upper:
            return 'RESOLUCAO'
        elif 'DELIBERAÇÃO' in tipo_upper or 'DELIBERACAO' in tipo_upper:
            return 'DELIBERACAO'
        else:
            return 'DIPLOMA'
    
    
    # NOTE: _get_or_create_legislatura is inherited from EnhancedSchemaMapper (with caching)
    # NOTE: Roman numeral conversion uses ROMAN_TO_NUMBER from LegislatureHandlerMixin

    def _process_diploma_publications(self, diploma: ET.Element, diploma_record: DiplomaAprovado):
        """
        Process publications for diploma
        
        Based on PublicacoesOut structure from PDF documentation
        """
        # Try both casing variants for robustness
        publicacao = diploma.find('Publicacao') or diploma.find('publicacao')
        if publicacao is not None:
            # Look for publication structures with different possible names
            pub_elements = (publicacao.findall('pt_gov_ar_objectos_PublicacoesOut') + 
                          publicacao.findall('PublicacoesOut'))
            
            for pub in pub_elements:
                # Extract all documented PublicacoesOut fields
                pub_nr = self._get_int_value(pub, 'pubNr')  # Número da Publicação
                pub_tipo = self._get_text_value(pub, 'pubTipo')  # Descrição do Tipo de Publicação
                pub_tp = self._get_text_value(pub, 'pubTp')  # Abreviatura do Tipo de Publicação
                pub_leg = self._get_text_value(pub, 'pubLeg')  # Legislatura em que ocorreu a Publicação
                pub_sl = self._get_int_value(pub, 'pubSL')  # Sessão legislativa em que ocorreu a Publicação
                pub_dt = self._parse_date(self._get_text_value(pub, 'pubdt'))  # Data da Publicação
                id_pag = self._get_int_value(pub, 'idPag')  # Identificador da Paginação
                url_diario = self._get_text_value(pub, 'URLDiario')  # Link para o DAR da Publicação
                supl = self._get_text_value(pub, 'supl')  # Suplemento da Publicação
                obs = self._get_text_value(pub, 'obs')  # Observações
                pag_final_diario_supl = self._get_text_value(pub, 'pagFinalDiarioSupl')  # Página final do suplemento
                
                # Additional fields from documentation
                debate_dt_reu = self._parse_date(self._get_text_value(pub, 'debateDtReu'))  # Data do debate na reunião plenária
                id_act = self._get_int_value(pub, 'idAct')  # Identificador da Atividade associada à Publicação
                id_deb = self._get_int_value(pub, 'idDeb')  # Identificador do Debate associado à Publicação
                id_int = self._get_int_value(pub, 'idInt')  # Identificador da Intervenção associada à Publicação
                
                # Handle page numbers (can be in <pag><string> elements)
                pag_text = None
                pag_elem = pub.find('pag')
                if pag_elem is not None:
                    string_elems = pag_elem.findall('string')
                    if string_elems:
                        pag_text = ', '.join([s.text for s in string_elems if s.text])
                
                publicacao_record = DiplomaPublicacao(
                    id=uuid.uuid4(),
                    diploma_id=diploma_record.id,
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
                    obs=obs,
                    pag_final_diario_supl=pag_final_diario_supl
                )
                self._add_with_tracking(publicacao_record)
    
    def _process_diploma_initiatives(self, diploma: ET.Element, diploma_record: DiplomaAprovado):
        """
        Process initiatives for diploma
        
        Based on Iniciativas_DetalhePesquisaIniciativasOut structure from PDF documentation
        """
        # Try both casing variants
        iniciativas = diploma.find('Iniciativas') or diploma.find('iniciativas')
        if iniciativas is not None:
            # Look for initiative structures
            ini_elements = (iniciativas.findall('DiplomaIniciativaOut') + 
                          iniciativas.findall('Iniciativas_DetalhePesquisaIniciativasOut'))
            
            for ini in ini_elements:
                # Extract all documented initiative fields (case-insensitive)
                ini_nr = (self._get_int_value(ini, 'IniNr') or 
                         self._get_int_value(ini, 'iniNr'))  # Número da Iniciativa
                ini_tipo = (self._get_text_value(ini, 'IniTipo') or 
                           self._get_text_value(ini, 'iniTipo'))  # Tipo de Iniciativa
                ini_link_texto = (self._get_text_value(ini, 'IniLinkTexto') or 
                                 self._get_text_value(ini, 'iniLinkTexto'))  # Link para o texto da iniciativa
                ini_id = (self._get_int_value(ini, 'IniId') or 
                         self._get_int_value(ini, 'iniId'))  # Identificador da Iniciativa
                
                # Additional fields from comprehensive documentation
                ini_leg = self._get_text_value(ini, 'iniLeg')  # Legislatura da iniciativa
                ini_sel = self._get_int_value(ini, 'iniSel')  # Sessão legislativa da iniciativa
                ini_titulo = self._get_text_value(ini, 'iniTitulo')  # Título da Iniciativa
                ini_obs = self._get_text_value(ini, 'iniObs')  # Observações associadas
                ini_desc_tipo = self._get_text_value(ini, 'iniDescTipo')  # Descrição do Tipo de Iniciativa
                ini_epigrafe = self._get_text_value(ini, 'iniEpigrafe')  # Indica se tem texto em epígrafe
                ini_testa_ficheiro = self._get_text_value(ini, 'iniTestaFicheiro')  # Indica se existe ficheiro
                ini_texto_subst = self._get_text_value(ini, 'iniTextoSubst')  # Indica se tem texto de substituição
                ini_texto_subst_campo = self._get_text_value(ini, 'iniTextoSubstCampo')  # Texto de substituição
                
                iniciativa_record = DiplomaIniciativa(
                    id=uuid.uuid4(),
                    diploma_id=diploma_record.id,
                    ini_nr=ini_nr,
                    ini_tipo=ini_tipo,
                    ini_link_texto=ini_link_texto,
                    ini_id=ini_id
                )
                self._add_with_tracking(iniciativa_record)
    
    def _process_orcam_contas_gerencia(self, diploma: ET.Element, diploma_record: DiplomaAprovado):
        """Process budget/management accounts for diploma (XIII Legislature)"""
        orcam_contas = diploma.find('OrcamContasGerencia')
        if orcam_contas is not None:
            for orcam in orcam_contas.findall('pt_gov_ar_objectos_OrcamentoContasGerencia_OrcamentoContasGerenciaOut'):
                orcam_id = self._get_int_value(orcam, 'id')
                leg = self._get_text_value(orcam, 'leg')
                tp = self._get_text_value(orcam, 'tp')
                titulo = self._get_text_value(orcam, 'titulo')
                tipo = self._get_text_value(orcam, 'tipo')
                
                # Create record if there's meaningful data
                if any([orcam_id, leg, tp, titulo, tipo]):
                    orcam_record = DiplomaOrcamContasGerencia(
                        id=uuid.uuid4(),
                        diploma_id=diploma_record.id,
                        orcam_id=orcam_id,
                        leg=leg,
                        tp=tp,
                        titulo=titulo,
                        tipo=tipo
                    )
                    self._add_with_tracking(orcam_record)
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime"""
        if not date_str:
            return None
        try:
            # Handle ISO format: YYYY-MM-DD
            if re.match(r'\\d{4}-\\d{2}-\\d{2}', date_str):
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            # Handle datetime format: YYYY-MM-DDTHH:MM:SS
            if 'T' in date_str:
                return datetime.strptime(date_str.split('T')[0], '%Y-%m-%d').date()
            # Handle DD/MM/YYYY format
            if '/' in date_str:
                parts = date_str.split('/')
                if len(parts) == 3 and len(parts[2]) == 4:
                    return datetime.strptime(f"{parts[2]}-{parts[1]}-{parts[0]}", '%Y-%m-%d').date()
            return None
        except Exception as e:
            logger.warning(f"Could not parse date '{date_str}': {e}")
            return None