"""
Parliamentary Permanent Delegations Mapper - SQLAlchemy ORM Version
===================================================================

Schema mapper for parliamentary permanent delegation files (DelegacaoPermanente*.xml).
Based on official Portuguese Parliament documentation (December 2017) - 
identical across legislatures IX through XIII.

DOCUMENTATION SOURCE:
Official PDF documentation from Portuguese Parliament data downloads.
Documentation is identical across all legislatures with available PDF files.

MAIN XML STRUCTURE MAPPED:
- ArrayOfDelegacaoPermanente: Root container for permanent delegation lists

DELEGATION STRUCTURE HANDLED:
1. DelegacaoPermanente (Permanent Delegation)
   - Id: Identificador do registo da Delegação Permanente
   - Nome: Nome da Delegação Permanente
   - Legislatura: Identificador da Legislatura
   - Sessão: Número da Sessão Legislativa
   - DataEleicao: Data da eleição da Delegação Permanente
   - Composicao: Lista de deputados (estruturas Membro)
   - Comissoes: Lista de comissões (estruturas Comissao)
   - Reunioes: Lista de reuniões (estruturas Reuniao)

2. Membro (Delegation Members)
   - Nome: Nome do deputado participante
   - Gp: Grupo parlamentar ao qual pertence o deputado
   - Cargo: Cargo exercido pelo deputado
   - DataInicio: Data do início do exercício de funções
   - DataFim: Data do fim do exercício de funções
   - Id: Identificador do deputado

3. Comissao (Commissions)
   - Nome: Nome da comissão pertencente à Delegação Permanente
   - Composição: Composição da comissão
   - Subcomissoes: Lista de Subcomissões

4. Reuniao (Meetings)
   - ID: Identificador do registo da reunião
   - Nome: Título da reunião
   - Tipo: Tipo de reunião (REN/RNI)
   - Local: Cidade e País onde foi realizada
   - Legislatura: Identificador da Legislatura
   - Sessão: Número da Sessão Legislativa
   - DataInicio: Data de início da reunião
   - DataFim: Data do fim da reunião
   - Participantes: Lista de participantes (estruturas Participante)

5. Participante (Meeting Participants)
   - Tipo: Tipo de participante (D=Deputado)
   - Nome: Nome do deputado participante
   - Gp: Grupo parlamentar
   - Leg: Legislatura do deputado
   - Id: Identificador do deputado

FIELD MAPPINGS (from official documentation):
Information about permanent delegations to international parliamentary organizations:
APCE, APOSCE, APNATO, UIP, AP-UPM, FPIA, AP-CPLP, and others.

Uses SQLAlchemy ORM models for clean, type-safe database operations.
All field mappings preserve official XML structure and naming conventions.

VERIFICATION COMPLETED:
✓ Mapper processes actual XML structure: ArrayOfDelegacaoPermanenteOut > DelegacaoPermanenteOut
✓ PDF documentation describes: ArrayOfDelegacaoPermanente > DelegacaoPermanente  
✓ Field mappings match between actual XML and documentation (verified via IX Legislature XML)
✓ All documented fields (Id, Nome, Legislatura, Sessao, DataEleicao, Composicao, etc.) present
✓ Member structure matches documentation (Nome, Gp, Cargo, DataInicio, DataFim, Id)
✓ Commission and meeting structures present but empty in sample data
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
from database.models import (
    DelegacaoPermanente, DelegacaoPermanenteMembro, DelegacaoPermanenteComissao, 
    DelegacaoPermanenteComissaoMembro, Deputado, Legislatura
)

logger = logging.getLogger(__name__)


class DelegacaoPermanenteMapper(SchemaMapper):
    """Schema mapper for parliamentary permanent delegation files"""

    def __init__(self, session, import_status_record=None):
        # Accept SQLAlchemy session directly (passed by unified importer)
        super().__init__(session, import_status_record=import_status_record)
        # Cache for delegation records to avoid duplicate inserts within same file
        self._delegacao_cache = {}  # delegacao_id -> DelegacaoPermanente
    
    def get_expected_fields(self) -> Set[str]:
        return {
            # Root elements
            'ArrayOfDelegacaoPermanenteOut',
            'ArrayOfDelegacaoPermanenteOut.DelegacaoPermanenteOut',
            
            # Main delegation fields
            'ArrayOfDelegacaoPermanenteOut.DelegacaoPermanenteOut.Id',
            'ArrayOfDelegacaoPermanenteOut.DelegacaoPermanenteOut.Nome',
            'ArrayOfDelegacaoPermanenteOut.DelegacaoPermanenteOut.Legislatura',
            'ArrayOfDelegacaoPermanenteOut.DelegacaoPermanenteOut.Sessao',
            'ArrayOfDelegacaoPermanenteOut.DelegacaoPermanenteOut.DataEleicao',
            'ArrayOfDelegacaoPermanenteOut.DelegacaoPermanenteOut.Composicao',
            'ArrayOfDelegacaoPermanenteOut.DelegacaoPermanenteOut.Comissoes',
            'ArrayOfDelegacaoPermanenteOut.DelegacaoPermanenteOut.Reunioes',
            
            # Members (IX Legislature composition structure)
            'ArrayOfDelegacaoPermanenteOut.DelegacaoPermanenteOut.Composicao.DelegacaoPermanenteMembroOut',
            'ArrayOfDelegacaoPermanenteOut.DelegacaoPermanenteOut.Composicao.DelegacaoPermanenteMembroOut.Id',
            'ArrayOfDelegacaoPermanenteOut.DelegacaoPermanenteOut.Composicao.DelegacaoPermanenteMembroOut.Nome',
            'ArrayOfDelegacaoPermanenteOut.DelegacaoPermanenteOut.Composicao.DelegacaoPermanenteMembroOut.Gp',
            'ArrayOfDelegacaoPermanenteOut.DelegacaoPermanenteOut.Composicao.DelegacaoPermanenteMembroOut.Cargo',
            'ArrayOfDelegacaoPermanenteOut.DelegacaoPermanenteOut.Composicao.DelegacaoPermanenteMembroOut.DataInicio',
            'ArrayOfDelegacaoPermanenteOut.DelegacaoPermanenteOut.Composicao.DelegacaoPermanenteMembroOut.DataFim',
            
            # XIII Legislature commission structure with XML namespace
            'ArrayOfDelegacaoPermanenteOut.DelegacaoPermanenteOut.Comissoes.Comissao',
            'ArrayOfDelegacaoPermanenteOut.DelegacaoPermanenteOut.Comissoes.Comissao.{http://parlamento.pt/AP/svc/}nome',
            'ArrayOfDelegacaoPermanenteOut.DelegacaoPermanenteOut.Comissoes.Comissao.{http://parlamento.pt/AP/svc/}composicao',
            'ArrayOfDelegacaoPermanenteOut.DelegacaoPermanenteOut.Comissoes.Comissao.{http://parlamento.pt/AP/svc/}subcomissoes',
            
            # XI Legislature deeper nested commission member structure with XML namespace
            'ArrayOfDelegacaoPermanenteOut.DelegacaoPermanenteOut.Comissoes.Comissao.{http://parlamento.pt/AP/svc/}composicao.{http://parlamento.pt/AP/svc/}Membro',
            'ArrayOfDelegacaoPermanenteOut.DelegacaoPermanenteOut.Comissoes.Comissao.{http://parlamento.pt/AP/svc/}composicao.{http://parlamento.pt/AP/svc/}Membro.{http://parlamento.pt/AP/svc/}nome',
            'ArrayOfDelegacaoPermanenteOut.DelegacaoPermanenteOut.Comissoes.Comissao.{http://parlamento.pt/AP/svc/}composicao.{http://parlamento.pt/AP/svc/}Membro.{http://parlamento.pt/AP/svc/}gp',
            'ArrayOfDelegacaoPermanenteOut.DelegacaoPermanenteOut.Comissoes.Comissao.{http://parlamento.pt/AP/svc/}composicao.{http://parlamento.pt/AP/svc/}Membro.{http://parlamento.pt/AP/svc/}cargo',
            'ArrayOfDelegacaoPermanenteOut.DelegacaoPermanenteOut.Comissoes.Comissao.{http://parlamento.pt/AP/svc/}composicao.{http://parlamento.pt/AP/svc/}Membro.{http://parlamento.pt/AP/svc/}dataInicio',
            'ArrayOfDelegacaoPermanenteOut.DelegacaoPermanenteOut.Comissoes.Comissao.{http://parlamento.pt/AP/svc/}composicao.{http://parlamento.pt/AP/svc/}Membro.{http://parlamento.pt/AP/svc/}dataFim'
        }
    
    def validate_and_map(self, xml_root: ET.Element, file_info: Dict, strict_mode: bool = False) -> Dict:
        """Map parliamentary permanent delegations to database"""
        results = {'records_processed': 0, 'records_imported': 0, 'errors': []}
        
        try:
            # Validate schema coverage according to strict mode
            self.validate_schema_coverage(xml_root, file_info, strict_mode)
            
            # Extract legislatura from filename or XML
            legislatura_sigla = self._extract_legislatura(file_info['file_path'], xml_root)
            legislatura = self._get_or_create_legislatura(legislatura_sigla)
            
            # Process permanent delegations
            for delegation in xml_root.findall('.//DelegacaoPermanenteOut'):
                try:
                    success = self._process_delegation(delegation, legislatura)
                    results['records_processed'] += 1
                    if success:
                        results['records_imported'] += 1
                except Exception as e:
                    error_msg = f"Permanent delegation processing error: {str(e)}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
                    results['records_processed'] += 1
                    self.session.rollback()
                    if strict_mode:
                        logger.error("STRICT MODE: Exiting due to permanent delegation processing error")
                        raise SchemaError(f"Permanent delegation processing failed in strict mode: {e}")
                    continue
            
            # Commit all changes
            return results
            
        except Exception as e:
            error_msg = f"Critical error processing permanent delegations: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            self.session.rollback()
            raise SchemaError(f"Critical permanent delegation processing error: {e}")
    
    
    def _process_delegation(self, delegation: ET.Element, legislatura: Legislatura) -> bool:
        """Process individual permanent delegation"""
        try:
            # Extract basic fields
            id_externo = self._get_int_value(delegation, 'Id')
            nome = self._get_text_value(delegation, 'Nome')
            sessao = self._get_text_value(delegation, 'Sessao')
            data_eleicao_str = self._get_text_value(delegation, 'DataEleicao')

            if not nome:
                logger.debug("Missing Nome field - importing with placeholder")
                nome = "DELEGACAO_SEM_NOME"

            # Parse election date
            data_eleicao = self._parse_date(data_eleicao_str)

            # Check cache first, then database, use upsert for parallel safety
            existing = None
            if id_externo:
                # Check in-memory cache first (for records added in this session)
                if id_externo in self._delegacao_cache:
                    existing = self._delegacao_cache[id_externo]
                else:
                    # Check database
                    existing = self.session.query(DelegacaoPermanente).filter_by(
                        delegacao_id=id_externo
                    ).first()
                    if existing:
                        # Add to cache for future lookups
                        self._delegacao_cache[id_externo] = existing

            if existing:
                # Update existing record
                existing.nome = nome
                existing.sessao = sessao
                existing.data_eleicao = data_eleicao
                existing.legislatura_id = legislatura.id
            else:
                # Use upsert for parallel-safe insert (handles race conditions)
                from sqlalchemy.dialects.postgresql import insert as pg_insert

                new_id = uuid.uuid4()
                stmt = pg_insert(DelegacaoPermanente).values(
                    id=new_id,
                    delegacao_id=id_externo,
                    nome=nome,
                    sessao=sessao,
                    data_eleicao=data_eleicao,
                    legislatura_id=legislatura.id
                ).on_conflict_do_update(
                    index_elements=['delegacao_id'],
                    set_={
                        'nome': nome,
                        'sessao': sessao,
                        'data_eleicao': data_eleicao,
                        'legislatura_id': legislatura.id
                    }
                ).returning(DelegacaoPermanente.id)

                result = self.session.execute(stmt)
                returned_id = result.scalar()

                # Fetch the record (either newly inserted or existing)
                existing = self.session.query(DelegacaoPermanente).filter_by(
                    delegacao_id=id_externo
                ).first()

                # Add to cache
                if id_externo and existing:
                    self._delegacao_cache[id_externo] = existing

            # Process members
            composicao = delegation.find('Composicao')
            if composicao is not None:
                for member in composicao.findall('DelegacaoPermanenteMembroOut'):
                    self._process_delegation_member(member, existing)

            # Process commissions (XIII Legislature)
            comissoes = delegation.find('Comissoes')
            if comissoes is not None:
                for comissao in comissoes.findall('Comissao'):
                    self._process_delegation_commission(comissao, existing)

            return True

        except Exception as e:
            logger.error(f"Error processing permanent delegation: {e}")
            return False
    
    def _process_delegation_member(self, member: ET.Element, delegacao: DelegacaoPermanente) -> bool:
        """Process delegation member"""
        try:
            # Extract member fields
            member_id = self._get_int_value(member, 'Id')
            nome = self._get_text_value(member, 'Nome')
            gp = self._get_text_value(member, 'Gp')
            cargo = self._get_text_value(member, 'Cargo')
            data_inicio_str = self._get_text_value(member, 'DataInicio')
            data_fim_str = self._get_text_value(member, 'DataFim')
            
            if not nome:
                logger.debug("Missing member name - importing with placeholder")
                nome = "MEMBRO_SEM_NOME"
            
            # Parse dates
            data_inicio = self._parse_date(data_inicio_str)
            data_fim = self._parse_date(data_fim_str) if data_fim_str else None
            
            # Check if member record already exists
            existing = None
            if member_id:
                existing = self.session.query(DelegacaoPermanenteMembro).filter_by(
                    membro_id=member_id,
                    delegacao_id=delegacao.id
                ).first()
            
            if existing:
                # Update existing member
                existing.nome = nome
                existing.gp = gp
                existing.cargo = cargo
                existing.data_inicio = data_inicio
                existing.data_fim = data_fim
            else:
                # Create new member record
                membro = DelegacaoPermanenteMembro(
                    id=uuid.uuid4(),
                    delegacao_id=delegacao.id,
                    membro_id=member_id,
                    nome=nome,
                    gp=gp,
                    cargo=cargo,
                    data_inicio=data_inicio,
                    data_fim=data_fim
                )
                self._add_with_tracking(membro)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing delegation member: {e}")
            return False
    
    def _process_delegation_commission(self, comissao: ET.Element, delegacao: DelegacaoPermanente) -> bool:
        """Process delegation commission (XIII Legislature with XML namespace)"""
        try:
            # Extract commission fields with namespace using base class methods
            nome = self._get_namespaced_text(comissao, 'ap', 'nome')
            composicao = self._get_namespaced_text(comissao, 'ap', 'composicao')
            subcomissoes = self._get_namespaced_text(comissao, 'ap', 'subcomissoes')
            
            # Create commission record if there's meaningful data
            comissao_record = None
            if any([nome, composicao, subcomissoes]):
                comissao_record = DelegacaoPermanenteComissao(
                    id=uuid.uuid4(),
                    delegacao_id=delegacao.id,
                    nome=nome,
                    composicao=composicao,
                    subcomissoes=subcomissoes
                )
                self._add_with_tracking(comissao_record)
            
            # Process nested commission members (XI Legislature)
            composicao_elem = self._get_namespaced_element(comissao, 'ap', 'composicao')
            if composicao_elem is not None and comissao_record is not None:
                for membro in composicao_elem.findall('.//{http://parlamento.pt/AP/svc/}Membro'):
                    self._process_commission_member(membro, comissao_record)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing delegation commission: {e}")
            return False
    
    def _process_commission_member(self, membro: ET.Element, comissao: DelegacaoPermanenteComissao) -> bool:
        """Process commission member (XI Legislature nested structure with XML namespace)"""
        try:
            # Extract member fields with namespace using base class methods
            nome = self._get_namespaced_text(membro, 'ap', 'nome')
            gp = self._get_namespaced_text(membro, 'ap', 'gp')
            cargo = self._get_namespaced_text(membro, 'ap', 'cargo')
            data_inicio_str = self._get_namespaced_text(membro, 'ap', 'dataInicio')
            data_fim_str = self._get_namespaced_text(membro, 'ap', 'dataFim')
            
            # Parse dates
            data_inicio = self._parse_date(data_inicio_str) if data_inicio_str else None
            data_fim = self._parse_date(data_fim_str) if data_fim_str else None
            
            # Create member record if there's meaningful data
            if any([nome, gp, cargo, data_inicio, data_fim]):
                membro_record = DelegacaoPermanenteComissaoMembro(
                    id=uuid.uuid4(),
                    comissao_id=comissao.id,
                    nome=nome,
                    gp=gp,
                    cargo=cargo,
                    data_inicio=data_inicio,
                    data_fim=data_fim
                )
                self._add_with_tracking(membro_record)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing commission member: {e}")
            return False
    
    # Utility methods now inherited from base class