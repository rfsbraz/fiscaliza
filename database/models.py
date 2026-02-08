"""
SQLAlchemy Models for Portuguese Parliament Database

Comprehensive models for all parliamentary data with zero data loss.
Uses PostgreSQL database with UUID primary keys for efficient imports.
"""

import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.types import GUID

Base = declarative_base()


# =====================================================
# MAIN ENTITIES
# =====================================================


class Legislatura(Base):
    """
    Legislature Model - Based on InformacaoBase LegislaturaOut specification

    Contains comprehensive legislature information including dates, identifiers and status.

    InformacaoBase Mapping (LegislaturaOut):
    - dtini: data_inicio (Start date of legislature)
    - dtfim: data_fim (End date of legislature)
    - sigla: numero (Legislature abbreviation/number - e.g., "XV", "Cons")

    Usage:
        Used as root container in InformacaoBase<Legislatura>.xml files
        References: DetalheLegislatura structure
    """

    __tablename__ = "legislaturas"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    numero = Column(
        String(20),
        unique=True,
        nullable=False,
        comment="Legislature abbreviation (XML: sigla)",
    )
    designacao = Column(
        String(100), nullable=False, comment="Full legislature designation"
    )
    data_inicio = Column(Date, comment="Legislature start date (XML: dtini)")
    data_fim = Column(Date, comment="Legislature end date (XML: dtfim)")
    # Note: Active legislature is now determined dynamically (data_fim IS NULL)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Partido(Base):
    """
    Political Party Model - Based on InformacaoBase GPOut specification

    Contains parliamentary group information as represented in parliament structure.

    InformacaoBase Mapping (GPOut):
    - sigla: sigla (Parliamentary group abbreviation - e.g., "PS", "PSD")
    - nome: nome (Full parliamentary group name)

    Usage:
        Referenced in GruposParlamentares section of InformacaoBase files
        Used for deputy parliamentary group associations
    """

    __tablename__ = "partidos"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    sigla = Column(
        String(10),
        unique=True,
        nullable=False,
        comment="Parliamentary group abbreviation (XML: sigla)",
    )
    nome = Column(
        String(200), nullable=False, comment="Full parliamentary group name (XML: nome)"
    )
    designacao_completa = Column(Text)
    cor_hex = Column(String(7))
    # Removed unreliable 'ativo' field - calculated at runtime based on current mandates
    data_fundacao = Column(Date)
    ideologia = Column(String(100))
    lider_parlamentar = Column(String(200))
    
    # Coalition support - distinguish parties from coalitions
    tipo_entidade = Column(
        String(20),
        default='partido',
        nullable=False,
        comment="Entity type: 'partido' (individual party) or 'coligacao' (coalition)"
    )
    coligacao_pai_id = Column(
        GUID(),
        ForeignKey("coligacoes.id"),
        comment="Parent coalition ID if this party is part of a coalition"
    )
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    coligacao_pai = relationship("Coligacao", foreign_keys=[coligacao_pai_id])

    @property
    def is_active(self):
        """Party is active if it has deputies in current legislature XVII.
        Result is cached on the instance to avoid repeated DB queries in loops."""
        if hasattr(self, '_is_active_cache'):
            return self._is_active_cache
        from database.connection import get_session
        from sqlalchemy import exists
        session = get_session()
        try:
            result = session.query(
                exists().where(
                    DeputadoMandatoLegislativo.par_sigla == self.sigla,
                    DeputadoMandatoLegislativo.leg_des.like('%XVII%')
                )
            ).scalar()
            self._is_active_cache = result
            return result
        finally:
            session.close()


class Coligacao(Base):
    """
    Political Coalition Model - Portuguese Parliamentary Coalitions
    
    Represents formal electoral alliances (coligações) between political parties.
    Based on Portuguese political analysis and coalition patterns detected in data.
    
    Coalition Examples:
    - "PPD/PSD.CDS-PP" = Aliança Democrática (PPD, PSD, CDS-PP)
    - "CDU" = Coligação Democrática Unitária (PCP, PEV)
    - "MDP/CDE" = Historical coalition
    
    Features:
    - Formal coalition metadata and formation dates
    - Electoral program and policy positions
    - Coalition leadership structure
    - Unified voting record tracking
    """
    
    __tablename__ = "coligacoes"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    sigla = Column(
        String(50), 
        unique=True, 
        nullable=False,
        comment="Coalition abbreviation/sigla (e.g., 'PPD/PSD.CDS-PP')"
    )
    nome = Column(
        String(300), 
        nullable=False,
        comment="Full coalition name (e.g., 'Aliança Democrática')"
    )
    nome_eleitoral = Column(
        String(300),
        comment="Electoral designation used in campaigns"
    )
    data_formacao = Column(Date, comment="Coalition formation date")
    data_dissolucao = Column(Date, comment="Coalition dissolution date (if applicable)")
    programa_eleitoral = Column(Text, comment="Joint electoral program summary")
    lideranca = Column(Text, comment="Coalition leadership structure")
    acordo_coligacao = Column(Text, comment="Coalition agreement details")
    
    # Coalition classification
    tipo_coligacao = Column(
        String(50), 
        default='eleitoral',
        comment="Coalition type: eleitoral, parlamentar, governo"
    )
    espectro_politico = Column(
        String(50),
        comment="Political spectrum: esquerda, centro-esquerda, centro, centro-direita, direita"
    )
    
    # Status tracking
    confianca_detecao = Column(Float, comment="Confidence score for automatic detection (0.0-1.0)")
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    partidos_componentes = relationship(
        "ColigacaoPartido", 
        back_populates="coligacao",
        cascade="all, delete-orphan"
    )
    partidos_filhos = relationship(
        "Partido",
        foreign_keys="Partido.coligacao_pai_id",
        back_populates="coligacao_pai"
    )
    
    @property
    def is_active(self):
        """
        Runtime calculation: Coalition is active if it has deputies in current legislature XVII
        Uses coalition ID and party sigla matching for detection
        """
        from database.connection import get_session
        from sqlalchemy import exists, or_, and_
        session = get_session()
        try:
            # Check if coalition has deputies in current legislature using coalition ID or party sigla match
            return session.query(
                exists().where(
                    and_(
                        or_(
                            # Coalition ID match (for mandates with coalition context)
                            DeputadoMandatoLegislativo.coligacao_id == self.id,
                            # Party sigla match (for direct coalition siglas like "CDU", "AD")
                            DeputadoMandatoLegislativo.par_sigla == self.sigla
                        ),
                        DeputadoMandatoLegislativo.leg_des.like('%XVII%')
                    )
                )
            ).scalar()
        finally:
            session.close()
    
    @property
    def ativo(self):
        """Alias for is_active to maintain API compatibility"""
        return self.is_active
    
    @property
    def num_partidos_componentes(self):
        """Number of component parties in coalition"""
        return len(self.partidos_componentes)
    
    def __repr__(self):
        return f"<Coligacao(sigla='{self.sigla}', nome='{self.nome}')>"


class ColigacaoPartido(Base):
    """
    Coalition-Party Relationship Model
    
    Junction table representing the many-to-many relationship between 
    coalitions and their component political parties.
    
    Tracks historical changes in coalition composition over time.
    """
    
    __tablename__ = "coligacao_partidos"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    coligacao_id = Column(GUID(), ForeignKey("coligacoes.id"), nullable=False)
    partido_sigla = Column(String(50), nullable=False, comment="Component party sigla")
    partido_nome = Column(String(200), comment="Component party name")
    
    # Temporal tracking
    data_adesao = Column(Date, comment="Date party joined coalition")
    data_saida = Column(Date, comment="Date party left coalition (if applicable)")
    ativo = Column(Boolean, default=True, comment="Whether party is currently in coalition")
    
    # Coalition role
    papel_coligacao = Column(
        String(100),
        comment="Party role in coalition: lider, principal, secundario, apoiante"
    )
    percentagem_acordada = Column(
        Float,
        comment="Agreed percentage for seat/resource distribution"
    )
    
    # Metadata
    confianca_detecao = Column(Float, comment="Detection confidence for this relationship")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    coligacao = relationship("Coligacao", back_populates="partidos_componentes")
    
    # Indexes and constraints for efficient queries
    __table_args__ = (
        UniqueConstraint('coligacao_id', 'partido_sigla', name='uq_coligacao_partido'),
        Index("idx_coligacao_partido", "coligacao_id", "partido_sigla"),
        Index("idx_partido_sigla", "partido_sigla"),
        Index("idx_ativo_coligacao", "ativo", "coligacao_id"),
    )
    
    def __repr__(self):
        return f"<ColigacaoPartido(coligacao_id={self.coligacao_id}, partido='{self.partido_sigla}')>"


class CirculoEleitoral(Base):
    """
    Electoral Circle Model - Based on InformacaoBase DadosCirculoEleitoralList specification

    Contains electoral constituency information for deputy elections.

    InformacaoBase Mapping (DadosCirculoEleitoralList):
    - cpId: codigo (Electoral circle code/identifier)
    - cpDes: designacao (Electoral circle description/name)
    - legDes: legislature reference (not stored, used for context)

    Usage:
        Referenced in CirculosEleitorais section of InformacaoBase files
        Used for deputy constituency associations (DepCPId field)
    """

    __tablename__ = "circulos_eleitorais"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    designacao = Column(
        String(100),
        unique=True,
        nullable=False,
        comment="Electoral circle name (XML: cpDes)",
    )
    codigo = Column(String(10), comment="Electoral circle code (XML: cpId)")
    regiao = Column(String(50))
    distrito = Column(String(50))
    num_deputados = Column(Integer, default=0)
    populacao = Column(Integer)
    area_km2 = Column(Integer)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Deputado(Base):
    """
    Deputy/Parliament Member Model - Central biographical data repository

    Combines data from multiple sources:
    1. InformacaoBase DadosDeputadoOrgaoPlenario specification
    2. RegistoBiografico<Legislatura>.xml DadosRegistoBiograficoWeb structure

    Contains comprehensive deputy information including identity, affiliations, status,
    and complete biographical profile.

    CRITICAL: Deputy Identity and Uniqueness Principle
    ================================================
    - `id`: Primary key, unique within this table but DIFFERENT for each legislature entry
    - `id_cadastro`: Registration number - THIS IS THE TRUE UNIQUE IDENTIFIER for a person
      across ALL legislatures. Use this field to identify the same person across different
      legislative periods, NOT the `id` field.

    DESIGN PRINCIPLE:
    - Each deputy gets a NEW `id` for EACH legislature they serve in
    - The same person (same `id_cadastro`) will have MULTIPLE records with different `id` values
    - Activity data (votes, interventions, initiatives) links to the legislature-specific `id`
    - Person identity queries (counting unique deputies) MUST use `id_cadastro`
    
    QUERY GUIDELINES:
    - Count unique PEOPLE: Use DISTINCT(id_cadastro)  
    - Count unique RECORDS: Use COUNT(id)
    - Find same person across legislatures: GROUP BY id_cadastro
    - Link to activities: Use the legislature-specific `id`
    
    EXAMPLE:
    - Tiago Barbosa Ribeiro (id_cadastro: 2445) has 5 different `id` values
    - His XVII legislature activities link to his XVII-specific `id`
    - To count him as 1 person, use his `id_cadastro`

    InformacaoBase Mapping (DadosDeputadoOrgaoPlenario):
    - DepId: id (Legislature-specific deputy identifier)
    - DepCadId: id_cadastro (Unique person registration ID across all legislatures)
    - DepNomeParlamentar: nome (Parliamentary name - shortened version)
    - DepNomeCompleto: nome_completo (Full deputy name)
    - DepCPId: Electoral circle identifier (links to CirculoEleitoral)
    - DepCPDes: Electoral circle name (for reference)
    - DepGP: Parliamentary group associations (DadosSituacaoGP structure)
    - DepSituacao: Deputy situations (DadosSituacaoDeputado structure)
    - LegDes: Legislature reference (not stored, used for context)

    Biographical Registry Mapping (DadosRegistoBiograficoWeb):
    - cadId: id_cadastro (Unique registration ID - matches across sources)
    - cadNomeCompleto: nome_completo (Full name)
    - cadDtNascimento: data_nascimento (Birth date)
    - cadSexo: sexo (Gender M/F)
    - cadProfissao: profissao (Profession)
    - cadNaturalidade: naturalidade (Place of birth)
    - cadHabilitacoes: habilitacoes (Linked via DeputadoHabilitacao relationship)
    - cadCargosFuncoes: cargos_funcoes (Linked via DeputadoCargoFuncao relationship)
    - cadTitulos: titulos (Linked via DeputadoTitulo relationship)
    - cadCondecoracoes: condecoracoes (Linked via DeputadoCondecoracao relationship)
    - cadObrasPublicadas: obras_publicadas (Linked via DeputadoObraPublicada relationship)
    - cadActividadeOrgaos: atividades_orgaos (Linked via DeputadoAtividadeOrgao relationship)
    - cadDeputadoLegis: mandatos_legislativos (Linked via DeputadoMandatoLegislativo relationship)

    Interest Registry Integration:
    - DadosDeputadoRgiWeb: registo_interesses_v2 (V2 structure)
    - RegistoInteressesV3/V5: registo_interesses_unified (Modern unified structure)

    Usage:
        Central entity linking all deputy-related information across multiple data sources
        Supports both current parliament operations and comprehensive biographical research
    """

    __tablename__ = "deputados"

    id = Column(
        GUID(), primary_key=True, default=uuid.uuid4, comment="UUID primary key"
    )
    xml_source_id = Column(
        Integer,
        nullable=True,
        index=True,
        unique=False,
        comment="Original DepId from XML (unique per legislature, used for FK resolution during import)"
    )
    id_cadastro = Column(
        Integer,
        nullable=False,
        comment="Person's unique registration ID across all legislatures (XML: DepCadId)",
    )
    nome = Column(
        String(200),
        nullable=False,
        comment="Parliamentary name - shortened version (XML: DepNomeParlamentar)",
    )
    nome_completo = Column(
        String(300), comment="Full deputy name (XML: DepNomeCompleto)"
    )
    legislatura_id = Column(GUID(), ForeignKey("legislaturas.id"), nullable=False)
    sexo = Column(String(1))  # M/F - cadSexo field
    profissao = Column(String(200))
    data_nascimento = Column(Date)
    naturalidade = Column(String(100))
    estado_civil_cod = Column(String(10))  # cadEstadoCivilCod
    habilitacoes_academicas = Column(Text)
    biografia = Column(Text)
    foto_url = Column(String(500))
    email = Column(String(100))
    telefone = Column(String(20))
    gabinete = Column(String(50))
    # Removed unreliable 'ativo' field - calculated at runtime based on current mandates
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Data provenance tracking
    import_status_id = Column(
        GUID(),
        ForeignKey("import_status.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Reference to import batch that created/updated this record"
    )

    # Relationships
    atividades = relationship(
        "AtividadeDeputado", back_populates="deputado", cascade="all, delete-orphan"
    )
    cargos = relationship(
        "DepCargo", back_populates="deputado", cascade="all, delete-orphan"
    )
    habilitacoes = relationship(
        "DeputadoHabilitacao", back_populates="deputado", cascade="all, delete-orphan"
    )
    cargos_funcoes = relationship(
        "DeputadoCargoFuncao", back_populates="deputado", cascade="all, delete-orphan"
    )
    titulos = relationship(
        "DeputadoTitulo", back_populates="deputado", cascade="all, delete-orphan"
    )
    condecoracoes = relationship(
        "DeputadoCondecoracao", back_populates="deputado", cascade="all, delete-orphan"
    )
    obras_publicadas = relationship(
        "DeputadoObraPublicada", back_populates="deputado", cascade="all, delete-orphan"
    )
    atividades_orgaos = relationship(
        "DeputadoAtividadeOrgao",
        back_populates="deputado",
        cascade="all, delete-orphan",
    )
    mandatos_legislativos = relationship(
        "DeputadoMandatoLegislativo",
        back_populates="deputado",
        cascade="all, delete-orphan",
    )
    gp_situations = relationship(
        "DeputyGPSituation", back_populates="deputado", cascade="all, delete-orphan"
    )
    situations = relationship(
        "DeputySituation", back_populates="deputado", cascade="all, delete-orphan"
    )

    @property
    def is_active(self):
        """Deputy is active if they have a mandate in current legislature XVII.
        Uses loaded relationship if available, otherwise falls back to DB query."""
        if 'mandatos_legislativos' in self.__dict__:
            return any(
                m.leg_des and 'XVII' in m.leg_des
                for m in self.mandatos_legislativos
            )
        from database.connection import get_session
        from sqlalchemy import exists
        session = get_session()
        try:
            return session.query(
                exists().where(
                    DeputadoMandatoLegislativo.deputado_id == self.id,
                    DeputadoMandatoLegislativo.leg_des.like('%XVII%')
                )
            ).scalar()
        finally:
            session.close()

    @property
    def mandate_status(self):
        """
        Get the mandate status for this deputy in the CURRENT legislature (XVII).

        Returns the sio_des value from the latest DadosSituacaoDeputado record
        for the current legislature only. For historical deputies not in XVII,
        returns None.

        Possible values: Efetivo, Efetivo Temporário, Efetivo Definitivo,
                        Suspenso(Eleito), Suspenso(Não Eleito), Renunciou,
                        Suplente, Impedido, Desistência

        Returns:
            str or None: The current mandate status or None if not in current legislature
        """
        # Only return status if deputy is in current legislature
        if not self.is_active:
            return None

        from database.connection import get_session
        from app.utils.deputy_status import get_deputy_status_by_cadastro
        session = get_session()
        try:
            # Get status in current legislature XVII using cadastro ID
            return get_deputy_status_by_cadastro(self.id_cadastro, 'XVII', session)
        finally:
            session.close()

    @property
    def is_seated(self):
        """
        Check if deputy is currently occupying a seat in the CURRENT legislature (XVII).

        A deputy is seated if:
        1. They have a mandate in the current legislature (XVII)
        2. Their current status is one of the Efetivo variants

        Deputies with these statuses are NOT seated:
        - Suspenso(Eleito) - suspended (e.g., government members)
        - Suspenso(Não Eleito) - suspended non-elected
        - Renunciou - resigned
        - Suplente - substitute (not currently in seat)
        - Impedido - impeded
        - Desistência - withdrawn

        Historical deputies (not in XVII) always return False.

        Returns:
            bool: True if deputy is currently seated in XVII, False otherwise
        """
        # Must be active (have mandate in XVII) to be seated
        if not self.is_active:
            return False

        from app.utils.deputy_status import is_seated_status
        return is_seated_status(self.mandate_status)

    # Indexes for query optimization
    __table_args__ = (
        Index("idx_deputy_cadastro", "id_cadastro"),
        Index("idx_deputy_legislature", "legislatura_id"),
        Index("idx_deputy_name", "nome"),
    )


class DeputyIdentityMapping(Base):
    """
    Deputy Identity Mapping Table - Tracks cadastral ID changes over time

    This table maintains a history of cadastral ID changes for deputies,
    allowing us to link the same person across different legislatures even
    when their cadastral ID changes in parliamentary records.

    Key Use Cases:
    - Track when deputy Beatriz Cal Brandão changes from cad_id 3346 to 4742
    - Maintain data integrity when processing biographical records
    - Enable robust deputy matching across time periods

    Processing Rules:
    - Only registo_biografico mapper should update this table
    - New entries created when cadastral ID changes are detected
    - Used for fallback matching when direct cadastral lookup fails
    """

    __tablename__ = "deputy_identity_mappings"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    old_cad_id = Column(Integer, nullable=False, comment="Previous cadastral ID")
    new_cad_id = Column(Integer, nullable=False, comment="New cadastral ID")
    deputy_name = Column(
        String(255), nullable=False, comment="Deputy name for verification"
    )
    deputy_full_name = Column(String(500), comment="Deputy full name for verification")
    first_seen_legislature = Column(
        String(50), comment="Legislature where old ID was used"
    )
    change_detected_legislature = Column(
        String(50), comment="Legislature where change was detected"
    )
    change_reason = Column(
        String(255), comment="Reason for cadastral ID change if known"
    )
    confidence_score = Column(
        Integer, default=100, comment="Confidence in mapping accuracy (0-100)"
    )
    verified = Column(
        Boolean, default=False, comment="Whether mapping has been manually verified"
    )
    created_at = Column(
        DateTime, default=func.now(), comment="When mapping was first detected"
    )
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Indexes for efficient lookups
    __table_args__ = (
        Index("idx_identity_mapping_old_cad_id", "old_cad_id"),
        Index("idx_identity_mapping_new_cad_id", "new_cad_id"),
        Index("idx_identity_mapping_deputy_name", "deputy_name"),
        UniqueConstraint("old_cad_id", "new_cad_id", name="uq_identity_mapping"),
    )


class DepCargo(Base):
    __tablename__ = "dep_cargos"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    deputado_id = Column(GUID(), ForeignKey("deputados.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    deputado = relationship("Deputado", back_populates="cargos")
    dados_cargo_deputado = relationship(
        "DadosCargoDeputado", back_populates="dep_cargo", cascade="all, delete-orphan"
    )


class DadosCargoDeputado(Base):
    __tablename__ = "dados_cargo_deputados"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    dep_cargo_id = Column(GUID(), ForeignKey("dep_cargos.id"), nullable=False)
    car_des = Column(String(200))  # carDes - Position description
    car_id = Column(Integer)  # carId - Position ID
    car_dt_inicio = Column(Date)  # carDtInicio - Position start date
    created_at = Column(DateTime, default=func.now())

    # Relationships
    dep_cargo = relationship("DepCargo", back_populates="dados_cargo_deputado")


# =====================================================
# COMPREHENSIVE DEPUTY ACTIVITIES - ZERO DATA LOSS
# =====================================================


# DeputyActivity removed - unused legacy code


# =====================================================
# INITIATIVES
# =====================================================


class DeputyInitiative(Base):
    __tablename__ = "deputy_initiatives"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    deputy_activity_id = Column(
        GUID(), ForeignKey("atividade_deputados.id"), nullable=False
    )
    id_iniciativa = Column(Integer)
    numero = Column(String(50))
    tipo = Column(Text)
    desc_tipo = Column(String(200))
    assunto = Column(Text)
    legislatura = Column(String(20))
    sessao = Column(String(20))
    data_entrada = Column(Date)
    data_agendamento_debate = Column(Date)
    orgao_exterior = Column(String(200))
    observacoes = Column(Text)
    tipo_autor = Column(String(100))
    created_at = Column(DateTime, default=func.now())

    # Relationships
    deputy_activity = relationship("AtividadeDeputado", back_populates="initiatives")
    # Removed unused supporting model relationships:
    # - votes, author_groups, author_elected, guests, publications

    __table_args__ = (
        Index("idx_deputy_initiatives_activity", "deputy_activity_id"),
        Index("idx_deputy_initiatives_data_entrada", "data_entrada"),
    )


# DeputyInitiativeVote model removed - unused legacy code


# DeputyInitiativeAuthorGroup model removed - unused legacy code


# DeputyInitiativeAuthorElected model removed - unused legacy code


# DeputyInitiativeGuest removed - unused legacy code


# DeputyInitiativePublication removed - unused legacy code


# =====================================================
# INTERVENTIONS
# =====================================================


# DeputyIntervention model removed - unused legacy code


# =====================================================
# REPORTS (same structure as initiatives)
# =====================================================


# DeputyReport removed - unused legacy code


# Report supporting tables (same pattern as initiatives)
# DeputyReportVote removed - unused legacy code


# DeputyReportAuthorGroup removed - unused legacy code


# DeputyReportAuthorElected removed - unused legacy code


# DeputyReportGuest removed - unused legacy code


# DeputyReportPublication removed - unused legacy code


# =====================================================
# PARLIAMENTARY ACTIVITIES (same structure as initiatives)
# =====================================================


# DeputyParliamentaryActivity removed - unused legacy code


# Parliamentary Activity supporting tables (same pattern)
# DeputyParliamentaryActivityVote removed - unused legacy code


# DeputyParliamentaryActivityAuthorGroup removed - unused legacy code


# DeputyParliamentaryActivityAuthorElected removed - unused legacy code


# DeputyParliamentaryActivityGuest removed - unused legacy code


# DeputyParliamentaryActivityPublication removed - unused legacy code


# =====================================================
# LEGISLATIVE DATA (same structure as initiatives)
# =====================================================


# DeputyLegislativeData removed - unused legacy code


# Legislative Data supporting tables (same pattern)
# DeputyLegislativeDataVote removed - unused legacy code


# DeputyLegislativeDataAuthorGroup removed - unused legacy code


# DeputyLegislativeDataAuthorElected removed - unused legacy code


# DeputyLegislativeDataGuest removed - unused legacy code


# DeputyLegislativeDataPublication removed - unused legacy code


# =====================================================
# COMPLEX NESTED STRUCTURES
# =====================================================


class DeputyGPSituation(Base):
    """
    Deputy Parliamentary Group Situation - Based on InformacaoBase DadosSituacaoGP specification

    Contains deputy's parliamentary group membership information with dates.

    InformacaoBase Mapping (DadosSituacaoGP):
    - gpId: gp_id (Parliamentary group identifier)
    - gpSigla: gp_sigla (Parliamentary group acronym - e.g., "PS", "PSD")
    - gpDtInicio: gp_dt_inicio (Group membership start date)
    - gpDtFim: gp_dt_fim (Group membership end date)

    Usage:
        Nested within DepGP structure in InformacaoBase files
        Tracks deputy parliamentary group changes over time
        Unified model for all contexts (InformacaoBase, activities, etc.)
    """

    __tablename__ = "deputy_gp_situations"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    deputado_id = Column(GUID(), ForeignKey("deputados.id"), nullable=False)
    legislatura_id = Column(GUID(), ForeignKey("legislaturas.id"), nullable=False)
    gp_id = Column(Integer, comment="Parliamentary group ID (XML: gpId)")
    gp_sigla = Column(String(20), comment="Parliamentary group acronym (XML: gpSigla)")
    gp_dt_inicio = Column(Date, comment="GP membership start date (XML: gpDtInicio)")
    gp_dt_fim = Column(Date, comment="GP membership end date (XML: gpDtFim)")
    composition_context = Column(
        String(50)
    )  # Context where this GP situation was recorded (ar_board, commission, etc.)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    deputado = relationship("Deputado", back_populates="gp_situations")
    legislatura = relationship("Legislatura")


class DeputySituation(Base):
    """Deputy Situation - unified model for all contexts (organ composition, activities, etc.)"""

    __tablename__ = "deputy_situations"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    deputado_id = Column(GUID(), ForeignKey("deputados.id"), nullable=False)
    legislatura_id = Column(GUID(), ForeignKey("legislaturas.id"), nullable=False)
    sio_des = Column(
        String(200)
    )  # Situation description (e.g., "Renunciou", "Efetivo", etc.)
    sio_tip_mem = Column(String(100))  # Type of membership
    sio_dt_inicio = Column(Date)  # Start date of situation
    sio_dt_fim = Column(Date)  # End date of situation
    created_at = Column(DateTime, default=func.now())

    # Relationships
    deputado = relationship("Deputado", back_populates="situations")
    legislatura = relationship("Legislatura")


# =====================================================
# LEGACY TABLES (for existing data compatibility)
# =====================================================


class TemasParliamentares(Base):
    __tablename__ = "temas_parlamentares"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    id_externo = Column(Integer)
    nome = Column(String(200), nullable=False)
    descricao = Column(Text)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    __table_args__ = (Index("idx_temas_parlamentares_id_externo", "id_externo"),)


class SecoesParliamentares(Base):
    __tablename__ = "secoes_parlamentares"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    id_externo = Column(Integer)
    nome = Column(String(200), nullable=False)
    descricao = Column(Text)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    __table_args__ = (Index("idx_secoes_parlamentares_id_externo", "id_externo"),)


class AgendaParlamentar(Base):
    """
    Parliamentary Agenda Root Container
    ==================================

    Root container for parliamentary agenda events from AgendaParlamentar.xml/.json.
    Based on official Portuguese Parliament documentation (June 2023):
    "AgendaParlamentar/RootObject" structure from XV_Legislatura documentation.

    MAPPED STRUCTURES (from official documentation):

    1. **AgendaParlamentar/RootObject** - Main agenda event structure
       - Id: Unique meeting/event identifier (id_externo)
       - SectionId: Section unique identifier (secao_id) - requires SectionType translator
       - Section: Section description (secao_nome) - mapped from SectionType enum
       - ThemeId: Theme unique identifier (tema_id) - requires ThemeType translator
       - Theme: Theme description (tema_nome) - mapped from ThemeType enum
       - ParlamentGroup: Parliamentary group ID (grupo_parlamentar)
       - AllDayEvent: Full day event indicator (evento_dia_inteiro)
       - EventStartDate: Event start date (data_evento)
       - EventStartTime: Event start time (hora_inicio)
       - EventEndDate: Event end date (calculated from start + duration)
       - EventEndTime: Event end time (hora_fim)
       - Title: Event title (titulo)
       - Subtitle: Event subtitle (subtitulo)
       - InternetText: HTML encoded descriptive text (descricao)
       - Local: Event location (local_evento)
       - Link: Parliament website link (link_externo)
       - LegDes: Legislature reference (legislatura_designacao)
       - OrgDes: Organ reference (orgao_designacao)
       - ReuNumero: Meeting number (reuniao_numero)
       - SelNumero: Legislative session number (sessao_numero)
       - PostPlenary: After plenary session indicator (pos_plenario)
       - OrderValue: Meeting/event order number (order_value)

    Translation Requirements:
    - secao_id: Maps to SectionType enum (24 section codes: 1-24)
    - tema_id: Maps to ThemeType enum (16 theme codes: 1-16)

    Attachment Support:
    - AnexosComissaoPermanente: Permanent committee attachments
    - AnexosPlenario: Plenary session attachments
    """

    __tablename__ = "agenda_parlamentar"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    id_externo = Column(
        Integer, comment="Unique meeting/event identifier (Id) - external system ID"
    )
    legislatura_id = Column(GUID(), nullable=False)
    secao_id = Column(
        Integer,
        comment="Section unique identifier (SectionId) - requires SectionType translator",
    )
    secao_nome = Column(
        Text, comment="Section description (Section) - derived from SectionType enum"
    )
    tema_id = Column(
        Integer,
        comment="Theme unique identifier (ThemeId) - requires ThemeType translator",
    )
    tema_nome = Column(
        Text, comment="Theme description (Theme) - derived from ThemeType enum"
    )
    grupo_parlamentar = Column(
        Text,
        comment="Parliamentary group ID (ParlamentGroup) - when associated with event",
    )
    data_evento = Column(
        Date,
        nullable=False,
        comment="Event start date (EventStartDate) - when event occurs",
    )
    hora_inicio = Column(
        Text, comment="Event start time (EventStartTime) - local time format"
    )  # TIME field stored as TEXT
    hora_fim = Column(
        Text, comment="Event end time (EventEndTime) - local time format"
    )  # TIME field stored as TEXT
    evento_dia_inteiro = Column(
        Boolean,
        default=False,
        comment="Full day event indicator (AllDayEvent) - true if all day",
    )
    titulo = Column(
        Text, nullable=False, comment="Event title (Title) - main event name"
    )
    subtitulo = Column(
        Text, comment="Event subtitle (Subtitle) - additional event description"
    )
    descricao = Column(
        Text,
        comment="HTML encoded descriptive text (InternetText) - detailed event information",
    )
    local_evento = Column(
        Text, comment="Event location (Local) - where the event takes place"
    )
    link_externo = Column(
        Text, comment="Parliament website link (Link) - URL to event page if exists"
    )
    pos_plenario = Column(
        Boolean,
        default=False,
        comment="After plenary session indicator (PostPlenary) - occurs after plenary",
    )
    estado = Column(Text, default="agendado")

    # Additional documented fields from XV Legislature documentation
    order_value = Column(
        Integer,
        comment="Meeting/event order number (OrderValue) - sequence within agenda",
    )
    legislatura_designacao = Column(
        Text,
        comment="Legislature reference (LegDes) - which legislature event belongs to",
    )
    orgao_designacao = Column(
        Text, comment="Organ reference (OrgDes) - which organ event belongs to"
    )
    reuniao_numero = Column(
        Integer, comment="Meeting number (ReuNumero) - sequential meeting identifier"
    )
    sessao_numero = Column(
        Integer, comment="Legislative session number (SelNumero) - session reference"
    )

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    secao_parlamentar_id = Column(GUID(), ForeignKey("secoes_parlamentares.id"))
    tema_parlamentar_id = Column(GUID(), ForeignKey("temas_parlamentares.id"))

    # Relationships
    anexos = relationship(
        "AgendaParlamentarAnexo", back_populates="agenda", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_agenda_data", "data_evento"),
        Index("idx_agenda_legislatura_data", "legislatura_id", "data_evento"),
        # Index('idx_agenda_grupo', 'grupo_parlamentar'),  # Removed - TEXT column cannot be indexed without key length
        UniqueConstraint("id_externo", "legislatura_id"),
        ForeignKeyConstraint(["legislatura_id"], ["legislaturas.id"]),
    )


class AgendaParlamentarAnexo(Base):
    """
    Parliamentary Agenda Attachments Container
    =========================================

    Container for agenda event attachments from AgendaParlamentar.xml/.json.
    Based on official Portuguese Parliament documentation (June 2023):
    "AnexoEventos" structure from XV_Legislatura documentation.

    MAPPED STRUCTURES (from official documentation):

    1. **AnexoEventos** - Document associated with agenda event
       - idField: Document unique identifier (id_field)
       - tipoDocumentoField: Document type (tipo_documento_field)
       - tituloField: Document title (titulo_field) - required
       - uRLField: Parliament website document link (url_field)

    2. **Attachment Types** - Based on parent structure
       - AnexosComissaoPermanente: Permanent committee attachments
       - AnexosPlenario: Plenary session attachments

    Note: Documents provide supplementary information for agenda events,
    typically including meeting agendas, reports, and supporting materials.
    """

    __tablename__ = "agenda_parlamentar_anexos"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    agenda_id = Column(GUID(), ForeignKey("agenda_parlamentar.id"), nullable=False)

    # AnexoEventos fields from XV Legislature documentation
    id_field = Column(
        Text, comment="Document unique identifier (idField) - external document ID"
    )
    tipo_documento_field = Column(
        Text, comment="Document type (tipoDocumentoField) - classification of document"
    )
    titulo_field = Column(
        Text,
        nullable=False,
        comment="Document title (tituloField) - descriptive name of document",
    )
    url_field = Column(
        Text,
        comment="Parliament website document link (uRLField) - URL to access document",
    )
    tipo_anexo = Column(
        String(100),
        comment="Attachment type - 'comissao_permanente' or 'plenario' based on parent structure",
    )

    created_at = Column(DateTime, default=func.now())

    # Relationships
    agenda = relationship("AgendaParlamentar", back_populates="anexos")

    __table_args__ = (
        Index("idx_agenda_anexo_agenda", "agenda_id"),
        Index("idx_agenda_anexo_tipo", "tipo_anexo"),
    )


# =====================================================
# PARLIAMENTARY ORGANIZATION STRUCTURE (OrganizacaoAR)
# =====================================================

"""
PARLIAMENTARY ORGANIZATION MODELS - FIELD DOCUMENTATION
========================================================

Based on official Portuguese Parliament documentation for OrgaoComposicao*.xml files.
Documentation is identical across all legislatures (Constituinte through XIII_Legislatura).

MAIN ORGANIZATIONAL STRUCTURE:
- OrganizacaoAR: Root container for all parliamentary organizational data
- Contains hierarchical structure of parliamentary bodies:
  * ConselhoAdministracao (Administrative Council)
  * ConferenciaLideres (Leaders Conference) 
  * ConferenciaPresidentesComissoes (Commission Presidents Conference)
  * MesaAR (Assembly Board)
  * Comissoes (Commissions)
  * SubComissoes (Sub-committees)
  * GruposTrabalho (Work Groups)
  * ComissaoPermanente (Permanent Committee)
  * Plenario (Plenary)

ORGAN DETAIL STRUCTURE (DetalheOrgao):
- idOrgao: Unique organ identifier (integer)
- siglaOrgao: Organ acronym/abbreviation (string)
- nomeSigla: Full organ name or description (string)
- numeroOrgao: Sequential organ number (integer)
- siglaLegislatura: Legislature designation (string)

COMPOSITION DATA (Composicao/HistoricoComposicao):
- depId: Deputy ID within legislature (integer)
- depCadId: Deputy registration/cadastral ID - unique person identifier (integer)
- depNomeParlamentar: Deputy's parliamentary name (string)
- depNomeCompleto: Deputy's full civil name (string)
- orgId: Associated organ ID (integer)
- legDes: Legislature designation (string)

PARLIAMENTARY GROUP DATA (DadosSituacaoGP):
- gpId: Parliamentary group ID (integer)
- gpSigla: Parliamentary group acronym (string)
- gpDtInicio: Group membership start date (date)
- gpDtFim: Group membership end date (date)

DEPUTY SITUATION DATA (DadosSituacaoDeputado):
- sioDes: Situation description (effective/substitute/etc.) (string)
- sioDtInicio: Situation start date (date)
- sioDtFim: Situation end date (date)

CARGO/POSITION DATA (for committees):
- carId: Position/role ID (integer)
- carDes: Position/role description (string)
- dtInicio: Position start date (date)
- dtFim: Position end date (date)

REUNIAO/MEETING DATA:
- reuId: Meeting ID (integer)
- reuData: Meeting date (date)
- reuHora: Meeting time (time)
- reuSumario: Meeting summary (text)
- reuTipoReuniao: Meeting type (string)
- reuLocal: Meeting location (string)
- reuObservacoes: Meeting observations (text)

MEETING ATTENDANCE:
- depId: Deputy ID (integer)
- depCadId: Deputy cadastral ID (integer)
- depNomeParlamentar: Deputy parliamentary name (string)
- depNomeCompleto: Deputy full name (string)
- depPresente: Attendance status (boolean)
- depJustificacao: Absence justification (string)
- depMotivoFalta: Reason for absence (string)

VIDEO DATA:
- videoId: Video identifier (string)
- videoURL: Video URL (string)
- videoDataPublicacao: Video publication date (date)
- videoTitulo: Video title (string)
- videoDescricao: Video description (text)

Source: Official Parliament documentation - identical across all legislatures
"""


class ParliamentaryOrganization(Base):
    """
    Root parliamentary organization container (OrganizacaoAR)

    Contains all parliamentary bodies for a given legislature.
    Maps to OrganizacaoAR root element in XML files.
    """

    __tablename__ = "parliamentary_organizations"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    legislatura_sigla = Column(String(20), nullable=False)  # Legislature designation
    xml_file_path = Column(String(500))  # Source XML file path
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    administrative_councils = relationship(
        "AdministrativeCouncil",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    leader_conferences = relationship(
        "LeaderConference", back_populates="organization", cascade="all, delete-orphan"
    )
    commission_president_conferences = relationship(
        "CommissionPresidentConference",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    plenaries = relationship(
        "Plenary", back_populates="organization", cascade="all, delete-orphan"
    )
    ar_boards = relationship(
        "ARBoard", back_populates="organization", cascade="all, delete-orphan"
    )
    commissions = relationship(
        "Commission", back_populates="organization", cascade="all, delete-orphan"
    )
    work_groups = relationship(
        "WorkGroup", back_populates="organization", cascade="all, delete-orphan"
    )
    permanent_committees = relationship(
        "PermanentCommittee",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    sub_committees = relationship(
        "SubCommittee", back_populates="organization", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_parliamentary_organizations_legislatura", "legislatura_sigla"),
    )


class AdministrativeCouncil(Base):
    """
    Administrative Council (ConselhoAdministracao)

    Parliamentary body responsible for administrative oversight.
    Contains organ details and historical composition data.
    """

    __tablename__ = "administrative_councils"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        GUID(), ForeignKey("parliamentary_organizations.id"), nullable=False
    )
    id_orgao = Column(Integer)  # Unique organ identifier from XML
    sigla_orgao = Column(String(50))  # Organ acronym/abbreviation
    nome_sigla = Column(String(500))  # Full organ name or description
    numero_orgao = Column(Integer)  # Sequential organ number
    sigla_legislatura = Column(String(20))  # Legislature designation
    created_at = Column(DateTime, default=func.now())

    organization = relationship(
        "ParliamentaryOrganization", back_populates="administrative_councils"
    )
    historical_compositions = relationship(
        "AdministrativeCouncilHistoricalComposition",
        back_populates="council",
        cascade="all, delete-orphan",
    )


class LeaderConference(Base):
    """
    Leader Conference (ConferenciaLideres)

    Parliamentary body comprising party leaders for coordination.
    Contains organ details and historical composition data.
    """

    __tablename__ = "leader_conferences"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        GUID(), ForeignKey("parliamentary_organizations.id"), nullable=False
    )
    id_orgao = Column(Integer)  # Unique organ identifier from XML
    sigla_orgao = Column(String(50))  # Organ acronym/abbreviation
    nome_sigla = Column(String(500))  # Full organ name or description
    numero_orgao = Column(Integer)  # Sequential organ number
    sigla_legislatura = Column(String(20))  # Legislature designation
    created_at = Column(DateTime, default=func.now())

    organization = relationship(
        "ParliamentaryOrganization", back_populates="leader_conferences"
    )
    historical_compositions = relationship(
        "LeaderConferenceHistoricalComposition",
        back_populates="conference",
        cascade="all, delete-orphan",
    )


class CommissionPresidentConference(Base):
    """
    Commission President Conference (ConferenciaPresidentesComissoes)

    Parliamentary body comprising committee chairs for coordination.
    Contains organ details and historical composition data.
    """

    __tablename__ = "commission_president_conferences"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        GUID(), ForeignKey("parliamentary_organizations.id"), nullable=False
    )
    id_orgao = Column(Integer)  # Unique organ identifier from XML
    sigla_orgao = Column(String(50))  # Organ acronym/abbreviation
    nome_sigla = Column(String(500))  # Full organ name or description
    numero_orgao = Column(Integer)  # Sequential organ number
    sigla_legislatura = Column(String(20))  # Legislature designation
    created_at = Column(DateTime, default=func.now())

    organization = relationship(
        "ParliamentaryOrganization", back_populates="commission_president_conferences"
    )
    historical_compositions = relationship(
        "CommissionPresidentConferenceHistoricalComposition",
        back_populates="conference",
        cascade="all, delete-orphan",
    )


class Plenary(Base):
    __tablename__ = "plenaries"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        GUID(), ForeignKey("parliamentary_organizations.id"), nullable=False
    )
    id_orgao = Column(Integer)
    sigla_orgao = Column(String(50))
    nome_sigla = Column(String(500))
    numero_orgao = Column(Integer)
    sigla_legislatura = Column(String(20))
    created_at = Column(DateTime, default=func.now())

    organization = relationship("ParliamentaryOrganization", back_populates="plenaries")
    compositions = relationship(
        "PlenaryComposition", back_populates="plenary", cascade="all, delete-orphan"
    )


class ARBoard(Base):
    __tablename__ = "ar_boards"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        GUID(), ForeignKey("parliamentary_organizations.id"), nullable=False
    )
    id_orgao = Column(Integer)
    sigla_orgao = Column(String(50))
    nome_sigla = Column(String(500))
    numero_orgao = Column(Integer)
    sigla_legislatura = Column(String(20))
    created_at = Column(DateTime, default=func.now())

    organization = relationship("ParliamentaryOrganization", back_populates="ar_boards")
    historical_compositions = relationship(
        "ARBoardHistoricalComposition",
        back_populates="board",
        cascade="all, delete-orphan",
    )


class Commission(Base):
    __tablename__ = "commissions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        GUID(), ForeignKey("parliamentary_organizations.id"), nullable=False
    )
    id_orgao = Column(Integer)
    sigla_orgao = Column(String(50))
    nome_sigla = Column(String(500))
    numero_orgao = Column(Integer)
    sigla_legislatura = Column(String(20))
    created_at = Column(DateTime, default=func.now())

    organization = relationship(
        "ParliamentaryOrganization", back_populates="commissions"
    )
    historical_compositions = relationship(
        "CommissionHistoricalComposition",
        back_populates="commission",
        cascade="all, delete-orphan",
    )
    meetings = relationship(
        "OrganMeeting", back_populates="commission", cascade="all, delete-orphan"
    )


