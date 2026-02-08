"""
Parliamentary Agenda Mapper - SQLAlchemy ORM Version
===================================================

Schema mapper for parliamentary agenda files (AgendaParlamentar*.xml/.json).
Based on official Portuguese Parliament documentation (June 2023):
"AgendaParlamentar.xml/.json" structure from XV_Legislatura documentation.

MAJOR STRUCTURES MAPPED (from official documentation):

1. **AgendaParlamentar/RootObject** - Main agenda event structure
   - Contains all event metadata including dates, times, locations
   - Maps section/theme IDs via SectionType/ThemeType translators
   - Includes parliamentary group associations and scheduling info

2. **Section Classification** - 24 section types (SectionId 1-24)
   - Maps from "Comissão Permanente" to "Grelhas de Tempos"
   - Requires SectionType translator for human-readable descriptions

3. **Theme Classification** - 16 theme types (ThemeId 1-16)  
   - Maps parliamentary activity themes and categories
   - Requires ThemeType translator for proper categorization

4. **AnexoEventos** - Document attachments
   - AnexosComissaoPermanente: Permanent committee attachments
   - AnexosPlenario: Plenary session attachments
   - Links to supporting documents and materials

5. **Scheduling Information** - Complete event timing
   - AllDayEvent: Full day event indicator
   - EventStartDate/EventStartTime: Event start timing
   - EventEndDate/EventEndTime: Event end timing
   - PostPlenary: After plenary session scheduling

REFERENCE TABLES USED:
- SectionType: 24 section codes (1-24) for meeting/event sections
- ThemeType: 16 theme codes (1-16) for parliamentary activity themes

Translation Support:
- All coded fields mapped to appropriate translator modules
- Cross-references with AgendaTranslator for section/theme resolution
- Maintains data integrity with official XV_Legislatura specifications

Uses SQLAlchemy ORM models for clean, type-safe database operations.
"""

import xml.etree.ElementTree as ET
import os
import re
import uuid
from datetime import datetime, date
from typing import Dict, Optional, Set
import logging

from .enhanced_base_mapper import SchemaMapper, SchemaError

# Import our models
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from database.models import AgendaParlamentar, AgendaParlamentarAnexo, Legislatura

logger = logging.getLogger(__name__)


