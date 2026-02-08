-- Comprehensive schema for Petições (Parliamentary Petitions) with every field and structure
-- Based on XML analysis: includes committee data, documents, interventions, reporters, etc.

-- Enhanced main petitions table with all core fields
CREATE TABLE IF NOT EXISTS peticoes_detalhadas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id INTEGER UNIQUE NOT NULL,         -- PetId from XML
    pet_nr INTEGER,                         -- PetNr
    pet_leg TEXT,                           -- PetLeg (IX, X, etc.)
    pet_sel INTEGER,                        -- PetSel (session)
    pet_assunto TEXT NOT NULL,              -- PetAssunto
    pet_situacao TEXT,                      -- PetSituacao (Concluída, etc.)
    pet_nr_assinaturas INTEGER,             -- PetNrAssinaturas
    pet_data_entrada DATE,                  -- PetDataEntrada
    pet_atividade_id INTEGER,               -- PetActividadeId
    pet_autor TEXT,                         -- PetAutor
    data_debate DATE,                       -- DataDebate
    legislatura_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (legislatura_id) REFERENCES legislaturas (id)
);

-- Publication data for petitions
CREATE TABLE IF NOT EXISTS peticoes_publicacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    peticao_id INTEGER NOT NULL,
    tipo TEXT,                              -- 'PublicacaoPeticao' or 'PublicacaoDebate'
    pub_nr INTEGER,                         -- <pubNr>43</pubNr>
    pub_tipo TEXT,                          -- <pubTipo>DAR II série B</pubTipo>
    pub_tp TEXT,                            -- <pubTp>B</pubTp>
    pub_leg TEXT,                           -- <pubLeg>IX</pubLeg>
    pub_sl INTEGER,                         -- <pubSL>1</pubSL>
    pub_dt DATE,                            -- <pubdt>2003-05-17</pubdt>
    pag TEXT,                               -- <pag><string>3357-3367</string></pag>
    id_pag INTEGER,                         -- <idPag>279888</idPag>
    url_diario TEXT,                        -- <URLDiario>https://debates...</URLDiario>
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (peticao_id) REFERENCES peticoes_detalhadas (id) ON DELETE CASCADE
);

-- Committee handling data for petitions (can have multiple committees across legislaturas)
CREATE TABLE IF NOT EXISTS peticoes_comissoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    peticao_id INTEGER NOT NULL,
    legislatura TEXT,                       -- <Legislatura>IX</Legislatura>
    numero INTEGER,                         -- <Numero>8</Numero>
    id_comissao INTEGER,                    -- <IdComissao>109</IdComissao>
    nome TEXT,                              -- <Nome>COMISSÃO DE TRABALHO E DOS ASSUNTOS SOCIAIS</Nome>
    admissibilidade TEXT,                   -- <Admissibilidade>Admitida</Admissibilidade>
    data_admissibilidade DATE,              -- <DataAdmissibilidade>2003-05-13</DataAdmissibilidade>
    data_envio_par DATE,                    -- <DataEnvioPAR>2003-07-04</DataEnvioPAR>
    data_arquivo DATE,                      -- <DataArquivo>2003-07-02</DataArquivo>
    situacao TEXT,                          -- <Situacao>Concluída</Situacao>
    data_reaberta DATE,                     -- <DataReaberta>2003-05-13</DataReaberta>
    data_baixa_comissao DATE,               -- <DataBaixaComissao>2005-05-17</DataBaixaComissao>
    transitada TEXT,                        -- <Transitada>Transitada da IX Legislatura.</Transitada>
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (peticao_id) REFERENCES peticoes_detalhadas (id) ON DELETE CASCADE
);

-- Reporters for petition committees
CREATE TABLE IF NOT EXISTS peticoes_relatores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comissao_peticao_id INTEGER NOT NULL,
    relator_id INTEGER,                     -- <id>321</id>
    nome TEXT,                              -- <nome>Francisco José Martins</nome>
    gp TEXT,                                -- <gp>PSD</gp>
    data_nomeacao DATE,                     -- <dataNomeacao>2004-01-01</dataNomeacao>
    data_cessacao DATE,                     -- <dataCessacao>2003-05-13</dataCessacao>
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (comissao_peticao_id) REFERENCES peticoes_comissoes (id) ON DELETE CASCADE
);