class WorkGroup(Base):
    __tablename__ = "work_groups"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        GUID(), ForeignKey("parliamentary_organizations.id"), nullable=False
    )
    id_orgao = Column(Integer)
    sigla_orgao = Column(String(50))
    nome_sigla = Column(String(500))
    numero_orgao = Column(Integer)
    sigla_legislatura = Column(String(20))
    created_at = Column(DateTime, default=func.now())

    organization = relationship(
        "ParliamentaryOrganization", back_populates="work_groups"
    )
    historical_compositions = relationship(
        "WorkGroupHistoricalComposition",
        back_populates="work_group",
        cascade="all, delete-orphan",
    )
    meetings = relationship(
        "OrganMeeting", back_populates="work_group", cascade="all, delete-orphan"
    )


class PermanentCommittee(Base):
    __tablename__ = "permanent_committees"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        GUID(), ForeignKey("parliamentary_organizations.id"), nullable=False
    )
    id_orgao = Column(Integer)
    sigla_orgao = Column(String(50))
    nome_sigla = Column(String(500))
    numero_orgao = Column(Integer)
    sigla_legislatura = Column(String(20))
    created_at = Column(DateTime, default=func.now())

    organization = relationship(
        "ParliamentaryOrganization", back_populates="permanent_committees"
    )
    historical_compositions = relationship(
        "PermanentCommitteeHistoricalComposition",
        back_populates="permanent_committee",
        cascade="all, delete-orphan",
    )
    meetings = relationship(
        "OrganMeeting",
        back_populates="permanent_committee",
        cascade="all, delete-orphan",
    )


class SubCommittee(Base):
    __tablename__ = "sub_committees"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        GUID(), ForeignKey("parliamentary_organizations.id"), nullable=False
    )
    id_orgao = Column(Integer)
    sigla_orgao = Column(String(50))
    nome_sigla = Column(String(500))
    numero_orgao = Column(Integer)
    sigla_legislatura = Column(String(20))
    created_at = Column(DateTime, default=func.now())

    organization = relationship(
        "ParliamentaryOrganization", back_populates="sub_committees"
    )
    historical_compositions = relationship(
        "SubCommitteeHistoricalComposition",
        back_populates="sub_committee",
        cascade="all, delete-orphan",
    )
    meetings = relationship(
        "OrganMeeting", back_populates="sub_committee", cascade="all, delete-orphan"
    )


# Meeting Model (shared by all organ types)
class OrganMeeting(Base):
    __tablename__ = "organ_meetings"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Foreign keys to different organ types
    commission_id = Column(GUID(), ForeignKey("commissions.id"))
    work_group_id = Column(GUID(), ForeignKey("work_groups.id"))
    permanent_committee_id = Column(GUID(), ForeignKey("permanent_committees.id"))
    sub_committee_id = Column(GUID(), ForeignKey("sub_committees.id"))

    # Meeting data
    reu_tar_sigla = Column(
        String(50)
    )  # Increased from 20 to handle longer meeting type descriptions
    reu_local = Column(String(200))
    reu_data = Column(Date)
    reu_hora = Column(String(10))
    reu_tipo = Column(String(100))
    reu_estado = Column(String(50))

    # Extended meeting fields (III Legislature)
    reu_id = Column(Integer)  # Meeting ID from XML
    reu_numero = Column(Integer)  # Meeting number
    reu_data_hora = Column(String(50))  # Combined date/time string
    reu_final_plenario = Column(Boolean)  # Final plenary indicator
    reu_tir_des = Column(String(200))  # Meeting type description
    leg_des = Column(String(50))  # Legislature description
    sel_numero = Column(String(50))  # Session number

    created_at = Column(DateTime, default=func.now())

    # Relationships
    commission = relationship("Commission", back_populates="meetings")
    work_group = relationship("WorkGroup", back_populates="meetings")
    permanent_committee = relationship("PermanentCommittee", back_populates="meetings")
    sub_committee = relationship("SubCommittee", back_populates="meetings")
    attendances = relationship(
        "MeetingAttendance", back_populates="meeting", cascade="all, delete-orphan"
    )


class MeetingAttendance(Base):
    """Meeting attendance data (Presencas) - tracks deputy attendance at meetings"""

    __tablename__ = "meeting_attendances"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(GUID(), ForeignKey("organ_meetings.id"), nullable=False)

    # Deputy information
    dep_id = Column(Integer)
    dep_cad_id = Column(Integer)
    dep_nome_parlamentar = Column(String(200))

    # Attendance details
    pres_tipo = Column(String(50))  # Presence type (present, absent, etc.)
    pres_justificacao = Column(Text)  # Justification for absence
    dt_reuniao = Column(Date)  # Meeting date for this attendance record
    tipo_reuniao = Column(String(100))  # Type of meeting
    # Structured attendance quality fields
    sigla_qualidade_presenca = Column(String(100))  # Presence quality designation
    sigla_grupo = Column(String(50))  # Group designation if applicable
    sigla_falta = Column(String(50))  # Absence designation if applicable
    motivo_falta = Column(Text)  # Reason for absence - XIII Legislature
    observacoes = Column(Text)  # Additional free-text observations

    created_at = Column(DateTime, default=func.now())

    # Relationships
    meeting = relationship("OrganMeeting", back_populates="attendances")


class DeputyVideo(Base):
    """Deputy video data - stores video links associated with deputies"""

    __tablename__ = "deputy_videos"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Deputy information
    dep_id = Column(Integer)
    dep_cad_id = Column(Integer)
    dep_nome_parlamentar = Column(String(200))

    # Video details
    url = Column(Text)  # Video URL
    tipo = Column(String(100))  # Video type/category

    # Context - which organ/composition this video is associated with
    organ_type = Column(String(50))  # Type of organ (Plenario, Commission, etc.)
    organ_id = Column(Integer)  # ID of the specific organ
    legislatura_numero = Column(String(20))  # Legislature designation

    created_at = Column(DateTime, default=func.now())


# Historical Composition Models
class AdministrativeCouncilHistoricalComposition(Base):
    """
    Administrative Council Historical Composition (HistoricoComposicao)

    Records of deputies who served on the Administrative Council over time.
    Contains deputy identification and parliamentary group/situation data.
    """

    __tablename__ = "administrative_council_historical_compositions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    council_id = Column(
        GUID(), ForeignKey("administrative_councils.id"), nullable=False
    )
    leg_des = Column(String(20))  # Legislature designation
    dep_id = Column(Integer)  # Deputy ID within legislature
    dep_cad_id = Column(Integer)  # Deputy cadastral ID (unique person identifier)
    dep_nome_parlamentar = Column(String(200))  # Deputy's parliamentary name
    dep_nome_completo = Column(String(200))  # Deputy's full civil name
    org_id = Column(Integer)  # Associated organ ID
    created_at = Column(DateTime, default=func.now())

    council = relationship(
        "AdministrativeCouncil", back_populates="historical_compositions"
    )
    gp_situations = relationship(
        "OrganCompositionGPSituation",
        back_populates="admin_council_composition",
        cascade="all, delete-orphan",
    )
    deputy_positions = relationship(
        "OrganCompositionDeputyPosition",
        back_populates="admin_council_composition",
        cascade="all, delete-orphan",
    )
    deputy_situations = relationship(
        "OrganCompositionDeputySituation",
        back_populates="admin_council_composition",
        cascade="all, delete-orphan",
    )


class LeaderConferenceHistoricalComposition(Base):
    __tablename__ = "leader_conference_historical_compositions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    conference_id = Column(GUID(), ForeignKey("leader_conferences.id"), nullable=False)
    leg_des = Column(String(20))
    dep_id = Column(Integer)
    dep_cad_id = Column(Integer)
    dep_nome_parlamentar = Column(String(200))
    dep_nome_completo = Column(String(200))
    org_id = Column(Integer)
    created_at = Column(DateTime, default=func.now())

    conference = relationship(
        "LeaderConference", back_populates="historical_compositions"
    )
    gp_situations = relationship(
        "OrganCompositionGPSituation",
        back_populates="leader_conference_composition",
        cascade="all, delete-orphan",
    )
    deputy_positions = relationship(
        "OrganCompositionDeputyPosition",
        back_populates="leader_conference_composition",
        cascade="all, delete-orphan",
    )
    deputy_situations = relationship(
        "OrganCompositionDeputySituation",
        back_populates="leader_conference_composition",
        cascade="all, delete-orphan",
    )


class CommissionPresidentConferenceHistoricalComposition(Base):
    __tablename__ = "commission_president_conference_historical_compositions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    conference_id = Column(
        GUID(), ForeignKey("commission_president_conferences.id"), nullable=False
    )
    leg_des = Column(String(20))
    dep_id = Column(Integer)
    dep_cad_id = Column(Integer)
    dep_nome_parlamentar = Column(String(200))
    org_id = Column(Integer)
    created_at = Column(DateTime, default=func.now())

    conference = relationship(
        "CommissionPresidentConference", back_populates="historical_compositions"
    )
    gp_situations = relationship(
        "OrganCompositionGPSituation",
        back_populates="cpc_composition",
        cascade="all, delete-orphan",
    )
    deputy_positions = relationship(
        "OrganCompositionDeputyPosition",
        back_populates="cpc_composition",
        cascade="all, delete-orphan",
    )
    deputy_situations = relationship(
        "OrganCompositionDeputySituation",
        back_populates="cpc_composition",
        cascade="all, delete-orphan",
    )
    presidency_organs = relationship(
        "PresidencyOrgan",
        back_populates="cpc_composition",
        cascade="all, delete-orphan",
    )


class PlenaryComposition(Base):
    """
    Plenary Composition (Composicao)

    Records of all deputies who serve in the plenary session.
    Contains comprehensive deputy data including parliamentary group and situation information.
    """

    __tablename__ = "plenary_compositions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    plenary_id = Column(GUID(), ForeignKey("plenaries.id"), nullable=False)
    leg_des = Column(String(20))  # Legislature designation
    dep_id = Column(Integer)  # Deputy ID within legislature
    dep_cad_id = Column(Integer)  # Deputy cadastral ID (unique person identifier)
    dep_nome_parlamentar = Column(String(200))  # Deputy's parliamentary name
    dep_nome_completo = Column(String(300))  # Deputy's full civil name
    org_id = Column(Integer)  # Associated organ ID
    created_at = Column(DateTime, default=func.now())

    plenary = relationship("Plenary", back_populates="compositions")
    gp_situations = relationship(
        "OrganCompositionGPSituation",
        back_populates="plenary_composition",
        cascade="all, delete-orphan",
    )
    deputy_positions = relationship(
        "OrganCompositionDeputyPosition",
        back_populates="plenary_composition",
        cascade="all, delete-orphan",
    )
    deputy_situations = relationship(
        "OrganCompositionDeputySituation",
        back_populates="plenary_composition",
        cascade="all, delete-orphan",
    )


class ARBoardHistoricalComposition(Base):
    __tablename__ = "ar_board_historical_compositions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    board_id = Column(GUID(), ForeignKey("ar_boards.id"), nullable=False)
    leg_des = Column(String(20))
    dep_id = Column(Integer)
    dep_cad_id = Column(Integer)
    dep_nome_parlamentar = Column(String(200))
    dep_nome_completo = Column(String(200))  # IX Legislature field
    org_id = Column(Integer)
    created_at = Column(DateTime, default=func.now())

    board = relationship("ARBoard", back_populates="historical_compositions")
    gp_situations = relationship(
        "OrganCompositionGPSituation",
        back_populates="ar_board_composition",
        cascade="all, delete-orphan",
    )
    deputy_positions = relationship(
        "OrganCompositionDeputyPosition",
        back_populates="ar_board_composition",
        cascade="all, delete-orphan",
    )
    deputy_situations = relationship(
        "OrganCompositionDeputySituation",
        back_populates="ar_board_composition",
        cascade="all, delete-orphan",
    )


class CommissionHistoricalComposition(Base):
    __tablename__ = "commission_historical_compositions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    commission_id = Column(GUID(), ForeignKey("commissions.id"), nullable=False)
    leg_des = Column(String(20))
    dep_id = Column(Integer)
    dep_cad_id = Column(Integer)
    dep_nome_parlamentar = Column(String(200))
    dep_nome_completo = Column(String(200))  # IX Legislature field
    org_id = Column(Integer)
    created_at = Column(DateTime, default=func.now())

    commission = relationship("Commission", back_populates="historical_compositions")
    gp_situations = relationship(
        "OrganCompositionGPSituation",
        back_populates="commission_composition",
        cascade="all, delete-orphan",
    )
    deputy_positions = relationship(
        "OrganCompositionDeputyPosition",
        back_populates="commission_composition",
        cascade="all, delete-orphan",
    )
    deputy_situations = relationship(
        "OrganCompositionDeputySituation",
        back_populates="commission_composition",
        cascade="all, delete-orphan",
    )


class WorkGroupHistoricalComposition(Base):
    __tablename__ = "work_group_historical_compositions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    work_group_id = Column(GUID(), ForeignKey("work_groups.id"), nullable=False)
    leg_des = Column(String(20))
    dep_id = Column(Integer)
    dep_cad_id = Column(Integer)
    dep_nome_parlamentar = Column(String(200))
    dep_nome_completo = Column(String(200))  # VIII Legislature field
    org_id = Column(Integer)
    created_at = Column(DateTime, default=func.now())

    work_group = relationship("WorkGroup", back_populates="historical_compositions")
    gp_situations = relationship(
        "OrganCompositionGPSituation",
        back_populates="work_group_composition",
        cascade="all, delete-orphan",
    )
    deputy_positions = relationship(
        "OrganCompositionDeputyPosition",
        back_populates="work_group_composition",
        cascade="all, delete-orphan",
    )
    deputy_situations = relationship(
        "OrganCompositionDeputySituation",
        back_populates="work_group_composition",
        cascade="all, delete-orphan",
    )


class PermanentCommitteeHistoricalComposition(Base):
    __tablename__ = "permanent_committee_historical_compositions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    permanent_committee_id = Column(
        GUID(), ForeignKey("permanent_committees.id"), nullable=False
    )
    leg_des = Column(String(20))
    dep_id = Column(Integer)
    dep_cad_id = Column(Integer)
    dep_nome_parlamentar = Column(String(200))
    dep_nome_completo = Column(String(200))  # VI Legislature field
    org_id = Column(Integer)
    created_at = Column(DateTime, default=func.now())

    permanent_committee = relationship(
        "PermanentCommittee", back_populates="historical_compositions"
    )
    gp_situations = relationship(
        "OrganCompositionGPSituation",
        back_populates="permanent_committee_composition",
        cascade="all, delete-orphan",
    )
    deputy_positions = relationship(
        "OrganCompositionDeputyPosition",
        back_populates="permanent_committee_composition",
        cascade="all, delete-orphan",
    )
    deputy_situations = relationship(
        "OrganCompositionDeputySituation",
        back_populates="permanent_committee_composition",
        cascade="all, delete-orphan",
    )


class SubCommitteeHistoricalComposition(Base):
    __tablename__ = "sub_committee_historical_compositions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    sub_committee_id = Column(GUID(), ForeignKey("sub_committees.id"), nullable=False)
    leg_des = Column(String(20))
    dep_id = Column(Integer)
    dep_cad_id = Column(Integer)
    dep_nome_parlamentar = Column(String(200))
    dep_nome_completo = Column(String(200))  # IX Legislature field
    org_id = Column(Integer)
    created_at = Column(DateTime, default=func.now())

    sub_committee = relationship(
        "SubCommittee", back_populates="historical_compositions"
    )
    gp_situations = relationship(
        "OrganCompositionGPSituation",
        back_populates="sub_committee_composition",
        cascade="all, delete-orphan",
    )
    deputy_positions = relationship(
        "OrganCompositionDeputyPosition",
        back_populates="sub_committee_composition",
        cascade="all, delete-orphan",
    )
    deputy_situations = relationship(
        "OrganCompositionDeputySituation",
        back_populates="sub_committee_composition",
        cascade="all, delete-orphan",
    )


# Deputy Position and Situation Models
class OrganCompositionGPSituation(Base):
    __tablename__ = "organ_composition_gp_situations"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    admin_council_composition_id = Column(
        GUID(), ForeignKey("administrative_council_historical_compositions.id")
    )
    leader_conference_composition_id = Column(
        GUID(), ForeignKey("leader_conference_historical_compositions.id")
    )
    cpc_composition_id = Column(
        GUID(),
        ForeignKey("commission_president_conference_historical_compositions.id"),
    )
    plenary_composition_id = Column(GUID(), ForeignKey("plenary_compositions.id"))
    ar_board_composition_id = Column(
        GUID(), ForeignKey("ar_board_historical_compositions.id")
    )
    commission_composition_id = Column(
        GUID(), ForeignKey("commission_historical_compositions.id")
    )
    work_group_composition_id = Column(
        GUID(), ForeignKey("work_group_historical_compositions.id")
    )
    permanent_committee_composition_id = Column(
        GUID(), ForeignKey("permanent_committee_historical_compositions.id")
    )
    sub_committee_composition_id = Column(
        GUID(), ForeignKey("sub_committee_historical_compositions.id")
    )
    gp_id = Column(Integer)
    gp_sigla = Column(String(20))
    gp_dt_inicio = Column(Date)
    gp_dt_fim = Column(Date)
    created_at = Column(DateTime, default=func.now())

    admin_council_composition = relationship(
        "AdministrativeCouncilHistoricalComposition", back_populates="gp_situations"
    )
    leader_conference_composition = relationship(
        "LeaderConferenceHistoricalComposition", back_populates="gp_situations"
    )
    cpc_composition = relationship(
        "CommissionPresidentConferenceHistoricalComposition",
        back_populates="gp_situations",
    )
    plenary_composition = relationship(
        "PlenaryComposition", back_populates="gp_situations"
    )
    ar_board_composition = relationship(
        "ARBoardHistoricalComposition", back_populates="gp_situations"
    )
    commission_composition = relationship(
        "CommissionHistoricalComposition", back_populates="gp_situations"
    )
    work_group_composition = relationship(
        "WorkGroupHistoricalComposition", back_populates="gp_situations"
    )
    permanent_committee_composition = relationship(
        "PermanentCommitteeHistoricalComposition", back_populates="gp_situations"
    )
    sub_committee_composition = relationship(
        "SubCommitteeHistoricalComposition", back_populates="gp_situations"
    )


class OrganCompositionDeputyPosition(Base):
    __tablename__ = "organ_composition_deputy_positions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    admin_council_composition_id = Column(
        GUID(), ForeignKey("administrative_council_historical_compositions.id")
    )
    leader_conference_composition_id = Column(
        GUID(), ForeignKey("leader_conference_historical_compositions.id")
    )
    cpc_composition_id = Column(
        GUID(),
        ForeignKey("commission_president_conference_historical_compositions.id"),
    )
    plenary_composition_id = Column(GUID(), ForeignKey("plenary_compositions.id"))
    ar_board_composition_id = Column(
        GUID(), ForeignKey("ar_board_historical_compositions.id")
    )
    commission_composition_id = Column(
        GUID(), ForeignKey("commission_historical_compositions.id")
    )
    work_group_composition_id = Column(
        GUID(), ForeignKey("work_group_historical_compositions.id")
    )
    permanent_committee_composition_id = Column(
        GUID(), ForeignKey("permanent_committee_historical_compositions.id")
    )
    sub_committee_composition_id = Column(
        GUID(), ForeignKey("sub_committee_historical_compositions.id")
    )
    car_id = Column(Integer)
    car_des = Column(String(200))
    car_dt_inicio = Column(Date)
    car_dt_fim = Column(Date)
    created_at = Column(DateTime, default=func.now())

    admin_council_composition = relationship(
        "AdministrativeCouncilHistoricalComposition", back_populates="deputy_positions"
    )
    leader_conference_composition = relationship(
        "LeaderConferenceHistoricalComposition", back_populates="deputy_positions"
    )
    cpc_composition = relationship(
        "CommissionPresidentConferenceHistoricalComposition",
        back_populates="deputy_positions",
    )
    plenary_composition = relationship(
        "PlenaryComposition", back_populates="deputy_positions"
    )
    ar_board_composition = relationship(
        "ARBoardHistoricalComposition", back_populates="deputy_positions"
    )
    commission_composition = relationship(
        "CommissionHistoricalComposition", back_populates="deputy_positions"
    )
    work_group_composition = relationship(
        "WorkGroupHistoricalComposition", back_populates="deputy_positions"
    )
    permanent_committee_composition = relationship(
        "PermanentCommitteeHistoricalComposition", back_populates="deputy_positions"
    )
    sub_committee_composition = relationship(
        "SubCommitteeHistoricalComposition", back_populates="deputy_positions"
    )


class OrganCompositionDeputySituation(Base):
    __tablename__ = "organ_composition_deputy_situations"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    admin_council_composition_id = Column(
        GUID(), ForeignKey("administrative_council_historical_compositions.id")
    )
    leader_conference_composition_id = Column(
        GUID(), ForeignKey("leader_conference_historical_compositions.id")
    )
    cpc_composition_id = Column(
        GUID(),
        ForeignKey("commission_president_conference_historical_compositions.id"),
    )
    plenary_composition_id = Column(GUID(), ForeignKey("plenary_compositions.id"))
    ar_board_composition_id = Column(
        GUID(), ForeignKey("ar_board_historical_compositions.id")
    )
    commission_composition_id = Column(
        GUID(), ForeignKey("commission_historical_compositions.id")
    )
    work_group_composition_id = Column(
        GUID(), ForeignKey("work_group_historical_compositions.id")
    )
    permanent_committee_composition_id = Column(
        GUID(), ForeignKey("permanent_committee_historical_compositions.id")
    )
    sub_committee_composition_id = Column(
        GUID(), ForeignKey("sub_committee_historical_compositions.id")
    )
    sio_des = Column(String(200))
    sio_tip_mem = Column(String(100))
    sio_dt_inicio = Column(Date)
    sio_dt_fim = Column(Date)
    created_at = Column(DateTime, default=func.now())

    admin_council_composition = relationship(
        "AdministrativeCouncilHistoricalComposition", back_populates="deputy_situations"
    )
    leader_conference_composition = relationship(
        "LeaderConferenceHistoricalComposition", back_populates="deputy_situations"
    )
    cpc_composition = relationship(
        "CommissionPresidentConferenceHistoricalComposition",
        back_populates="deputy_situations",
    )
    plenary_composition = relationship(
        "PlenaryComposition", back_populates="deputy_situations"
    )
    ar_board_composition = relationship(
        "ARBoardHistoricalComposition", back_populates="deputy_situations"
    )
    commission_composition = relationship(
        "CommissionHistoricalComposition", back_populates="deputy_situations"
    )
    work_group_composition = relationship(
        "WorkGroupHistoricalComposition", back_populates="deputy_situations"
    )
    permanent_committee_composition = relationship(
        "PermanentCommitteeHistoricalComposition", back_populates="deputy_situations"
    )
    sub_committee_composition = relationship(
        "SubCommitteeHistoricalComposition", back_populates="deputy_situations"
    )


# Commission Presidency Models
class PresidencyOrgan(Base):
    __tablename__ = "presidency_organs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    cpc_composition_id = Column(
        GUID(),
        ForeignKey("commission_president_conference_historical_compositions.id"),
        nullable=False,
    )
    org_id = Column(Integer)
    org_numero = Column(Integer)
    org_sigla = Column(String(20))
    org_des = Column(String(200))
    created_at = Column(DateTime, default=func.now())

    cpc_composition = relationship(
        "CommissionPresidentConferenceHistoricalComposition",
        back_populates="presidency_organs",
    )
    commission_presidencies = relationship(
        "CommissionPresidency",
        back_populates="presidency_organ",
        cascade="all, delete-orphan",
    )


class CommissionPresidency(Base):
    __tablename__ = "commission_presidencies"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    presidency_organ_id = Column(
        GUID(), ForeignKey("presidency_organs.id"), nullable=False
    )
    pec_id = Column(Integer)
    pec_tia_des = Column(String(200))
    pec_dt_inicio = Column(Date)
    pec_dt_fim = Column(Date)
    created_at = Column(DateTime, default=func.now())

    presidency_organ = relationship(
        "PresidencyOrgan", back_populates="commission_presidencies"
    )


# =====================================================
# IMPORT TRACKING
# =====================================================


class ImportStatus(Base):
    __tablename__ = "import_status"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    file_url = Column(String(1000), nullable=False)
    file_path = Column(String(500))
    file_name = Column(String(200), nullable=False)
    file_type = Column(String(20), nullable=False)  # 'JSON', 'XML', 'PDF', 'Archive'
    category = Column(String(100), nullable=False)
    legislatura = Column(String(20))
    sub_series = Column(String(100))  # For DAR files
    session = Column(String(50))  # For DAR files
    number = Column(String(50))  # For DAR files
    file_hash = Column(String(64))  # SHA1 hash of file content
    file_size = Column(Integer)
    
    # New fields for HTTP metadata and change detection
    last_modified = Column(DateTime, comment="Server Last-Modified header timestamp")
    content_length = Column(Integer, comment="Server Content-Length header value")
    etag = Column(String(200), comment="Server ETag header for change detection")
    discovered_at = Column(DateTime, comment="When this file URL was first discovered")
    
    # Additional discovery metadata for debugging and URL refresh
    source_page_url = Column(String(1000), comment="URL of the page where the link was found")
    anchor_text = Column(String(500), comment="Text content of the link anchor element")
    url_pattern = Column(String(200), comment="Heuristic pattern for URL token refresh (e.g., doc.xml?path=...&fich=...)")
    navigation_context = Column(String(1000), comment="Navigation hierarchy path for debugging (e.g., 'section > subsection > item')")
    
    status = Column(
        String(50), nullable=False, default="pending"
    )  # 'discovered', 'download_pending', 'downloading', 'pending', 'processing', 'completed', 'failed', 'recrawl', 'import_error', 'schema_mismatch', 'skipped'
    schema_issues = Column(Text)  # JSON array of schema validation issues
    processing_started_at = Column(DateTime)
    processing_completed_at = Column(DateTime)
    error_message = Column(Text)
    records_imported = Column(Integer, default=0)
    processing_duration_seconds = Column(Float, comment="Time taken to process the file in seconds")

    # Error tracking and retry counters
    recrawl_count = Column(Integer, default=0, comment="Number of times URL has been recrawled")
    error_count = Column(Integer, default=0, comment="Number of import errors encountered")
    retry_at = Column(DateTime, comment="Scheduled retry time for failed imports with exponential backoff")
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        # Unique constraint on logical file identity - prevents duplicates even with changing URLs
        # The parliament uses token-based URLs that change between sessions, so we identify files
        # by their (file_name, category, legislatura) combination instead of URL
        UniqueConstraint(
            "file_name", "category", "legislatura",
            name="uq_import_status_file_identity"
        ),
        # Index('idx_import_status_url', 'file_url'),  # Removed - VARCHAR(1000) too long for MySQL index
        Index("idx_import_status_hash", "file_hash"),
        Index("idx_import_status_status", "status"),
        Index("idx_import_status_category", "category"),
        Index("idx_import_status_legislatura", "legislatura"),
    )


# AtividadeDeputado Models for Deputy Activity Data


class AtividadeDeputado(Base):
    """
    Deputy Activities Root Container
    ===============================

    Root container for all activities performed by a deputy during their mandate.
    Based on official Portuguese Parliament documentation (December 2017):
    "AtividadeDeputado<Legislatura>.xml"

    This model represents the top-level structure containing information about
    deputy activities such as initiatives presented, questions and requirements
    submitted, committee appointments, parliamentary interventions, and other
    parliamentary activities performed during their mandate.

    Structure: ArrayOfAtividadeDeputado.AtividadeDeputado

    Related Documentation Fields:
    - Contains: AtividadeDeputadoList (list of deputy activities)
    - Contains: Deputado (deputy information via DadosDeputadoSearch)
    """

    __tablename__ = "atividade_deputados"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Core deputy reference
    deputado_id = Column(
        GUID(),
        ForeignKey("deputados.id"),
        nullable=False,
        comment="Reference to the deputy this activity record belongs to",
    )

    # Official Parliament fields from documentation
    dep_cad_id = Column(
        Integer, comment="Deputy's cadastral identifier (DepCadId) - unique registry ID"
    )
    leg_des = Column(
        String(20),
        comment="Legislature designation (LegDes) - which legislature this activity pertains to",
    )

    # System tracking
    created_at = Column(
        DateTime, default=func.now(), comment="Record creation timestamp"
    )

    # Relationships - following official documentation structure
    deputado = relationship(
        "Deputado",
        back_populates="atividades",
        doc="Deputy who performed these activities",
    )

    atividade_list = relationship(
        "AtividadeDeputadoList",
        back_populates="atividade_deputado",
        cascade="all, delete-orphan",
        doc="List of deputy activities (AtividadeDeputadoList structure)",
    )

    deputado_situacoes = relationship(
        "DeputadoSituacao",
        back_populates="atividade_deputado",
        cascade="all, delete-orphan",
        doc="Deputy status/situation records",
    )

    initiatives = relationship(
        "DeputyInitiative",
        back_populates="deputy_activity",
        cascade="all, delete-orphan",
        doc="Initiatives presented by the deputy (IniciativasOut)",
    )

    # interventions relationship removed - DeputyIntervention model unused

    # reports relationship removed - DeputyReport model unused

    # parliamentary_activities relationship removed - DeputyParliamentaryActivity model unused

    # legislative_data relationship removed - DeputyLegislativeData model unused

    # Indexes for performance optimization
    __table_args__ = (
        Index("idx_atividade_deputado_id", "deputado_id"),
        Index("idx_atividade_dep_cad_id", "dep_cad_id"),
        Index("idx_atividade_leg_des", "leg_des"),
        Index("idx_atividade_deputado_leg_composite", "deputado_id", "leg_des"),
    )


class AtividadeDeputadoList(Base):
    """
    Deputy Activity List Container
    =============================

    Container for the detailed list of deputy activities represented by the
    ActividadeOut structure. Based on official Portuguese Parliament documentation:

    Structure: ArrayOfAtividadeDeputado.AtividadeDeputado.AtividadeDeputadoList

    This model serves as the bridge between the deputy root record and the
    detailed activity data (ActividadeOut), which contains all the specific
    activities like initiatives, requirements, committee memberships, etc.

    Documentation Reference:
    - AtividadeDeputadoList: "Lista de atividades do deputado representadas por estrutura ActividadeOut"
    """

    __tablename__ = "atividade_deputado_lists"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Parent reference
    atividade_deputado_id = Column(
        GUID(),
        ForeignKey("atividade_deputados.id"),
        nullable=False,
        comment="Reference to parent AtividadeDeputado record",
    )

    # System tracking
    created_at = Column(
        DateTime, default=func.now(), comment="Record creation timestamp"
    )

    # Relationships following official documentation structure
    atividade_deputado = relationship(
        "AtividadeDeputado",
        back_populates="atividade_list",
        doc="Parent deputy activity record",
    )

    actividade_outs = relationship(
        "ActividadeOut",
        back_populates="atividade_list",
        cascade="all, delete-orphan",
        doc="Detailed activity data (ActividadeOut structure)",
    )


