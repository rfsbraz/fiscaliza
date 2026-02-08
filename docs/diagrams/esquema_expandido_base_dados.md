# Esquema Expandido da Base de Dados - Parlamento Português

**Autor:** Manus AI  
**Data:** 25 de julho de 2025  
**Versão:** 2.0 - Esquema Relacional Completo

## Introdução

Com base na análise detalhada dos schemas XML disponibilizados pelo Parlamento Português, este documento apresenta um esquema expandido da base de dados que permite implementar funcionalidades avançadas de navegação relacional e análise de dados parlamentares. O esquema original, que incluía apenas informação base sobre deputados, partidos e círculos eleitorais, é agora expandido para incluir atividades parlamentares, intervenções, agenda diária, votações e outras entidades fundamentais para uma análise completa da atividade parlamentar.

A expansão do esquema foi motivada pela necessidade de implementar funcionalidades específicas solicitadas pelo utilizador, nomeadamente a navegação hierárquica "Partido → Deputados → Deputado → Atividades", a agenda diária com ordens de trabalho e resultados de votações, e a análise de padrões de participação e assiduidade dos deputados. Esta abordagem relacional permite não apenas armazenar os dados de forma estruturada, mas também estabelecer conexões significativas entre as diferentes entidades do sistema parlamentar português.

## Análise dos Dados Disponíveis

### Categorias de Dados Identificadas

A análise dos dados abertos do Parlamento Português revelou a existência de múltiplas categorias de dados estruturados em formato XML, cada uma com características específicas e potencial de relacionamento com outras entidades do sistema. As principais categorias analisadas incluem:

**Informação Base** - Esta categoria constitui o fundamento do sistema, contendo dados sobre deputados, partidos políticos, círculos eleitorais e legislaturas. A análise revelou 249 registros de deputados na XVII Legislatura, distribuídos por 10 partidos e 22 círculos eleitorais. Cada registro de deputado inclui informação pessoal (nome, profissão), afiliação partidária e representação geográfica.

**Intervenções Parlamentares** - O ficheiro XML das intervenções contém 188 registros detalhados de participações dos deputados em sessões plenárias. Cada intervenção inclui identificadores únicos, data da reunião plenária, tipo de intervenção (leitura, interpelação à mesa, debate), sumário do conteúdo, deputado interveniente com afiliação partidária, e ligações para conteúdo audiovisual. Esta categoria é fundamental para analisar a participação ativa dos deputados no processo legislativo.

**Agenda Parlamentar** - Com 29 registros analisados, a agenda parlamentar fornece informação sobre atividades programadas, incluindo reuniões plenárias, sessões de comissões, audiências e outros eventos. Cada entrada contém datas, horários, títulos, descrições detalhadas e informação sobre a legislatura correspondente. Esta categoria é essencial para implementar a funcionalidade de agenda diária solicitada.

**Iniciativas Legislativas** - O conjunto de dados das iniciativas inclui 357 registros de propostas de lei, projetos de resolução e outras iniciativas legislativas. Cada iniciativa contém número identificador, tipo, título, autores (incluindo afiliação partidária), texto integral e histórico de eventos relacionados. Esta categoria permite rastrear a atividade legislativa por deputado e partido.

### Estruturas de Dados e Relações Identificadas

A análise detalhada dos schemas XML revelou padrões consistentes de identificação e relacionamento entre entidades. Os campos de identificação mais relevantes incluem identificadores únicos de deputados (idCadastro), códigos de grupos parlamentares (GP), identificadores de atividades (ActividadeId) e referências temporais (Legislatura, Sessao).

As relações mais significativas identificadas estabelecem conexões entre deputados e suas atividades parlamentares através de múltiplos pontos de ligação. Cada intervenção está associada a um deputado específico através do campo idCadastro, permitindo rastrear toda a atividade discursiva de um parlamentar. Simultaneamente, as intervenções estão ligadas a atividades específicas através do ActividadeId, criando uma hierarquia clara de eventos parlamentares.

