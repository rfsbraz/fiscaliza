# Deploy

O Fiscaliza é um site estático no Cloudflare Pages, projeto `fiscaliza`, enviado com
`wrangler pages deploy` (envio direto, sem integração com o Git). O ramo de produção é `master`, em
`fiscaliza-ceg.pages.dev`; qualquer outro ramo é uma pré-visualização em
`<ramo>.fiscaliza-ceg.pages.dev` (o Pages troca `/` e outros caracteres do nome do ramo por `-`).

Os deploys correm na CI, em `.github/workflows/deploy.yml`, no runner self-hosted do repositório.
O workflow só chama `deploy/pages.py`; tudo o que um deploy faz está nesse script.

## Quando há deploy

| Evento | Deploy |
|---|---|
| Push para `master` | produção |
| Pull request deste repositório que muda o site, ou tem a etiqueta `preview` | uma pré-visualização num ramo do Pages com o nome do ramo do pull request |

Não há agendamento: os dados só mudam quando o pin muda, e mudar o pin é um pull request, que faz
o deploy de produção quando é integrado.

Pull requests de forks não têm deploy, nem os do Dependabot: nenhum deles recebe os segredos do
repositório.

Um deploy ocupa o runner durante bastante tempo, por isso um pull request só tem pré-visualização
quando precisa. Um job curto, `Preview Needed`, compara o pull request com `master` e deixa correr
o deploy quando algo mudou em `frontend/`, `fiscaliza_data/`, `app/` ou `deploy/`, ou em
`.github/workflows/deploy.yml` (`PREVIEW_PATHS` no workflow). O resto, como documentação ou
testes, não tem job de deploy.

Para ter pré-visualização noutro pull request, adicione a etiqueta `preview`. Isso começa logo um
deploy, e cada push seguinte para esse pull request faz novo deploy até a etiqueta sair. Adicionar
outra etiqueta não começa nada.

Há um só grupo de concorrência para todos os eventos, com `cancel-in-progress: false`: um deploy
espera que o anterior acabe e nunca é cancelado a meio de um envio. O grupo está no job de
deploy, por isso um pull request que não precisa de pré-visualização não fica à espera de um deploy
em curso só para o saltar.

O workflow precisa de:

- o segredo `CLOUDFLARE_API_TOKEN`, um token da API da Cloudflare com Pages: Edit na conta;
- `CLOUDFLARE_ACCOUNT_ID`, definido no workflow como variável de ambiente simples (o ID de uma conta
  não é segredo).

O projeto já existe. Nada o cria, e nada imprime o token.

## O pin dos dados

`deploy/data-pin` guarda o commit do parlamento-aberto a partir do qual o site é construído, e a
tag da release quando existe. É o único sítio onde a versão dos dados é definida, e todos os
deploys, de produção e de pré-visualização, constroem exatamente esse commit.

A produção está fixada porque a CI começa sempre com a pasta de dados vazia: a verificação da
sincronização de que nenhuma tabela perdeu mais de 5% das linhas não tem com que comparar, por isso
um commit mau no `main` do parlamento-aberto iria direto para produção. Mudar o pin é um pull
request próprio, depois de verificar os dados novos; a sua pré-visualização mostra os dados novos
antes de ser integrado.

Quando o parlamento-aberto ligar as releases de dados (`DATA_RELEASES`), o pin passa para uma tag
de release.

## O que um deploy corre

```bash
python deploy/pages.py deploy --parlamento-aberto ~/src/parlamento-aberto --branch my-preview
```

Isto corre, por ordem:

1. Um fetch do SHA fixado quando o clone não o tem (com profundidade um num clone raso), depois
   `git worktree add --detach` do commit fixado e, aí,
   `uv run python -m parlamento_aberto.release build` (o mesmo comando do seu workflow de release),
   para uma pasta temporária.
2. `python -m fiscaliza_data sync --from-dir <release>` para uma pasta DuckDB temporária.
3. `python -m fiscaliza_data.export --out frontend/public/api` (a exportação estática, ver
   [STATIC_EXPORT.md](STATIC_EXPORT.md)).
4. `npm ci` e `npm run build` em `frontend/`.
5. O passo do Pages sobre `frontend/dist`: apaga `404.html`, copia `deploy/_headers` para lá e
   verifica os limites do Pages (menos de 20 000 ficheiros, cada um com menos de 25 MiB).
6. `wrangler pages deploy dist --project-name fiscaliza --branch <ramo>`.

A pasta temporária e o worktree do parlamento-aberto são removidos no fim. A CI clona o
parlamento-aberto com `--depth 1 --no-checkout`, por isso os dados são extraídos uma só vez, no
passo 1, e o commit fixado é descarregado se o `main` já o tiver ultrapassado.