class ActividadeOut(Base):
    __tablename__ = "actividade_outs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    atividade_list_id = Column(
        GUID(), ForeignKey("atividade_deputado_lists.id"), nullable=False
    )
    rel = Column(Text)  # Rel field - appears to be empty in the XML
    created_at = Column(DateTime, default=func.now())

    atividade_list = relationship(
        "AtividadeDeputadoList", back_populates="actividade_outs"
    )
    dados_legis_deputados = relationship(
        "DadosLegisDeputado",
        back_populates="actividade_out",
        cascade="all, delete-orphan",
    )
    audiencias = relationship(
        "ActividadeAudiencia",
        back_populates="actividade_out",
        cascade="all, delete-orphan",
    )
    audicoes = relationship(
        "ActividadeAudicao",
        back_populates="actividade_out",
        cascade="all, delete-orphan",
    )
    intervencoes = relationship(
        "ActividadeIntervencao",
        back_populates="actividade_out",
        cascade="all, delete-orphan",
    )

    # IX Legislature relationships
    atividades_parlamentares = relationship(
        "ActividadesParlamentares",
        back_populates="actividade_out",
        cascade="all, delete-orphan",
    )
    grupos_parlamentares_amizade = relationship(
        "GruposParlamentaresAmizade",
        back_populates="actividade_out",
        cascade="all, delete-orphan",
    )
    delegacoes_permanentes = relationship(
        "DelegacoesPermanentes",
        back_populates="actividade_out",
        cascade="all, delete-orphan",
    )
    delegacoes_eventuais = relationship(
        "DelegacoesEventuais",
        back_populates="actividade_out",
        cascade="all, delete-orphan",
    )
    requerimentos_ativ_dep = relationship(
        "RequerimentosAtivDep",
        back_populates="actividade_out",
        cascade="all, delete-orphan",
    )
    subcomissoes_grupos_trabalho = relationship(
        "SubComissoesGruposTrabalho",
        back_populates="actividade_out",
        cascade="all, delete-orphan",
    )
    relatores_peticoes = relationship(
        "RelatoresPeticoes",
        back_populates="actividade_out",
        cascade="all, delete-orphan",
    )
    relatores_iniciativas = relationship(
        "RelatoresIniciativas",
        back_populates="actividade_out",
        cascade="all, delete-orphan",
    )
    comissoes = relationship(
        "Comissoes", back_populates="actividade_out", cascade="all, delete-orphan"
    )

    # I Legislature relationships
    autores_pareceres_inc_imu = relationship(
        "AutoresPareceresIncImu",
        back_populates="actividade_out",
        cascade="all, delete-orphan",
    )
    relatores_ini_europeias = relationship(
        "RelatoresIniEuropeias",
        back_populates="actividade_out",
        cascade="all, delete-orphan",
    )
    parlamento_jovens = relationship(
        "ParlamentoJovens",
        back_populates="actividade_out",
        cascade="all, delete-orphan",
    )
    eventos = relationship(
        "Eventos", back_populates="actividade_out", cascade="all, delete-orphan"
    )


class DadosLegisDeputado(Base):
    __tablename__ = "dados_legis_deputados"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    actividade_out_id = Column(
        GUID(), ForeignKey("actividade_outs.id"), nullable=False
    )
    nome = Column(String(200))  # Nome field
    dpl_grpar = Column(String(100))  # Dpl_grpar field
    dpl_lg = Column(String(100))  # Dpl_lg field - NEW FIELD
    created_at = Column(DateTime, default=func.now())

    actividade_out = relationship(
        "ActividadeOut", back_populates="dados_legis_deputados"
    )


class ActividadeAudiencia(Base):
    """
    Activity Audience Association
    ============================

    Links activities to parliamentary audiences (formal hearings).
    Based on official Portuguese Parliament documentation (December 2017):
    "Audiencias" structure from VI_Legislatura documentation.

    This model represents the relationship between general activities and
    formal parliamentary audiences where external entities present to committees.

    MAPPED RELATIONSHIPS:
    - Links ActividadeOut to AudienciasParlamentares data
    - Enables committee activities to reference formal hearings
    """

    __tablename__ = "actividade_audiencias"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    actividade_out_id = Column(
        GUID(),
        ForeignKey("actividade_outs.id"),
        nullable=False,
        comment="Reference to general activity record",
    )
    created_at = Column(DateTime, default=func.now())

    actividade_out = relationship("ActividadeOut", back_populates="audiencias")
    actividades_comissao = relationship(
        "ActividadesComissaoOut",
        back_populates="audiencia",
        cascade="all, delete-orphan",
    )


class ActividadeAudicao(Base):
    """
    Activity Audition Association
    ============================

    Links activities to parliamentary auditions (hearings).
    Based on official Portuguese Parliament documentation (December 2017):
    "Audicoes" structure from VI_Legislatura documentation.

    This model represents the relationship between general activities and
    parliamentary auditions, which are committee hearings for specific purposes.

    MAPPED RELATIONSHIPS:
    - Links ActividadeOut to audition/hearing data
    - Enables committee activities to reference specific hearings

    Note: Audicoes (auditions) are distinct from Audiencias (formal audiences).
    """

    __tablename__ = "actividade_audicoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    actividade_out_id = Column(
        GUID(),
        ForeignKey("actividade_outs.id"),
        nullable=False,
        comment="Reference to general activity record",
    )
    created_at = Column(DateTime, default=func.now())

    actividade_out = relationship("ActividadeOut", back_populates="audicoes")
    actividades_comissao = relationship(
        "ActividadesComissaoOut", back_populates="audicao", cascade="all, delete-orphan"
    )


class ActividadesComissaoOut(Base):
    __tablename__ = "actividades_comissao_outs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    audiencia_id = Column(
        GUID(), ForeignKey("actividade_audiencias.id"), nullable=True
    )
    audicao_id = Column(GUID(), ForeignKey("actividade_audicoes.id"), nullable=True)
    evento_id = Column(
        GUID(), ForeignKey("eventos.id"), nullable=True
    )  # I Legislature Events
    deslocacao_id = Column(
        GUID(), ForeignKey("deslocacoes.id"), nullable=True
    )  # I Legislature Displacements

    # IX Legislature additional fields
    act_id = Column(Integer)  # ActId
    act_as = Column(Text)  # ActAs - subject/title
    act_dtent = Column(String(50))  # ActDtent - entry date
    acc_dtaud = Column(String(50))  # AccDtaud - hearing date
    act_tp = Column(String(10))  # ActTp - activity type
    act_tpdesc = Column(String(200))  # ActTpdesc - type description
    act_nr = Column(String(50))  # ActNr - activity number
    act_lg = Column(String(20))  # ActLg - legislature
    act_loc = Column(
        String(500)
    )  # ActLoc - activity location (I Legislature Events/Deslocacoes)
    act_dtdes1 = Column(String(50))  # ActDtdes1 - first displacement date
    act_dtdes2 = Column(String(50))  # ActDtdes2 - second displacement date
    act_dtent = Column(String(50))  # ActDtent - entry date (for Events section)
    act_tpdesc = Column(
        String(200)
    )  # ActTpdesc - activity type description (for Events)
    act_sl = Column(String(20))  # ActSl - session legislature
    tev_tp = Column(String(100))  # TevTp - event type
    nome_entidade_externa = Column(Text)  # NomeEntidadeExterna
    cms_no = Column(String(500))  # CmsNo - committee name
    cms_ab = Column(String(20))  # CmsAb - committee abbreviation

    created_at = Column(DateTime, default=func.now())

    audiencia = relationship(
        "ActividadeAudiencia", back_populates="actividades_comissao"
    )
    audicao = relationship("ActividadeAudicao", back_populates="actividades_comissao")
    evento = relationship("Eventos", back_populates="actividades_comissao")
    deslocacao = relationship("Deslocacoes", back_populates="actividades_comissao")


class ActividadeIntervencao(Base):
    __tablename__ = "actividade_intervencoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    actividade_out_id = Column(
        GUID(), ForeignKey("actividade_outs.id"), nullable=False
    )
    created_at = Column(DateTime, default=func.now())

    actividade_out = relationship("ActividadeOut", back_populates="intervencoes")
    intervencoes_out = relationship(
        "ActividadeIntervencaoOut",
        back_populates="actividade_intervencao",
        cascade="all, delete-orphan",
    )


class ActividadeIntervencaoOut(Base):
    __tablename__ = "actividade_intervencoes_out"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    actividade_intervencao_id = Column(
        GUID(), ForeignKey("actividade_intervencoes.id"), nullable=False
    )

    # IntervencoesOut fields from XML
    int_id = Column(Integer)  # IntId
    int_su = Column(Text)  # IntSu - Summary
    int_te = Column(Text)  # IntTe - Intervention Text
    pub_dar = Column(String(200))  # PubDar - Publication Diary
    pub_dtreu = Column(Date)  # PubDtreu - Publication Date
    pub_lg = Column(String(50))  # PubLg - Publication Legislature
    pub_nr = Column(Integer)  # PubNr - Publication Number
    pub_tp = Column(String(100))  # PubTp - Publication Type
    pub_sl = Column(String(200))  # PubSl - Publication Series/Supplement
    tin_ds = Column(String(200))  # TinDs - Intervention Type Description

    created_at = Column(DateTime, default=func.now())

    actividade_intervencao = relationship(
        "ActividadeIntervencao", back_populates="intervencoes_out"
    )


class DeputadoSituacao(Base):
    __tablename__ = "deputado_situacoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    atividade_deputado_id = Column(
        GUID(), ForeignKey("atividade_deputados.id"), nullable=False
    )
    created_at = Column(DateTime, default=func.now())

    atividade_deputado = relationship(
        "AtividadeDeputado", back_populates="deputado_situacoes"
    )
    dados_situacao = relationship(
        "DadosSituacaoDeputado",
        back_populates="deputado_situacao",
        cascade="all, delete-orphan",
    )


class DadosSituacaoDeputado(Base):
    """
    Deputy Situation Data - Based on InformacaoBase DadosSituacaoDeputado specification

    Contains deputy situational information with dates and descriptions.

    InformacaoBase Mapping (DadosSituacaoDeputado):
    - sioDes: sio_des (Situation description - e.g., "Efetivo", "Suplente")
    - sioDtInicio: sio_dt_inicio (Situation start date)
    - sioDtFim: sio_dt_fim (Situation end date)

    Usage:
        Nested within DepSituacao structure in InformacaoBase files
        Tracks deputy status changes over time within legislature
    """

    __tablename__ = "dados_situacao_deputados"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    deputado_situacao_id = Column(
        GUID(), ForeignKey("deputado_situacoes.id"), nullable=False
    )
    sio_des = Column(String(100), comment="Situation description (XML: sioDes)")
    sio_dt_inicio = Column(Date, comment="Situation start date (XML: sioDtInicio)")
    sio_dt_fim = Column(Date, comment="Situation end date (XML: sioDtFim)")
    created_at = Column(DateTime, default=func.now())

    deputado_situacao = relationship(
        "DeputadoSituacao", back_populates="dados_situacao"
    )



class DiplomaAprovado(Base):
    __tablename__ = "diplomas_aprovados"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    legislatura_id = Column(GUID(), ForeignKey("legislaturas.id"), nullable=False)

    # Core diploma fields
    diploma_id = Column(Integer, unique=True)  # External ID
    numero = Column(Integer)
    numero2 = Column(String(50))  # Secondary diploma number
    titulo = Column(Text)
    tipo = Column(String(100))
    sessao = Column(Integer)
    ano_civil = Column(Integer)
    link_texto = Column(Text)
    observacoes = Column(Text)
    tp = Column(String(50))
    versao = Column(String(50))  # Versao field from IV Legislature
    anexos = Column(Text)  # Anexos field from XIII Legislature (comma-separated)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    legislatura = relationship("Legislatura", backref="diplomas_aprovados")
    publicacoes = relationship(
        "DiplomaPublicacao", back_populates="diploma", cascade="all, delete-orphan"
    )
    iniciativas = relationship(
        "DiplomaIniciativa", back_populates="diploma", cascade="all, delete-orphan"
    )
    orcam_contas_gerencia = relationship(
        "DiplomaOrcamContasGerencia",
        back_populates="diploma",
        cascade="all, delete-orphan",
    )


class DiplomaOrcamContasGerencia(Base):
    """Budget/Management Accounts associated with diplomas (XIII Legislature)"""

    __tablename__ = "diploma_orcam_contas_gerencia"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    diploma_id = Column(GUID(), ForeignKey("diplomas_aprovados.id"), nullable=False)
    orcam_id = Column(Integer)  # id from OrcamentoContasGerenciaOut
    leg = Column(String(50))  # leg field
    tp = Column(String(50))  # tp field
    titulo = Column(Text)  # titulo field
    tipo = Column(String(100))  # tipo field

    # Relationships
    diploma = relationship("DiplomaAprovado", back_populates="orcam_contas_gerencia")


class DiplomaPublicacao(Base):
    __tablename__ = "diploma_publicacoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    diploma_id = Column(GUID(), ForeignKey("diplomas_aprovados.id"), nullable=False)

    pub_nr = Column(Integer)
    pub_tipo = Column(String(50))
    pub_tp = Column(String(10))
    pub_leg = Column(String(20))
    pub_sl = Column(Integer)
    pub_dt = Column(Date)
    pag = Column(Text)  # Can contain multiple page numbers
    id_pag = Column(Integer)
    url_diario = Column(Text)
    supl = Column(String(10))
    obs = Column(Text)
    pag_final_diario_supl = Column(String(50))

    created_at = Column(DateTime, default=func.now())

    diploma = relationship("DiplomaAprovado", back_populates="publicacoes")


class DiplomaIniciativa(Base):
    __tablename__ = "diploma_iniciativas"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    diploma_id = Column(GUID(), ForeignKey("diplomas_aprovados.id"), nullable=False)

    ini_nr = Column(Integer)
    ini_tipo = Column(String(100))
    ini_link_texto = Column(Text)
    ini_id = Column(Integer)

    created_at = Column(DateTime, default=func.now())

    diploma = relationship("DiplomaAprovado", back_populates="iniciativas")


class PerguntaRequerimento(Base):
    """
    Parliamentary Questions and Requests Model
    =========================================

    Based on Requerimentos_DetalheRequerimentosOut structure from official documentation.

    Questions (Perguntas) are oversight instruments and political control acts that can only
    be directed to the Government and Public Administration, not to regional and local administration.

    Requests (Requerimentos) are used to obtain information, elements and official publications
    useful for the exercise of the Deputy's mandate and can be directed to any public entity.

    XML Structure Mapping (Requerimentos<Legislatura>.xml):
    - id: Código de Identificação do Requerimento (XML: id)
    - tipo: Tipo: Pergunta ou Requerimento (XML: tipo)
    - nr: Número do Requerimento/Pergunta (XML: nr)
    - reqTipo: Campo Tipo de Registo da estrutura TipodeRequerimento (XML: reqTipo)
    - sessao: Sessão Legislativa (XML: sessao)
    - assunto: Assunto do requerimento ou pergunta (XML: assunto)
    - dtEntrada: Data da Entrada do Requerimento (XML: dtEntrada)
    - dataEnvio: Data de envio do requerimento para o destinatário (XML: dataEnvio)
    - observacoes: Observações (XML: observacoes)
    - ficheiro: Nome do ficheiro que contém o texto do requerimento (XML: ficheiro)
    - fundamentacao: Descrição da fundamentação do requerimento (XML: fundamentacao)
    - autores: Lista de autores using Iniciativas_AutoresDeputadosOut structure
    - destinatarios: Lista de destinatários using Requerimentos_DestinatariosOut structure
    - publicacao: Lista de publicações using PublicacoesOut structure
    - respostasSPerguntas: Lista de respostas (apenas para requerimentos mais antigos)
    """

    __tablename__ = "perguntas_requerimentos"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    legislatura_id = Column(GUID(), ForeignKey("legislaturas.id"), nullable=False)

    # Core fields from XML mapping
    requerimento_id = Column(
        Integer,
        unique=True,
        comment="Código de Identificação do Requerimento (XML: id)",
    )
    tipo = Column(String(100), comment="Tipo: Pergunta ou Requerimento (XML: tipo)")
    nr = Column(Integer, comment="Número do Requerimento/Pergunta (XML: nr)")
    req_tipo = Column(
        String(100),
        comment="Tipo de Registo usando TipodeRequerimento enum (XML: reqTipo)",
    )
    sessao = Column(Integer, comment="Sessão Legislativa (XML: sessao)")
    assunto = Column(Text, comment="Assunto do requerimento ou pergunta (XML: assunto)")
    dt_entrada = Column(
        Date, comment="Data da Entrada do Requerimento (XML: dtEntrada)"
    )
    data_envio = Column(
        Date, comment="Data de envio para o destinatário (XML: dataEnvio)"
    )
    observacoes = Column(Text, comment="Observações (XML: observacoes)")
    ficheiro = Column(
        Text, comment="Nome do ficheiro que contém o texto (XML: ficheiro)"
    )
    fundamentacao = Column(
        Text, comment="Descrição da fundamentação do requerimento (XML: fundamentacao)"
    )

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    legislatura = relationship("Legislatura", backref="perguntas_requerimentos")
    publicacoes = relationship(
        "PerguntaRequerimentoPublicacao",
        back_populates="pergunta_requerimento",
        cascade="all, delete-orphan",
    )
    destinatarios = relationship(
        "PerguntaRequerimentoDestinatario",
        back_populates="pergunta_requerimento",
        cascade="all, delete-orphan",
    )
    autores = relationship(
        "PerguntaRequerimentoAutor",
        back_populates="pergunta_requerimento",
        cascade="all, delete-orphan",
    )


class PerguntaRequerimentoPublicacao(Base):
    """
    Parliamentary Questions and Requests Publications Model
    ======================================================

    Based on PublicacoesOut structure from official documentation.
    Contains publications related to parliamentary questions and requests.

    XML Structure Mapping (PublicacoesOut):
    - pubNr: Número da Publicação (XML: pubNr)
    - pubTipo: Descrição de tipo de publicação na estrutura TipodePublicacao (XML: pubTipo)
    - pubTp: Tipo de publicação na estrutura TipodePublicacao (XML: pubTp)
    - pubLeg: Legislatura em que ocorreu a Publicação (XML: pubLeg)
    - pubSL: Sessão legislativa em que ocorreu a Publicação (XML: pubSL)
    - pubdt: Data da Publicação (XML: pubdt)
    - idPag: Identificador da Paginação (XML: idPag)
    - URLDiario: Link para o DAR da Publicação (XML: URLDiario)
    - pag: Páginas (XML: pag)
    - supl: Suplemento da Publicação (XML: supl)
    - obs: Observações (XML: obs)
    - pagFinalDiarioSupl: Página final do suplemento (XML: pagFinalDiarioSupl)
    - debateDtReu: Data da reunião plenária onde ocorreu o Debate (XML: debateDtReu)
    - idAct: Identificador da Atividade associada à Publicação (XML: idAct)
    """

    __tablename__ = "pergunta_requerimento_publicacoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    pergunta_requerimento_id = Column(
        GUID(), ForeignKey("perguntas_requerimentos.id"), nullable=False
    )

    # Publications fields from XML mapping
    pub_nr = Column(Integer, comment="Número da Publicação (XML: pubNr)")
    pub_tipo = Column(
        String(50), comment="Descrição de tipo usando TipodePublicacao (XML: pubTipo)"
    )
    pub_tp = Column(
        String(10),
        comment="Tipo de publicação usando TipodePublicacao enum (XML: pubTp)",
    )
    pub_leg = Column(String(20), comment="Legislatura da Publicação (XML: pubLeg)")
    pub_sl = Column(Integer, comment="Sessão legislativa da Publicação (XML: pubSL)")
    pub_dt = Column(Date, comment="Data da Publicação (XML: pubdt)")
    id_pag = Column(Integer, comment="Identificador da Paginação (XML: idPag)")
    url_diario = Column(Text, comment="Link para o DAR da Publicação (XML: URLDiario)")
    pag = Column(Text, comment="Páginas (XML: pag)")
    supl = Column(String(10), comment="Suplemento da Publicação (XML: supl)")
    obs = Column(Text, comment="Observações (XML: obs)")
    pag_final_diario_supl = Column(
        String(50), comment="Página final do suplemento (XML: pagFinalDiarioSupl)"
    )
    debate_dt_reu = Column(
        Date,
        comment="Data da reunião plenária onde ocorreu o Debate (XML: debateDtReu)",
    )
    id_act = Column(
        Integer, comment="Identificador da Atividade associada (XML: idAct)"
    )

    created_at = Column(DateTime, default=func.now())

    pergunta_requerimento = relationship(
        "PerguntaRequerimento", back_populates="publicacoes"
    )


class PerguntaRequerimentoDestinatario(Base):
    """
    Parliamentary Questions and Requests Recipients Model
    ====================================================

    Based on Requerimentos_DestinatariosOut structure from official documentation.
    Contains recipient information for parliamentary questions and requests.

    XML Structure Mapping (Requerimentos_DestinatariosOut):
    - nomeEntidade: Nome do destinatário (XML: nomeEntidade)
    - dataProrrogacao: Data do pedido de prorrogação do prazo (XML: dataProrrogacao)
    - dataReenvio: Data de reenvio para outro destinatário (XML: dataReenvio)
    - devolvido: Indica se o requerimento foi devolvido (XML: devolvido)
    - prazoProrrogacao: Prazo em dias (XML: prazoProrrogacao)
    - prorrogado: Indica se o requerimento foi prorrogado (XML: prorrogado)
    - reenviado: Indica se o requerimento foi reenviado (XML: reenviado)
    - respostas: Contém os dados da resposta ao requerimento (XML: respostas)
    - retirado: Indica se o requerimento foi retirado (XML: retirado)
    """

    __tablename__ = "pergunta_requerimento_destinatarios"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    pergunta_requerimento_id = Column(
        GUID(), ForeignKey("perguntas_requerimentos.id"), nullable=False
    )

    # Recipient fields from XML mapping
    nome_entidade = Column(
        String(200), comment="Nome do destinatário (XML: nomeEntidade)"
    )
    data_prorrogacao = Column(
        Date, comment="Data do pedido de prorrogação do prazo (XML: dataProrrogacao)"
    )
    data_reenvio = Column(
        Date, comment="Data de reenvio para outro destinatário (XML: dataReenvio)"
    )
    devolvido = Column(Boolean, comment="Indica se foi devolvido (XML: devolvido)")
    prazo_prorrogacao = Column(Integer, comment="Prazo em dias (XML: prazoProrrogacao)")
    prorrogado = Column(Boolean, comment="Indica se foi prorrogado (XML: prorrogado)")
    reenviado = Column(Boolean, comment="Indica se foi reenviado (XML: reenviado)")
    retirado = Column(Boolean, comment="Indica se foi retirado (XML: retirado)")
    # Legacy field maintained for backward compatibility
    data_envio = Column(Date, comment="Data de envio (legacy compatibility)")

    created_at = Column(DateTime, default=func.now())

    pergunta_requerimento = relationship(
        "PerguntaRequerimento", back_populates="destinatarios"
    )
    respostas = relationship(
        "PerguntaRequerimentoResposta",
        back_populates="destinatario",
        cascade="all, delete-orphan",
    )

    # Indexes for performance optimization
    __table_args__ = (
        Index("idx_dest_pergunta_req_id", "pergunta_requerimento_id"),
        Index("idx_dest_nome_entidade", "nome_entidade"),
        Index("idx_dest_data_prorrogacao", "data_prorrogacao"),
        Index("idx_dest_data_reenvio", "data_reenvio"),
        Index("idx_dest_prorrogado", "prorrogado"),
    )


class PerguntaRequerimentoResposta(Base):
    """
    Parliamentary Questions and Requests Responses Model
    ===================================================

    Based on Requerimentos_RespostasOut structure from official documentation.
    Contains response information for parliamentary questions and requests.

    XML Structure Mapping (supports two response types):
    1. Regular responses (under Destinatarios/respostas) - with destinatario_id
    2. Direct responses (under RespostasSPerguntas) - with NULL destinatario_id
    
    Fields:
    - dataResposta: Data da resposta (XML: dataResposta)
    - docRemetida: Documentação remetida com a resposta (XML: docRemetida)
    - Entidade: Entidade que elaborou a resposta (XML: Entidade)
    - Ficheiro: Link para o ficheiro (XML: Ficheiro)
    - publicacao: Lista de publicações representadas por estrutura PublicacoesOut (XML: publicacao)
    """

    __tablename__ = "pergunta_requerimento_respostas"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    destinatario_id = Column(
        GUID(), ForeignKey("pergunta_requerimento_destinatarios.id"), nullable=True,
        comment="Recipient ID (NULL for direct responses like RespostasSPerguntas)"
    )

    # Response fields from XML mapping
    entidade = Column(
        String(200), comment="Entidade que elaborou a resposta (XML: Entidade)"
    )
    data_resposta = Column(Date, comment="Data da resposta (XML: dataResposta)")
    ficheiro = Column(Text, comment="Link para o ficheiro (XML: Ficheiro)")
    doc_remetida = Column(
        String(200), comment="Documentação remetida com a resposta (XML: docRemetida)"
    )
    
    # File attachment fields from ficheiroComTipo structure
    ficheiro_url = Column(Text, comment="File attachment URL (XML: ficheiroComTipo.url)")
    ficheiro_tipo = Column(String(50), comment="File attachment type (XML: ficheiroComTipo.tipo)")

    created_at = Column(DateTime, default=func.now())

    destinatario = relationship(
        "PerguntaRequerimentoDestinatario", back_populates="respostas"
    )

    # Indexes for performance optimization
    __table_args__ = (
        Index("idx_resp_destinatario_id", "destinatario_id"),
        Index("idx_resp_data_resposta", "data_resposta"),
        Index("idx_resp_entidade", "entidade"),
    )


class PerguntaRequerimentoAutor(Base):
    """
    Parliamentary Questions and Requests Authors Model
    =================================================

    Based on Iniciativas_AutoresDeputadosOut structure from official documentation.
    Contains author information for parliamentary questions and requests.

    XML Structure Mapping (Iniciativas_AutoresDeputadosOut):
    - GP: Grupo Parlamentar do Deputado (XML: GP)
    - idCadastro: Identificador do registo de cadastro do Deputado (XML: idCadastro)
    - nome: Nome do Deputado (XML: nome)
    """

    __tablename__ = "pergunta_requerimento_autores"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    pergunta_requerimento_id = Column(
        GUID(), ForeignKey("perguntas_requerimentos.id"), nullable=False
    )
    deputado_id = Column(GUID(), ForeignKey("deputados.id"), nullable=True)

    # Author fields from XML mapping
    id_cadastro = Column(
        Integer,
        comment="Identificador do registo de cadastro do Deputado (XML: idCadastro)",
    )
    nome = Column(String(200), comment="Nome do Deputado (XML: nome)")
    gp = Column(String(50), comment="Grupo Parlamentar do Deputado (XML: GP)")

    created_at = Column(DateTime, default=func.now())

    pergunta_requerimento = relationship(
        "PerguntaRequerimento", back_populates="autores"
    )
    deputado = relationship("Deputado", backref="perguntas_requerimentos_autoria")


class CooperacaoParlamentar(Base):
    __tablename__ = "cooperacao_parlamentar"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    legislatura_id = Column(GUID(), ForeignKey("legislaturas.id"), nullable=False)

    # Core fields
    cooperacao_id = Column(Integer, unique=True)  # External ID
    tipo = Column(String(100))
    nome = Column(Text)
    sessao = Column(Integer)
    data = Column(Date)
    local = Column(Text)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    legislatura = relationship("Legislatura", backref="cooperacao_parlamentar")
    programas = relationship(
        "CooperacaoPrograma", back_populates="cooperacao", cascade="all, delete-orphan"
    )
    atividades = relationship(
        "CooperacaoAtividade", back_populates="cooperacao", cascade="all, delete-orphan"
    )


class CooperacaoPrograma(Base):
    __tablename__ = "cooperacao_programas"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    cooperacao_id = Column(
        GUID(), ForeignKey("cooperacao_parlamentar.id"), nullable=False
    )

    nome = Column(Text)
    descricao = Column(Text)

    created_at = Column(DateTime, default=func.now())

    cooperacao = relationship("CooperacaoParlamentar", back_populates="programas")


class CooperacaoAtividade(Base):
    __tablename__ = "cooperacao_atividades"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    cooperacao_id = Column(
        GUID(), ForeignKey("cooperacao_parlamentar.id"), nullable=False
    )
    atividade_id = Column(Integer)  # External activity ID from XML

    nome = Column(Text)
    tipo_atividade = Column(String(100))
    data_inicio = Column(Date)
    data_fim = Column(Date)
    local = Column(String(255))
    descricao = Column(Text)

    created_at = Column(DateTime, default=func.now())

    cooperacao = relationship("CooperacaoParlamentar", back_populates="atividades")
    participantes = relationship(
        "CooperacaoParticipante",
        back_populates="atividade",
        cascade="all, delete-orphan",
    )


class CooperacaoParticipante(Base):
    __tablename__ = "cooperacao_participantes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    atividade_id = Column(
        GUID(), ForeignKey("cooperacao_atividades.id"), nullable=False
    )
    participante_id = Column(Integer)  # External participant ID from XML

    nome = Column(String(200))
    cargo = Column(String(100))
    entidade = Column(String(200))
    tipo_participante = Column(String(50))  # 'interno', 'externo', etc.

    created_at = Column(DateTime, default=func.now())

    atividade = relationship("CooperacaoAtividade", back_populates="participantes")


class DelegacaoEventual(Base):
    """
    Eventual Delegation (Delegação Eventual)

    Information about sporadic meetings attended by Assembly deputies.
    Maps to Reuniao structure in DelegacoesEventuais.xml files.

    Based on official Parliament documentation (December 2017) -
    identical across legislatures IX through XIII.
    """

    __tablename__ = "delegacao_eventual"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    legislatura_id = Column(GUID(), ForeignKey("legislaturas.id"), nullable=False)

    # Core meeting fields from official documentation
    delegacao_id = Column(
        Integer, unique=True
    )  # ID: Identificador do registo das Delegação Eventual
    nome = Column(Text)  # Nome: Título da reunião da Delegação Eventual
    local = Column(
        Text
    )  # Local: Cidade e País onde foi realizada a reunião da Delegação Eventual
    sessao = Column(Integer)  # Sessão: Número da Sessão Legislativa
    data_inicio = Column(
        Date
    )  # DataInicio: Data de Início da reunião da Delegação Eventual
    data_fim = Column(Date)  # DataFim: Data do fim da reunião da Delegação Eventual
    tipo = Column(String(100))  # Additional classification field

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    legislatura = relationship("Legislatura", backref="delegacoes_eventuais")
    participantes = relationship(
        "DelegacaoEventualParticipante",
        back_populates="delegacao",
        cascade="all, delete-orphan",
    )


class DelegacaoEventualParticipante(Base):
    """
    Eventual Delegation Participant (Participante)

    Individual participants in eventual delegation meetings.
    Maps to Participante structure in DelegacoesEventuais.xml files.

    Based on official Parliament documentation (December 2017) -
    identical across legislatures IX through XIII.
    """

    __tablename__ = "delegacao_eventual_participantes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    delegacao_id = Column(GUID(), ForeignKey("delegacao_eventual.id"), nullable=False)
    deputado_id = Column(GUID(), ForeignKey("deputados.id"), nullable=True)
    participante_id = Column(
        Integer
    )  # External participant ID from XML (IX Legislature)

    # Participant fields from official documentation
    nome = Column(String(200))  # Nome: Nome do deputado participante na reunião
    cargo = Column(String(100))  # Additional position/role field
    gp = Column(String(50))  # Gp: Grupo parlamentar ao qual pertence o deputado
    tipo_participante = Column(String(50))  # Tipo: Tipo de participante (D=Deputado)

    created_at = Column(DateTime, default=func.now())

    delegacao = relationship("DelegacaoEventual", back_populates="participantes")
    deputado = relationship("Deputado", backref="delegacoes_eventuais_participacao")


class DelegacaoPermanente(Base):
    """
    Permanent Parliamentary Delegations Model
    ========================================

    Information about permanent delegations to international parliamentary organizations,
    including delegations to APCE (Parliamentary Assembly of the Council of Europe),
    APOSCE (OSCE Parliamentary Assembly), APNATO (NATO Parliamentary Assembly),
    UIP (Inter-Parliamentary Union), AP-UPM (Parliamentary Assembly of the Union for the Mediterranean),
    FPIA (Ibero-American Parliamentary Forum), and AP-CPLP (Parliamentary Assembly of the Community
    of Portuguese Speaking Countries), among others.

    Based on official Parliament documentation (December 2017) -
    identical across legislatures IX through XIII.

    XML Structure: ArrayOfDelegacaoPermanente > DelegacaoPermanente

    Field Mappings (from official documentation):
    - Id: Identificador do registo da Delegação Permanente
    - Nome: Nome da Delegação Permanente
    - Legislatura: Identificador da Legislatura
    - Sessão: Número da Sessão Legislativa
    - DataEleicao: Data da eleição da Delegação Permanente
    - Composicao: Lista de deputados da Delegação (estruturas Membro)
    - Comissoes: Lista de comissões da Delegação (estruturas Comissao)
    - Reunioes: Lista de reuniões da Delegação (estruturas Reuniao)
    """

    __tablename__ = "delegacao_permanente"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    legislatura_id = Column(
        GUID(),
        ForeignKey("legislaturas.id"),
        nullable=False,
        comment="Legislature identifier (Legislatura)",
    )

    # Core fields from official documentation
    delegacao_id = Column(
        Integer, unique=True, comment="Delegation record identifier (Id)"
    )
    nome = Column(Text, comment="Permanent delegation name (Nome)")
    sessao = Column(String(50), comment="Legislative session number (Sessão)")
    data_eleicao = Column(Date, comment="Delegation election date (DataEleicao)")

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    legislatura = relationship("Legislatura", backref="delegacoes_permanentes")
    membros = relationship(
        "DelegacaoPermanenteMembro",
        back_populates="delegacao",
        cascade="all, delete-orphan",
    )


class DelegacaoPermanenteMembro(Base):
    """
    Permanent Delegation Members Model
    =================================

    Members (deputies) belonging to permanent delegations.

    XML Structure: DelegacaoPermanente > Composicao > Membro

    Field Mappings (from official documentation):
    - Nome: Nome do deputado participante na reunião
    - Gp: Grupo parlamentar ao qual pertence o deputado
    - Cargo: Cargo exercido pelo deputado
    - DataInicio: Data do início do exercício de funções na Delegação Permanente pelo deputado
    - DataFim: Data do fim do exercício de funções na Delegação Permanente
    - Id: Identificador do deputado
    """

    __tablename__ = "delegacao_permanente_membros"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    delegacao_id = Column(
        GUID(), ForeignKey("delegacao_permanente.id"), nullable=False
    )
    deputado_id = Column(GUID(), ForeignKey("deputados.id"), nullable=True)

    membro_id = Column(Integer, comment="Deputy identifier (Id)")
    nome = Column(String(200), comment="Deputy participant name (Nome)")
    cargo = Column(String(100), comment="Position held by deputy (Cargo)")
    gp = Column(String(50), comment="Parliamentary group (Gp)")
    data_inicio = Column(Date, comment="Start date of functions (DataInicio)")
    data_fim = Column(Date, comment="End date of functions (DataFim)")

    created_at = Column(DateTime, default=func.now())

    delegacao = relationship("DelegacaoPermanente", back_populates="membros")
    deputado = relationship("Deputado", backref="delegacoes_permanentes_participacao")


class DelegacaoPermanenteComissao(Base):
    """
    Permanent Delegation Commissions Model
    =====================================

    Commissions belonging to permanent delegations.

    XML Structure: DelegacaoPermanente > Comissoes > Comissao

    Field Mappings (from official documentation):
    - Nome: Nome da comissão pertencente à Delegação Permanente
    - Composição: Composição da comissão
    - Subcomissoes: Lista de Subcomissões pertencentes a cada comissão
    """

    __tablename__ = "delegacao_permanente_comissoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    delegacao_id = Column(
        GUID(), ForeignKey("delegacao_permanente.id"), nullable=False
    )

    # Commission fields from official documentation
    nome = Column(Text, comment="Commission name (Nome)")
    composicao = Column(Text, comment="Commission composition details (Composição)")
    subcomissoes = Column(Text, comment="Subcommissions data (Subcomissoes)")

    created_at = Column(DateTime, default=func.now())

    # Relationships
    delegacao = relationship("DelegacaoPermanente", backref="comissoes")
    membros = relationship(
        "DelegacaoPermanenteComissaoMembro",
        back_populates="comissao",
        cascade="all, delete-orphan",
    )


class DelegacaoPermanenteComissaoMembro(Base):
    """Commission member data for permanent delegations - XI Legislature nested structure"""

    __tablename__ = "delegacao_permanente_comissao_membros"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    comissao_id = Column(
        GUID(), ForeignKey("delegacao_permanente_comissoes.id"), nullable=False
    )

    # Member fields with XML namespace support
    nome = Column(Text)  # Member name (can be long)
    gp = Column(String(50))  # Parliamentary group
    cargo = Column(Text)  # Position/role (can be long)
    data_inicio = Column(Date)  # Start date
    data_fim = Column(Date)  # End date

    created_at = Column(DateTime, default=func.now())

    # Relationships
    comissao = relationship("DelegacaoPermanenteComissao", back_populates="membros")


