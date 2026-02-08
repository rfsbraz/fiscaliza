#!/usr/bin/env python3
"""
Generate complete expected fields list for iniciativas mapper
"""

import xml.etree.ElementTree as ET
import os
from typing import Set

def extract_all_xml_paths(element: ET.Element, current_path: str = "") -> Set[str]:
    """
    Recursively extract all XML element paths from the document.
    """
    paths = set()
    
    # Add current element path
    if current_path:
        paths.add(current_path)
    else:
        paths.add(element.tag)
        current_path = element.tag
    
    # Process child elements
    for child in element:
        child_path = f"{current_path}.{child.tag}"
        paths.update(extract_all_xml_paths(child, child_path))
        
    return paths

def generate_expected_fields():
    """Generate expected fields from sample XML files"""
    
    data_dir = r"E:\dev\parliament\data\downloads\Iniciativas"
    all_paths = set()
    
    # Find all XML files
    for root, dirs, files in os.walk(data_dir):
        for file in files:
            if file.endswith('.xml'):
                xml_path = os.path.join(root, file)
                print(f"Processing: {xml_path}")
                
                try:
                    tree = ET.parse(xml_path)
                    xml_root = tree.getroot()
                    paths = extract_all_xml_paths(xml_root)
                    all_paths.update(paths)
                    print(f"  Found {len(paths)} paths")
                except Exception as e:
                    print(f"  Error: {e}")
                    continue
                    
                # Only process a few files to get comprehensive coverage
                if len(all_paths) > 300:
                    break
        if len(all_paths) > 300:
            break
    
    print(f"\nTotal unique paths found: {len(all_paths)}")
    
    # Generate Python set code
    print("\n# Generated expected fields set:")
    print("return {")
    for path in sorted(all_paths):
        print(f"    '{path}',")
    print("}")

if __name__ == "__main__":
    generate_expected_fields()