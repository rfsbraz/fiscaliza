"""
National Meetings and Visits Mapper - SQLAlchemy ORM Version
===========================================================

Schema mapper for national meetings and visits files (ReunioesNacionais.xml).
Based on official Portuguese Parliament documentation (December 2017) - 
documented across legislatures IX through XIII.

DOCUMENTATION SOURCE:
Official PDF documentation "Significado das Tags do Ficheiro ReunioesNacionais.xml"
from Portuguese Parliament data downloads (December 2017).

MAIN XML STRUCTURE MAPPED:
- ArrayOfReuniao: Root container for national meetings and visits
  (Contains list of external relations meetings outside standard parliamentary categories)

MEETING STRUCTURE HANDLED:
1. Reuniao (Meeting/Visit Record)
   - Id: Reuniao registry identifier
   - Nome: Meeting title/designation
   - Tipo: Meeting type (RNI=International Meeting, RNN=National Meeting, VEE=Foreign Entity Visit)
   - TipoDesignacao: Meeting type designation description
   - DataInicio: Meeting start date
   - DataFim: Meeting end date
   - Local: Meeting location
   - Promotor: Meeting organizer/promoter
   - Observacoes: Additional observations/notes
   - Participantes: List of meeting participants

2. Participante (Meeting Participant)
   - Tipo: Participant type (D=Deputado/Deputy)
   - Nome: Participant name
   - Gp: Parliamentary group affiliation
   - Id: Deputy identifier for cross-referencing

FIELD MAPPINGS (from official documentation):
External relations meetings and visits containing information about:
- International meetings with foreign parliamentary bodies
- National meetings within Portuguese institutional framework  
- Foreign entity visits to Portuguese Parliament
- Deputy participation with parliamentary group context

Uses SQLAlchemy ORM models for comprehensive data preservation.
All field mappings follow official XML structure documented December 2017.
"""

import xml.etree.ElementTree as ET
import os
import re
import uuid
from datetime import datetime
from typing import Dict, Optional, Set, List
import logging

from .enhanced_base_mapper import EnhancedSchemaMapper, SchemaError

# Import our models
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from database.models import (
    ReuniaoNacional, ParticipanteReuniaoNacional, Deputado, Legislatura
)
from database.translators.reunioes_visitas import meeting_visit_translator

logger = logging.getLogger(__name__)