class AtividadeParlamentar(Base):
    """
    Parliamentary Activities Root Container
    ======================================

    Root container for all parliamentary activities from Atividades.xml.
    Based on official Portuguese Parliament documentation (December 2017):
    "AtividadesGerais" structure from VI_Legislatura documentation.

    MAPPED STRUCTURES (from official documentation):

    1. **AtividadesGerais** - General parliamentary activities
       - IDAtividade: Activity identifier (atividade_id)
       - Tipo: Activity type code (tipo) - requires TipodeAtividade translator
       - DescTipo: Activity type description (desc_tipo)
       - Assunto: Activity subject matter (assunto)
       - Numero: Activity number (numero)
       - Data: Activity date (data_atividade)
       - DataEntrada: Entry date (data_entrada)
       - DataAgendamentoDebate: Scheduled debate date (data_agendamento_debate)
       - TipoAutor: Author type (tipo_autor) - requires TipodeAutor translator
       - AutoresGP: Group authors list (autores_gp)
       - OutrosSubscritores: Other subscribers (outros_subscritores)
       - TextosAprovados: Approved texts (textos_aprovados)
       - ResultadoVotacaoPontos: Voting results by points (resultado_votacao_pontos)
       - Observacoes: General observations (observacoes)

    Translation Requirements:
    - tipo: Maps to TipodeAtividade enum (24 codes: AUD, AUDI, etc.)
    - tipo_autor: Maps to TipodeAutor enum (author type classifications)
    """

    __tablename__ = "atividade_parlamentar"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    legislatura_id = Column(GUID(), ForeignKey("legislaturas.id"), nullable=False)

    # Core fields from AtividadesGerais structure
    atividade_id = Column(
        Integer,
        comment="Activity identifier (IDAtividade) - unique per legislature",
    )

    __table_args__ = (
        UniqueConstraint('atividade_id', 'legislatura_id', name='uq_atividade_legislatura'),
    )
    tipo = Column(
        String(100),
        comment="Activity type code (Tipo) - requires TipodeAtividade translator",
    )
    desc_tipo = Column(
        String(200),
        comment="Activity type description (DescTipo) - official classification name",
    )
    assunto = Column(
        Text,
        comment="Activity subject matter (Assunto) - descriptive text of activity topic",
    )
    numero = Column(
        String(50), comment="Activity number (Numero) - sequential or reference number"
    )
    data_atividade = Column(
        Date, comment="Activity date (Data) - when the activity took place"
    )
    data_entrada = Column(
        Date,
        comment="Entry date (DataEntrada) - when activity was registered in system",
    )
    data_agendamento_debate = Column(
        Date,
        comment="Scheduled debate date (DataAgendamentoDebate) - planned discussion date",
    )
    tipo_autor = Column(
        String(100),
        comment="Author type (TipoAutor) - requires TipodeAutor translator for classification",
    )
    autores_gp = Column(
        Text,
        comment="Group authors (AutoresGP) - parliamentary groups authoring the activity",
    )
    outros_subscritores = Column(
        Text,
        comment="Other subscribers (OutrosSubscritores) - additional supporters or co-authors",
    )
    textos_aprovados = Column(
        Text,
        comment="Approved texts (TextosAprovados) - texts that were approved during activity",
    )
    resultado_votacao_pontos = Column(
        Text,
        comment="Voting results by points (ResultadoVotacaoPontos) - detailed voting outcomes",
    )
    observacoes = Column(
        Text,
        comment="General observations (Observacoes) - additional notes and comments",
    )

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    legislatura = relationship("Legislatura", backref="atividades_parlamentares")
    publicacoes = relationship(
        "AtividadeParlamentarPublicacao",
        back_populates="atividade",
        cascade="all, delete-orphan",
    )
    votacoes = relationship(
        "AtividadeParlamentarVotacao",
        back_populates="atividade",
        cascade="all, delete-orphan",
    )
    eleitos = relationship(
        "AtividadeParlamentarEleito",
        back_populates="atividade",
        cascade="all, delete-orphan",
    )
    convidados = relationship(
        "AtividadeParlamentarConvidado",
        back_populates="atividade",
        cascade="all, delete-orphan",
    )


class AtividadeParlamentarPublicacao(Base):
    __tablename__ = "atividade_parlamentar_publicacoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    atividade_id = Column(
        GUID(), ForeignKey("atividade_parlamentar.id"), nullable=False
    )

    pub_nr = Column(Integer)
    pub_tipo = Column(String(100))
    pub_tp = Column(String(50))
    pub_leg = Column(String(50))
    pub_sl = Column(Integer)
    pub_dt = Column(Date)
    pag = Column(Text)
    url_diario = Column(Text)
    id_pag = Column(Integer)
    id_deb = Column(Integer)
    supl = Column(String(100))  # Missing supplement field
    obs = Column(Text)  # Missing observations field

    created_at = Column(DateTime, default=func.now())

    atividade = relationship("AtividadeParlamentar", back_populates="publicacoes")


class AtividadeParlamentarVotacao(Base):
    __tablename__ = "atividade_parlamentar_votacoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    atividade_id = Column(
        GUID(), ForeignKey("atividade_parlamentar.id"), nullable=False
    )

    votacao_id = Column(Integer)
    resultado = Column(String(100))
    unanime = Column(Boolean)  # Missing unanimous field
    reuniao = Column(String(100))
    publicacao = Column(String(200))
    data = Column(Date)
    detalhe = Column(Text)  # Missing voting detail field
    descricao = Column(Text)  # Missing voting description field
    ausencias = Column(Text)  # Missing voting absences field

    created_at = Column(DateTime, default=func.now())

    atividade = relationship("AtividadeParlamentar", back_populates="votacoes")


class AtividadeParlamentarEleito(Base):
    __tablename__ = "atividade_parlamentar_eleitos"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    atividade_id = Column(
        GUID(), ForeignKey("atividade_parlamentar.id"), nullable=False
    )

    nome = Column(String(200))
    cargo = Column(String(100))

    created_at = Column(DateTime, default=func.now())

    atividade = relationship("AtividadeParlamentar", back_populates="eleitos")


class AtividadeParlamentarConvidado(Base):
    __tablename__ = "atividade_parlamentar_convidados"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    atividade_id = Column(
        GUID(), ForeignKey("atividade_parlamentar.id"), nullable=False
    )

    nome = Column(String(200))
    pais = Column(String(100))
    honra = Column(String(100))

    created_at = Column(DateTime, default=func.now())

    atividade = relationship("AtividadeParlamentar", back_populates="convidados")


class DebateParlamentar(Base):
    __tablename__ = "debate_parlamentar"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    legislatura_id = Column(GUID(), ForeignKey("legislaturas.id"), nullable=False)

    # Core fields
    debate_id = Column(Integer, unique=True)  # External ID
    tipo_debate_desig = Column(String(200))
    data_debate = Column(Date)
    tipo_debate = Column(String(100))
    sessao = Column(Integer)  # Missing session field
    assunto = Column(Text)
    tipo_autor = Column(String(100))  # Missing TipoAutor field
    autores_deputados = Column(Text)  # Missing authors field
    autores_gp = Column(Text)  # Missing AutoresGP field
    data_entrada = Column(Date)  # Missing DataEntrada field
    intervencoes = Column(Text)
    observacoes = Column(Text)  # Missing Observacoes field for debates
    artigo = Column(Text)  # Artigo field for debates

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    legislatura = relationship("Legislatura", backref="debates_parlamentares")
    publicacoes = relationship(
        "DebateParlamentarPublicacao",
        back_populates="debate",
        cascade="all, delete-orphan",
    )


class DebateParlamentarPublicacao(Base):
    __tablename__ = "debate_parlamentar_publicacoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    debate_id = Column(GUID(), ForeignKey("debate_parlamentar.id"), nullable=False)

    pub_nr = Column(Integer)
    pub_tipo = Column(String(100))
    pub_tp = Column(String(50))
    pub_leg = Column(String(50))
    pub_sl = Column(Integer)
    pub_dt = Column(Date)
    pag = Column(Text)
    url_diario = Column(Text)
    id_pag = Column(Integer)
    id_deb = Column(Integer)
    supl = Column(String(100))  # Missing supplement field
    obs = Column(Text)  # Observations field

    created_at = Column(DateTime, default=func.now())

    debate = relationship("DebateParlamentar", back_populates="publicacoes")


class RelatorioParlamentar(Base):
    __tablename__ = "relatorio_parlamentar"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    legislatura_id = Column(GUID(), ForeignKey("legislaturas.id"), nullable=False)

    # Core fields
    relatorio_id = Column(Integer, unique=True)  # External ID if available
    tipo = Column(String(100))
    desc_tipo = Column(String(200))  # Missing DescTipo field
    assunto = Column(Text)
    sessao = Column(Integer)  # Missing session field
    data_entrada = Column(Date)
    data_agendamento_debate = Column(Date)  # Missing DataAgendamentoDebate field
    comissao = Column(String(200))
    entidades_externas = Column(Text)
    textos_aprovados = Column(Text)  # Missing TextosAprovados field for reports
    observacoes = Column(Text)  # Missing Observacoes field

    # Additional XIII Legislature fields
    data_parecer_utao = Column(Date)  # DataParecerUTAO field
    data_pedido_parecer = Column(Date)  # DataPedidoParecer field
    membros_governo = Column(Text)  # MembrosGoverno field
    audicoes = Column(Text)  # Audicoes field

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    legislatura = relationship("Legislatura", backref="relatorios_parlamentares")
    publicacoes = relationship(
        "RelatorioParlamentarPublicacao",
        back_populates="relatorio",
        cascade="all, delete-orphan",
    )
    votacoes = relationship(
        "RelatorioParlamentarVotacao",
        back_populates="relatorio",
        cascade="all, delete-orphan",
    )
    relatores = relationship(
        "RelatorioParlamentarRelator",
        back_populates="relatorio",
        cascade="all, delete-orphan",
    )
    documentos = relationship(
        "RelatorioParlamentarDocumento",
        back_populates="relatorio",
        cascade="all, delete-orphan",
    )
    links = relationship(
        "RelatorioParlamentarLink",
        back_populates="relatorio",
        cascade="all, delete-orphan",
    )
    comissoes_opinioes = relationship(
        "RelatorioParlamentarComissaoOpiniao",
        back_populates="relatorio",
        cascade="all, delete-orphan",
    )


class RelatorioParlamentarPublicacao(Base):
    __tablename__ = "relatorio_parlamentar_publicacoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    relatorio_id = Column(
        GUID(), ForeignKey("relatorio_parlamentar.id"), nullable=False
    )

    pub_nr = Column(Integer)
    pub_tipo = Column(String(100))
    pub_tp = Column(String(50))
    pub_leg = Column(String(50))
    pub_sl = Column(Integer)
    pub_dt = Column(Date)
    pag = Column(Text)
    url_diario = Column(Text)
    id_pag = Column(Integer)
    id_deb = Column(Integer)
    supl = Column(String(100))  # Missing supplement field
    obs = Column(Text)  # Observations field

    created_at = Column(DateTime, default=func.now())

    relatorio = relationship("RelatorioParlamentar", back_populates="publicacoes")


class RelatorioParlamentarVotacao(Base):
    __tablename__ = "relatorio_parlamentar_votacoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    relatorio_id = Column(
        GUID(), ForeignKey("relatorio_parlamentar.id"), nullable=False
    )

    votacao_id = Column(Integer)
    id_votacao = Column(Integer)  # VotacaoRelatorio.id field
    resultado = Column(String(100))
    unanime = Column(Boolean)  # VotacaoRelatorio.unanime field
    descricao = Column(Text)  # VotacaoRelatorio.descricao
    reuniao = Column(String(100))
    data = Column(Date)

    created_at = Column(DateTime, default=func.now())

    relatorio = relationship("RelatorioParlamentar", back_populates="votacoes")
    publicacao = relationship(
        "RelatorioParlamentarVotacaoPublicacao",
        back_populates="votacao",
        cascade="all, delete-orphan",
    )


class RelatorioParlamentarVotacaoPublicacao(Base):
    __tablename__ = "relatorio_parlamentar_votacao_publicacoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    votacao_id = Column(
        GUID(), ForeignKey("relatorio_parlamentar_votacoes.id"), nullable=False
    )

    pub_nr = Column(Integer)
    pub_tipo = Column(String(100))
    pub_tp = Column(String(50))
    pub_leg = Column(String(50))
    pub_sl = Column(Integer)
    pub_dt = Column(Date)
    pag = Column(Text)
    url_diario = Column(Text)
    id_pag = Column(Integer)
    id_deb = Column(Integer)
    obs = Column(Text)

    created_at = Column(DateTime, default=func.now())

    votacao = relationship("RelatorioParlamentarVotacao", back_populates="publicacao")


class RelatorioParlamentarRelator(Base):
    __tablename__ = "relatorio_parlamentar_relatores"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    relatorio_id = Column(
        GUID(), ForeignKey("relatorio_parlamentar.id"), nullable=False
    )

    relator_id = Column(Integer)  # Relatores.pt_gov_ar_objectos_RelatoresOut.id
    nome = Column(String(200))  # Relatores.pt_gov_ar_objectos_RelatoresOut.nome
    gp = Column(String(100))  # Relatores.pt_gov_ar_objectos_RelatoresOut.gp

    created_at = Column(DateTime, default=func.now())

    relatorio = relationship("RelatorioParlamentar", back_populates="relatores")


class RelatorioParlamentarDocumento(Base):
    __tablename__ = "relatorio_parlamentar_documentos"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    relatorio_id = Column(
        GUID(), ForeignKey("relatorio_parlamentar.id"), nullable=False
    )

    # Document fields from Documentos.DocsOut
    data_documento = Column(Date)
    tipo_documento = Column(String(200))
    titulo_documento = Column(Text)
    url = Column(Text)

    created_at = Column(DateTime, default=func.now())

    # Relationships
    relatorio = relationship("RelatorioParlamentar", back_populates="documentos")


class RelatorioParlamentarLink(Base):
    __tablename__ = "relatorio_parlamentar_links"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    relatorio_id = Column(
        GUID(), ForeignKey("relatorio_parlamentar.id"), nullable=False
    )

    # Link fields from Links.DocsOut
    data_documento = Column(Date)
    tipo_documento = Column(String(200))
    titulo_documento = Column(Text)
    url = Column(Text)

    created_at = Column(DateTime, default=func.now())

    # Relationships
    relatorio = relationship("RelatorioParlamentar", back_populates="links")


class EventoParlamentar(Base):
    """
    Parliamentary Events Container
    =============================

    Container for parliamentary events from Atividades.xml.
    Based on official Portuguese Parliament documentation (December 2017):
    "Eventos" structure from VI_Legislatura documentation.

    MAPPED STRUCTURES (from official documentation):

    1. **DadosEventosComissaoOut** - Committee event data
       - IDEvento: Event identifier (id_evento)
       - Data: Event date (data)
       - Designacao: Event designation/title (designacao)
       - LocalEvento: Event location (local_evento)
       - SessaoLegislativa: Legislative session (sessao_legislativa)
       - TipoEvento: Event type (tipo_evento) - requires TipodeEvento translator

    Translation Requirements:
    - tipo_evento: Maps to TipodeEvento enum from reference tables
    """

    __tablename__ = "eventos_parlamentares"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    legislatura_id = Column(GUID(), ForeignKey("legislaturas.id"), nullable=False)

    # Event fields from DadosEventosComissaoOut structure
    id_evento = Column(
        Integer,
        nullable=False,
        comment="Event identifier (IDEvento) - unique event registry ID",
    )
    data = Column(Date, comment="Event date (Data) - when the event took place")
    designacao = Column(
        Text, comment="Event designation (Designacao) - official title or name of event"
    )
    local_evento = Column(
        String(500), comment="Event location (LocalEvento) - where the event was held"
    )
    sessao_legislativa = Column(
        Integer,
        comment="Legislative session (SessaoLegislativa) - session number when event occurred",
    )
    tipo_evento = Column(
        String(200),
        comment="Event type (TipoEvento) - requires TipodeEvento translator for classification",
    )

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    legislatura = relationship("Legislatura")

    # Indexes
    __table_args__ = (
        Index("idx_evento_parlamentar_id_evento", "id_evento"),
        Index("idx_evento_parlamentar_legislatura", "legislatura_id"),
        Index("idx_evento_parlamentar_data", "data"),
        UniqueConstraint(
            "id_evento", "legislatura_id", name="uq_evento_parlamentar_id_leg"
        ),
    )


class DeslocacaoParlamentar(Base):
    """
    Parliamentary Displacements Container
    ====================================

    Container for parliamentary displacements from Atividades.xml.
    Based on official Portuguese Parliament documentation (December 2017):
    "Deslocacoes" structure from VI_Legislatura documentation.

    MAPPED STRUCTURES (from official documentation):

    1. **DadosDeslocacoesComissaoOut** - Committee displacement data
       - IDDeslocacao: Displacement identifier (id_deslocacao)
       - DataIni: Start date (data_ini)
       - DataFim: End date (data_fim)
       - Designacao: Displacement designation (designacao)
       - TipoDeslocacao: Displacement type - requires TipodeDeslocacoes translator

    Translation Requirements:
    - Displacement type classification from TipodeDeslocacoes reference table
    """

    __tablename__ = "deslocacoes_parlamentares"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    legislatura_id = Column(GUID(), ForeignKey("legislaturas.id"), nullable=False)

    # Displacement fields from DadosDeslocacoesComissaoOut structure
    id_deslocacao = Column(
        Integer,
        nullable=False,
        comment="Displacement identifier (IDDeslocacao) - unique displacement registry ID",
    )
    data_ini = Column(Date, comment="Start date (DataIni) - when displacement begins")
    data_fim = Column(Date, comment="End date (DataFim) - when displacement ends")
    designacao = Column(
        Text,
        comment="Displacement designation (Designacao) - official purpose or destination description",
    )
    local_evento = Column(String(500))
    sessao_legislativa = Column(Integer)
    tipo = Column(String(200))

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    legislatura = relationship("Legislatura")

    # Indexes
    __table_args__ = (
        Index("idx_deslocacao_parlamentar_id_deslocacao", "id_deslocacao"),
        Index("idx_deslocacao_parlamentar_legislatura", "legislatura_id"),
        Index("idx_deslocacao_parlamentar_data_ini", "data_ini"),
        UniqueConstraint(
            "id_deslocacao", "legislatura_id", name="uq_deslocacao_parlamentar_id_leg"
        ),
    )


class RelatorioParlamentarComissaoOpiniao(Base):
    __tablename__ = "relatorio_parlamentar_comissoes_opinioes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    relatorio_parlamentar_id = Column(
        GUID(), ForeignKey("relatorio_parlamentar.id"), nullable=False
    )

    # Commission Opinion fields from ParecerComissao.AtividadeComissoesOut
    comissao_id = Column(Integer)  # AtividadeComissoesOut.Id
    nome = Column(String(500))  # AtividadeComissoesOut.Nome
    numero = Column(Integer)  # AtividadeComissoesOut.Numero
    sigla = Column(String(50))  # AtividadeComissoesOut.Sigla

    created_at = Column(DateTime, default=func.now())

    # Relationships
    relatorio = relationship(
        "RelatorioParlamentar", back_populates="comissoes_opinioes"
    )
    documentos = relationship(
        "RelatorioParlamentarComissaoDocumento", back_populates="comissao_opiniao"
    )
    relatores = relationship(
        "RelatorioParlamentarComissaoRelator", back_populates="comissao_opiniao"
    )


class RelatorioParlamentarComissaoDocumento(Base):
    __tablename__ = "relatorio_parlamentar_comissao_documentos"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    comissao_opiniao_id = Column(
        GUID(),
        ForeignKey("relatorio_parlamentar_comissoes_opinioes.id"),
        nullable=False,
    )

    # Document fields from ParecerComissao.AtividadeComissoesOut.Documentos.pt_gov_ar_objectos_DocsOut
    url = Column(Text)
    data_documento = Column(Date)
    publicar_internet = Column(Boolean)
    tipo_documento = Column(String(200))
    titulo_documento = Column(Text)

    created_at = Column(DateTime, default=func.now())

    # Relationships
    comissao_opiniao = relationship(
        "RelatorioParlamentarComissaoOpiniao", back_populates="documentos"
    )


class RelatorioParlamentarComissaoRelator(Base):
    __tablename__ = "relatorio_parlamentar_comissao_relatores"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    comissao_opiniao_id = Column(
        GUID(),
        ForeignKey("relatorio_parlamentar_comissoes_opinioes.id"),
        nullable=False,
    )

    # Relator fields from ParecerComissao.AtividadeComissoesOut.Relatores.pt_gov_ar_objectos_RelatoresOut
    relator_id = Column(Integer)
    nome = Column(String(200))
    gp = Column(String(100))

    created_at = Column(DateTime, default=func.now())

    # Relationships
    comissao_opiniao = relationship(
        "RelatorioParlamentarComissaoOpiniao", back_populates="relatores"
    )


class RelatorioParlamentarIniciativaConjunta(Base):
    __tablename__ = "relatorio_parlamentar_iniciativas_conjuntas"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    relatorio_id = Column(
        GUID(), ForeignKey("relatorio_parlamentar.id"), nullable=False
    )

    # Joint Initiative fields from IniciativasConjuntas.pt_gov_ar_objectos_iniciativas_DiscussaoConjuntaOut
    iniciativa_id = Column(Integer)  # id field
    tipo = Column(String(200))  # tipo field
    desc_tipo = Column(String(500))  # descTipo field

    created_at = Column(DateTime, default=func.now())

    # Relationships
    relatorio = relationship("RelatorioParlamentar", backref="iniciativas_conjuntas")


class AudicoesParlamentares(Base):
    __tablename__ = "audicoes_parlamentares"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    legislatura_id = Column(GUID(), ForeignKey("legislaturas.id"))

    id_audicao = Column(Integer)  # IDAudicao
    numero_audicao = Column(String(100))  # NumeroAudicao field
    sessao_legislativa = Column(String(100))  # SessaoLegislativa field
    assunto = Column(Text)
    data_audicao = Column(Date)
    data = Column(Date)  # Data field (alternative date format)
    comissao = Column(String(200))
    tipo_audicao = Column(String(100))
    entidades = Column(Text)  # Entidades field
    observacoes = Column(Text)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    legislatura = relationship("Legislatura", backref="audicoes_parlamentares")


class AudienciasParlamentares(Base):
    """
    Parliamentary Audiences Container
    ================================

    Container for parliamentary audiences from Atividades.xml.
    Based on official Portuguese Parliament documentation (December 2017):
    "Audiencias" structure from VI_Legislatura documentation.

    MAPPED STRUCTURES (from official documentation):

    1. **DadosAudienciasComissaoOut** - Committee audience data
       - IDAudiencia: Audience identifier (id_audiencia)
       - NumeroAudiencia: Audience sequential number (numero_audiencia)
       - SessaoLegislativa: Legislative session (sessao_legislativa)
       - Assunto: Audience subject matter (assunto)
       - Data: Audience date (data_audiencia, data)
       - Comissao: Committee name (comissao)
       - Concedida: Whether audience was granted (concedida)
       - TipoAudiencia: Audience type (tipo_audiencia)
       - Entidades: Participating entities (entidades)
       - Observacoes: Additional observations (observacoes)

    Note: Audiences are formal hearings where external entities present to committees.
    """

    __tablename__ = "audiencias_parlamentares"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    legislatura_id = Column(GUID(), ForeignKey("legislaturas.id"))

    id_audiencia = Column(
        Integer,
        comment="Audience identifier (IDAudiencia) - unique audience registry ID",
    )
    numero_audiencia = Column(
        Integer,
        comment="Audience number (NumeroAudiencia) - sequential numbering within session",
    )
    sessao_legislativa = Column(
        String(100),
        comment="Legislative session (SessaoLegislativa) - session when audience occurred",
    )
    assunto = Column(
        Text, comment="Audience subject (Assunto) - topic or matter being discussed"
    )
    data_audiencia = Column(
        Date, comment="Audience date (Data) - when the audience took place"
    )
    data = Column(
        Date, comment="Alternative date field (Data) - additional date reference"
    )
    comissao = Column(
        String(200), comment="Committee (Comissao) - committee conducting the audience"
    )
    concedida = Column(
        Boolean,
        comment="Granted status (Concedida) - whether the audience request was approved",
    )
    tipo_audiencia = Column(
        String(100),
        comment="Audience type (TipoAudiencia) - classification of audience format",
    )
    entidades = Column(
        Text,
        comment="Participating entities (Entidades) - organizations or individuals presenting",
    )
    observacoes = Column(
        Text, comment="Observations (Observacoes) - additional notes and remarks"
    )

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    legislatura = relationship("Legislatura", backref="audiencias_parlamentares")


class AudicaoParlamentar(Base):
    """
    Parliamentary Auditions Model - Based on Atividades.xml DadosAudicoesComissaoOut

    Model for parliamentary auditions (committee hearings) from Atividades.xml.
    Maps DadosAudicoesComissaoOut structure from the XML files.

    Fields:
    - IDAudicao: Audition identifier (id_audicao)
    - NumeroAudicao: Audition sequential number (numero_audicao)
    - Data: Audition date (data)
    - Assunto: Subject matter (assunto)
    - Entidades: Participating entities (entidades)
    - SessaoLegislativa: Legislative session number (sessao_legislativa)
    """

    __tablename__ = "audicao_parlamentar"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    legislatura_id = Column(GUID(), ForeignKey("legislaturas.id"), nullable=False)

    id_audicao = Column(Integer, comment="Audition identifier (IDAudicao)")
    numero_audicao = Column(String(100), comment="Audition number (NumeroAudicao)")
    data = Column(Date, comment="Audition date (Data)")
    assunto = Column(Text, comment="Subject matter (Assunto)")
    entidades = Column(Text, comment="Participating entities (Entidades)")
    sessao_legislativa = Column(
        Integer, comment="Legislative session (SessaoLegislativa)"
    )

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Index for performance
    __table_args__ = (
        Index("idx_audicao_parlamentar_id_audicao_leg", "id_audicao", "legislatura_id"),
    )

    # Relationships
    legislatura = relationship("Legislatura", backref="audicoes")


class AudienciaParlamentar(Base):
    """
    Parliamentary Audiences Model - Based on Atividades.xml DadosAudienciasComissaoOut

    Model for parliamentary audiences from Atividades.xml.
    Maps DadosAudienciasComissaoOut structure from the XML files.

    Fields:
    - IDAudiencia: Audience identifier (id_audiencia)
    - NumeroAudiencia: Audience sequential number (numero_audiencia)
    - Data: Audience date (data)
    - Assunto: Subject matter (assunto)
    - Entidades: Participating entities (entidades)
    - SessaoLegislativa: Legislative session number (sessao_legislativa)
    - Concedida: Whether audience was granted (concedida)
    """

    __tablename__ = "audiencia_parlamentar"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    legislatura_id = Column(GUID(), ForeignKey("legislaturas.id"), nullable=False)

    id_audiencia = Column(Integer, comment="Audience identifier (IDAudiencia)")
    numero_audiencia = Column(String(100), comment="Audience number (NumeroAudiencia)")
    data = Column(Date, comment="Audience date (Data)")
    assunto = Column(Text, comment="Subject matter (Assunto)")
    entidades = Column(Text, comment="Participating entities (Entidades)")
    sessao_legislativa = Column(
        Integer, comment="Legislative session (SessaoLegislativa)"
    )
    concedida = Column(String(50), comment="Granted status (Concedida)")

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Index for performance
    __table_args__ = (
        Index(
            "idx_audiencia_parlamentar_id_audiencia_leg",
            "id_audiencia",
            "legislatura_id",
        ),
    )

    # Relationships
    legislatura = relationship("Legislatura", backref="audiencias")


# Initiative models
class IniciativaParlamentar(Base):
    """
    Parliamentary Initiative Model - Based on Iniciativas<Legislatura>.xml specification

    Iniciativas Mapping (Iniciativas_DetalhePesquisaIniciativasOut):
    - iniId: ini_id (Identificador da Iniciativa)
    - iniNr: ini_nr (Número da Iniciativa)
    - iniTipo: ini_tipo (Indica o Tipo de Iniciativa)
    - iniDescTipo: ini_desc_tipo (Descrição do Tipo de Iniciativa)
    - iniLeg: ini_leg (Legislatura da iniciativa)
    - iniSel: ini_sel (Sessão legislativa da iniciativa)
    - dataInicioleg: data_inicio_leg (Data de Inicio da Legislatura)
    - dataFimleg: data_fim_leg (Data de Fim da Legislatura)
    - iniTitulo: ini_titulo (Indica o Titulo da Iniciativa)
    - iniTextoSubst: ini_texto_subst (Indica se tem texto de substituição)
    - iniTextoSubstCampo: ini_texto_subst_campo (Observações sobre substituição do ficheiro)
    - iniLinkTexto: ini_link_texto (Link para o texto da iniciativa)
    - iniObs: ini_obs (Observações associadas)

    Related Structures:
    - iniAutorDeputados: Deputado autor (Iniciativas_AutoresDeputadosOut)
    - iniAutorGruposParlamentares: Grupo Parlamentar autor (AutoresGruposParlamentaresOut)
    - iniAutorOutros: Outros autores (AutoresOutrosOut)
    - iniEventos: Eventos associados (Iniciativas_EventosOut)
    - iniAnexos: Anexos representados (Iniciativas_AnexosOut)
    - propostasAlteracao: Propostas de alteração (Iniciativas_PropostasAlteracaoOut)
    - iniciativasOrigem: Iniciativas que deram origem (Iniciativa_DadosGeraisOut)
    - iniciativasOriginadas: Iniciativas originadas (Iniciativa_DadosGeraisOut)
    - peticoes: Petições relacionadas (Iniciativas_DadosGeraisOut)
    - links: Links diversos associados

    Additional Fields:
    - iniEpigrafe: Indica se tem texto em epígrafe
    - iniciativasEuropeias: Iniciativas Europeias que deram origem
    """

    __tablename__ = "iniciativas_detalhadas"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    ini_id = Column(
        Integer,
        unique=True,
        nullable=False,
        comment="Identificador da Iniciativa (XML: iniId)",
    )
    ini_nr = Column(Integer, comment="Número da Iniciativa (XML: iniNr)")
    ini_tipo = Column(Text, comment="Tipo de Iniciativa - código (XML: iniTipo)")
    ini_desc_tipo = Column(
        Text, comment="Descrição do Tipo de Iniciativa (XML: iniDescTipo)"
    )
    ini_leg = Column(Text, comment="Legislatura da iniciativa (XML: iniLeg)")
    ini_sel = Column(Integer, comment="Sessão legislativa da iniciativa (XML: iniSel)")
    data_inicio_leg = Column(
        Date, comment="Data de Inicio da Legislatura (XML: dataInicioleg)"
    )
    data_fim_leg = Column(Date, comment="Data de Fim da Legislatura (XML: dataFimleg)")
    ini_titulo = Column(Text, comment="Titulo da Iniciativa (XML: iniTitulo)")
    ini_texto_subst = Column(
        Text, comment="Indica se tem texto de substituição (XML: iniTextoSubst)"
    )
    ini_texto_subst_campo = Column(
        Text,
        comment="Observações sobre substituição do ficheiro (XML: iniTextoSubstCampo)",
    )
    ini_link_texto = Column(
        Text, comment="Link para o texto da iniciativa (XML: iniLinkTexto)"
    )
    ini_obs = Column(Text, comment="Observações associadas (XML: iniObs)")
    legislatura_id = Column(GUID(), ForeignKey("legislaturas.id"), nullable=False)
    updated_at = Column(DateTime, default=func.now, onupdate=func.now)

    # Data provenance tracking
    import_status_id = Column(
        GUID(),
        ForeignKey("import_status.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Reference to import batch that created/updated this record"
    )

    # Relationships
    legislatura = relationship("Legislatura", backref="iniciativas")
    autores_outros = relationship(
        "IniciativaAutorOutro",
        back_populates="iniciativa",
        cascade="all, delete-orphan",
    )
    autores_deputados = relationship(
        "IniciativaAutorDeputado",
        back_populates="iniciativa",
        cascade="all, delete-orphan",
    )
    autores_grupos = relationship(
        "IniciativaAutorGrupoParlamentar",
        back_populates="iniciativa",
        cascade="all, delete-orphan",
    )
    propostas_alteracao = relationship(
        "IniciativaPropostaAlteracao",
        back_populates="iniciativa",
        cascade="all, delete-orphan",
    )
    eventos = relationship(
        "IniciativaEvento", back_populates="iniciativa", cascade="all, delete-orphan"
    )
    origens = relationship(
        "IniciativaOrigem", back_populates="iniciativa", cascade="all, delete-orphan"
    )
    originadas = relationship(
        "IniciativaOriginada", back_populates="iniciativa", cascade="all, delete-orphan"
    )


class IniciativaAutorOutro(Base):
    __tablename__ = "iniciativas_autores_outros"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    iniciativa_id = Column(
        GUID(), ForeignKey("iniciativas_detalhadas.id"), nullable=False
    )
    sigla = Column(Text)
    nome = Column(Text)

    # Relationships
    iniciativa = relationship("IniciativaParlamentar", back_populates="autores_outros")


class IniciativaAutorDeputado(Base):
    __tablename__ = "iniciativas_autores_deputados"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    iniciativa_id = Column(
        GUID(), ForeignKey("iniciativas_detalhadas.id"), nullable=False
    )
    id_cadastro = Column(Integer)
    nome = Column(Text)
    gp = Column(Text)

    # Relationships
    iniciativa = relationship(
        "IniciativaParlamentar", back_populates="autores_deputados"
    )


class IniciativaAutorGrupoParlamentar(Base):
    __tablename__ = "iniciativas_autores_grupos_parlamentares"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    iniciativa_id = Column(
        GUID(), ForeignKey("iniciativas_detalhadas.id"), nullable=False
    )
    gp = Column(Text)

    # Relationships
    iniciativa = relationship("IniciativaParlamentar", back_populates="autores_grupos")


class IniciativaPropostaAlteracao(Base):
    __tablename__ = "iniciativas_propostas_alteracao"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    iniciativa_id = Column(
        GUID(), ForeignKey("iniciativas_detalhadas.id"), nullable=False
    )
    proposta_id = Column(Integer)
    tipo = Column(Text)
    autor = Column(Text)

    # Relationships
    iniciativa = relationship(
        "IniciativaParlamentar", back_populates="propostas_alteracao"
    )
    publicacoes = relationship(
        "IniciativaPropostaAlteracaoPublicacao",
        back_populates="proposta",
        cascade="all, delete-orphan",
    )


class IniciativaPropostaAlteracaoPublicacao(Base):
    __tablename__ = "iniciativas_propostas_alteracao_publicacoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    proposta_id = Column(
        GUID(), ForeignKey("iniciativas_propostas_alteracao.id"), nullable=False
    )
    pub_nr = Column(Integer)
    pub_tipo = Column(Text)
    pub_tp = Column(Text)
    pub_leg = Column(Text)
    pub_sl = Column(Integer)
    pub_dt = Column(Date)
    pag = Column(Text)
    id_pag = Column(Integer)
    url_diario = Column(Text)

    # Relationships
    proposta = relationship("IniciativaPropostaAlteracao", back_populates="publicacoes")


class IniciativaEvento(Base):
    __tablename__ = "iniciativas_eventos"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    iniciativa_id = Column(
        GUID(), ForeignKey("iniciativas_detalhadas.id"), nullable=False
    )
    oev_id = Column(Integer)
    data_fase = Column(Date)
    fase = Column(Text)
    evt_id = Column(Integer)
    codigo_fase = Column(Integer)
    obs_fase = Column(Text)
    act_id = Column(Integer)
    oev_text_id = Column(Integer)
    textos_aprovados = Column(Text)

    # Relationships
    iniciativa = relationship("IniciativaParlamentar", back_populates="eventos")
    publicacoes = relationship(
        "IniciativaEventoPublicacao",
        back_populates="evento",
        cascade="all, delete-orphan",
    )
    votacoes = relationship(
        "IniciativaEventoVotacao", back_populates="evento", cascade="all, delete-orphan"
    )
    comissoes = relationship(
        "IniciativaEventoComissao",
        back_populates="evento",
        cascade="all, delete-orphan",
    )
    recursos_gp = relationship(
        "IniciativaEventoRecursoGP",
        back_populates="evento",
        cascade="all, delete-orphan",
    )
    recursos_deputados = relationship(
        "IniciativaEventoRecursoDeputado",
        back_populates="evento",
        cascade="all, delete-orphan",
    )
    iniciativas_conjuntas = relationship(
        "IniciativaConjunta", back_populates="evento", cascade="all, delete-orphan"
    )
    intervencoes_debates = relationship(
        "IniciativaIntervencaoDebate",
        back_populates="evento",
        cascade="all, delete-orphan",
    )
    anexos_fase = relationship(
        "IniciativaEventoAnexo", back_populates="evento", cascade="all, delete-orphan"
    )

    # Indexes for performance optimization
    __table_args__ = (
        Index("idx_eventos_iniciativa_id", "iniciativa_id"),
        Index("idx_eventos_data_fase", "data_fase"),
        Index("idx_eventos_oev_id", "oev_id"),
        Index("idx_eventos_evt_id", "evt_id"),
        Index("idx_eventos_codigo_fase", "codigo_fase"),
        Index("idx_eventos_iniciativa_data_composite", "iniciativa_id", "data_fase"),
    )


