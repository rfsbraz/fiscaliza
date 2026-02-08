# Análise da Estrutura dos Dados do Parlamento Português

## 1. Informação Base (XVII Legislatura)

### Estrutura do XML:
- **Root element**: `pt_gov_ar_objectos_InformacaoBase`
- **Namespace**: `http://schemas.parlamento.pt/`
- **Encoding**: UTF-8

### Elementos principais:
1. **Deputados** (`pt_gov_ar_objectos_PessoaDeputado`)
   - ID único do deputado
   - Nome completo
   - Nome parlamentar
   - Data de nascimento
   - Sexo
   - Partido político
   - Círculo eleitoral
   - Profissão
   - Habilitações literárias
   - Mandatos (com datas de início e fim)

2. **Partidos** (`pt_gov_ar_objectos_Partido`)
   - ID único do partido
   - Sigla
   - Designação completa
   - Data de constituição

3. **Círculos Eleitorais** (`pt_gov_ar_objectos_Circulo`)
   - ID único do círculo
   - Designação
   - Tipo (territorial, emigração, etc.)

4. **Comissões** (`pt_gov_ar_objectos_Comissao`)
   - ID único da comissão
   - Sigla
   - Designação
   - Tipo de comissão
   - Estado (ativa/inativa)

### Relações identificadas:
- Deputados ↔ Partidos (através de ID do partido)
- Deputados ↔ Círculos Eleitorais (através de ID do círculo)
- Deputados ↔ Comissões (através de membros das comissões)
- Mandatos ↔ Deputados (histórico de mandatos)

### Campos importantes para análise:
- Distribuição por género
- Distribuição por partido
- Distribuição por círculo eleitoral
- Idades dos deputados
- Profissões mais comuns
- Habilitações literárias
- Duração dos mandatos



## 2. Agenda Parlamentar (XVII Legislatura)

### Estrutura do XML:
- **Root element**: `ArrayOfAgendaParlamentar`
- **Namespace**: Padrão XML Schema
- **Encoding**: UTF-8

### Elementos principais:
1. **AgendaParlamentar** (cada evento da agenda)
   - **Id**: Identificador único do evento
   - **SectionId**: ID da secção
   - **Section**: Nome da secção (ex: "Grupos Parlamentares / Partidos / DURP / Ninsc")
   - **ThemeId**: ID do tema
   - **Theme**: Nome do tema
   - **OrderValue**: Valor de ordenação
   - **ParlamentGroup**: ID do grupo parlamentar
   - **AllDayEvent**: Booleano se é evento de dia inteiro
   - **EventStartDate**: Data de início (formato DD/MM/YYYY)
   - **EventStartTime**: Hora de início (pode ser null)
   - **EventEndDate**: Data de fim
   - **EventEndTime**: Hora de fim (pode ser null)
   - **Title**: Título do evento
   - **Subtitle**: Subtítulo (pode ser null)
   - **InternetText**: Texto HTML com detalhes do evento
   - **Local**: Local do evento (pode ser null)
   - **Link**: Link relacionado (pode ser null)
   - **LegDes**: Designação da legislatura (ex: "XVII")
   - **OrgDes**: Designação do órgão (pode ser null)
   - **ReuNumero**: Número da reunião (pode ser null)
   - **SelNumero**: Número da sessão (pode ser null)
   - **PostPlenary**: Booleano se é pós-plenário
   - **AnexosComissaoPermanente**: Anexos de comissão permanente (pode ser null)
   - **AnexosPlenario**: Anexos de plenário (pode ser null)

### Relações identificadas:
- Eventos ↔ Grupos Parlamentares (através de ParlamentGroup)
- Eventos ↔ Secções/Temas (através de SectionId/ThemeId)
- Eventos ↔ Legislaturas (através de LegDes)

### Tipos de eventos encontrados:
- Audiências de grupos parlamentares
- Reuniões de comissões
- Sessões plenárias
- Eventos especiais

### Campos importantes para análise:
- Distribuição de eventos por grupo parlamentar
- Tipos de audiências mais frequentes
- Padrões temporais de atividade
- Organizações que mais participam em audiências


