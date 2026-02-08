#!/usr/bin/env python3
"""
Parliament Data Discovery Service
================================

Discovers and catalogs all parliament data files without downloading them.
Stores metadata in ImportStatus table for later processing by the import pipeline.

Features:
- URL discovery through parliament website crawling
- HTTP HEAD requests for change detection metadata
- Legislatura, category, and file type extraction from URLs
- Database-driven file tracking without local storage

Usage:
    python discovery_service.py --discover-all
    python discovery_service.py --legislature XVII
    python discovery_service.py --category "Atividade Deputado"
"""

import argparse
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests.exceptions import ConnectionError, ConnectTimeout, ReadTimeout, Timeout

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from database.connection import DatabaseSession
from database.models import ImportStatus
from http_retry_utils import HTTPRetryClient, get_http_metadata


class ParliamentURLExtractor:
    """Extracts metadata from parliament URLs and file paths"""

    # Category mapping from URL patterns to human-readable categories
    CATEGORY_PATTERNS = {
        r"atividade[_\s]*deputado": "Atividade Deputado",
        r"composicao[_\s]*orgaos": "Composição Órgãos",
        r"boletim[_\s]*informativo": "Agenda Parlamentar",
        r"atividades": "Atividades",
        r"cooperacao[_\s]*parlamentar": "Cooperação Parlamentar",
        r"delegacoes[_\s]*eventuais": "Delegações Eventuais",
        r"delegacoes[_\s]*permanentes": "Delegações Permanentes",
        r"informacao[_\s]*base": "Informação Base",
        r"registo[_\s]*biografico": "Registo Biográfico",
        r"iniciativas": "Iniciativas",
        r"intervencoes": "Intervenções",
        r"peticoes": "Petições",
        r"perguntas[_\s]*requerimentos": "Perguntas Requerimentos",
        r"diplomas[_\s]*aprovados": "Diplomas Aprovados",
        r"o_e|orcamento[_\s]*estado": "Orçamento Estado",
        r"reunioes[_\s]*visitas": "Reuniões Visitas",
        r"grupos[_\s]*amizade": "Grupos Amizade",
        r"dar|diario[_\s]*assembleia": "Diário Assembleia",
    }

    @classmethod
    def extract_metadata(cls, file_url: str, file_name: str) -> Dict[str, str]:
        """Extract all metadata from URL and filename"""
        metadata = {
            "file_url": file_url,
            "file_name": file_name,
            "legislatura": None,
            "category": None,
            "file_type": None,
            "sub_series": None,
            "session": None,
            "number": None,
        }

        # Extract file type from extension and URL patterns
        if file_name.endswith(".xml"):
            metadata["file_type"] = "XML"
        elif file_name.endswith(".json") or file_name.endswith("_json.txt"):
            metadata["file_type"] = "JSON"
        elif file_name.endswith(".pdf"):
            metadata["file_type"] = "PDF"
        elif file_name.endswith(".xsd"):
            metadata["file_type"] = "XSD"
        elif file_name.endswith(".zip"):
            metadata["file_type"] = "Archive"
        elif not file_name or "." not in file_name:
            # For files without extensions, try to detect from URL patterns
            if "doc.pdf" in file_url.lower():
                metadata["file_type"] = "PDF"
            elif "doc.xsd" in file_url.lower():
                metadata["file_type"] = "XSD"
            elif "doc.xml" in file_url.lower():
                metadata["file_type"] = "XML"
            elif "doc.json" in file_url.lower():
                metadata["file_type"] = "JSON"
            elif "doc.zip" in file_url.lower():
                metadata["file_type"] = "Archive"
            else:
                metadata["file_type"] = "Unknown"
        else:
            metadata["file_type"] = "Unknown"

        # Extract legislatura from URL path and filename
        metadata["legislatura"] = cls._extract_legislatura(file_url, file_name)

        # Extract category from URL path
        metadata["category"] = cls._extract_category(file_url)

        # Extract DAR-specific fields
        if "dar" in file_url.lower() or "diario" in file_url.lower():
            metadata.update(cls._extract_dar_metadata(file_url))

        return metadata

    @classmethod
    def _extract_legislatura(
        cls, file_url: str, file_name: str = None
    ) -> Optional[str]:
        """Extract legislatura from URL path or filename"""
        # Combine URL and filename for comprehensive pattern matching
        search_text = file_url
        if file_name:
            search_text += " " + file_name

        # Try different patterns for legislature identification
        patterns = [
            # URL-based patterns
            # Ordered by length (longest first) to prevent false matches like "I" matching before "IB" 
            r"(CONSTITUINTE|XVII|XVI|XV|XIV|XIII|XII|VIII|VII|VI|IV|III|IB|IA|IX|II|X|V|I)[_\s]*Legislatura",
            r"Legislatura[_\s]*(CONSTITUINTE|XVII|XVI|XV|XIV|XIII|XII|VIII|VII|VI|IV|III|IB|IA|IX|II|X|V|I)",
            r"/(CONSTITUINTE|XVII|XVI|XV|XIV|XIII|XII|VIII|VII|VI|IV|III|IB|IA|IX|II|X|V|I)_Legislatura/",
            r"/(CONSTITUINTE|XVII|XVI|XV|XIV|XIII|XII|VIII|VII|VI|IV|III|IB|IA|IX|II|X|V|I)/",
            r"(Constituinte)",
            # Filename-based patterns (common in parliament files) - ordered by length to avoid false matches
            r"(CONSTITUINTE|XVII|XVI|XV|XIV|XIII|XII|VIII|VII|VI|IV|III|IB|IA|IX|II|X|V|I)\.xml$",  # AtividadesXVII.xml
            r"(CONSTITUINTE|XVII|XVI|XV|XIV|XIII|XII|VIII|VII|VI|IV|III|IB|IA|IX|II|X|V|I)_json\.txt$",  # AtividadesXVII_json.txt
            r"Base(CONSTITUINTE|XVII|XVI|XV|XIV|XIII|XII|VIII|VII|VI|IV|III|IB|IA|IX|II|X|V|I)\.xml$",  # InformacaoBaseXVII.xml
            r"Deputado(CONSTITUINTE|XVII|XVI|XV|XIV|XIII|XII|VIII|VII|VI|IV|III|IB|IA|IX|II|X|V|I)\.xml$",  # AtividadeDeputadoXVII.xml
            r"Composicao(CONSTITUINTE|XVII|XVI|XV|XIV|XIII|XII|VIII|VII|VI|IV|III|IB|IA|IX|II|X|V|I)\.xml$",  # OrgaoComposicaoXVII.xml
            r"Eventual(CONSTITUINTE|XVII|XVI|XV|XIV|XIII|XII|VIII|VII|VI|IV|III|IB|IA|IX|II|X|V|I)\.xml$",  # DelegacaoEventualXVII.xml
            r"Permanente(CONSTITUINTE|XVII|XVI|XV|XIV|XIII|XII|VIII|VII|VI|IV|III|IB|IA|IX|II|X|V|I)\.xml$",  # DelegacaoPermanenteXVII.xml
            r"Iniciativas(CONSTITUINTE|XVII|XVI|XV|XIV|XIII|XII|VIII|VII|VI|IV|III|IB|IA|IX|II|X|V|I)\.xml$",  # IniciativasXVII.xml
            r"Intervencoes(CONSTITUINTE|XVII|XVI|XV|XIV|XIII|XII|VIII|VII|VI|IV|III|IB|IA|IX|II|X|V|I)\.xml$",  # IntervencoesXVII.xml
            r"Peticoes(CONSTITUINTE|XVII|XVI|XV|XIV|XIII|XII|VIII|VII|VI|IV|III|IB|IA|IX|II|X|V|I)\.xml$",  # PeticoesXVII.xml
            r"Requerimentos(CONSTITUINTE|XVII|XVI|XV|XIV|XIII|XII|VIII|VII|VI|IV|III|IB|IA|IX|II|X|V|I)\.xml$",  # RequerimentosXVII.xml
            r"Biografico(CONSTITUINTE|XVII|XVI|XV|XIV|XIII|XII|VIII|VII|VI|IV|III|IB|IA|IX|II|X|V|I)\.xml$",  # RegistoBiograficoXVII.xml
            r"Interesses(CONSTITUINTE|XVII|XVI|XV|XIV|XIII|XII|VIII|VII|VI|IV|III|IB|IA|IX|II|X|V|I)\.xml$",  # RegistoInteressesXVII.xml
            r"Diplomas(CONSTITUINTE|XVII|XVI|XV|XIV|XIII|XII|VIII|VII|VI|IV|III|IB|IA|IX|II|X|V|I)\.xml$",  # DiplomasXVII.xml
            r"Cooperacao(CONSTITUINTE|XVII|XVI|XV|XIV|XIII|XII|VIII|VII|VI|IV|III|IB|IA|IX|II|X|V|I)\.xml$",  # CooperacaoXVII.xml
            r"Visitas(CONSTITUINTE|XVII|XVI|XV|XIV|XIII|XII|VIII|VII|VI|IV|III|IB|IA|IX|II|X|V|I)\.xml$",  # ReunioesVisitasXVII.xml
            r"Amizade(CONSTITUINTE|XVII|XVI|XV|XIV|XIII|XII|VIII|VII|VI|IV|III|IB|IA|IX|II|X|V|I)\.xml$",  # GrupoDeAmizadeXVII.xml
            # Special cases
            r"(Cons)\.xml$",  # Constituinte files end with "Cons"
        ]

        for pattern in patterns:
            match = re.search(pattern, search_text, re.IGNORECASE)
            if match:
                leg = match.group(1).upper()
                # Convert special cases to standardized format
                if leg == "CONSTITUINTE":
                    return "Constituinte"
                elif leg == "CONS":
                    return "Constituinte"
                return leg

        return None

    @classmethod
    def _extract_category(cls, file_url: str) -> Optional[str]:
        """Extract category from URL path"""
        url_lower = file_url.lower()

        for pattern, category in cls.CATEGORY_PATTERNS.items():
            if re.search(pattern, url_lower):
                return category

        return "Unknown"

    @classmethod
    def _extract_dar_metadata(cls, file_url: str) -> Dict[str, Optional[str]]:
        """Extract DAR-specific metadata (sub_series, session, number)"""
        metadata = {
            "sub_series": None,
            "session": None,
            "number": None,
        }

        # Extract sub-series (e.g., "Serie_I", "Serie_II-A")
        series_match = re.search(r"Serie[_\s]*(I+(?:-[A-Z])?)", file_url, re.IGNORECASE)
        if series_match:
            metadata["sub_series"] = f"Serie_{series_match.group(1).upper()}"

        # Extract session (e.g., "Sessao_04")
        session_match = re.search(r"Sessao[_\s]*(\d+)", file_url, re.IGNORECASE)
        if session_match:
            metadata["session"] = f"Sessao_{session_match.group(1).zfill(2)}"

        # Extract number (e.g., "Numero_036")
        number_match = re.search(r"Numero[_\s]*(\d+)", file_url, re.IGNORECASE)
        if number_match:
            metadata["number"] = f"Numero_{number_match.group(1).zfill(3)}"

        return metadata