class IniciativaEventoPublicacao(Base):
    """
    Initiative Event Publication Model - Based on PublicacoesOut specification

    Publication Mapping (PublicacoesOut):
    - pubNr: pub_nr (Número da Publicação)
    - pubTipo: pub_tipo (Descrição do Tipo de Publicação)
    - pubTp: pub_tp (Abreviatura do Tipo de Publicação)
    - pubLeg: pub_leg (Legislatura em que ocorreu a Publicação)
    - pubSL: pub_sl (Sessão legislativa em que ocorreu a Publicação)
    - pubdt: pub_dt (Data da Publicação)
    - pag: pag (Páginas)
    - idPag: id_pag (Identificador da Paginação)
    - idInt: id_int (Identificador da Intervenção associada à Publicação)
    - URLDiario: url_diario (Link para o DAR da Publicação)

    Additional Fields from Specification:
    - idAct: Identificador da Atividade associada à Publicação
    - idDeb: Identificador do Debate associado à Publicação
    - obs: Observações
    - pagFinalDiarioSupl: Página final do suplemento
    - Supl: Suplemento da Publicação
    - debateDtReu: Data da reunião plenária onde ocorreu o Debate
    """

    __tablename__ = "iniciativas_eventos_publicacoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    evento_id = Column(GUID(), ForeignKey("iniciativas_eventos.id"), nullable=False)
    pub_nr = Column(Integer, comment="Número da Publicação (XML: pubNr)")
    pub_tipo = Column(Text, comment="Descrição do Tipo de Publicação (XML: pubTipo)")
    pub_tp = Column(Text, comment="Abreviatura do Tipo de Publicação (XML: pubTp)")
    pub_leg = Column(
        Text, comment="Legislatura em que ocorreu a Publicação (XML: pubLeg)"
    )
    pub_sl = Column(
        Integer, comment="Sessão legislativa em que ocorreu a Publicação (XML: pubSL)"
    )
    pub_dt = Column(Date, comment="Data da Publicação (XML: pubdt)")
    pag = Column(Text, comment="Páginas (XML: pag)")
    id_pag = Column(Integer, comment="Identificador da Paginação (XML: idPag)")
    id_int = Column(
        Integer,
        comment="Identificador da Intervenção associada à Publicação (XML: idInt)",
    )
    url_diario = Column(Text, comment="Link para o DAR da Publicação (XML: URLDiario)")

    # Relationships
    evento = relationship("IniciativaEvento", back_populates="publicacoes")


class IniciativaEventoVotacao(Base):
    __tablename__ = "iniciativas_eventos_votacoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    evento_id = Column(GUID(), ForeignKey("iniciativas_eventos.id"), nullable=False)
    id_votacao = Column(Integer)
    resultado = Column(Text)
    desc = Column(Text)  # Voting description (desc field from XML)
    a_favor = Column(Integer)  # Votes in favor
    contra = Column(Integer)  # Votes against
    abstencao = Column(Integer)  # Abstentions
    reuniao = Column(Integer)
    tipo_reuniao = Column(Text)
    detalhe = Column(Text)
    unanime = Column(Text)
    data_votacao = Column(Date)
    descricao = Column(Text)  # Voting description (descricao field from XML)

    # Relationships
    evento = relationship("IniciativaEvento", back_populates="votacoes")
    ausencias = relationship(
        "IniciativaVotacaoAusencia",
        back_populates="votacao",
        cascade="all, delete-orphan",
    )
    publicacoes = relationship(
        "IniciativaVotacaoPublicacao",
        back_populates="votacao",
        cascade="all, delete-orphan",
    )

    # Indexes for performance optimization
    __table_args__ = (
        Index("idx_votacoes_data_votacao", "data_votacao"),
        Index("idx_votacoes_evento_id", "evento_id"),
    )


class IniciativaVotacaoAusencia(Base):
    __tablename__ = "iniciativas_votacoes_ausencias"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    votacao_id = Column(
        GUID(), ForeignKey("iniciativas_eventos_votacoes.id"), nullable=False
    )
    grupo_parlamentar = Column(Text)

    # Relationships
    votacao = relationship("IniciativaEventoVotacao", back_populates="ausencias")


class IniciativaVotacaoPublicacao(Base):
    """Publications associated with voting records in legislative initiatives"""

    __tablename__ = "iniciativas_votacoes_publicacoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    votacao_id = Column(
        GUID(), ForeignKey("iniciativas_eventos_votacoes.id"), nullable=False
    )

    # Publication fields from publicacao.pt_gov_ar_objectos_PublicacoesOut
    pub_nr = Column(Integer)  # Publication number
    pub_tipo = Column(Text)  # Publication type (e.g., "DAR I série")
    pub_tp = Column(Text)  # Publication type code (e.g., "D")
    pub_leg = Column(Text)  # Legislature (e.g., "II")
    pub_sl = Column(Integer)  # Session number
    pub_dt = Column(Date)  # Publication date
    pag = Column(Text)  # Page numbers (can be range like "73-74")
    id_pag = Column(Integer)  # Internal page ID
    url_diario = Column(Text)  # URL to parliamentary diary

    # Relationships
    votacao = relationship("IniciativaEventoVotacao", back_populates="publicacoes")


class IniciativaEventoComissao(Base):
    __tablename__ = "iniciativas_eventos_comissoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    evento_id = Column(GUID(), ForeignKey("iniciativas_eventos.id"), nullable=False)
    acc_id = Column(Integer)
    numero = Column(Integer)
    id_comissao = Column(Integer)
    nome = Column(Text)
    competente = Column(Text)
    data_distribuicao = Column(Date)
    data_entrada = Column(Date)
    data_agendamento_plenario = Column(Text)
    data_motivo_nao_parecer = Column(Date)  # XII Legislature - DataMotivoNaoParecer
    motivo_nao_parecer = Column(Text)  # XII Legislature - MotivoNaoParecer
    # Additional fields from XML
    data_relatorio = Column(Date)  # dataRelatorio from XML
    data_parecer = Column(Date)  # dataParecer from XML
    obs = Column(Text)  # obs from XML
    link_parecer = Column(Text)  # linkParecer from XML

    # Relationships
    evento = relationship("IniciativaEvento", back_populates="comissoes")
    publicacoes = relationship(
        "IniciativaComissaoPublicacao",
        back_populates="comissao",
        cascade="all, delete-orphan",
    )
    relatores = relationship(
        "IniciativaComissaoRelator",
        back_populates="comissao",
        cascade="all, delete-orphan",
    )
    remessas = relationship(
        "IniciativaComissaoRemessa",
        back_populates="comissao",
        cascade="all, delete-orphan",
    )


class IniciativaComissaoPublicacao(Base):
    __tablename__ = "iniciativas_comissoes_publicacoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    comissao_id = Column(
        GUID(), ForeignKey("iniciativas_eventos_comissoes.id"), nullable=False
    )
    tipo = Column(Text)  # Publication type (e.g., "Publicacao", "PublicacaoRelatorio")
    pub_nr = Column(Integer)
    pub_tipo = Column(Text)
    pub_tp = Column(Text)
    pub_leg = Column(Text)
    pub_sl = Column(Integer)
    pub_dt = Column(Date)
    pag = Column(Text)
    id_pag = Column(Integer)
    id_int = Column(Integer)  # Internal ID field
    url_diario = Column(Text)
    obs = Column(Text)  # Observatory field found in PublicacaoRelatorio

    # Relationships
    comissao = relationship("IniciativaEventoComissao", back_populates="publicacoes")


class IniciativaComissaoRelator(Base):
    """Committee reporters for legislative initiatives - tracks who reports on initiatives in committees"""

    __tablename__ = "iniciativas_comissoes_relatores"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    comissao_id = Column(
        GUID(), ForeignKey("iniciativas_eventos_comissoes.id"), nullable=False
    )

    # Reporter fields from Relatores.pt_gov_ar_objectos_RelatoresOut
    relator_id = Column(Integer)  # Internal reporter ID
    nome = Column(Text)  # Reporter name
    gp = Column(Text)  # Parliamentary group (e.g., "PS", "PSD")
    data_nomeacao = Column(Date)  # Appointment date
    data_cessacao = Column(Date)  # End date of appointment

    # Relationships
    comissao = relationship("IniciativaEventoComissao", back_populates="relatores")


class IniciativaComissaoRemessa(Base):
    """Committee dispatches/referrals for legislative initiatives - tracks official communications"""

    __tablename__ = "iniciativas_comissoes_remessas"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    comissao_id = Column(
        GUID(), ForeignKey("iniciativas_eventos_comissoes.id"), nullable=False
    )

    # Dispatch fields from Remessas.pt_gov_ar_objectos_RemessasOut
    numero_oficio = Column(Text)  # Official document number
    data_remessa = Column(Date)  # Dispatch date
    destinatario = Column(Text)  # Recipient of the dispatch

    # Relationships
    comissao = relationship("IniciativaEventoComissao", back_populates="remessas")


class IniciativaIntervencaoOrador(Base):
    """Speakers data for legislative initiative interventions - detailed session speaker info"""

    __tablename__ = "iniciativas_intervencoes_oradores"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    intervencao_id = Column(
        GUID(), ForeignKey("iniciativas_intervencoes_debates.id"), nullable=False
    )

    # Speaker timing and session details from pt_gov_ar_objectos_peticoes_OradoresOut
    hora_inicio = Column(Text)  # Starting time
    hora_termo = Column(Text)  # Ending time
    fase_sessao = Column(Text)  # Session phase
    sumario = Column(Text)  # Summary of intervention

    # Relationships
    intervencao = relationship("IniciativaIntervencaoDebate", back_populates="oradores")
    publicacoes = relationship(
        "IniciativaIntervencaoOradorPublicacao",
        back_populates="orador",
        cascade="all, delete-orphan",
    )
    convidados = relationship(
        "IniciativaIntervencaoOradorConvidado",
        back_populates="orador",
        cascade="all, delete-orphan",
    )
    membros_governo = relationship(
        "IniciativaIntervencaoOradorMembroGoverno",
        back_populates="orador",
        cascade="all, delete-orphan",
    )


class IniciativaIntervencaoOradorPublicacao(Base):
    """Publications associated with speaker interventions in legislative initiatives"""

    __tablename__ = "iniciativas_intervencoes_oradores_publicacoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    orador_id = Column(
        GUID(), ForeignKey("iniciativas_intervencoes_oradores.id"), nullable=False
    )

    # Publication fields from nested publicacao.pt_gov_ar_objectos_PublicacoesOut
    pub_nr = Column(Integer)  # Publication number
    pub_tipo = Column(Text)  # Publication type
    pub_tp = Column(Text)  # Publication subtype
    pub_leg = Column(Text)  # Legislature
    pub_sl = Column(Integer)  # Session or series number
    pub_dt = Column(Date)  # Publication date
    pag = Column(Text)  # Page numbers (comma-separated)
    id_pag = Column(Integer)  # Page ID
    id_int = Column(Integer)  # Internal ID field
    url_diario = Column(Text)  # Parliamentary diary URL

    # Relationships
    orador = relationship("IniciativaIntervencaoOrador", back_populates="publicacoes")


class IniciativaIntervencaoOradorConvidado(Base):
    """Guest speakers in legislative initiative interventions"""

    __tablename__ = "iniciativas_intervencoes_oradores_convidados"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    orador_id = Column(
        GUID(), ForeignKey("iniciativas_intervencoes_oradores.id"), nullable=False
    )

    # Guest details from convidados structure
    nome = Column(Text)  # Guest name
    cargo = Column(Text)  # Position/role
    entidade = Column(Text)  # Organization/entity

    # Relationships
    orador = relationship("IniciativaIntervencaoOrador", back_populates="convidados")


class IniciativaIntervencaoOradorMembroGoverno(Base):
    """Government members speaking in legislative initiative interventions"""

    __tablename__ = "iniciativas_intervencoes_oradores_membros_governo"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    orador_id = Column(
        GUID(), ForeignKey("iniciativas_intervencoes_oradores.id"), nullable=False
    )

    # Government member details from membrosGoverno structure
    nome = Column(Text)  # Member name
    cargo = Column(Text)  # Government position
    governo = Column(Text)  # Government/Ministry

    # Relationships
    orador = relationship(
        "IniciativaIntervencaoOrador", back_populates="membros_governo"
    )


class IniciativaEventoRecursoGP(Base):
    __tablename__ = "iniciativas_eventos_recursos_gp"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    evento_id = Column(GUID(), ForeignKey("iniciativas_eventos.id"), nullable=False)
    grupo_parlamentar = Column(Text)

    # Relationships
    evento = relationship("IniciativaEvento", back_populates="recursos_gp")


class IniciativaEventoRecursoDeputado(Base):
    __tablename__ = "iniciativas_eventos_recursos_deputados"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    evento_id = Column(GUID(), ForeignKey("iniciativas_eventos.id"), nullable=False)
    deputado_info = Column(Text)  # String information about deputy

    # Relationships
    evento = relationship("IniciativaEvento", back_populates="recursos_deputados")


class IniciativaEventoAnexo(Base):
    """Phase attachments for initiative events (AnexosFase) - IX Legislature feature"""

    __tablename__ = "iniciativas_eventos_anexos"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    evento_id = Column(GUID(), ForeignKey("iniciativas_eventos.id"), nullable=False)

    # Attachment fields from AnexosFase.pt_gov_ar_objectos_iniciativas_AnexosOut
    anexo_id = Column(Integer)  # Internal attachment ID
    anexo_nome = Column(Text)  # Attachment name/title
    anexo_fich = Column(Text)  # File path/name
    link = Column(Text)  # Link to attachment

    # Relationships
    evento = relationship("IniciativaEvento", back_populates="anexos_fase")


class IniciativaConjunta(Base):
    __tablename__ = "iniciativas_conjuntas"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    evento_id = Column(GUID(), ForeignKey("iniciativas_eventos.id"), nullable=False)
    nr = Column(Integer)
    tipo = Column(Text)
    desc_tipo = Column(Text)
    leg = Column(Text)
    sel = Column(Integer)
    titulo = Column(Text)
    ini_id = Column(Integer)

    # Relationships
    evento = relationship("IniciativaEvento", back_populates="iniciativas_conjuntas")


class IniciativaIntervencaoDebate(Base):
    __tablename__ = "iniciativas_intervencoes_debates"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    evento_id = Column(GUID(), ForeignKey("iniciativas_eventos.id"), nullable=False)
    data_reuniao_plenaria = Column(Date)

    # Relationships
    evento = relationship("IniciativaEvento", back_populates="intervencoes_debates")
    oradores = relationship(
        "IniciativaIntervencaoOrador",
        back_populates="intervencao",
        cascade="all, delete-orphan",
    )


class IniciativaAnexo(Base):
    """Attachments/Annexes for legislative initiatives"""

    __tablename__ = "iniciativas_anexos"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    iniciativa_id = Column(
        GUID(), ForeignKey("iniciativas_detalhadas.id"), nullable=False
    )

    # Attachment fields from IniAnexos.pt_gov_ar_objectos_iniciativas_AnexosOut
    anexo_id = Column(Integer)  # Internal attachment ID
    anexo_nome = Column(Text)  # Attachment name
    anexo_fich = Column(Text)  # File path/name
    link = Column(Text)  # Link to attachment

    # Optional link to event phase (AnexosFase - IX Legislature feature)
    fase_evento_id = Column(GUID(), ForeignKey("iniciativas_eventos.id"), nullable=True)

    # Relationships
    iniciativa = relationship("IniciativaParlamentar", backref="anexos")
    fase_evento = relationship("IniciativaEvento", backref="iniciativa_anexos_fase")


class IniciativaOradorVideoLink(Base):
    """Video links for speaker interventions in legislative initiatives"""

    __tablename__ = "iniciativas_oradores_video_links"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    orador_id = Column(
        GUID(), ForeignKey("iniciativas_intervencoes_oradores.id"), nullable=False
    )

    # Video link fields from linkVideo.pt_gov_ar_objectos_peticoes_LinksVideos
    link_url = Column(Text)  # Video URL
    descricao = Column(Text)  # Video description

    # Relationships
    orador = relationship("IniciativaIntervencaoOrador", backref="video_links")


class IniciativaComissaoDistribuicaoSubcomissao(Base):
    """Subcommission distribution data for legislative initiative committees"""

    __tablename__ = "iniciativas_comissoes_distribuicao_subcomissao"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    comissao_id = Column(
        GUID(), ForeignKey("iniciativas_eventos_comissoes.id"), nullable=False
    )

    # Subcommission distribution fields from DistribuicaoSubcomissao.pt_gov_ar_objectos_ComissoesOut
    subcomissao_id = Column(Integer)  # Subcommission ID
    sigla = Column(Text)  # Subcommission abbreviation
    nome = Column(Text)  # Subcommission name
    data_distribuicao = Column(Date)  # Distribution date

    # Relationships
    comissao = relationship(
        "IniciativaEventoComissao", backref="distribuicoes_subcomissao"
    )


class IniciativaEventoComissaoVotacao(Base):
    """Committee voting data for legislative initiative events"""

    __tablename__ = "iniciativas_eventos_comissoes_votacoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    comissao_id = Column(
        GUID(), ForeignKey("iniciativas_eventos_comissoes.id"), nullable=True
    )

    # Committee voting fields from Comissao.Votacao.pt_gov_ar_objectos_VotacaoOut
    id_votacao = Column(Integer)  # Voting ID
    resultado = Column(Text)  # Voting result
    reuniao = Column(Integer)  # Meeting number
    tipo_reuniao = Column(Text)  # Meeting type
    detalhe = Column(Text)  # Voting details
    unanime = Column(Text)  # Unanimous vote indicator
    data_votacao = Column(Date)  # Voting date
    ausencias = Column(Text)  # Absences data
    descricao = Column(Text)  # Voting description

    # Relationships
    comissao = relationship("IniciativaEventoComissao", backref="votacoes")


class IniciativaComissaoDocumento(Base):
    """Committee documents for legislative initiatives - tracks official documents processed by committees"""

    __tablename__ = "iniciativas_comissoes_documentos"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    comissao_id = Column(
        GUID(), ForeignKey("iniciativas_eventos_comissoes.id"), nullable=False
    )

    # Document fields from Documentos.DocsOut
    titulo_documento = Column(Text)  # Document title (docNome)
    tipo_documento = Column(Text)  # Document type (docTipo)
    doc_link = Column(Text)  # Link to document

    # Relationships
    comissao = relationship("IniciativaEventoComissao", backref="documentos")


class IniciativaComissaoAudiencia(Base):
    """Committee hearings for legislative initiatives - tracks hearings and related activities"""

    __tablename__ = "iniciativas_comissoes_audiencias"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    comissao_id = Column(
        GUID(), ForeignKey("iniciativas_eventos_comissoes.id"), nullable=False
    )

    # Hearing fields from Audiencias.pt_gov_ar_objectos_iniciativas_ActividadesRelacionadasOut
    audiencia_id = Column(Integer)  # Hearing ID
    data = Column(Date)  # Hearing date (dataActividade)
    descricao = Column(Text)  # Description of the hearing

    # Relationships
    comissao = relationship("IniciativaEventoComissao", backref="audiencias")


class IniciativaComissaoAudicao(Base):
    """Committee hearings/auditions for legislative initiatives - tracks auditions and related activities"""

    __tablename__ = "iniciativas_comissoes_audicoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    comissao_id = Column(
        GUID(), ForeignKey("iniciativas_eventos_comissoes.id"), nullable=False
    )

    # Audition fields from Audicoes.pt_gov_ar_objectos_iniciativas_ActividadesRelacionadasOut
    data = Column(Date)  # Audition date (dataActividade)
    descricao = Column(Text)  # Description of the audition

    # Relationships
    comissao = relationship("IniciativaEventoComissao", backref="audicoes")


class IniciativaEventoPeticaoConjunta(Base):
    """Joint petitions for legislative initiative events - tracks petitions discussed together"""

    __tablename__ = "iniciativas_eventos_peticoes_conjuntas"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    evento_id = Column(GUID(), ForeignKey("iniciativas_eventos.id"), nullable=False)

    # Joint petition fields from PeticoesConjuntas.pt_gov_ar_objectos_iniciativas_DiscussaoConjuntaOut
    leg = Column(Text)  # Legislature
    nr = Column(Integer)  # Petition number
    titulo = Column(Text)  # Petition title

    # Additional fields from IX Legislature format
    peticao_id = Column(Integer)  # iniId - Internal petition ID
    peticao_titulo = Column(Text)  # iniTitulo - Petition title (alternative field)
    peticao_nr = Column(Text)  # iniNr - Petition number as text
    peticao_tipo = Column(Text)  # iniTipo - Petition type

    # Relationships
    evento = relationship("IniciativaEvento", backref="peticoes_conjuntas")


class IniciativaPeticao(Base):
    """Petitions associated with legislative initiatives - general petition data"""

    __tablename__ = "iniciativas_peticoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    iniciativa_id = Column(
        GUID(), ForeignKey("iniciativas_detalhadas.id"), nullable=False
    )

    # Petition fields from Peticoes.pt_gov_ar_objectos_iniciativas_DadosGeraisOut
    numero = Column(Integer)  # Petition number

    # Relationships
    iniciativa = relationship("IniciativaParlamentar", backref="peticoes")


class IniciativaEuropeia(Base):
    """European initiatives as string data - simple string references to European initiatives"""

    __tablename__ = "iniciativas_europeias_simples"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    iniciativa_id = Column(
        GUID(), ForeignKey("iniciativas_detalhadas.id"), nullable=False
    )

    # European initiative as string from IniciativasEuropeias.string
    referencia = Column(Text)  # String reference to European initiative

    # Relationships
    iniciativa = relationship(
        "IniciativaParlamentar", backref="iniciativas_europeias_simples"
    )


class IniciativaLink(Base):
    """Document links for legislative initiatives - tracks related documents with URLs and metadata"""

    __tablename__ = "iniciativas_links"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    iniciativa_id = Column(
        GUID(), ForeignKey("iniciativas_detalhadas.id"), nullable=False
    )

    # Document link fields from Links.DocsOut
    titulo_documento = Column(Text)  # Document title
    data_documento = Column(Date)  # Document date
    url = Column(Text)  # Document URL

    # Relationships
    iniciativa = relationship("IniciativaParlamentar", backref="links")


# Petition models
class PeticaoParlamentar(Base):
    """
    Parliamentary Petitions Model - Based on Peticoes_DetalhePesquisaPeticoesOut specification

    Contains comprehensive petition information following the official Parliament documentation.
    Maps to the complete Peticoes<Legislatura>.xml structure including all lifecycle tracking.

    Peticoes_DetalhePesquisaPeticoesOut Mapping:
    - petId: pet_id (Petition identifier)
    - petNr: pet_nr (Petition number)
    - petLeg: pet_leg (Legislature designation)
    - petSel: pet_sel (Legislative session)
    - petAssunto: pet_assunto (Petition subject/topic)
    - petSituacao: pet_situacao (Current status of petition)
    - petNrAssinaturas: pet_nr_assinaturas (Number of signatures)
    - petDataEntrada: pet_data_entrada (Entry date)
    - petActividadeId: pet_atividade_id (Associated activity identifier)
    - petAutor: pet_autor (Petition author/submitter)
    - dataDebate: data_debate (Debate date)
    - petObs: pet_obs (Observations - IX Legislature)
    - iniciativasConjuntas: iniciativas_conjuntas (Joint initiatives - XIII Legislature)
    - peticoesAssociadas: peticoes_associadas (Associated petitions - XIII Legislature)
    - petNrAssinaturasInicial: pet_nr_assinaturas_inicial (Initial signature count - XIII Legislature)
    - iniciativasOriginadas: iniciativas_originadas (Originated initiatives - XIII Legislature)

    Related Structures:
    - Peticoes_ComissoesPetOut: Committee handling data (relationship: comissoes)
    - DocsOut: Document management (relationship: documentos)
    - IntervencoesOut: Interventions and debates (relationship: intervencoes)
    - VotacaoOut: Voting results (via committee relationships)
    - PublicacoesOut: Publications using TipodePublicacao enum (relationship: publicacoes)

    Usage:
        Core container for petition lifecycle tracking with comprehensive audit trail
        References: Multiple committee assignments, voting records, debate interventions
    """

    __tablename__ = "peticoes_detalhadas"
    __table_args__ = (
        Index("idx_peticao_pet_id", "pet_id"),
        Index("idx_peticao_legislatura", "legislatura_id"),
        # Note: pet_situacao is TEXT field, would need length specification for MySQL
        # Index('idx_peticao_situacao', text('pet_situacao(20)')),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    pet_id = Column(
        Integer, unique=True, nullable=False, comment="Petition identifier (XML: petId)"
    )
    pet_nr = Column(Integer, comment="Petition number (XML: petNr)")
    pet_leg = Column(Text, comment="Legislature designation (XML: petLeg)")
    pet_sel = Column(Integer, comment="Legislative session (XML: petSel)")
    pet_assunto = Column(Text, comment="Petition subject/topic (XML: petAssunto)")
    pet_situacao = Column(Text, comment="Current status of petition (XML: petSituacao)")
    pet_nr_assinaturas = Column(
        Integer, comment="Number of signatures (XML: petNrAssinaturas)"
    )
    pet_data_entrada = Column(Date, comment="Entry date (XML: petDataEntrada)")
    pet_atividade_id = Column(
        Integer, comment="Associated activity identifier (XML: petActividadeId)"
    )
    pet_autor = Column(Text, comment="Petition author/submitter (XML: petAutor)")
    data_debate = Column(Date, comment="Debate date (XML: dataDebate)")
    pet_obs = Column(Text, comment="Observations - IX Legislature (XML: petObs)")
    iniciativas_conjuntas = Column(
        Text, comment="Joint initiatives - XIII Legislature (XML: iniciativasConjuntas)"
    )
    peticoes_associadas = Column(
        Text,
        comment="Associated petitions - XIII Legislature (XML: peticoesAssociadas)",
    )
    pet_nr_assinaturas_inicial = Column(
        Integer,
        comment="Initial signature count - XIII Legislature (XML: petNrAssinaturasInicial)",
    )
    iniciativas_originadas = Column(
        Text,
        comment="Originated initiatives - XIII Legislature (XML: iniciativasOriginadas)",
    )
    legislatura_id = Column(
        GUID(),
        ForeignKey("legislaturas.id"),
        nullable=False,
        comment="Legislature foreign key reference",
    )
    updated_at = Column(DateTime, default=func.now, onupdate=func.now)

    # Data provenance tracking
    import_status_id = Column(
        GUID(),
        ForeignKey("import_status.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Reference to import batch that created/updated this record"
    )

    # Relationships
    legislatura = relationship("Legislatura", backref="peticoes")
    publicacoes = relationship(
        "PeticaoPublicacao", back_populates="peticao", cascade="all, delete-orphan"
    )
    comissoes = relationship(
        "PeticaoComissao", back_populates="peticao", cascade="all, delete-orphan"
    )
    documentos = relationship(
        "PeticaoDocumento", back_populates="peticao", cascade="all, delete-orphan"
    )
    intervencoes = relationship(
        "PeticaoIntervencao", back_populates="peticao", cascade="all, delete-orphan"
    )
    pedidos_esclarecimento = relationship(
        "PeticaoPedidoEsclarecimento",
        back_populates="peticao",
        cascade="all, delete-orphan",
    )
    links = relationship(
        "PeticaoLink", back_populates="peticao", cascade="all, delete-orphan"
    )


class PeticaoLink(Base):
    """Links associated with petitions (XIII Legislature)"""

    __tablename__ = "peticoes_links"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    peticao_id = Column(GUID(), ForeignKey("peticoes_detalhadas.id"), nullable=False)
    tipo_documento = Column(Text)  # TipoDocumento from PeticaoDocsOut
    titulo_documento = Column(Text)  # TituloDocumento from PeticaoDocsOut
    data_documento = Column(Date)  # DataDocumento from PeticaoDocsOut
    url = Column(Text)  # URL from PeticaoDocsOut

    # Relationships
    peticao = relationship("PeticaoParlamentar", back_populates="links")


class PeticaoPublicacao(Base):
    """
    Petition Publications Model - Based on PublicacoesOut specification

    Manages publication records for petitions using the standard TipodePublicacao enum.
    Handles both PublicacaoPeticao and PublicacaoDebate types from the XML structure.

    PublicacoesOut Mapping:
    - pubNr: pub_nr (Publication number)
    - pubTipo: pub_tipo (Publication type description using TipodePublicacao)
    - pubTp: pub_tp (Publication type code using TipodePublicacao enum)
    - pubLeg: pub_leg (Publication legislature)
    - pubSL: pub_sl (Publication legislative session)
    - pubdt: pub_dt (Publication date)
    - pag: pag (Page numbers)
    - idPag: id_pag (Page identifier)
    - URLDiario: url_diario (Parliamentary diary URL)
    - supl: supl (Supplement designation - IX Legislature)
    - pagFinalDiarioSupl: pag_final_diario_supl (Final supplement page - IX Legislature)
    - obs: obs (Observations - XIV Legislature)

    Usage:
        Tracks all publication records for petition lifecycle phases
        References: TipodePublicacao enum for type standardization
    """

    __tablename__ = "peticoes_publicacoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    peticao_id = Column(
        GUID(),
        ForeignKey("peticoes_detalhadas.id"),
        nullable=False,
        comment="Petition foreign key reference",
    )
    tipo = Column(
        Text, comment="Publication category (PublicacaoPeticao or PublicacaoDebate)"
    )
    pub_nr = Column(Integer, comment="Publication number (XML: pubNr)")
    pub_tipo = Column(
        Text,
        comment="Publication type description using TipodePublicacao (XML: pubTipo)",
    )
    pub_tp = Column(
        Text, comment="Publication type code using TipodePublicacao enum (XML: pubTp)"
    )
    pub_leg = Column(Text, comment="Publication legislature (XML: pubLeg)")
    pub_sl = Column(Integer, comment="Publication legislative session (XML: pubSL)")
    pub_dt = Column(Date, comment="Publication date (XML: pubdt)")
    pag = Column(Text, comment="Page numbers (XML: pag)")
    id_pag = Column(Integer, comment="Page identifier (XML: idPag)")
    url_diario = Column(Text, comment="Parliamentary diary URL (XML: URLDiario)")
    supl = Column(Text, comment="Supplement designation - IX Legislature (XML: supl)")
    pag_final_diario_supl = Column(
        Text, comment="Final supplement page - IX Legislature (XML: pagFinalDiarioSupl)"
    )
    obs = Column(Text, comment="Observations - XIV Legislature (XML: obs)")

    # Relationships
    peticao = relationship("PeticaoParlamentar", back_populates="publicacoes")


class PeticaoComissao(Base):
    """
    Petition Committee Model - Based on Peticoes_ComissoesPetOut specification

    Manages committee assignment and processing workflow for petitions.
    Tracks complete committee lifecycle including admissibility, transfers, and archiving.

    Peticoes_ComissoesPetOut Mapping:
    - legislatura: legislatura (Committee legislature)
    - numero: numero (Committee number)
    - idComissao: id_comissao (Committee identifier)
    - nome: nome (Committee name)
    - admissibilidade: admissibilidade (Admissibility status)
    - dataAdmissibilidade: data_admissibilidade (Admissibility decision date)
    - dataEnvioPar: data_envio_par (Date sent to Parliament)
    - dataArquivo: data_arquivo (Archive date)
    - situacao: situacao (Current processing status)
    - dataReaberta: data_reaberta (Reopening date)
    - dataBaixaComissao: data_baixa_comissao (Committee discharge date)
    - transitada: transitada (Transfer status)

    Related Structures:
    - RelatoresOut: Committee reporters (relationship: relatores)
    - RelatoriosFinaisOut: Final reports and voting (relationship: relatorios_finais)
    - DocsOut: Committee documents (relationship: documentos)
    - TipodeReuniao: Meeting type enum for committee sessions

    Usage:
        Central workflow management for petition committee processing
        References: Multiple committee handling across different legislatures
    """

    __tablename__ = "peticoes_comissoes"
    __table_args__ = (
        Index("idx_peticao_comissao_peticao", "peticao_id"),
        # Note: legislatura is TEXT field, MySQL indexes need length specification
        # Index('idx_peticao_comissao_legislatura', text('legislatura(10)')),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    peticao_id = Column(
        GUID(),
        ForeignKey("peticoes_detalhadas.id"),
        nullable=False,
        comment="Petition foreign key reference",
    )
    legislatura = Column(Text, comment="Committee legislature (XML: legislatura)")
    numero = Column(Integer, comment="Committee number (XML: numero)")
    id_comissao = Column(Integer, comment="Committee identifier (XML: idComissao)")
    nome = Column(Text, comment="Committee name (XML: nome)")
    admissibilidade = Column(
        Text, comment="Admissibility status (XML: admissibilidade)"
    )
    data_admissibilidade = Column(
        Date, comment="Admissibility decision date (XML: dataAdmissibilidade)"
    )
    data_envio_par = Column(Date, comment="Date sent to Parliament (XML: dataEnvioPar)")
    data_arquivo = Column(Date, comment="Archive date (XML: dataArquivo)")
    situacao = Column(Text, comment="Current processing status (XML: situacao)")
    data_reaberta = Column(Date, comment="Reopening date (XML: dataReaberta)")
    data_baixa_comissao = Column(
        Date, comment="Committee discharge date (XML: dataBaixaComissao)"
    )
    transitada = Column(Text, comment="Transfer status (XML: transitada)")

    # Relationships
    peticao = relationship("PeticaoParlamentar", back_populates="comissoes")
    relatores = relationship(
        "PeticaoRelator", back_populates="comissao", cascade="all, delete-orphan"
    )
    relatorios_finais = relationship(
        "PeticaoRelatorioFinal", back_populates="comissao", cascade="all, delete-orphan"
    )
    documentos = relationship(
        "PeticaoDocumento",
        back_populates="comissao_peticao",
        cascade="all, delete-orphan",
    )
    audiencias = relationship(
        "PeticaoAudiencia", back_populates="comissao", cascade="all, delete-orphan"
    )
    pedidos_informacao = relationship(
        "PeticaoPedidoInformacao",
        back_populates="comissao",
        cascade="all, delete-orphan",
    )


class PeticaoRelator(Base):
    __tablename__ = "peticoes_relatores"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    comissao_peticao_id = Column(
        GUID(), ForeignKey("peticoes_comissoes.id"), nullable=False
    )
    relator_id = Column(Integer)
    nome = Column(Text)
    gp = Column(Text)
    data_nomeacao = Column(Date)
    data_cessacao = Column(Date)
    motivo_cessacao = Column(Text)  # motivoCessacao field from IX Legislature

    # Relationships
    comissao = relationship("PeticaoComissao", back_populates="relatores")


class PeticaoRelatorioFinal(Base):
    __tablename__ = "peticoes_relatorios_finais"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    comissao_peticao_id = Column(
        GUID(), ForeignKey("peticoes_comissoes.id"), nullable=False
    )
    data_relatorio = Column(Date)
    votacao = Column(Text)
    relatorio_final_id = Column(Text)

    # XII Legislature voting fields
    votacao_id = Column(Integer)  # votacao.id
    votacao_data = Column(Date)  # votacao.data
    votacao_unanime = Column(Boolean)  # votacao.unanime
    votacao_resultado = Column(Text)  # votacao.resultado
    votacao_reuniao = Column(Integer)  # votacao.reuniao
    votacao_tipo_reuniao = Column(Text)  # votacao.tipoReuniao

    # XIV Legislature additional voting fields
    votacao_ausencias = Column(Text)  # votacao.ausencias (comma-separated)
    votacao_detalhe = Column(Text)  # votacao.detalhe

    # XV Legislature additional voting field
    votacao_descricao = Column(Text)  # votacao.descricao

    # Relationships
    comissao = relationship("PeticaoComissao", back_populates="relatorios_finais")
    publicacoes = relationship(
        "PeticaoRelatorioFinalPublicacao",
        back_populates="relatorio_final",
        cascade="all, delete-orphan",
    )


class PeticaoRelatorioFinalPublicacao(Base):
    """Publications associated with final reports"""

    __tablename__ = "peticoes_relatorios_finais_publicacoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    relatorio_final_id = Column(
        GUID(), ForeignKey("peticoes_relatorios_finais.id"), nullable=False
    )
    pub_nr = Column(Integer)
    pub_tipo = Column(Text)
    pub_tp = Column(Text)
    pub_leg = Column(Text)
    pub_sl = Column(Integer)
    pub_dt = Column(Date)
    pag = Column(Text)
    id_pag = Column(Integer)
    url_diario = Column(Text)
    obs = Column(Text)  # obs field from XIII Legislature

    # Relationships
    relatorio_final = relationship(
        "PeticaoRelatorioFinal", back_populates="publicacoes"
    )


class PeticaoDocumento(Base):
    __tablename__ = "peticoes_documentos"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    peticao_id = Column(GUID(), ForeignKey("peticoes_detalhadas.id"), nullable=True)
    comissao_peticao_id = Column(
        GUID(), ForeignKey("peticoes_comissoes.id"), nullable=True
    )
    tipo_documento_categoria = Column(Text)
    titulo_documento = Column(Text)
    data_documento = Column(Date)
    tipo_documento = Column(Text)
    url = Column(Text)

    # Relationships
    peticao = relationship("PeticaoParlamentar", back_populates="documentos")
    comissao_peticao = relationship("PeticaoComissao", back_populates="documentos")


class PeticaoIntervencao(Base):
    __tablename__ = "peticoes_intervencoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    peticao_id = Column(GUID(), ForeignKey("peticoes_detalhadas.id"), nullable=False)
    data_reuniao_plenaria = Column(Date)

    # Relationships
    peticao = relationship("PeticaoParlamentar", back_populates="intervencoes")
    oradores = relationship(
        "PeticaoOrador", back_populates="intervencao", cascade="all, delete-orphan"
    )


