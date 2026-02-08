"""
Enhanced Base Schema Mapper
==========================

Consolidated base classes to eliminate code duplication across all schema mappers.
Provides common functionality for SQLAlchemy session management, legislature handling,
XML processing, and error handling.
"""

import logging
import os
import re
import uuid

# Import models
import sys
import xml.etree.ElementTree as ET

# SQLAlchemy session handling (sessions passed from unified importer)
from abc import ABC, abstractmethod
from datetime import datetime
from sqlalchemy.dialects.postgresql import insert as pg_insert
from .common_utilities import DataValidationUtils
from typing import Any, Dict, List, Optional, Set

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from database.models import Legislatura, Deputado, DeputyIdentityMapping, Coligacao, ColigacaoPartido
from .coalition_detector import CoalitionDetector

logger = logging.getLogger(__name__)


class CacheMixin:
    """
    Mixin providing entity caching and batch processing capabilities.

    This mixin dramatically improves import performance by:
    1. Caching frequently accessed entities (Legislatura, Deputado, Partido)
    2. Batching database flushes to reduce round-trips
    3. Providing foundation for import order dependencies

    All caches are session-scoped and should be cleared between processing runs.
    """

    # Batch processing configuration
    BATCH_SIZE = 100  # Flush every N records for performance

    # Import order dependencies - override in child classes to declare dependencies
    # Example: IMPORT_DEPENDENCIES = ['biografico', 'legislaturas']
    IMPORT_DEPENDENCIES: List[str] = []

    def _init_caches(self):
        """Initialize all entity caches - call from __init__"""
        # Core entity caches
        self._legislatura_cache: Dict[str, 'Legislatura'] = {}  # numero -> Legislatura
        self._deputado_cache: Dict[str, 'Deputado'] = {}  # Various keys -> Deputado
        self._partido_cache: Dict[str, Any] = {}  # sigla -> Partido (when model exists)

        # Batch flush counter
        self._pending_count = 0

    def _batch_flush(self, force: bool = False) -> None:
        """
        Batch flush strategy - only flush every BATCH_SIZE operations.
        This dramatically reduces database round-trips.

        Args:
            force: If True, flush immediately regardless of pending count
        """
        self._pending_count += 1
        if force or self._pending_count >= self.BATCH_SIZE:
            self.session.flush()
            self._pending_count = 0

    def _preload_shared_caches(self, legislatura: 'Legislatura' = None) -> None:
        """
        Preload shared entity caches for performance optimization.

        Call this at the start of processing to pre-populate caches with
        existing entities, avoiding individual queries during processing.

        Args:
            legislatura: Optional legislature to scope preloading
        """
        logger.info("Preloading shared entity caches...")

        # Preload all legislaturas (typically small table)
        from database.models import Legislatura as LegislaturaModel
        all_legislaturas = self.session.query(LegislaturaModel).all()
        for leg in all_legislaturas:
            self._legislatura_cache[leg.numero] = leg
        logger.debug(f"Cached {len(self._legislatura_cache)} legislaturas")

        # Preload deputies for specific legislature if provided
        if legislatura:
            from database.models import Deputado as DeputadoModel
            deputies = self.session.query(DeputadoModel).filter_by(
                legislatura_id=legislatura.id
            ).all()
            for deputy in deputies:
                # Cache by multiple keys for flexible lookup - use xml_source_id for FK resolution
                if deputy.xml_source_id:
                    self._deputado_cache[f"xml_source_id_{deputy.xml_source_id}"] = deputy
                if deputy.id_cadastro:
                    self._deputado_cache[f"cadastro_{deputy.id_cadastro}"] = deputy
            logger.debug(f"Cached {len(deputies)} deputies for legislature {legislatura.numero}")

    def _clear_caches(self) -> None:
        """
        Clear all entity caches.

        Call this when switching legislatures or after processing completes
        to free memory and ensure fresh data on next processing run.
        """
        if hasattr(self, '_legislatura_cache'):
            self._legislatura_cache.clear()
        if hasattr(self, '_deputado_cache'):
            self._deputado_cache.clear()
        if hasattr(self, '_partido_cache'):
            self._partido_cache.clear()
        self._pending_count = 0
        logger.debug("Cleared all entity caches")

    def _new_id(self) -> uuid.UUID:
        """
        Generate a new UUID for primary key.

        With UUID primary keys, IDs are generated client-side before database insertion.
        This eliminates the need for session.flush() to obtain IDs after session.add().

        Returns:
            A new UUID4 suitable for use as a primary key
        """
        return uuid.uuid4()

    def _get_cached_legislatura(self, numero: str) -> Optional['Legislatura']:
        """Get legislatura from cache if available"""
        return self._legislatura_cache.get(numero)

    def _cache_legislatura(self, legislatura: 'Legislatura') -> None:
        """Add legislatura to cache"""
        self._legislatura_cache[legislatura.numero] = legislatura

    def _get_cached_deputado(self, key: str) -> Optional['Deputado']:
        """Get deputado from cache if available"""
        return self._deputado_cache.get(key)

    def _cache_deputado(self, deputado: 'Deputado') -> None:
        """Add deputado to cache with multiple lookup keys"""
        if deputado.xml_source_id:
            self._deputado_cache[f"xml_source_id_{deputado.xml_source_id}"] = deputado
        if deputado.id_cadastro:
            self._deputado_cache[f"cadastro_{deputado.id_cadastro}"] = deputado