class DiscoveryService:
    """Main discovery service for parliament data files"""

    def __init__(self, rate_limit_delay: float = 0.5, enable_metadata_requests: bool = False, quiet: bool = False):
        self.rate_limit_delay = rate_limit_delay
        self.enable_metadata_requests = enable_metadata_requests  # Disabled by default due to server issues
        self.quiet = quiet  # Suppress console output when True
        self.base_url = "https://www.parlamento.pt/Cidadania/paginas/dadosabertos.aspx"
        # Use HTTP retry client instead of regular requests session
        self.http_client = HTTPRetryClient(
            max_retries=5,
            initial_backoff=1.0,
            max_backoff=120.0,
            backoff_multiplier=2.0,
            timeout=30,
            user_agent="Fiscaliza/1.0 (https://fiscaliza.pt; open-source parliamentary data)"
        )
    
    def _print(self, *args, **kwargs):
        """Print only if not in quiet mode"""
        if not self.quiet:
            print(*args, **kwargs)

    def discover_all_files(
        self, legislature_filter: str = None, category_filter: str = None
    ) -> int:
        """Discover all parliament files and store metadata in database"""
        self._print(f"Starting discovery from {self.base_url}")
        if legislature_filter:
            self._print(f"Filtering for legislature: {legislature_filter}")
        if category_filter:
            self._print(f"Filtering for category: {category_filter}")

        discovered_count = 0

        # Get recursos links from main page
        recursos_links = self._extract_recursos_links()
        if not recursos_links:
            self._print("ERROR: No recursos links found")
            return 0

        self._print(f"Found {len(recursos_links)} main sections")

        # Process each section
        with DatabaseSession() as db_session:
            for i, link_info in enumerate(recursos_links, 1):
                section_name = link_info["section_name"]
                section_url = link_info["url"]

                self._print(
                    f"\n[{i}/{len(recursos_links)}] Processing section: {section_name}"
                )

                # Check category filter
                if (
                    category_filter
                    and category_filter.lower() not in section_name.lower()
                ):
                    self._print(f"SKIP: Skipping section (category filter)")
                    continue

                section_count = self._discover_section_files(
                    db_session, section_url, section_name, legislature_filter
                )
                discovered_count += section_count

                self._print(f"DONE: Section complete: {section_count} files discovered")

                # Rate limiting
                time.sleep(self.rate_limit_delay)

            # No bulk commit needed - each file commits immediately

        self._print(f"\nDiscovery complete: {discovered_count} total files cataloged")
        return discovered_count

    def _extract_recursos_links(self) -> List[Dict[str, str]]:
        """Extract main recursos section links"""
        try:
            response = self.http_client.get(self.base_url)

            soup = BeautifulSoup(response.text, "html.parser")
            recursos_links = []

            for link in soup.find_all("a", href=True):
                link_text = link.get_text(strip=True)
                if "Recursos" in link_text:
                    href = link["href"]
                    full_url = urljoin(self.base_url, href)

                    # Extract section name from URL
                    url_parts = href.split("/")
                    if url_parts:
                        filename = url_parts[-1]
                        if filename.startswith("DA"):
                            name_part = filename[2:].replace(".aspx", "")
                            section_name = re.sub(r"([A-Z])", r" \1", name_part).strip()
                        else:
                            section_name = filename.replace(".aspx", "")
                    else:
                        section_name = "Unknown Section"

                    recursos_links.append(
                        {
                            "section_name": section_name,
                            "text": link_text,
                            "url": full_url,
                        }
                    )

            # Filter out DAR sections for now (skip DAR processing)
            filtered_sections = []
            
            for link in recursos_links:
                section_name = link["section_name"].lower()
                if "dar" in section_name or "diário" in section_name or "diario" in section_name:
                    # Skip DAR sections - too complex for now
                    continue
                else:
                    filtered_sections.append(link)
            
            return filtered_sections

        except Exception as e:
            self._print(f"ERROR: Error extracting recursos links: {e}")
            return []

    def _discover_section_files(
        self,
        db_session,
        section_url: str,
        section_name: str,
        legislature_filter: str = None,
    ) -> int:
        """Discover files within a section using tiered approach"""
        discovered_count = 0

        # Extract category from section name for context
        section_category = self._normalize_section_category(section_name)

        try:
            response = self.http_client.get(section_url)

            soup = BeautifulSoup(response.text, "html.parser")
            archive_items = soup.find_all("div", class_="archive-item")

            if not archive_items:
                self._print(f"  FOLDER: No archive items found in section")
                return 0

            self._print(f"  FOLDER: Found {len(archive_items)} level-2 items")

            for item in archive_items:
                link = item.find("a", href=True)
                if not link:
                    continue

                item_url = urljoin(section_url, link["href"])
                item_name = link.get_text(strip=True)

                # Extract legislature from navigation hierarchy (level-2)
                item_legislature = self._extract_legislature_from_navigation(item_name)

                # Apply legislature filter at level-2
                if legislature_filter and not self._matches_legislature(
                    item_name, legislature_filter
                ):
                    continue

                self._print(
                    f"    SEARCH: Exploring: {item_name} (Legislature: {item_legislature or 'Unknown'})"
                )

                # Create navigation context to pass down
                navigation_context = {
                    "section_category": section_category,
                    "legislature": item_legislature,
                    "path": [section_name, item_name],
                }

                count = self._discover_tiered(
                    db_session, item_url, item_name, navigation_context, max_depth=6,
                    source_page_url=section_url, anchor_text=item_name
                )
                discovered_count += count

                # Rate limiting
                time.sleep(self.rate_limit_delay * 0.5)

        except Exception as e:
            self._print(f"  ERROR: Error processing section {section_name}: {e}")

        return discovered_count

    def _discover_tiered(
        self,
        db_session,
        url: str,
        name: str,
        navigation_context: Dict,
        current_depth: int = 1,
        max_depth: int = 6,
        source_page_url: str = None,
        anchor_text: str = None
    ) -> int:
        """Recursively discover files using tiered approach with navigation context"""
        if current_depth > max_depth:
            return 0

        discovered_count = 0

        # Check if this is a direct file
        if self._is_file_url(url, name):
            return self._catalog_file_with_context(
                db_session, url, name, navigation_context, 
                source_page_url=source_page_url or url, 
                anchor_text=anchor_text or name
            )

        # Otherwise, explore deeper
        try:
            response = self.http_client.get(url)

            soup = BeautifulSoup(response.text, "html.parser")
            archive_items = soup.find_all("div", class_="archive-item")

            if archive_items:
                self._print(
                    f"      {'  ' * current_depth}DIR: Level {current_depth + 1}: {len(archive_items)} items"
                )

                for item in archive_items:
                    link = item.find("a", href=True)
                    if not link:
                        continue

                    next_url = urljoin(url, link["href"])
                    next_name = link.get_text(strip=True)

                    # Update navigation context with current level
                    updated_context = navigation_context.copy()
                    updated_context["path"] = navigation_context["path"] + [next_name]

                    # Try to extract more specific context from deeper levels (like original)
                    if current_depth == 2:  # Often subcategories are at level 3
                        sub_legislature = self._extract_legislature_from_navigation(
                            next_name
                        )
                        if sub_legislature and not navigation_context.get(
                            "legislature"
                        ):
                            updated_context["legislature"] = sub_legislature

                        # Also try to detect subcategories from level 3+ names
                        if current_depth >= 2:
                            subcategory = self._extract_subcategory_from_navigation(
                                next_name, navigation_context.get("section_category")
                            )
                            if subcategory and subcategory != navigation_context.get(
                                "section_category"
                            ):
                                updated_context["subcategory"] = subcategory

                    count = self._discover_tiered(
                        db_session,
                        next_url,
                        next_name,
                        updated_context,
                        current_depth + 1,
                        max_depth,
                        source_page_url=url,  # Pass current page as source
                        anchor_text=next_name  # Pass link text as anchor
                    )
                    discovered_count += count

                    # Rate limiting
                    time.sleep(self.rate_limit_delay * 0.2)
            else:
                self._print(
                    f"      {'  ' * current_depth}FILE: No more archive items at level {current_depth + 1}"
                )

        except Exception as e:
            self._print(
                f"      {'  ' * current_depth}ERROR: Error at depth {current_depth}: {e}"
            )

        return discovered_count

    def _is_file_url(self, url: str, name: str) -> bool:
        """Check if URL/name represents a downloadable file"""
        file_extensions = [".xml", ".json", ".pdf", ".xsd", ".zip", "_json.txt"]

        # Check name for file extension
        if any(name.lower().endswith(ext) for ext in file_extensions):
            return True

        # Check URL path for file extension
        url_path = urlparse(url).path.lower()
        if any(url_path.endswith(ext) for ext in file_extensions):
            return True

        return False

    def _catalog_file_with_context(
        self, db_session, file_url: str, file_name: str, navigation_context: Dict,
        source_page_url: str = None, anchor_text: str = None
    ) -> int:
        """Catalog a single file in the database with navigation context"""
        try:
            # Extract metadata from URL and name (fallback method)
            fallback_metadata = ParliamentURLExtractor.extract_metadata(
                file_url, file_name
            )

            # Special handling for DAR files using navigation context
            if self._is_dar_file(navigation_context.get("path", []), file_url):
                category, dar_metadata = self._extract_dar_hierarchy_from_navigation(
                    navigation_context.get("path", []), file_name
                )
                legislatura = dar_metadata.get("legislature") or navigation_context.get("legislature")
                sub_series = dar_metadata.get("sub_series")
                session = dar_metadata.get("session") 
                number = dar_metadata.get("number")
            else:
                # Use navigation context as primary source, fallback to extracted metadata
                category = (
                    navigation_context["section_category"] or fallback_metadata["category"]
                )
                legislatura = (
                    navigation_context["legislature"] or fallback_metadata["legislatura"]
                )
                sub_series = fallback_metadata.get("sub_series")
                session = fallback_metadata.get("session")
                number = fallback_metadata.get("number")

                # Enhance category with subcategory if available (like original folder structure)
                subcategory = navigation_context.get("subcategory")
                if subcategory and subcategory != category:
                    category = f"{category} > {subcategory}"

            # Extract URL pattern heuristic for potential token refresh
            url_pattern = self._extract_url_pattern(file_url)
            
            # Get HTTP metadata with HEAD request
            http_metadata = self._get_http_metadata(file_url)

            # Check if file already exists in database by logical identity
            # (file_name, category, legislatura) - NOT by URL since parliament uses
            # token-based URLs that change between sessions
            existing = (
                db_session.query(ImportStatus).filter_by(
                    file_name=file_name,
                    category=category,
                    legislatura=legislatura
                ).first()
            )

            if existing:
                # Separate concerns:
                # 1. content_changed - triggers re-download (HTTP metadata indicates new version)
                # 2. metadata_updated - silent update (URL token refresh, context improvements)
                content_changed = False
                metadata_updated = False

                # Always update URL if it changed (parliament uses token-based URLs)
                # This ensures downloads use fresh tokens - but does NOT trigger re-download
                if file_url != existing.file_url:
                    existing.file_url = file_url
                    metadata_updated = True

                # HTTP metadata changes indicate content changed - triggers re-download
                if http_metadata.get("last_modified") and http_metadata.get("last_modified") != existing.last_modified:
                    existing.last_modified = http_metadata.get("last_modified")
                    content_changed = True
                if http_metadata.get("content_length") and http_metadata.get("content_length") != existing.content_length:
                    existing.content_length = http_metadata.get("content_length")
                    content_changed = True
                if http_metadata.get("etag") and http_metadata.get("etag") != existing.etag:
                    existing.etag = http_metadata.get("etag")
                    content_changed = True

                # Context improvements - silent updates, don't trigger re-download
                if category and category != existing.category:
                    existing.category = category
                    metadata_updated = True
                if legislatura and legislatura != existing.legislatura:
                    existing.legislatura = legislatura
                    metadata_updated = True

                # Discovery metadata updates - silent, don't trigger re-download
                if source_page_url and source_page_url != existing.source_page_url:
                    existing.source_page_url = source_page_url
                    metadata_updated = True
                if anchor_text and anchor_text != existing.anchor_text:
                    existing.anchor_text = anchor_text
                    metadata_updated = True
                if url_pattern and url_pattern != existing.url_pattern:
                    existing.url_pattern = url_pattern
                    metadata_updated = True

                if content_changed:
                    # Content actually changed - mark for re-download
                    existing.updated_at = datetime.now()
                    existing.status = "download_pending"
                    db_session.flush()
                    db_session.commit()
                    # Log what triggered the re-download
                    changes = []
                    if http_metadata.get("last_modified") != existing.last_modified:
                        changes.append("last_modified")
                    if http_metadata.get("content_length") != existing.content_length:
                        changes.append("content_length")
                    if http_metadata.get("etag") != existing.etag:
                        changes.append("etag")
                    self._print(
                        f"        RE-DOWNLOAD: {file_name} ({', '.join(changes)} changed)"
                    )
                elif metadata_updated:
                    # Only metadata changed (URL token, context) - save but don't re-download
                    existing.updated_at = datetime.now()
                    db_session.flush()
                    db_session.commit()
                    self._print(f"        REFRESH: {file_name} (URL token updated)")
                else:
                    self._print(f"        SKIP: {file_name} (unchanged)")
                    # Still commit to ensure any session state is flushed
                    db_session.commit()

            else:
                # Create new record with navigation context
                # Build navigation path for context preservation (like original folder structure)
                navigation_path = " > ".join(navigation_context["path"])

                import_status = ImportStatus(
                    file_url=file_url,
                    file_name=file_name,
                    file_type=fallback_metadata["file_type"],
                    category=category,
                    legislatura=legislatura,
                    sub_series=sub_series,
                    session=session,
                    number=number,
                    # Store navigation path for debugging and context preservation
                    navigation_context=(
                        navigation_path
                        if len(navigation_context["path"]) > 2
                        else None
                    ),
                    # HTTP metadata for change detection
                    last_modified=http_metadata.get("last_modified"),
                    content_length=http_metadata.get("content_length"),
                    etag=http_metadata.get("etag"),
                    discovered_at=datetime.now(),
                    # Discovery metadata for debugging and URL refresh
                    source_page_url=source_page_url,
                    anchor_text=anchor_text,
                    url_pattern=url_pattern,
                    status="discovered",
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                db_session.add(import_status)
                # Flush immediately to persist the discovery
                db_session.flush()
                self._print(
                    f"        SUCCESS: Cataloged: {file_name} (Cat: {category}, Leg: {legislatura})"
                )

            # Commit the transaction immediately after each file discovery
            db_session.commit()
            return 1

        except Exception as e:
            # Rollback the transaction on error to maintain consistency
            try:
                db_session.rollback()
            except:
                pass  # Ignore rollback errors
            self._print(f"        ERROR: Error cataloging {file_name}: {e}")
            return 0

    def _is_dar_file(self, navigation_path: List[str], file_url: str) -> bool:
        """Check if this is a DAR (Diário da Assembleia da República) file"""
        if not navigation_path:
            return False
        
        # Check if DAR is in the navigation path
        first_level = navigation_path[0].lower() if navigation_path else ""
        return "dar" in first_level or "diário" in first_level or "diario" in first_level

    def _extract_dar_hierarchy_from_navigation(self, navigation_path: List[str], file_name: str) -> Tuple[str, Dict]:
        """
        Extract DAR hierarchical structure from navigation path.
        Expected structure: dar > Série I > XVII Legislatura > Sessão 01 > Número 001 > file.xml
        
        Returns: (category, dar_metadata)
        """
        dar_metadata = {
            "sub_series": None,
            "legislature": None,
            "session": None,
            "number": None
        }
        
        # Base category
        category = "Diário da Assembleia da República"
        
        if len(navigation_path) < 2:
            return category, dar_metadata
        
        # Parse navigation path (skip first 'dar' element)
        for i, path_element in enumerate(navigation_path[1:], 1):
            element_lower = path_element.lower()
            
            # Extract series (e.g., "Série I", "Série II-A")
            if "série" in element_lower or "serie" in element_lower:
                # Clean and standardize series format
                series_match = re.search(r"s[eé]rie\s*(.*)", path_element, re.IGNORECASE)
                if series_match:
                    series_part = series_match.group(1).strip()
                    dar_metadata["sub_series"] = f"Série {series_part}" if series_part else "Série I"
                    
            # Extract legislature (e.g., "XVII Legislatura")
            elif "legislatura" in element_lower:
                leg_match = re.search(r"([xvii]+)\s*legislatura", path_element, re.IGNORECASE)
                if leg_match:
                    dar_metadata["legislature"] = leg_match.group(1).upper()
                    
            # Extract session (e.g., "Sessão 01")
            elif "sess" in element_lower:
                session_match = re.search(r"sess[aã]o\s*(\d+)", path_element, re.IGNORECASE)
                if session_match:
                    session_num = session_match.group(1).zfill(2)  # Pad to 2 digits
                    dar_metadata["session"] = f"Sessão {session_num}"
                    
            # Extract number from path element (e.g., "Número 001")
            elif "número" in element_lower or "numero" in element_lower:
                number_match = re.search(r"n[uú]mero\s*(\d+)", path_element, re.IGNORECASE)
                if number_match:
                    number_num = number_match.group(1).zfill(3)  # Pad to 3 digits
                    dar_metadata["number"] = f"Número {number_num}"
        
        # Also try to extract number from filename if not found in path
        if not dar_metadata["number"] and file_name:
            filename_number_match = re.search(r"n[uú]mero[_\s]*(\d+)", file_name, re.IGNORECASE)
            if filename_number_match:
                number_num = filename_number_match.group(1).zfill(3)
                dar_metadata["number"] = f"Número {number_num}"
        
        return category, dar_metadata

    def _get_http_metadata(self, url: str) -> Dict:
        """Get HTTP metadata using HEAD request (if enabled)"""
        if not self.enable_metadata_requests:
            return {}  # Return empty metadata if HEAD requests are disabled
        
        try:
            metadata_raw = self.http_client.get_metadata(url, indent="          ")
            
            # Convert to the format expected by the rest of the code
            metadata = {}
            
            # Parse Last-Modified header  
            if metadata_raw.get("last_modified"):
                from email.utils import parsedate_to_datetime
                try:
                    metadata["last_modified"] = parsedate_to_datetime(metadata_raw["last_modified"])
                except:
                    pass
            
            # Parse Content-Length header
            if metadata_raw.get("content_length"):
                try:
                    metadata["content_length"] = int(metadata_raw["content_length"])
                except:
                    pass
            
            # Parse ETag header
            if metadata_raw.get("etag"):
                metadata["etag"] = metadata_raw["etag"]
            
            return metadata
            
        except Exception as e:
            self._print(f"          WARNING: HEAD request failed: {e}")
            return {}  # Return empty metadata on error

    def _matches_legislature(self, name: str, target_legislature: str) -> bool:
        """Check if item name matches target legislature"""
        if not target_legislature or target_legislature.lower() == "all":
            return True

        # Handle "latest" by converting to actual latest legislature
        if target_legislature.lower() == "latest":
            target_legislature = "XVII"

        name_upper = name.upper()
        target_upper = target_legislature.upper()

        # Roman numeral mapping
        roman_map = {
            "1": "I",
            "2": "II",
            "3": "III",
            "4": "IV",
            "5": "V",
            "6": "VI",
            "7": "VII",
            "8": "VIII",
            "9": "IX",
            "10": "X",
            "11": "XI",
            "12": "XII",
            "13": "XIII",
            "14": "XIV",
            "15": "XV",
            "16": "XVI",
            "17": "XVII",
            "18": "XVIII",
            "19": "XIX",
            "20": "XX",
        }

        # Build target variants
        target_variants = {target_upper}

        if target_upper.isdigit():
            # Target is number - add roman equivalent
            roman = roman_map.get(target_upper)
            if roman:
                target_variants.add(roman)
        else:
            # Target is roman - add numeric equivalent
            for num, roman in roman_map.items():
                if target_upper == roman:
                    target_variants.add(num)
                    break

        # Special case for Constituinte
        if target_upper == "CONSTITUINTE":
            target_variants.add("CONS")

        # Check if any variant matches
        for variant in target_variants:
            if re.search(r"\b" + re.escape(variant) + r"\b", name_upper):
                return True

        return False

    def _normalize_section_category(self, section_name: str) -> str:
        """Extract normalized category from section name"""
        # Map section names to standardized categories
        section_lower = section_name.lower()

        category_map = {
            "boletim informativo": "Agenda Parlamentar",
            "atividade deputado": "Atividade Deputado",
            "atividades": "Atividades",
            "composição órgãos": "Composição Órgãos",
            "cooperação parlamentar": "Cooperação Parlamentar",
            "delegações eventuais": "Delegações Eventuais",
            "delegações permanentes": "Delegações Permanentes",
            "informação base": "Informação Base",
            "registo biográfico": "Registo Biográfico",
            "iniciativas": "Iniciativas",
            "intervenções": "Intervenções",
            "petições": "Petições",
            "perguntas requerimentos": "Perguntas Requerimentos",
            "diplomas aprovados": "Diplomas Aprovados",
            "orçamento estado": "Orçamento Estado",
            "reuniões visitas": "Reuniões Visitas",
            "grupos amizade": "Grupos Amizade",
            "diário assembleia": "Diário Assembleia",
        }

        for key, category in category_map.items():
            if key in section_lower:
                return category

        return section_name  # Return original if no match

    def _extract_legislature_from_navigation(
        self, navigation_item: str
    ) -> Optional[str]:
        """Extract legislature from navigation hierarchy item"""
        # This is more reliable than filename parsing because it uses the site's own navigation
        patterns = [
            r"([XVII]+)\s*Legislatura",
            r"Legislatura\s*([XVII]+)",
            r"([XVII]+)ª?\s*Leg(?:islatura)?",
            r"^([XVII]+)$",  # Just roman numerals
            r"(Constituinte)",
        ]

        for pattern in patterns:
            match = re.search(pattern, navigation_item, re.IGNORECASE)
            if match:
                leg = match.group(1).upper()
                if leg == "CONSTITUINTE":
                    return "Constituinte"
                return leg

        return None

    def _extract_subcategory_from_navigation(
        self, navigation_item: str, parent_category: str
    ) -> Optional[str]:
        """Extract subcategory from deeper navigation levels (like original folder structure)"""
        # Common subcategories found in parliament data
        subcategory_patterns = {
            # DAR (Diário Assembleia) subcategories
            "Serie I": "Serie I",
            "Serie II": "Serie II",
            "Serie II-A": "Serie II-A",
            "Serie II-B": "Serie II-B",
            "Serie II-C": "Serie II-C",
            # Session patterns
            "Sessao": "Sessão",
            "Session": "Sessão",
            # Common navigation subcategories
            "Decretos": "Decretos",
            "Resoluções": "Resoluções",
            "Projetos": "Projetos",
            "Propostas": "Propostas",
            "Petições": "Petições",
            "Requerimentos": "Requerimentos",
            "Perguntas": "Perguntas",
            "Grupo": "Grupos",
            "Comissão": "Comissões",
            "Delegação": "Delegações",
        }

        item_lower = navigation_item.lower()

        for pattern, subcategory in subcategory_patterns.items():
            if pattern.lower() in item_lower:
                # Don't return subcategory if it's the same as parent category
                if parent_category and subcategory.lower() in parent_category.lower():
                    continue
                return subcategory

        # If item looks like a meaningful subcategory (not just files), return it
        if (
            not any(
                ext in item_lower for ext in [".xml", ".json", ".pdf", ".zip", ".xsd"]
            )
            and len(navigation_item) > 2
            and len(navigation_item) < 50
        ):
            return navigation_item

        return None
    
    def _extract_url_pattern(self, file_url: str) -> Optional[str]:
        """Extract heuristic URL pattern for potential token refresh"""
        from urllib.parse import urlparse, parse_qs
        
        try:
            parsed = urlparse(file_url)
            
            # Parliament doc.xml/doc.txt pattern: doc.xml?path=...&fich=...
            if 'doc.xml' in parsed.path or 'doc.txt' in parsed.path:
                query_params = parse_qs(parsed.query)
                if 'path' in query_params and 'fich' in query_params:
                    doc_type = 'doc.xml' if 'doc.xml' in parsed.path else 'doc.txt'
                    fich_param = query_params['fich'][0] if query_params['fich'] else None
                    inline_param = '&Inline=true' if 'Inline' in query_params else ''
                    return f"{doc_type}?path=TOKEN&fich={fich_param}{inline_param}"
            
            # List service pattern: Lists.asmx/GetListItems?listname=...
            elif 'Lists.asmx/GetListItems' in file_url:
                query_params = parse_qs(parsed.query)
                if 'listname' in query_params:
                    listname = query_params['listname'][0] if query_params['listname'] else None
                    return f"Lists.asmx/GetListItems?listname={listname}&PARAMS=TOKEN"
            
            # Other parliament service patterns
            elif '.aspx' in parsed.path:
                return f"{parsed.path.split('/')[-1]}?PARAMS=TOKEN"
            
            # Generic file download pattern
            elif any(ext in file_url.lower() for ext in ['.xml', '.json', '.pdf', '.zip']):
                path_parts = parsed.path.split('/')
                if len(path_parts) > 2:
                    return f".../{path_parts[-2]}/{path_parts[-1]}"
            
        except Exception:
            pass  # Return None on any parsing error
        
        return None
    
    def recrawl_files(self, status_filter: str = 'recrawl') -> int:
        """Recrawl files with 'recrawl' status to refresh their URLs"""
        self._print(f"Starting recrawl of files with status '{status_filter}'")
        
        recrawled_count = 0
        
        with DatabaseSession() as db_session:
            # Get all files that need recrawling
            files_to_recrawl = db_session.query(ImportStatus).filter_by(status=status_filter).all()
            
            if not files_to_recrawl:
                self._print(f"No files found with status '{status_filter}'")
                return 0
                
            self._print(f"Found {len(files_to_recrawl)} files to recrawl")
            
            for i, import_record in enumerate(files_to_recrawl, 1):
                self._print(f"\n[{i}/{len(files_to_recrawl)}] Recrawling: {import_record.file_name}")
                
                if self._recrawl_single_file(db_session, import_record):
                    recrawled_count += 1
                    self._print(f"    SUCCESS: URL refreshed")
                else:
                    self._print(f"    FAILED: Could not refresh URL")
                
                # Rate limiting between recrawl attempts
                time.sleep(self.rate_limit_delay)
        
        self._print(f"\nRecrawl complete: {recrawled_count}/{len(files_to_recrawl)} files refreshed")
        return recrawled_count
    
    def _recrawl_single_file(self, db_session, import_record: ImportStatus) -> bool:
        """Recrawl a single file to refresh its URL"""
        try:
            # Step 1: Check if we have the necessary metadata for recrawling
            if not import_record.source_page_url:
                self._print(f"    ERROR: No source_page_url available for {import_record.file_name}")
                return False
            
            if not import_record.anchor_text:
                self._print(f"    ERROR: No anchor_text available for {import_record.file_name}")
                return False
            
            self._print(f"    Source page: {import_record.source_page_url[:60]}...")
            self._print(f"    Looking for: {import_record.anchor_text}")
            
            # Step 2: Fetch the source page
            try:
                response = self.http_client.get(import_record.source_page_url)
                response.raise_for_status()
            except Exception as e:
                self._print(f"    ERROR: Failed to fetch source page: {e}")
                return False
            
            # Step 3: Parse the page and look for our anchor text
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for links with matching anchor text
            matching_links = []
            for link in soup.find_all('a', href=True):
                link_text = link.get_text(strip=True)
                if link_text == import_record.anchor_text:
                    href = link['href']
                    full_url = urljoin(import_record.source_page_url, href)
                    matching_links.append(full_url)
            
            if not matching_links:
                self._print(f"    ERROR: Anchor text '{import_record.anchor_text}' not found on source page")
                return False
            
            if len(matching_links) > 1:
                self._print(f"    WARNING: Found {len(matching_links)} links with same anchor text, using first one")
            
            new_url = matching_links[0]
            self._print(f"    Found new URL: {new_url[:60]}...")
            
            # Step 4: Verify the new URL is different and valid
            if new_url == import_record.file_url:
                self._print(f"    INFO: URL unchanged, marking as discovered")
                import_record.status = 'discovered'
                import_record.recrawl_count = (import_record.recrawl_count or 0) + 1
                import_record.updated_at = datetime.now()
                db_session.commit()
                return True
            
            # Step 5: Test the new URL with a HEAD request
            try:
                test_response = self.http_client.head(new_url)
                if test_response.status_code not in [200, 302, 303, 307, 308]:
                    self._print(f"    ERROR: New URL returns status {test_response.status_code}")
                    return False
            except Exception as e:
                self._print(f"    WARNING: HEAD request failed, but continuing: {e}")
            
            # Step 6: Update the record with the new URL
            import_record.file_url = new_url
            import_record.status = 'discovered'  # Reset to discovered for re-processing
            import_record.recrawl_count = (import_record.recrawl_count or 0) + 1
            import_record.updated_at = datetime.now()
            
            # Update HTTP metadata if we got it from the HEAD request
            if 'test_response' in locals() and test_response.status_code == 200:
                http_metadata = {}
                if 'Last-Modified' in test_response.headers:
                    from email.utils import parsedate_to_datetime
                    try:
                        http_metadata['last_modified'] = parsedate_to_datetime(
                            test_response.headers['Last-Modified']
                        )
                    except:
                        pass
                if 'Content-Length' in test_response.headers:
                    try:
                        http_metadata['content_length'] = int(test_response.headers['Content-Length'])
                    except:
                        pass
                if 'ETag' in test_response.headers:
                    http_metadata['etag'] = test_response.headers['ETag']
                
                # Update HTTP metadata
                if http_metadata.get('last_modified'):
                    import_record.last_modified = http_metadata['last_modified']
                if http_metadata.get('content_length'):
                    import_record.content_length = http_metadata['content_length']
                if http_metadata.get('etag'):
                    import_record.etag = http_metadata['etag']
            
            # Commit the changes
            db_session.commit()
            return True
            
        except Exception as e:
            self._print(f"    ERROR: Recrawl failed: {e}")
            # Mark as failed so it doesn't keep trying
            import_record.status = 'failed'
            import_record.error_message = f"Recrawl failed: {str(e)}"
            import_record.updated_at = datetime.now()
            try:
                db_session.commit()
            except:
                db_session.rollback()
            return False


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="Parliament Data Discovery Service")
    parser.add_argument(
        "--discover-all", action="store_true", help="Discover all available files"
    )
    parser.add_argument(
        "--recrawl", action="store_true", help="Recrawl files with 'recrawl' status to refresh URLs"
    )
    parser.add_argument(
        "--recrawl-status", type=str, default="recrawl", 
        help="Status of files to recrawl (default: recrawl)"
    )
    parser.add_argument(
        "--legislature",
        type=str,
        help="Filter by legislature (e.g., XVII, 17, Constituinte)",
    )
    parser.add_argument(
        "--category", type=str, help='Filter by category (e.g., "Atividade Deputado")'
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=0.5,
        help="Rate limit delay between requests (default: 0.5s)",
    )

    args = parser.parse_args()

    # Create discovery service
    service = DiscoveryService(rate_limit_delay=args.rate_limit)

    if args.recrawl:
        # Run recrawl functionality
        recrawled_count = service.recrawl_files(status_filter=args.recrawl_status)
        print(f"\nFINISH: Recrawl completed: {recrawled_count} URLs refreshed")
        
    elif args.discover_all:
        # Run discovery
        discovered_count = service.discover_all_files(
            legislature_filter=args.legislature, category_filter=args.category
        )
        print(f"\nFINISH: Discovery completed: {discovered_count} files cataloged")
        
    else:
        print("Use --discover-all to start discovery or --recrawl to refresh URLs")
        print("Example: python discovery_service.py --recrawl")
        return


if __name__ == "__main__":
    main()