class PeticaoOrador(Base):
    __tablename__ = "peticoes_oradores"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    intervencao_id = Column(
        GUID(), ForeignKey("peticoes_intervencoes.id"), nullable=False
    )
    fase_sessao = Column(Text)
    sumario = Column(Text)
    convidados = Column(Text)
    membros_governo = Column(Text)
    governo = Column(Text)  # MembrosGoverno.governo field
    membro_governo_nome = Column(Text)  # MembrosGoverno.nome field
    membro_governo_cargo = Column(Text)  # MembrosGoverno.cargo field
    deputado_id_cadastro = Column(Integer)  # Deputados.idCadastro field
    deputado_nome = Column(Text)  # Deputados.nome field
    teor = Column(Text)  # Teor field from IX Legislature
    fase_debate = Column(Text)  # FaseDebate field from VIII Legislature
    link_video = Column(Text)  # LinkVideo field from XIII Legislature

    # Relationships
    intervencao = relationship("PeticaoIntervencao", back_populates="oradores")
    publicacoes = relationship(
        "PeticaoOradorPublicacao", back_populates="orador", cascade="all, delete-orphan"
    )


class PeticaoOradorPublicacao(Base):
    __tablename__ = "peticoes_oradores_publicacoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    orador_id = Column(GUID(), ForeignKey("peticoes_oradores.id"), nullable=False)
    pub_nr = Column(Integer)
    pub_tipo = Column(Text)
    pub_tp = Column(Text)
    pub_leg = Column(Text)
    pub_sl = Column(Integer)
    pub_dt = Column(Date)
    pag = Column(Text)
    id_pag = Column(Integer)  # idPag field from IX Legislature
    id_int = Column(Integer)
    url_diario = Column(Text)

    # Relationships
    orador = relationship("PeticaoOrador", back_populates="publicacoes")


class PeticaoAudiencia(Base):
    """Hearings/audiencias for petition committee processing"""

    __tablename__ = "peticoes_audiencias"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    comissao_peticao_id = Column(
        GUID(), ForeignKey("peticoes_comissoes.id"), nullable=False
    )
    audiencia_id = Column(
        Integer
    )  # id from pt_gov_ar_objectos_peticoes_AudienciasDiligenciasOut.id
    data = Column(
        Date
    )  # Data from pt_gov_ar_objectos_peticoes_AudienciasDiligenciasOut.data
    titulo = Column(
        Text
    )  # Titulo from pt_gov_ar_objectos_peticoes_AudienciasDiligenciasOut.titulo
    tipo = Column(
        String(50), default="audiencia"
    )  # Type identifier: 'audiencia' or 'audicao'

    # Relationships
    comissao = relationship("PeticaoComissao", back_populates="audiencias")


class PeticaoPedidoInformacao(Base):
    """Information requests for petition committee processing"""

    __tablename__ = "peticoes_pedidos_informacao"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    comissao_peticao_id = Column(
        GUID(), ForeignKey("peticoes_comissoes.id"), nullable=False
    )
    nr_oficio = Column(
        Text
    )  # nrOficio from pt_gov_ar_objectos_peticoes_PedidosInformacaoOut.nrOficio
    entidades = Column(
        Text
    )  # entidades.string from pt_gov_ar_objectos_peticoes_PedidosInformacaoOut.entidades.string
    relatorio_intercalar = Column(Text)  # relatorioIntercalar field from IX Legislature
    data_resposta = Column(Date)  # dataResposta field from IX Legislature
    data_oficio = Column(Date)  # dataOficio field from IX Legislature

    # Relationships
    comissao = relationship("PeticaoComissao", back_populates="pedidos_informacao")
    pedidos_reiteracao = relationship(
        "PeticaoPedidoReiteracao",
        back_populates="pedido_informacao",
        cascade="all, delete-orphan",
    )


class PeticaoPedidoEsclarecimento(Base):
    """Clarification requests for petition processing (VI Legislature)"""

    __tablename__ = "peticoes_pedidos_esclarecimento"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    peticao_id = Column(GUID(), ForeignKey("peticoes_detalhadas.id"), nullable=False)
    nr_oficio = Column(
        Text
    )  # nrOficio from pt_gov_ar_objectos_peticoes_PedidosEsclarecimentoOut.nrOficio
    data_resposta = Column(
        Date
    )  # dataResposta from pt_gov_ar_objectos_peticoes_PedidosEsclarecimentoOut.dataResposta

    # Relationships
    peticao = relationship(
        "PeticaoParlamentar", back_populates="pedidos_esclarecimento"
    )


class PeticaoPedidoReiteracao(Base):
    """Reiteration requests for information requests"""

    __tablename__ = "peticoes_pedidos_reiteracao"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    pedido_informacao_id = Column(
        GUID(), ForeignKey("peticoes_pedidos_informacao.id"), nullable=False
    )
    data = Column(
        Date
    )  # data field from pt_gov_ar_objectos_peticoes_PedidosReiteracaoOut.data
    data_resposta = Column(
        Date
    )  # dataResposta field from pt_gov_ar_objectos_peticoes_PedidosReiteracaoOut.dataResposta
    nr_oficio = Column(Text)  # nrOficio field from IX Legislature
    oficio_resposta = Column(Text)  # oficioResposta field from IX Legislature
    data_oficio = Column(Date)  # dataOficio field from IX Legislature

    # Relationships
    pedido_informacao = relationship(
        "PeticaoPedidoInformacao", back_populates="pedidos_reiteracao"
    )


class IntervencaoParlamentar(Base):
    """
    Parliamentary Interventions
    ==========================

    Parliamentary interventions made by deputies during plenary sessions.
    Based on official Portuguese Parliament documentation (December 2017):
    "IntervencoesOut" structure from AtividadeDeputado documentation.

    Documentation Reference:
    - intId: "Identificador da intervenção" - Intervention identifier
    - intTe: "Resumo da Intervenção" - Intervention summary/abstract
    - intSu: "Sumário da intervenção" - Intervention summary
    - pubDtreu: "Data de publicação da reunião da intervenção" - Meeting publication date
    - pubTp: "Tipo de publicação da intervenção, campo tipo em TipodePublicacao" - Publication type (coded)
    - pubSup: "Suplemento onde foi publicada a intervenção" - Publication supplement
    - pubLg: "Legislatura" - Legislature
    - pubSl: "Sessão legislativa" - Legislative session
    - pubNr: "Número da publicação da intervenção" - Publication number
    - tinDs: "Tipo de intervenção" - Intervention type
    - pubDar: "Número do Diário da Assembleia da República da publicação da intervenção" - Assembly Diary number

    Translation Requirements:
    - pubTp: Use TipodePublicacao translator for publication types
    - tinDs: Intervention type descriptions
    """

    __tablename__ = "intervencao_parlamentar"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    legislatura_id = Column(
        GUID(),
        ForeignKey("legislaturas.id"),
        nullable=False,
        comment="Reference to legislature",
    )

    # Core fields from IntervencoesOut documentation
    intervencao_id = Column(
        Integer, unique=True, comment="Intervention identifier (intId)"
    )
    legislatura_numero = Column(String(50), comment="Legislature number (pubLg)")
    sessao_numero = Column(String(50), comment="Legislative session number (pubSl)")
    tipo_intervencao = Column(
        String(200), comment="Intervention type description (TipoIntervencao from XML)"
    )
    data_reuniao_plenaria = Column(
        Date, comment="Plenary meeting date (DataReuniaoPlenaria)"
    )
    qualidade = Column(String(100), comment="Intervention quality/context (Qualidade)")
    fase_sessao = Column(
        String(100), comment="Session phase when intervention occurred (FaseSessao)"
    )
    sumario = Column(Text, comment="Intervention summary (Sumario)")
    resumo = Column(Text, comment="Intervention abstract/resume (Resumo)")
    atividade_id = Column(Integer, comment="Related activity identifier (ActividadeId)")
    id_debate = Column(Integer, comment="Related debate identifier (IdDebate)")
    debate = Column(Text, comment="Debate description (Debate)")
    fase_debate = Column(Text, comment="Debate phase (FaseDebate)")

    # System tracking
    created_at = Column(
        DateTime, default=func.now(), comment="Record creation timestamp"
    )
    updated_at = Column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        comment="Record update timestamp",
    )

    # Data provenance tracking
    import_status_id = Column(
        GUID(),
        ForeignKey("import_status.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Reference to import batch that created/updated this record"
    )

    # Relationships following official documentation structure
    legislatura = relationship(
        "Legislatura",
        backref="intervencoes_parlamentares",
        doc="Legislature where intervention occurred",
    )

    publicacoes = relationship(
        "IntervencaoPublicacao",
        back_populates="intervencao",
        cascade="all, delete-orphan",
        doc="Publication details (pubTp, pubNr, pubDar, etc.)",
    )

    deputados = relationship(
        "IntervencaoDeputado",
        back_populates="intervencao",
        cascade="all, delete-orphan",
        doc="Deputies who made this intervention",
    )

    membros_governo = relationship(
        "IntervencaoMembroGoverno",
        back_populates="intervencao",
        cascade="all, delete-orphan",
        doc="Government members involved in intervention",
    )

    convidados = relationship(
        "IntervencaoConvidado",
        back_populates="intervencao",
        cascade="all, delete-orphan",
        doc="Invited guests who participated",
    )

    atividades_relacionadas = relationship(
        "IntervencaoAtividadeRelacionada",
        back_populates="intervencao",
        cascade="all, delete-orphan",
        doc="Related parliamentary activities",
    )

    iniciativas = relationship(
        "IntervencaoIniciativa",
        back_populates="intervencao",
        cascade="all, delete-orphan",
        doc="Related parliamentary initiatives",
    )

    audiovisuais = relationship(
        "IntervencaoAudiovisual",
        back_populates="intervencao",
        cascade="all, delete-orphan",
        doc="Audiovisual materials related to intervention",
    )


class IntervencaoPublicacao(Base):
    __tablename__ = "intervencao_publicacoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    intervencao_id = Column(
        GUID(), ForeignKey("intervencao_parlamentar.id"), nullable=False
    )

    pub_nr = Column(Integer)
    pub_tipo = Column(String(100))
    pub_tp = Column(String(50))
    pub_leg = Column(String(50))
    pub_sl = Column(Integer)
    pub_dt = Column(Date)
    pag = Column(Text)
    id_int = Column(Integer)
    url_diario = Column(Text)

    created_at = Column(DateTime, default=func.now())

    intervencao = relationship("IntervencaoParlamentar", back_populates="publicacoes")


class IntervencaoDeputado(Base):
    __tablename__ = "intervencao_deputados"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    intervencao_id = Column(
        GUID(), ForeignKey("intervencao_parlamentar.id"), nullable=False
    )
    deputado_id = Column(GUID(), ForeignKey("deputados.id"), nullable=True)

    id_cadastro = Column(Integer)
    nome = Column(String(200))
    gp = Column(String(50))  # Grupo Parlamentar

    created_at = Column(DateTime, default=func.now())

    intervencao = relationship("IntervencaoParlamentar", back_populates="deputados")
    deputado = relationship("Deputado", backref="intervencoes_parlamentares")


class IntervencaoMembroGoverno(Base):
    __tablename__ = "intervencao_membros_governo"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    intervencao_id = Column(
        GUID(), ForeignKey("intervencao_parlamentar.id"), nullable=False
    )

    nome = Column(String(200))
    cargo = Column(String(200))
    governo = Column(String(100))

    created_at = Column(DateTime, default=func.now())

    intervencao = relationship(
        "IntervencaoParlamentar", back_populates="membros_governo"
    )


class IntervencaoConvidado(Base):
    __tablename__ = "intervencao_convidados"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    intervencao_id = Column(
        GUID(), ForeignKey("intervencao_parlamentar.id"), nullable=False
    )

    nome = Column(String(200))
    cargo = Column(String(200))

    created_at = Column(DateTime, default=func.now())

    intervencao = relationship("IntervencaoParlamentar", back_populates="convidados")


class IntervencaoAtividadeRelacionada(Base):
    __tablename__ = "intervencao_atividades_relacionadas"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    intervencao_id = Column(
        GUID(), ForeignKey("intervencao_parlamentar.id"), nullable=False
    )

    atividade_id = Column(Integer)
    tipo = Column(Text)  # Changed from String(100) to Text for long initiative lists

    created_at = Column(DateTime, default=func.now())

    intervencao = relationship(
        "IntervencaoParlamentar", back_populates="atividades_relacionadas"
    )


class IntervencaoIniciativa(Base):
    __tablename__ = "intervencao_iniciativas"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    intervencao_id = Column(
        GUID(), ForeignKey("intervencao_parlamentar.id"), nullable=False
    )

    iniciativa_id = Column(Integer)
    tipo = Column(String(100))
    numero = Column(String(50))
    fase = Column(String(100))

    created_at = Column(DateTime, default=func.now())

    intervencao = relationship("IntervencaoParlamentar", back_populates="iniciativas")


class IntervencaoAudiovisual(Base):
    __tablename__ = "intervencao_audiovisuais"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    intervencao_id = Column(
        GUID(), ForeignKey("intervencao_parlamentar.id"), nullable=False
    )

    duracao = Column(String(50))
    assunto = Column(Text)
    url = Column(Text)
    tipo_intervencao = Column(String(200))
    video_url = Column(Text)  # Legacy field

    created_at = Column(DateTime, default=func.now())

    intervencao = relationship("IntervencaoParlamentar", back_populates="audiovisuais")


# =====================================================
# ORÇAMENTO E CONTAS DE GERÊNCIA
# =====================================================


class OrcamentoContasGerencia(Base):
    __tablename__ = "orcamento_contas_gerencia"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    entry_id = Column(Integer, nullable=False)  # id field from XML
    legislatura_id = Column(GUID(), ForeignKey("legislaturas.id"), nullable=False)

    # Core fields
    tipo = Column(
        String(100), nullable=False
    )  # "Orçamento da A.R." or "Conta Gerência"
    tp = Column(String(10), nullable=False)  # "OAR" or "CGE"
    titulo = Column(Text, nullable=False)  # Full title/description
    ano = Column(Integer, nullable=False)  # Year
    leg = Column(String(20), nullable=False)  # Legislature code (V, XI, etc.)
    sl = Column(Integer, nullable=False)  # Session number

    # Optional date fields
    dt_aprovacao_ca = Column(Date)  # dtAprovacaoCA - approval date
    dt_agendamento = Column(Date)  # dtAgendamento - scheduling date

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    legislatura = relationship("Legislatura")

    # Indexes for performance
    __table_args__ = (
        Index("idx_orcamento_gerencia_entry_id", "entry_id"),
        Index("idx_orcamento_gerencia_legislatura", "legislatura_id"),
        Index("idx_orcamento_gerencia_tipo", "tipo"),
        Index("idx_orcamento_gerencia_ano", "ano"),
        UniqueConstraint(
            "entry_id", "legislatura_id", name="uq_orcamento_gerencia_entry_leg"
        ),
    )


# =====================================================
# IX LEGISLATURE COMPREHENSIVE MODELS
# =====================================================


class ActividadesParlamentares(Base):
    """Parliamentary Activities - ActP section"""

    __tablename__ = "atividades_parlamentares"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    actividade_out_id = Column(
        GUID(), ForeignKey("actividade_outs.id"), nullable=False
    )
    created_at = Column(DateTime, default=func.now())

    # Relationships
    actividade_out = relationship("ActividadeOut")
    atividades = relationship(
        "ActividadesParlamentaresOut",
        back_populates="atividades_parlamentares",
        cascade="all, delete-orphan",
    )


class ActividadesParlamentaresOut(Base):
    """Individual Parliamentary Activities"""

    __tablename__ = "atividades_parlamentares_out"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    atividades_parlamentares_id = Column(
        GUID(), ForeignKey("atividades_parlamentares.id"), nullable=False
    )

    # Core fields from XML
    act_id = Column(Integer)  # ActId
    act_nr = Column(String(50))  # ActNr
    act_tp = Column(String(10))  # ActTp
    act_tpdesc = Column(String(200))  # ActTpdesc
    act_sel_lg = Column(String(20))  # ActSelLg
    act_sel_nr = Column(String(20))  # ActSelNr
    act_dtent = Column(String(50))  # ActDtent - entry date as string
    act_dtdeb = Column(DateTime)  # ActDtdeb - debate date
    act_as = Column(Text)  # ActAs - subject/title

    created_at = Column(DateTime, default=func.now())

    # Relationships
    atividades_parlamentares = relationship(
        "ActividadesParlamentares", back_populates="atividades"
    )


class GruposParlamentaresAmizade(Base):
    """
    Parliamentary Friendship Groups - Gpa section (Deputy Activities Context)
    ========================================================================

    This model represents friendship group associations as they appear within
    deputy activity files (AtividadeDeputado*.xml). It captures basic friendship
    group membership information linked to specific deputy activities.

    For comprehensive friendship group data including meetings, detailed member
    information, and visit records, see GrupoAmizadeStandalone model which
    processes the dedicated GrupoDeAmizadeXX.xml files.

    XML Context: ArrayOfAtividadeDeputado.AtividadeDeputado.ActividadeOut.Gpa
    """

    __tablename__ = "grupos_parlamentares_amizade"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    actividade_out_id = Column(
        GUID(), ForeignKey("actividade_outs.id"), nullable=False
    )
    created_at = Column(DateTime, default=func.now())

    # Relationships
    actividade_out = relationship("ActividadeOut")
    grupos = relationship(
        "GruposParlamentaresAmizadeOut",
        back_populates="grupos_parlamentares_amizade",
        cascade="all, delete-orphan",
    )


class GruposParlamentaresAmizadeOut(Base):
    """Individual Friendship Groups"""

    __tablename__ = "grupos_parlamentares_amizade_out"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    grupos_parlamentares_amizade_id = Column(
        GUID(), ForeignKey("grupos_parlamentares_amizade.id"), nullable=False
    )

    # Core fields from XML
    gpl_id = Column(Integer)  # GplId - group ID
    gpl_no = Column(String(500))  # GplNo - group name
    gpl_sel_lg = Column(String(20))  # GplSelLg - group session legislature
    cga_crg = Column(String(200))  # CgaCrg - group charge/responsibility
    cga_dtini = Column(String(50))  # CgaDtini - group start date
    cga_dtfim = Column(String(50))  # CgaDtfim - group end date

    created_at = Column(DateTime, default=func.now())

    # Relationships
    grupos_parlamentares_amizade = relationship(
        "GruposParlamentaresAmizade", back_populates="grupos"
    )


class DelegacoesPermanentes(Base):
    """Permanent Delegations - DlP section"""

    __tablename__ = "delegacoes_permanentes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    actividade_out_id = Column(
        GUID(), ForeignKey("actividade_outs.id"), nullable=False
    )
    created_at = Column(DateTime, default=func.now())

    # Relationships
    actividade_out = relationship("ActividadeOut")
    delegacoes = relationship(
        "DelegacoesPermanentesOut",
        back_populates="delegacoes_permanentes",
        cascade="all, delete-orphan",
    )


class DelegacoesPermanentesOut(Base):
    """Individual Permanent Delegations"""

    __tablename__ = "delegacoes_permanentes_out"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    delegacoes_permanentes_id = Column(
        GUID(), ForeignKey("delegacoes_permanentes.id"), nullable=False
    )

    # Core fields from XML
    dep_id = Column(Integer)  # DepId
    dep_no = Column(String(500))  # DepNo - delegation name
    dep_sel_lg = Column(String(20))  # DepSelLg - delegation session legislature
    dep_sel_nr = Column(String(20))  # DepSelNr - delegation session number
    cde_crg = Column(String(200))  # CdeCrg - charge/responsibility

    created_at = Column(DateTime, default=func.now())

    # Relationships
    delegacoes_permanentes = relationship(
        "DelegacoesPermanentes", back_populates="delegacoes"
    )
    reunioes = relationship(
        "ReunioesDelegacoesPermanentes",
        back_populates="delegacoes_permanentes_out",
        cascade="all, delete-orphan",
    )


class DelegacoesEventuais(Base):
    """Occasional Delegations - DlE section"""

    __tablename__ = "delegacoes_eventuais"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    actividade_out_id = Column(
        GUID(), ForeignKey("actividade_outs.id"), nullable=False
    )
    created_at = Column(DateTime, default=func.now())

    # Relationships
    actividade_out = relationship("ActividadeOut")
    delegacoes = relationship(
        "DelegacoesEventuaisOut",
        back_populates="delegacoes_eventuais",
        cascade="all, delete-orphan",
    )


class DelegacoesEventuaisOut(Base):
    """Individual Occasional Delegations"""

    __tablename__ = "delegacoes_eventuais_out"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    delegacoes_eventuais_id = Column(
        GUID(), ForeignKey("delegacoes_eventuais.id"), nullable=False
    )

    # Core fields from XML
    dev_id = Column(Integer)  # DevId - delegation ID
    dev_no = Column(String(500))  # DevNo - delegation name
    dev_tp = Column(String(100))  # DevTp - delegation type (I Legislature)
    dev_dtini = Column(String(50))  # DevDtIni - start date
    dev_dtfim = Column(String(50))  # DevDtfim - end date
    dev_sel_nr = Column(String(20))  # DevSelNr - session number
    dev_sel_lg = Column(String(20))  # DevSelLg - session legislature
    dev_loc = Column(String(500))  # DevLoc - location

    created_at = Column(DateTime, default=func.now())

    # Relationships
    delegacoes_eventuais = relationship(
        "DelegacoesEventuais", back_populates="delegacoes"
    )


class RequerimentosAtivDep(Base):
    """Deputy Activity Requirements - Req section"""

    __tablename__ = "requerimentos_ativ_dep"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    actividade_out_id = Column(
        GUID(), ForeignKey("actividade_outs.id"), nullable=False
    )
    created_at = Column(DateTime, default=func.now())

    # Relationships
    actividade_out = relationship("ActividadeOut")
    requerimentos = relationship(
        "RequerimentosAtivDepOut",
        back_populates="requerimentos_ativ_dep",
        cascade="all, delete-orphan",
    )


class RequerimentosAtivDepOut(Base):
    """Individual Requirements"""

    __tablename__ = "requerimentos_ativ_dep_out"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    requerimentos_ativ_dep_id = Column(
        GUID(), ForeignKey("requerimentos_ativ_dep.id"), nullable=False
    )

    # Core fields from XML
    req_id = Column(Integer)  # ReqId
    req_nr = Column(String(50))  # ReqNr
    req_tp = Column(String(10))  # ReqTp
    req_lg = Column(String(20))  # ReqLg
    req_sl = Column(String(20))  # ReqSl
    req_as = Column(Text)  # ReqAs - subject
    req_dt = Column(DateTime)  # ReqDt - date
    req_per_tp = Column(String(20))  # ReqPerTp

    created_at = Column(DateTime, default=func.now())

    # Relationships
    requerimentos_ativ_dep = relationship(
        "RequerimentosAtivDep", back_populates="requerimentos"
    )


class SubComissoesGruposTrabalho(Base):
    """Sub-committees and Working Groups - Scgt section"""

    __tablename__ = "subcomissoes_grupos_trabalho"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    actividade_out_id = Column(
        GUID(), ForeignKey("actividade_outs.id"), nullable=False
    )
    created_at = Column(DateTime, default=func.now())

    # Relationships
    actividade_out = relationship("ActividadeOut")
    subcomissoes = relationship(
        "SubComissoesGruposTrabalhoOut",
        back_populates="subcomissoes_grupos_trabalho",
        cascade="all, delete-orphan",
    )


class SubComissoesGruposTrabalhoOut(Base):
    """Individual Sub-committees/Working Groups"""

    __tablename__ = "subcomissoes_grupos_trabalho_out"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    subcomissoes_grupos_trabalho_id = Column(
        GUID(), ForeignKey("subcomissoes_grupos_trabalho.id"), nullable=False
    )

    # Core fields from XML
    scm_cd = Column(String(20))  # ScmCd - sub-committee code
    scm_com_cd = Column(String(20))  # ScmComCd - committee code
    ccm_dscom = Column(Text)  # CcmDscom - committee description
    cms_situacao = Column(
        String(200)
    )  # CmsSituacao - committee situation (I Legislature)
    cms_cargo = Column(String(200))  # CmsCargo - committee position
    scm_com_lg = Column(String(20))  # ScmComLg - committee legislature

    created_at = Column(DateTime, default=func.now())

    # Relationships
    subcomissoes_grupos_trabalho = relationship(
        "SubComissoesGruposTrabalho", back_populates="subcomissoes"
    )


class RelatoresPeticoes(Base):
    """Petition Rapporteurs - Rel.RelatoresPeticoes section"""

    __tablename__ = "relatores_peticoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    actividade_out_id = Column(
        GUID(), ForeignKey("actividade_outs.id"), nullable=False
    )
    created_at = Column(DateTime, default=func.now())

    # Relationships
    actividade_out = relationship("ActividadeOut")
    relatores = relationship(
        "RelatoresPeticoesOut",
        back_populates="relatores_peticoes",
        cascade="all, delete-orphan",
    )


class RelatoresPeticoesOut(Base):
    """Individual Petition Rapporteurs"""

    __tablename__ = "relatores_peticoes_out"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    relatores_peticoes_id = Column(
        GUID(), ForeignKey("relatores_peticoes.id"), nullable=False
    )

    # Core fields from XML
    pec_dtrelf = Column(String(50))  # PecDtrelf - petition report date
    pet_id = Column(Integer)  # PetId - petition ID
    pet_nr = Column(String(50))  # PetNr - petition number
    pet_aspet = Column(Text)  # PetAspet - petition subject
    pet_sel_lg_pk = Column(String(20))  # PetSelLgPk - petition legislature primary key
    pet_sel_nr_pk = Column(
        String(20)
    )  # PetSelNrPk - petition session number primary key

    created_at = Column(DateTime, default=func.now())

    # Relationships
    relatores_peticoes = relationship("RelatoresPeticoes", back_populates="relatores")


class Comissoes(Base):
    """Committees - Cms section"""

    __tablename__ = "comissoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    actividade_out_id = Column(
        GUID(), ForeignKey("actividade_outs.id"), nullable=False
    )
    created_at = Column(DateTime, default=func.now())

    # Relationships
    actividade_out = relationship("ActividadeOut")
    comissoes_out = relationship(
        "ComissoesOut", back_populates="comissoes", cascade="all, delete-orphan"
    )


class ComissoesOut(Base):
    """Individual Committee entries"""

    __tablename__ = "comissoes_out"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    comissoes_id = Column(GUID(), ForeignKey("comissoes.id"), nullable=False)

    # Core fields from XML
    cms_no = Column(String(500))  # CmsNo - committee name
    cms_cd = Column(String(20))  # CmsCd - committee code
    cms_lg = Column(String(20))  # CmsLg - committee legislature
    cms_cargo = Column(String(200))  # CmsCargo - committee position
    cms_sub_cargo = Column(
        Text
    )  # CmsSubCargo - committee sub-position (can be very long list)
    cms_situacao = Column(String(200))  # CmsSituacao - committee situation

    created_at = Column(DateTime, default=func.now())

    # Relationships
    comissoes = relationship("Comissoes", back_populates="comissoes_out")


class RelatoresIniciativas(Base):
    """Initiative Rapporteurs - Rel.RelatoresIniciativas section"""

    __tablename__ = "relatores_iniciativas"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    actividade_out_id = Column(
        GUID(), ForeignKey("actividade_outs.id"), nullable=False
    )
    created_at = Column(DateTime, default=func.now())

    # Relationships
    actividade_out = relationship("ActividadeOut")
    relatores = relationship(
        "RelatoresIniciativasOut",
        back_populates="relatores_iniciativas",
        cascade="all, delete-orphan",
    )


class RelatoresIniciativasOut(Base):
    """Individual Initiative Rapporteurs"""

    __tablename__ = "relatores_iniciativas_out"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    relatores_iniciativas_id = Column(
        GUID(), ForeignKey("relatores_iniciativas.id"), nullable=False
    )

    # Core fields from XML
    ini_id = Column(Integer)  # IniId - initiative ID
    ini_nr = Column(String(50))  # IniNr - initiative number
    ini_tp = Column(String(100))  # IniTp - initiative type
    ini_sel_lg = Column(String(20))  # IniSelLg - initiative session legislature
    acc_dtrel = Column(String(50))  # AccDtrel - rapporteur assignment date
    rel_fase = Column(String(200))  # RelFase - rapporteur phase
    ini_ti = Column(Text)  # IniTi - initiative title

    created_at = Column(DateTime, default=func.now())

    # Relationships
    relatores_iniciativas = relationship(
        "RelatoresIniciativas", back_populates="relatores"
    )


class ReunioesDelegacoesPermanentes(Base):
    """Permanent Delegation Meetings - DlP.DelegacoesPermanentesOut.DepReunioes section"""

    __tablename__ = "reunioes_delegacoes_permanentes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    delegacoes_permanentes_out_id = Column(
        GUID(), ForeignKey("delegacoes_permanentes_out.id"), nullable=False
    )

    # Core fields from XML
    ren_dt_ini = Column(String(50))  # RenDtIni - meeting start date
    ren_loc = Column(String(500))  # RenLoc - meeting location
    ren_dt_fim = Column(String(50))  # RenDtFim - meeting end date
    ren_ti = Column(Text)  # RenTi - meeting title

    created_at = Column(DateTime, default=func.now())

    # Relationships
    delegacoes_permanentes_out = relationship(
        "DelegacoesPermanentesOut", back_populates="reunioes"
    )


# =====================================================
# I LEGISLATURE SPECIFIC MODELS
# =====================================================


class AutoresPareceresIncImu(Base):
    """Authors of Incompatibility/Immunity Opinions - I Legislature Rel.AutoresPareceresIncImu section"""

    __tablename__ = "autores_pareceres_inc_imu"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    actividade_out_id = Column(
        GUID(), ForeignKey("actividade_outs.id"), nullable=False
    )
    created_at = Column(DateTime, default=func.now())

    # Relationships
    actividade_out = relationship("ActividadeOut")
    autores = relationship(
        "AutoresPareceresIncImuOut",
        back_populates="autores_pareceres_inc_imu",
        cascade="all, delete-orphan",
    )


class AutoresPareceresIncImuOut(Base):
    """Individual Authors of Incompatibility/Immunity Opinions"""

    __tablename__ = "autores_pareceres_inc_imu_out"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    autores_pareceres_inc_imu_id = Column(
        GUID(), ForeignKey("autores_pareceres_inc_imu.id"), nullable=False
    )

    # Core fields from XML
    act_id = Column(Integer)  # ActId - activity ID
    act_as = Column(Text)  # ActAs - activity subject
    act_sel_lg = Column(String(20))  # ActSelLg - activity session legislature
    act_tp_desc = Column(String(200))  # ActTpDesc - activity type description

    created_at = Column(DateTime, default=func.now())

    # Relationships
    autores_pareceres_inc_imu = relationship(
        "AutoresPareceresIncImu", back_populates="autores"
    )


class RelatoresIniEuropeias(Base):
    """European Initiative Rapporteurs - I Legislature Rel.RelatoresIniEuropeias section"""

    __tablename__ = "relatores_ini_europeias"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    actividade_out_id = Column(
        GUID(), ForeignKey("actividade_outs.id"), nullable=False
    )
    created_at = Column(DateTime, default=func.now())

    # Relationships
    actividade_out = relationship("ActividadeOut")
    relatores = relationship(
        "RelatoresIniEuropeiasOut",
        back_populates="relatores_ini_europeias",
        cascade="all, delete-orphan",
    )


class RelatoresIniEuropeiasOut(Base):
    """Individual European Initiative Rapporteurs"""

    __tablename__ = "relatores_ini_europeias_out"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    relatores_ini_europeias_id = Column(
        GUID(), ForeignKey("relatores_ini_europeias.id"), nullable=False
    )

    # Core fields from XML
    ine_id = Column(Integer)  # IneId - European initiative ID
    ine_data_relatorio = Column(String(50))  # IneDataRelatorio - report date
    ine_referencia = Column(String(200))  # IneReferencia - reference
    ine_titulo = Column(Text)  # IneTitulo - title
    leg = Column(String(20))  # Leg - legislature

    created_at = Column(DateTime, default=func.now())

    # Relationships
    relatores_ini_europeias = relationship(
        "RelatoresIniEuropeias", back_populates="relatores"
    )


class ParlamentoJovens(Base):
    """Youth Parliament - I Legislature ParlamentoJovens section"""

    __tablename__ = "parlamento_jovens"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    actividade_out_id = Column(
        GUID(), ForeignKey("actividade_outs.id"), nullable=False
    )
    created_at = Column(DateTime, default=func.now())

    # Relationships
    actividade_out = relationship("ActividadeOut")
    dados_deputado = relationship(
        "DadosDeputadoParlamentoJovens",
        back_populates="parlamento_jovens",
        cascade="all, delete-orphan",
    )


class DadosDeputadoParlamentoJovens(Base):
    """Youth Parliament Deputy Data"""

    __tablename__ = "dados_deputado_parlamento_jovens"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    parlamento_jovens_id = Column(
        GUID(), ForeignKey("parlamento_jovens.id"), nullable=False
    )

    # Core fields from XML
    tipo_reuniao = Column(String(200))  # TipoReuniao - meeting type
    circulo_eleitoral = Column(String(200))  # CirculoEleitoral - electoral district
    legislatura = Column(String(20))  # Legislatura - legislature
    data = Column(String(50))  # Data - date
    sessao = Column(String(100))  # Sessao - session
    estabelecimento = Column(String(500))  # Estabelecimento - establishment

    created_at = Column(DateTime, default=func.now())

    # Relationships
    parlamento_jovens = relationship(
        "ParlamentoJovens", back_populates="dados_deputado"
    )


class Eventos(Base):
    """Events - I Legislature Eventos section"""

    __tablename__ = "eventos"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    actividade_out_id = Column(
        GUID(), ForeignKey("actividade_outs.id"), nullable=False
    )
    created_at = Column(DateTime, default=func.now())

    # Relationships
    actividade_out = relationship("ActividadeOut")
    actividades_comissao = relationship(
        "ActividadesComissaoOut", back_populates="evento", cascade="all, delete-orphan"
    )


class Deslocacoes(Base):
    """Displacements - I Legislature Deslocacoes section"""

    __tablename__ = "deslocacoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    actividade_out_id = Column(
        GUID(), ForeignKey("actividade_outs.id"), nullable=False
    )
    created_at = Column(DateTime, default=func.now())

    # Relationships
    actividade_out = relationship("ActividadeOut")
    actividades_comissao = relationship(
        "ActividadesComissaoOut",
        back_populates="deslocacao",
        cascade="all, delete-orphan",
    )


class RelatoresContasPublicas(Base):
    """Public Accounts Rapporteurs - I Legislature Rel.RelatoresContasPublicas section"""

    __tablename__ = "relatores_contas_publicas"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    actividade_out_id = Column(
        GUID(), ForeignKey("actividade_outs.id"), nullable=False
    )
    created_at = Column(DateTime, default=func.now())

    # Relationships
    actividade_out = relationship("ActividadeOut")
    relatores = relationship(
        "RelatoresContasPublicasOut",
        back_populates="relatores_contas_publicas",
        cascade="all, delete-orphan",
    )


class RelatoresContasPublicasOut(Base):
    """Individual Public Accounts Rapporteurs"""

    __tablename__ = "relatores_contas_publicas_out"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    relatores_contas_publicas_id = Column(
        GUID(), ForeignKey("relatores_contas_publicas.id"), nullable=False
    )

    # Core fields from XML - based on similar structure to other rapporteur models
    act_id = Column(Integer)  # ActId - activity ID
    act_as = Column(Text)  # ActAs - activity subject
    act_tp = Column(String(100))  # ActTp - activity type
    cta_id = Column(Integer)  # CtaId - account ID
    cta_no = Column(String(500))  # CtaNo - account name

    created_at = Column(DateTime, default=func.now())

    # Relationships
    relatores_contas_publicas = relationship(
        "RelatoresContasPublicas", back_populates="relatores"
    )  # I Legislature Biographical Models - to be appended to models.py


# =====================================================
# I LEGISLATURE BIOGRAPHICAL DATA MODELS - COMPREHENSIVE
# =====================================================


class DeputadoHabilitacao(Base):
    """
    Deputy Academic Qualifications - Based on RegistoBiografico DadosHabilitacoes

    Stores comprehensive academic and professional qualifications for deputies
    from the biographical registry (cadHabilitacoes structure).

    RegistoBiografico Mapping (pt_ar_wsgode_objectos_DadosHabilitacoes):
    - habId: hab_id (Qualification unique identifier)
    - habDes: hab_des (Complete qualification description)
    - habTipoId: hab_tipo_id (Qualification type classification ID)
    - habEstado: hab_estado (Current status: completed/in progress/suspended)

    Qualification Types (habTipoId examples):
    - Academic degrees (Bachelor, Master, PhD)
    - Professional certifications
    - Technical qualifications
    - Honorary degrees

    Status Values (habEstado):
    - "Concluída" (Completed)
    - "Em curso" (In progress)
    - "Interrompida" (Interrupted/Suspended)

    Usage:
        Links to Deputado via deputado_id foreign key
        Multiple qualifications per deputy supported
        Order preserved through database insertion sequence
    """

    __tablename__ = "deputado_habilitacoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    deputado_id = Column(GUID(), ForeignKey("deputados.id"), nullable=False)
    hab_id = Column(Integer, comment="Qualification unique identifier (XML: habId)")
    hab_des = Column(
        String(500), comment="Complete qualification description (XML: habDes)"
    )
    hab_tipo_id = Column(
        Integer, comment="Qualification type classification ID (XML: habTipoId)"
    )
    hab_estado = Column(
        String(50),
        comment="Current status: completed/in progress/suspended (XML: habEstado)",
    )
    created_at = Column(DateTime, default=func.now())

    # Relationships
    deputado = relationship("Deputado", back_populates="habilitacoes")