class CoalitionDetectionMixin:
    """Mixin providing coalition detection capabilities to mappers"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.coalition_detector = CoalitionDetector()
        self._coalition_cache = {}  # Cache detection results
        self._created_coalitions = {}  # Cache created Coligacao objects by sigla
    
    def detect_and_process_coalition(self, par_sigla: str, par_des: str = None) -> Dict:
        """
        Detect if par_sigla is a coalition and process accordingly
        
        Returns:
            Dict with coalition information and processing instructions
        """
        if not par_sigla:
            return {"is_coalition": False, "entity_type": "unknown"}
        
        # Check cache first
        if par_sigla in self._coalition_cache:
            return self._coalition_cache[par_sigla]
        
        # Detect coalition
        detection = self.coalition_detector.detect(par_sigla)
        
        result = {
            "is_coalition": detection.is_coalition,
            "entity_type": "coligacao" if detection.is_coalition else "partido", 
            "confidence": detection.confidence,
            "coalition_sigla": par_sigla,  # Use the input sigla as coalition sigla
            "coalition_name": detection.coalition_name,
            "component_parties": detection.component_parties,
            "detection_method": detection.detection_method,
            "political_spectrum": detection.political_spectrum,
            "formation_date": detection.formation_date
        }
        
        # Cache result
        self._coalition_cache[par_sigla] = result
        return result
    
    def get_or_create_coalition(self, coalition_info: Dict) -> Optional[Coligacao]:
        """Create or retrieve coalition record using upsert for parallel safety"""
        if not coalition_info["is_coalition"]:
            return None

        sigla = coalition_info.get("coalition_sigla", "")
        if not sigla:
            return None

        # Check in-memory cache first (handles uncommitted objects in same session)
        if sigla in self._created_coalitions:
            return self._created_coalitions[sigla]

        # Use PostgreSQL upsert for parallel-safe coalition creation
        # This prevents UniqueViolation when multiple workers try to create the same coalition
        new_id = uuid.uuid4()
        nome = coalition_info.get("coalition_name", f"Coligação {sigla}")

        try:
            stmt = pg_insert(Coligacao.__table__).values(
                id=new_id,
                sigla=sigla,
                nome=nome,
                nome_eleitoral=coalition_info.get("coalition_name"),
                data_formacao=coalition_info.get("formation_date"),
                tipo_coligacao="eleitoral",
                espectro_politico=coalition_info.get("political_spectrum"),
                confianca_detecao=coalition_info.get("confidence", 0.0)
            ).on_conflict_do_update(
                index_elements=['sigla'],  # Unique constraint column
                set_={
                    # On conflict, update these fields (keep existing values for most)
                    'nome': nome,
                    'confianca_detecao': coalition_info.get("confidence", 0.0)
                }
            ).returning(Coligacao.__table__.c.id)

            result = self.session.execute(stmt)
            coalition_id = result.scalar()
            self.session.flush()

            # Fetch the ORM object (either newly created or existing)
            coalition = self.session.query(Coligacao).filter_by(id=coalition_id).first()

            if coalition:
                # Cache the coalition
                self._created_coalitions[sigla] = coalition

                # Create component party relationships (use upsert too)
                for component in coalition_info.get("component_parties", []):
                    rel_stmt = pg_insert(ColigacaoPartido.__table__).values(
                        id=uuid.uuid4(),
                        coligacao_id=coalition.id,
                        partido_sigla=component["sigla"],
                        partido_nome=component["nome"],
                        ativo=True,
                        papel_coligacao="componente",
                        confianca_detecao=coalition_info.get("confidence", 0.0)
                    ).on_conflict_do_nothing(
                        index_elements=['coligacao_id', 'partido_sigla']
                    )
                    self.session.execute(rel_stmt)

                if str(coalition_id) == str(new_id):
                    logger.info(f"Created coalition: {sigla} with {len(coalition_info.get('component_parties', []))} components")
                else:
                    logger.debug(f"Found existing coalition '{sigla}' via upsert")

            return coalition

        except Exception as e:
            logger.error(f"Error creating coalition {sigla}: {e}")
            # Remove from cache on error
            self._created_coalitions.pop(sigla, None)
            raise  # Re-raise to abort transaction properly
    
    def update_mandate_coalition_context(self, mandate, par_sigla: str):
        """Update mandate record with coalition context"""
        coalition_info = self.detect_and_process_coalition(par_sigla)
        
        # Update mandate fields
        mandate.tipo_entidade_politica = coalition_info["entity_type"]
        mandate.eh_coligacao = coalition_info["is_coalition"]
        mandate.confianca_detecao_coligacao = coalition_info["confidence"]
        
        # Link to coalition if detected
        if coalition_info["is_coalition"]:
            coalition = self.get_or_create_coalition(coalition_info)
            if coalition:
                mandate.coligacao_id = coalition.id
        
        return mandate


class SchemaError(Exception):
    """Raised when schema validation fails - unmapped fields detected"""

    pass


class DatabaseSessionMixin:
    """Mixin providing SQLAlchemy session management"""

    def __init__(self, session):
        """Initialize with SQLAlchemy session"""
        # Only accept SQLAlchemy sessions - unified importer passes these
        self.session = session
        self.engine = self.session.bind
        self._owns_session = False

    def close_session(self):
        """Close session if we own it"""
        if self._owns_session and self.session:
            self.session.close()

    def commit_transaction(self):
        """Commit current transaction"""
        try:
            self.session.commit()
        except Exception as e:
            error_msg = f"Transaction commit failed: {str(e)}"
            logger.error(error_msg)
            self.session.rollback()
            raise RuntimeError(error_msg)

    def rollback_transaction(self):
        """Rollback transaction and raise exception with details"""
        logger.error("Data integrity issue detected - rolling back transaction")
        try:
            self.session.rollback()
        except Exception as rollback_error:
            logger.error(f"Rollback failed: {rollback_error}")
        raise RuntimeError("Data integrity issue detected during processing")


class LegislatureHandlerMixin:
    """Mixin providing legislature extraction and management"""

    # Roman numeral mapping
    ROMAN_TO_NUMBER = {
        "CONSTITUINTE": 0,
        "I": 1,
        "IA": 1,
        "IB": 1,
        "II": 2,
        "III": 3,
        "IV": 4,
        "V": 5,
        "VI": 6,
        "VII": 7,
        "VIII": 8,
        "IX": 9,
        "X": 10,
        "XI": 11,
        "XII": 12,
        "XIII": 13,
        "XIV": 14,
        "XV": 15,
        "XVI": 16,
        "XVII": 17,
    }

    # Create NUMBER_TO_ROMAN mapping, preferring main periods over sub-periods
    NUMBER_TO_ROMAN = {
        0: 'CONSTITUINTE', 1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V',
        6: 'VI', 7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X', 11: 'XI',
        12: 'XII', 13: 'XIII', 14: 'XIV', 15: 'XV', 16: 'XVI', 17: 'XVII'
    }

    def _extract_legislatura(self, file_path: str, xml_root: ET.Element) -> str:
        """Extract legislatura from filename or XML content with comprehensive fallback"""

        # Try filename first - most reliable (case-insensitive)
        filename = os.path.basename(file_path)
        # Use specific, ordered patterns to avoid false matches
        # Order by length (longest first) to ensure correct matching
        sorted_legislatures = [
            "CONSTITUINTE",
            "XVII",
            "XVI",
            "XV",
            "XIV",
            "XIII",
            "XII",
            "XI",
            "VIII",
            "VII",
            "VI",
            "IV",
            "III",
            "IB",
            "IA",
            "II",
            "IX",
            "X",
            "V",
            "I",
        ]

        # Check each legislature individually with specific context patterns
        for legislature in sorted_legislatures:
            patterns = [
                # Pattern 1: After known prefixes (RegistoBiografico, RegistoInteresses, Atividade, etc.)
                rf"(Biografico|Interesses|Atividade.*|Iniciativas|Intervencoes|File|Data){legislature}\.xml$",
                # Pattern 2: After Composicao (for OrgaoComposicao files)
                rf"(Composicao){legislature}\.xml$",
                # Pattern 3: After specific meeting types and other common prefixes
                rf"(ReuniaoNacional|Reuniao|Nacional|Grupo.*Amizade|Agenda|Peticoes|Diploma){legislature}\.xml$",
                # Pattern 4: After underscore/dash
                rf"[_-]{legislature}\.xml$",
                # Pattern 5: Before underscore/dash
                rf"^{legislature}[_-]",
                # Pattern 6: Standalone at start or end
                rf"^{legislature}([^A-Za-z]|$)",
                rf"[^A-Za-z]{legislature}\.xml$",
            ]

            for i, pattern in enumerate(patterns):
                leg_match = re.search(pattern, filename, re.IGNORECASE)
                if leg_match:
                    return legislature

        # Try XML content - multiple possible locations (only if xml_root is provided)
        if xml_root is not None:
            xml_patterns = [
                ".//Legislatura",
                ".//LegDes",
                ".//IniLeg",
                ".//leg",
                ".//Leg",
            ]

            for pattern in xml_patterns:
                leg_element = xml_root.find(pattern)
                if leg_element is not None and leg_element.text:
                    leg_text = leg_element.text.strip()

                    # Handle numeric format
                    if leg_text.isdigit():
                        leg_num = int(leg_text)
                        if leg_num in self.NUMBER_TO_ROMAN:
                            result = self.NUMBER_TO_ROMAN[leg_num]
                            return result

                    # Handle roman numeral format
                    if leg_text.upper() in self.ROMAN_TO_NUMBER:
                        result = leg_text.upper()
                        return result

                    # Handle partial matches for CONSTITUINTE
                    if leg_text.upper().startswith("CONS"):
                        return "CONSTITUINTE"

        # Final fallback - extract from directory structure (case-insensitive)
        # Pattern 1: Full legislature directory names (with or without "_Legislatura" suffix)
        path_match = re.search(
            r"[/\\\\](CONSTITUINTE|XVII|XVI|XV|XIV|XIII|XII|XI|VIII|VII|VI|IV|III|IB|IA|IX|II|X|V|I)(_?[Ll]egislatura)?[/\\\\]",
            file_path,
            re.IGNORECASE,
        )
        if path_match:
            result = path_match.group(1).upper()
            return result
            
        # Pattern 2: Legislature names in filename (with word boundaries to avoid false matches)
        filename_match = re.search(
            r"\b(CONSTITUINTE|XVII|XVI|XV|XIV|XIII|XII|XI|VIII|VII|VI|IV|III|IB|IA|IX|II|X|V|I)\b",
            filename,
            re.IGNORECASE,
        )
        if filename_match:
            result = filename_match.group(1).upper()
            return result

        raise SchemaError(f"Could not extract legislatura from file path: {file_path}")

    def _extract_legislatura_from_xml_content(self, leg_des: str) -> str:
        """
        Extract and normalize legislature identifier from XML LegDes content.
        
        This method handles the specific format of legislature identifiers found in
        XML LegDes fields and converts them to our standardized legislature format.
        
        Args:
            leg_des: Legislature identifier from XML (e.g. 'XVII', '17', 'CONSTITUINTE')
            
        Returns:
            Standardized legislature identifier
            
        Examples:
            'XVII' -> 'XVII'
            '17' -> 'XVII' 
            'CONSTITUINTE' -> 'CONSTITUINTE'
        """
        if not leg_des:
            return None
            
        leg_des = leg_des.strip().upper()
        
        # Direct match for known legislature formats
        if leg_des in ['CONSTITUINTE', 'XVII', 'XVI', 'XV', 'XIV', 'XIII', 'XII', 
                       'XI', 'X', 'IX', 'VIII', 'VII', 'VI', 'V', 'IV', 'III', 
                       'II', 'I', 'IA', 'IB']:
            return leg_des
            
        # Convert numeric to roman
        if leg_des.isdigit():
            leg_num = int(leg_des)
            if leg_num in self.NUMBER_TO_ROMAN:
                return self.NUMBER_TO_ROMAN[leg_num]
                
        # Handle special variations
        if leg_des in ['CONS', 'CON', 'CONSTITUENT']:
            return 'CONSTITUINTE'
            
        # Return as-is if we can't normalize it
        logger.warning(f"Unknown legislature format in XML LegDes: '{leg_des}', returning as-is")
        return leg_des

    def _get_or_create_legislatura(self, legislatura_sigla: str) -> Legislatura:
        """
        Get existing or create new legislatura record by Roman numeral (cached).

        Uses CacheMixin cache if available for performance optimization.
        """
        logger.debug(f"_get_or_create_legislatura called with sigla: '{legislatura_sigla}'")

        if not hasattr(self, "session"):
            raise AttributeError(
                "Session not available - ensure DatabaseSessionMixin is used"
            )

        # Normalize input
        normalized_sigla = legislatura_sigla.upper().strip()
        if not normalized_sigla:
            raise ValueError("legislatura_sigla cannot be empty or whitespace-only")

        # Map variations to standard forms
        legislature_mappings = {
            # CONSTITUINTE variations
            "CONSTITUINTE": "CONSTITUINTE",
            "CONSTITUENTE": "CONSTITUINTE",
            "CONS": "CONSTITUINTE",
            "CONST": "CONSTITUINTE",
            # First legislature variations
            "I": "I",
            "IA": "I",
            "IB": "I",
            # All other Roman numerals (no variations)
            "II": "II", "III": "III", "IV": "IV", "V": "V", "VI": "VI",
            "VII": "VII", "VIII": "VIII", "IX": "IX", "X": "X", "XI": "XI",
            "XII": "XII", "XIII": "XIII", "XIV": "XIV", "XV": "XV",
            "XVI": "XVI", "XVII": "XVII", "XVIII": "XVIII"
        }

        # Get the canonical form
        target_legislature = legislature_mappings.get(normalized_sigla, normalized_sigla)
        logger.debug(f"Mapped '{legislatura_sigla}' to '{target_legislature}'")

        # Check cache first (if CacheMixin is available)
        if hasattr(self, '_legislatura_cache') and target_legislature in self._legislatura_cache:
            logger.debug(f"Cache hit for legislatura '{target_legislature}'")
            return self._legislatura_cache[target_legislature]

        # Build designacao for potential insert
        if target_legislature == "CONSTITUINTE":
            designacao = "Assembleia Constituinte"
        else:
            leg_number = self.ROMAN_TO_NUMBER.get(target_legislature, 0)
            designacao = f"{leg_number}.ª Legislatura" if leg_number > 0 else target_legislature

        # Use PostgreSQL upsert to handle race conditions in parallel imports
        # This prevents UniqueViolation when multiple workers try to create the same legislatura
        new_id = self._new_id()
        stmt = pg_insert(Legislatura.__table__).values(
            id=new_id,
            numero=target_legislature,
            designacao=designacao,
            data_inicio=None,
            data_fim=None,
        ).on_conflict_do_update(
            index_elements=['numero'],  # Unique constraint column
            set_={
                # On conflict, keep existing values (effectively a no-op update)
                'designacao': Legislatura.__table__.c.designacao
            }
        ).returning(Legislatura.__table__.c.id)

        result = self.session.execute(stmt)
        row = result.fetchone()
        legislatura_id = row[0]
        self.session.flush()

        # Fetch the ORM object (either newly created or existing)
        legislatura = self.session.query(Legislatura).filter_by(id=legislatura_id).first()

        if legislatura:
            # Cache for future lookups
            if hasattr(self, '_legislatura_cache'):
                self._legislatura_cache[target_legislature] = legislatura

            if str(legislatura_id) == str(new_id):
                logger.info(f"Created new legislatura: {target_legislature} (ID: {legislatura.id})")
            else:
                logger.debug(f"Found existing legislatura '{target_legislature}' (ID: {legislatura.id}) via upsert")

        return legislatura

    def _get_legislatura_id(self, file_info: Dict) -> int:
        """
        Extract legislature ID from file info for deputy records.

        Args:
            file_info: Dictionary containing file_path and other metadata

        Returns:
            Legislature ID for use in deputado records
        """
        logger.info(f"[LEGISLATURE_ID] Getting legislature ID from file_info: {file_info}")
        
        if not hasattr(self, "session"):
            raise AttributeError(
                "Session not available - ensure DatabaseSessionMixin is used"
            )

        # Extract legislatura sigla from file path
        file_path = file_info.get("file_path", "")
        logger.info(f"[LEGISLATURE_ID] Extracting from file path: {file_path}")
        legislatura_sigla = self._extract_legislatura(file_path, None)
        logger.info(f"[LEGISLATURE_ID] Extracted legislature sigla: '{legislatura_sigla}'")

        # Get or create the legislatura record
        logger.info(f"[LEGISLATURE_ID] Getting or creating legislature record for sigla: '{legislatura_sigla}'")
        legislatura = self._get_or_create_legislatura(legislatura_sigla)
        logger.info(f"[LEGISLATURE_ID] Got legislature with ID={legislatura.id}, numero='{legislatura.numero}'")

        return legislatura.id

    def _get_or_create_deputado(self, record_id: int, id_cadastro: int, nome: str, nome_completo: str = None, legislatura_id: int = None, xml_context: ET.Element = None) -> Deputado:
        """
        Get or create deputy record with UUID primary key handling (cached).

        With UUID primary keys:
        - xml_source_id stores the original XML DepId for foreign key reference resolution
        - id is a UUID generated automatically (no flush needed)
        - id_cadastro tracks the same person across legislatures

        IMPORTANT: LegDes from XML takes precedence over filename-based legislature extraction
        to handle cases where files contain data for multiple legislatures.

        Uses CacheMixin cache if available for performance optimization.

        Args:
            record_id: The original DepId from XML (stored in xml_source_id for FK resolution)
            id_cadastro: The cadastral ID for linking the same person across legislatures
            nome: Deputy's parliamentary name
            nome_completo: Deputy's full name (optional)
            legislatura_id: Legislature ID (optional, can be derived from context)
            xml_context: XML element context to extract LegDes (takes precedence over filename)

        Returns:
            Deputado record with UUID id and xml_source_id set to record_id
        """
        if not hasattr(self, "session"):
            raise AttributeError("Session not available - ensure DatabaseSessionMixin is used")

        # Check cache first (if CacheMixin is available) - use xml_source_id as cache key
        cache_key = f"xml_source_id_{record_id}"
        if hasattr(self, '_deputado_cache') and cache_key in self._deputado_cache:
            deputado = self._deputado_cache[cache_key]
            # Update with any new information we have
            if nome_completo and not deputado.nome_completo:
                deputado.nome_completo = nome_completo
            if nome and deputado.nome != nome:
                deputado.nome = nome
            return deputado

        # First, check if this specific record_id already exists as xml_source_id
        deputado = self.session.query(Deputado).filter_by(xml_source_id=record_id).first()
        if deputado:
            # Update with any new information we have
            if nome_completo and not deputado.nome_completo:
                deputado.nome_completo = nome_completo
            if nome and deputado.nome != nome:
                deputado.nome = nome
            # Cache for future lookups
            if hasattr(self, '_deputado_cache'):
                self._deputado_cache[cache_key] = deputado
                if id_cadastro:
                    self._deputado_cache[f"cadastro_{id_cadastro}"] = deputado
            return deputado

        # Check if this person (by id_cadastro) exists with a different record_id
        existing_person = self.session.query(Deputado).filter_by(id_cadastro=id_cadastro).first()
        if existing_person:
            logger.info(f"Deputy {nome} (cadastro {id_cadastro}) already exists with different xml_source_id {existing_person.xml_source_id}, creating new record with xml_source_id {record_id}")

        # Get legislature ID if not provided - prioritize XML LegDes over filename
        if legislatura_id is None:
            # CRITICAL FIX: First try to extract from XML context (LegDes takes precedence)
            if xml_context is not None:
                leg_des = self._get_text_value(xml_context, "LegDes")
                if leg_des:
                    logger.debug(f"Found LegDes '{leg_des}' in XML context for deputy {nome}")
                    # Extract legislature from XML content first
                    try:
                        legislatura_sigla = self._extract_legislatura_from_xml_content(leg_des)
                        if legislatura_sigla:
                            legislatura = self._get_or_create_legislatura(legislatura_sigla)
                            legislatura_id = legislatura.id
                            logger.info(f"Using legislature from XML LegDes '{leg_des}' -> '{legislatura_sigla}' (ID: {legislatura_id}) for deputy {nome}")
                    except Exception as e:
                        logger.warning(f"Failed to extract legislature from XML LegDes '{leg_des}' for deputy {nome}: {e}")

            # Fallback to filename-based extraction if XML didn't provide legislature
            if legislatura_id is None:
                if hasattr(self, 'file_info'):
                    legislatura_id = self._get_legislatura_id(self.file_info)
                    logger.debug(f"Using legislature from filename for deputy {nome}: {legislatura_id}")
                else:
                    # Last resort fallback
                    raise ValueError(f"Cannot determine legislature_id for deputy {nome} - no XML LegDes or file context available")

        # Create new deputy record with UUID primary key and xml_source_id for FK resolution
        deputado = Deputado(
            id=self._new_id(),  # Generate UUID client-side for immediate availability
            xml_source_id=record_id,  # Store original XML DepId for FK resolution
            id_cadastro=id_cadastro,  # This tracks the same person across legislatures
            nome=nome,
            nome_completo=nome_completo,
            legislatura_id=legislatura_id
        )

        self.session.add(deputado)
        # Flush is required here because PostgreSQL checks FK constraints immediately.
        # Child records (atividades, intervencoes, etc.) will reference this deputado_id,
        # and the parent row must exist in the DB before INSERT of children.
        self.session.flush()

        # Cache for future lookups
        if hasattr(self, '_deputado_cache'):
            self._deputado_cache[cache_key] = deputado
            if id_cadastro:
                self._deputado_cache[f"cadastro_{id_cadastro}"] = deputado

        logger.debug(f"Created deputy record: ID={deputado.id}, xml_source_id={record_id}, cadastro={id_cadastro}, name={nome}")
        return deputado



class XMLProcessingMixin:
    """Mixin providing common XML processing utilities"""

    @staticmethod
    def safe_text_extract(element: Optional[ET.Element], default: str = "") -> str:
        """Safely extract text from XML element"""
        if element is not None and element.text:
            return element.text.strip()
        return default

    @staticmethod
    def safe_int_extract(element: Optional[ET.Element], default: int = 0) -> int:
        """Safely extract integer from XML element"""
        if element is not None and element.text:
            try:
                return int(element.text.strip())
            except ValueError:
                pass
        return default

    @staticmethod
    def safe_date_extract(
        element: Optional[ET.Element], format_str: str = "%Y-%m-%d"
    ) -> Optional[datetime]:
        """Safely extract date from XML element"""
        if element is not None and element.text:
            try:
                return datetime.strptime(element.text.strip(), format_str)
            except ValueError:
                # Try alternative formats
                alt_formats = ["%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y"]
                for alt_format in alt_formats:
                    try:
                        return datetime.strptime(element.text.strip(), alt_format)
                    except ValueError:
                        continue
        return None

    def _collect_field_names(
        self, element: ET.Element, field_set: Set[str], prefix: str = ""
    ):
        """Recursively collect all field names from XML"""
        current_name = f"{prefix}.{element.tag}" if prefix else element.tag
        field_set.add(current_name)

        for child in element:
            self._collect_field_names(child, field_set, current_name)

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string using common flexible date parser"""
        from .common_utilities import DataValidationUtils
        
        parsed = DataValidationUtils.parse_date_flexible(date_str)
        if parsed:
            # Return date object if it's a datetime, otherwise return as-is
            return parsed.date() if hasattr(parsed, 'date') else parsed
        return None

    def _get_text(self, parent: ET.Element, tag: str) -> Optional[str]:
        """
        Get text from XML element.

        DEPRECATED: Use _get_text_value() instead for consistency across all mappers.
        This method is kept for backward compatibility but will be removed in a future version.
        """
        import warnings
        warnings.warn(
            "_get_text() is deprecated, use _get_text_value() instead for consistency",
            DeprecationWarning,
            stacklevel=2
        )
        if parent is None:
            return None
        element = parent.find(tag)
        if element is not None and element.text:
            return element.text.strip()
        return None

    def _get_namespaced_text(
        self, parent: ET.Element, namespace: str, tag: str
    ) -> Optional[str]:
        """Get text from namespaced XML element"""
        if namespace == "tempuri":
            full_tag = f"{{http://tempuri.org/}}{tag}"
        else:
            full_tag = f"{{{namespace}}}{tag}"

        element = parent.find(full_tag)
        if element is not None and element.text:
            return element.text.strip()
        return None

    def _get_namespaced_element(
        self, parent: ET.Element, namespace: str, tag: str
    ) -> Optional[ET.Element]:
        """Get namespaced XML element"""
        if namespace == "tempuri":
            full_tag = f"{{http://tempuri.org/}}{tag}"
        else:
            full_tag = f"{{{namespace}}}{tag}"

        return parent.find(full_tag)

    def _get_int_text(self, parent: ET.Element, tag: str) -> Optional[int]:
        """Get integer value from XML element text"""
        text = self._get_text(parent, tag)
        # Use _safe_int to properly handle float strings like '8526.0'
        return self._safe_int(text)

    def _get_text_value(self, parent: ET.Element, tag_name: str) -> Optional[str]:
        """Get text value from XML element - standardized method used across all mappers"""
        if parent is None:
            return None
        try:
            element = parent.find(tag_name)
            if element is not None and element.text:
                text = element.text.strip()
                return text
            return None
        except AttributeError:
            logger.warning(f"Error accessing element with tag '{tag_name}' from parent")
            return None


    def _get_int_value(self, parent: ET.Element, tag_name: str) -> Optional[int]:
        """Get integer value from XML element - standardized method used across all mappers"""
        text_value = self._get_text_value(parent, tag_name)
        if text_value:
            try:
                # Handle both integer and float strings
                return int(text_value)
            except (ValueError, TypeError):
                return None
        return None

    def _get_boolean_value(self, parent: ET.Element, tag_name: str) -> Optional[bool]:
        """
        Get boolean value from XML element - standardized method used across all mappers
        
        Handles common boolean representations:
        - True: 'true', '1', 'yes', 'sim', 's', 'True', 'TRUE'
        - False: 'false', '0', 'no', 'não', 'nao', 'n', 'False', 'FALSE'
        - None: empty, None, or unrecognized values
        
        Args:
            parent: XML element to search within
            tag_name: Name of the tag to extract boolean from
            
        Returns:
            Optional[bool]: True/False if recognized, None otherwise
        """
        text_value = self._get_text_value(parent, tag_name)
        if text_value is None:
            return None
        
        value_lower = text_value.lower().strip()
        
        # True values (English and Portuguese)
        if value_lower in ('true', '1', 'yes', 'sim', 's'):
            return True
        # False values (English and Portuguese) 
        elif value_lower in ('false', '0', 'no', 'não', 'nao', 'n'):
            return False
        
        # Log warning for unrecognized values
        logger.warning(f"Unrecognized boolean value '{text_value}' for tag '{tag_name}', returning None")
        return None

    def _safe_int(self, value) -> Optional[int]:
        """Safely convert value to int - handles strings, floats, None, and float strings like '7890.0'"""
        if value is None or value == '':
            return None
        try:
            # First try direct int conversion for normal cases
            if isinstance(value, int):
                return value
            elif isinstance(value, float):
                return int(value)
            elif isinstance(value, str):
                # Handle whitespace-only strings
                if not value.strip():
                    return None
                
                stripped_value = value.strip()
                
                # Reject scientific notation (e.g., "1e5", "1.23e4")
                if 'e' in stripped_value.lower():
                    return None
                
                # Handle float format strings like '7890.0' by converting to float first
                float_value = DataValidationUtils.safe_float_convert(stripped_value)
                if float_value is not None:
                    return int(float_value)
            return None
        except (ValueError, TypeError):
            return None


