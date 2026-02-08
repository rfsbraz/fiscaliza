#!/usr/bin/env python3
"""
Test single file processing
"""

from file_processor import ParliamentFileProcessor

def test_single_file():
    processor = ParliamentFileProcessor()
    
    # Test with a simple file from the Agenda Parlamentar
    test_file = {
        'url': 'https://app.parlamento.pt/webutils/docs/doc.txt?path=6148523063484d364c793968636d356c6443395953556c4qmFuZUdoYjJOcWFHU09ib1AvNmX4fSTh3Z2%3d',
        'text': 'AgendaParlamentar_json.txt',
        'type': 'JSON',
        'category': 'Agenda Parlamentar',
        'legislatura': 'XVII'
    }
    
    success = processor.process_single_file(test_file)
    print(f"\nProcessing result: {'Success' if success else 'Failed'}")
    
    # Show status
    summary = processor.get_import_status_summary()
    print("\nImport Status Summary:")
    for status, count in summary.items():
        print(f"  {status}: {count}")

if __name__ == "__main__":
    test_single_file()