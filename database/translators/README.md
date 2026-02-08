# Portuguese Parliament Field Translators

This directory contains thematic field translation modules for Portuguese Parliament data, organized by functional area.

## Module Organization

### `publications.py`
- **TipodePublicacao** enum with 21 publication type codes
- Used across models: IntervencaoParlamentar, IniciativaPublicacao, RequerimentoPublicacao
- Translates codes like "A" → "DAR II série A"

### `deputy_activities.py` 
- **TipodeAtividade** enum with 24 activity type codes
- **TipodeRequerimento** enum with 5 request type codes
- **Committee status** translations (suplente/efetivo)
- **Delegation types** (Nacional/Internacional)
- Used across models: ActividadesParlamentaresOut, ActividadesComissaoOut, RequerimentosOut

### `initiatives.py`
- **TipodeIniciativa** enum with 11 initiative type codes  
- **Initiative phases** for parliamentary procedure stages
- Used across models: IniciativasOut, IniciativaParlamentar

### `parliamentary_interventions.py`
- **Intervention types** for parliamentary debates
- **Publication supplements** and Assembly Diary formatting
- Combines intervention-specific logic with shared publication types
- Used across models: IntervencaoParlamentar, IntervencaoPublicacao

### `general_activities.py`
- **TipodeAutor** enum for parliamentary activity author types (11 codes: A, C, D, G, I, M, P, R, U, V, Z)
- **TipodeEvento** enum for parliamentary event types (11 codes: 2, 3, 4, 5, 42, 61, 81, 101, 121, 141, 161)
- **TipodeDeslocacoes** enum for displacement types (6 codes: CO, DV, MI, PR, SM, VO)
- **TipodeReuniao** enum for meeting types (8 codes: AG, AS, AU, CO, CR, GA, IE, PP)
- Used across models: AtividadeParlamentar, EventoParlamentar, DeslocacaoParlamentar, VotacaoOut

### `agenda_parlamentar.py`
- **SectionType** enum for agenda section types (24 codes: 1-24)
- **ThemeType** enum for agenda theme types (16 codes: 1-16)
- Used across models: AgendaParlamentar (secao_id, tema_id fields)

### `delegacao_eventual.py`
- Uses shared **TipoParticipante** enum from common_enums
- Used across models: DelegacaoEventualParticipante (tipo_participante field)

### `delegacoes_permanentes.py`
- **TipoReuniao** enum for meeting types (2 codes: REN, RNI)
- Uses shared **TipoParticipante** enum from common_enums
- Used across models: DelegacaoPermanente meeting and participant records

### `common_enums.py`
- **TipoParticipante** enum for participant types (1 code: D)
- Shared across multiple modules to avoid duplication
- Used in both eventual and permanent delegations

### `registo_biografico.py`
- **SexoType** enum for gender classification (2 codes: M, F)
- **EstadoCivilType** enum for marital status (5 codes: S, C, D, V, UF)
- **HabilitacaoEstadoType** enum for qualification status (5 codes: CONCLUIDA, EM_CURSO, INTERROMPIDA, ABANDONADA, SUSPENSA)
- **CargoFuncaoAntigaType** enum for historical position flag (2 codes: S, N)
- **TipoAtividadeOrgaoType** enum for parliamentary organ activity types (2 codes: ATIVIDADE_COM, ATIVIDADE_GT)
- **PosicaoOrgaoType** enum for parliamentary positions (6 codes: PRESIDENTE, VICE_PRESIDENTE, RELATOR, VOGAL, SECRETARIO, MEMBRO)
- **LegislaturaDesignacaoType** enum for legislature designations (15 codes: CONSTITUINTE, IA-XV)
- **CirculoEleitoralType** enum for electoral circles (22 codes: 18 districts + 4 special)
- Used across biographical models: Deputado, DeputadoHabilitacao, DeputadoCargoFuncao, DeputadoAtividadeOrgao, DeputadoMandatoLegislativo

### `reunioes_visitas.py`
- **TipoReuniaoVisita** enum for meeting/visit types (3 codes: RNI, RNN, VEE)
- **TipoParticipanteReuniao** enum for meeting participant types (1 code: D)
- Used across meeting models: ReuniaoNacional, ParticipanteReuniaoNacional

## Usage Patterns