class DeputadoCargoFuncao(Base):
    """
    Deputy Career Positions/Functions - Based on RegistoBiografico DadosCargosFuncoes

    Stores comprehensive professional positions and career functions held by deputies
    throughout their careers, both before and during parliamentary service.

    RegistoBiografico Mapping (pt_ar_wsgode_objectos_DadosCargosFuncoes):
    - funId: fun_id (Function unique identifier)
    - funDes: fun_des (Complete function/position description)
    - funOrdem: fun_ordem (Display order for biographical presentation)
    - funAntiga: fun_antiga (S/N flag indicating if position is historical)

    Position Categories (examples from funDes):
    - Academic positions (Professor, Researcher, Dean)
    - Government positions (Minister, Secretary of State, Mayor)
    - Private sector positions (CEO, Director, Manager)
    - Professional associations (President, Vice-President, Board Member)
    - Judicial positions (Judge, Prosecutor, Lawyer)

    Historical Flag (funAntiga):
    - "S": Historical/previous position (no longer held)
    - "N": Current position (actively held)
    - Note: Used to distinguish current from past professional roles

    Usage:
        Links to Deputado via deputado_id foreign key
        Multiple positions per deputy supported
        Chronological ordering via fun_ordem field
        Historical tracking via funAntiga flag
    """

    __tablename__ = "deputado_cargos_funcoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    deputado_id = Column(GUID(), ForeignKey("deputados.id"), nullable=False)
    fun_id = Column(Integer, comment="Function unique identifier (XML: funId)")
    fun_des = Column(
        Text, comment="Complete function/position description (XML: funDes)"
    )
    fun_ordem = Column(
        Integer, comment="Display order for biographical presentation (XML: funOrdem)"
    )
    fun_antiga = Column(
        String(1),
        comment="S/N flag indicating if position is historical (XML: funAntiga)",
    )
    created_at = Column(DateTime, default=func.now())

    # Relationships
    deputado = relationship("Deputado", back_populates="cargos_funcoes")


class DeputadoTitulo(Base):
    """
    Deputy Academic and Honorary Titles - Based on RegistoBiografico DadosTitulos

    Stores academic titles, honorary degrees, and professional distinctions
    awarded to deputies throughout their careers.

    RegistoBiografico Mapping (pt_ar_wsgode_objectos_DadosTitulos):
    - titId: tit_id (Title unique identifier)
    - titDes: tit_des (Complete title description)
    - titOrdem: tit_ordem (Display order for biographical presentation)

    Title Categories (examples from titDes):
    - Academic titles (Professor Catedrático, Professor Associado, Doutor Honoris Causa)
    - Professional titles (Engenheiro, Médico, Advogado, Arquitecto)
    - Honorary titles (Comendador, Oficial, Cavaleiro)
    - Recognition awards (Prémio Nacional, Distinção Científica)
    - International honors (Foreign decorations, Academic distinctions)

    Usage:
        Links to Deputado via deputado_id foreign key
        Multiple titles per deputy supported
        Ordered presentation via tit_ordem field
        Complements DeputadoCondecoracao for comprehensive honors tracking
    """

    __tablename__ = "deputado_titulos"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    deputado_id = Column(GUID(), ForeignKey("deputados.id"), nullable=False)
    tit_id = Column(Integer, comment="Title unique identifier (XML: titId)")
    tit_des = Column(Text, comment="Complete title description (XML: titDes)")
    tit_ordem = Column(
        Integer, comment="Display order for biographical presentation (XML: titOrdem)"
    )
    created_at = Column(DateTime, default=func.now())

    # Relationships
    deputado = relationship("Deputado", back_populates="titulos")


class DeputadoCondecoracao(Base):
    """
    Deputy Decorations and Honors - Based on RegistoBiografico DadosCondecoracoes

    Stores state decorations, honors, and official recognitions awarded to deputies
    by Portuguese and foreign governmental entities.

    RegistoBiografico Mapping (pt_ar_wsgode_objectos_DadosCondecoracoes):
    - codId: cod_id (Decoration unique identifier)
    - codDes: cod_des (Complete decoration description)
    - codOrdem: cod_ordem (Display order for biographical presentation)

    Decoration Categories (examples from codDes):
    - Portuguese Orders (Ordem do Infante D. Henrique, Ordem de Cristo, Ordem da Torre e Espada)
    - Portuguese Medals (Medalha de Ouro dos Bons Serviços, Medalha de Mérito)
    - Military decorations (Cruz de Guerra, Medalha Militar de Serviços Distintos)
    - Foreign orders and decorations (awarded by other countries)
    - Civic recognition (municipal honors, professional association awards)

    Hierarchical Levels:
    - Grã-Cruz (Grand Cross) - highest level
    - Grande-Oficial (Grand Officer)
    - Comendador (Commander)
    - Oficial (Officer)
    - Cavaleiro (Knight) - entry level

    Usage:
        Links to Deputado via deputado_id foreign key
        Multiple decorations per deputy supported
        Ordered presentation via cod_ordem field
        Distinct from DeputadoTitulo (focuses on state/official honors)
    """

    __tablename__ = "deputado_condecoracoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    deputado_id = Column(GUID(), ForeignKey("deputados.id"), nullable=False)
    cod_id = Column(Integer, comment="Decoration unique identifier (XML: codId)")
    cod_des = Column(Text, comment="Complete decoration description (XML: codDes)")
    cod_ordem = Column(
        Integer, comment="Display order for biographical presentation (XML: codOrdem)"
    )
    created_at = Column(DateTime, default=func.now())

    # Relationships
    deputado = relationship("Deputado", back_populates="condecoracoes")


class DeputadoObraPublicada(Base):
    """
    Deputy Published Works - Based on RegistoBiografico DadosObrasPublicadas

    Stores comprehensive bibliography of works authored, co-authored, or edited by deputies
    including books, academic papers, articles, and other publications.

    RegistoBiografico Mapping (pt_ar_wsgode_objectos_DadosObrasPublicadas):
    - pubId: pub_id (Publication unique identifier)
    - pubDes: pub_des (Complete publication description with bibliographic details)
    - pubOrdem: pub_ordem (Display order for biographical presentation)

    Publication Categories (examples from pubDes):
    - Academic books (monographs, textbooks, edited volumes)
    - Scholarly articles (journal papers, conference proceedings)
    - Professional publications (reports, technical manuals, policy papers)
    - Literary works (novels, poetry, essays)
    - Popular publications (magazine articles, newspaper columns)
    - Translations and edited works

    Bibliographic Information Included:
    - Full titles and subtitles
    - Co-authors and editors
    - Publication dates and editions
    - Publishers and institutions
    - ISBN/ISSN when available
    - Page counts and formats

    Usage:
        Links to Deputado via deputado_id foreign key
        Multiple publications per deputy supported
        Chronological or thematic ordering via pub_ordem field
        Supports comprehensive academic and intellectual biography
    """

    __tablename__ = "deputado_obras_publicadas"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    deputado_id = Column(GUID(), ForeignKey("deputados.id"), nullable=False)
    pub_id = Column(Integer, comment="Publication unique identifier (XML: pubId)")
    pub_des = Column(
        Text,
        comment="Complete publication description with bibliographic details (XML: pubDes)",
    )
    pub_ordem = Column(
        Integer, comment="Display order for biographical presentation (XML: pubOrdem)"
    )
    created_at = Column(DateTime, default=func.now())

    # Relationships
    deputado = relationship("Deputado", back_populates="obras_publicadas")


class DeputadoAtividadeOrgao(Base):
    """
    Deputy Parliamentary Organ Activities - Based on RegistoBiografico cadActividadeOrgaos

    Stores detailed information about deputy participation in parliamentary committees
    and working groups, including positions held and mandate periods.

    This model handles two distinct activity types with parallel structure:
    1. Committee Activities (actividadeCom) - permanent and specialized committees
    2. Working Group Activities (actividadeGT) - temporary thematic working groups

    RegistoBiografico Mapping Structure:
    - cadActividadeOrgaos (Root container)
      ├── actividadeCom (Committee activities)
      └── actividadeGT (Working group activities)

    Both activity types use pt_ar_wsgode_objectos_DadosOrgaos structure:
    - orgId: org_id (Organ unique identifier)
    - orgSigla: org_sigla (Official organ acronym)
    - orgDes: org_des (Full organ name/description)
    - legDes: leg_des (Legislature designation: IA, IB, II, III, etc.)
    - timDes: tim_des (Mandate period description)
    - cargoDes: cargo_des (Contains nested DadosCargosOrgao with position details)

    Position Details (pt_ar_wsgode_objectos_DadosCargosOrgao):
    - tiaDes: tia_des (Position type: Presidente, Vice-Presidente, Relator, Vogal, etc.)

    Activity Types:
    - "actividadeCom": Committee membership and leadership
    - "actividadeGT": Working group participation and roles

    Common Position Types (tiaDes):
    - "Presidente" (President/Chair)
    - "Vice-Presidente" (Vice-President/Vice-Chair)
    - "Relator" (Rapporteur)
    - "Vogal" (Member)
    - "Secretário" (Secretary)

    Usage:
        Links to Deputado via deputado_id foreign key
        Multiple organ activities per deputy supported
        Tracks complete parliamentary service history across all legislatures
        Essential for understanding deputy's areas of specialization and leadership roles
    """

    __tablename__ = "deputado_atividades_orgaos"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    deputado_id = Column(GUID(), ForeignKey("deputados.id"), nullable=False)

    # Activity type - 'actividadeCom' or 'actividadeGT'
    tipo_atividade = Column(
        String(50),
        nullable=False,
        comment="Activity type: actividadeCom (committee) or actividadeGT (working group)",
    )

    # Organ details (pt_ar_wsgode_objectos_DadosOrgaos)
    org_id = Column(Integer, comment="Organ unique identifier (XML: orgId)")
    org_sigla = Column(String(50), comment="Official organ acronym (XML: orgSigla)")
    org_des = Column(String(200), comment="Full organ name/description (XML: orgDes)")
    leg_des = Column(
        String(50),
        comment="Legislature designation: IA, IB, II, III, etc. (XML: legDes)",
    )
    tim_des = Column(String(50), comment="Mandate period description (XML: timDes)")

    # Position details (extracted from pt_ar_wsgode_objectos_DadosCargosOrgao within cargoDes)
    tia_des = Column(
        String(200),
        comment="Position type: Presidente, Vice-Presidente, Relator, Vogal, etc. (XML: tiaDes)",
    )

    created_at = Column(DateTime, default=func.now())

    # Relationships
    deputado = relationship("Deputado", back_populates="atividades_orgaos")


class DeputadoMandatoLegislativo(Base):
    """
    Deputy Legislative Mandates - Based on RegistoBiografico cadDeputadoLegis

    Stores comprehensive information about each legislative mandate served by a deputy,
    including electoral details, party affiliations, and parliamentary group memberships.

    Each record represents one legislative period where the deputy served, creating
    a complete electoral and political history for biographical research.

    RegistoBiografico Mapping (pt_ar_wsgode_objectos_DadosDeputadoLegis):
    - depNomeParlamentar: dep_nome_parlamentar (Parliamentary name used during mandate)
    - legDes: leg_des (Legislature designation: IA, IB, II, III, IV, V, etc.)
    - ceDes: ce_des (Electoral circle description: Aveiro, Braga, Lisboa, etc.)
    - parSigla: par_sigla (Political party acronym: PS, PSD, CDS, BE, etc.)
    - parDes: par_des (Full political party name)
    - gpSigla: gp_sigla (Parliamentary group acronym - may differ from party)
    - gpDes: gp_des (Parliamentary group full name)
    - indDes: ind_des (Indication/appointment description for special cases)
    - urlVideoBiografia: url_video_biografia (Biography video URL if available)
    - indData: ind_data (Indication/appointment date for special appointments)

    Legislature Designations (legDes):
    - "IA", "IB": First legislature divided phases
    - "II" through "XV": Standard numbered legislatures
    - "CONSTITUINTE": Constitutional Assembly (1975-1976)

    Electoral Circles (ceDes examples):
    - District-based: "Aveiro", "Braga", "Coimbra", "Lisboa", "Porto"
    - Island-based: "Açores", "Madeira"
    - Special: "Emigração" (Emigration), "Europa" (European)

    Political Context:
    - Party (par*) vs Parliamentary Group (gp*) distinction important
    - Deputies may switch groups during mandate (tracked via parliamentary group models)
    - Special appointments (indDes/indData) for interim or replacement deputies

    Usage:
        Links to Deputado via deputado_id foreign key
        One record per legislature served by deputy
        Essential for electoral history and political affiliation tracking
        Supports longitudinal analysis of deputy careers
    """

    __tablename__ = "deputado_mandatos_legislativos"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    deputado_id = Column(GUID(), ForeignKey("deputados.id"), nullable=False)

    # Core mandate data
    dep_nome_parlamentar = Column(
        String(200),
        comment="Parliamentary name used during mandate (XML: depNomeParlamentar)",
    )
    leg_des = Column(
        String(50),
        comment="Legislature designation: IA, IB, II, III, etc. (XML: legDes)",
    )
    ce_des = Column(
        String(100),
        comment="Electoral circle: Aveiro, Braga, Lisboa, Porto, etc. (XML: ceDes)",
    )
    par_sigla = Column(
        String(20),
        comment="Political party acronym: PS, PSD, CDS, BE, etc. (XML: parSigla)",
    )
    par_des = Column(String(200), comment="Full political party name (XML: parDes)")
    gp_sigla = Column(
        String(20),
        comment="Parliamentary group acronym - may differ from party (XML: gpSigla)",
    )
    gp_des = Column(String(200), comment="Parliamentary group full name (XML: gpDes)")
    ind_des = Column(
        String(200),
        comment="Indication/appointment description for special cases (XML: indDes)",
    )
    url_video_biografia = Column(
        String(500), comment="Biography video URL if available (XML: urlVideoBiografia)"
    )
    ind_data = Column(
        Date,
        comment="Indication/appointment date for special appointments (XML: indData)",
    )
    
    # Coalition context - enhanced political entity tracking
    tipo_entidade_politica = Column(
        String(20),
        comment="Type of political entity: 'partido' (individual party) or 'coligacao' (coalition)"
    )
    coligacao_id = Column(
        GUID(),
        ForeignKey("coligacoes.id"),
        comment="Coalition ID if this mandate was under a coalition"
    )
    eh_coligacao = Column(
        Boolean,
        default=False,
        comment="Whether the par_sigla represents a coalition (auto-detected)"
    )
    confianca_detecao_coligacao = Column(
        Float,
        comment="Confidence score for coalition detection (0.0-1.0)"
    )

    created_at = Column(DateTime, default=func.now())

    # Data provenance tracking
    import_status_id = Column(
        GUID(),
        ForeignKey("import_status.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Reference to import batch that created/updated this record"
    )

    # Relationships
    deputado = relationship("Deputado", back_populates="mandatos_legislativos")
    coligacao = relationship("Coligacao", foreign_keys=[coligacao_id])

    # Indexes for performance optimization
    __table_args__ = (
        Index("idx_mandatos_deputado_id", "deputado_id"),
        Index("idx_mandatos_leg_des", "leg_des"),
        Index("idx_mandatos_par_sigla", "par_sigla"),
        Index("idx_mandatos_legislatura_composite", "deputado_id", "leg_des"),
    )










class IniciativaOrigem(Base):
    """Initiative that originated from another initiative"""

    __tablename__ = "iniciativas_origem"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    iniciativa_id = Column(
        GUID(), ForeignKey("iniciativas_detalhadas.id"), nullable=False
    )

    # Fields from pt_gov_ar_objectos_iniciativas_DadosGeraisOut
    origem_id = Column(Integer)  # id
    leg = Column(String(20))
    numero = Column(String(50))
    sel = Column(String(10))
    tipo = Column(String(100))
    titulo = Column(Text)
    desc_tipo = Column(String(200))  # descTipo
    legislatura = Column(String(20))
    sessao = Column(String(50))
    assunto = Column(Text)

    created_at = Column(DateTime, default=func.now())

    # Relationships
    iniciativa = relationship("IniciativaParlamentar", back_populates="origens")


class IniciativaOriginada(Base):
    """Initiative that was originated from this initiative"""

    __tablename__ = "iniciativas_originadas"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    iniciativa_id = Column(
        GUID(), ForeignKey("iniciativas_detalhadas.id"), nullable=False
    )

    # Fields from pt_gov_ar_objectos_iniciativas_DadosGeraisOut
    originada_id = Column(Integer)  # id
    leg = Column(String(20))
    numero = Column(String(50))
    sel = Column(String(10))
    tipo = Column(String(100))
    titulo = Column(Text)
    desc_tipo = Column(String(200))  # descTipo
    legislatura = Column(String(20))
    sessao = Column(String(50))
    assunto = Column(Text)

    created_at = Column(DateTime, default=func.now())

    # Relationships
    iniciativa = relationship("IniciativaParlamentar", back_populates="originadas")


# =====================================================
# UNIFIED INTEREST REGISTRY MODELS (Phase 2)
# =====================================================


class RegistoInteressesUnified(Base):
    """
    Unified Interest Registry Model - Phase 2 Consolidation

    Consolidates all interest registry data from different schema versions
    (V1, V2, V3, V5) into a single, optimized structure.

    Replaces fragmented system of RegistoInteresses + RegistoInteressesV2
    with unified architecture supporting all schema versions.
    """

    __tablename__ = "registo_interesses_unified"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    deputado_id = Column(GUID(), ForeignKey("deputados.id"), nullable=False)
    legislatura_id = Column(GUID(), ForeignKey("legislaturas.id"), nullable=False)

    # Core identification fields
    cad_id = Column(Integer)  # V1/V2 cadastral ID
    schema_version = Column(String(10), nullable=False)  # "V1", "V2", "V3", "V5"

    # Personal information (unified across all versions)
    full_name = Column(String(200))
    marital_status_code = Column(String(10))
    marital_status_desc = Column(String(50))
    spouse_name = Column(String(200))
    matrimonial_regime = Column(String(100))
    professional_activity = Column(Text)

    # V3+ specific fields
    exclusivity = Column(String(10))  # "Yes"/"No"
    dgf_number = Column(String(50))

    # V5+ specific fields
    category = Column(String(100))
    declaration_fact = Column(Text)
    gender = Column(String(1))  # V5 Sexo field (M/F)

    # V3+ Position dates (from RecordInterestResponse)
    position_begin_date = Column(String(50))  # PositionBeginDate
    position_end_date = Column(String(50))  # PositionEndDate
    position_changed_date = Column(String(50))  # PositionChangedDate
    position_designation = Column(String(200))  # PositionDesignation

    # Metadata
    version_date = Column(String(50))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    deputado = relationship("Deputado")
    legislatura = relationship("Legislatura")
    atividades = relationship(
        "RegistoInteressesAtividadeUnified",
        back_populates="registo",
        cascade="all, delete-orphan",
    )
    sociedades = relationship(
        "RegistoInteressesSociedadeUnified",
        back_populates="registo",
        cascade="all, delete-orphan",
    )
    social_positions = relationship(
        "RegistoInteressesSocialPositionUnified",
        back_populates="registo",
        cascade="all, delete-orphan",
    )
    apoios = relationship(
        "RegistoInteressesApoioUnified",
        back_populates="registo",
        cascade="all, delete-orphan",
    )
    facto_declaracao = relationship(
        "RegistoInteressesFactoDeclaracao",
        back_populates="registo",
        cascade="all, delete-orphan",
        uselist=False  # One-to-one relationship
    )


class RegistoInteressesFactoDeclaracao(Base):
    """
    Declaration Facts Model for Interest Registry V5 Schema
    
    Stores FactoDeclaracao data from V5 registo de interesses XML files.
    Contains declaration metadata including function details and dates.
    
    XML Mapping (FactoDeclaracao from V5):
    - Id: declaracao_id (Usually "0" for standard declarations)
    - CargoFuncao: cargo_funcao (Deputy function title)
    - ChkDeclaracao: chk_declaracao (Declaration check flag)
    - TxtDeclaracao: txt_declaracao (Declaration text, optional)
    - DataInicioFuncao: data_inicio_funcao (Function start date)
    - DataAlteracaoFuncao: data_alteracao_funcao (Function change date, optional) 
    - DataCessacaoFuncao: data_cessacao_funcao (Function end date, optional)
    
    Used in XIV and XV legislatures (V5 schema).
    """
    
    __tablename__ = "registo_interesses_facto_declaracao"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    registo_id = Column(
        GUID(),
        ForeignKey("registo_interesses_unified.id", ondelete="CASCADE"),
        nullable=False,
        unique=True  # One-to-one relationship
    )
    
    # FactoDeclaracao fields from V5 XML
    declaracao_id = Column(String(50), comment="Declaration ID from XML (XML: Id)")
    cargo_funcao = Column(String(200), comment="Function/position title (XML: CargoFuncao)") 
    chk_declaracao = Column(String(10), comment="Declaration check flag (XML: ChkDeclaracao)")
    txt_declaracao = Column(Text, comment="Declaration text content (XML: TxtDeclaracao)")
    data_inicio_funcao = Column(Date, comment="Function start date (XML: DataInicioFuncao)")
    data_alteracao_funcao = Column(Date, comment="Function change date (XML: DataAlteracaoFuncao)")
    data_cessacao_funcao = Column(Date, comment="Function end date (XML: DataCessacaoFuncao)")
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    registo = relationship(
        "RegistoInteressesUnified", 
        back_populates="facto_declaracao"
    )


class RegistoInteressesAtividadeUnified(Base):
    """
    Unified Activities Model for Interest Registry

    Handles all activity types across schema versions:
    - V1/V2: Basic professional activities
    - V2+: Detailed structured activities
    - V5+: Extended activity classifications
    """

    __tablename__ = "registo_interesses_activities_unified"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    registo_id = Column(
        GUID(),
        ForeignKey("registo_interesses_unified.id", ondelete="CASCADE"),
        nullable=False,
    )
    activity_type = Column(
        String(50)
    )  # 'professional', 'cargo_menos_3', 'cargo_mais_3'
    type_classification = Column(String(50))  # V3 Type field - supports both integers and strings like "menos_tres_anos"

    # Common fields across all versions
    description = Column(Text)
    entity = Column(String(500))
    nature_area = Column(String(500))
    start_date = Column(String(50))
    end_date = Column(String(50))
    remunerated = Column(String(10))  # Y/N
    value = Column(String(200))  # Can be descriptive text
    observations = Column(Text)

    # V5 specific fields
    service_description = Column(Text)
    cargo_funcao_atividade = Column(Text)

    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    registo = relationship("RegistoInteressesUnified", back_populates="atividades")


class RegistoInteressesSociedadeUnified(Base):
    """
    Unified Societies/Companies Model for Interest Registry

    Handles company shareholdings and business interests
    across all schema versions.
    """

    __tablename__ = "registo_interesses_societies_unified"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    registo_id = Column(
        GUID(),
        ForeignKey("registo_interesses_unified.id", ondelete="CASCADE"),
        nullable=False,
    )

    entity = Column(String(500))
    activity_area = Column(String(500))
    headquarters = Column(String(500))
    social_participation = Column(Text)  # Shareholding details
    value = Column(String(200))
    observations = Column(Text)

    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    registo = relationship("RegistoInteressesUnified", back_populates="sociedades")


class RegistoInteressesSocialPositionUnified(Base):
    """
    Unified Social Positions Model for Interest Registry

    Handles V3+ social positions (SocialPositions.RecordInterestSocialPositionResponse)
    which are distinct from activities and include board positions, memberships, etc.
    """

    __tablename__ = "registo_interesses_social_positions_unified"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    registo_id = Column(
        GUID(),
        ForeignKey("registo_interesses_unified.id", ondelete="CASCADE"),
        nullable=False,
    )

    position = Column(String(500))  # Position title/role
    entity = Column(String(500))  # Organization/company name
    activity_area = Column(String(500))  # Area of activity
    headquarters_location = Column(String(500))  # HeadOfficeLocation
    type_classification = Column(String(50))  # V3 Type field - supports both integers and strings like "menos_tres_anos"
    social_participation = Column(Text)  # Participation details
    value = Column(String(200))  # Monetary value if any
    observations = Column(Text)

    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    registo = relationship(
        "RegistoInteressesUnified", back_populates="social_positions"
    )


class RegistoInteressesApoioUnified(Base):
    """
    Unified Benefits/Support Model for Interest Registry

    Handles V3+ ServicesProvided and V5+ apoios/servicos_prestados declarations.
    - V3 ServicesProvided.RecordInterestServiceProvidedResponse.Service
    - V5 GenServicoPrestado and GenApoios structures
    """

    __tablename__ = "registo_interesses_benefits_unified"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    registo_id = Column(
        GUID(),
        ForeignKey("registo_interesses_unified.id", ondelete="CASCADE"),
        nullable=False,
    )

    benefit_type = Column(String(100))  # 'apoio', 'servico_prestado', 'service'
    entity = Column(String(500))
    nature_area = Column(String(500))
    description = Column(Text)
    service_location = Column(String(500))  # V5 GenServicoPrestado Local field
    value = Column(String(200))
    start_date = Column(String(50))
    end_date = Column(String(50))

    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    registo = relationship("RegistoInteressesUnified", back_populates="apoios")


# =====================================================
# PHASE 3: ANALYTICS MODELS - Database-Driven Parliamentary Analytics
# =====================================================


class DeputyAnalytics(Base):
    """Comprehensive deputy performance analytics with real-time scoring"""

    __tablename__ = "deputy_analytics"
    __table_args__ = (
        UniqueConstraint(
            "deputado_id", "legislatura_id", name="unique_deputy_legislature_analytics"
        ),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    deputado_id = Column(GUID(), ForeignKey("deputados.id"), nullable=False)
    legislatura_id = Column(GUID(), ForeignKey("legislaturas.id"))

    # Activity Scoring (0-100 scale) - calculated by stored procedures
    activity_score = Column(Integer, default=0)
    attendance_score = Column(Integer, default=0)
    initiative_score = Column(Integer, default=0)
    intervention_score = Column(Integer, default=0)
    engagement_score = Column(Integer, default=0)

    # Core Activity Metrics
    total_sessions_attended = Column(Integer, default=0)
    total_sessions_eligible = Column(Integer, default=0)
    attendance_percentage = Column(Integer, default=0)  # 0-100 percentage as integer
    total_initiatives = Column(Integer, default=0)
    total_interventions = Column(Integer, default=0)
    total_words_spoken = Column(Integer, default=0)

    # Success and Impact Metrics
    initiatives_approved = Column(Integer, default=0)
    initiatives_pending = Column(Integer, default=0)
    initiatives_rejected = Column(Integer, default=0)
    approval_rate = Column(Integer, default=0)  # 0-100 percentage as integer
    collaboration_count = Column(Integer, default=0)
    leadership_score = Column(Integer, default=0)

    # Temporal Activity Tracking
    days_active = Column(Integer, default=0)
    avg_monthly_activity = Column(
        Integer, default=0
    )  # Average activities per month as integer
    peak_activity_month = Column(String(7))
    activity_trend = Column(String(20))

    # Ranking and Comparison
    rank_overall = Column(Integer)
    rank_in_party = Column(Integer)
    rank_in_legislature = Column(Integer)
    percentile_overall = Column(Integer)

    # Data Quality and Freshness
    data_completeness_score = Column(Integer, default=0)
    last_activity_date = Column(Date)
    calculation_date = Column(DateTime, server_default=func.now())
    needs_recalculation = Column(Boolean, default=False)

    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    deputado = relationship("Deputado", backref="analytics")
    legislatura = relationship("Legislatura", backref="deputy_analytics")


class AttendanceAnalytics(Base):
    """Monthly attendance analytics for deputies"""

    __tablename__ = "attendance_analytics"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    deputado_id = Column(GUID(), ForeignKey("deputados.id"), nullable=False)
    legislatura_id = Column(GUID(), ForeignKey("legislaturas.id"))
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)

    # Basic Attendance Metrics
    sessions_scheduled = Column(Integer, default=0)
    sessions_attended = Column(Integer, default=0)
    sessions_absent = Column(Integer, default=0)
    sessions_justified_absence = Column(Integer, default=0)
    sessions_unjustified_absence = Column(Integer, default=0)
    attendance_rate = Column(String(10))  # Decimal(5,2) as string

    # Advanced Metrics
    consecutive_absences = Column(Integer, default=0)
    max_consecutive_absences = Column(Integer, default=0)
    attendance_consistency = Column(Integer, default=0)
    seasonal_pattern = Column(String(20))

    # Session Type Breakdown
    plenario_attended = Column(Integer, default=0)
    comissao_attended = Column(Integer, default=0)
    other_sessions_attended = Column(Integer, default=0)

    # Punctuality Metrics
    early_departures = Column(Integer, default=0)
    late_arrivals = Column(Integer, default=0)
    full_session_attendance = Column(Integer, default=0)
    punctuality_score = Column(Integer, default=0)

    # Ranking and Comparison
    rank_in_month = Column(Integer)
    above_average_attendance = Column(Boolean, default=False)
    improvement_from_prev_month = Column(String(10))  # Decimal(5,2) as string

    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class InitiativeAnalytics(Base):
    """Comprehensive initiative analytics for deputies"""

    __tablename__ = "initiative_analytics"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    deputado_id = Column(GUID(), ForeignKey("deputados.id"), nullable=False)
    legislatura_id = Column(GUID(), ForeignKey("legislaturas.id"))

    # Authorship Metrics
    total_initiatives_authored = Column(Integer, default=0)
    total_initiatives_co_authored = Column(Integer, default=0)
    solo_initiatives = Column(Integer, default=0)
    collaborative_initiatives = Column(Integer, default=0)
    cross_party_initiatives = Column(Integer, default=0)

    # Initiative Types
    projetos_lei = Column(Integer, default=0)
    propostas_lei = Column(Integer, default=0)
    requerimentos = Column(Integer, default=0)
    perguntas = Column(Integer, default=0)
    mocoes = Column(Integer, default=0)
    other_types = Column(Integer, default=0)

    # Success Metrics
    initiatives_approved = Column(Integer, default=0)
    initiatives_in_progress = Column(Integer, default=0)
    initiatives_rejected = Column(Integer, default=0)
    initiatives_withdrawn = Column(Integer, default=0)
    success_rate = Column(String(10))  # Decimal(5,2) as string
    impact_score = Column(Integer, default=0)

    # Productivity Metrics
    avg_initiatives_per_month = Column(String(10))  # Decimal(5,2) as string
    most_productive_month = Column(String(7))
    productivity_trend = Column(String(20))

    # Temporal Metrics
    first_initiative_date = Column(Date)
    latest_initiative_date = Column(Date)
    initiative_span_days = Column(Integer)

    # Topic and Expertise
    primary_topic_area = Column(String(100))
    topic_diversity_score = Column(Integer, default=0)
    expertise_areas = Column(Text)

    # Collaboration Metrics
    unique_collaborators = Column(Integer, default=0)
    collaboration_score = Column(Integer, default=0)
    leadership_ratio = Column(String(10))  # Decimal(5,2) as string

    # Quality Metrics
    avg_initiative_complexity = Column(Integer, default=0)
    amendment_rate = Column(String(10))  # Decimal(5,2) as string
    debate_generation_score = Column(Integer, default=0)

    # Rankings
    rank_by_quantity = Column(Integer)
    rank_by_success_rate = Column(Integer)
    rank_by_impact = Column(Integer)

    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class DeputyTimeline(Base):
    """
    Career timeline and experience analytics for deputies

    IMPORTANT: Uses id_cadastro to track the same PERSON across all legislatures,
    not deputado_id which is legislature-specific.
    """

    __tablename__ = "deputy_timeline"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    id_cadastro = Column(
        Integer, nullable=False, unique=True
    )  # Person's unique ID across all legislatures

    # Career Timeline
    first_election_date = Column(Date)
    total_legislatures_served = Column(Integer, default=0)
    consecutive_terms = Column(Integer, default=0)
    years_of_service = Column(Integer, default=0)
    current_term_start = Column(Date)
    is_currently_active = Column(Boolean, default=True)

    # Career Highlights
    key_positions_held = Column(Text)
    committee_memberships = Column(Text)
    leadership_roles = Column(Text)
    significant_initiatives = Column(Text)

    # Performance Evolution
    career_peak_year = Column(Integer)
    career_peak_score = Column(Integer)
    current_performance_trend = Column(String(20))
    experience_category = Column(String(20))

    # Focus Areas Over Time
    early_career_focus = Column(String(100))
    mid_career_focus = Column(String(100))
    current_focus = Column(String(100))
    focus_evolution_pattern = Column(String(50))

    # Influence and Network
    mentorship_score = Column(Integer, default=0)
    network_centrality = Column(Integer, default=0)
    cross_party_influence = Column(Integer, default=0)
    media_attention_score = Column(Integer, default=0)

    # Future Projections
    projected_career_trajectory = Column(String(50))
    specialization_strength = Column(Integer, default=0)
    institutional_memory_value = Column(Integer, default=0)

    # Calculation Metadata
    last_calculated = Column(DateTime)
    calculation_version = Column(String(10))

    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class DataQualityMetrics(Base):
    """Data quality metrics for database tables"""

    __tablename__ = "data_quality_metrics"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    table_name = Column(String(100), nullable=False)
    metric_date = Column(Date, nullable=False)

    # Volume Metrics
    total_records = Column(Integer, default=0)
    complete_records = Column(Integer, default=0)
    incomplete_records = Column(Integer, default=0)

    # Quality Scores
    completeness_percentage = Column(String(10))  # Decimal(5,2) as string
    consistency_score = Column(Integer, default=0)
    referential_integrity_score = Column(Integer, default=0)
    temporal_consistency_score = Column(Integer, default=0)

    # Issue Counts
    null_critical_fields = Column(Integer, default=0)
    invalid_date_ranges = Column(Integer, default=0)
    duplicate_records = Column(Integer, default=0)
    orphaned_records = Column(Integer, default=0)

    # Temporal Coverage
    oldest_record_date = Column(Date)
    newest_record_date = Column(Date)
    data_span_days = Column(Integer)
    last_update_lag_hours = Column(Integer)

    # Trends and Issues
    quality_trend = Column(String(20))
    issue_categories = Column(Text)
    improvement_suggestions = Column(Text)

    # Performance
    check_duration_seconds = Column(Integer)

    # Metadata
    created_at = Column(DateTime, server_default=func.now())


# Parliamentary Friendship Groups (Standalone Data) Models
# ========================================================


class GrupoAmizadeStandalone(Base):
    """
    Parliamentary Friendship Groups - Comprehensive Standalone Data
    ==============================================================

    This model represents complete friendship group information as it appears in
    the dedicated GrupoDeAmizadeXX.xml files. These files contain comprehensive
    data about friendship groups including detailed member information, meetings,
    visits, and participant records.

    XML Structure: ArrayOfGrupoDeAmizadeOut/GrupoDeAmizadeOut
    Source Files: GrupoDeAmizadeV.xml, GrupoDeAmizadeVI.xml, etc.

    Key Differences from GruposParlamentaresAmizade:
    - Not tied to deputy activities (standalone data)
    - Includes complete member composition with roles and dates
    - Contains meeting and visit records
    - Has detailed participant information
    - Covers all friendship groups comprehensively per legislature
    """

    __tablename__ = "grupos_amizade_standalone"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Core identification (from GrupoDeAmizadeOut)
    group_id = Column(Integer, nullable=False, index=True)  # XML: Id
    nome = Column(String(500), nullable=False)  # XML: Nome
    legislatura = Column(
        String(10), nullable=False, index=True
    )  # XML: Legislatura (e.g., "XV")
    sessao = Column(Integer)  # XML: Sessao
    data_criacao = Column(DateTime)  # XML: DataCriacao

    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    membros = relationship(
        "GrupoAmizadeMembro", back_populates="grupo", cascade="all, delete-orphan"
    )
    reunioes = relationship(
        "GrupoAmizadeReuniao", back_populates="grupo", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<GrupoAmizadeStandalone(id={self.group_id}, nome='{self.nome}', legislatura='{self.legislatura}')>"


class GrupoAmizadeMembro(Base):
    """
    Parliamentary Friendship Group Members
    =====================================

    Represents individual members of parliamentary friendship groups with their
    roles, parliamentary group affiliation, and service periods.

    XML Structure: GrupoDeAmizadeOut/Composicao/DelegacaoPermanenteMembroOut
    """

    __tablename__ = "grupos_amizade_membros"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    grupo_amizade_id = Column(
        GUID(), ForeignKey("grupos_amizade_standalone.id"), nullable=False
    )

    # Member information (from DelegacaoPermanenteMembroOut)
    nome = Column(String(500), nullable=False)  # XML: Nome
    grupo_parlamentar = Column(
        String(200)
    )  # XML: Gp (full name, e.g., "Partido Socialista")
    cargo = Column(String(100))  # XML: Cargo (Presidente, Vice-Presidente, Membro)
    data_inicio = Column(DateTime)  # XML: DataInicio
    data_fim = Column(DateTime)  # XML: DataFim

    # Metadata
    created_at = Column(DateTime, default=func.now())

    # Relationships
    grupo = relationship("GrupoAmizadeStandalone", back_populates="membros")

    def __repr__(self):
        return f"<GrupoAmizadeMembro(nome='{self.nome}', cargo='{self.cargo}', gp='{self.grupo_parlamentar}')>"


class GrupoAmizadeReuniao(Base):
    """
    Parliamentary Friendship Group Meetings and Visits
    =================================================

    Represents meetings, visits, and other events organized by parliamentary
    friendship groups, including participant information.

    XML Structure: 
    - GrupoDeAmizadeOut/Reunioes/GrupoDeAmizadeReuniao (meetings)
    - GrupoDeAmizadeOut/Visitas/GrupoDeAmizadeReuniao (visits)
    
    The event_source field distinguishes between the two types:
    - 'Reunioes': Formal meetings held by the friendship group
    - 'Visitas': Visits and informal events
    """

    __tablename__ = "grupos_amizade_reunioes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    grupo_amizade_id = Column(
        GUID(), ForeignKey("grupos_amizade_standalone.id"), nullable=False
    )

    # Meeting information (from GrupoDeAmizadeReuniao)
    meeting_id = Column(Integer, nullable=False, index=True)  # XML: Id
    nome = Column(Text, nullable=False)  # XML: Nome (can be long descriptions)
    tipo = Column(String(200))  # XML: Tipo (often empty)
    local = Column(String(500))  # XML: Local
    data_inicio = Column(DateTime, nullable=False)  # XML: DataInicio
    data_fim = Column(DateTime)  # XML: DataFim (rarely used)
    
    # Event classification based on XML structure source
    event_source = Column(
        String(20), 
        nullable=False, 
        comment="Source XML structure: 'Reunioes' for meetings, 'Visitas' for visits"
    )

    # Metadata
    created_at = Column(DateTime, default=func.now())

    # Relationships
    grupo = relationship("GrupoAmizadeStandalone", back_populates="reunioes")
    participantes = relationship(
        "GrupoAmizadeParticipante",
        back_populates="reuniao",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<GrupoAmizadeReuniao(id={self.meeting_id}, nome='{self.nome[:50]}...', local='{self.local}')>"


class GrupoAmizadeParticipante(Base):
    """
    Parliamentary Friendship Group Meeting Participants
    ==================================================

    Represents deputies and other participants in friendship group meetings
    and events, with their parliamentary group affiliation and roles.

    XML Structure: GrupoDeAmizadeReuniao/Participantes/RelacoesExternasParticipantes
    """

    __tablename__ = "grupos_amizade_participantes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    reuniao_id = Column(
        GUID(), ForeignKey("grupos_amizade_reunioes.id"), nullable=False
    )

    # Participant information (from RelacoesExternasParticipantes)
    participant_id = Column(Integer, nullable=False, index=True)  # XML: Id (deputy ID)
    nome = Column(String(500), nullable=False)  # XML: Nome
    tipo = Column(String(10), nullable=False)  # XML: Tipo (typically "D" for Deputy)
    grupo_parlamentar = Column(String(200))  # XML: Gp
    legislatura = Column(String(10))  # XML: Leg

    # Metadata
    created_at = Column(DateTime, default=func.now())

    # Relationships
    reuniao = relationship("GrupoAmizadeReuniao", back_populates="participantes")

    def __repr__(self):
        return f"<GrupoAmizadeParticipante(id={self.participant_id}, nome='{self.nome}', tipo='{self.tipo}')>"


# =====================================================
# ORÇAMENTO DO ESTADO (STATE BUDGET) MODELS
# =====================================================


class OrcamentoEstado(Base):
    """
    Base State Budget Model
    ======================

    Root container for State Budget data across all legislative periods.
    Handles both legacy (OEPropostasAlteracao) and current (OE) formats.

    Format Detection:
    - Legacy: OEPropostasAlteracao<numOE>*.xml (Legislaturas X-XV)
    - Current: OE<numOE>*.xml (Legislatura XVI+)

    Based on official Parliament documentation:
    - "Significado das Tags dos Ficheiros OEPropostasAlteracao<numOE>Or.xml/Al.xml"
    - "Significado das Tags dos Ficheiros OE<numOE>Or.xml/Al.xml"
    """

    __tablename__ = "orcamento_estado"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    legislatura_id = Column(GUID(), ForeignKey("legislaturas.id"), nullable=False)

    # File metadata
    file_path = Column(String(500), nullable=False)
    format_type = Column(String(10), nullable=False)  # 'legacy' or 'current'
    numero_orcamento = Column(String(20))  # OE number (e.g., "2020", "2021")
    tipo_arquivo = Column(String(10))  # 'Or' (Original) or 'Al' (Alterações)

    # Processing metadata
    total_propostas = Column(Integer, default=0)
    total_items = Column(Integer, default=0)
    data_processamento = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    legislatura = relationship("Legislatura")
    propostas_alteracao = relationship(
        "OrcamentoEstadoPropostaAlteracao", back_populates="orcamento"
    )
    items = relationship("OrcamentoEstadoItem", back_populates="orcamento")

    def __repr__(self):
        return f"<OrcamentoEstado(id={self.id}, format='{self.format_type}', num_orcamento='{self.numero_orcamento}')>"


class OrcamentoEstadoPropostaAlteracao(Base):
    """
    State Budget Amendment Proposal Model
    ====================================

    Represents amendment proposals in both legacy and current formats.
    Legacy format has more detailed workflow tracking.

    Legacy Structure (OEPropostasAlteracao):
    - Complex amendment proposal workflow with proponents, voting, regional opinions
    - Rich metadata about amendment scope and parliamentary processing

    Current Structure (OE/Item/PropostasDeAlteracao/Proposta):
    - Simplified proposal structure within budget items
    - Basic amendment information with less workflow detail

    XML Mapping:
    - ID/ID_PA: proposta_id (Unique proposal identifier)
    - Numero: numero (Proposal number)
    - Data: data_proposta (Proposal date)
    - Titulo/Objeto: titulo (Proposal title)
    """

    __tablename__ = "orcamento_estado_propostas_alteracao"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    orcamento_id = Column(GUID(), ForeignKey("orcamento_estado.id"), nullable=True)
    legislatura_id = Column(GUID(), ForeignKey("legislaturas.id"), nullable=False)
    item_id = Column(
        GUID(), ForeignKey("orcamento_estado_items.id"), nullable=True
    )  # Link to budget items

    # Core proposal identification
    proposta_id = Column(Integer, nullable=False, index=True)  # XML: ID/ID_PA
    numero = Column(String(50))  # XML: Numero
    data_proposta = Column(Date)  # XML: Data
    titulo = Column(Text)  # XML: Titulo/Objeto

    # Legacy format specific fields
    tema = Column(Text)  # XML: Tema (legacy only)
    apresentada = Column(String(200))  # XML: Apresentada (legacy only)
    incide = Column(String(50))  # XML: Incide (legacy only)
    tipo = Column(String(50))  # XML: Tipo
    estado = Column(String(100))  # XML: Estado
    numero_artigo_novo = Column(String(50))  # XML: NumeroArtigoNovo (legacy only)
    conteudo = Column(Text)  # XML: Conteudo (legacy only)
    ficheiro_url = Column(String(500))  # XML: Ficheiro
    grupo_parlamentar = Column(
        String(200)
    )  # XML: GrupoParlamentar_Partido (legacy only)

    # Current format specific fields
    id_pai = Column(Integer)  # XML: ID_Pai (current only)
    apresentado = Column(String(200))  # XML: Apresentado (current only)

    # Format identification
    format_type = Column(String(10), nullable=False)  # 'legacy' or 'current'

    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    orcamento = relationship("OrcamentoEstado", back_populates="propostas_alteracao")
    legislatura = relationship("Legislatura")
    item = relationship("OrcamentoEstadoItem", back_populates="propostas")
    proponentes = relationship("OrcamentoEstadoProponente", back_populates="proposta")
    votacoes = relationship("OrcamentoEstadoVotacao", back_populates="proposta")
    artigos = relationship("OrcamentoEstadoArtigo", back_populates="proposta")
    diploma_medidas = relationship(
        "OrcamentoEstadoDiplomaMedida",
        back_populates="proposta",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("proposta_id", name="uq_oe_proposta_id"),
        Index("idx_oe_proposta_id", "proposta_id"),
        Index("idx_oe_proposta_legislatura", "legislatura_id"),
        Index("idx_oe_proposta_format", "format_type"),
    )

    def __repr__(self):
        return f"<OrcamentoEstadoPropostaAlteracao(id={self.proposta_id}, numero='{self.numero}', format='{self.format_type}')>"


class OrcamentoEstadoItem(Base):
    """
    State Budget Item Model (Current Format)
    =======================================

    Represents budget items in current OE format (Legislatura XVI+).
    Items are hierarchical and can contain proposals, articles, diplomas, etc.

    Current Structure (OE/Item):
    - Hierarchical budget item structure with parent-child relationships
    - Type-based categorization (1=Diplomas, 2=Iniciativas/Artigos, 3=Iniciativas/Mapas)
    - Contains nested amendment proposals, voting records, and related data

    XML Mapping:
    - ID: item_id (Unique item identifier)
    - ID_Pai: id_pai (Parent item reference)
    - Tipo: tipo (Item type: 1, 2, or 3)
    - Numero: numero (Item number)
    - Titulo: titulo (Item title)
    - Texto: texto (Item text content)
    - Estado: estado (Item state)
    """

    __tablename__ = "orcamento_estado_items"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    orcamento_id = Column(GUID(), ForeignKey("orcamento_estado.id"), nullable=True)
    legislatura_id = Column(GUID(), ForeignKey("legislaturas.id"), nullable=False)

    # Core item identification
    item_id = Column(Integer, nullable=False, index=True)  # XML: ID
    id_pai = Column(Integer)  # XML: ID_Pai (parent item reference)
    tipo = Column(String(50))  # XML: Tipo (1, 2, or 3)
    tipo_desc = Column(String(200))  # Translated tipo value
    numero = Column(
        String(100)
    )  # XML: Numero - Increased to accommodate long decree references
    titulo = Column(Text)  # XML: Titulo
    texto = Column(Text)  # XML: Texto
    estado = Column(String(100))  # XML: Estado
    estado_desc = Column(String(200))  # Translated estado value

    # Format identification
    format_type = Column(String(10), default="current")

    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    orcamento = relationship("OrcamentoEstado", back_populates="items")
    legislatura = relationship("Legislatura")
    artigos = relationship("OrcamentoEstadoArtigo", back_populates="item")
    propostas = relationship("OrcamentoEstadoPropostaAlteracao", back_populates="item")
    diplomas = relationship("OrcamentoEstadoDiploma", back_populates="item")
    iniciativas = relationship("OrcamentoEstadoIniciativa", back_populates="item")
    votacoes = relationship("OrcamentoEstadoVotacao", back_populates="item")
    requerimentos_avocacao = relationship(
        "OrcamentoEstadoRequerimentoAvocacao", back_populates="item"
    )

    __table_args__ = (
        UniqueConstraint("item_id", name="uq_oe_item_id"),
        Index("idx_oe_item_id", "item_id"),
        Index("idx_oe_item_pai", "id_pai"),
        Index("idx_oe_item_tipo", "tipo"),
        Index("idx_oe_item_legislatura", "legislatura_id"),
    )

    def __repr__(self):
        return f"<OrcamentoEstadoItem(id={self.item_id}, tipo='{self.tipo}', titulo='{self.titulo[:50] if self.titulo else ''}...')>"


class OrcamentoEstadoProponente(Base):
    """
    State Budget Proposal Proponent Model
    ====================================

    Represents proponents (deputies/groups) of amendment proposals.
    Primarily used in legacy format with detailed proponent information.

    Legacy Structure (PropostasDeAlteracao/PropostaDeAlteracao/Proponentes/Proponente):
    - GP_Partido: grupo_parlamentar (Parliamentary group)
    - Deputado: deputado_nome (Deputy name)

    XML Mapping:
    - GP_Partido: grupo_parlamentar (Parliamentary group/party)
    - Deputado: deputado_nome (Deputy name if individual proponent)
    """

    __tablename__ = "orcamento_estado_proponentes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    proposta_id = Column(
        GUID(), ForeignKey("orcamento_estado_propostas_alteracao.id"), nullable=False
    )

    # Proponent information
    grupo_parlamentar = Column(String(200))  # XML: GP_Partido
    deputado_nome = Column(String(200))  # XML: Deputado
    tipo_proponente = Column(String(50))  # 'grupo' or 'deputado'

    # Metadata
    created_at = Column(DateTime, default=func.now())

    # Relationships
    proposta = relationship(
        "OrcamentoEstadoPropostaAlteracao", back_populates="proponentes"
    )

    def __repr__(self):
        return f"<OrcamentoEstadoProponente(gp='{self.grupo_parlamentar}', deputado='{self.deputado_nome}')>"