A estrutura temporal dos dados é consistente em todas as categorias, utilizando a combinação Legislatura/Sessao para contextualizar cronologicamente todas as atividades. Esta estrutura permite análises longitudinais e comparações entre diferentes períodos legislativos.

## Esquema da Base de Dados Expandido

### Tabelas Principais

#### 1. Tabela `legislaturas`
Esta tabela mantém a informação sobre os diferentes períodos legislativos, servindo como referência temporal para todas as outras entidades do sistema.

```sql
CREATE TABLE legislaturas (
    id INTEGER PRIMARY KEY,
    numero INTEGER NOT NULL UNIQUE,
    designacao TEXT NOT NULL,
    data_inicio DATE,
    data_fim DATE,
    ativa BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2. Tabela `partidos`
Expandida para incluir informação adicional sobre os grupos parlamentares e sua evolução ao longo do tempo.

```sql
CREATE TABLE partidos (
    id INTEGER PRIMARY KEY,
    sigla TEXT NOT NULL,
    nome TEXT NOT NULL,
    designacao_completa TEXT,
    cor_hex TEXT,
    ativo BOOLEAN DEFAULT TRUE,
    data_fundacao DATE,
    ideologia TEXT,
    lider_parlamentar TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(sigla)
);
```

#### 3. Tabela `circulos_eleitorais`
Mantém a estrutura original com adições para melhor caracterização geográfica.

```sql
CREATE TABLE circulos_eleitorais (
    id INTEGER PRIMARY KEY,
    designacao TEXT NOT NULL UNIQUE,
    codigo TEXT,
    regiao TEXT,
    distrito TEXT,
    num_deputados INTEGER DEFAULT 0,
    populacao INTEGER,
    area_km2 REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 4. Tabela `deputados`
Expandida significativamente para incluir informação biográfica e de contacto.

```sql
CREATE TABLE deputados (
    id INTEGER PRIMARY KEY,
    id_cadastro INTEGER NOT NULL UNIQUE,
    nome TEXT NOT NULL,
    nome_completo TEXT,
    profissao TEXT,
    data_nascimento DATE,
    naturalidade TEXT,
    habilitacoes_academicas TEXT,
    biografia TEXT,
    foto_url TEXT,
    email TEXT,
    telefone TEXT,
    gabinete TEXT,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 5. Tabela `mandatos`
Relação entre deputados, partidos e círculos eleitorais por legislatura.

```sql
CREATE TABLE mandatos (
    id INTEGER PRIMARY KEY,
    deputado_id INTEGER NOT NULL,
    partido_id INTEGER NOT NULL,
    circulo_id INTEGER NOT NULL,
    legislatura_id INTEGER NOT NULL,
    data_inicio DATE NOT NULL,
    data_fim DATE,
    ativo BOOLEAN DEFAULT TRUE,
    posicao_lista INTEGER,
    votos_obtidos INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (deputado_id) REFERENCES deputados (id),
    FOREIGN KEY (partido_id) REFERENCES partidos (id),
    FOREIGN KEY (circulo_id) REFERENCES circulos_eleitorais (id),
    FOREIGN KEY (legislatura_id) REFERENCES legislaturas (id),
    UNIQUE(deputado_id, legislatura_id)
);
```

### Tabelas de Atividade Parlamentar

#### 6. Tabela `sessoes_plenarias`
Regista as sessões plenárias da Assembleia da República.

```sql
CREATE TABLE sessoes_plenarias (
    id INTEGER PRIMARY KEY,
    legislatura_id INTEGER NOT NULL,
    numero_sessao INTEGER NOT NULL,
    data_sessao DATE NOT NULL,
    hora_inicio TIME,
    hora_fim TIME,
    tipo_sessao TEXT, -- 'ordinaria', 'extraordinaria', 'solene'
    estado TEXT DEFAULT 'agendada', -- 'agendada', 'em_curso', 'concluida', 'cancelada'
    ordem_trabalhos TEXT,
    resumo TEXT,
    presidente_sessao TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (legislatura_id) REFERENCES legislaturas (id),
    UNIQUE(legislatura_id, numero_sessao, data_sessao)
);
```

#### 7. Tabela `atividades_parlamentares`
Tabela central para todas as atividades que ocorrem no parlamento.

```sql
CREATE TABLE atividades_parlamentares (
    id INTEGER PRIMARY KEY,
    id_externo INTEGER, -- ID do sistema externo
    legislatura_id INTEGER NOT NULL,
    sessao_plenaria_id INTEGER,
    tipo_atividade TEXT NOT NULL, -- 'debate', 'votacao', 'audiencia', 'interpelacao'
    titulo TEXT NOT NULL,
    descricao TEXT,
    data_atividade DATE NOT NULL,
    hora_inicio TIME,
    hora_fim TIME,
    fase_sessao TEXT, -- 'POD', 'OD', etc.
    estado TEXT DEFAULT 'agendada',
    resultado TEXT,
    observacoes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (legislatura_id) REFERENCES legislaturas (id),
    FOREIGN KEY (sessao_plenaria_id) REFERENCES sessoes_plenarias (id)
);
```

#### 8. Tabela `intervencoes`
Regista todas as intervenções dos deputados em sessões plenárias.

```sql
CREATE TABLE intervencoes (
    id INTEGER PRIMARY KEY,
    id_externo INTEGER UNIQUE, -- ID do XML original
    deputado_id INTEGER NOT NULL,
    atividade_id INTEGER,
    sessao_plenaria_id INTEGER,
    legislatura_id INTEGER NOT NULL,
    tipo_intervencao TEXT NOT NULL, -- 'Leitura', 'Interpelação à mesa', 'Debate'
    data_intervencao DATE NOT NULL,
    qualidade TEXT, -- 'Deputado', 'Sec. Mesa', etc.
    sumario TEXT,
    resumo TEXT,
    fase_sessao TEXT,
    duracao_segundos INTEGER,
    url_video TEXT,
    url_diario TEXT,
    pagina_diario TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (deputado_id) REFERENCES deputados (id),
    FOREIGN KEY (atividade_id) REFERENCES atividades_parlamentares (id),
    FOREIGN KEY (sessao_plenaria_id) REFERENCES sessoes_plenarias (id),
    FOREIGN KEY (legislatura_id) REFERENCES legislaturas (id)
);
```

#### 9. Tabela `iniciativas_legislativas`
Armazena todas as propostas de lei, projetos de resolução e outras iniciativas.

```sql
CREATE TABLE iniciativas_legislativas (
    id INTEGER PRIMARY KEY,
    id_externo INTEGER UNIQUE, -- IniId do XML
    numero INTEGER NOT NULL,
    tipo TEXT NOT NULL, -- 'P' (Proposta de Lei), 'PJR' (Projeto de Resolução), etc.
    tipo_descricao TEXT,
    legislatura_id INTEGER NOT NULL,
    sessao INTEGER,
    titulo TEXT NOT NULL,
    data_apresentacao DATE,
    texto_substituto BOOLEAN DEFAULT FALSE,
    url_texto TEXT,
    estado TEXT,
    resultado TEXT,
    observacoes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (legislatura_id) REFERENCES legislaturas (id),
    UNIQUE(numero, tipo, legislatura_id)
);
```

#### 10. Tabela `autores_iniciativas`
Relação many-to-many entre iniciativas e seus autores (deputados/partidos).

```sql
CREATE TABLE autores_iniciativas (
    id INTEGER PRIMARY KEY,
    iniciativa_id INTEGER NOT NULL,
    deputado_id INTEGER,
    partido_id INTEGER,
    tipo_autor TEXT, -- 'principal', 'subscritor', 'apresentante'
    ordem INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (iniciativa_id) REFERENCES iniciativas_legislativas (id),
    FOREIGN KEY (deputado_id) REFERENCES deputados (id),
    FOREIGN KEY (partido_id) REFERENCES partidos (id),
    CHECK ((deputado_id IS NOT NULL) OR (partido_id IS NOT NULL))
);
```

### Tabelas de Agenda e Eventos

#### 11. Tabela `agenda_parlamentar`
Agenda diária das atividades parlamentares.

```sql
CREATE TABLE agenda_parlamentar (
    id INTEGER PRIMARY KEY,
    id_externo INTEGER UNIQUE, -- ID do XML original
    legislatura_id INTEGER NOT NULL,
    secao_id INTEGER,
    secao_nome TEXT,
    tema_id INTEGER,
    tema_nome TEXT,
    grupo_parlamentar TEXT,
    data_evento DATE NOT NULL,
    hora_inicio TIME,
    hora_fim TIME,
    evento_dia_inteiro BOOLEAN DEFAULT FALSE,
    titulo TEXT NOT NULL,
    subtitulo TEXT,
    descricao TEXT,
    local_evento TEXT,
    link_externo TEXT,
    pos_plenario BOOLEAN DEFAULT FALSE,
    estado TEXT DEFAULT 'agendado', -- 'agendado', 'em_curso', 'concluido', 'cancelado'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (legislatura_id) REFERENCES legislaturas (id)
);
```

#### 12. Tabela `eventos_iniciativas`
Histórico de eventos relacionados com iniciativas legislativas.

```sql
CREATE TABLE eventos_iniciativas (
    id INTEGER PRIMARY KEY,
    iniciativa_id INTEGER NOT NULL,
    data_evento DATE NOT NULL,
    tipo_evento TEXT NOT NULL,
    descricao_evento TEXT,
    fase TEXT,
    resultado TEXT,
    observacoes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (iniciativa_id) REFERENCES iniciativas_legislativas (id)
);
```

### Tabelas de Votações (Preparação para Futura Implementação)

#### 13. Tabela `votacoes`
Regista as votações realizadas no parlamento.

```sql
CREATE TABLE votacoes (
    id INTEGER PRIMARY KEY,
    iniciativa_id INTEGER,
    atividade_id INTEGER,
    sessao_plenaria_id INTEGER NOT NULL,
    legislatura_id INTEGER NOT NULL,
    numero_votacao INTEGER,
    data_votacao DATE NOT NULL,
    hora_votacao TIME,
    tipo_votacao TEXT, -- 'nominal', 'secreta', 'por_divisao'
    objeto_votacao TEXT NOT NULL,
    resultado TEXT, -- 'aprovada', 'rejeitada', 'retirada'
    votos_favor INTEGER DEFAULT 0,
    votos_contra INTEGER DEFAULT 0,
    abstencoes INTEGER DEFAULT 0,
    ausencias INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (iniciativa_id) REFERENCES iniciativas_legislativas (id),
    FOREIGN KEY (atividade_id) REFERENCES atividades_parlamentares (id),
    FOREIGN KEY (sessao_plenaria_id) REFERENCES sessoes_plenarias (id),
    FOREIGN KEY (legislatura_id) REFERENCES legislaturas (id)
);
```

#### 14. Tabela `votos_individuais`
Regista o voto individual de cada deputado em cada votação.

```sql
CREATE TABLE votos_individuais (
    id INTEGER PRIMARY KEY,
    votacao_id INTEGER NOT NULL,
    deputado_id INTEGER NOT NULL,
    voto TEXT NOT NULL, -- 'favor', 'contra', 'abstencao', 'ausente'
    justificacao TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (votacao_id) REFERENCES votacoes (id),
    FOREIGN KEY (deputado_id) REFERENCES deputados (id),
    UNIQUE(votacao_id, deputado_id)
);
```

### Tabelas de Análise e Métricas

#### 15. Tabela `metricas_deputados`
Métricas calculadas sobre a atividade dos deputados.

```sql
CREATE TABLE metricas_deputados (
    id INTEGER PRIMARY KEY,
    deputado_id INTEGER NOT NULL,
    legislatura_id INTEGER NOT NULL,
    periodo_inicio DATE NOT NULL,
    periodo_fim DATE NOT NULL,
    total_intervencoes INTEGER DEFAULT 0,
    total_iniciativas INTEGER DEFAULT 0,
    total_votacoes_participadas INTEGER DEFAULT 0,
    taxa_assiduidade REAL DEFAULT 0.0,
    tempo_total_intervencoes INTEGER DEFAULT 0, -- em segundos
    ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (deputado_id) REFERENCES deputados (id),
    FOREIGN KEY (legislatura_id) REFERENCES legislaturas (id),
    UNIQUE(deputado_id, legislatura_id, periodo_inicio, periodo_fim)
);
```

## Índices e Otimizações

Para garantir performance adequada nas consultas mais frequentes, são criados índices específicos nas tabelas principais:

```sql
-- Índices para consultas por deputado
CREATE INDEX idx_mandatos_deputado_legislatura ON mandatos(deputado_id, legislatura_id);
CREATE INDEX idx_intervencoes_deputado_data ON intervencoes(deputado_id, data_intervencao);
CREATE INDEX idx_votos_individuais_deputado ON votos_individuais(deputado_id, votacao_id);

-- Índices para consultas por partido
CREATE INDEX idx_mandatos_partido_legislatura ON mandatos(partido_id, legislatura_id);
CREATE INDEX idx_autores_iniciativas_partido ON autores_iniciativas(partido_id, iniciativa_id);

-- Índices temporais
CREATE INDEX idx_agenda_data ON agenda_parlamentar(data_evento);
CREATE INDEX idx_atividades_data ON atividades_parlamentares(data_atividade);
CREATE INDEX idx_votacoes_data ON votacoes(data_votacao);

-- Índices para relações
CREATE INDEX idx_intervencoes_atividade ON intervencoes(atividade_id);
CREATE INDEX idx_eventos_iniciativa ON eventos_iniciativas(iniciativa_id, data_evento);
```

## Relações e Integridade Referencial

O esquema expandido estabelece uma rede complexa de relações que permite navegação hierárquica e análise multidimensional dos dados parlamentares. As relações principais incluem:

**Hierarquia Temporal**: Legislaturas → Sessões Plenárias → Atividades → Intervenções/Votações, permitindo contextualização cronológica de todas as atividades.

**Hierarquia Política**: Partidos → Deputados (via Mandatos) → Atividades Individuais, facilitando análise por afiliação partidária.

**Hierarquia Geográfica**: Círculos Eleitorais → Deputados (via Mandatos) → Representação Regional, permitindo análise territorial.

**Relações de Atividade**: Iniciativas → Eventos → Votações → Votos Individuais, criando um fluxo completo do processo legislativo.

As constraints de integridade referencial garantem consistência dos dados e previnem inconsistências que poderiam comprometer análises futuras.

## Considerações de Implementação

A implementação deste esquema expandido requer consideração cuidadosa da migração de dados existentes e da integração com os sistemas de importação. A estratégia recomendada inclui:

**Migração Incremental**: Implementação faseada começando pelas tabelas de atividade parlamentar mais críticas (intervenções e agenda), seguida pelas tabelas de votações e métricas.

**Compatibilidade Retroativa**: Manutenção da estrutura original das tabelas principais (deputados, partidos, círculos_eleitorais, mandatos) para garantir funcionamento contínuo da aplicação existente.

**Validação de Dados**: Implementação de procedures de validação para garantir integridade dos dados importados, especialmente nas relações entre entidades.

**Performance**: Monitorização contínua da performance das consultas e ajuste dos índices conforme necessário, considerando os padrões de uso da aplicação.

Este esquema expandido fornece a base técnica necessária para implementar todas as funcionalidades solicitadas, desde a navegação hierárquica até à análise detalhada de padrões de atividade parlamentar, estabelecendo uma fundação sólida para futuras expansões do sistema.