class EnhancedSchemaMapper(
    CacheMixin, DatabaseSessionMixin, LegislatureHandlerMixin, XMLProcessingMixin, CoalitionDetectionMixin, ABC
):
    """
    Enhanced base class for all schema mappers with consolidated functionality.

    Provides:
    - Entity caching (Legislatura, Deputado, Partido) via CacheMixin
    - Batch processing with _batch_flush() for performance
    - SQLAlchemy session management via DatabaseSessionMixin
    - Legislature extraction and handling via LegislatureHandlerMixin
    - XML processing utilities via XMLProcessingMixin
    - Coalition detection via CoalitionDetectionMixin
    - Import source tracking for data provenance

    Child classes can declare import order dependencies by overriding:
        IMPORT_DEPENDENCIES = ['dependency1', 'dependency2']

    Cache is session-scoped and automatically initialized. Call _clear_caches()
    when switching between processing runs or legislatures.
    """

    def __init__(self, session, import_status_record=None):
        DatabaseSessionMixin.__init__(self, session)
        CoalitionDetectionMixin.__init__(self)
        # Initialize entity caches from CacheMixin
        self._init_caches()
        # Store import status record for data provenance tracking
        self._import_status_record = import_status_record
        self._import_status_id = import_status_record.id if import_status_record else None

    def _attach_import_source(self, record):
        """
        Attach import source tracking to a record before adding to session.

        This enables data provenance tracking - knowing which import file
        created each record in the database.

        Args:
            record: SQLAlchemy model instance to attach source to

        Returns:
            The record with import_status_id set (if available)
        """
        if self._import_status_id and hasattr(record, 'import_status_id'):
            record.import_status_id = self._import_status_id
        return record

    def _add_with_tracking(self, record):
        """
        Add a record to session with import source tracking.

        Convenience method that combines _attach_import_source and session.add.

        Args:
            record: SQLAlchemy model instance to add
        """
        self._attach_import_source(record)
        self.session.add(record)
        return record

    def _normalize_name(self, name: str) -> str:
        """
        Normalize name to proper title case, handling Portuguese names correctly.

        Historical XML sources (legislatures I-XII) often use ALL CAPS names.
        This method normalizes them to proper case while respecting Portuguese
        prepositions and articles that should remain lowercase.

        Args:
            name: Name string to normalize

        Returns:
            Normalized name with proper capitalization
        """
        if not name:
            return name

        # If already mixed case (has both upper and lower), preserve it
        if not name.isupper() and not name.islower():
            return name

        # Portuguese prepositions/articles to keep lowercase (except at start)
        lowercase_words = {'de', 'da', 'do', 'das', 'dos', 'e', 'a', 'o', 'as', 'os'}

        words = name.lower().split()
        result = []
        for i, word in enumerate(words):
            if i == 0 or word not in lowercase_words:
                result.append(word.capitalize())
            else:
                result.append(word)

        return ' '.join(result)

    @abstractmethod
    def get_expected_fields(self) -> Set[str]:
        """Return set of expected XML field names for this schema"""
        pass

    @abstractmethod
    def validate_and_map(
        self, xml_root: ET.Element, file_info: Dict, strict_mode: bool = False
    ) -> Dict:
        """Validate XML structure and map to database schema"""
        pass

    def check_schema_coverage(self, xml_root: ET.Element) -> List[str]:
        """Check for unmapped fields in XML"""
        found_fields = set()
        self._collect_field_names(xml_root, found_fields)

        expected_fields = self.get_expected_fields()
        unmapped_fields = found_fields - expected_fields

        return list(unmapped_fields)

    def validate_schema_coverage(
        self, xml_root: ET.Element, file_info: Dict, strict_mode: bool = False
    ):
        """Validate schema coverage and raise SchemaError if unmapped fields are found"""
        unmapped_fields = self.check_schema_coverage(xml_root)
        if unmapped_fields:
            unmapped_summary = ", ".join(list(unmapped_fields)[:10])
            
            logger.error(
                f"Schema coverage violation: Unmapped fields detected in {file_info.get('file_path', 'unknown file')}"
            )
            logger.error(f"Unmapped fields: {unmapped_summary}")
            if len(unmapped_fields) > 10:
                logger.error(
                    f"... and {len(unmapped_fields) - 10} more unmapped fields"
                )
            
            # Always raise SchemaError when unmapped fields are found - this is a serious data integrity issue
            raise SchemaError(f"Schema coverage violation: {unmapped_summary}")
        return unmapped_fields

    def process_with_error_handling(
        self, processing_func, item, error_context: str = "item"
    ) -> bool:
        """Common error handling pattern for processing items"""
        try:
            processing_func(item)
            return True
        except Exception as e:
            error_msg = f"{error_context} processing error: {str(e)}"
            logger.error(error_msg)
            logger.error("Data integrity issue detected during processing")
            raise RuntimeError(f"Data integrity issue: {error_msg}")

    def create_processing_results(self) -> Dict:
        """Create standard results dictionary"""
        return {"records_processed": 0, "records_imported": 0, "errors": []}

    def finalize_processing(self, results: Dict) -> Dict:
        """Finalize processing with transaction commit"""
        try:
            self.commit_transaction()
            logger.info(
                f"Processing completed: {results['records_imported']}/{results['records_processed']} imported"
            )
        except Exception as e:
            logger.error(f"Transaction commit failed: {str(e)}")
            results["errors"].append(f"Transaction commit failed: {str(e)}")

        return results

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with proper cleanup"""
        if exc_type:
            logger.error("Exception occurred in context manager")
            logger.error(f"Exception type: {exc_type}")
            logger.error(f"Exception value: {exc_val}")
            # Let the exception propagate naturally instead of calling sys.exit()
        self.close_session()

    def _find_deputy_robust(
        self, cad_id: int, nome_completo: str = None, nome_parlamentar: str = None, legislatura_id: int = None
    ) -> Deputado:
        """
        Robust deputy matching with cadastral ID change tracking and caching.

        This method handles cases where deputy cadastral IDs change over time by implementing
        a multi-level matching strategy and tracking identity mappings.

        Args:
            cad_id: Current cadastral ID to look up
            nome_completo: Full deputy name for fallback matching
            nome_parlamentar: Parliamentary name for fallback matching
            legislatura_id: Legislature ID to scope the search (CRITICAL FIX)

        Returns:
            Deputado: The matched deputy record

        Raises:
            ValueError: If no deputy can be matched using any strategy
        """
        # Step 0: Check cache first - avoid database queries for known deputies
        cache_key = f"cadastro_{cad_id}"
        if legislatura_id is not None:
            cache_key = f"cadastro_{cad_id}_leg_{legislatura_id}"

        cached = self._deputado_cache.get(cache_key)
        if cached:
            return cached

        # Step 1: Try direct cadastral ID lookup within the current legislature
        query = self.session.query(Deputado).filter(Deputado.id_cadastro == cad_id)

        # CRITICAL FIX: Scope to specific legislature if provided
        if legislatura_id is not None:
            query = query.filter(Deputado.legislatura_id == legislatura_id)

        deputy = query.first()
        if deputy:
            # Cache for future lookups
            self._deputado_cache[cache_key] = deputy
            self._cache_deputado(deputy)
            return deputy

        # Step 2: Check if this cadastral ID is mapped to another ID
        identity_mapping = (
            self.session.query(DeputyIdentityMapping)
            .filter(DeputyIdentityMapping.old_cad_id == cad_id)
            .first()
        )

        if identity_mapping:
            # Try to find deputy with the new cadastral ID within the current legislature
            query = self.session.query(Deputado).filter(Deputado.id_cadastro == identity_mapping.new_cad_id)

            if legislatura_id is not None:
                query = query.filter(Deputado.legislatura_id == legislatura_id)

            deputy = query.first()
            if deputy:
                logger.info(
                    f"Found deputy via identity mapping: old_cad_id={cad_id} -> new_cad_id={identity_mapping.new_cad_id}"
                )
                # Cache for future lookups (both old and new cad_id)
                self._deputado_cache[cache_key] = deputy
                self._cache_deputado(deputy)
                return deputy

        # Step 3: Fallback to name-based matching if names are provided
        if nome_completo or nome_parlamentar:
            # Check name-based cache first
            name_cache_key = None
            if nome_completo:
                name_cache_key = f"nome_{nome_completo.lower()}_leg_{legislatura_id}"
                cached = self._deputado_cache.get(name_cache_key)
                if cached:
                    return cached

            query = self.session.query(Deputado)

            # Scope to current legislature if provided
            if legislatura_id is not None:
                query = query.filter(Deputado.legislatura_id == legislatura_id)

            # Try full name match first
            if nome_completo:
                deputy = query.filter(
                    Deputado.nome_completo.ilike(f"%{nome_completo}%")
                ).first()
                if deputy:
                    # Record the identity mapping for future lookups
                    # deputy.id_cadastro is the OLD ID (existing in DB), cad_id is the NEW ID (we're trying to find)
                    self._record_identity_mapping(
                        deputy.id_cadastro, cad_id, nome_completo or nome_parlamentar, deputy
                    )
                    logger.info(
                        f"Deputy found by full name match - recording identity mapping: old_cad_id={deputy.id_cadastro} -> new_cad_id={cad_id} ({nome_completo})"
                    )
                    # Cache for future lookups
                    self._deputado_cache[cache_key] = deputy
                    if name_cache_key:
                        self._deputado_cache[name_cache_key] = deputy
                    self._cache_deputado(deputy)
                    return deputy

            # Try parliamentary name match
            if nome_parlamentar:
                parl_name_cache_key = f"nome_parl_{nome_parlamentar.lower()}_leg_{legislatura_id}"
                cached = self._deputado_cache.get(parl_name_cache_key)
                if cached:
                    return cached

                deputy = query.filter(
                    Deputado.nome.ilike(f"%{nome_parlamentar}%")
                ).first()
                if deputy:
                    # Record the identity mapping for future lookups
                    # deputy.id_cadastro is the OLD ID (existing in DB), cad_id is the NEW ID (we're trying to find)
                    self._record_identity_mapping(
                        deputy.id_cadastro, cad_id, nome_parlamentar, deputy
                    )
                    logger.info(
                        f"Deputy found by parliamentary name match - recording identity mapping: old_cad_id={deputy.id_cadastro} -> new_cad_id={cad_id} ({nome_parlamentar})"
                    )
                    # Cache for future lookups
                    self._deputado_cache[cache_key] = deputy
                    self._deputado_cache[parl_name_cache_key] = deputy
                    self._cache_deputado(deputy)
                    return deputy

        # Step 4: No match found - create new deputy
        # With on-the-fly file processing, files can arrive in any order.
        # Deputies are created from whichever source arrives first and enriched later.
        if legislatura_id is None:
            raise ValueError(f"Cannot create deputy {cad_id} - legislatura_id is required")

        nome = nome_parlamentar or nome_completo or f"Deputy {cad_id}"
        deputado = Deputado(
            id_cadastro=cad_id,
            nome=nome,
            nome_completo=nome_completo,
            legislatura_id=legislatura_id,
        )
        self.session.add(deputado)
        self.session.flush()  # Get ID for relationships

        # Cache for future lookups
        self._deputado_cache[cache_key] = deputado
        self._cache_deputado(deputado)

        logger.debug(f"Created deputy {cad_id} ({nome}) in legislature {legislatura_id}")
        return deputado

    def _record_identity_mapping(
        self, old_cad_id: int, new_cad_id: int, deputy_name: str, deputy: Deputado
    ):
        """Record an identity mapping between old and new cadastral IDs and update the deputy record."""
        # Flush session to ensure any pending objects are written to DB for query
        self.session.flush()
        
        # Check if mapping already exists (including any just flushed)
        existing_mapping = (
            self.session.query(DeputyIdentityMapping)
            .filter(
                DeputyIdentityMapping.old_cad_id == old_cad_id,
                DeputyIdentityMapping.new_cad_id == new_cad_id,
            )
            .first()
        )

        if existing_mapping:
            logger.debug(f"Identity mapping {old_cad_id} -> {new_cad_id} already exists, skipping")
            return

        # Record the identity mapping
        mapping = DeputyIdentityMapping(
            old_cad_id=old_cad_id,
            new_cad_id=new_cad_id,
            deputy_name=deputy_name,
            confidence_score=90,  # Discovered via name matching
            verified=False,
        )
        self.session.add(mapping)

        # Update deputy's current cadastral ID to the new value
        deputy.id_cadastro = new_cad_id
        logger.info(f"Updated deputy cadastral ID: {old_cad_id} -> {new_cad_id} for {deputy_name}")


# Backward compatibility alias
SchemaMapper = EnhancedSchemaMapper
