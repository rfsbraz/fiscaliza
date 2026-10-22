# Fiscaliza

[![CI](https://github.com/rfsbraz/fiscaliza/actions/workflows/ci.yml/badge.svg)](https://github.com/rfsbraz/fiscaliza/actions/workflows/ci.yml)

Atividade da Assembleia da República a partir dos dados abertos: deputados, votações, presenças, iniciativas e agenda, em [fiscaliza.pt](https://fiscaliza.pt).

> O histórico deste repositório anterior à mudança para português, em outubro de 2026 (commits, issues e pull requests), está em inglês. A partir daí, a documentação, as issues, os pull requests e as mensagens de commit estão em português de Portugal.

## Como funciona

O Fiscaliza é um site estático. Nenhum servidor responde a pedidos em tempo real.

| Camada | Tecnologia |
|---|---|
| **Dados** | O [parlamento-aberto](https://github.com/rfsbraz/parlamento-aberto) no commit fixado em `deploy/data-pin`, carregado num ficheiro DuckDB local só de leitura |
| **Exportação** | `fiscaliza_data.export` escreve em ficheiros JSON todas as respostas de que o frontend precisa |
| **Frontend** | React 18 e Vite, que lê esses ficheiros em `/api` na mesma origem |
| **Alojamento** | Cloudflare Pages, com um deploy por cada push para `master` e uma pré-visualização por pull request ([docs/DEPLOY.md](docs/DEPLOY.md)) |

```
├── app/                    # Serviços e consultas SQL (data/repository.py) que a exportação usa; também correm como API Flask local
├── deploy/                 # pages.py (build e deploy), data-pin (o commit dos dados), _headers
├── docs/                   # DEPLOY.md, STATIC_EXPORT.md
├── fiscaliza_data/         # Sincronização, regra dos lugares, vistas e exportação estática
├── frontend/src/           # Componentes React
└── tests/                  # pytest, incluindo os contratos dos endpoints
```

A sincronização cria `fiscaliza-<tag>.duckdb` a partir de uma release de dados do parlamento-aberto, verifica-o e aponta `current.duckdb` para ele. A exportação lê esse ficheiro e escreve os JSON em `frontend/public/api`. O build do Vite copia-os para `dist/api`. Os detalhes estão em [docs/STATIC_EXPORT.md](docs/STATIC_EXPORT.md).

## Arranque rápido

É preciso Python 3.12, Node.js 20 ou mais recente, o [uv](https://docs.astral.sh/uv/) e o git.

```bash
git clone https://github.com/rfsbraz/fiscaliza.git
cd fiscaliza
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# O parlamento-aberto ainda não publica releases: os dados constroem-se no commit fixado.
git clone --depth 1 --no-checkout https://github.com/rfsbraz/parlamento-aberto.git ../parlamento-aberto
python deploy/pages.py build --parlamento-aberto ../parlamento-aberto

cd frontend && npm ci && npm run dev
```

O `build` demora cerca de dois minutos e escreve `data/current.duckdb` e `frontend/public/api` (ambos ignorados pelo git). O servidor do Vite serve o site em <http://localhost:5173> com os dados em `/api`.

O [CONTRIBUTING.md](CONTRIBUTING.md) tem o guia completo.

## Sincronização dos dados

```bash
python -m fiscaliza_data.sync [--tag TAG] [--from CAMINHO] [--data-dir PASTA]
```

- Sem `--from`, lê a release mais recente do parlamento-aberto no GitHub (ou `--tag`), com um pedido à API sem autenticação. Enquanto o parlamento-aberto não publicar releases, o comando para e indica o `deploy/pages.py build`.
- `--from CAMINHO` lê um resultado local de `release build`: a pasta, o seu `manifest.json`, ou um `.tar.gz`, `.tgz` ou `.zip` da pasta. `--from-dir` continua a funcionar como nome antigo.
- `--data-dir` usa por omissão `$FISCALIZA_DATA_DIR` e depois `data`.
- `python -m fiscaliza_data sync` é o mesmo comando.

Todas as fontes passam pelas mesmas verificações: o SHA-256 de cada ficheiro Parquet contra o manifest, a versão principal do esquema, 230 deputados em funções na legislatura atual, e nenhuma tabela mais de 5% menor do que a que está em uso. Uma falha termina com código diferente de zero e deixa em uso o ficheiro anterior. Ficam guardados os dois últimos ficheiros.

## Ainda não disponível

As presenças (`/api/deputados/<id>/attendance`) e a agenda de hoje e da semana (`/api/agenda/hoje`, `/api/agenda/semana`) esperam pelos marts respetivos do parlamento-aberto. Respondem 503 com o motivo, e o frontend mostra o aviso "indisponível".

## Contribuir

O [CONTRIBUTING.md](CONTRIBUTING.md) explica como preparar o ambiente, as verificações antes de um pull request e as convenções de commits.

## Licença

Código: [AGPL-3.0-or-later](LICENSE). Pode usar, alterar e distribuir este software. Se correr uma versão alterada num servidor acessível pela rede, tem de disponibilizar o código-fonte a quem a usa. Copyright © Rodrigo Braz e contribuidores.

O nome Fiscaliza e o logótipo não estão abrangidos pela AGPL. Quem publicar um fork tem de usar outro nome e outro logótipo.

Dados: vêm dos dados abertos da Assembleia da República, reutilizados nos termos da AR, através do parlamento-aberto, cujas tabelas derivadas estão sob CC BY 4.0. Os termos completos estão no [LICENSE-DATA](https://github.com/rfsbraz/parlamento-aberto/blob/main/LICENSE-DATA) do parlamento-aberto. O rodapé do site tem a atribuição.
