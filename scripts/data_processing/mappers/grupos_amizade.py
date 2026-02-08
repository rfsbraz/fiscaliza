"""
Parliamentary Friendship Groups Standalone Mapper
================================================

Schema mapper for standalone parliamentary friendship groups files (GrupoDeAmizadeXX.xml).
These files contain comprehensive friendship group data including detailed member information,
meetings, visits, and participant records.

Based on analysis of actual XML structure from GrupoDeAmizadeXV.xml and other legislature files.

XML Structure:
- Root: ArrayOfGrupoDeAmizadeOut
- Main Group: GrupoDeAmizadeOut  
- Members: Composicao/DelegacaoPermanenteMembroOut
- Meetings/Visits: Visitas/GrupoDeAmizadeReuniao
- Participants: Participantes/RelacoesExternasParticipantes

Key differences from deputy activity GPA data:
- Standalone files with complete group information
- Detailed member composition with roles and service periods  
- Meeting and visit records with participant lists
- Not tied to specific deputy activities
"""

import xml.etree.ElementTree as ET
import os
import logging
import uuid
from datetime import datetime
from typing import Dict, Optional, Set, List, Tuple

from .enhanced_base_mapper import EnhancedSchemaMapper, SchemaError

# Import our models
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from database.models import (
    GrupoAmizadeStandalone, GrupoAmizadeMembro, GrupoAmizadeReuniao, 
    GrupoAmizadeParticipante, Legislatura
)

# GPA data is already in meaningful form, no field translation needed

logger = logging.getLogger(__name__)


