"""
Data Attribution Utilities
===========================

Provides data provenance tracking for API responses, allowing users to trace
where data comes from and enabling developers to debug data issues.

Usage:
    from app.utils.attribution import AttributionBuilder

    # In an API endpoint:
    attribution = AttributionBuilder(session, detailed=detailed_mode)

    # Track queries as they're made
    deputies = session.query(Deputado).filter(...).all()
    attribution.track_query(Deputado, deputies)

    # Include attribution in response
    if include_attribution:
        response['_attribution'] = attribution.get_attribution()
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
import logging

logger = logging.getLogger(__name__)


@dataclass
class SourceAttribution:
    """Represents a single data source contribution to query results"""
    source_type: str          # Category from ImportStatus (e.g., 'RegistoBiografico', 'Iniciativas')
    file_name: str            # Original filename
    legislature: Optional[str] # Legislature designation
    imported_at: Optional[datetime]  # When the import was processed
    parliament_url: Optional[str]    # URL to original Parliament source
    record_count: int         # Number of records from this source


@dataclass
class QueryTrace:
    """Detailed trace of a single query for debugging"""
    purpose: str              # Description of what this query retrieves
    table: str                # Primary table queried
    records: int              # Number of records returned
    import_files: List[str]   # Files that contributed to these records


class AttributionBuilder:
    """
    Tracks data sources used during query execution for API attribution.

    Provides two modes:
    - Standard: Summary of sources used
    - Detailed: Full query traces and field-level attribution

    Example:
        attribution = AttributionBuilder(session, detailed=True)

        # Track a query
        deputies = query_deputies(...)
        attribution.track_query(Deputado, deputies, purpose="get_deputy_info")

        # Get attribution summary
        attr_data = attribution.get_attribution()
        # Returns: {
        #     'sources': [...],
        #     'source_types': ['RegistoBiografico'],
        #     'legislatures': ['XVII'],
        #     'total_sources': 1
        # }
    """

    def __init__(self, session, detailed: bool = False):
        """
        Initialize attribution builder.

        Args:
            session: SQLAlchemy database session
            detailed: If True, collect detailed query traces
        """
        self.session = session
        self.detailed = detailed
        self.sources_used: List[SourceAttribution] = []
        self.query_traces: List[QueryTrace] = []
        self._import_status_cache: Dict[str, Any] = {}
        self._tracked_import_ids: Set[str] = set()

    def track_query(
        self,
        model,
        records: List[Any],
        purpose: str = "query"
    ) -> None:
        """
        Track which import sources contributed to query results.

        Args:
            model: SQLAlchemy model class (for table name)
            records: List of ORM records returned by query
            purpose: Description of the query's purpose
        """
        if not records:
            return

        # Get unique import_status_ids from records
        import_ids = set()
        for record in records:
            if hasattr(record, 'import_status_id') and record.import_status_id:
                import_ids.add(str(record.import_status_id))

        if not import_ids:
            return

        # Get table name
        table_name = getattr(model, '__tablename__', str(model))

        # Fetch import status records (with caching)
        import_files = []
        for import_id in import_ids:
            # Skip if already tracked (avoid duplicates in summary)
            if import_id in self._tracked_import_ids:
                # Still add to query trace if in detailed mode
                import_status = self._get_import_status(import_id)
                if import_status and self.detailed:
                    import_files.append(import_status.file_name or "unknown")
                continue

            import_status = self._get_import_status(import_id)
            if import_status:
                self._tracked_import_ids.add(import_id)

                # Count records from this import
                record_count = len([
                    r for r in records
                    if hasattr(r, 'import_status_id') and str(r.import_status_id) == import_id
                ])

                self.sources_used.append(SourceAttribution(
                    source_type=import_status.category or "unknown",
                    file_name=import_status.file_name or "unknown",
                    legislature=import_status.legislatura,
                    imported_at=import_status.processing_completed_at,
                    parliament_url=import_status.file_url,
                    record_count=record_count
                ))

                if self.detailed:
                    import_files.append(import_status.file_name or "unknown")

        # Add query trace if in detailed mode
        if self.detailed and import_files:
            self.query_traces.append(QueryTrace(
                purpose=purpose,
                table=table_name,
                records=len(records),
                import_files=import_files
            ))

    def _get_import_status(self, import_id: str) -> Optional[Any]:
        """Get ImportStatus record with caching."""
        if import_id in self._import_status_cache:
            return self._import_status_cache[import_id]

        try:
            from database.models import ImportStatus
            import_status = self.session.query(ImportStatus).filter(
                ImportStatus.id == import_id
            ).first()
            self._import_status_cache[import_id] = import_status
            return import_status
        except Exception as e:
            logger.warning(f"Failed to get import status {import_id}: {e}")
            return None

    def get_attribution(self) -> Dict[str, Any]:
        """
        Return attribution summary.

        Returns dict with:
        - sources: List of SourceAttribution details
        - source_types: Unique list of source types
        - legislatures: Unique list of legislatures
        - total_sources: Count of unique sources

        If detailed mode is enabled, also includes:
        - query_trace: List of query traces
        """
        # Convert sources to dicts, handling datetime serialization
        sources = []
        for source in self.sources_used:
            source_dict = asdict(source)
            # Convert datetime to ISO format string for JSON serialization
            if source_dict.get('imported_at'):
                source_dict['imported_at'] = source_dict['imported_at'].isoformat()
            sources.append(source_dict)

        result = {
            'sources': sources,
            'source_types': list(set(s.source_type for s in self.sources_used)),
            'legislatures': list(set(
                s.legislature for s in self.sources_used if s.legislature
            )),
            'total_sources': len(self.sources_used)
        }

        if self.detailed:
            result['query_trace'] = [asdict(qt) for qt in self.query_traces]

        return result

    def add_parliament_profile_link(self, deputy_id: int) -> Optional[str]:
        """
        Generate link to Parliament's official deputy profile.

        Args:
            deputy_id: The deputy's BID (Biographical ID)

        Returns:
            URL to Parliament's deputy biography page
        """
        if deputy_id:
            return f"https://www.parlamento.pt/DeputadoGP/Paginas/Biografia.aspx?BID={deputy_id}"
        return None


def format_attribution_response(
    data: Dict[str, Any],
    attribution: AttributionBuilder,
    include_attribution: bool = False,
    deputy_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Helper function to add attribution to an API response.

    Args:
        data: The response data dict
        attribution: AttributionBuilder instance with tracked queries
        include_attribution: Whether to include attribution data
        deputy_id: Optional deputy ID to add profile link

    Returns:
        Data dict with _attribution added if requested
    """
    if not include_attribution:
        return data

    attribution_data = attribution.get_attribution()

    # Add Parliament profile link if deputy_id provided
    if deputy_id:
        profile_link = attribution.add_parliament_profile_link(deputy_id)
        if profile_link:
            attribution_data['parliament_profile'] = profile_link

    data['_attribution'] = attribution_data
    return data