class AgendaParlamentarMapper(SchemaMapper):
    """
    Schema mapper for parliamentary agenda files - SQLAlchemy ORM Version
    
    Processes AgendaParlamentar*.xml/.json files containing comprehensive
    parliamentary agenda data:
    
    - AgendaParlamentar/RootObject: Main event and meeting scheduling
    - AnexoEventos: Document attachments and supporting materials
    - Section/Theme Classification: Event categorization and organization
    
    All field mappings based on official XV_Legislatura documentation
    with proper translator integration for coded field values.
    """
    
    def __init__(self, session, import_status_record=None):
        # Accept SQLAlchemy session directly (passed by unified importer)
        super().__init__(session, import_status_record=import_status_record)
    
    def get_expected_fields(self) -> Set[str]:
        return {
            # Root elements
            'ArrayOfAgendaParlamentar',
            
            # AgendaParlamentar nested elements
            'ArrayOfAgendaParlamentar.AgendaParlamentar',
            'ArrayOfAgendaParlamentar.AgendaParlamentar.Id',
            'ArrayOfAgendaParlamentar.AgendaParlamentar.SectionId',
            'ArrayOfAgendaParlamentar.AgendaParlamentar.Section',
            'ArrayOfAgendaParlamentar.AgendaParlamentar.ThemeId',
            'ArrayOfAgendaParlamentar.AgendaParlamentar.Theme',
            'ArrayOfAgendaParlamentar.AgendaParlamentar.OrderValue',
            'ArrayOfAgendaParlamentar.AgendaParlamentar.ParlamentGroup',
            'ArrayOfAgendaParlamentar.AgendaParlamentar.AllDayEvent',
            'ArrayOfAgendaParlamentar.AgendaParlamentar.EventStartDate',
            'ArrayOfAgendaParlamentar.AgendaParlamentar.EventStartTime',
            'ArrayOfAgendaParlamentar.AgendaParlamentar.EventEndDate',
            'ArrayOfAgendaParlamentar.AgendaParlamentar.EventEndTime',
            'ArrayOfAgendaParlamentar.AgendaParlamentar.Title',
            'ArrayOfAgendaParlamentar.AgendaParlamentar.Subtitle',
            'ArrayOfAgendaParlamentar.AgendaParlamentar.InternetText',
            'ArrayOfAgendaParlamentar.AgendaParlamentar.Local',
            'ArrayOfAgendaParlamentar.AgendaParlamentar.Link',
            'ArrayOfAgendaParlamentar.AgendaParlamentar.LegDes',
            'ArrayOfAgendaParlamentar.AgendaParlamentar.OrgDes',
            'ArrayOfAgendaParlamentar.AgendaParlamentar.ReuNumero',
            'ArrayOfAgendaParlamentar.AgendaParlamentar.SelNumero',
            'ArrayOfAgendaParlamentar.AgendaParlamentar.PostPlenary',
            'ArrayOfAgendaParlamentar.AgendaParlamentar.AnexosComissaoPermanente',
            'ArrayOfAgendaParlamentar.AgendaParlamentar.AnexosPlenario'
        }
    
    def validate_and_map(self, xml_root: ET.Element, file_info: Dict, strict_mode: bool = False) -> Dict:
        """Map parliamentary agenda to database"""
        results = {'records_processed': 0, 'records_imported': 0, 'errors': []}
        
        # Validate schema coverage according to strict mode
        self.validate_schema_coverage(xml_root, file_info, strict_mode)
        
        # Extract legislatura - prioritize ImportStatus data, then XML, finally filename  
        legislatura_sigla = None
        
        # First try: Use legislature data from ImportStatus (most reliable)
        if 'legislatura' in file_info and file_info['legislatura']:
            legislatura_sigla = file_info['legislatura']
            logger.debug(f"Using legislature from ImportStatus: {legislatura_sigla}")
        
        # Second try: Extract from XML content
        elif xml_root is not None:
            try:
                legislatura_sigla = self._extract_legislatura_from_xml(xml_root)
                logger.debug(f"Extracted legislature from XML: {legislatura_sigla}")
            except:
                pass
        
        # Third try: Extract from filename (fallback)
        if not legislatura_sigla:
            try:
                legislatura_sigla = self._extract_legislatura(file_info['file_path'], xml_root)
                logger.debug(f"Extracted legislature from filename: {legislatura_sigla}")
            except Exception as e:
                logger.error(f"Could not extract legislature from any source: {e}")
                raise
        
        legislatura = self._get_or_create_legislatura(legislatura_sigla)
        legislatura_id = legislatura.id
        
        # Process each agenda item
        for agenda_item in xml_root.findall('.//AgendaParlamentar'):
            try:
                success = self._process_agenda_item(agenda_item, legislatura_id)
                results['records_processed'] += 1
                if success:
                    results['records_imported'] += 1
            except Exception as e:
                error_msg = f"Agenda item processing error: {str(e)}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
                results['records_processed'] += 1
        
        return results
    
    
    def _process_agenda_item(self, agenda_item: ET.Element, legislatura_id: int) -> bool:
        """Process individual agenda item using SQLAlchemy ORM"""
        try:
            # Extract basic fields
            id_externo = self._get_int_value(agenda_item, 'Id')
            secao_id = self._get_int_value(agenda_item, 'SectionId')
            secao_nome = self._get_text_value(agenda_item, 'Section')
            tema_id = self._get_int_value(agenda_item, 'ThemeId')
            tema_nome = self._get_text_value(agenda_item, 'Theme')
            order_value = self._get_int_value(agenda_item, 'OrderValue')
            grupo_parlamentar = self._get_text_value(agenda_item, 'ParlamentGroup')
            
            # Extract additional documented fields
            legislatura_designacao = self._get_text_value(agenda_item, 'LegDes')
            orgao_designacao = self._get_text_value(agenda_item, 'OrgDes')
            reuniao_numero = self._get_int_value(agenda_item, 'ReuNumero')
            sessao_numero = self._get_int_value(agenda_item, 'SelNumero')
            
            # Extract dates and times
            event_start_date = self._get_text_value(agenda_item, 'EventStartDate')
            event_start_time = self._get_text_value(agenda_item, 'EventStartTime')
            event_end_date = self._get_text_value(agenda_item, 'EventEndDate')
            event_end_time = self._get_text_value(agenda_item, 'EventEndTime')
            
            # Parse date - must be valid for data integrity
            data_evento = self._parse_date(event_start_date)
            if not data_evento:
                raise ValueError(f"Invalid or missing event date: '{event_start_date}'. Data integrity violation - cannot use artificial dates")
            
            # Parse times
            hora_inicio = self._parse_time(event_start_time)
            hora_fim = self._parse_time(event_end_time)
            
            # Extract other fields
            all_day_event = self._get_boolean_value(agenda_item, 'AllDayEvent')
            titulo = self._get_text_value(agenda_item, 'Title')
            subtitulo = self._get_text_value(agenda_item, 'Subtitle')
            descricao = self._get_text_value(agenda_item, 'InternetText')
            local_evento = self._get_text_value(agenda_item, 'Local')
            link_externo = self._get_text_value(agenda_item, 'Link')
            pos_plenario = self._get_boolean_value(agenda_item, 'PostPlenary')
            
            if not titulo:
                raise ValueError("Missing required Title field. Data integrity violation - cannot generate artificial titles")
            
            # Check if record already exists using SQLAlchemy ORM
            existing_agenda = self.session.query(AgendaParlamentar).filter_by(
                id_externo=id_externo, 
                legislatura_id=legislatura_id
            ).first()
            
            if existing_agenda:
                # Update existing record
                existing_agenda.secao_id = secao_id
                existing_agenda.secao_nome = secao_nome
                existing_agenda.tema_id = tema_id
                existing_agenda.tema_nome = tema_nome
                existing_agenda.order_value = order_value
                existing_agenda.grupo_parlamentar = grupo_parlamentar
                existing_agenda.legislatura_designacao = legislatura_designacao
                existing_agenda.orgao_designacao = orgao_designacao
                existing_agenda.reuniao_numero = reuniao_numero
                existing_agenda.sessao_numero = sessao_numero
                existing_agenda.data_evento = data_evento
                existing_agenda.hora_inicio = hora_inicio
                existing_agenda.hora_fim = hora_fim
                existing_agenda.evento_dia_inteiro = all_day_event
                existing_agenda.titulo = titulo
                existing_agenda.subtitulo = subtitulo
                existing_agenda.descricao = descricao
                existing_agenda.local_evento = local_evento
                existing_agenda.link_externo = link_externo
                existing_agenda.pos_plenario = pos_plenario
            else:
                # Create new record - explicit UUID for immediate availability
                new_agenda = AgendaParlamentar(
                    id=uuid.uuid4(),
                    id_externo=id_externo,
                    legislatura_id=legislatura_id,
                    secao_id=secao_id,
                    secao_nome=secao_nome,
                    tema_id=tema_id,
                    tema_nome=tema_nome,
                    order_value=order_value,
                    grupo_parlamentar=grupo_parlamentar,
                    legislatura_designacao=legislatura_designacao,
                    orgao_designacao=orgao_designacao,
                    reuniao_numero=reuniao_numero,
                    sessao_numero=sessao_numero,
                    data_evento=data_evento,
                    hora_inicio=hora_inicio,
                    hora_fim=hora_fim,
                    evento_dia_inteiro=all_day_event,
                    titulo=titulo,
                    subtitulo=subtitulo,
                    descricao=descricao,
                    local_evento=local_evento,
                    link_externo=link_externo,
                    pos_plenario=pos_plenario
                )
                self._add_with_tracking(new_agenda)
            
            # Process attachments (AnexoEventos structures)
            self._process_agenda_anexos(agenda_item, new_agenda if 'new_agenda' in locals() else existing_agenda)
            
            return True
            
        except Exception as e:
            error_msg = f"Error processing agenda item: {e}"
            logger.error(error_msg)
            logger.error("Data integrity issue detected during agenda item processing")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise RuntimeError(f"Data integrity issue: {error_msg}")
    
    
    def _get_boolean_value(self, parent: ET.Element, tag_name: str) -> bool:
        """Get boolean value from XML element"""
        text_value = self._get_text_value(parent, tag_name)
        if text_value:
            return text_value.lower() in ('true', '1', 'yes')
        return False
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string to Python date object"""
        if not date_str:
            return None
        
        try:
            # Try common Portuguese date format: DD/MM/YYYY
            if '/' in date_str:
                day, month, year = date_str.split('/')
                return date(int(year), int(month), int(day))
            
            # Try ISO format: YYYY-MM-DD
            if '-' in date_str and len(date_str) == 10:
                year, month, day = date_str.split('-')
                return date(int(year), int(month), int(day))
            
        except (ValueError, IndexError) as e:
            logger.warning(f"Could not parse date '{date_str}': {e}")
        
        return None
    
    def _parse_time(self, time_str: str) -> Optional[str]:
        """Parse time string to HH:MM:SS format"""
        if not time_str:
            return None
        
        try:
            # Handle HH:MM:SS format
            if time_str.count(':') == 2:
                return time_str
            
            # Handle HH:MM format
            if time_str.count(':') == 1:
                return f"{time_str}:00"
            
        except Exception:
            logger.warning(f"Could not parse time: {time_str}")
        
        return None
    
    def _process_agenda_anexos(self, agenda_item: ET.Element, agenda_record) -> bool:
        """Process agenda attachments (AnexoEventos structures)"""
        try:
            # Process Permanent Committee attachments
            anexos_comissao = agenda_item.find('AnexosComissaoPermanente')
            if anexos_comissao is not None:
                logger.debug(f"Processing AnexosComissaoPermanente for agenda {agenda_record.id}")
                self._process_anexo_eventos(anexos_comissao, agenda_record.id, 'comissao_permanente')
            
            # Process Plenary attachments
            anexos_plenario = agenda_item.find('AnexosPlenario')
            if anexos_plenario is not None:
                logger.debug(f"Processing AnexosPlenario for agenda {agenda_record.id}")
                self._process_anexo_eventos(anexos_plenario, agenda_record.id, 'plenario')
            
            return True
        except Exception as e:
            logger.error(f"Error processing agenda attachments: {e}")
            return False
    
    def _process_anexo_eventos(self, anexos_container: ET.Element, agenda_id: int, tipo_anexo: str) -> bool:
        """Process individual AnexoEventos structures"""
        try:
            for anexo in anexos_container.findall('.//AnexoEventos'):
                id_field = self._get_text_value(anexo, 'idField')
                tipo_documento = self._get_text_value(anexo, 'tipoDocumentoField')
                titulo = self._get_text_value(anexo, 'tituloField')
                url = self._get_text_value(anexo, 'uRLField')
                
                if not titulo:  # At minimum require titulo for data integrity
                    continue
                
                # Check if anexo already exists
                existing_anexo = self.session.query(AgendaParlamentarAnexo).filter_by(
                    agenda_id=agenda_id,
                    id_field=id_field,
                    tipo_anexo=tipo_anexo
                ).first()
                
                if existing_anexo:
                    # Update existing record
                    existing_anexo.tipo_documento_field = tipo_documento
                    existing_anexo.titulo_field = titulo
                    existing_anexo.url_field = url
                else:
                    # Create new attachment record - explicit UUID for immediate availability
                    anexo_record = AgendaParlamentarAnexo(
                        id=uuid.uuid4(),
                        agenda_id=agenda_id,
                        id_field=id_field,
                        tipo_documento_field=tipo_documento,
                        titulo_field=titulo,
                        url_field=url,
                        tipo_anexo=tipo_anexo
                    )
                    self._add_with_tracking(anexo_record)
                
                logger.debug(f"Processed anexo: {titulo} ({tipo_documento})")
            
            return True
        except Exception as e:
            logger.error(f"Error processing anexo eventos: {e}")
            return False
    
    # NOTE: _get_or_create_legislatura is inherited from EnhancedSchemaMapper (with caching)
    # Updated calling code at line 148-149 to use legislatura.id

    def __del__(self):
        """Cleanup SQLAlchemy session"""
        if hasattr(self, 'session'):
            self.session.close()
    
    def _extract_legislatura_from_xml(self, xml_root: ET.Element) -> str:
        """Extract legislature information from XML LegDes elements"""
        # Look for LegDes elements in the XML content
        for agenda_item in xml_root.findall('.//AgendaParlamentar'):
            leg_des_element = agenda_item.find('LegDes')
            if leg_des_element is not None and leg_des_element.text:
                leg_text = leg_des_element.text.strip()
                if leg_text and leg_text.upper() != 'NULL':
                    return leg_text.upper()
        
        # Fallback - look for any LegDes elements at any level
        leg_des_element = xml_root.find('.//LegDes')
        if leg_des_element is not None and leg_des_element.text:
            leg_text = leg_des_element.text.strip()
            if leg_text and leg_text.upper() != 'NULL':
                return leg_text.upper()
        
        raise Exception("No legislature information found in XML content")

    # NOTE: Roman numeral conversion uses ROMAN_TO_NUMBER from LegislatureHandlerMixin