class GruposAmizadeMapper(EnhancedSchemaMapper):
    """
    Schema mapper for standalone parliamentary friendship groups files
    
    Processes GrupoDeAmizadeXX.xml files containing comprehensive parliamentary
    friendship group data including:
    
    - Basic group information (ID, name, legislature, creation date)
    - Complete member composition with roles and service periods
    - Meeting and visit records with locations and dates
    - Detailed participant information for all events
    
    All field mappings based on actual XML structure analysis with proper
    field conversion using the grupos_amizade translator module.
    """
    
    def __init__(self, session, import_status_record=None):
        super().__init__(session, import_status_record=import_status_record)
        self.processed_groups = 0
        self.processed_members = 0
        self.processed_meetings = 0
        self.processed_participants = 0
        
    def get_expected_fields(self) -> Set[str]:
        """Define expected XML fields for validation - Updated with Reunioes support"""
        return {
            # Root structure  
            'ArrayOfGrupoDeAmizadeOut',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut',
            
            # Main group fields  
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Id',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Nome',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Legislatura',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Sessao',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.DataCriacao',
            
            # Member composition
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Composicao',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Composicao.DelegacaoPermanenteMembroOut',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Composicao.DelegacaoPermanenteMembroOut.Nome',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Composicao.DelegacaoPermanenteMembroOut.Gp',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Composicao.DelegacaoPermanenteMembroOut.Cargo',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Composicao.DelegacaoPermanenteMembroOut.DataInicio',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Composicao.DelegacaoPermanenteMembroOut.DataFim',
            
            # Meetings and visits - dual structure support (Reunioes and Visitas)
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Reunioes',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Visitas',
            
            # Meetings under Reunioes structure
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Reunioes.GrupoDeAmizadeReuniao',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Reunioes.GrupoDeAmizadeReuniao.Id',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Reunioes.GrupoDeAmizadeReuniao.Nome',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Reunioes.GrupoDeAmizadeReuniao.Tipo',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Reunioes.GrupoDeAmizadeReuniao.Local',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Reunioes.GrupoDeAmizadeReuniao.DataInicio',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Reunioes.GrupoDeAmizadeReuniao.DataFim',
            
            # Meetings under Visitas structure (legacy support)
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Visitas.GrupoDeAmizadeReuniao',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Visitas.GrupoDeAmizadeReuniao.Id',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Visitas.GrupoDeAmizadeReuniao.Nome',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Visitas.GrupoDeAmizadeReuniao.Tipo',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Visitas.GrupoDeAmizadeReuniao.Local',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Visitas.GrupoDeAmizadeReuniao.DataInicio',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Visitas.GrupoDeAmizadeReuniao.DataFim',
            
            # Participants under Reunioes structure
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Reunioes.GrupoDeAmizadeReuniao.Participantes',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Reunioes.GrupoDeAmizadeReuniao.Participantes.RelacoesExternasParticipantes',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Reunioes.GrupoDeAmizadeReuniao.Participantes.RelacoesExternasParticipantes.Id',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Reunioes.GrupoDeAmizadeReuniao.Participantes.RelacoesExternasParticipantes.Nome',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Reunioes.GrupoDeAmizadeReuniao.Participantes.RelacoesExternasParticipantes.Tipo',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Reunioes.GrupoDeAmizadeReuniao.Participantes.RelacoesExternasParticipantes.Gp',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Reunioes.GrupoDeAmizadeReuniao.Participantes.RelacoesExternasParticipantes.Leg',
            
            # Participants under Visitas structure (legacy support)
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Visitas.GrupoDeAmizadeReuniao.Participantes',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Visitas.GrupoDeAmizadeReuniao.Participantes.RelacoesExternasParticipantes',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Visitas.GrupoDeAmizadeReuniao.Participantes.RelacoesExternasParticipantes.Id',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Visitas.GrupoDeAmizadeReuniao.Participantes.RelacoesExternasParticipantes.Nome',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Visitas.GrupoDeAmizadeReuniao.Participantes.RelacoesExternasParticipantes.Tipo',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Visitas.GrupoDeAmizadeReuniao.Participantes.RelacoesExternasParticipantes.Gp',
            'ArrayOfGrupoDeAmizadeOut.GrupoDeAmizadeOut.Visitas.GrupoDeAmizadeReuniao.Participantes.RelacoesExternasParticipantes.Leg'
        }
    
    def validate_and_map(self, xml_root: ET.Element, file_info: Dict, strict_mode: bool = False) -> Dict:
        """Map parliamentary friendship groups to database"""
        results = {"records_processed": 0, "records_imported": 0, "errors": []}
        
        try:
            # Validate schema coverage according to strict mode
            self.validate_schema_coverage(xml_root, file_info, strict_mode)
            
            # Validate root structure
            if xml_root.tag != 'ArrayOfGrupoDeAmizadeOut':
                raise SchemaError(f"Unexpected root element: {xml_root.tag}, expected: ArrayOfGrupoDeAmizadeOut")
            
            # Process each friendship group
            grupo_elements = xml_root.findall('GrupoDeAmizadeOut')
            if not grupo_elements:
                logger.warning(f"No friendship groups found in file")
                return results
                
            for grupo_element in grupo_elements:
                try:
                    success = self._process_grupo_amizade(grupo_element)
                    results["records_processed"] += 1
                    if success:
                        results["records_imported"] += 1
                except Exception as e:
                    error_msg = f"Group processing error: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
                    results["records_processed"] += 1
                    raise RuntimeError(f"Data integrity issue: {error_msg}")
                
            logger.info(f"Successfully processed {len(grupo_elements)} friendship groups")
            logger.info(f"Total processed: {self.processed_groups} groups, {self.processed_members} members, "
                       f"{self.processed_meetings} meetings, {self.processed_participants} participants")
            
            return results
            
        except Exception as e:
            error_msg = f"Critical error processing friendship groups: {str(e)}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
            raise RuntimeError(f"Data integrity issue: {error_msg}")
    
    def _process_grupo_amizade(self, grupo_element: ET.Element) -> Optional[GrupoAmizadeStandalone]:
        """Process a single friendship group element"""
        try:
            # Extract basic group information
            group_id = self._get_int_value(grupo_element, 'Id')
            nome = self._get_text_value(grupo_element, 'Nome')
            legislatura = self._get_text_value(grupo_element, 'Legislatura')
            sessao = self._get_int_value(grupo_element, 'Sessao')
            data_criacao_str = self._get_text_value(grupo_element, 'DataCriacao')
            
            # Validate required fields
            if not group_id:
                logger.warning("Friendship group missing required Id field, skipping")
                return None
            if not nome:
                logger.warning(f"Friendship group {group_id} missing required Nome field, skipping")
                return None
            if not legislatura:
                logger.warning(f"Friendship group {group_id} missing required Legislatura field, skipping")
                return None
            
            # Parse data criacao using standard base mapper method
            data_criacao = self._parse_date(data_criacao_str) if data_criacao_str else None
            
            # Check if group already exists (avoid duplicates)
            existing_group = self.session.query(GrupoAmizadeStandalone).filter_by(
                group_id=group_id, 
                legislatura=legislatura
            ).first()
            
            if existing_group:
                logger.info(f"Friendship group {group_id} ({nome}) already exists for legislature {legislatura}, updating")
                grupo = existing_group
                grupo.nome = nome
                grupo.sessao = sessao
                grupo.data_criacao = data_criacao
            else:
                # Create new friendship group
                grupo = GrupoAmizadeStandalone(
                    id=uuid.uuid4(),
                    group_id=group_id,
                    nome=nome,
                    legislatura=legislatura,
                    sessao=sessao,
                    data_criacao=data_criacao
                )
                self._add_with_tracking(grupo)
            
            # Process members
            composicao = grupo_element.find('Composicao')
            if composicao is not None:
                # Clear existing members for updates
                if existing_group:
                    self.session.query(GrupoAmizadeMembro).filter_by(grupo_amizade_id=grupo.id).delete()
                
                for membro_element in composicao.findall('DelegacaoPermanenteMembroOut'):
                    self._process_membro(membro_element, grupo.id)
            
            # Process meetings/visits - handle both Reunioes and Visitas structures
            reunioes = grupo_element.find('Reunioes')
            visitas = grupo_element.find('Visitas')
            
            if reunioes is not None or visitas is not None:
                # Clear existing meetings for updates
                if existing_group:
                    self.session.query(GrupoAmizadeReuniao).filter_by(grupo_amizade_id=grupo.id).delete()
                
                # Process meetings from Reunioes structure (primary)
                if reunioes is not None:
                    for reuniao_element in reunioes.findall('GrupoDeAmizadeReuniao'):
                        self._process_reuniao(reuniao_element, grupo.id, event_source="Reunioes")
                
                # Process meetings from Visitas structure (fallback/legacy)
                if visitas is not None:
                    for reuniao_element in visitas.findall('GrupoDeAmizadeReuniao'):
                        self._process_reuniao(reuniao_element, grupo.id, event_source="Visitas")
            
            self.processed_groups += 1
            logger.debug(f"Processed friendship group: {group_id} ({nome}) - Legislature {legislatura}")
            
            return grupo
            
        except Exception as e:
            logger.error(f"Error processing friendship group: {e}")
            return None
    
    def _process_membro(self, membro_element: ET.Element, grupo_id: int) -> Optional[GrupoAmizadeMembro]:
        """Process a single group member element"""
        try:
            # Extract member information
            nome = self._get_text_value(membro_element, 'Nome')
            grupo_parlamentar = self._get_text_value(membro_element, 'Gp')
            cargo = self._get_text_value(membro_element, 'Cargo')
            data_inicio_str = self._get_text_value(membro_element, 'DataInicio')
            data_fim_str = self._get_text_value(membro_element, 'DataFim')
            
            if not nome:
                logger.warning("Group member missing required Nome field, skipping")
                return None
            
            # Parse dates using standard base mapper method
            data_inicio = self._parse_date(data_inicio_str) if data_inicio_str else None
            data_fim = self._parse_date(data_fim_str) if data_fim_str else None
            
            # Create member record
            membro = GrupoAmizadeMembro(
                id=uuid.uuid4(),
                grupo_amizade_id=grupo_id,
                nome=nome,
                grupo_parlamentar=grupo_parlamentar,
                cargo=cargo,
                data_inicio=data_inicio,
                data_fim=data_fim
            )

            self._add_with_tracking(membro)
            self.processed_members += 1
            
            logger.debug(f"Processed member: {nome} ({cargo}) - GP: {grupo_parlamentar}")
            
            return membro
            
        except Exception as e:
            logger.error(f"Error processing group member: {e}")
            return None
    
    def _process_reuniao(self, reuniao_element: ET.Element, grupo_id: int, event_source: str = "Visitas") -> Optional[GrupoAmizadeReuniao]:
        """Process a single meeting/visit element"""
        try:
            # Extract meeting information
            meeting_id = self._get_int_value(reuniao_element, 'Id')
            nome = self._get_text_value(reuniao_element, 'Nome')
            tipo = self._get_text_value(reuniao_element, 'Tipo')
            local = self._get_text_value(reuniao_element, 'Local')
            data_inicio_str = self._get_text_value(reuniao_element, 'DataInicio')
            data_fim_str = self._get_text_value(reuniao_element, 'DataFim')
            
            # Validate required fields
            if not meeting_id:
                logger.warning("Meeting missing required Id field, skipping")
                return None
            if not nome:
                logger.warning(f"Meeting {meeting_id} missing required Nome field, skipping")
                return None
            if not data_inicio_str:
                logger.warning(f"Meeting {meeting_id} missing required DataInicio field, skipping")
                return None
            
            # Parse dates using standard base mapper method
            data_inicio = self._parse_date(data_inicio_str) if data_inicio_str else None
            data_fim = self._parse_date(data_fim_str) if data_fim_str else None
            
            if not data_inicio:
                logger.warning(f"Meeting {meeting_id} failed to parse DataInicio: {data_inicio_str}")
                return None
            
            # Create meeting record
            reuniao = GrupoAmizadeReuniao(
                id=uuid.uuid4(),
                grupo_amizade_id=grupo_id,
                meeting_id=meeting_id,
                nome=nome,
                tipo=tipo,
                local=local,
                data_inicio=data_inicio,
                data_fim=data_fim,
                event_source=event_source
            )

            self._add_with_tracking(reuniao)
            
            # Process participants
            participantes = reuniao_element.find('Participantes')
            if participantes is not None:
                for participante_element in participantes.findall('RelacoesExternasParticipantes'):
                    self._process_participante(participante_element, reuniao.id)
            
            self.processed_meetings += 1
            logger.debug(f"Processed meeting: {meeting_id} ({nome[:50]}) - Location: {local}")
            
            return reuniao
            
        except Exception as e:
            logger.error(f"Error processing meeting: {e}")
            return None
    
    def _process_participante(self, participante_element: ET.Element, reuniao_id: int) -> Optional[GrupoAmizadeParticipante]:
        """Process a single meeting participant element"""
        try:
            # Extract participant information
            participant_id = self._get_int_value(participante_element, 'Id')
            nome = self._get_text_value(participante_element, 'Nome')
            tipo = self._get_text_value(participante_element, 'Tipo')
            grupo_parlamentar = self._get_text_value(participante_element, 'Gp')
            legislatura = self._get_text_value(participante_element, 'Leg')
            
            # Validate required fields
            if not participant_id:
                logger.warning("Participant missing required Id field, skipping")
                return None
            if not nome:
                logger.warning(f"Participant {participant_id} missing required Nome field, skipping")
                return None
            if not tipo:
                logger.warning(f"Participant {participant_id} missing required Tipo field, skipping")  
                return None
            
            # Create participant record
            participante = GrupoAmizadeParticipante(
                id=uuid.uuid4(),
                reuniao_id=reuniao_id,
                participant_id=participant_id,
                nome=nome,
                tipo=tipo,
                grupo_parlamentar=grupo_parlamentar,
                legislatura=legislatura
            )

            self._add_with_tracking(participante)
            self.processed_participants += 1
            
            logger.debug(f"Processed participant: {participant_id} ({nome}) - Type: {tipo}")
            
            return participante
            
        except Exception as e:
            logger.error(f"Error processing participant: {e}")
            return None
    
    def _get_text_value(self, element: ET.Element, tag: str) -> Optional[str]:
        """Safely extract text value from XML element"""
        child = element.find(tag)
        if child is not None and child.text:
            return child.text.strip()
        return None
    
    def _get_int_value(self, element: ET.Element, tag: str) -> Optional[int]:
        """Safely extract integer value from XML element"""
        text_value = self._get_text_value(element, tag)
        if text_value:
            return self._safe_int(text_value)
        return None
    
    def get_processing_stats(self) -> Dict[str, int]:
        """Return processing statistics"""
        return {
            'processed_groups': self.processed_groups,
            'processed_members': self.processed_members,
            'processed_meetings': self.processed_meetings,
            'processed_participants': self.processed_participants
        }