"""
Parliamentary Eventual Delegations Mapper - SQLAlchemy ORM Version
=================================================================

Schema mapper for parliamentary eventual delegation files (DelegacaoEventual*.xml).
Based on official Portuguese Parliament documentation (December 2017) - 
identical across legislatures IX through XIII.

DOCUMENTATION SOURCE:
Official PDF documentation from Portuguese Parliament data downloads.
Documentation is identical across all legislatures with available PDF files.

MAIN XML STRUCTURE MAPPED:
- ArrayOfDelegacaoEventualReuniao: Root container for delegation meeting lists
  (Documentation references this as "ArrayOfReuniao" conceptually)

DELEGATION STRUCTURE HANDLED:
1. DelegacaoEventualReuniao (Meeting/Delegation Event)
   (Documentation references this as "Reuniao" conceptually)
   - ID: Identificador do registo das Delegação Eventual
   - Nome: Título da reunião da Delegação Eventual
   - Local: Cidade e País onde foi realizada a reunião da Delegação Eventual
   - Legislatura: Identificador da Legislatura
   - Sessão: Número da Sessão Legislativa
   - DataInicio: Data de Início da reunião da Delegação Eventual
   - DataFim: Data do fim da reunião da Delegação Eventual
   - Participantes: Lista de participantes nas reuniões

2. RelacoesExternasParticipantes (Meeting Participants)
   (Documentation references this as "Participante" conceptually)
   - Tipo: Tipo de participante (D=Deputado)
   - Nome: Nome do deputado participante na reunião
   - Gp: Grupo parlamentar ao qual pertence o deputado
   - Leg: Legislatura do deputado
   - Id: Identificador do deputado

FIELD MAPPINGS (from official documentation):
Information about sporadic meetings attended by Assembly deputies.
Contains comprehensive participant data with parliamentary group affiliations.

Uses SQLAlchemy ORM models for clean, type-safe database operations.
All field mappings preserve official XML structure and naming conventions.
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
    DelegacaoEventual, DelegacaoEventualParticipante, Deputado, Legislatura
)

logger = logging.getLogger(__name__)


class DelegacaoEventualMapper(SchemaMapper):
    """
    Schema mapper for parliamentary eventual delegation files (DelegacaoEventual*.xml)

    Processes ArrayOfReuniao XML structure containing sporadic delegation meetings:
    - Meeting/delegation event records with dates, locations, and legislative session info
    - Participant lists with deputy identification and parliamentary group affiliation
    - Maps to comprehensive SQLAlchemy ORM models for zero data loss

    Based on official Parliament documentation identical across IX-XIII legislatures.
    """

    def __init__(self, session, import_status_record=None):
        # Accept SQLAlchemy session directly (passed by unified importer)
        super().__init__(session, import_status_record=import_status_record)
        # Cache for delegation records to avoid duplicate inserts within same file
        self._delegacao_cache = {}  # delegacao_id -> DelegacaoEventual
    
    def get_expected_fields(self) -> Set[str]:
        return {
            # Root elements
            'ArrayOfDelegacaoEventualReuniao',
            'ArrayOfDelegacaoEventualReuniao.DelegacaoEventualReuniao',
            
            # Main delegation fields
            'ArrayOfDelegacaoEventualReuniao.DelegacaoEventualReuniao.Id',
            'ArrayOfDelegacaoEventualReuniao.DelegacaoEventualReuniao.Nome',
            'ArrayOfDelegacaoEventualReuniao.DelegacaoEventualReuniao.Local',
            'ArrayOfDelegacaoEventualReuniao.DelegacaoEventualReuniao.Legislatura',
            'ArrayOfDelegacaoEventualReuniao.DelegacaoEventualReuniao.Sessao',
            'ArrayOfDelegacaoEventualReuniao.DelegacaoEventualReuniao.DataInicio',
            'ArrayOfDelegacaoEventualReuniao.DelegacaoEventualReuniao.DataFim',
            'ArrayOfDelegacaoEventualReuniao.DelegacaoEventualReuniao.Tipo',
            
            # Participants
            'ArrayOfDelegacaoEventualReuniao.DelegacaoEventualReuniao.Participantes',
            'ArrayOfDelegacaoEventualReuniao.DelegacaoEventualReuniao.Participantes.RelacoesExternasParticipantes',
            'ArrayOfDelegacaoEventualReuniao.DelegacaoEventualReuniao.Participantes.RelacoesExternasParticipantes.Gp',
            'ArrayOfDelegacaoEventualReuniao.DelegacaoEventualReuniao.Participantes.RelacoesExternasParticipantes.Leg',
            'ArrayOfDelegacaoEventualReuniao.DelegacaoEventualReuniao.Participantes.RelacoesExternasParticipantes.Id',  # IX Legislature
            'ArrayOfDelegacaoEventualReuniao.DelegacaoEventualReuniao.Participantes.RelacoesExternasParticipantes.Nome',  # IX Legislature
            'ArrayOfDelegacaoEventualReuniao.DelegacaoEventualReuniao.Participantes.RelacoesExternasParticipantes.Tipo'  # IX Legislature
        }
    
    def validate_and_map(self, xml_root: ET.Element, file_info: Dict, strict_mode: bool = False) -> Dict:
        """Map parliamentary delegation events to database"""
        results = {'records_processed': 0, 'records_imported': 0, 'errors': []}
        
        try:
            # Validate schema coverage according to strict mode
            self.validate_schema_coverage(xml_root, file_info, strict_mode)
            
            # Extract legislatura from filename or XML
            legislatura_sigla = self._extract_legislatura(file_info['file_path'], xml_root)
            legislatura = self._get_or_create_legislatura(legislatura_sigla)
            
            # Process delegation events
            for delegation_event in xml_root.findall('.//DelegacaoEventualReuniao'):
                try:
                    success = self._process_delegation_event(delegation_event, legislatura)
                    results['records_processed'] += 1
                    if success:
                        results['records_imported'] += 1
                except Exception as e:
                    error_msg = f"Delegation event processing error: {str(e)}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
                    results['records_processed'] += 1
                    self.session.rollback()
                    if strict_mode:
                        logger.error("STRICT MODE: Exiting due to delegation event processing error")
                        raise SchemaError(f"Delegation event processing failed in strict mode: {e}")
                    continue
            
            # Commit all changes
            return results
            
        except Exception as e:
            error_msg = f"Critical error processing delegation events: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            self.session.rollback()
            raise SchemaError(f"Critical delegation processing error: {e}")
    
    
    def _process_delegation_event(self, delegation_event: ET.Element, legislatura: Legislatura) -> bool:
        """Process individual delegation event"""
        try:
            # Extract basic fields
            id_externo = self._get_int_value(delegation_event, 'Id')
            nome = self._get_text_value(delegation_event, 'Nome')
            local = self._get_text_value(delegation_event, 'Local')
            sessao = self._get_int_value(delegation_event, 'Sessao')
            data_inicio_str = self._get_text_value(delegation_event, 'DataInicio')
            data_fim_str = self._get_text_value(delegation_event, 'DataFim')

            if not nome:
                logger.debug("Missing Nome field - importing with placeholder")
                nome = "DELEGACAO_EVENTUAL_SEM_NOME"

            # Parse dates
            data_inicio = self._parse_date(data_inicio_str)
            data_fim = self._parse_date(data_fim_str)

            # Check cache first, then database, use upsert for parallel safety
            existing = None
            if id_externo:
                # Check in-memory cache first (for records added in this session)
                if id_externo in self._delegacao_cache:
                    existing = self._delegacao_cache[id_externo]
                else:
                    # Check database
                    existing = self.session.query(DelegacaoEventual).filter_by(
                        delegacao_id=id_externo
                    ).first()
                    if existing:
                        # Add to cache for future lookups
                        self._delegacao_cache[id_externo] = existing

            if existing:
                # Update existing record
                existing.nome = nome
                existing.local = local
                existing.sessao = sessao
                existing.data_inicio = data_inicio
                existing.data_fim = data_fim
                existing.legislatura_id = legislatura.id
            else:
                # Use upsert for parallel-safe insert (handles race conditions)
                from sqlalchemy.dialects.postgresql import insert as pg_insert

                new_id = uuid.uuid4()
                stmt = pg_insert(DelegacaoEventual).values(
                    id=new_id,
                    delegacao_id=id_externo,
                    nome=nome,
                    local=local,
                    sessao=sessao,
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    legislatura_id=legislatura.id
                ).on_conflict_do_update(
                    index_elements=['delegacao_id'],
                    set_={
                        'nome': nome,
                        'local': local,
                        'sessao': sessao,
                        'data_inicio': data_inicio,
                        'data_fim': data_fim,
                        'legislatura_id': legislatura.id
                    }
                ).returning(DelegacaoEventual.id)

                result = self.session.execute(stmt)
                returned_id = result.scalar()

                # Fetch the record (either newly inserted or existing)
                existing = self.session.query(DelegacaoEventual).filter_by(
                    delegacao_id=id_externo
                ).first()

                # Add to cache
                if id_externo and existing:
                    self._delegacao_cache[id_externo] = existing

            # Process participants
            self._process_delegation_participants(delegation_event, existing)

            return True

        except Exception as e:
            logger.error(f"Error processing delegation event: {e}")
            return False
    
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to ISO format"""
        if not date_str:
            return None
        
        try:
            # Handle datetime format: DD/MM/YYYY HH:MM:SS
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
            
            # Try ISO format
            if re.match(r'\d{4}-\d{2}-\d{2}', date_part):
                return date_part
            
        except (ValueError, IndexError):
            logger.warning(f"Could not parse date: {date_str}")
        
        return None
    
    # NOTE: _get_or_create_legislatura is inherited from EnhancedSchemaMapper (with caching)
    # NOTE: Roman numeral conversion uses ROMAN_TO_NUMBER from LegislatureHandlerMixin

    def _process_delegation_participants(self, delegation_event: ET.Element, delegacao: DelegacaoEventual):
        """Process delegation participants"""
        # Process internal participants
        participantes = delegation_event.find('Participantes')
        if participantes is not None:
            for participante in participantes:
                nome = participante.text if participante.text else participante.tag
                tipo = self._get_text_value(participante, 'Tipo')
                gp = self._get_text_value(participante, 'Gp')
                leg = self._get_text_value(participante, 'Leg')
                
                if nome:
                    participante_record = DelegacaoEventualParticipante(
                        id=uuid.uuid4(),
                        delegacao_id=delegacao.id,
                        nome=nome,
                        gp=gp,
                        tipo_participante='interno'
                    )
                    self._add_with_tracking(participante_record)
        
        # Process external participants (enhanced for IX Legislature)
        participantes_elem = delegation_event.find('Participantes')
        if participantes_elem is not None:
            relacoes_externas = participantes_elem.find('RelacoesExternasParticipantes')
            if relacoes_externas is not None:
                # IX Legislature structure with Id, Nome, Tipo fields
                participante_id = self._get_int_value(relacoes_externas, 'Id')
                nome = self._get_text_value(relacoes_externas, 'Nome')
                tipo = self._get_text_value(relacoes_externas, 'Tipo')
                gp = self._get_text_value(relacoes_externas, 'Gp')
                
                if nome or participante_id:
                    if not tipo:
                        raise ValueError("Missing required participant type. Data integrity violation - cannot generate artificial participant types")

                    participante_record = DelegacaoEventualParticipante(
                        id=uuid.uuid4(),
                        delegacao_id=delegacao.id,
                        participante_id=participante_id,
                        nome=nome,
                        gp=gp,
                        tipo_participante=tipo
                    )
                    self._add_with_tracking(participante_record)