"""
Example: Using Thematic Parliament Field Translators
===================================================

This example demonstrates how to use the reorganized thematic field translators
with database models at the application level.
"""

import sys
import os

# Add project root to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from database.translators.deputy_activities import deputy_activity_translator
from database.translators.publications import publication_translator
from database.translators.initiatives import initiative_translator
from database.translators.parliamentary_interventions import intervention_translator


def demo_thematic_organization():
    """Demonstrate thematic translator organization"""
    print("=== Thematic Translator Organization ===")
    
    # Deputy activities - committee work, parliamentary activities
    print("Deputy Activities:")
    print(f"  Activity AUD: {deputy_activity_translator.activity_type('AUD')}")
    print(f"  Request AR: {deputy_activity_translator.request_type('AR')}")
    print(f"  Status efetivo: {deputy_activity_translator.committee_status('efetivo')}")
    
    # Publications - shared across multiple areas
    print("\nPublications:")
    print(f"  Publication A: {publication_translator.publication_type('A')}")
    print(f"  Publication D: {publication_translator.publication_type('D')}")
    
    # Initiatives - parliamentary proposals and laws
    print("\nInitiatives:")
    print(f"  Initiative J: {initiative_translator.initiative_type('J')}")
    print(f"  Initiative C: {initiative_translator.initiative_type('C')}")
    
    # Interventions - parliamentary debates and speeches
    print("\nParliamentary Interventions:")
    print(f"  Publication A: {intervention_translator.publication_type('A')}")
    print(f"  Intervention DEBATE: {intervention_translator.intervention_type('DEBATE')}")


def demo_model_specific_usage():
    """Demonstrate usage patterns for specific model types"""
    print("\n=== Model-Specific Translation Patterns ===")
    
    # Simulate different model data
    class MockIntervention:
        def __init__(self, pub_tp, tin_ds, sumario):
            self.pub_tp = pub_tp
            self.tin_ds = tin_ds  
            self.sumario = sumario
    
    class MockActivity:
        def __init__(self, act_tp, cms_situacao, act_as):
            self.act_tp = act_tp
            self.cms_situacao = cms_situacao
            self.act_as = act_as
    
    class MockInitiative:
        def __init__(self, ini_tp, ini_ti):
            self.ini_tp = ini_tp
            self.ini_ti = ini_ti
    
    # Parliamentary intervention example
    intervention = MockIntervention("A", "DEBATE", "Discussão sobre orçamento")
    print("Parliamentary Intervention:")
    print(f"  Publication: {intervention_translator.publication_type(intervention.pub_tp)}")
    print(f"  Type: {intervention_translator.intervention_type(intervention.tin_ds)}")
    print(f"  Summary: {intervention.sumario}")
    
    # Committee activity example
    activity = MockActivity("AUD", "efetivo", "Audiência sobre política energética")
    print("\nCommittee Activity:")
    print(f"  Activity: {deputy_activity_translator.activity_type(activity.act_tp)}")
    print(f"  Status: {deputy_activity_translator.committee_status(activity.cms_situacao)}")
    print(f"  Subject: {activity.act_as}")
    
    # Legislative initiative example  
    initiative = MockInitiative("J", "Lei sobre transparência")
    print("\nLegislative Initiative:")
    print(f"  Type: {initiative_translator.initiative_type(initiative.ini_tp)}")
    print(f"  Title: {initiative.ini_ti}")


def demo_api_response_formatting():
    """Demonstrate API response formatting with thematic translators"""
    print("\n=== API Response Formatting ===")
    
    # Simulate complex record with multiple coded fields
    raw_record = {
        "intervention_id": 123,
        "pub_tp": "A",           # Publication type
        "tin_ds": "DEBATE",      # Intervention type
        "act_tp": "AUD",         # Activity type
        "ini_tp": "J",           # Initiative type
        "cms_situacao": "efetivo", # Committee status
        "subject": "Discussão sobre orçamento de Estado"
    }
    
    # Transform for API with appropriate thematic translators
    api_response = {
        "id": raw_record["intervention_id"],
        "subject": raw_record["subject"],
        "publication": {
            "code": raw_record["pub_tp"],
            "description": intervention_translator.publication_type(raw_record["pub_tp"])
        },
        "intervention": {
            "code": raw_record["tin_ds"],
            "description": intervention_translator.intervention_type(raw_record["tin_ds"])
        },
        "activity": {
            "code": raw_record["act_tp"],
            "description": deputy_activity_translator.activity_type(raw_record["act_tp"])
        },
        "initiative": {
            "code": raw_record["ini_tp"],
            "description": initiative_translator.initiative_type(raw_record["ini_tp"])
        },
        "committee_status": {
            "code": raw_record["cms_situacao"],
            "description": deputy_activity_translator.committee_status(raw_record["cms_situacao"])
        }
    }
    
    print("Formatted API Response:")
    for key, value in api_response.items():
        if isinstance(value, dict) and 'code' in value:
            print(f"  {key}: {value['code']} - {value['description']}")
        else:
            print(f"  {key}: {value}")


def demo_validation_and_metadata():
    """Demonstrate validation capabilities with metadata"""
    print("\n=== Validation and Metadata ===")
    
    # Test various codes for validation
    test_cases = [
        ("Publication", "A", publication_translator.get_publication_type),
        ("Publication", "INVALID", publication_translator.get_publication_type),
        ("Activity", "AUD", deputy_activity_translator.get_activity_type),
        ("Activity", "FAKE", deputy_activity_translator.get_activity_type),
        ("Initiative", "J", initiative_translator.get_initiative_type),
        ("Initiative", "WRONG", initiative_translator.get_initiative_type)
    ]
    
    print("Validation Results:")
    for category, code, translator_method in test_cases:
        translation = translator_method(code)
        if translation:
            status = "✓ Valid" if translation.is_valid else "✗ Invalid"
            print(f"  {category} '{code}': {status} - {translation.description}")
        else:
            print(f"  {category} '{code}': ✗ No translation")


def demo_cross_translator_sharing():
    """Demonstrate how publication types are shared across translators"""
    print("\n=== Cross-Translator Sharing ===")
    
    # Publication type "A" should be consistent across all translators that use it
    pub_direct = publication_translator.publication_type("A")
    pub_via_intervention = intervention_translator.publication_type("A")
    
    print("Publication Type Consistency:")
    print(f"  Direct: {pub_direct}")
    print(f"  Via Intervention: {pub_via_intervention}")
    print(f"  Consistent: {'✓' if pub_direct == pub_via_intervention else '✗'}")


if __name__ == "__main__":
    demo_thematic_organization()
    demo_model_specific_usage()
    demo_api_response_formatting()
    demo_validation_and_metadata()
    demo_cross_translator_sharing()