"""
Database Mixins for Parliament Data Models
==========================================

Provides reusable mixins for cross-cutting concerns like import source tracking.

Usage:
    # Apply to individual model classes
    class MyModel(Base, ImportTrackingMixin):
        pass

    # Or apply to all models at once
    from database.mixins import apply_import_tracking_to_all_models
    apply_import_tracking_to_all_models(Base)
"""

from sqlalchemy import Column, ForeignKey, Index
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship

from database.types import GUID


class ImportTrackingMixin:
    """
    Mixin to add import source tracking to any model.

    Adds:
        - import_status_id: FK to ImportStatus table
        - import_status: Relationship to ImportStatus model

    This enables data provenance tracking - knowing which import file
    created each record in the database.
    """

    @declared_attr
    def import_status_id(cls):
        return Column(
            GUID(),
            ForeignKey("import_status.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
            comment="Reference to import batch that created/updated this record"
        )

    @declared_attr
    def import_status(cls):
        # Avoid circular imports by using string reference
        return relationship(
            "ImportStatus",
            foreign_keys=[cls.import_status_id],
            lazy="select"
        )


def apply_import_tracking_to_all_models(base_class, exclude_tables=None):
    """
    Dynamically add import_status_id column to all models inheriting from Base.

    This function modifies model classes in-place to add the import_status_id
    column. Must be called AFTER all models are defined but BEFORE the
    database tables are created or queries are run.

    Args:
        base_class: The SQLAlchemy declarative Base class
        exclude_tables: Set of table names to exclude (e.g., {'import_status'})

    Example:
        from database.models import Base
        from database.mixins import apply_import_tracking_to_all_models
        apply_import_tracking_to_all_models(Base, exclude_tables={'import_status'})
    """
    if exclude_tables is None:
        exclude_tables = {'import_status', 'alembic_version'}

    # Get all model classes
    for mapper in base_class.registry.mappers:
        model_class = mapper.class_
        table_name = getattr(model_class, '__tablename__', None)

        if table_name and table_name not in exclude_tables:
            # Check if column already exists
            if not hasattr(model_class, 'import_status_id'):
                # Add the column definition to the class
                model_class.import_status_id = Column(
                    GUID(),
                    ForeignKey("import_status.id", ondelete="SET NULL"),
                    nullable=True,
                    index=True,
                    comment="Reference to import batch that created/updated this record"
                )


def get_models_needing_import_tracking(base_class, exclude_tables=None):
    """
    Get list of model classes that should have import_status_id tracking.

    Useful for migration scripts to know which tables need the column added.

    Args:
        base_class: The SQLAlchemy declarative Base class
        exclude_tables: Set of table names to exclude

    Returns:
        List of (table_name, model_class) tuples
    """
    if exclude_tables is None:
        exclude_tables = {'import_status', 'alembic_version'}

    models = []
    for mapper in base_class.registry.mappers:
        model_class = mapper.class_
        table_name = getattr(model_class, '__tablename__', None)

        if table_name and table_name not in exclude_tables:
            models.append((table_name, model_class))

    return sorted(models, key=lambda x: x[0])
