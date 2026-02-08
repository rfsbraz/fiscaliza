-- Comprehensive schema for Iniciativas (Legislative Initiatives) with every field and structure
-- Based on XML analysis: includes events, voting, committees, authors, publication data

-- Enhanced main iniciativas table with all core fields
CREATE TABLE IF NOT EXISTS iniciativas_detalhadas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ini_id INTEGER UNIQUE NOT NULL,           -- IniId from XML
    ini_nr INTEGER,                           -- IniNr
    ini_tipo TEXT,                           -- IniTipo (P, F, R, etc.)
    ini_desc_tipo TEXT,                      -- IniDescTipo (Proposta de Lei, etc.)
    ini_leg TEXT,                           -- IniLeg (XVII, XVI, etc.)
    ini_sel INTEGER,                        -- IniSel (session)
    data_inicio_leg DATE,                   -- DataInicioleg
    data_fim_leg DATE,                      -- DataFimleg
    ini_titulo TEXT NOT NULL,               -- IniTitulo
    ini_texto_subst TEXT,                   -- IniTextoSubst (NAO/SIM)
    ini_link_texto TEXT,                    -- IniLinkTexto
    legislatura_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (legislatura_id) REFERENCES legislaturas (id)
);

-- Authors - Other entities (Government, Deputados, etc.)
CREATE TABLE IF NOT EXISTS iniciativas_autores_outros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    iniciativa_id INTEGER NOT NULL,
    sigla TEXT,                             -- <sigla>V</sigla>
    nome TEXT,                              -- <nome>Governo</nome>
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (iniciativa_id) REFERENCES iniciativas_detalhadas (id) ON DELETE CASCADE
);

-- Authors - Deputies 
CREATE TABLE IF NOT EXISTS iniciativas_autores_deputados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    iniciativa_id INTEGER NOT NULL,
    id_cadastro INTEGER,                    -- <idCadastro>196</idCadastro>
    nome TEXT,                              -- <nome>Luís Filipe Madeira</nome>
    gp TEXT,                                -- <GP>PS</GP>
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (iniciativa_id) REFERENCES iniciativas_detalhadas (id) ON DELETE CASCADE
);

-- Authors - Parliamentary Groups
CREATE TABLE IF NOT EXISTS iniciativas_autores_grupos_parlamentares (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    iniciativa_id INTEGER NOT NULL,
    gp TEXT,                                -- <GP>PS</GP>
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (iniciativa_id) REFERENCES iniciativas_detalhadas (id) ON DELETE CASCADE
);

-- Events timeline for each initiative
CREATE TABLE IF NOT EXISTS iniciativas_eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    iniciativa_id INTEGER NOT NULL,
    oev_id INTEGER,                         -- <OevId>235377</OevId>
    data_fase DATE,                         -- <DataFase>1982-12-16</DataFase>
    fase TEXT,                              -- <Fase>Anúncio</Fase>
    evt_id INTEGER,                         -- <EvtId>3</EvtId>
    codigo_fase INTEGER,                    -- <CodigoFase>21</CodigoFase>
    obs_fase TEXT,                          -- <ObsFase>Suspensão do Decreto-Lei</ObsFase>
    act_id INTEGER,                         -- <ActId>15748</ActId>
    oev_text_id INTEGER,                    -- <OevTextId>13367</OevTextId>
    textos_aprovados TEXT,                  -- <TextosAprovados>13367</TextosAprovados>
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (iniciativa_id) REFERENCES iniciativas_detalhadas (id) ON DELETE CASCADE
);

-- Publication data for events
CREATE TABLE IF NOT EXISTS iniciativas_eventos_publicacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evento_id INTEGER NOT NULL,
    pub_nr INTEGER,                         -- <pubNr>29</pubNr>
    pub_tipo TEXT,                          -- <pubTipo>DAR II série</pubTipo>
    pub_tp TEXT,                            -- <pubTp>K</pubTp>
    pub_leg TEXT,                           -- <pubLeg>II</pubLeg>
    pub_sl INTEGER,                         -- <pubSL>3</pubSL>
    pub_dt DATE,                            -- <pubdt>1982-12-17</pubdt>
    pag TEXT,                               -- <pag><string>425-427</string></pag>
    id_pag INTEGER,                         -- <idPag>342569</idPag>
    url_diario TEXT,                        -- <URLDiario>https://debates...</URLDiario>
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (evento_id) REFERENCES iniciativas_eventos (id) ON DELETE CASCADE
);

-- Voting data for events
CREATE TABLE IF NOT EXISTS iniciativas_eventos_votacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evento_id INTEGER NOT NULL,
    id_votacao INTEGER,                     -- <id>47328</id>
    resultado TEXT,                         -- <resultado>Aprovado</resultado>
    reuniao INTEGER,                        -- <reuniao>28</reuniao>
    tipo_reuniao TEXT,                      -- <tipoReuniao>RP</tipoReuniao>
    detalhe TEXT,                           -- Detailed voting breakdown
    unanime TEXT,                           -- <unanime>unanime</unanime>
    data_votacao DATE,                      -- <data>1982-12-21</data>
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (evento_id) REFERENCES iniciativas_eventos (id) ON DELETE CASCADE
);