class OrcamentoEstadoVotacao(Base):
    """
    State Budget Voting Records Model
    ================================

    Represents voting records for proposals and items in both formats.
    Contains voting results and parliamentary group positions.

    Legacy Structure (PropostasDeAlteracao/PropostaDeAlteracao/Votacoes/Votacao):
    - More detailed voting information with group-by-group results

    Current Structure (Item/Votacoes/Votacao):
    - Simplified voting records within budget items

    XML Mapping:
    - Data: data_votacao (Voting date)
    - Resultado/ResultadoCompleto: resultado (Voting result)
    - Descricoes: descricao (Voting description)
    """

    __tablename__ = "orcamento_estado_votacoes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    proposta_id = Column(
        GUID(), ForeignKey("orcamento_estado_propostas_alteracao.id"), nullable=True
    )
    item_id = Column(GUID(), ForeignKey("orcamento_estado_items.id"), nullable=True)

    # Voting information
    data_votacao = Column(Date)  # XML: Data
    descricao = Column(Text)  # XML: Descricoes
    sub_descricao = Column(Text)  # XML: SubDescricao
    resultado = Column(Text)  # XML: Resultado/ResultadoCompleto
    diplomas_terceiros_texto = Column(Text)  # XML: DiplomasTerceiros (text storage)
    grupos_parlamentares_texto = Column(
        Text
    )  # XML: GruposParlamentares (JSON-like storage)

    # Metadata
    created_at = Column(DateTime, default=func.now())

    # Relationships
    proposta = relationship(
        "OrcamentoEstadoPropostaAlteracao", back_populates="votacoes"
    )
    item = relationship("OrcamentoEstadoItem", back_populates="votacoes")
    grupos_parlamentares_votos = relationship(
        "OrcamentoEstadoGrupoParlamentarVoto",
        back_populates="votacao",
        cascade="all, delete-orphan",
    )
    diplomas_terceiros = relationship(
        "OrcamentoEstadoDiplomaTerceiro",
        back_populates="votacao",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<OrcamentoEstadoVotacao(data='{self.data_votacao}', resultado='{self.resultado[:50] if self.resultado else ''}...')>"


class OrcamentoEstadoArtigo(Base):
    """
    State Budget Article Model
    =========================

    Represents articles within proposals and items.
    Can be nested within both legacy proposals and current items.

    Legacy Structure (PropostasDeAlteracao/PropostaDeAlteracao/Iniciativas_Artigos/Iniciativa_Artigo):
    - Artigo: numero (Article number)
    - Titulo: titulo (Article title)
    - Texto: texto (Article text)
    - Estado: estado (Article state)

    Current Structure (Item/Artigos/Artigo):
    - ID_Art: artigo_id (Article identifier)
    - ID_Pai: id_pai (Parent reference)
    - Similar structure with type, number, title, text, state

    XML Mapping:
    - ID_Art/Artigo: artigo_id/numero (Article identifier)
    - Numero: numero (Article number)
    - Titulo: titulo (Article title)
    - Texto: texto (Article text content)
    - Estado: estado (Article state)
    """

    __tablename__ = "orcamento_estado_artigos"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    proposta_id = Column(
        GUID(), ForeignKey("orcamento_estado_propostas_alteracao.id"), nullable=True
    )
    item_id = Column(GUID(), ForeignKey("orcamento_estado_items.id"), nullable=True)

    # Article identification
    artigo_id = Column(Integer)  # XML: ID_Art (current format)
    id_pai = Column(Integer)  # XML: ID_Pai (current format)
    numero = Column(
        String(200)
    )  # XML: Artigo/Numero (can be long titles like "LISTA I (BENS E SERVIÇOS...)")
    tipo = Column(String(100))  # XML: Tipo (current format)
    titulo = Column(Text().with_variant(mysql.LONGTEXT(), "mysql"))  # XML: Titulo
    texto = Column(Text().with_variant(mysql.LONGTEXT(), "mysql"))  # XML: Texto
    estado = Column(String(100))  # XML: Estado

    # Metadata
    created_at = Column(DateTime, default=func.now())

    # Relationships
    proposta = relationship(
        "OrcamentoEstadoPropostaAlteracao", back_populates="artigos"
    )
    item = relationship("OrcamentoEstadoItem", back_populates="artigos")
    numeros = relationship(
        "OrcamentoEstadoArtigoNumero",
        back_populates="artigo",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<OrcamentoEstadoArtigo(numero='{self.numero}', titulo='{self.titulo[:50] if self.titulo else ''}...')>"


class OrcamentoEstadoDiploma(Base):
    """
    State Budget Diploma Model (Current Format)
    ==========================================

    Represents diplomas to be modified within budget items.
    Used in current format for type 1 items (Diplomas a modificar).

    Current Structure (Item/DiplomasaModificar/DiplomaModificar):
    - ID_Dip: diploma_id (Diploma identifier)
    - DiplomaTitulo: titulo (Diploma title)
    - DiplomaSubTitulo: sub_titulo (Diploma subtitle)
    - DiplomasArtigos: artigos_texto (Related articles text)

    XML Mapping:
    - ID_Dip: diploma_id (Diploma identifier)
    - DiplomaTitulo: titulo (Diploma title)
    - DiplomaSubTitulo: sub_titulo (Diploma subtitle)
    - DiplomasArtigos: artigos_texto (Related articles)
    """

    __tablename__ = "orcamento_estado_diplomas"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    item_id = Column(GUID(), ForeignKey("orcamento_estado_items.id"), nullable=False)

    # Diploma identification
    diploma_id = Column(Integer)  # XML: ID_Dip
    titulo = Column(Text)  # XML: DiplomaTitulo
    sub_titulo = Column(Text)  # XML: DiplomaSubTitulo
    artigos_texto = Column(Text)  # XML: DiplomasArtigos

    # Metadata
    created_at = Column(DateTime, default=func.now())

    # Relationships
    item = relationship("OrcamentoEstadoItem", back_populates="diplomas")
    artigos_detalhados = relationship(
        "OrcamentoEstadoDiplomaArtigo", back_populates="diploma"
    )

    def __repr__(self):
        return f"<OrcamentoEstadoDiploma(id={self.diploma_id}, titulo='{self.titulo[:50] if self.titulo else ''}...')>"


class OrcamentoEstadoIniciativa(Base):
    """
    State Budget Initiative/Map Model (Current Format)
    =================================================

    Represents initiatives and maps within budget items.
    Used in current format for type 3 items (Iniciativas/Mapas).

    Current Structure (Item/IniciativasMapas/IniciativaMapa):
    - MapasNumero: numero (Map number)
    - MapasTitulo: titulo (Map title)
    - MapasEstado: estado (Map state)
    - MapasLink: link_url (Map link/URL)

    XML Mapping:
    - MapasNumero: numero (Map/initiative number)
    - MapasTitulo: titulo (Map/initiative title)
    - MapasEstado: estado (Map/initiative state)
    - MapasLink: link_url (Map/initiative link)
    """

    __tablename__ = "orcamento_estado_iniciativas"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    item_id = Column(GUID(), ForeignKey("orcamento_estado_items.id"), nullable=False)

    # Initiative/Map information
    numero = Column(String(50))  # XML: MapasNumero
    titulo = Column(Text)  # XML: MapasTitulo
    estado = Column(String(100))  # XML: MapasEstado
    link_url = Column(String(500))  # XML: MapasLink

    # Metadata
    created_at = Column(DateTime, default=func.now())

    # Relationships
    item = relationship("OrcamentoEstadoItem", back_populates="iniciativas")

    def __repr__(self):
        return f"<OrcamentoEstadoIniciativa(numero='{self.numero}', titulo='{self.titulo[:50] if self.titulo else ''}...')>"


class OrcamentoEstadoDiplomaArtigo(Base):
    """
    State Budget Diploma Article Model
    =================================

    Represents individual articles within diploma modifications.
    Handles the nested DiplomasArtigos.DiplomaArtigo structure.

    XML Mapping (DiplomasArtigos.DiplomaArtigo):
    - ID_Art: artigo_id (Article identifier)
    - Numero: numero (Article number)
    - Titulo: titulo (Article title)
    - Texto: texto (Article content)
    - Estado: estado (Article state)
    """

    __tablename__ = "orcamento_estado_diploma_artigos"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    diploma_id = Column(
        GUID(), ForeignKey("orcamento_estado_diplomas.id"), nullable=False
    )

    # Article identification
    artigo_id = Column(Integer, comment="Article ID (ID_Art)")
    diploma_artigo_id_alt = Column(
        Integer, comment="Alternative Article ID (DiplomaArtigoID)"
    )
    numero = Column(String(100), comment="Article number (Numero)")
    titulo = Column(Text, comment="Article title (Titulo)")
    diploma_artigo_titulo_alt = Column(
        Text, comment="Alternative Article title (DiplomaArtigoTituto)"
    )
    diploma_artigo_subtitulo = Column(
        Text, comment="Alternative Article subtitle (DiplomaArtigoSubTitulo)"
    )
    texto = Column(Text, comment="Article content (Texto)")
    diploma_artigo_texto = Column(
        Text, comment="Alternative Article text (DiplomaArtigoTexto)"
    )
    estado = Column(String(100), comment="Article state (Estado)")
    diploma_artigo_estado = Column(
        String(100), comment="Alternative Article state (DiplomaArtigoEstado)"
    )

    # Metadata
    created_at = Column(DateTime, default=func.now())

    # Relationships
    diploma = relationship(
        "OrcamentoEstadoDiploma", back_populates="artigos_detalhados"
    )
    numeros = relationship(
        "OrcamentoEstadoDiplomaNumero", back_populates="diploma_artigo"
    )


class OrcamentoEstadoDiplomaNumero(Base):
    """
    State Budget Diploma Number Model
    ================================

    Represents diploma numbers within diploma articles.
    Handles the nested DiplomaNumeros.DiplomaNumero structure.

    XML Mapping (DiplomaNumeros.DiplomaNumero):
    - DiplomaNumeroTitulo: titulo (Number title)
    - DiplomaNumeroEstado: estado (Number state)
    """

    __tablename__ = "orcamento_estado_diploma_numeros"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    diploma_artigo_id = Column(
        GUID(), ForeignKey("orcamento_estado_diploma_artigos.id"), nullable=False
    )

    # Number information
    diploma_numero_id = Column(Integer, comment="Number ID (DiplomaNumeroID)")
    titulo = Column(Text, comment="Number title (DiplomaNumeroTitulo)")
    estado = Column(String(100), comment="Number state (DiplomaNumeroEstado)")

    # Metadata
    created_at = Column(DateTime, default=func.now())

    # Relationships
    diploma_artigo = relationship(
        "OrcamentoEstadoDiplomaArtigo", back_populates="numeros"
    )
    alineas = relationship(
        "OrcamentoEstadoDiplomaAlinea", back_populates="diploma_numero"
    )


class OrcamentoEstadoDiplomaAlinea(Base):
    """
    State Budget Diploma Alinea Model
    ================================

    Represents diploma alineas within diploma numbers.
    Handles the nested DiplomaAlineas.DiplomaAlinea structure.

    XML Mapping (DiplomaAlineas.DiplomaAlinea):
    - DiplomaAlineaTitulo: titulo (Alinea title)
    """

    __tablename__ = "orcamento_estado_diploma_alineas"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    diploma_numero_id = Column(
        GUID(), ForeignKey("orcamento_estado_diploma_numeros.id"), nullable=False
    )

    # Alinea information
    titulo = Column(Text, comment="Alinea title (DiplomaAlineaTitulo)")
    estado = Column(String(100), comment="Alinea state (DiplomaAlineaEstado)")

    # Metadata
    created_at = Column(DateTime, default=func.now())

    # Relationships
    diploma_numero = relationship(
        "OrcamentoEstadoDiplomaNumero", back_populates="alineas"
    )


class OrcamentoEstadoRequerimentoAvocacao(Base):
    """
    State Budget Avocation Request Model
    ===================================

    Represents avocation requests within budget items.
    Handles the RequerimentosDeAvocacao.RequerimentoDeAvocacao structure.

    XML Mapping (RequerimentosDeAvocacao.RequerimentoDeAvocacao):
    - AvocacaoDescricao: descricao (Request description)
    - AvocacaoData: data_avocacao (Request date)
    - AvocacaoTitulo: titulo (Request title)
    - AvocacaoEstado: estado (Request state)
    - AvocacaoFicheiro: ficheiro_url (Request file URL)
    """

    __tablename__ = "orcamento_estado_requerimentos_avocacao"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    item_id = Column(GUID(), ForeignKey("orcamento_estado_items.id"), nullable=False)

    # Avocation request information
    descricao = Column(Text, comment="Request description (AvocacaoDescricao)")
    data_avocacao = Column(Date, comment="Request date (AvocacaoData)")
    titulo = Column(Text, comment="Request title (AvocacaoTitulo)")
    estado = Column(String(100), comment="Request state (AvocacaoEstado)")
    ficheiro_url = Column(String(500), comment="Request file URL (AvocacaoFicheiro)")

    # Metadata
    created_at = Column(DateTime, default=func.now())

    # Relationships
    item = relationship("OrcamentoEstadoItem", back_populates="requerimentos_avocacao")


class OrcamentoEstadoGrupoParlamentarVoto(Base):
    """
    State Budget Parliamentary Group Vote Model
    ==========================================

    Represents individual parliamentary group votes within voting records.
    Handles the GruposParlamentares nested structure within Votacao.

    XML Structure: Votacoes/Votacao/GruposParlamentares
    The structure alternates between GrupoParlamentar and Voto elements:
    <GruposParlamentares>
        <GrupoParlamentar>Partido Social Democrata</GrupoParlamentar>
        <Voto>Abstenção</Voto>
        <GrupoParlamentar>Partido Socialista</GrupoParlamentar>
        <Voto>Favor</Voto>
    </GruposParlamentares>

    XML Mapping:
    - GrupoParlamentar: grupo_parlamentar (Parliamentary group name)
    - Voto: voto (Vote result: Favor, Contra, Abstenção)
    """

    __tablename__ = "orcamento_estado_grupos_parlamentares_votos"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    votacao_id = Column(
        GUID(), ForeignKey("orcamento_estado_votacoes.id"), nullable=False
    )

    # Parliamentary group and vote information
    grupo_parlamentar = Column(
        String(200), comment="Parliamentary group name (GrupoParlamentar)"
    )
    voto = Column(String(50), comment="Vote result (Voto): Favor, Contra, Abstenção")

    # Metadata
    created_at = Column(DateTime, default=func.now())

    # Relationships
    votacao = relationship(
        "OrcamentoEstadoVotacao", back_populates="grupos_parlamentares_votos"
    )


class OrcamentoEstadoArtigoNumero(Base):
    """
    State Budget Article Number Model
    ================================

    Represents numbers within articles.
    Handles the Numeros.Numero structure within Iniciativas_Artigos.

    XML Structure: Iniciativa_Artigo/Numeros/Numero

    XML Mapping:
    - Numero: numero (Number identifier e.g., "N.º 1", "N.º 2")
    - Titulo: titulo (Number title)
    - Texto: texto (Number text content)
    - Estado: estado (Number state)
    """

    __tablename__ = "orcamento_estado_artigo_numeros"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    artigo_id = Column(
        GUID(), ForeignKey("orcamento_estado_artigos.id"), nullable=False
    )

    # Number information
    numero = Column(String(50), comment="Number identifier (Numero)")
    titulo = Column(Text, comment="Number title (Titulo)")
    texto = Column(Text, comment="Number text content (Texto)")
    estado = Column(String(100), comment="Number state (Estado)")

    # Metadata
    created_at = Column(DateTime, default=func.now())

    # Relationships
    artigo = relationship("OrcamentoEstadoArtigo", back_populates="numeros")
    alineas = relationship(
        "OrcamentoEstadoArtigoAlinea",
        back_populates="numero",
        cascade="all, delete-orphan",
    )


class OrcamentoEstadoArtigoAlinea(Base):
    """
    State Budget Article Alinea Model
    =================================

    Represents alineas within article numbers.
    Handles the Alineas.Alinea structure within Numeros.

    XML Structure: Iniciativa_Artigo/Numeros/Numero/Alineas/Alinea

    XML Mapping:
    - Alinea: alinea (Alinea identifier e.g., "Alínea a)", "Alínea b)")
    - Titulo: titulo (Alinea title)
    - Texto: texto (Alinea text content)
    - Estado: estado (Alinea state)
    """

    __tablename__ = "orcamento_estado_artigo_alineas"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    numero_id = Column(
        GUID(), ForeignKey("orcamento_estado_artigo_numeros.id"), nullable=False
    )

    # Alinea information
    alinea = Column(String(50), comment="Alinea identifier (Alinea)")
    titulo = Column(Text, comment="Alinea title (Titulo)")
    texto = Column(Text, comment="Alinea text content (Texto)")
    estado = Column(String(100), comment="Alinea state (Estado)")

    # Metadata
    created_at = Column(DateTime, default=func.now())

    # Relationships
    numero = relationship("OrcamentoEstadoArtigoNumero", back_populates="alineas")


class OrcamentoEstadoDiplomaTerceiro(Base):
    """
    State Budget Third-Party Diploma Model
    ======================================

    Represents references to third-party diplomas or law proposals.
    Handles the DiplomasTerceirosouPropostasDeLeiMapas.Diploma structure.

    XML Structure: Votacao/DiplomasTerceirosouPropostasDeLeiMapas/Diploma

    XML Mapping:
    - Diploma: diploma_referencia (Diploma reference code or description)
    """

    __tablename__ = "orcamento_estado_diplomas_terceiros"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    votacao_id = Column(
        GUID(), ForeignKey("orcamento_estado_votacoes.id"), nullable=False
    )

    # Diploma reference information
    diploma_referencia = Column(Text, comment="Diploma reference (Diploma)")

    # Metadata
    created_at = Column(DateTime, default=func.now())

    # Relationships
    votacao = relationship(
        "OrcamentoEstadoVotacao", back_populates="diplomas_terceiros"
    )


class OrcamentoEstadoDiplomaMedida(Base):
    """
    State Budget Diploma Measure Model
    =================================

    Represents diploma measures within proposals.
    Handles the DiplomasMedidas.DiplomaMedida structure.

    XML Structure: PropostaDeAlteracao/DiplomasMedidas/DiplomaMedida

    XML Mapping:
    - Titulo: titulo (Diploma measure title)
    - Texto: texto (Diploma measure text content)
    """

    __tablename__ = "orcamento_estado_diploma_medidas"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    proposta_id = Column(
        GUID(), ForeignKey("orcamento_estado_propostas_alteracao.id"), nullable=False
    )

    # Diploma measure information
    titulo = Column(Text, comment="Diploma measure title (Titulo)")
    texto = Column(Text, comment="Diploma measure text (Texto)")

    # Metadata
    created_at = Column(DateTime, default=func.now())

    # Relationships
    proposta = relationship(
        "OrcamentoEstadoPropostaAlteracao", back_populates="diploma_medidas"
    )
    numeros_medidas = relationship(
        "OrcamentoEstadoDiplomaMedidaNumero",
        back_populates="diploma_medida",
        cascade="all, delete-orphan",
    )


class OrcamentoEstadoDiplomaMedidaNumero(Base):
    """
    State Budget Diploma Measure Number Model
    ========================================

    Represents numbered measures within diploma measures.
    Handles the NumerosMedidas.NumeroMedida structure.

    XML Structure: DiplomaMedida/NumerosMedidas/NumeroMedida

    XML Mapping:
    - Designacao: designacao (Measure number designation)
    """

    __tablename__ = "orcamento_estado_diploma_medida_numeros"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    diploma_medida_id = Column(
        GUID(), ForeignKey("orcamento_estado_diploma_medidas.id"), nullable=False
    )

    # Measure number information
    designacao = Column(Text, comment="Measure number designation (Designacao)")

    # Metadata
    created_at = Column(DateTime, default=func.now())

    # Relationships
    diploma_medida = relationship(
        "OrcamentoEstadoDiplomaMedida", back_populates="numeros_medidas"
    )


# =====================================================
# REUNIÕES E VISITAS (MEETINGS AND VISITS) MODELS
# =====================================================


class ReuniaoNacional(Base):
    """
    National Meetings and Visits Model - Based on ReunioesNacionais.xml specification

    Manages meetings and visits outside the scope of other external relations categories
    promoted by the Portuguese Parliament (Assembleia da República).

    ReunioesNacionais.xml Mapping (Reuniao structure):
    - Id: reuniao_id (Meeting registry identifier)
    - Nome: nome (Meeting title)
    - Tipo: tipo (Meeting type: RNI/RNN/VEE using TipoReuniaoVisita enum)
    - Local: local (Meeting location)
    - Legislatura: legislatura_id (Legislature identifier - foreign key)
    - Sessão: sessao (Legislative session number)
    - DataInicio: data_inicio (Meeting start date)
    - DataFim: data_fim (Meeting end date)
    - Promotor: promotor (Meeting organizer/promoter)
    - Participantes: participantes (List via ParticipanteReuniaoNacional relationship)

    Meeting Types (Tipo field):
    - RNI: Reunião Internacional (International Meeting)
    - RNN: Reunião Nacional (National Meeting)
    - VEE: Visita de entidade estrangeira (Foreign Entity Visit)

    External Relations Context:
    - Covers meetings and visits outside standard parliamentary categories
    - Focuses on external relations and international cooperation activities
    - Includes visits from foreign entities and international meeting participation

    Usage:
        Central model for external relations meetings and visits
        Links to deputy participants via ParticipanteReuniaoNacional
        References legislature periods for temporal organization
    """

    __tablename__ = "reunioes_nacionais"
    __table_args__ = (
        Index("idx_reuniao_nacional_reuniao_id", "reuniao_id"),
        Index("idx_reuniao_nacional_tipo", "tipo"),
        Index("idx_reuniao_nacional_legislatura", "legislatura_id"),
        Index("idx_reuniao_nacional_data", "data_inicio"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    reuniao_id = Column(
        Integer,
        unique=True,
        nullable=False,
        comment="Meeting registry identifier (XML: Id)",
    )
    nome = Column(Text, comment="Meeting title (XML: Nome)")
    tipo = Column(String(10), comment="Meeting type: RNI/RNN/VEE (XML: Tipo)")
    local = Column(Text, comment="Meeting location (XML: Local)")
    legislatura_id = Column(
        GUID(),
        ForeignKey("legislaturas.id"),
        nullable=False,
        comment="Legislature identifier (XML: Legislatura)",
    )
    sessao = Column(Integer, comment="Legislative session number (XML: Sessão)")
    data_inicio = Column(Date, comment="Meeting start date (XML: DataInicio)")
    data_fim = Column(Date, comment="Meeting end date (XML: DataFim)")
    promotor = Column(Text, comment="Meeting organizer/promoter (XML: Promotor)")
    observacoes = Column(Text, comment="Meeting observations/notes (XML: observacoes)")
    tipo_designacao = Column(String(100), comment="Meeting type designation (XML: tipoDesignacao)")

    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    legislatura = relationship("Legislatura")
    participantes = relationship(
        "ParticipanteReuniaoNacional",
        back_populates="reuniao",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<ReuniaoNacional(id={self.reuniao_id}, nome='{self.nome[:50] if self.nome else ''}...', tipo='{self.tipo}')>"


class ParticipanteReuniaoNacional(Base):
    """
    National Meeting Participant Model - Based on ReunioesNacionais.xml Participante structure

    Tracks deputy participation in external relations meetings and visits,
    providing complete deputy information and parliamentary group affiliation.

    ReunioesNacionais.xml Mapping (Participante structure):
    - Tipo: tipo (Participant type: D=Deputado using TipoParticipanteReuniao enum)
    - Nome: nome (Deputy participant name)
    - Gp: grupo_parlamentar (Parliamentary group affiliation)
    - Leg: legislatura (Legislature identifier for deputy context)
    - Id: deputado_id (Deputy identifier)

    Participant Type:
    - D: Deputado (Deputy) - currently the only supported participant type
    - Indicates focus on deputy participation in external relations activities

    Parliamentary Context:
    - Links meeting participation to specific deputy records
    - Preserves parliamentary group affiliation at time of meeting
    - Maintains legislature context for deputy identification

    Usage:
        Links deputies to specific meetings/visits
        Tracks parliamentary group representation in external relations
        Supports analysis of deputy international engagement patterns
    """

    __tablename__ = "participantes_reunioes_nacionais"
    __table_args__ = (
        Index("idx_participante_reuniao_nacional_reuniao", "reuniao_id"),
        Index("idx_participante_reuniao_nacional_deputado", "deputado_id"),
        Index("idx_participante_reuniao_nacional_gp", "grupo_parlamentar"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    reuniao_id = Column(
        GUID(),
        ForeignKey("reunioes_nacionais.id"),
        nullable=False,
        comment="Meeting foreign key reference",
    )
    tipo = Column(String(10), comment="Participant type: D=Deputado (XML: Tipo)")
    nome = Column(String(200), comment="Deputy participant name (XML: Nome)")
    grupo_parlamentar = Column(
        String(50), comment="Parliamentary group affiliation (XML: Gp)"
    )
    legislatura = Column(
        String(20), comment="Legislature identifier for deputy context (XML: Leg)"
    )
    deputado_id = Column(Integer, comment="Deputy identifier (XML: Id)")

    # Metadata
    created_at = Column(DateTime, default=func.now())

    # Relationships
    reuniao = relationship("ReuniaoNacional", back_populates="participantes")

    def __repr__(self):
        return f"<ParticipanteReuniaoNacional(nome='{self.nome}', gp='{self.grupo_parlamentar}', tipo='{self.tipo}')>"


# =============================================================================
# FLASK-SQLALCHEMY COMPATIBILITY
# =============================================================================

# For Flask-SQLAlchemy compatibility, create a mock db object
class MockDB:
    """Mock Flask-SQLAlchemy db object for compatibility with Flask apps."""
    
    def __init__(self):
        self.Model = Base
        
    def init_app(self, app):
        """Initialize with Flask app - no-op since we use pure SQLAlchemy."""
        pass

# Create the db instance that Flask expects
db = MockDB()
