"""
Biographical Registry Translators
=================================

Translators for biographical registry-related coded fields from RegistoBiografico<Legislatura>.xml files.
Based on official Parliament documentation (December 2017 and May 2023):
"Estruturas de dados do Registo Biográfico dos Deputados" specifications.

Handles multi-version data structures with evolution tracking:
- V1: Basic biographical data (older legislatures)
- V2: Enhanced with interest registry (DadosDeputadoRgiWeb)
- V3: Expanded professional activities and social positions
- V5: Modern unified structure with comprehensive interest tracking (XV Legislature+)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SexoType(Enum):
    """
    Gender classification codes from RegistoBiografico
    
    Used in models:
    - Deputado (sexo field)
    - DadosRegistoBiograficoWeb (cadSexo field)
    
    Documentation Reference:
    - cadSexo: "Sexo do Deputado"
    - Standard M/F binary classification in Portuguese Parliament records
    """
    M = "Masculino"
    F = "Feminino"


class EstadoCivilType(Enum):
    """
    Marital status codes from RegistoBiografico
    
    Used in models:
    - Deputado (estado_civil_cod field)  
    - RegistoInteressesV2 (cad_estado_civil_cod field)
    - Interest registry declarations
    
    Documentation Reference:
    - cadEstadoCivilCod/cadEstadoCivilDes: "Estado civil do Deputado"
    - Common Portuguese marital status classifications
    """
    S = "Solteiro"     # Single
    C = "Casado"       # Married
    D = "Divorciado"   # Divorced
    V = "Viúvo"        # Widowed
    UF = "União de Facto"  # Common-law partnership


class HabilitacaoEstadoType(Enum):
    """
    Academic qualification status codes from RegistoBiografico
    
    Used in models:
    - DeputadoHabilitacao (hab_estado field)
    
    Documentation Reference:
    - habEstado: "Estado da habilitação"
    - Tracks completion status of academic qualifications
    """
    CONCLUIDA = "Concluída"           # Completed
    EM_CURSO = "Em curso"             # In progress
    INTERROMPIDA = "Interrompida"     # Interrupted/Suspended
    ABANDONADA = "Abandonada"         # Abandoned
    SUSPENSA = "Suspensa"             # Suspended


class CargoFuncaoAntigaType(Enum):
    """
    Historical position flag from RegistoBiografico
    
    Used in models:
    - DeputadoCargoFuncao (fun_antiga field)
    
    Documentation Reference:
    - funAntiga: "S/N se é função antiga"
    - Distinguishes current from historical professional positions
    """
    S = "Função antiga (já não exercida)"    # Historical position
    N = "Função atual (ainda exercida)"      # Current position


class TipoAtividadeOrgaoType(Enum):
    """
    Parliamentary organ activity types from RegistoBiografico
    
    Used in models:
    - DeputadoAtividadeOrgao (tipo_atividade field)
    
    Documentation Reference:
    - cadActividadeOrgaos structure distinction
    - Two parallel activity tracking systems
    """
    ATIVIDADE_COM = "Atividade em Comissões"           # Committee activities
    ATIVIDADE_GT = "Atividade em Grupos de Trabalho"   # Working group activities


class PosicaoOrgaoType(Enum):
    """
    Parliamentary organ position types from RegistoBiografico
    
    Used in models:
    - DeputadoAtividadeOrgao (tia_des field)
    
    Documentation Reference:
    - tiaDes: "Tipo de posição no órgão"
    - Standard Portuguese Parliament hierarchical positions
    """
    PRESIDENTE = "Presidente"           # President/Chair
    VICE_PRESIDENTE = "Vice-Presidente" # Vice-President/Vice-Chair
    RELATOR = "Relator"                # Rapporteur
    VOGAL = "Vogal"                    # Member
    SECRETARIO = "Secretário"          # Secretary
    MEMBRO = "Membro"                  # General member


class LegislaturaDesignacaoType(Enum):
    """
    Legislature designation codes from RegistoBiografico
    
    Used in models:
    - DeputadoMandatoLegislativo (leg_des field)
    - DeputadoAtividadeOrgao (leg_des field)
    
    Documentation Reference:
    - legDes: "Designação da Legislatura"
    - Complete historical sequence of Portuguese legislatures
    """
    CONSTITUINTE = "Assembleia Constituinte (1975-1976)"
    IA = "I Legislatura - Primeira Parte (1976-1977)"
    IB = "I Legislatura - Segunda Parte (1977-1980)"
    II = "II Legislatura (1980-1983)"
    III = "III Legislatura (1983-1985)"
    IV = "IV Legislatura (1985-1987)"
    V = "V Legislatura (1987-1991)"
    VI = "VI Legislatura (1991-1995)"
    VII = "VII Legislatura (1995-1999)"
    VIII = "VIII Legislatura (1999-2002)"
    IX = "IX Legislatura (2002-2005)"
    X = "X Legislatura (2005-2009)"
    XI = "XI Legislatura (2009-2011)"
    XII = "XII Legislatura (2011-2015)"
    XIII = "XIII Legislatura (2015-2019)"
    XIV = "XIV Legislatura (2019-2022)"
    XV = "XV Legislatura (2022-presente)"


class CirculoEleitoralType(Enum):
    """
    Electoral circle designations from RegistoBiografico
    
    Used in models:
    - DeputadoMandatoLegislativo (ce_des field)
    
    Documentation Reference:
    - ceDes: "Círculo eleitoral"
    - Portuguese electoral geography including districts and special circles
    """
    # Continental Districts
    AVEIRO = "Aveiro"
    BEJA = "Beja"
    BRAGA = "Braga"
    BRAGANCA = "Bragança"
    CASTELO_BRANCO = "Castelo Branco"
    COIMBRA = "Coimbra"
    EVORA = "Évora"
    FARO = "Faro"
    GUARDA = "Guarda"
    LEIRIA = "Leiria"
    LISBOA = "Lisboa"
    PORTALEGRE = "Portalegre"
    PORTO = "Porto"
    SANTAREM = "Santarém"
    SETUBAL = "Setúbal"
    VIANA_DO_CASTELO = "Viana do Castelo"
    VILA_REAL = "Vila Real"
    VISEU = "Viseu"
    
    # Island Regions
    ACORES = "Açores"
    MADEIRA = "Madeira"
    
    # Special Circles
    EMIGRACAO = "Emigração"
    EUROPA = "Europa"


@dataclass
class BiographicalTranslation:
    """Container for biographical field translation results"""
    
    code: str
    description: str
    category: str = "biographical"
    is_valid: bool = True

    def __str__(self) -> str:
        return self.description


class BiographicalTranslator:
    """
    Translator for biographical registry-related coded fields
    
    Handles all enum translations for RegistoBiografico<Legislatura>.xml structures
    including deputy personal data, qualifications, positions, and electoral history.
    
    Usage:
        translator = BiographicalTranslator()
        
        # Gender translation
        gender = translator.gender("M")  # "Masculino"
        
        # Marital status
        marital = translator.marital_status("C")  # "Casado"
        
        # Academic qualification status
        qual_status = translator.qualification_status("CONCLUIDA")  # "Concluída"
        
        # Legislature designation
        legislature = translator.legislature_designation("XV")  # "XV Legislatura (2022-presente)"
    """

    def gender(self, code: str) -> Optional[str]:
        """Get readable description for gender code"""
        translation = self.get_gender(code)
        return translation.description if translation else None

    def get_gender(self, code: str) -> Optional[BiographicalTranslation]:
        """
        Get full translation metadata for gender code
        
        Documentation Reference:
        - Maps cadSexo codes to their descriptions
        - Used in Deputado.sexo field
        """
        if not code:
            return None

        try:
            enum_value = SexoType[code.upper()]
            return BiographicalTranslation(
                code=code,
                description=enum_value.value,
                category="gender",
                is_valid=True,
            )
        except KeyError:
            return BiographicalTranslation(
                code=code,
                description=f"Sexo desconhecido: {code}",
                category="gender",
                is_valid=False,
            )

    def marital_status(self, code: str) -> Optional[str]:
        """Get readable description for marital status code"""
        translation = self.get_marital_status(code)
        return translation.description if translation else None

    def get_marital_status(self, code: str) -> Optional[BiographicalTranslation]:
        """
        Get full translation metadata for marital status code
        
        Documentation Reference:
        - Maps cadEstadoCivilCod codes to their descriptions
        - Used in Deputado.estado_civil_cod and RegistoInteressesV2 fields
        """
        if not code:
            return None

        try:
            enum_value = EstadoCivilType[code.upper()]
            return BiographicalTranslation(
                code=code,
                description=enum_value.value,
                category="marital_status",
                is_valid=True,
            )
        except KeyError:
            return BiographicalTranslation(
                code=code,
                description=f"Estado civil desconhecido: {code}",
                category="marital_status",
                is_valid=False,
            )

    def qualification_status(self, code: str) -> Optional[str]:
        """Get readable description for academic qualification status"""
        translation = self.get_qualification_status(code)
        return translation.description if translation else None

    def get_qualification_status(self, code: str) -> Optional[BiographicalTranslation]:
        """
        Get full translation metadata for qualification status
        
        Documentation Reference:
        - Maps habEstado values to their descriptions
        - Used in DeputadoHabilitacao.hab_estado field
        """
        if not code:
            return None

        try:
            enum_value = HabilitacaoEstadoType[code.upper()]
            return BiographicalTranslation(
                code=code,
                description=enum_value.value,
                category="qualification_status",
                is_valid=True,
            )
        except KeyError:
            return BiographicalTranslation(
                code=code,
                description=f"Estado de habilitação desconhecido: {code}",
                category="qualification_status",
                is_valid=False,
            )

    def position_historical_flag(self, code: str) -> Optional[str]:
        """Get readable description for historical position flag"""
        translation = self.get_position_historical_flag(code)
        return translation.description if translation else None

    def get_position_historical_flag(self, code: str) -> Optional[BiographicalTranslation]:
        """
        Get full translation metadata for position historical flag
        
        Documentation Reference:
        - Maps funAntiga S/N values to their descriptions
        - Used in DeputadoCargoFuncao.fun_antiga field
        """
        if not code:
            return None

        try:
            enum_value = CargoFuncaoAntigaType[code.upper()]
            return BiographicalTranslation(
                code=code,
                description=enum_value.value,
                category="position_historical",
                is_valid=True,
            )
        except KeyError:
            return BiographicalTranslation(
                code=code,
                description=f"Flag função antiga desconhecida: {code}",
                category="position_historical",
                is_valid=False,
            )

    def organ_activity_type(self, code: str) -> Optional[str]:
        """Get readable description for parliamentary organ activity type"""
        translation = self.get_organ_activity_type(code)
        return translation.description if translation else None

    def get_organ_activity_type(self, code: str) -> Optional[BiographicalTranslation]:
        """
        Get full translation metadata for organ activity type
        
        Documentation Reference:
        - Maps cadActividadeOrgaos activity types to descriptions
        - Used in DeputadoAtividadeOrgao.tipo_atividade field
        """
        if not code:
            return None

        try:
            # Normalize code variations
            normalized_code = code.upper().replace("ATIVIDADE", "ATIVIDADE_")
            if normalized_code == "ACTIVIDADECOM":
                normalized_code = "ATIVIDADE_COM"
            elif normalized_code == "ACTIVIDADEGT":
                normalized_code = "ATIVIDADE_GT"
            
            enum_value = TipoAtividadeOrgaoType[normalized_code]
            return BiographicalTranslation(
                code=code,
                description=enum_value.value,
                category="organ_activity_type",
                is_valid=True,
            )
        except KeyError:
            return BiographicalTranslation(
                code=code,
                description=f"Tipo de atividade desconhecido: {code}",
                category="organ_activity_type",
                is_valid=False,
            )

    def organ_position_type(self, code: str) -> Optional[str]:
        """Get readable description for parliamentary organ position"""
        translation = self.get_organ_position_type(code)
        return translation.description if translation else None

    def get_organ_position_type(self, code: str) -> Optional[BiographicalTranslation]:
        """
        Get full translation metadata for organ position type
        
        Documentation Reference:
        - Maps tiaDes position values to descriptions
        - Used in DeputadoAtividadeOrgao.tia_des field
        """
        if not code:
            return None

        try:
            # Handle variations in position naming
            normalized_code = code.upper().replace("-", "_").replace(" ", "_")
            enum_value = PosicaoOrgaoType[normalized_code]
            return BiographicalTranslation(
                code=code,
                description=enum_value.value,
                category="organ_position",
                is_valid=True,
            )
        except KeyError:
            return BiographicalTranslation(
                code=code,
                description=f"Posição no órgão desconhecida: {code}",
                category="organ_position",
                is_valid=False,
            )

    def legislature_designation(self, code: str) -> Optional[str]:
        """Get readable description for legislature designation"""
        translation = self.get_legislature_designation(code)
        return translation.description if translation else None

    def get_legislature_designation(self, code: str) -> Optional[BiographicalTranslation]:
        """
        Get full translation metadata for legislature designation
        
        Documentation Reference:
        - Maps legDes legislature codes to full descriptions
        - Used in DeputadoMandatoLegislativo and DeputadoAtividadeOrgao
        """
        if not code:
            return None

        try:
            enum_value = LegislaturaDesignacaoType[code.upper()]
            return BiographicalTranslation(
                code=code,
                description=enum_value.value,
                category="legislature",
                is_valid=True,
            )
        except KeyError:
            return BiographicalTranslation(
                code=code,
                description=f"Legislatura desconhecida: {code}",
                category="legislature",
                is_valid=False,
            )

    def electoral_circle(self, code: str) -> Optional[str]:
        """Get readable description for electoral circle"""
        translation = self.get_electoral_circle(code)
        return translation.description if translation else None

    def get_electoral_circle(self, code: str) -> Optional[BiographicalTranslation]:
        """
        Get full translation metadata for electoral circle
        
        Documentation Reference:
        - Maps ceDes electoral circle codes to descriptions
        - Used in DeputadoMandatoLegislativo.ce_des field
        """
        if not code:
            return None

        try:
            # Handle common variations in circle naming
            normalized_code = code.upper().replace(" ", "_").replace("Ç", "C").replace("Ã", "A")
            enum_value = CirculoEleitoralType[normalized_code]
            return BiographicalTranslation(
                code=code,
                description=enum_value.value,
                category="electoral_circle",
                is_valid=True,
            )
        except KeyError:
            return BiographicalTranslation(
                code=code,
                description=f"Círculo eleitoral desconhecido: {code}",
                category="electoral_circle",
                is_valid=False,
            )


# Global instance for convenience
biographical_translator = BiographicalTranslator()


def translate_gender(code: str) -> Optional[str]:
    """Quick translation of gender code"""
    return biographical_translator.gender(code)


def translate_marital_status(code: str) -> Optional[str]:
    """Quick translation of marital status code"""
    return biographical_translator.marital_status(code)


def translate_qualification_status(code: str) -> Optional[str]:
    """Quick translation of qualification status code"""
    return biographical_translator.qualification_status(code)


def translate_position_historical_flag(code: str) -> Optional[str]:
    """Quick translation of position historical flag"""
    return biographical_translator.position_historical_flag(code)


def translate_organ_activity_type(code: str) -> Optional[str]:
    """Quick translation of organ activity type"""
    return biographical_translator.organ_activity_type(code)


def translate_organ_position_type(code: str) -> Optional[str]:
    """Quick translation of organ position type"""
    return biographical_translator.organ_position_type(code)


def translate_legislature_designation(code: str) -> Optional[str]:
    """Quick translation of legislature designation"""
    return biographical_translator.legislature_designation(code)


def translate_electoral_circle(code: str) -> Optional[str]:
    """Quick translation of electoral circle"""
    return biographical_translator.electoral_circle(code)