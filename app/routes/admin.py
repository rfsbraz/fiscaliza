"""
Admin API routes for internal monitoring and data import status.
These endpoints are designed to be accessed only from localhost.
"""
from flask import Blueprint, jsonify, request
import os
import sys
import logging
from datetime import datetime, timedelta

# Set up logging
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from database.connection import get_session
from database.models import ImportStatus
from sqlalchemy import func, desc, case

admin_bp = Blueprint('admin', __name__)


def is_localhost():
    """Check if request is from localhost"""
    remote_addr = request.remote_addr
    # Accept localhost, 127.0.0.1, and ::1 (IPv6 localhost)
    return remote_addr in ('localhost', '127.0.0.1', '::1', None)


@admin_bp.before_request
def check_localhost():
    """Restrict all admin routes to localhost only"""
    if not is_localhost():
        return jsonify({
            'error': 'Forbidden',
            'message': 'Admin endpoints are only accessible from localhost'
        }), 403


@admin_bp.route('/admin/import-status', methods=['GET'])
def get_import_status():
    """
    Get comprehensive import status data for the admin dashboard.

    Query params:
    - category: Filter by category
    - status: Filter by status
    - legislatura: Filter by legislatura
    - limit: Number of records (default 100)
    - offset: Pagination offset
    - sort: Sort field (default: updated_at)
    - order: Sort order (asc/desc, default: desc)
    """
    try:
        session = get_session()

        # Get query parameters
        category = request.args.get('category')
        status_filter = request.args.get('status')
        legislatura = request.args.get('legislatura')
        limit = min(int(request.args.get('limit', 100)), 500)
        offset = int(request.args.get('offset', 0))
        sort_field = request.args.get('sort', 'updated_at')
        sort_order = request.args.get('order', 'desc')

        # Build query
        query = session.query(ImportStatus)

        if category:
            query = query.filter(ImportStatus.category == category)
        if status_filter:
            query = query.filter(ImportStatus.status == status_filter)
        if legislatura:
            query = query.filter(ImportStatus.legislatura == legislatura)

        # Get total count before pagination
        total_count = query.count()

        # Apply sorting
        sort_column = getattr(ImportStatus, sort_field, ImportStatus.updated_at)
        if sort_order == 'asc':
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # Apply pagination
        records = query.offset(offset).limit(limit).all()

        # Format records
        formatted_records = []
        for r in records:
            formatted_records.append({
                'id': str(r.id),
                'file_name': r.file_name,
                'file_url': r.file_url,
                'file_type': r.file_type,
                'category': r.category,
                'legislatura': r.legislatura,
                'status': r.status,
                'error_message': r.error_message,
                'schema_issues': r.schema_issues,
                'records_imported': r.records_imported,
                'file_size': r.file_size,
                'processing_duration_seconds': r.processing_duration_seconds,
                'processing_started_at': r.processing_started_at.isoformat() if r.processing_started_at else None,
                'processing_completed_at': r.processing_completed_at.isoformat() if r.processing_completed_at else None,
                'error_count': r.error_count,
                'recrawl_count': r.recrawl_count,
                'retry_at': r.retry_at.isoformat() if r.retry_at else None,
                'created_at': r.created_at.isoformat() if r.created_at else None,
                'updated_at': r.updated_at.isoformat() if r.updated_at else None,
            })

        session.close()

        return jsonify({
            'records': formatted_records,
            'total': total_count,
            'limit': limit,
            'offset': offset
        })

    except Exception as e:
        logger.error(f"Error fetching import status: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/import-stats', methods=['GET'])
def get_import_stats():
    """
    Get aggregated statistics about import status.
    """
    try:
        session = get_session()

        # Overall status counts
        status_counts = session.query(
            ImportStatus.status,
            func.count(ImportStatus.id).label('count')
        ).group_by(ImportStatus.status).all()

        # Category counts
        category_counts = session.query(
            ImportStatus.category,
            func.count(ImportStatus.id).label('count')
        ).group_by(ImportStatus.category).all()

        # Recent activity (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(hours=24)
        recent_completed = session.query(func.count(ImportStatus.id)).filter(
            ImportStatus.status == 'completed',
            ImportStatus.processing_completed_at >= yesterday
        ).scalar()

        recent_failed = session.query(func.count(ImportStatus.id)).filter(
            ImportStatus.status.in_(['failed', 'import_error']),
            ImportStatus.updated_at >= yesterday
        ).scalar()

        # Total records imported
        total_imported = session.query(
            func.sum(ImportStatus.records_imported)
        ).scalar() or 0

        # Average processing time
        avg_duration = session.query(
            func.avg(ImportStatus.processing_duration_seconds)
        ).filter(
            ImportStatus.processing_duration_seconds.isnot(None),
            ImportStatus.status == 'completed'
        ).scalar() or 0

        # Files by legislatura
        legislatura_counts = session.query(
            ImportStatus.legislatura,
            func.count(ImportStatus.id).label('count')
        ).group_by(ImportStatus.legislatura).order_by(
            ImportStatus.legislatura.desc()
        ).all()

        # Error breakdown
        error_types = session.query(
            ImportStatus.status,
            func.count(ImportStatus.id).label('count')
        ).filter(
            ImportStatus.status.in_(['failed', 'import_error', 'schema_mismatch'])
        ).group_by(ImportStatus.status).all()

        # Processing status (active work)
        processing_count = session.query(func.count(ImportStatus.id)).filter(
            ImportStatus.status.in_(['downloading', 'processing'])
        ).scalar()

        pending_count = session.query(func.count(ImportStatus.id)).filter(
            ImportStatus.status.in_(['pending', 'download_pending', 'discovered'])
        ).scalar()

        session.close()

        return jsonify({
            'status_counts': {s: c for s, c in status_counts},
            'category_counts': {c: n for c, n in category_counts},
            'legislatura_counts': {l: c for l, c in legislatura_counts if l},
            'error_types': {e: c for e, c in error_types},
            'recent_24h': {
                'completed': recent_completed,
                'failed': recent_failed
            },
            'totals': {
                'records_imported': total_imported,
                'avg_processing_seconds': round(float(avg_duration), 2),
                'currently_processing': processing_count,
                'pending': pending_count
            }
        })

    except Exception as e:
        logger.error(f"Error fetching import stats: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/recent-errors', methods=['GET'])
def get_recent_errors():
    """Get recent errors with full details for debugging."""
    try:
        session = get_session()
        limit = min(int(request.args.get('limit', 20)), 100)

        errors = session.query(ImportStatus).filter(
            ImportStatus.status.in_(['failed', 'import_error', 'schema_mismatch'])
        ).order_by(
            desc(ImportStatus.updated_at)
        ).limit(limit).all()

        formatted_errors = []
        for e in errors:
            formatted_errors.append({
                'id': str(e.id),
                'file_name': e.file_name,
                'category': e.category,
                'legislatura': e.legislatura,
                'status': e.status,
                'error_message': e.error_message,
                'schema_issues': e.schema_issues,
                'error_count': e.error_count,
                'retry_at': e.retry_at.isoformat() if e.retry_at else None,
                'updated_at': e.updated_at.isoformat() if e.updated_at else None,
            })

        session.close()
        return jsonify({'errors': formatted_errors})

    except Exception as e:
        logger.error(f"Error fetching recent errors: {e}")
        return jsonify({'error': str(e)}), 500
