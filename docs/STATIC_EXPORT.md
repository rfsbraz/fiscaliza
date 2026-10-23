# Exportação estática

O Fiscaliza corre como site estático. A release de dados é sincronizada para um ficheiro DuckDB,
todas as respostas de que o frontend precisa são geradas como ficheiros JSON, e o frontend
compilado e esses ficheiros vão para qualquer alojamento estático. Não corre nenhum servidor
quando alguém faz um pedido.

## Como construir

```bash
python -m fiscaliza_data sync                                   # a release, para $FISCALIZA_DATA_DIR
python -m fiscaliza_data.export --out frontend/public/api       # todas as respostas, em JSON
cd frontend && npm ci && npm run build                          # dist/ com os ficheiros em dist/api
```

`dist/` é o site inteiro. A exportação também pode ser escrita diretamente em `dist/api` depois
do build. `--jobs N` define os processos para os ficheiros dos deputados (por omissão, todos os
núcleos); a release completa demora alguns minutos. A exportação escreve uma pasta nova e só a
põe no lugar quando tudo foi gerado, por isso uma execução que falha deixa a anterior intacta.

Para o `npm run dev`, gere para `frontend/public/api` (ignorado pelo git) e o servidor de
desenvolvimento serve-o em `/api`. O frontend lê os ficheiros de `VITE_API_BASE_URL`, definido no
build, por omissão `/api` na origem do próprio site. Se os ficheiros estiverem noutra origem, esse
alojamento tem de enviar cabeçalhos CORS.

## Estrutura

Legislaturas, partidos e coligações aparecem nos caminhos numa só forma: sem acentos, em
minúsculas, e cada sequência de outros caracteres (barra, espaço) passa a um hífen. XVII é
`xvii`, PàF é `paf`, MDP/CDE é `mdp-cde`, CDS-PP é `cds-pp`. A exportação para se dois nomes
derem o mesmo caminho. O browser aplica a mesma regra (`frontend/src/config/staticApi.js`) e
aceita uma legislatura em numeração romana ou como número (`17`), como a API.

| Endpoint | Ficheiro |
|---|---|
| `legislaturas`, `estatisticas`, `partidos`, `health`, `dados`, `estatisticas/atividade` | `legislaturas.json`, `estatisticas.json`, `partidos.json`, `health.json`, `dados.json`, `estatisticas/atividade.json` |
| `votacoes/recentes?limite=5` (e o valor por omissão, 10) | `votacoes/recentes/5.json`, `votacoes/recentes/10.json` |
| `coligacoes?include_inactive=false` / `true` | `coligacoes.json` / `coligacoes-todas.json` |
| `coligacoes/{id}`, `/deputados`, `/partidos` (uma página por lista e sequência: `ad-2024`, `ad-acores-2025`, `CDU`) | `coligacoes/{slug}.json`, `coligacoes/{slug}/deputados.json`, `coligacoes/{slug}/partidos.json` |
| `deputados?page&per_page&active_only&search` | `deputados.json`: todos, pela ordem da lista; a pesquisa, o filtro e a paginação correm no browser |
| `deputados/{id}/detalhes`, `/conflitos-interesse`, `/atividades`, `/voting-analytics`, `/attendance` | `deputados/{id}.json`: um ficheiro por pessoa com tudo isto, para todas as legislaturas em que esteve; as intervenções são filtradas, ordenadas e paginadas no browser |
| `partidos/{sigla}/deputados` | `partidos/{slug}/deputados.json` |
| `partidos/{sigla}/voting-analytics[?legislatura]` | `partidos/{slug}/voting-analytics.json`, `partidos/{slug}/voting-analytics/{slug da legislatura}.json` |

Um ficheiro por deputado faz o número de ficheiros crescer com as pessoas e não com pessoas vezes
legislaturas: cerca de 3400 ficheiros na release completa em vez de cerca de 20 000. O
`tests/test_static_export.py` falha se uma geração chegar aos 20 000 ficheiros ou se algum
ficheiro chegar aos 25 MiB, e a própria exportação recusa pôr no lugar uma geração assim. Esses
limites servem os alojamentos estáticos habituais (o Cloudflare Pages, por exemplo, permite
20 000 ficheiros por deploy e 25 MiB por ficheiro); armazenamento de objetos atrás de uma CDN não
tem limites destes.

Os ficheiros dos deputados são gerados 50 pessoas de cada vez. Cada pergunta que a página do
deputado faz corre uma vez para o lote inteiro (`app/data/deputy_rows.py`), e não uma vez por
pessoa e legislatura, e as rotas Flask constroem as mesmas respostas a partir das mesmas linhas
para uma pessoa.

Os pedidos que o frontend não faz (por exemplo `estatisticas?legislatura=XVI`, ou as atividades
de um deputado numa legislatura em que nunca esteve) não são gerados e respondem 404.

## Ainda não gerado

A agenda de hoje e da semana (`agenda/hoje`, `agenda/semana`, S13) espera pelo seu mart no
parlamento-aberto. O browser responde-lhe 503 "não disponível" com o passo que a vai trazer, e a
página mostra o aviso. Vai ter um ficheiro por semana, com o "hoje" escolhido no browser na hora
de Europe/Lisbon.

A assiduidade (`deputados/{id}/attendance`, S11) é o campo `attendance` do ficheiro de cada
deputado: uma `DeputySection` em `DEPUTY_SECTIONS` (`fiscaliza_data/export.py`) e uma entrada no
`staticApi.js`. Um endpoint novo de deputado acrescenta-se da mesma forma.

Os endpoints dos partidos são gerados quando o S6 (#79) e o S7 (#81) estiverem no master; a
exportação apanha os seus serviços sozinha.

## Ligações diretas

A aplicação trata das rotas no browser, por isso `/deputados/123` não tem ficheiro próprio. O
build escreve o `index.html` outra vez como `404.html`. Os alojamentos que servem o `404.html`
para um caminho que não existe carregam a aplicação em qualquer ligação direta: GitHub Pages,
Cloudflare Pages, S3 ou CloudFront com `404.html` como documento de erro, nginx com
`error_page 404 /404.html`. Estes respondem às ligações diretas com o estado 404 e a aplicação
aparece na mesma. Para responder 200, use a regra de SPA do próprio alojamento: no nginx
`try_files $uri /index.html` ou uma reescrita para `/index.html` numa CDN. Para o Cloudflare
Pages, o `deploy/pages.py` escreve um ficheiro HTML por rota da aplicação com o head dessa rota,
que responde 200 e mantém um 404 a sério para todos os outros caminhos, e um `sitemap.xml` com as
mesmas rotas (ver [DEPLOY.md](DEPLOY.md)).

Um ficheiro de dados em falta passa então a vir como `404.html` (ou `index.html`) em vez de JSON.
O frontend trata tudo o que não é JSON como não encontrado, por isso não há problema.

Para experimentar um build localmente sem Flask: `npm run preview` em `frontend/`, ou qualquer
servidor estático com recurso a index.html.