-- Absences in voting
CREATE TABLE IF NOT EXISTS iniciativas_votacoes_ausencias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    votacao_id INTEGER NOT NULL,
    grupo_parlamentar TEXT,                 -- <string>MDP/CDE</string>
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (votacao_id) REFERENCES iniciativas_eventos_votacoes (id) ON DELETE CASCADE
);

-- Resource groups for events (RecursoGP)
CREATE TABLE IF NOT EXISTS iniciativas_eventos_recursos_gp (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evento_id INTEGER NOT NULL,
    grupo_parlamentar TEXT,                 -- <string>PS</string>
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (evento_id) REFERENCES iniciativas_eventos (id) ON DELETE CASCADE
);

-- Committee data for events
CREATE TABLE IF NOT EXISTS iniciativas_eventos_comissoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evento_id INTEGER NOT NULL,
    acc_id INTEGER,                         -- <AccId>16294</AccId>
    numero INTEGER,                         -- <Numero>834</Numero>
    id_comissao INTEGER,                    -- <IdComissao>834</IdComissao>
    nome TEXT,                              -- <Nome>COMISSÃO DE ECONOMIA, FINANÇAS E PLANO</Nome>
    competente TEXT,                        -- <Competente>N</Competente>
    data_distribuicao DATE,                 -- <DataDistribuicao>1982-12-17</DataDistribuicao>
    data_entrada DATE,                      -- <DataEntrada>1983-02-01</DataEntrada>
    data_agendamento_plenario DATETIME,     -- <DataAgendamentoPlenario>0001-01-01T00:00:00</DataAgendamentoPlenario>
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (evento_id) REFERENCES iniciativas_eventos (id) ON DELETE CASCADE
);

-- Committee publications
CREATE TABLE IF NOT EXISTS iniciativas_comissoes_publicacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comissao_id INTEGER NOT NULL,
    tipo TEXT,                              -- 'Publicacao' or 'PublicacaoRelatorio'
    pub_nr INTEGER,
    pub_tipo TEXT,
    pub_tp TEXT,
    pub_leg TEXT,
    pub_sl INTEGER,
    pub_dt DATE,
    pag TEXT,
    id_pag INTEGER,
    url_diario TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (comissao_id) REFERENCES iniciativas_eventos_comissoes (id) ON DELETE CASCADE
);

-- Joint initiatives discussions
CREATE TABLE IF NOT EXISTS iniciativas_conjuntas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evento_id INTEGER NOT NULL,
    nr INTEGER,                             -- <nr>164</nr>
    tipo TEXT,                              -- <tipo>F</tipo>
    desc_tipo TEXT,                         -- <descTipo>Ratificação</descTipo>
    leg TEXT,                               -- <leg>II</leg>
    sel INTEGER,                            -- <sel>2</sel>
    titulo TEXT,                            -- <titulo>Decreto-lei nº 224/82...</titulo>
    ini_id INTEGER,                         -- <id>31103</id>
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (evento_id) REFERENCES iniciativas_eventos (id) ON DELETE CASCADE
);

-- Interventions/debates
CREATE TABLE IF NOT EXISTS iniciativas_intervencoes_debates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evento_id INTEGER NOT NULL,
    data_reuniao_plenaria DATE,             -- <dataReuniaoPlenaria>1982-10-19</dataReuniaoPlenaria>
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (evento_id) REFERENCES iniciativas_eventos (id) ON DELETE CASCADE
);

-- Amendment proposals
CREATE TABLE IF NOT EXISTS iniciativas_propostas_alteracao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    iniciativa_id INTEGER NOT NULL,
    proposta_id INTEGER,                    -- <id>31205</id>
    tipo TEXT,                              -- <tipo>Proposta de Alteração</tipo>
    autor TEXT,                             -- <autor />
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (iniciativa_id) REFERENCES iniciativas_detalhadas (id) ON DELETE CASCADE
);

-- Publications for amendment proposals
CREATE TABLE IF NOT EXISTS iniciativas_propostas_alteracao_publicacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proposta_id INTEGER NOT NULL,
    pub_nr INTEGER,
    pub_tipo TEXT,
    pub_tp TEXT,
    pub_leg TEXT,
    pub_sl INTEGER,
    pub_dt DATE,
    pag TEXT,
    id_pag INTEGER,
    url_diario TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (proposta_id) REFERENCES iniciativas_propostas_alteracao (id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_iniciativas_detalhadas_ini_id ON iniciativas_detalhadas(ini_id);
CREATE INDEX IF NOT EXISTS idx_iniciativas_detalhadas_tipo ON iniciativas_detalhadas(ini_tipo);
CREATE INDEX IF NOT EXISTS idx_iniciativas_detalhadas_leg ON iniciativas_detalhadas(ini_leg);
CREATE INDEX IF NOT EXISTS idx_iniciativas_eventos_iniciativa ON iniciativas_eventos(iniciativa_id);
CREATE INDEX IF NOT EXISTS idx_iniciativas_eventos_fase ON iniciativas_eventos(fase);
CREATE INDEX IF NOT EXISTS idx_iniciativas_votacoes_resultado ON iniciativas_eventos_votacoes(resultado);
CREATE INDEX IF NOT EXISTS idx_iniciativas_autores_deputados_iniciativa ON iniciativas_autores_deputados(iniciativa_id);
CREATE INDEX IF NOT EXISTS idx_iniciativas_autores_deputados_cadastro ON iniciativas_autores_deputados(id_cadastro);