-- Final reports data
CREATE TABLE IF NOT EXISTS peticoes_relatorios_finais (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comissao_peticao_id INTEGER NOT NULL,
    data_relatorio DATE,                    -- <data>2003-06-27</data>
    votacao TEXT,                           -- <votacao /> - can contain voting details
    relatorio_final_id TEXT,                -- <string>21896</string>
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (comissao_peticao_id) REFERENCES peticoes_comissoes (id) ON DELETE CASCADE
);

-- Documents associated with petitions
CREATE TABLE IF NOT EXISTS peticoes_documentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    peticao_id INTEGER,                     -- Main petition documents
    comissao_peticao_id INTEGER,            -- Committee-specific documents
    tipo_documento_categoria TEXT,          -- 'Documentos', 'DocsRelatorioFinal'
    titulo_documento TEXT,                  -- <TituloDocumento>Texto</TituloDocumento>
    data_documento DATE,                    -- <DataDocumento>2003-03-06</DataDocumento>
    tipo_documento TEXT,                    -- <TipoDocumento>Texto</TipoDocumento>
    url TEXT,                               -- <URL>http://app.parlamento.pt/...</URL>
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (peticao_id) REFERENCES peticoes_detalhadas (id) ON DELETE CASCADE,
    FOREIGN KEY (comissao_peticao_id) REFERENCES peticoes_comissoes (id) ON DELETE CASCADE
);

-- Interventions/speeches in petition debates
CREATE TABLE IF NOT EXISTS peticoes_intervencoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    peticao_id INTEGER NOT NULL,
    data_reuniao_plenaria DATE,             -- <DataReuniaoPlenaria>2004-03-06</DataReuniaoPlenaria>
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (peticao_id) REFERENCES peticoes_detalhadas (id) ON DELETE CASCADE
);

-- Speakers in petition interventions
CREATE TABLE IF NOT EXISTS peticoes_oradores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intervencao_id INTEGER NOT NULL,
    fase_sessao TEXT,                       -- <FaseSessao>POD</FaseSessao>
    sumario TEXT,                           -- <Sumario>Revogação da Lei nº 4/99...</Sumario>
    convidados TEXT,                        -- <Convidados /> - invited participants
    membros_governo TEXT,                   -- <MembrosGoverno /> - government members
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (intervencao_id) REFERENCES peticoes_intervencoes (id) ON DELETE CASCADE
);

-- Publications for speakers
CREATE TABLE IF NOT EXISTS peticoes_oradores_publicacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    orador_id INTEGER NOT NULL,
    pub_nr INTEGER,                         -- <pubNr>60</pubNr>
    pub_tipo TEXT,                          -- <pubTipo>DAR I série</pubTipo>
    pub_tp TEXT,                            -- <pubTp>D</pubTp>
    pub_leg TEXT,                           -- <pubLeg>IX</pubLeg>
    pub_sl INTEGER,                         -- <pubSL>2</pubSL>
    pub_dt DATE,                            -- <pubdt>2004-03-06</pubdt>
    pag TEXT,                               -- <pag><string>3357-3358</string></pag>
    id_int INTEGER,                         -- <idInt>148746</idInt>
    url_diario TEXT,                        -- <URLDiario>https://debates...</URLDiario>
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (orador_id) REFERENCES peticoes_oradores (id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_peticoes_detalhadas_pet_id ON peticoes_detalhadas(pet_id);
CREATE INDEX IF NOT EXISTS idx_peticoes_detalhadas_leg ON peticoes_detalhadas(pet_leg);
CREATE INDEX IF NOT EXISTS idx_peticoes_detalhadas_situacao ON peticoes_detalhadas(pet_situacao);
CREATE INDEX IF NOT EXISTS idx_peticoes_comissoes_peticao ON peticoes_comissoes(peticao_id);
CREATE INDEX IF NOT EXISTS idx_peticoes_comissoes_id_comissao ON peticoes_comissoes(id_comissao);
CREATE INDEX IF NOT EXISTS idx_peticoes_relatores_comissao ON peticoes_relatores(comissao_peticao_id);
CREATE INDEX IF NOT EXISTS idx_peticoes_documentos_peticao ON peticoes_documentos(peticao_id);
CREATE INDEX IF NOT EXISTS idx_peticoes_intervencoes_peticao ON peticoes_intervencoes(peticao_id);
CREATE INDEX IF NOT EXISTS idx_peticoes_oradores_intervencao ON peticoes_oradores(intervencao_id);