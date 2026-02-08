#!/usr/bin/env python3
"""
Portuguese Parliament Analytics Calculator

This script calculates and updates all analytics tables for Portuguese Parliamentary data.
It can be run after data imports or when data refreshes to ensure analytics are up-to-date.

Usage:
    python calculate_analytics.py                    # Process all legislatures
    python calculate_analytics.py --legislature 15   # Process only XV Legislature
    python calculate_analytics.py --force-refresh    # Force recalculation of all data
    python calculate_analytics.py --verbose          # Show detailed progress
"""

import sys
import os
import argparse
import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from decimal import Decimal

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy import create_engine, text, func, case
from sqlalchemy.orm import sessionmaker
from database.models import (
    DeputyAnalytics, AttendanceAnalytics, InitiativeAnalytics, 
    DeputyTimeline, DataQualityMetrics,
    Deputado, MeetingAttendance, IniciativaParlamentar, IniciativaAutorDeputado,
    IntervencaoParlamentar, IntervencaoDeputado, Legislatura
)
from database.connection import get_engine


class AnalyticsCalculator:
    """
    Main analytics calculation engine for Portuguese Parliamentary data.
    
    This class handles all analytics calculations and updates for deputy performance,
    attendance patterns, initiative success rates, and data quality metrics.
    """
    
    def __init__(self, engine, verbose: bool = False):
        self.engine = engine
        self.Session = sessionmaker(bind=engine)
        self.verbose = verbose
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration."""
        logger = logging.getLogger('analytics_calculator')
        logger.setLevel(logging.DEBUG if self.verbose else logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def calculate_all_analytics(self, legislatura_id: Optional[int] = None, force_refresh: bool = False):
        """
        Calculate all analytics for the specified legislature or all legislatures.
        
        Args:
            legislatura_id: Optional legislature ID to filter processing
            force_refresh: Force recalculation even if data exists
        """
        start_time = datetime.now()
        self.logger.info(f"Starting analytics calculation at {start_time}")
        
        if legislatura_id:
            self.logger.info(f"Processing legislature {legislatura_id}")
            legislatures = [legislatura_id]
        else:
            legislatures = self._get_all_legislatures()
            self.logger.info(f"Processing {len(legislatures)} legislatures: {legislatures}")
        
        total_deputies = 0
        
        for legislature in legislatures:
            self.logger.info(f"Processing Legislature {legislature}...")
            
            # Get deputies for this legislature
            deputies = self._get_deputies_for_legislature(legislature)
            self.logger.info(f"Found {len(deputies)} deputies in Legislature {legislature}")
            total_deputies += len(deputies)
            
            # Process each analytics component
            self._calculate_deputy_analytics(deputies, legislature, force_refresh)
            self._calculate_attendance_analytics(deputies, legislature, force_refresh)
            self._calculate_initiative_analytics(deputies, legislature, force_refresh)
            self._calculate_deputy_timelines(deputies, legislature, force_refresh)
            self._calculate_data_quality_metrics(legislature)
            
            self.logger.info(f"Completed Legislature {legislature}")
        
        duration = datetime.now() - start_time
        self.logger.info(f"Analytics calculation completed for {total_deputies} deputies in {duration}")
    
    def _get_all_legislatures(self) -> List[int]:
        """Get all available legislature IDs."""
        with self.Session() as session:
            result = session.query(Legislatura.id).all()
            return [r[0] for r in result]
    
    def _get_deputies_for_legislature(self, legislatura_id: int) -> List[Dict[str, Any]]:
        """Get all deputies for a specific legislature."""
        with self.Session() as session:
            deputies = session.query(
                Deputado.id,
                Deputado.id_cadastro,
                Deputado.nome,
                Deputado.legislatura_id
            ).filter(
                Deputado.legislatura_id == legislatura_id
            ).all()
            
            return [
                {
                    'id': d.id,
                    'id_cadastro': d.id_cadastro,
                    'nome': d.nome,
                    'legislatura_id': d.legislatura_id
                }
                for d in deputies
            ]
    
    def _calculate_deputy_analytics(self, deputies: List[Dict], legislatura_id: int, force_refresh: bool):
        """Calculate core deputy analytics for all deputies."""
        self.logger.info(f"Calculating deputy analytics for {len(deputies)} deputies...")
        
        with self.Session() as session:
            for i, deputy in enumerate(deputies, 1):
                if self.verbose and i % 10 == 0:
                    self.logger.debug(f"Processing deputy {i}/{len(deputies)}: {deputy['nome']}")
                
                # Check if we need to calculate (new or force refresh)
                existing = session.query(DeputyAnalytics).filter(
                    DeputyAnalytics.deputado_id == deputy['id'],
                    DeputyAnalytics.legislatura_id == legislatura_id
                ).first()
                
                if existing and not force_refresh:
                    continue
                
                # Calculate attendance metrics
                attendance_data = self._calculate_attendance_metrics(session, deputy['id'], legislatura_id)
                
                # Calculate initiative metrics
                initiative_data = self._calculate_initiative_metrics(session, deputy['id'], legislatura_id)
                
                # Calculate intervention metrics
                intervention_data = self._calculate_intervention_metrics(session, deputy['id'], legislatura_id)
                
                # Calculate composite activity score
                activity_score = self._calculate_activity_score(
                    attendance_data, initiative_data, intervention_data
                )
                
                # Create or update record
                if existing:
                    # Update existing record
                    for key, value in {
                        'activity_score': activity_score,
                        'attendance_score': attendance_data['score'],
                        'initiative_score': initiative_data['score'],
                        'intervention_score': intervention_data['score'],
                        'total_sessions_attended': attendance_data['sessions_attended'],
                        'total_sessions_eligible': attendance_data['sessions_eligible'],
                        'attendance_percentage': attendance_data['percentage'],
                        'total_initiatives': initiative_data['total_initiatives'],
                        'total_interventions': intervention_data['total_interventions'],
                        'total_words_spoken': intervention_data['total_words'],
                        'initiatives_approved': initiative_data['approved'],
                        'approval_rate': initiative_data['approval_rate'],
                        'last_activity_date': max(
                            attendance_data.get('last_attendance') or date.min,
                            initiative_data.get('last_initiative') or date.min,
                            intervention_data.get('last_intervention') or date.min
                        ),
                        'calculation_date': datetime.now(),
                        'updated_at': datetime.now()
                    }.items():
                        setattr(existing, key, value)
                else:
                    # Create new record
                    analytics = DeputyAnalytics(
                        deputado_id=deputy['id'],
                        legislatura_id=legislatura_id,
                        activity_score=activity_score,
                        attendance_score=attendance_data['score'],
                        initiative_score=initiative_data['score'],
                        intervention_score=intervention_data['score'],
                        total_sessions_attended=attendance_data['sessions_attended'],
                        total_sessions_eligible=attendance_data['sessions_eligible'],
                        attendance_percentage=attendance_data['percentage'],
                        total_initiatives=initiative_data['total_initiatives'],
                        total_interventions=intervention_data['total_interventions'],
                        total_words_spoken=intervention_data['total_words'],
                        initiatives_approved=initiative_data['approved'],
                        approval_rate=initiative_data['approval_rate'],
                        last_activity_date=max(
                            attendance_data.get('last_attendance') or date.min,
                            initiative_data.get('last_initiative') or date.min,
                            intervention_data.get('last_intervention') or date.min
                        ),
                        calculation_date=datetime.now()
                    )
                    session.add(analytics)
            
            session.commit()
        
        self.logger.info(f"Completed deputy analytics calculation")
    
    def _calculate_attendance_metrics(self, session, deputado_id: int, legislatura_id: int) -> Dict[str, Any]:
        """Calculate attendance metrics for a deputy."""
        # Get attendance statistics
        attendance_query = session.query(
            func.count(MeetingAttendance.id).label('total_sessions'),
            func.sum(case((MeetingAttendance.sigla_falta == 'PT', 1), else_=0)).label('attended_sessions'),
            func.max(MeetingAttendance.dt_reuniao).label('last_attendance')
        ).filter(
            MeetingAttendance.dep_id == deputado_id
        ).first()
        
        total_sessions = attendance_query.total_sessions or 0
        attended_sessions = attendance_query.attended_sessions or 0
        last_attendance = attendance_query.last_attendance
        
        # Calculate percentage and score
        if total_sessions > 0:
            percentage = Decimal(str((attended_sessions / total_sessions) * 100))
            # Base score (0-85) plus consistency bonus (0-15)
            base_score = min(85, int(percentage * 0.85))
            
            # Calculate consistency bonus (simplified: months with >= 3 attendances)
            consistency_query = session.query(
                func.count().label('consistent_months')
            ).select_from(
                session.query(
                    func.year(MeetingAttendance.dt_reuniao).label('year'),
                    func.month(MeetingAttendance.dt_reuniao).label('month')
                ).filter(
                    MeetingAttendance.dep_id == deputado_id,
                    MeetingAttendance.sigla_falta == 'PT'
                ).group_by(
                    func.year(MeetingAttendance.dt_reuniao),
                    func.month(MeetingAttendance.dt_reuniao)
                ).having(func.count() >= 3).subquery()
            ).first()
            
            consistent_months = consistency_query.consistent_months or 0
            consistency_bonus = min(15, consistent_months * 2)
            score = min(100, base_score + consistency_bonus)
        else:
            percentage = Decimal('0.0')
            score = 0
        
        return {
            'sessions_eligible': total_sessions,
            'sessions_attended': attended_sessions,
            'percentage': percentage,
            'score': score,
            'last_attendance': last_attendance
        }
    
    def _calculate_initiative_metrics(self, session, deputado_id: int, legislatura_id: int) -> Dict[str, Any]:
        """Calculate initiative metrics for a deputy."""
        # Get initiative statistics
        initiatives_query = session.query(
            func.count(func.distinct(IniciativaParlamentar.id)).label('total_initiatives'),
            func.count(IniciativaParlamentar.id).label('approved'),  # TODO: Add proper status tracking
            func.max(IniciativaParlamentar.data_inicio_leg).label('last_initiative')
        ).join(
            IniciativaAutorDeputado, IniciativaParlamentar.id == IniciativaAutorDeputado.iniciativa_id
        ).join(
            Deputado, Deputado.id_cadastro == IniciativaAutorDeputado.id_cadastro
        ).filter(
            Deputado.id == deputado_id,
            IniciativaParlamentar.legislatura_id == legislatura_id
        ).first()
        
        total_initiatives = initiatives_query.total_initiatives or 0
        approved = initiatives_query.approved or 0
        last_initiative = initiatives_query.last_initiative
        
        # Calculate approval rate
        if total_initiatives > 0:
            approval_rate = Decimal(str((approved / total_initiatives) * 100))
        else:
            approval_rate = Decimal('0.0')
        
        # Calculate initiative score (0-100)
        # Quantity score (0-50) - logarithmic scale
        import math
        quantity_score = min(50, int(math.log(1 + total_initiatives) * 15))
        
        # Success rate score (0-35)
        success_score = int(float(approval_rate) * 0.35)
        
        # Collaboration score (0-15) - initiatives with multiple authors
        collaboration_query = session.query(
            func.count(func.distinct(IniciativaParlamentar.id)).label('collaborative')
        ).join(
            IniciativaAutorDeputado, IniciativaParlamentar.id == IniciativaAutorDeputado.iniciativa_id
        ).join(
            Deputado, Deputado.id_cadastro == IniciativaAutorDeputado.id_cadastro
        ).filter(
            Deputado.id == deputado_id,
            IniciativaParlamentar.legislatura_id == legislatura_id
        ).group_by(
            IniciativaParlamentar.id
        ).having(
            func.count(IniciativaAutorDeputado.id_cadastro) > 1
        ).subquery()
        
        collaborative_count = session.query(func.count()).select_from(collaboration_query).scalar() or 0
        
        if total_initiatives > 0:
            collaboration_score = min(15, int((collaborative_count / total_initiatives) * 15))
        else:
            collaboration_score = 0
        
        score = min(100, quantity_score + success_score + collaboration_score)
        
        return {
            'total_initiatives': total_initiatives,
            'approved': approved,
            'approval_rate': approval_rate,
            'score': score,
            'last_initiative': last_initiative
        }
    
    def _calculate_intervention_metrics(self, session, deputado_id: int, legislatura_id: int) -> Dict[str, Any]:
        """Calculate intervention metrics for a deputy."""
        # Get intervention statistics
        interventions_query = session.query(
            func.count(IntervencaoParlamentar.id).label('total_interventions'),
            func.sum(
                func.char_length(func.coalesce(IntervencaoParlamentar.sumario, '')) +
                func.char_length(func.coalesce(IntervencaoParlamentar.resumo, ''))
            ).label('total_words'),
            func.max(IntervencaoParlamentar.data_reuniao_plenaria).label('last_intervention')
        ).join(
            IntervencaoDeputado, IntervencaoParlamentar.id == IntervencaoDeputado.intervencao_id
        ).filter(
            IntervencaoDeputado.deputado_id == deputado_id,
            IntervencaoParlamentar.legislatura_id == legislatura_id
        ).first()
        
        total_interventions = interventions_query.total_interventions or 0
        total_words = interventions_query.total_words or 0
        last_intervention = interventions_query.last_intervention
        
        # Calculate intervention score (0-100)
        import math
        
        # Frequency score (0-60) - logarithmic scaling
        frequency_score = min(60, int(math.log(1 + total_interventions) * 18))
        
        # Substance score (0-40) - based on word count
        if total_words > 0:
            avg_words = total_words / max(1, total_interventions)
            substance_score = min(40, int(math.log(1 + avg_words) * 8))
        else:
            substance_score = 0
        
        score = min(100, frequency_score + substance_score)
        
        return {
            'total_interventions': total_interventions,
            'total_words': total_words,
            'score': score,
            'last_intervention': last_intervention
        }
    
    def _calculate_activity_score(self, attendance_data: Dict, initiative_data: Dict, intervention_data: Dict) -> int:
        """Calculate composite activity score (0-100)."""
        # Weighted composite calculation
        composite_score = (
            (attendance_data['score'] * 0.40) +
            (initiative_data['score'] * 0.30) +
            (intervention_data['score'] * 0.20) +
            (0 * 0.10)  # Engagement score placeholder
        )
        
        return min(100, max(0, int(round(composite_score))))
    
    def _calculate_attendance_analytics(self, deputies: List[Dict], legislatura_id: int, force_refresh: bool):
        """Calculate monthly attendance analytics."""
        self.logger.info(f"Calculating attendance analytics for {len(deputies)} deputies...")
        
        with self.Session() as session:
            for deputy in deputies:
                # Get all months with attendance data for this deputy
                months_query = session.query(
                    func.year(MeetingAttendance.dt_reuniao).label('year'),
                    func.month(MeetingAttendance.dt_reuniao).label('month')
                ).filter(
                    MeetingAttendance.dep_id == deputy['id']
                ).group_by(
                    func.year(MeetingAttendance.dt_reuniao),
                    func.month(MeetingAttendance.dt_reuniao)
                ).all()
                
                for year, month in months_query:
                    # Check if record exists
                    existing = session.query(AttendanceAnalytics).filter(
                        AttendanceAnalytics.deputado_id == deputy['id'],
                        AttendanceAnalytics.legislatura_id == legislatura_id,
                        AttendanceAnalytics.year == year,
                        AttendanceAnalytics.month == month
                    ).first()
                    
                    if existing and not force_refresh:
                        continue
                    
                    # Calculate monthly statistics
                    monthly_stats = session.query(
                        func.count(MeetingAttendance.id).label('scheduled'),
                        func.sum(case((MeetingAttendance.sigla_falta == 'PT', 1), else_=0)).label('attended'),
                        func.sum(case((MeetingAttendance.sigla_falta != 'PT', 1), else_=0)).label('absent')
                    ).filter(
                        MeetingAttendance.dep_id == deputy['id'],
                        func.year(MeetingAttendance.dt_reuniao) == year,
                        func.month(MeetingAttendance.dt_reuniao) == month
                    ).first()
                    
                    scheduled = monthly_stats.scheduled or 0
                    attended = monthly_stats.attended or 0
                    absent = monthly_stats.absent or 0
                    
                    # Calculate attendance rate
                    if scheduled > 0:
                        attendance_rate = Decimal(str((attended / scheduled) * 100))
                    else:
                        attendance_rate = Decimal('0.0')
                    
                    if existing:
                        # Update existing record
                        existing.sessions_scheduled = scheduled
                        existing.sessions_attended = attended
                        existing.sessions_absent = absent
                        existing.attendance_rate = attendance_rate
                        existing.updated_at = datetime.now()
                    else:
                        # Create new record
                        analytics = AttendanceAnalytics(
                            deputado_id=deputy['id'],
                            legislatura_id=legislatura_id,
                            year=year,
                            month=month,
                            sessions_scheduled=scheduled,
                            sessions_attended=attended,
                            sessions_absent=absent,
                            attendance_rate=attendance_rate
                        )
                        session.add(analytics)
            
            session.commit()
        
        self.logger.info("Completed attendance analytics calculation")
    
    def _calculate_initiative_analytics(self, deputies: List[Dict], legislatura_id: int, force_refresh: bool):
        """Calculate initiative analytics for all deputies."""
        self.logger.info(f"Calculating initiative analytics for {len(deputies)} deputies...")
        
        with self.Session() as session:
            for deputy in deputies:
                # Check if record exists
                existing = session.query(InitiativeAnalytics).filter(
                    InitiativeAnalytics.deputado_id == deputy['id'],
                    InitiativeAnalytics.legislatura_id == legislatura_id
                ).first()
                
                if existing and not force_refresh:
                    continue
                
                # Get comprehensive initiative statistics
                initiative_stats = session.query(
                    func.count(func.distinct(IniciativaParlamentar.id)).label('total_authored'),
                    func.count(IniciativaParlamentar.id).label('approved'),  # TODO: Add proper status tracking
                    func.count(IniciativaParlamentar.id).label('in_progress'),  # TODO: Add proper status tracking
                    func.count(IniciativaParlamentar.id).label('rejected'),  # TODO: Add proper status tracking
                    func.min(IniciativaParlamentar.data_inicio_leg).label('first_date'),
                    func.max(IniciativaParlamentar.data_fim_leg).label('latest_date')
                ).join(
                    IniciativaAutorDeputado, IniciativaParlamentar.id == IniciativaAutorDeputado.iniciativa_id
                ).join(
                    Deputado, Deputado.id_cadastro == IniciativaAutorDeputado.id_cadastro
                ).filter(
                    Deputado.id == deputy['id'],
                    IniciativaParlamentar.legislatura_id == legislatura_id
                ).first()
                
                total_authored = initiative_stats.total_authored or 0
                approved = initiative_stats.approved or 0
                in_progress = initiative_stats.in_progress or 0
                rejected = initiative_stats.rejected or 0
                first_date = initiative_stats.first_date
                latest_date = initiative_stats.latest_date
                
                # Calculate success rate
                if total_authored > 0:
                    success_rate = Decimal(str((approved / total_authored) * 100))
                else:
                    success_rate = Decimal('0.0')
                
                # Calculate collaborative initiatives
                collaborative_query = session.query(
                    func.count(func.distinct(IniciativaParlamentar.id)).label('collaborative')
                ).select_from(
                    session.query(IniciativaParlamentar.id).join(
                        IniciativaAutorDeputado, IniciativaParlamentar.id == IniciativaAutorDeputado.iniciativa_id
                    ).join(
                        Deputado, Deputado.id_cadastro == IniciativaAutorDeputado.id_cadastro
                    ).filter(
                        Deputado.id == deputy['id'],
                        IniciativaParlamentar.legislatura_id == legislatura_id
                    ).group_by(IniciativaParlamentar.id).having(
                        func.count(IniciativaAutorDeputado.id_cadastro) > 1
                    ).subquery()
                ).first()
                
                collaborative = collaborative_query.collaborative or 0
                
                # Calculate span days
                if first_date and latest_date:
                    span_days = (latest_date - first_date).days
                else:
                    span_days = 0
                
                if existing:
                    # Update existing record
                    existing.total_initiatives_authored = total_authored
                    existing.initiatives_approved = approved
                    existing.initiatives_in_progress = in_progress  
                    existing.initiatives_rejected = rejected
                    existing.success_rate = success_rate
                    existing.collaborative_initiatives = collaborative
                    existing.first_initiative_date = first_date
                    existing.latest_initiative_date = latest_date
                    existing.initiative_span_days = span_days
                    existing.updated_at = datetime.now()
                else:
                    # Create new record
                    analytics = InitiativeAnalytics(
                        deputado_id=deputy['id'],
                        legislatura_id=legislatura_id,
                        total_initiatives_authored=total_authored,
                        initiatives_approved=approved,
                        initiatives_in_progress=in_progress,
                        initiatives_rejected=rejected,
                        success_rate=success_rate,
                        collaborative_initiatives=collaborative,
                        first_initiative_date=first_date,
                        latest_initiative_date=latest_date,
                        initiative_span_days=span_days
                    )
                    session.add(analytics)
            
            session.commit()
        
        self.logger.info("Completed initiative analytics calculation")
    
    def _calculate_deputy_timelines(self, deputies: List[Dict], legislatura_id: int, force_refresh: bool):
        """Calculate deputy timeline/career progression data."""
        self.logger.info(f"Calculating deputy timelines for {len(deputies)} deputies...")
        
        with self.Session() as session:
            for deputy in deputies:
                # Check if record exists
                existing = session.query(DeputyTimeline).filter(
                    DeputyTimeline.id_cadastro == deputy['id_cadastro']
                ).first()
                
                if existing and not force_refresh:
                    continue
                
                # Get career statistics across all legislatures using id_cadastro
                career_stats = session.query(
                    func.count(func.distinct(Deputado.legislatura_id)).label('total_legislatures'),
                    func.min(Legislatura.data_inicio).label('first_election'),
                    func.max(Legislatura.data_fim).label('current_term_end')
                ).select_from(
                    Deputado
                ).join(
                    Legislatura, Deputado.legislatura_id == Legislatura.id
                ).filter(
                    Deputado.id_cadastro == deputy['id_cadastro']
                ).first()
                
                total_legislatures = career_stats.total_legislatures or 0
                first_election = career_stats.first_election
                current_term_end = career_stats.current_term_end
                
                # Calculate years of service
                if first_election and current_term_end:
                    years_of_service = (current_term_end - first_election).days // 365
                else:
                    years_of_service = 0
                
                # Determine experience category
                if years_of_service <= 2:
                    experience_category = 'junior'
                elif years_of_service <= 6:
                    experience_category = 'mid-career'
                elif years_of_service <= 12:
                    experience_category = 'senior'
                else:
                    experience_category = 'veteran'
                
                if existing:
                    # Update existing record
                    existing.first_election_date = first_election
                    existing.total_legislatures_served = total_legislatures
                    existing.years_of_service = years_of_service
                    existing.experience_category = experience_category
                    existing.updated_at = datetime.now()
                else:
                    # Create new record
                    timeline = DeputyTimeline(
                        id_cadastro=deputy['id_cadastro'],
                        first_election_date=first_election,
                        total_legislatures_served=total_legislatures,
                        years_of_service=years_of_service,
                        experience_category=experience_category
                    )
                    session.add(timeline)
            
            session.commit()
        
        self.logger.info("Completed deputy timeline calculation")
    
    def _calculate_data_quality_metrics(self, legislatura_id: int):
        """Calculate data quality metrics for the legislature."""
        self.logger.info(f"Calculating data quality metrics for Legislature {legislatura_id}...")
        
        tables_to_check = [
            ('deputados', Deputado),
            ('meeting_attendances', MeetingAttendance),
            ('iniciativas', IniciativaParlamentar),
            ('intervencoes', IntervencaoParlamentar)
        ]
        
        with self.Session() as session:
            for table_name, model_class in tables_to_check:
                # Check if record exists for today
                today = date.today()
                existing = session.query(DataQualityMetrics).filter(
                    DataQualityMetrics.table_name == table_name,
                    DataQualityMetrics.metric_date == today
                ).first()
                
                if existing:
                    continue  # Skip if already calculated today
                
                # Count total records
                if hasattr(model_class, 'legislatura_id'):
                    total_records = session.query(func.count(model_class.id)).filter(
                        model_class.legislatura_id == legislatura_id
                    ).scalar() or 0
                else:
                    total_records = session.query(func.count(model_class.id)).scalar() or 0
                
                # For simplicity, assume 95% completeness (could be enhanced)
                complete_records = int(total_records * 0.95)
                incomplete_records = total_records - complete_records
                completeness_percentage = Decimal('95.0') if total_records > 0 else Decimal('0.0')
                
                # Create quality metrics record
                quality_metrics = DataQualityMetrics(
                    table_name=table_name,
                    metric_date=today,
                    total_records=total_records,
                    complete_records=complete_records,
                    incomplete_records=incomplete_records,
                    completeness_percentage=completeness_percentage,
                    quality_trend='stable'
                )
                session.add(quality_metrics)
            
            session.commit()
        
        self.logger.info("Completed data quality metrics calculation")


def main():
    """Main entry point for the analytics calculator."""
    parser = argparse.ArgumentParser(
        description='Calculate Portuguese Parliament Analytics',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--legislature', '-l',
        type=int,
        help='Specific legislature ID to process (e.g., 15 for XV Legislature)'
    )
    
    parser.add_argument(
        '--force-refresh', '-f',
        action='store_true',
        help='Force recalculation of all analytics data'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show verbose output with detailed progress'
    )
    
    args = parser.parse_args()
    
    try:
        # Get database connection
        engine = get_engine()
        
        # Create calculator instance
        calculator = AnalyticsCalculator(engine, verbose=args.verbose)
        
        # Run calculations
        calculator.calculate_all_analytics(
            legislatura_id=args.legislature,
            force_refresh=args.force_refresh
        )
        
        print("Analytics calculation completed successfully!")
        
    except Exception as e:
        print(f"Error during analytics calculation: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()