class ReunioesNacionaisMapper(EnhancedSchemaMapper):
    """
    Schema mapper for national meetings and visits files (ReunioesNacionais.xml)
    
    Processes ArrayOfReuniao XML structure containing external relations meetings:
    - Meeting records with dates, locations, types, and organizers
    - Participant lists with deputy identification and parliamentary group context
    - Maps to comprehensive SQLAlchemy ORM models for complete data preservation
    
    Based on official Parliament documentation (December 2017) consistent across legislatures.
    """
    
    def __init__(self, session, import_status_record=None):
        # Accept SQLAlchemy session directly (passed by unified importer)
        super().__init__(session, import_status_record=import_status_record)
    
    def get_expected_fields(self) -> Set[str]:
        return {
            # Root elements - Original format
            'ArrayOfReuniao',
            'ArrayOfReuniao.Reuniao',
            
            # Root elements - ReuniaoNacionalOut format
            'ArrayOfReuniaoNacionalOut',
            'ArrayOfReuniaoNacionalOut.ReuniaoNacionalOut',
            
            # Main meeting fields (XML uses lowercase) - Original format
            'ArrayOfReuniao.Reuniao.id',
            'ArrayOfReuniao.Reuniao.nome',
            'ArrayOfReuniao.Reuniao.tipo',
            'ArrayOfReuniao.Reuniao.tipoDesignacao',
            'ArrayOfReuniao.Reuniao.dataInicio',
            'ArrayOfReuniao.Reuniao.dataFim',
            'ArrayOfReuniao.Reuniao.local',
            'ArrayOfReuniao.Reuniao.promotor',
            'ArrayOfReuniao.Reuniao.observacoes',
            'ArrayOfReuniao.Reuniao.legislatura',
            'ArrayOfReuniao.Reuniao.sessao',
            
            # Main meeting fields - ReuniaoNacionalOut format (CamelCase)
            'ArrayOfReuniaoNacionalOut.ReuniaoNacionalOut.Id',
            'ArrayOfReuniaoNacionalOut.ReuniaoNacionalOut.Nome',
            'ArrayOfReuniaoNacionalOut.ReuniaoNacionalOut.Tipo',
            'ArrayOfReuniaoNacionalOut.ReuniaoNacionalOut.DataInicio',
            'ArrayOfReuniaoNacionalOut.ReuniaoNacionalOut.DataFim',
            'ArrayOfReuniaoNacionalOut.ReuniaoNacionalOut.Local',
            'ArrayOfReuniaoNacionalOut.ReuniaoNacionalOut.Promotor',
            'ArrayOfReuniaoNacionalOut.ReuniaoNacionalOut.Legislatura',
            'ArrayOfReuniaoNacionalOut.ReuniaoNacionalOut.Sessao',
            
            # Participants (XML uses lowercase) - Original format
            'ArrayOfReuniao.Reuniao.participantes',
            'ArrayOfReuniao.Reuniao.participantes.Participante',
            'ArrayOfReuniao.Reuniao.participantes.Participante.tipo',
            'ArrayOfReuniao.Reuniao.participantes.Participante.nome',
            'ArrayOfReuniao.Reuniao.participantes.Participante.gp',
            'ArrayOfReuniao.Reuniao.participantes.Participante.id',
            'ArrayOfReuniao.Reuniao.participantes.Participante.leg',
            'ArrayOfReuniao.Reuniao.participantes.Participante.pais',
            
            # Participants - ReuniaoNacionalOut format (CamelCase)
            'ArrayOfReuniaoNacionalOut.ReuniaoNacionalOut.Participantes',
            'ArrayOfReuniaoNacionalOut.ReuniaoNacionalOut.Participantes.RelacoesExternasParticipantes',
            'ArrayOfReuniaoNacionalOut.ReuniaoNacionalOut.Participantes.RelacoesExternasParticipantes.Id',
            'ArrayOfReuniaoNacionalOut.ReuniaoNacionalOut.Participantes.RelacoesExternasParticipantes.Nome',
            'ArrayOfReuniaoNacionalOut.ReuniaoNacionalOut.Participantes.RelacoesExternasParticipantes.Tipo',
            'ArrayOfReuniaoNacionalOut.ReuniaoNacionalOut.Participantes.RelacoesExternasParticipantes.Gp',
            'ArrayOfReuniaoNacionalOut.ReuniaoNacionalOut.Participantes.RelacoesExternasParticipantes.Leg'
        }
    
    def validate_and_map(self, xml_root: ET.Element, file_info: Dict, strict_mode: bool = False) -> Dict:
        """Map national meetings and visits to database"""
        results = {'records_processed': 0, 'records_imported': 0, 'errors': []}
        
        try:
            # Store file info for legislature extraction
            self.file_info = file_info
            
            # Validate schema coverage according to strict mode
            self.validate_schema_coverage(xml_root, file_info, strict_mode)
            
            # Get legislatura from file_info (from ImportStatus) or fallback to filename extraction
            logger.debug(f"ReunioesNacionais: file_info contents: {file_info}")
            
            if 'legislatura' in file_info and file_info['legislatura']:
                legislatura_sigla = file_info['legislatura']
                logger.info(f"Using legislatura from file_info: {legislatura_sigla}")
            else:
                logger.warning(f"No legislatura in file_info, attempting filename extraction from: {file_info.get('file_path', 'NO_PATH')}")
                try:
                    # Fallback to filename extraction
                    legislatura_sigla = self._extract_legislatura(file_info['file_path'], xml_root)
                    logger.info(f"Extracted legislatura from filename: {legislatura_sigla}")
                except Exception as e:
                    logger.error(f"Failed to extract legislatura from filename: {e}")
                    raise SchemaError(f"Could not determine legislatura from file_info or filename: {e}")
            
            legislatura = self._get_or_create_legislatura(legislatura_sigla)
            
            # Process national meetings - handle both XML formats
            meetings = xml_root.findall('.//Reuniao') or xml_root.findall('.//ReuniaoNacionalOut')
            for reuniao in meetings:
                try:
                    success = self._process_meeting(reuniao, legislatura)
                    results['records_processed'] += 1
                    if success:
                        results['records_imported'] += 1
                except Exception as e:
                    error_msg = f"Meeting processing error: {str(e)}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
                    results['records_processed'] += 1
                    raise RuntimeError(f"Data integrity issue: {error_msg}")
            
            # Commit all changes
            return results
            
        except Exception as e:
            error_msg = f"Critical error processing national meetings: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            self.session.rollback()
            raise SchemaError(f"Critical meeting processing error: {e}")
    
    
    def _process_meeting(self, reuniao: ET.Element, legislatura: Legislatura) -> bool:
        """Process individual national meeting record"""
        try:
            # Extract basic fields - try both lowercase (original) and CamelCase (ReuniaoNacionalOut) formats
            reuniao_id = self._get_int_value(reuniao, 'id') or self._get_int_value(reuniao, 'Id')
            nome = self._get_text_value(reuniao, 'nome') or self._get_text_value(reuniao, 'Nome')
            tipo = self._get_text_value(reuniao, 'tipo') or self._get_text_value(reuniao, 'Tipo')
            tipo_designacao = self._get_text_value(reuniao, 'tipoDesignacao')
            data_inicio_str = self._get_text_value(reuniao, 'dataInicio') or self._get_text_value(reuniao, 'DataInicio')
            data_fim_str = self._get_text_value(reuniao, 'dataFim') or self._get_text_value(reuniao, 'DataFim')
            local = self._get_text_value(reuniao, 'local') or self._get_text_value(reuniao, 'Local')
            promotor = self._get_text_value(reuniao, 'promotor') or self._get_text_value(reuniao, 'Promotor')
            observacoes = self._get_text_value(reuniao, 'observacoes')
            
            if not reuniao_id:
                logger.warning("Missing meeting ID - skipping record")
                return False
                
            if not nome:
                logger.debug("Missing meeting name - using placeholder")
                nome = f"REUNIAO_NACIONAL_{reuniao_id}"
            
            # Parse dates
            data_inicio = None
            data_fim = None
            if data_inicio_str:
                data_inicio = self._parse_date(data_inicio_str)
            if data_fim_str:
                data_fim = self._parse_date(data_fim_str)
            
            # Validate meeting type using translator
            if tipo:
                translation = meeting_visit_translator.get_meeting_type(tipo)
                if not translation or not translation.is_valid:
                    logger.warning(f"Unknown meeting type '{tipo}' for meeting ID {reuniao_id}")
            
            # Check if meeting already exists
            existing = self.session.query(ReuniaoNacional).filter_by(
                reuniao_id=reuniao_id
            ).first()
            
            if existing:
                # Update existing record
                existing.nome = nome
                existing.tipo = tipo
                existing.tipo_designacao = tipo_designacao
                existing.data_inicio = data_inicio
                existing.data_fim = data_fim
                existing.local = local
                existing.promotor = promotor
                existing.observacoes = observacoes
                existing.legislatura_id = legislatura.id
                meeting_record = existing
            else:
                # Create new meeting record
                meeting_record = ReuniaoNacional(
                    id=uuid.uuid4(),
                    reuniao_id=reuniao_id,
                    nome=nome,
                    tipo=tipo,
                    tipo_designacao=tipo_designacao,
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    local=local,
                    promotor=promotor,
                    observacoes=observacoes,
                    legislatura_id=legislatura.id
                )
                self._add_with_tracking(meeting_record)
            
            # Process participants
            self._process_meeting_participants(reuniao, meeting_record)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing meeting: {str(e)}")
            return False
    
    def _process_meeting_participants(self, reuniao: ET.Element, meeting_record: ReuniaoNacional) -> None:
        """Process participants for a meeting"""
        
        # Clear existing participants for update scenarios
        self.session.query(ParticipanteReuniaoNacional).filter_by(
            reuniao_id=meeting_record.id
        ).delete()
        
        # Process participants - handle both XML formats
        participantes_element = reuniao.find('participantes') or reuniao.find('Participantes')
        if participantes_element is not None:
            # Handle both 'Participante' and 'RelacoesExternasParticipantes' structures
            participants = participantes_element.findall('Participante') or \
                          participantes_element.findall('RelacoesExternasParticipantes')
            for participante in participants:
                self._process_participant(participante, meeting_record)
    
    def _process_participant(self, participante: ET.Element, meeting_record: ReuniaoNacional) -> None:
        """Process individual meeting participant"""
        try:
            # Extract participant fields - handle both lowercase and CamelCase formats
            tipo = self._get_text_value(participante, 'tipo') or self._get_text_value(participante, 'Tipo')
            nome = self._get_text_value(participante, 'nome') or self._get_text_value(participante, 'Nome')
            gp = self._get_text_value(participante, 'gp') or self._get_text_value(participante, 'Gp')
            deputy_id = self._get_int_value(participante, 'id') or self._get_int_value(participante, 'Id')
            
            if not nome:
                logger.warning("Participant missing name - skipping")
                return
                
            # Store participant type as-is from source data (translator available for runtime interpretation)
            
            # Try to find or create deputy record if we have deputy_id
            deputado = None
            if deputy_id:
                deputado = self._get_or_create_deputado(
                    record_id=deputy_id,
                    id_cadastro=deputy_id,  # For now, assume same
                    nome=nome,
                    legislatura_id=meeting_record.legislatura_id
                )
            
            # Create participant record
            # Note: deputado_id stores the XML's integer ID, not the UUID foreign key
            participant_record = ParticipanteReuniaoNacional(
                id=uuid.uuid4(),
                reuniao_id=meeting_record.id,
                tipo=tipo,
                nome=nome,
                grupo_parlamentar=gp,
                deputado_id=deputy_id  # Use XML integer ID, not UUID
            )

            self._add_with_tracking(participant_record)
            
        except Exception as e:
            logger.error(f"Error processing participant {nome}: {str(e)}")