## 3. Iniciativas (XVII Legislatura) - Análise Detalhada

### Estrutura do XML:
- **Root element**: `ArrayOfPt_gov_ar_objectos_iniciativas_DetalhePesquisaIniciativasOut`
- **Total de registos**: 357 iniciativas
- **Elementos únicos**: 156 tipos diferentes

### Elementos principais de cada Iniciativa:
1. **Dados Básicos**:
   - **IniNr**: Número da iniciativa
   - **IniTipo**: Tipo (P=Proposta, PL=Projeto de Lei, etc.)
   - **IniDescTipo**: Descrição do tipo
   - **IniLeg**: Legislatura (XVII)
   - **IniSel**: Sessão legislativa
   - **DataInicioleg**: Data de início da legislatura
   - **IniTitulo**: Título da iniciativa
   - **IniTextoSubst**: Se tem texto substituto (NAO/SIM)
   - **IniLinkTexto**: Link para o documento PDF
   - **IniId**: ID único da iniciativa

2. **Autores e Comissões**:
   - **IniAutorGoverno**: Autor do governo
   - **IniAutorOutros**: Outros autores
   - **ComissaoInOut**: Dados da comissão responsável

3. **Eventos e Votações** (DESCOBERTA IMPORTANTE):
   - **IniEventos**: Contém todos os eventos relacionados com a iniciativa
   - **Votacao**: Dados detalhados de votações
     - **id**: ID da votação
     - **resultado**: Resultado da votação
     - **reuniao**: Número da reunião
     - **tipoReuniao**: Tipo de reunião
     - **unanime**: Se foi unânime (quando aplicável)
     - **ausencias**: Deputados ausentes
     - **abstencoes**: Deputados que se abstiveram
     - **contraVotos**: Deputados que votaram contra
     - **favorVotos**: Deputados que votaram a favor

4. **Petições Relacionadas**:
   - **Peticoes**: Lista de petições relacionadas
     - **assunto**: Assunto da petição
     - **id**: ID da petição
     - **legislatura**: Legislatura
     - **numero**: Número da petição
     - **sessao**: Sessão

### Relações identificadas:
- Iniciativas ↔ Votações (uma iniciativa pode ter múltiplas votações)
- Iniciativas ↔ Deputados (através dos votos individuais)
- Iniciativas ↔ Comissões (através de ComissaoInOut)
- Iniciativas ↔ Petições (através de Peticoes)
- Votações ↔ Deputados (votos individuais: favor, contra, abstenção, ausência)

### Tipos de Iniciativas encontradas:
- Propostas de Lei (P)
- Projetos de Lei (PL)
- Projetos de Resolução (PR)
- Propostas de Resolução
- Apreciações Parlamentares
- Ratificações

### Campos importantes para análise:
- Padrões de votação por partido
- Taxa de aprovação por tipo de iniciativa
- Deputados mais ativos (presença/ausência)
- Disciplina partidária
- Evolução temporal das votações
- Relação entre petições e iniciativas legislativas

## 4. Descobertas Importantes

### Dados de Votações Integrados:
Os dados de votações estão integrados no ficheiro das Iniciativas, não existindo uma categoria separada de "Votações". Cada iniciativa contém:
- Histórico completo de votações
- Votos individuais de cada deputado
- Resultados detalhados
- Informações sobre unanimidade

### Estrutura Relacional Identificada:
1. **Deputados** (Informação Base) ↔ **Votos** (Iniciativas)
2. **Partidos** (Informação Base) ↔ **Deputados** ↔ **Votos**
3. **Comissões** (Informação Base) ↔ **Iniciativas**
4. **Agenda** ↔ **Grupos Parlamentares** ↔ **Deputados**
5. **Petições** ↔ **Iniciativas**

### Potencial para Análises Avançadas:
- Análise de disciplina partidária
- Padrões de votação por deputado
- Eficácia legislativa por partido
- Correlação entre audiências e votações
- Impacto das petições na atividade legislativa

