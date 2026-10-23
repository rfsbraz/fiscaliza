# Como contribuir

Obrigado pelo interesse no Fiscaliza. Este site mostra a atividade da Assembleia da República a partir dos dados abertos, através do [parlamento-aberto](https://github.com/rfsbraz/parlamento-aberto). Este guia explica como preparar o ambiente, que verificações correr antes de abrir um pull request e que convenções seguir.

## Antes de começar

- Um número errado pode vir dos dados ou do cálculo. Se o dado está errado na origem, reporte-o no parlamento-aberto com o formulário [Correção de dados](https://github.com/rfsbraz/parlamento-aberto/issues/new?template=correcao-de-dados.yml). Se o dado está certo e o site o mostra mal, abra uma issue aqui.
- Para reportar uma vulnerabilidade, siga o [SECURITY.md](SECURITY.md) e não abra uma issue pública.
- Para uma alteração maior (uma página nova, uma métrica nova), abra primeiro uma issue a descrever a ideia.

## Preparar o ambiente

É preciso Python 3.12, Node.js 20 ou mais recente, o [uv](https://docs.astral.sh/uv/) (para construir os dados do parlamento-aberto) e o git. Não é preciso nenhum servidor de base de dados.

```bash
git clone https://github.com/rfsbraz/fiscaliza.git
cd fiscaliza
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install pytest ruff==0.17.1
cd frontend && npm ci && cd ..
```

### Dados

O site lê um ficheiro DuckDB só de leitura, construído a partir do commit do parlamento-aberto fixado em `deploy/data-pin`. Quando o pin tem uma tag de release (`tag=`), `python deploy/pages.py build` descarrega essa release do GitHub, sem clone nem `uv`. Sem tag, a release constrói-se localmente:

```bash
git clone --depth 1 --no-checkout https://github.com/rfsbraz/parlamento-aberto.git ../parlamento-aberto
python deploy/pages.py build --parlamento-aberto ../parlamento-aberto
```

O comando vai buscar o commit fixado ao clone (mesmo que o `main` já tenha avançado), constrói a release com `uv`, sincroniza-a para `data/` e exporta os JSON para `frontend/public/api`. Demora cerca de dois minutos. `--data-dir` muda a pasta dos dados e `--dry-run` mostra os passos sem correr nada.

Se já tiver um resultado de `release build` feito a partir do commit fixado, use `--release PASTA` em vez de `--parlamento-aberto`.

### Correr o site

```bash
cd frontend && npm run dev
```

O Vite serve o site em <http://localhost:5173> e os ficheiros de `frontend/public/api` em `/api`, como o alojamento estático. Depois de mudar um serviço ou uma vista, volte a correr `python -m fiscaliza_data.export --out frontend/public/api`.

Para depurar uma resposta sem exportar tudo, a API Flask em `app/` dá as mesmas respostas:

```bash
FISCALIZA_DATA_DIR=data flask --app app.main run --port 5000
```

## Verificações antes de um pull request

A CI corre estas verificações em cada pull request. Corra-as localmente antes de enviar:

```bash
ruff check .
ruff format --check .
pytest                    # tudo, incluindo tests/contracts
cd frontend && npm test && npm run build
```

- `ruff` 0.17.1 verifica o estilo e a formatação (`ruff format .` corrige a formatação).
- Os testes constroem releases sintéticas minúsculas. Não usam a rede nem dados reais, mas o teste da exportação estática precisa do `node`.
- `pytest tests/contracts` corre só os contratos: as chaves que o frontend lê em cada endpoint.

Os hooks de pre-commit (`pip install pre-commit && pre-commit install`) correm o ruff e o gitleaks antes de cada commit.

## Código

- Todo o SQL está em `app/data/repository.py`, `app/data/deputy_rows.py` e `fiscaliza_data/*.sql`. As rotas leem os argumentos, chamam um serviço em `app/services/` e devolvem o seu dicionário em JSON. A exportação chama os mesmos serviços.
- No frontend: componentes funcionais com hooks, pedidos através de `apiFetch()` em `config/api.js`, e números formatados com `utils/format.js` (formato de Portugal).
- Comentários, nomes de variáveis, funções e chaves de JSON ficam em inglês (ou nos nomes portugueses que já existem, como `deputados`). Todo o texto que um leitor vê no site, incluindo mensagens de erro, fica em português de Portugal.

## Rigor dos dados

O site só vale o que valem os seus números:

- Nunca invente dados nem ponha valores por omissão onde falta um dado real.
- Se um número está errado, corrija-o onde é calculado: no parlamento-aberto para os marts, ou nas vistas e serviços deste repositório. Nunca altere o ficheiro de dados à mão.
- Quando um mart ainda não existe, o endpoint diz isso (503 com o motivo) e a página mostra um aviso. Nada de números provisórios.

## Commits e pull requests

- Abra cada pull request a partir de `master`, com uma alteração por pull request. Para atualizar um ramo, faça merge de `master` no ramo.
- Use [Conventional Commits](https://www.conventionalcommits.org/) em inglês, na forma `type(scope): subject`, por exemplo `fix(voting): show the group's position instead of an alignment rate`.
- Escreva o título, a descrição, as issues e os comentários em português de Portugal.
- Preencha o modelo de pull request: um resumo de uma ou duas linhas, uma tabela antes/depois, capturas de ecrã para alterações visíveis e uma linha sobre como foi testado.

## Licença

Ao contribuir, aceita que o código que enviar fica sob a licença AGPL-3.0-or-later ([LICENSE](LICENSE)).