# Additional utility functions for external use
def create_reunioes_nacionais_mapper(session):
    """Factory function to create ReunioesNacionaisMapper instance"""
    return ReunioesNacionaisMapper(session)


def validate_reunioes_nacionais_xml(xml_file_path: str) -> Dict:
    """
    Validate ReunioesNacionais.xml file structure without database operations
    
    Args:
        xml_file_path: Path to XML file to validate
        
    Returns:
        Dictionary containing validation results and field coverage analysis
    """
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        
        # Create temporary mapper for validation (no session)
        mapper = ReunioesNacionaisMapper(None)
        
        # Check schema coverage
        unmapped_fields = mapper.check_schema_coverage(root)
        
        # Count records
        meetings = root.findall('.//Reuniao')
        total_participants = 0
        for meeting in meetings:
            participantes = meeting.find('Participantes')
            if participantes is not None:
                total_participants += len(participantes.findall('Participante'))
        
        return {
            'valid': True,
            'total_meetings': len(meetings),
            'total_participants': total_participants,
            'unmapped_fields': unmapped_fields,
            'schema_coverage': len(unmapped_fields) == 0
        }
        
    except ET.ParseError as e:
        return {
            'valid': False,
            'error': f"XML parsing error: {str(e)}",
            'total_meetings': 0,
            'total_participants': 0,
            'unmapped_fields': [],
            'schema_coverage': False
        }
    except Exception as e:
        return {
            'valid': False,
            'error': f"Validation error: {str(e)}",
            'total_meetings': 0,
            'total_participants': 0,
            'unmapped_fields': [],
            'schema_coverage': False
        }