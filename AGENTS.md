# Instruções para agentes

Este ficheiro é para agentes de programação (e para pessoas) que trabalham neste repositório. O [CONTRIBUTING.md](CONTRIBUTING.md) tem o guia completo; aqui fica o essencial.

## O projeto

O Fiscaliza é um site estático com a atividade da Assembleia da República, construído a partir do [parlamento-aberto](https://github.com/rfsbraz/parlamento-aberto) no commit fixado em `deploy/data-pin`.

```
├── app/                    # Serviços e SQL que a exportação usa
│   ├── data/               # connection.py (DuckDB só de leitura), repository.py (todo o SQL), deputy_rows.py (linhas das páginas de deputados, em lote)
│   ├── services/           # os dicionários que cada endpoint devolve
│   └── routes/             # rotas finas; pending.py responde 503 para dados ainda não publicados
├── deploy/                 # pages.py (build e deploy), data-pin, _headers
├── fiscaliza_data/         # sync.py, export.py, seating.sql, views.sql
├── frontend/src/           # componentes React
└── tests/                  # pytest; tests/contracts fixa o que o frontend lê
```

## Comandos

```bash
pip install -r requirements.txt && pip install pytest ruff==0.17.1
python deploy/pages.py build --parlamento-aberto ../parlamento-aberto   # dados locais a partir do pin
ruff check . && ruff format --check .
pytest
cd frontend && npm ci && npm test && npm run build
```

## Regras

- Não corra `python deploy/pages.py deploy` sem `--dry-run`, nem nada que escreva no Cloudflare Pages, em releases do GitHub ou numa pasta de dados de produção.
- Rigor dos dados acima de tudo: use só dados que correspondem exatamente à fonte. Nunca invente dados nem ponha valores por omissão. Se um mart não existe, o endpoint responde 503 com o motivo.
- Todo o SQL fica em `app/data/repository.py`, `app/data/deputy_rows.py` ou `fiscaliza_data/*.sql`. Os serviços devolvem dicionários simples; as rotas ficam curtas.
- Cada endpoint que o frontend chama tem um contrato em `tests/contracts/endpoints/`. Altere o contrato junto com o componente.
- Os testes usam só dados sintéticos (`tests/site_data.py`), nunca dados pessoais reais.
- Texto visível no site em português de Portugal, com números no formato de Portugal (`frontend/src/utils/format.js`). Comentários e identificadores em inglês.
- Commits em inglês, em Conventional Commits na forma `type(scope): subject`. Issues e pull requests em português de Portugal, curtos, com o modelo de pull request preenchido.
- Nunca escreva segredos, tokens ou dados pessoais em código, fixtures, logs, issues ou commits.