### Individual Model Translation
```python
from database.translators.deputy_activities import deputy_activity_translator

# In your application/API layer
activity = session.query(ActividadesParlamentaresOut).first()
readable_type = deputy_activity_translator.activity_type(activity.act_tp)
```

### API Response Formatting
```python
from database.translators.publications import publication_translator

intervention = session.query(IntervencaoParlamentar).first()
api_response = {
    "id": intervention.id,
    "publication_type": {
        "code": intervention.pub_tp,
        "description": publication_translator.publication_type(intervention.pub_tp)
    }
}
```

### Validation Workflows
```python
from database.translators.initiatives import initiative_translator

translation = initiative_translator.get_initiative_type("J")
if translation.is_valid:
    print(f"Valid initiative: {translation.description}")
else:
    print(f"Invalid code: {translation.code}")
```

## Design Principles

1. **Thematic Organization**: Each module focuses on a specific functional area
2. **Enum-Based Safety**: All translations use Python enums for type safety
3. **Official Documentation**: All mappings based on December 2017 Parliament docs
4. **Separation of Concerns**: Translation logic separated from data processing
5. **Shared Components**: Common functionality (like publications) reused across modules
6. **Validation Support**: All translators provide validity checks for codes

## Cross-References

### Database Models → Translator Mapping

| Model | Field | Translator Module | Method |
|-------|-------|------------------|---------|
| IntervencaoParlamentar | pub_tp | publications | publication_type() |
| ActividadesParlamentaresOut | act_tp | deputy_activities | activity_type() |
| IniciativasOut | ini_tp | initiatives | initiative_type() |
| RequerimentosOut | req_tp | deputy_activities | request_type() |
| ComissoesOut | cms_situacao | deputy_activities | committee_status() |
| AtividadeParlamentar | tipo_autor | general_activities | author_type() |
| EventoParlamentar | tipo_evento | general_activities | event_type() |
| DeslocacaoParlamentar | displacement_type | general_activities | displacement_type() |
| VotacaoOut | TipoReuniao | general_activities | meeting_type() |
| AgendaParlamentar | secao_id | agenda_parlamentar | section_type() |
| AgendaParlamentar | tema_id | agenda_parlamentar | theme_type() |
| DelegacaoEventualParticipante | tipo_participante | delegacao_eventual | participant_type() |
| DelegacaoPermanente | meeting_type | delegacoes_permanentes | meeting_type() |
| DelegacaoPermanente | participant_type | delegacoes_permanentes | participant_type() |
| Deputado | sexo | registo_biografico | gender() |
| Deputado | estado_civil_cod | registo_biografico | marital_status() |
| DeputadoHabilitacao | hab_estado | registo_biografico | qualification_status() |
| DeputadoCargoFuncao | fun_antiga | registo_biografico | position_historical_flag() |
| DeputadoAtividadeOrgao | tipo_atividade | registo_biografico | organ_activity_type() |
| DeputadoAtividadeOrgao | tia_des | registo_biografico | organ_position_type() |
| DeputadoMandatoLegislativo | leg_des | registo_biografico | legislature_designation() |
| DeputadoMandatoLegislativo | ce_des | registo_biografico | electoral_circle() |
| ReuniaoNacional | tipo | reunioes_visitas | meeting_type() |
| ParticipanteReuniaoNacional | tipo | reunioes_visitas | participant_type() |

### Official Documentation Mapping

All translations are based on multiple official sources:
- **AtividadeDeputado**: "Significado das Tags do Ficheiro AtividadeDeputado<Legislatura>.xml" (December 2017)
- **Atividades**: "VI_Legislatura Atividades.xml" structure documentation (December 2017)
- **AgendaParlamentar**: "AgendaParlamentar.xml/.json" structure documentation (June 2023)
- **DelegacoesEventuais**: "DelegacoesEventuais.xml" structure documentation (December 2017)
- **DelegacoesPermanentes**: "DelegacoesPermanentes.xml" structure documentation (December 2017)
- **RegistoBiografico**: "Estruturas de dados do Registo Biográfico dos Deputados" specifications (December 2017 and May 2023)
- **ReunioesNacionais**: "Significado das Tags do Ficheiro ReunioesNacionais.xml" specification (December 2017)
- **Validation**: Consistent across legislatures with version-specific updates
- **Location**: `E:\dev\parliament\scripts\data_processing\data\downloads\`