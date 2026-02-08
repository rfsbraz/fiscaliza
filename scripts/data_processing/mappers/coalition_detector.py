"""
Coalition Detection System for Portuguese Parliamentary Data
==========================================================

Automatically detects coalitions (coligações) vs individual parties in Portuguese 
parliamentary data based on naming patterns and political knowledge.

Based on Portuguese political analysis:
- Coalitions use separators: "/" (main), "." (secondary), "-" (within party names)
- Known historical coalitions and their component parties
- Confidence scoring for automatic detection accuracy
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CoalitionDetection:
    """Results of coalition detection analysis"""
    is_coalition: bool
    confidence: float
    coalition_sigla: str
    coalition_name: Optional[str]
    component_parties: List[Dict[str, str]]
    detection_method: str
    political_spectrum: Optional[str] = None
    formation_date: Optional[datetime] = None


class CoalitionDetector:
    """
    Portuguese Parliamentary Coalition Detection System
    
    Detects and analyzes coalitions based on:
    1. Naming pattern recognition (/, ., -)
    2. Known coalition database
    3. Political context and historical data
    """
    
    def __init__(self):
        self.known_coalitions = self._initialize_known_coalitions()
        self.pattern_rules = self._initialize_pattern_rules()
        
    def _initialize_known_coalitions(self) -> Dict[str, Dict]:
        """Initialize database of known Portuguese coalitions with metadata
        Based on comprehensive political analysis from 1910-2024"""
        return {
            # Modern Democratic Period - Current and Recent Coalitions (1974-present)
            "PPD/PSD.CDS-PP": {
                "name": "Aliança Democrática",
                "electoral_name": "Aliança Democrática", 
                "components": [
                    {"sigla": "PPD", "nome": "Partido Popular Democrático"},
                    {"sigla": "PSD", "nome": "Partido Social Democrata"}, 
                    {"sigla": "CDS-PP", "nome": "Centro Democrático Social - Partido Popular"}
                ],
                "spectrum": "centro-direita",
                "formation_date": "1979-12-02",
                "dissolution_date": "1983-01-01",
                "type": "eleitoral",
                "historical_significance": "Major center-right coalition, won 1979 and 1980 elections"
            },
            "PPD/PSD.CDS-PP.PPM": {
                "name": "Aliança Democrática (com PPM)",
                "electoral_name": "Aliança Democrática",
                "components": [
                    {"sigla": "PPD", "nome": "Partido Popular Democrático"},
                    {"sigla": "PSD", "nome": "Partido Social Democrata"},
                    {"sigla": "CDS-PP", "nome": "Centro Democrático Social - Partido Popular"},
                    {"sigla": "PPM", "nome": "Partido Popular Monárquico"}
                ],
                "spectrum": "centro-direita", 
                "formation_date": "1979-12-02",
                "dissolution_date": "1983-01-01",
                "type": "eleitoral",
                "historical_significance": "Extended Aliança Democrática with monarchist party"
            },
            "AD": {
                "name": "Aliança Democrática",
                "electoral_name": "Aliança Democrática",
                "components": [
                    {"sigla": "PSD", "nome": "Partido Social Democrata"},
                    {"sigla": "CDS-PP", "nome": "Centro Democrático Social - Partido Popular"}
                ],
                "spectrum": "centro-direita",
                "formation_date": "1979-12-02",
                "dissolution_date": "1983-01-01",
                "revival_date": "2024-01-01",
                "type": "eleitoral",
                "historical_significance": "Revived for 2024 European elections, successful return"
            },
            "PAF": {
                "name": "Portugal à Frente", 
                "electoral_name": "Portugal à Frente",
                "components": [
                    {"sigla": "PSD", "nome": "Partido Social Democrata"},
                    {"sigla": "CDS-PP", "nome": "Centro Democrático Social - Partido Popular"}
                ],
                "spectrum": "centro-direita",
                "formation_date": "2015-01-01",
                "dissolution_date": "2015-12-31",
                "type": "eleitoral",
                "historical_significance": "Alternative name for AD revival, won 2015 elections"
            },
            
            # Left Coalitions - Historical Evolution
            "CDU": {
                "name": "Coligação Democrática Unitária",
                "electoral_name": "CDU",
                "components": [
                    {"sigla": "PCP", "nome": "Partido Comunista Português"},
                    {"sigla": "PEV", "nome": "Partido Ecologista Os Verdes"}
                ],
                "spectrum": "esquerda",
                "formation_date": "1987-01-01",
                "type": "eleitoral",
                "historical_significance": "Longest-standing coalition in Portugal, succeeded APU"
            },
            "APU": {
                "name": "Aliança do Povo Unido",
                "electoral_name": "APU",
                "components": [
                    {"sigla": "PCP", "nome": "Partido Comunista Português"},
                    {"sigla": "MDP", "nome": "Movimento Democrático Português"}
                ],
                "spectrum": "esquerda",
                "formation_date": "1976-01-01",
                "dissolution_date": "1987-01-01",
                "type": "eleitoral",
                "historical_significance": "Important left coalition during democratic consolidation, 14-19% electoral support"
            },
            
            # Democratic Transition Coalitions
            "MDP/CDE": {
                "name": "Movimento Democrático Português/Comissão Democrática Eleitoral",
                "electoral_name": "MDP/CDE", 
                "components": [
                    {"sigla": "MDP", "nome": "Movimento Democrático Português"},
                    {"sigla": "CDE", "nome": "Comissão Democrática Eleitoral"}
                ],
                "spectrum": "centro-esquerda",
                "formation_date": "1973-01-01",
                "dissolution_date": "1987-01-01",
                "type": "historica",
                "historical_significance": "Crucial in democratic transition, formed before 1974 revolution"
            },
            
            # Party Transitions (NOT true coalitions)
            "PPD/PSD": {
                "name": "Partido Social Democrata (transição)",
                "electoral_name": "PSD",
                "components": [
                    {"sigla": "PPD", "nome": "Partido Popular Democrático"},
                    {"sigla": "PSD", "nome": "Partido Social Democrata"}
                ],
                "spectrum": "centro-direita",
                "formation_date": "1974-05-06", 
                "type": "transicao",  # Party name transition, not true coalition
                "historical_significance": "Party name change from PPD to PSD, not a coalition"
            },
            
            # Special Cases - Parties formed from coalitions
            "BE": {
                "name": "Bloco de Esquerda",
                "electoral_name": "Bloco de Esquerda",
                "components": [
                    {"sigla": "PSR", "nome": "Partido Socialista Revolucionário"},
                    {"sigla": "UDP", "nome": "União Democrática Popular"},
                    {"sigla": "POL-XXI", "nome": "Política XXI"}
                ],
                "spectrum": "esquerda", 
                "formation_date": "1999-02-07",
                "type": "fusao",
                "historical_significance": "Formed from fusion of three parties, now unified party"
            },
            
            # Regional Coalitions
            "PSD-M": {
                "name": "Partido Social Democrata - Madeira",
                "electoral_name": "PSD-Madeira",
                "components": [
                    {"sigla": "PSD", "nome": "Partido Social Democrata"},
                    {"sigla": "LOCAL-M", "nome": "Partidos Locais Madeirenses"}
                ],
                "spectrum": "centro-direita",
                "formation_date": "1976-01-01",
                "type": "regional",
                "historical_significance": "Regional autonomist alliance in Madeira"
            }
        }
    
    def _initialize_pattern_rules(self) -> List[Dict]:
        """Initialize enhanced coalition detection patterns based on Portuguese political analysis"""
        return [
            {
                "pattern": r"^[A-Z]+/[A-Z]+(\.[A-Z\-]+)*$",
                "description": "Primary Portuguese coalition pattern: slash-separated with optional dot extensions",
                "confidence": 0.95,
                "examples": ["PPD/PSD", "PPD/PSD.CDS-PP", "MDP/CDE", "PPD/PSD.CDS-PP.PPM"],
                "political_context": "Main coalition format used in Portuguese elections"
            },
            {
                "pattern": r"^[A-Z]{2,}\.[A-Z\-]{2,}$", 
                "description": "Secondary coalition pattern: dot-separated parties",
                "confidence": 0.8,
                "examples": ["PSD.CDS-PP"],
                "political_context": "Alternative coalition notation"
            },
            {
                "pattern": r"^(AD|CDU|APU|PAF)$",
                "description": "Verified Portuguese coalition acronyms - major historical coalitions",
                "confidence": 0.98,
                "examples": ["AD", "CDU", "APU", "PAF"],
                "political_context": "Established coalition brands with electoral significance"
            },
            {
                "pattern": r"^[A-Z]{2,4}/[A-Z]{2,4}$",
                "description": "Simple two-party coalition pattern",
                "confidence": 0.9,
                "examples": ["MDP/CDE", "PPD/PSD"],
                "political_context": "Basic bilateral coalition format"
            },
            {
                "pattern": r"^[A-Z]+-[A-Z]+\.[A-Z]+-[A-Z]+$",
                "description": "Hyphenated parties in coalition",
                "confidence": 0.85,
                "examples": ["CDS-PP.PSD-Regional"],
                "political_context": "Coalitions involving parties with compound names"
            },
            {
                "pattern": r"^[A-Z]{2,}\-M$",
                "description": "Regional Madeira coalition pattern",
                "confidence": 0.9,
                "examples": ["PSD-M"],
                "political_context": "Madeira regional autonomist coalitions"
            }
        ]
    
    def detect(self, sigla: str, context: Optional[Dict] = None) -> CoalitionDetection:
        """
        Main detection method - analyzes party sigla for coalition patterns
        
        Args:
            sigla: Party/coalition abbreviation to analyze
            context: Optional context (legislature, date, etc.)
            
        Returns:
            CoalitionDetection with analysis results
        """
        if not sigla or not sigla.strip():
            return self._create_negative_detection(sigla, "empty_sigla")
        
        sigla = sigla.strip().upper()
        
        # Step 1: Check known coalitions database (highest confidence)
        if sigla in self.known_coalitions:
            return self._detect_known_coalition(sigla)
        
        # Step 2: Pattern-based detection
        pattern_result = self._detect_by_patterns(sigla)
        if pattern_result.is_coalition:
            return pattern_result
        
        # Step 3: Contextual analysis (if context provided)
        if context:
            context_result = self._detect_by_context(sigla, context)
            if context_result.is_coalition:
                return context_result
        
        # Default: treat as individual party
        return self._create_negative_detection(sigla, "individual_party")
    
    def _detect_known_coalition(self, sigla: str) -> CoalitionDetection:
        """Detect from known coalitions database"""
        coalition_data = self.known_coalitions[sigla]
        
        # Handle special cases where it's marked as individual party
        if coalition_data.get("type") in ["partido", "fusao", "transicao"]:
            return self._create_negative_detection(sigla, "known_individual_party")
        
        return CoalitionDetection(
            is_coalition=True,
            confidence=0.98,  # High confidence for known coalitions
            coalition_sigla=sigla,
            coalition_name=coalition_data["name"],
            component_parties=coalition_data["components"],
            detection_method="known_coalition_database",
            political_spectrum=coalition_data.get("spectrum"),
            formation_date=self._parse_date(coalition_data.get("formation_date"))
        )
    
    def _detect_by_patterns(self, sigla: str) -> CoalitionDetection:
        """Detect coalitions using pattern matching"""
        for rule in self.pattern_rules:
            if re.match(rule["pattern"], sigla):
                components = self._extract_components_from_pattern(sigla, rule)
                
                return CoalitionDetection(
                    is_coalition=True,
                    confidence=rule["confidence"],
                    coalition_sigla=sigla,
                    coalition_name=f"Coligação {sigla}",  # Generic name
                    component_parties=components,
                    detection_method=f"pattern_match: {rule['description']}"
                )
        
        return self._create_negative_detection(sigla, "no_pattern_match")
    
    def _extract_components_from_pattern(self, sigla: str, rule: Dict) -> List[Dict[str, str]]:
        """Extract component party siglas from coalition pattern"""
        components = []
        
        # Handle slash-separated patterns
        if "/" in sigla:
            parts = sigla.split("/")
            for part in parts:
                # Handle dot-separated sub-components
                if "." in part:
                    sub_parts = part.split(".")
                    for sub_part in sub_parts:
                        if sub_part:  # Skip empty parts
                            components.append({
                                "sigla": sub_part,
                                "nome": f"Partido {sub_part}"  # Generic name
                            })
                else:
                    if part:  # Skip empty parts
                        components.append({
                            "sigla": part,
                            "nome": f"Partido {part}"  # Generic name
                        })
        
        # Handle dot-separated only
        elif "." in sigla:
            parts = sigla.split(".")
            for part in parts:
                if part:  # Skip empty parts
                    components.append({
                        "sigla": part,
                        "nome": f"Partido {part}"  # Generic name
                    })
        
        # Single entity (fallback)
        else:
            components.append({
                "sigla": sigla,
                "nome": f"Partido {sigla}"
            })
        
        return components
    
    def _detect_by_context(self, sigla: str, context: Dict) -> CoalitionDetection:
        """Detect coalitions using contextual information"""
        # This could be enhanced with:
        # - Legislature-specific coalition knowledge
        # - Cross-reference with electoral data
        # - Deputy count analysis (coalitions typically have more deputies)
        
        # For now, return negative detection
        return self._create_negative_detection(sigla, "no_contextual_evidence")
    
    def _create_negative_detection(self, sigla: str, reason: str) -> CoalitionDetection:
        """Create negative detection result"""
        return CoalitionDetection(
            is_coalition=False,
            confidence=0.0,
            coalition_sigla=sigla,
            coalition_name=None,
            component_parties=[],
            detection_method=f"negative_detection: {reason}"
        )
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime"""
        if not date_str:
            return None
        
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            return None
    
    def get_coalition_statistics(self, siglas: List[str]) -> Dict:
        """Analyze a list of siglas and return coalition statistics"""
        stats = {
            "total_entities": len(siglas),
            "coalitions_detected": 0,
            "individual_parties": 0,
            "high_confidence": 0,  # > 0.8
            "medium_confidence": 0,  # 0.5-0.8  
            "low_confidence": 0,  # < 0.5
            "detection_methods": {},
            "political_spectrum": {}
        }
        
        for sigla in siglas:
            detection = self.detect(sigla)
            
            if detection.is_coalition:
                stats["coalitions_detected"] += 1
            else:
                stats["individual_parties"] += 1
            
            # Confidence distribution
            if detection.confidence > 0.8:
                stats["high_confidence"] += 1
            elif detection.confidence > 0.5:
                stats["medium_confidence"] += 1
            else:
                stats["low_confidence"] += 1
            
            # Detection methods
            method = detection.detection_method.split(":")[0]  # Get base method
            stats["detection_methods"][method] = stats["detection_methods"].get(method, 0) + 1
            
            # Political spectrum (for coalitions)
            if detection.political_spectrum:
                spectrum = detection.political_spectrum
                stats["political_spectrum"][spectrum] = stats["political_spectrum"].get(spectrum, 0) + 1
        
        return stats