`python deploy/pages.py build --parlamento-aberto CAMINHO` corre só os passos 1 a 3, com os dados
em `data/` (ou `--data-dir`), sem build do frontend nem envio. É o caminho para preparar os dados
num clone novo (ver o [CONTRIBUTING.md](../CONTRIBUTING.md)).

Opções:

- `--branch NOME` escolhe o ramo da pré-visualização (por omissão `preview`).
- `--production` faz o deploy de `master`. `--branch master` sem esta opção é recusado.
- `--release PASTA` usa uma pasta de `release build` que já tenha. O seu `manifest.json` tem de
  indicar o commit fixado como `data_commit`, ou o script para.
- Sem fonte e com um `tag=` no pin, a sincronização descarrega essa release do GitHub.
- `EXPORT_WORKERS` define os processos da exportação. Sem ele, a exportação usa o limite de CPU do
  cgroup (`/sys/fs/cgroup/cpu.max`) e, sem esse, o número de CPUs. Cada processo usa uma thread do
  DuckDB. A CI deixa `EXPORT_WORKERS` por definir, por isso a exportação segue o limite do runner.
  O passo de deploy para ao fim de 80 minutos e o job ao fim de 90.
- `--work PASTA` guarda os ficheiros temporários nessa pasta em vez de numa temporária.
- `--dry-run` mostra todos os comandos e não corre nada.
- `WRANGLER` substitui o comando do wrangler. Por omissão é `npx --yes wrangler@4.151.3`, fixado
  para que a CI e uma execução local usem a mesma versão. O Wrangler 4 precisa do Node 22 ou mais
  recente; o workflow instala o Node 22.
- `python deploy/pages.py prepare frontend/dist` corre só o passo 5.

Corrido à mão, o wrangler usa o login da Cloudflare que a máquina tiver (`wrangler whoami`
mostra-o), ou `CLOUDFLARE_API_TOKEN` e `CLOUDFLARE_ACCOUNT_ID` quando estão definidos. O script
nunca faz login e nunca cria tokens.

## Ligações diretas

A aplicação trata das rotas no browser. No Pages, um build sem `404.html` na raiz é tratado como
aplicação de página única: qualquer caminho sem ficheiro próprio recebe `index.html` com o estado
200. É por isso que o passo do Pages apaga `404.html`. O `npm run build` simples continua a
escrevê-lo, porque o GitHub Pages, o S3 e o nginx com `error_page` precisam dele.

Um ficheiro de dados que não existe em `/api` também recebe então `index.html`. O frontend trata
tudo o que não é JSON como não encontrado.

## Cabeçalhos

`deploy/_headers`, copiado para o build:

| Caminho | Cabeçalho |
|---|---|
| `/assets/*` | `Cache-Control: public, max-age=31536000, immutable` (o Vite põe um hash nestes nomes) |
| `/`, `/index.html` | `Cache-Control: no-cache` |
| `/api/*` | `Cache-Control: public, max-age=300` (os dados mudam a cada deploy, os nomes não) |
| tudo | HSTS durante um ano com subdomínios, sem preload; `X-Content-Type-Options: nosniff`; `Referrer-Policy: strict-origin-when-cross-origin`; `X-Frame-Options: DENY`; uma `Permissions-Policy` que desliga câmara, microfone e localização; a CSP abaixo |

As ligações diretas ficam com a predefinição do Pages para HTML,
`public, max-age=0, must-revalidate`. O Pages junta com uma vírgula o mesmo cabeçalho de todas as
regras que coincidem, por isso o `Cache-Control` nunca é definido em `/*`.

A CSP: scripts, dados e frames só do próprio site (`frame-ancestors 'none'`), estilos do site e do
Google Fonts (`'unsafe-inline'` para os atributos de estilo que o Recharts e o framer-motion
definem), tipos de letra de `fonts.gstatic.com`, e imagens do site, `data:`, `app.parlamento.pt`
(as fotografias dos deputados em `picture_url`) e `www.parlamento.pt` (as fotografias na
demografia dos partidos). Um novo anfitrião externo de imagens, tipos de letra ou scripts precisa de
uma linha aqui, e `tests/test_pages_deploy.py` falha quando o frontend ou `PICTURE_URL` usam um
anfitrião de imagens que a CSP não permite.

Se os ficheiros da API passarem para outra origem (`VITE_API_BASE_URL`), acrescente-a a
`connect-src`.

## Antes do domínio próprio

- Um deploy de produção a partir de `master` verificado em `fiscaliza-ceg.pages.dev`.
- O domínio próprio `fiscaliza.pt` adicionado ao projeto do Pages (a Cloudflare acrescenta o
  registo DNS, já que a zona está na Cloudflare).
