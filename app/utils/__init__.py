"""
Utility modules for the Parliament application
"""

from .deputy_linking import (
    get_deputy_unique_key,
    group_deputies_by_person,
    get_most_recent_mandate,
    enhance_deputy_with_career_info
)

__all__ = [
    'get_deputy_unique_key',
    'group_deputies_by_person', 
    'get_most_recent_mandate',
    'enhance_deputy_with_career_info'
]