def test_coalition_detector():
    """Test the coalition detection system with known examples"""
    detector = CoalitionDetector()
    
    test_cases = [
        "PPD/PSD.CDS-PP",  # Known coalition
        "CDU",             # Known coalition  
        "CH",              # Individual party
        "PS",              # Individual party
        "MDP/CDE",         # Historical coalition
        "PPD/PSD.CDS-PP.PPM",  # Extended coalition
        "BE",              # Former coalition, now individual party
    ]
    
    print("=== Coalition Detection Test Results ===")
    for sigla in test_cases:
        detection = detector.detect(sigla)
        status = "COALITION" if detection.is_coalition else "PARTY"
        print(f"{status:9} | {sigla:20} | Conf: {detection.confidence:.2f} | {detection.detection_method}")
        
        if detection.is_coalition and detection.component_parties:
            for component in detection.component_parties:
                print(f"         -> {component['sigla']}: {component['nome']}")
    
    # Test statistics
    all_siglas = ["PPD/PSD.CDS-PP", "CDU", "CH", "PS", "IL", "BE", "PCP", "MDP/CDE"]
    stats = detector.get_coalition_statistics(all_siglas)
    
    print(f"\n=== Detection Statistics ===")
    print(f"Total entities: {stats['total_entities']}")
    print(f"Coalitions: {stats['coalitions_detected']}")
    print(f"Individual parties: {stats['individual_parties']}")
    print(f"High confidence: {stats['high_confidence']}")


if __name__ == "__main__":
    test_coalition_detector()