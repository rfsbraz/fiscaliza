#!/usr/bin/env python3
"""
Coalition Data Migration Script
==============================

Analyzes existing party data to detect coalitions and automatically creates
coalition records with proper relationships. This migration script applies
the coalition detection system to historical data.

Key Operations:
1. Analyze all party siglas in the database
2. Detect coalitions using the CoalitionDetector
3. Create coalition records and relationships
4. Update mandate records with coalition context
5. Generate migration summary report

Usage:
    python migrate_coalition_data.py [--dry-run] [--legislatura XVII]
"""

import sys
import argparse
import logging
from datetime import datetime
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple

# Add project root to path
sys.path.append('E:/dev/parliament')

from database.connection import DatabaseSession
from database.models import (
    Partido, Coligacao, ColigacaoPartido, DeputadoMandatoLegislativo
)
from scripts.data_processing.mappers.coalition_detector import CoalitionDetector, CoalitionDetection
from scripts.data_processing.mappers.political_entity_queries import PoliticalEntityQueries

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('coalition_migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class CoalitionDataMigrator:
    """
    Migrates existing party data to include coalition structure
    """
    
    def __init__(self, session: DatabaseSession, dry_run: bool = False):
        self.session = session
        self.dry_run = dry_run
        self.coalition_detector = CoalitionDetector()
        self.political_queries = PoliticalEntityQueries(session)
        
        # Migration statistics
        self.stats = {
            'parties_analyzed': 0,
            'coalitions_detected': 0,
            'coalitions_created': 0,
            'relationships_created': 0,
            'mandates_updated': 0,
            'errors': 0
        }
        
        # Track created entities
        self.created_coalitions = {}  # sigla -> coalition_id
        self.processed_parties = set()
        
    def run_migration(self, target_legislatura: str = None) -> Dict:
        """
        Run the complete coalition data migration
        
        Args:
            target_legislatura: Optional specific legislature to migrate
            
        Returns:
            Migration statistics and report
        """
        logger.info("="*60)
        logger.info("COALITION DATA MIGRATION STARTED")
        logger.info("="*60)
        logger.info(f"Dry run mode: {self.dry_run}")
        
        try:
            # Step 1: Analyze existing party data
            logger.info("Step 1: Analyzing existing party data...")
            party_siglas = self._get_unique_party_siglas(target_legislatura)
            logger.info(f"Found {len(party_siglas)} unique party siglas to analyze")
            
            # Step 2: Detect coalitions
            logger.info("Step 2: Detecting coalitions...")
            coalition_detections = self._detect_coalitions(party_siglas)
            logger.info(f"Detected {len(coalition_detections)} potential coalitions")
            
            # Step 3: Create coalition records
            logger.info("Step 3: Creating coalition records...")
            self._create_coalition_records(coalition_detections)
            
            # Step 4: Update mandate records with coalition context
            logger.info("Step 4: Updating mandate records...")
            self._update_mandate_coalition_context(target_legislatura)
            
            # Step 5: Generate summary report
            logger.info("Step 5: Generating migration report...")
            report = self._generate_migration_report()
            
            if not self.dry_run:
                self.session.commit()
                logger.info("Migration committed successfully!")
            else:
                self.session.rollback()
                logger.info("Dry run completed - no changes committed")
                
            return report
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            self.session.rollback()
            self.stats['errors'] += 1
            raise
    
    def _get_unique_party_siglas(self, target_legislatura: str = None) -> Set[str]:
        """Get unique party siglas from mandate records"""
        query = self.session.query(DeputadoMandatoLegislativo.par_sigla).distinct()
        
        if target_legislatura:
            query = query.filter(DeputadoMandatoLegislativo.leg_des == target_legislatura)
        
        siglas = {result.par_sigla for result in query.all() if result.par_sigla}
        self.stats['parties_analyzed'] = len(siglas)
        return siglas
    
    def _detect_coalitions(self, party_siglas: Set[str]) -> List[CoalitionDetection]:
        """Detect coalitions from party siglas"""
        coalitions = []
        
        for sigla in sorted(party_siglas):
            logger.debug(f"Analyzing: {sigla}")
            detection = self.coalition_detector.detect(sigla)
            
            if detection.is_coalition and detection.confidence >= 0.7:
                coalitions.append(detection)
                logger.info(f"Coalition detected: {sigla} (confidence: {detection.confidence:.2f})")
        
        self.stats['coalitions_detected'] = len(coalitions)
        return coalitions
    
    def _create_coalition_records(self, detections: List[CoalitionDetection]) -> None:
        """Create coalition and coalition-party relationship records"""
        
        for detection in detections:
            try:
                # Check if coalition already exists
                existing = self.session.query(Coligacao).filter_by(
                    sigla=detection.coalition_sigla
                ).first()
                
                if existing:
                    logger.debug(f"Coalition {detection.coalition_sigla} already exists")
                    self.created_coalitions[detection.coalition_sigla] = existing.id
                    continue
                
                # Create coalition record
                coalition_data = {
                    'sigla': detection.coalition_sigla,
                    'nome': detection.coalition_name or f"Coligação {detection.coalition_sigla}",
                    'tipo_coligacao': 'eleitoral',  # Default type
                    'confianca_detecao': detection.confidence
                }
                
                # Add optional fields from detection
                if detection.political_spectrum:
                    coalition_data['espectro_politico'] = detection.political_spectrum
                if detection.formation_date:
                    coalition_data['data_formacao'] = detection.formation_date
                
                if not self.dry_run:
                    coalition = Coligacao(**coalition_data)
                    self.session.add(coalition)
                    self.session.flush()  # Get the ID
                    coalition_id = coalition.id
                else:
                    # Simulate ID for dry run
                    coalition_id = len(self.created_coalitions) + 1
                
                self.created_coalitions[detection.coalition_sigla] = coalition_id
                self.stats['coalitions_created'] += 1
                
                logger.info(f"Created coalition: {detection.coalition_sigla}")
                
                # Create coalition-party relationships
                self._create_coalition_party_relationships(detection, coalition_id)
                
            except Exception as e:
                logger.error(f"Error creating coalition {detection.coalition_sigla}: {e}")
                self.stats['errors'] += 1
    
    def _create_coalition_party_relationships(
        self, detection: CoalitionDetection, coalition_id: int
    ) -> None:
        """Create coalition-party relationship records"""
        
        for i, component in enumerate(detection.component_parties):
            try:
                # Ensure party record exists
                party = self._ensure_party_exists(component['sigla'], component['nome'])
                
                # Create relationship record
                relationship_data = {
                    'coligacao_id': coalition_id,
                    'partido_sigla': component['sigla'],
                    'partido_nome': component['nome'],
                    'ativo': True,
                    'papel_coligacao': 'componente'
                }
                
                if not self.dry_run:
                    relationship = ColigacaoPartido(**relationship_data)
                    self.session.add(relationship)
                    
                    # Update party to reference parent coalition if party object exists
                    if hasattr(party, 'id'):
                        party.coligacao_pai_id = coalition_id
                        party.tipo_entidade = 'partido'  # Component party
                
                self.stats['relationships_created'] += 1
                logger.debug(f"Created relationship: {detection.coalition_sigla} -> {component['sigla']}")
                
            except Exception as e:
                logger.error(f"Error creating relationship for {component['sigla']}: {e}")
                self.stats['errors'] += 1
    
    def _ensure_party_exists(self, sigla: str, nome: str) -> Partido:
        """Ensure party record exists, create if necessary"""
        party = self.session.query(Partido).filter_by(sigla=sigla).first()
        
        if not party:
            if not self.dry_run:
                party = Partido(
                    sigla=sigla,
                    nome=nome,
                    tipo_entidade='partido'
                )
                self.session.add(party)
                self.session.flush()
            else:
                # Create mock party for dry run
                class MockParty:
                    def __init__(self):
                        self.id = hash(sigla) % 10000
                        self.sigla = sigla
                        self.nome = nome
                party = MockParty()
            
            logger.debug(f"Created missing party record: {sigla}")
        
        return party
    
    def _update_mandate_coalition_context(self, target_legislatura: str = None) -> None:
        """Update mandate records with coalition context"""
        
        query = self.session.query(DeputadoMandatoLegislativo)
        if target_legislatura:
            query = query.filter(DeputadoMandatoLegislativo.leg_des == target_legislatura)
        
        mandates = query.all()
        logger.info(f"Updating {len(mandates)} mandate records with coalition context...")
        
        for mandate in mandates:
            try:
                if not mandate.par_sigla:
                    continue
                
                # Check if party belongs to a coalition
                detection = self.coalition_detector.detect(mandate.par_sigla)
                
                if detection.is_coalition and detection.confidence >= 0.7:
                    # Update with coalition context
                    coalition_id = self.created_coalitions.get(detection.coalition_sigla)
                    
                    if not self.dry_run:
                        mandate.tipo_entidade_politica = 'coligacao'
                        mandate.eh_coligacao = True
                        mandate.coligacao_id = coalition_id
                        mandate.coligacao_contexto_sigla = detection.coalition_sigla
                        mandate.coligacao_contexto_nome = detection.coalition_name
                        mandate.confianca_detecao_coligacao = detection.confidence
                    
                    self.stats['mandates_updated'] += 1
                    
                else:
                    # Mark as individual party
                    if not self.dry_run:
                        mandate.tipo_entidade_politica = 'partido'
                        mandate.eh_coligacao = False
                        mandate.coligacao_id = None
                        mandate.coligacao_contexto_sigla = None
                        mandate.coligacao_contexto_nome = None
                        mandate.confianca_detecao_coligacao = None
                
            except Exception as e:
                logger.error(f"Error updating mandate {mandate.id}: {e}")
                self.stats['errors'] += 1
        
        logger.info(f"Updated {self.stats['mandates_updated']} mandates with coalition context")
    
    def _generate_migration_report(self) -> Dict:
        """Generate comprehensive migration report"""
        
        # Analyze detection patterns
        detection_stats = self.coalition_detector.get_coalition_statistics(
            list(self.processed_parties)
        )
        
        report = {
            'migration_summary': {
                'timestamp': datetime.now().isoformat(),
                'dry_run': self.dry_run,
                'status': 'success' if self.stats['errors'] == 0 else 'completed_with_errors'
            },
            'statistics': self.stats.copy(),
            'detection_analysis': detection_stats,
            'created_coalitions': list(self.created_coalitions.keys()),
            'recommendations': []
        }
        
        # Add recommendations based on results
        if self.stats['coalitions_detected'] > self.stats['coalitions_created']:
            report['recommendations'].append(
                "Some detected coalitions were not created (possibly already exist)"
            )
        
        if self.stats['errors'] > 0:
            report['recommendations'].append(
                "Review migration log for errors and consider manual fixes"
            )
        
        if detection_stats['low_confidence'] > 0:
            report['recommendations'].append(
                "Review low-confidence detections for manual verification"
            )
        
        # Log summary
        logger.info("="*60)
        logger.info("MIGRATION SUMMARY")
        logger.info("="*60)
        for key, value in self.stats.items():
            logger.info(f"{key.replace('_', ' ').title()}: {value}")
        
        if self.created_coalitions:
            logger.info(f"Created coalitions: {', '.join(self.created_coalitions.keys())}")
        
        return report


def main():
    """Main migration script entry point"""
    parser = argparse.ArgumentParser(description='Migrate coalition data from existing party records')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without committing')
    parser.add_argument('--legislatura', type=str, help='Target specific legislature (e.g., XVII)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        with DatabaseSession() as session:
            migrator = CoalitionDataMigrator(session, dry_run=args.dry_run)
            report = migrator.run_migration(target_legislatura=args.legislatura)
            
            # Write report to file
            import json
            report_filename = f"coalition_migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Migration report saved to: {report_filename}")
            
            if report['migration_summary']['status'] == 'success':
                logger.info("Migration completed successfully!")
                return 0
            else:
                logger.warning("Migration completed with errors - check log for details")
                return 1
                
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)