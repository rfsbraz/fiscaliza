"""
Example: Using Parliament Field Translators
==========================================

This example demonstrates how to use the field translators with database models
at the application level, separate from data processing concerns.
"""

import sys
import os

# Add project root to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from database.field_translators import (
    ParliamentFieldTranslator,
    translate_publication_type,
    translate_activity_type,
    translate_initiative_type
)


def demo_basic_translation():
    """Demonstrate basic field translation"""
    print("=== Basic Field Translation ===")
    
    # Using convenience functions
    print(f"Publication A: {translate_publication_type('A')}")
    print(f"Activity AUD: {translate_activity_type('AUD')}")  
    print(f"Initiative J: {translate_initiative_type('J')}")
    print(f"Invalid code: {translate_activity_type('INVALID')}")


def demo_advanced_translation():
    """Demonstrate advanced translation with metadata"""
    print("\n=== Advanced Translation with Metadata ===")
    
    translator = ParliamentFieldTranslator()
    
    # Get full translation metadata
    translation = translator.get_publication_type("A")
    print(f"Translation: {translation}")
    print(f"Code: {translation.code}")
    print(f"Description: {translation.description}")
    print(f"Category: {translation.category}")
    print(f"Is valid: {translation.is_valid}")
    
    # Handle invalid codes gracefully
    invalid = translator.get_activity_type("INVALID")
    print(f"\nInvalid translation: {invalid}")
    print(f"Is valid: {invalid.is_valid}")


def demo_model_integration():
    """Demonstrate how translators would work with database models"""
    print("\n=== Model Integration Examples ===")
    
    translator = ParliamentFieldTranslator()
    
    # Simulate database model data
    class MockIntervention:
        def __init__(self, pub_tp, tin_ds):
            self.pub_tp = pub_tp
            self.tin_ds = tin_ds
    
    class MockActivity:
        def __init__(self, act_tp, act_as):
            self.act_tp = act_tp
            self.act_as = act_as
    
    # Example interventions
    intervention1 = MockIntervention("A", "Debate")
    intervention2 = MockIntervention("AUD", "Committee Hearing")
    
    print("Parliamentary Interventions:")
    print(f"- {translator.publication_type(intervention1.pub_tp)} - {intervention1.tin_ds}")
    print(f"- {translator.publication_type(intervention2.pub_tp)} - {intervention2.tin_ds}")
    
    # Example activities
    activity1 = MockActivity("AUD", "Audiência sobre orçamento")
    activity2 = MockActivity("DES", "Deslocação a Bruxelas")
    
    print("\nParliamentary Activities:")
    print(f"- {translator.activity_type(activity1.act_tp)}: {activity1.act_as}")
    print(f"- {translator.activity_type(activity2.act_tp)}: {activity2.act_as}")


def demo_api_response_formatting():
    """Demonstrate formatting for API responses"""
    print("\n=== API Response Formatting ===")
    
    translator = ParliamentFieldTranslator()
    
    # Simulate API data transformation
    raw_data = {
        "id": 123,
        "pub_tp": "A",
        "act_tp": "AUD", 
        "ini_tp": "J",
        "subject": "Discussão do Orçamento de Estado"
    }
    
    # Transform for API response
    api_response = {
        "id": raw_data["id"],
        "subject": raw_data["subject"],
        "publication_type": {
            "code": raw_data["pub_tp"],
            "description": translator.publication_type(raw_data["pub_tp"])
        },
        "activity_type": {
            "code": raw_data["act_tp"], 
            "description": translator.activity_type(raw_data["act_tp"])
        },
        "initiative_type": {
            "code": raw_data["ini_tp"],
            "description": translator.initiative_type(raw_data["ini_tp"])
        }
    }
    
    print("API Response:")
    for key, value in api_response.items():
        if isinstance(value, dict):
            print(f"  {key}: {value['code']} - {value['description']}")
        else:
            print(f"  {key}: {value}")


def demo_validation_workflow():
    """Demonstrate validation of field codes"""
    print("\n=== Field Code Validation ===")
    
    translator = ParliamentFieldTranslator()
    
    test_codes = ["A", "AUD", "INVALID", "J", "NONEXISTENT"]
    
    print("Validation results:")
    for code in test_codes:
        pub_translation = translator.get_publication_type(code)
        act_translation = translator.get_activity_type(code)
        
        if pub_translation and pub_translation.is_valid:
            print(f"  {code}: Valid publication type - {pub_translation.description}")
        elif act_translation and act_translation.is_valid:
            print(f"  {code}: Valid activity type - {act_translation.description}")
        else:
            print(f"  {code}: Invalid code")


if __name__ == "__main__":
    demo_basic_translation()
    demo_advanced_translation()
    demo_model_integration()
    demo_api_response_formatting()
    demo_validation_workflow()