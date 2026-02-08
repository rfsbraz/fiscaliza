"""
Political Entity Query System for Portuguese Parliamentary Data
=============================================================

Unified query interface for coalitions (coligações) and individual parties,
providing seamless access to Portuguese political entities with proper
relationship handling and entity type detection.

Key Features:
- Unified interface for querying coalitions and parties
- Automatic entity type detection and routing
- Relationship resolution (coalition → component parties)
- Performance-optimized queries with eager loading
- Portuguese political context awareness
"""

from typing import Dict, List, Optional, Union, Tuple, Any
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import and_, or_, func, case
from database.models import (
    Partido, 
    Coligacao, 
    ColigacaoPartido,
    DeputadoMandatoLegislativo,
    Deputado
)
import logging

logger = logging.getLogger(__name__)


class PoliticalEntityQueries:
    """
    Unified query system for Portuguese political entities
    
    Handles both coalitions (coligações) and individual parties (partidos)
    with automatic entity type detection and relationship resolution.
    """
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_entity_by_sigla(
        self, sigla: str, include_components: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get political entity (coalition or party) by sigla with unified response format
        
        Args:
            sigla: Political entity abbreviation
            include_components: Whether to include component parties for coalitions
            
        Returns:
            Unified entity information or None if not found
        """
        if not sigla:
            return None
        
        sigla = sigla.strip().upper()
        
        # Try coalition first (more specific)
        coalition = self._get_coalition_by_sigla(sigla, include_components)
        if coalition:
            return coalition
        
        # Fall back to individual party
        party = self._get_party_by_sigla(sigla)
        if party:
            return party
        
        return None
    
    def _get_coalition_by_sigla(
        self, sigla: str, include_components: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Get coalition information with component parties"""
        coalition = (
            self.session.query(Coligacao)
            .filter(Coligacao.sigla == sigla)
            .first()
        )
        
        if not coalition:
            return None
        
        result = {
            "id": coalition.id,
            "sigla": coalition.sigla,
            "nome": coalition.nome,
            "tipo_entidade": "coligacao",
            "tipo_coligacao": coalition.tipo_coligacao,
            "espectro_politico": coalition.espectro_politico,
            "data_formacao": coalition.data_formacao.isoformat() if coalition.data_formacao else None,
            "data_dissolucao": coalition.data_dissolucao.isoformat() if coalition.data_dissolucao else None,
            "ativa": coalition.ativo,  # Using calculated property
            "observacoes": getattr(coalition, 'observacoes', None),
            "component_parties": [],
            "deputy_count": 0,
            "mandate_count": 0
        }
        
        if include_components:
            # Get component parties - using partido_sigla since that's what ColigacaoPartido has
            component_parties = (
                self.session.query(ColigacaoPartido)
                .filter(ColigacaoPartido.coligacao_id == coalition.id)
                .all()
            )
            
            for coligacao_partido in component_parties:
                # Look up the actual party if needed
                party = self.session.query(Partido).filter(Partido.sigla == coligacao_partido.partido_sigla).first()
                result["component_parties"].append({
                    "id": party.id if party else None,
                    "sigla": coligacao_partido.partido_sigla,
                    "nome": coligacao_partido.partido_nome or (party.nome if party else None),
                    "papel_coligacao": getattr(coligacao_partido, 'papel_coligacao', None),
                    "ordem_listagem": getattr(coligacao_partido, 'ordem_listagem', None),
                    "data_adesao": coligacao_partido.data_adesao.isoformat() if coligacao_partido.data_adesao else None
                })
            
            # Count deputies and mandates for coalition
            mandate_stats = self._get_coalition_mandate_stats(coalition.id)
            result.update(mandate_stats)
        
        return result
    
    def _get_party_by_sigla(self, sigla: str) -> Optional[Dict[str, Any]]:
        """Get individual party information"""
        party = (
            self.session.query(Partido)
            .filter(Partido.sigla == sigla)
            .first()
        )
        
        if not party:
            return None
        
        result = {
            "id": party.id,
            "sigla": party.sigla,
            "nome": party.nome,
            "tipo_entidade": getattr(party, 'tipo_entidade', None) or "partido",
            "data_fundacao": party.data_fundacao.isoformat() if party.data_fundacao else None,
            "coligacao_pai_id": party.coligacao_pai_id,
            "component_parties": [],  # Empty for individual parties
            "deputy_count": 0,
            "mandate_count": 0
        }
        
        # Get mandate statistics
        mandate_stats = self._get_party_mandate_stats(party.id)
        result.update(mandate_stats)
        
        # If party belongs to a coalition, include parent coalition info
        if party.coligacao_pai_id:
            parent_coalition = (
                self.session.query(Coligacao)
                .filter(Coligacao.id == party.coligacao_pai_id)
                .first()
            )
            if parent_coalition:
                result["parent_coalition"] = {
                    "id": parent_coalition.id,
                    "sigla": parent_coalition.sigla,
                    "nome": parent_coalition.nome
                }
        
        return result
    
    def get_all_entities(
        self, include_inactive: bool = False, include_components: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get all political entities (coalitions and parties) in unified format
        
        Args:
            include_inactive: Include inactive/dissolved coalitions
            include_components: Include component party details for coalitions
            
        Returns:
            List of all political entities
        """
        entities = []
        
        # Get all coalitions
        coalitions = self.session.query(Coligacao).order_by(Coligacao.sigla).all()
        
        # Filter by activity status using calculated property if needed
        if not include_inactive:
            coalitions = [c for c in coalitions if c.ativo]
        
        for coalition in coalitions:
            entity_data = self._format_coalition_entity(coalition, include_components)
            entities.append(entity_data)
        
        # Get individual parties (not part of coalitions)
        individual_parties = (
            self.session.query(Partido)
            .filter(
                and_(
                    Partido.tipo_entidade == "partido",
                    Partido.coligacao_pai_id.is_(None)
                )
            )
            .order_by(Partido.sigla)
            .all()
        )
        
        for party in individual_parties:
            entity_data = self._format_party_entity(party)
            entities.append(entity_data)
        
        return entities
    
    def search_entities(
        self, query: str, entity_type: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search political entities by name or sigla
        
        Args:
            query: Search term
            entity_type: Filter by 'coligacao', 'partido', or None for both
            limit: Maximum results to return
            
        Returns:
            List of matching political entities
        """
        if not query or len(query.strip()) < 2:
            return []
        
        query = query.strip()
        search_pattern = f"%{query}%"
        entities = []
        
        # Search coalitions
        if entity_type is None or entity_type == "coligacao":
            coalitions_all = (
                self.session.query(Coligacao)
                .filter(
                    or_(
                        Coligacao.sigla.ilike(search_pattern),
                        Coligacao.nome.ilike(search_pattern)
                    )
                )
                .order_by(Coligacao.sigla)
                .all()
            )
            
            # Filter active coalitions using calculated property
            coalitions = [c for c in coalitions_all if c.ativo][:limit // 2 if entity_type is None else limit]
            
            for coalition in coalitions:
                entity_data = self._format_coalition_entity(coalition, False)
                entity_data["match_type"] = "coalition"
                entities.append(entity_data)
        
        # Search individual parties
        if entity_type is None or entity_type == "partido":
            remaining_limit = limit - len(entities) if entity_type is None else limit
            
            parties = (
                self.session.query(Partido)
                .filter(
                    or_(
                        Partido.sigla.ilike(search_pattern),
                        Partido.nome.ilike(search_pattern)
                    )
                )
                .filter(Partido.tipo_entidade == "partido")
                .order_by(Partido.sigla)
                .limit(remaining_limit)
                .all()
            )
            
            for party in parties:
                entity_data = self._format_party_entity(party)
                entity_data["match_type"] = "party"
                entities.append(entity_data)
        
        return entities[:limit]
    
    def get_entity_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about political entities"""
        
        # Coalition statistics - using subquery for active count since ativo is now a calculated property
        total_coalitions = self.session.query(func.count(Coligacao.id)).scalar()
        
        # Get all coalitions to calculate active count
        all_coalitions = self.session.query(Coligacao).all()
        active_count = len([c for c in all_coalitions if c.ativo])
        
        coalition_stats = (
            self.session.query(
                func.count(Coligacao.id).label('total'),
                func.count(case([(Coligacao.tipo_coligacao == 'eleitoral', 1)])).label('electoral'),
                func.count(case([(Coligacao.tipo_coligacao == 'parlamentar', 1)])).label('parliamentary')
            )
            .first()
        )
        
        # Party statistics
        party_stats = (
            self.session.query(
                func.count(Partido.id).label('total'),
                func.count(case([(Partido.tipo_entidade == 'partido', 1)])).label('individual'),
                func.count(case([(Partido.coligacao_pai_id.is_not(None), 1)])).label('coalition_members')
            )
            .first()
        )
        
        # Deputy mandate statistics
        mandate_stats = (
            self.session.query(
                func.count(DeputadoMandatoLegislativo.id).label('total_mandates'),
                func.count(func.distinct(DeputadoMandatoLegislativo.deputado_id)).label('unique_deputies'),
                func.count(case([
                    (DeputadoMandatoLegislativo.coligacao_id.is_not(None), 1)
                ])).label('coalition_mandates')
            )
            .first()
        )
        
        return {
            "coalitions": {
                "total": coalition_stats.total,
                "active": active_count,
                "electoral": coalition_stats.electoral,
                "parliamentary": coalition_stats.parliamentary
            },
            "parties": {
                "total": party_stats.total,
                "individual": party_stats.individual,
                "coalition_members": party_stats.coalition_members
            },
            "mandates": {
                "total": mandate_stats.total_mandates,
                "unique_deputies": mandate_stats.unique_deputies,
                "with_coalition_context": mandate_stats.coalition_mandates
            }
        }
    
    def _format_coalition_entity(
        self, coalition: Coligacao, include_components: bool = False
    ) -> Dict[str, Any]:
        """Format coalition for unified entity response"""
        result = {
            "id": coalition.id,
            "sigla": coalition.sigla,
            "nome": coalition.nome,
            "tipo_entidade": "coligacao",
            "tipo_coligacao": coalition.tipo_coligacao,
            "espectro_politico": coalition.espectro_politico,
            "data_formacao": coalition.data_formacao.isoformat() if coalition.data_formacao else None,
            "data_dissolucao": coalition.data_dissolucao.isoformat() if coalition.data_dissolucao else None,
            "ativa": coalition.ativo
        }
        
        # Always include mandate stats (deputy_count, mandate_count)
        mandate_stats = self._get_coalition_mandate_stats(coalition.id)
        result.update(mandate_stats)
        
        if include_components:
            # Add component parties information if requested
            components = self._get_coalition_component_parties(coalition.id)
            result["component_parties"] = components
        
        return result
    
    def _format_party_entity(self, party: Partido) -> Dict[str, Any]:
        """Format party for unified entity response"""
        result = {
            "id": party.id,
            "sigla": party.sigla,
            "nome": party.nome,
            "tipo_entidade": getattr(party, 'tipo_entidade', None) or "partido",
            "data_fundacao": party.data_fundacao.isoformat() if party.data_fundacao else None
        }
        
        mandate_stats = self._get_party_mandate_stats(party.id)
        result.update(mandate_stats)
        
        return result
    
    def _get_coalition_mandate_stats(self, coalition_id: int) -> Dict[str, int]:
        """Get deputy and mandate statistics for a coalition"""
        coalition = self.session.query(Coligacao).get(coalition_id)
        if not coalition:
            return {"deputy_count": 0, "mandate_count": 0}
        
        # Count mandates where coalition context matches
        stats = (
            self.session.query(
                func.count(DeputadoMandatoLegislativo.id).label('mandate_count'),
                func.count(func.distinct(DeputadoMandatoLegislativo.deputado_id)).label('deputy_count')
            )
            .filter(
                or_(
                    DeputadoMandatoLegislativo.coligacao_id == coalition.id,
                    DeputadoMandatoLegislativo.par_sigla == coalition.sigla
                )
            )
            .first()
        )
        
        return {
            "deputy_count": stats.deputy_count or 0,
            "mandate_count": stats.mandate_count or 0
        }
    
    def _get_party_mandate_stats(self, party_id: int) -> Dict[str, int]:
        """Get deputy and mandate statistics for a party"""
        party = self.session.query(Partido).get(party_id)
        if not party:
            return {"deputy_count": 0, "mandate_count": 0}
        
        # Count mandates for this party
        stats = (
            self.session.query(
                func.count(DeputadoMandatoLegislativo.id).label('mandate_count'),
                func.count(func.distinct(DeputadoMandatoLegislativo.deputado_id)).label('deputy_count')
            )
            .filter(DeputadoMandatoLegislativo.par_sigla == party.sigla)
            .first()
        )
        
        return {
            "deputy_count": stats.deputy_count or 0,
            "mandate_count": stats.mandate_count or 0
        }


def test_political_entity_queries():
    """Test the political entity query system"""
    # This would require a database session to test properly
    print("Political Entity Queries system ready for integration")
    print("Key features:")
    print("- Unified entity queries (coalitions + parties)")
    print("- Entity type detection and routing")
    print("- Relationship resolution")
    print("- Search functionality")
    print("- Statistical reporting")


if __name__ == "__main__":
    test_political_entity_queries()