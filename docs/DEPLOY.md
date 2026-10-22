# Deploy

O Fiscaliza é um site estático no Cloudflare Pages, projeto `fiscaliza`, enviado com
`wrangler pages deploy` (envio direto, sem integração com o Git). O ramo de produção é `master`, em
`fiscaliza-ceg.pages.dev`; qualquer outro ramo é uma pré-visualização em
`<ramo>.fiscaliza-ceg.pages.dev` (o Pages troca `/` e outros caracteres do nome do ramo por `-`).

Os deploys correm na CI, em `.github/workflows/deploy.yml`, num runner alojado pelo GitHub
(`ubuntu-latest`). O workflow só chama `deploy/pages.py`; tudo o que um deploy faz está nesse
script.

## Quando há deploy

| Evento | Deploy |
|---|---|
| Push para `master` | produção |
| Pull request deste repositório que muda o site, ou tem a etiqueta `preview` | uma pré-visualização num ramo do Pages com o nome do ramo do pull request |

Não há agendamento: os dados só mudam quando o pin muda, e mudar o pin é um pull request, que faz
o deploy de produção quando é integrado.

Pull requests de forks não têm deploy, nem os do Dependabot: nenhum deles recebe os segredos do
repositório.

Um deploy constrói o site inteiro e envia-o, por isso um pull request só tem pré-visualização
quando precisa. Um job curto, `Preview Needed`, compara o pull request com `master` e deixa correr
o deploy quando algo mudou em `frontend/`, `fiscaliza_data/`, `app/` ou `deploy/`, ou em
`.github/workflows/deploy.yml` (`PREVIEW_PATHS` no workflow). O resto, como documentação ou
testes, não tem job de deploy.

Para ter pré-visualização noutro pull request, adicione a etiqueta `preview`. Isso começa logo um
deploy, e cada push seguinte para esse pull request faz novo deploy até a etiqueta sair. Adicionar
outra etiqueta não começa nada.

### Concorrência

As pré-visualizações e a produção nunca partilham um grupo de concorrência (#152). O GitHub mantém
no máximo um job a correr e um pendente por grupo, e um job mais recente substitui o pendente. Com um
só grupo para todos os eventos, cada push para `master` cancelava as pré-visualizações que estavam à
espera, por isso os pull requests mostravam um Deploy cancelado, uma pré-visualização podia cancelar
um deploy de produção pendente, e o `Pin Merge` parava num pull request do pin cuja
pré-visualização tinha sido cancelada (#151).

- Um pull request faz o deploy no seu próprio grupo, `pages-preview-<número do PR>`, com
  `cancel-in-progress: true`: um push mais recente para o mesmo pull request cancela a
  pré-visualização anterior, mesmo a meio, porque só interessa a cabeça mais recente. Um deploy do
  Pages só fica ativo quando o envio acaba, por isso um deploy cancelado deixa a pré-visualização
  anterior no lugar. Outros pull requests e `master` nunca o cancelam.
- A produção faz o deploy em `pages-production`, com `cancel-in-progress: false`: nada cancela um
  deploy de produção em curso. Um push para `master` enquanto um corre fica à espera dele. Um
  terceiro push enquanto esse ainda espera substitui-o, e a execução substituída aparece como
  cancelada. Uma série de merges salta por isso os deploys intermédios, e o `master` mais recente,
  com o pin mais recente, é sempre o último a ter deploy.

As pré-visualizações e a produção podem agora correr ao mesmo tempo; enviam para ramos diferentes
do Pages. Os grupos estão no job de deploy, por isso um pull request que não precisa de
pré-visualização nunca entra num.

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
request pequeno e próprio; a sua pré-visualização mostra os dados novos antes de ser integrado. A
maior parte das mudanças é automática (ver [Mudanças automáticas do pin](#mudanças-automáticas-do-pin));
continuo a mudá-lo à mão quando uma alteração precisa que se verifiquem números novos primeiro, como
no #132.

Antes de o mudar, construa uma release a partir do commit novo e corra `tests/test_release_pin.py`
sobre ela, com `FISCALIZA_RELEASE_DIR` a apontar para essa pasta. O teste verifica que a release foi
construída a partir do pin e tem os números para os quais o pin muda; atualize-os no mesmo pull
request.

Quando o parlamento-aberto ligar as releases de dados (`DATA_RELEASES`), o pin passa para uma tag
de release.

## Mudanças automáticas do pin

Quando o `main` do parlamento-aberto muda, abre-se aqui um pull request do pin, que se integra
sozinho quando todas as verificações estão verdes (#133). É a minha única exceção a integrar à mão,
só para pull requests do pin. O `master` não tem proteção de ramo nem verificações obrigatórias, por
isso o auto-merge do GitHub não consegue esperar pela CI; dois workflows fazem esse trabalho, e
`deploy/pin_bump.py` tem a lógica (testada em `tests/test_pin_bump.py`).

1. O `fiscaliza-dispatch.yml` do parlamento-aberto corre em cada push para o seu `main` e envia
   para aqui um `repository_dispatch`: tipo de evento `data-updated`, payload `{"sha": "<commit>"}`.
2. O `data-pin-bump.yml` (`Pin Bump`) verifica que o SHA é um commit completo no `main` do
   parlamento-aberto. Quando o pin em `master` já o tem, ou é mais antigo que o pin, para aí e não
   abre nada. Caso contrário, repõe o ramo `data/pin-bump` a partir de `master`, escreve o pin novo e
   faz force-push desse ramo. É o único ramo onde algo faz force-push. Depois abre o pull request do
   pin, ou atualiza o que está aberto, para haver sempre só um. O título é
   `chore(data): move the data pin to parlamento-aberto <sha curto>`, e a descrição lista os SHAs
   antigo e novo e os commits do parlamento-aberto entre eles. Um dispatch mais recente cancela um
   que esteja a correr e substitui a cabeça do pull request.
3. A CI e o Deploy de pré-visualização do pull request correm como em qualquer pull request.
4. O `data-pin-merge.yml` (`Pin Merge`) corre cada vez que a CI, o Deploy ou o gitleaks
   acabam em `data/pin-bump`. Olha para todas as execuções de workflows na cabeça do pull
   request: enquanto uma ainda corre, sai e espera que a próxima acabe, por isso nunca ocupa um
   runner enquanto a CI corre. Quando todas passaram, e a CI e o Deploy estão entre elas, faz squash-merge do pull request
   nessa cabeça. O push para `master` faz depois o deploy de produção.

Os dois workflows correm em runners alojados pelo GitHub (`ubuntu-latest`), como a CI e o Deploy.

### Paragens de segurança

O `Pin Merge` não integra, deixa o pull request aberto com um comentário a dizer porquê, e falha,
quando:

- um workflow na cabeça do pull request falhou, foi cancelado ou excedeu o tempo. Só conta a
  execução mais recente de cada workflow nessa cabeça, e só um push mais recente para o pull request
  do pin cancela a sua pré-visualização, por isso outros deploys já não a cancelam;
- as verificações não acabaram 6 horas depois do commit do pin;
- o major de `schema_version` no parlamento-aberto (`src/parlamento_aberto/models/schema.yml`) é
  diferente entre o pin antigo e o novo (o `Pin Bump` também comenta logo neste caso);
- o pull request muda algo além de `deploy/data-pin`;
- o GitHub recusa o merge, por exemplo quando o próprio `master` mudou o pin e o pull request entra
  em conflito.

Uma cabeça parada nunca é integrada mais tarde. Eu vejo-a e integro ou fecho o pull request à mão.
O próximo commit do parlamento-aberto repõe o ramo e começa de novo.

### Segredos

| Repositório | Segredo | Token |
|---|---|---|
| `rfsbraz/fiscaliza` | `PIN_BOT_TOKEN` | token fine-grained, com acesso só ao repositório `rfsbraz/fiscaliza`, com Contents: read and write e Pull requests: read and write (o Metadata: read vem incluído) |
| `rfsbraz/parlamento-aberto` | `FISCALIZA_DISPATCH_TOKEN` | token fine-grained, com acesso só ao repositório `rfsbraz/fiscaliza`, com Contents: read and write |

O `PIN_BOT_TOKEN` faz push de `data/pin-bump`, abre e edita o pull request e integra-o. Um pull
request aberto ou integrado com o `GITHUB_TOKEN` não inicia workflows, por isso sem ele o pull
request não teria CI e o merge não teria Deploy de produção. O próprio `GITHUB_TOKEN` dos workflows
faz as leituras (o parlamento-aberto é público) e publica os comentários das paragens. Os dois
workflows param no primeiro passo com um erro que nomeia o `PIN_BOT_TOKEN` quando ele falta.

O `FISCALIZA_DISPATCH_TOKEN` só envia o dispatch. O GitHub pede Contents: write no repositório de
destino para `POST /repos/{owner}/{repo}/dispatches`, por isso não pode ser menor. Um só token com
Contents e Pull requests read and write em `rfsbraz/fiscaliza` serviria para os dois, guardado com
os dois nomes, mas mantenho dois para poder revogar cada um à parte. Nenhum deles vai para outro
sítio além dos segredos do repositório.

Se o push de `data/pin-bump` for alguma vez recusado porque o `master` mudou um ficheiro de
workflow desde o último push do ramo, feche o pull request do pin e apague o ramo; a próxima
execução volta a criá-lo.

### Execução manual

Actions, `Data Pin Bump`, Run workflow, com um SHA de commit do parlamento-aberto (os 40
caracteres). Com o pin atual não faz nada e não abre nenhum pull request, que é a forma mais rápida
de verificar que o token funciona. `gh workflow run data-pin-bump.yml -f sha=<sha>` faz o mesmo.

Quando o parlamento-aberto ligar as releases de dados, o dispatch passa para `release: published` e
o pin para a tag da release (#57). Relacionados: #132 (a última mudança à mão) e #128 (a página de
metodologia diz que o site só muda de versão dos dados de propósito, o que agora quer dizer através
de um pull request do pin que passou na CI, e não de um que eu abri à mão).

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
5. O passo do Pages sobre `frontend/dist`: copia para lá `deploy/_headers` e `deploy/_redirects`,
   mantém o `404.html` do build (de novo a aplicação) e verifica os limites do Pages (menos de
   20 000 ficheiros, cada um com menos de 25 MiB). Escreve também um HTML por cada rota da
   aplicação, com o título, a descrição, o canonical e o `og:url` dessa rota (ver "Ligações
   diretas"), e o `sitemap.xml` com essas mesmas rotas (ver "Sitemap"). Qualquer outro caminho sem ficheiro recebe o `404.html` e o estado 404, e a aplicação
   mostra a vista "Página não encontrada". Uma rota nova em `frontend/src/App.jsx` precisa de
   entrar em `route_heads` no `deploy/pages.py`, e `tests/test_route_heads.py` verifica isso.
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
  DuckDB. A CI deixa `EXPORT_WORKERS` por definir, por isso a exportação usa os CPUs do runner. O
  passo de deploy para ao fim de 80 minutos e o job ao fim de 90; um deploy costuma demorar poucos
  minutos.
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

A aplicação trata das rotas no browser. Para que uma ligação direta carregue a aplicação e as
pré-visualizações de ligações (WhatsApp, X, Telegram, que não correm JavaScript) mostrem a página
certa, o passo do Pages escreve um HTML por rota: `deputados/2105.html` para `/deputados/2105`,
`partidos/PS.html`, `coligacoes/ad-2024.html`, `perguntas/XVII.html`, `deputados.html`,
`metodologia.html`, e assim por diante. Cada um é o `index.html` do build com o título, a descrição,
o canonical e o `og:url` dessa rota, e responde 200. As rotas saem dos ficheiros de índice da
exportação, por isso um deputado, partido ou coligação novo tem a sua página no deploy seguinte. O
próprio `/` é o `index.html`.

O `deploy/_redirects` não tem regras para as rotas. O Pages aplica uma regra 200 antes de procurar
o ficheiro, por isso uma regra `/deputados/* / 200` esconderia estas páginas. As únicas regras são
301 de páginas que deixaram de existir: `/coligacoes/AD` e `/coligacoes/Madeira Primeiro` passaram a
uma página por lista (#111) e levam à lista mais recente. Com cerca de 3 300 ficheiros da
exportação, 3 070 páginas de rotas e o sitemap, o deploy fica perto dos 6 400 ficheiros, longe do
limite de 20 000.

Qualquer outro caminho sem ficheiro, como `/sobre`, recebe o `404.html` de topo com o estado 404.
Esse ficheiro é de novo a aplicação, escrito pelo build, e a aplicação mostra a vista "Página não
encontrada" com `noindex`.

## Sitemap

O passo do Pages escreve o `sitemap.xml` com a mesma lista de rotas das páginas acima, mais o `/`,
cada uma com o seu URL canonical. Um deputado, partido ou coligação novo entra no sitemap no deploy
seguinte. Com os dados atuais são cerca de 3 070 URLs e 175 KB. Acima de 50 000 URLs, o limite de
um sitemap, o passo escreve `sitemap-1.xml`, `sitemap-2.xml` e assim por diante, e o `sitemap.xml`
passa a ser o índice desses ficheiros. Um ficheiro acima de 50 MB faz o deploy parar.

O `/robots.txt` é um ficheiro real de `frontend/public`: permite tudo e indica
`https://fiscaliza.pt/sitemap.xml`.

Um ficheiro de dados que não existe em `/api` também responde 404. O frontend trata tudo o que não
é JSON como não encontrado.

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

A CSP: scripts, dados e frames só do próprio site (`frame-ancestors 'none'`), com duas exceções
para o Cloudflare Web Analytics (o script de `static.cloudflareinsights.com` e os envios para
`cloudflareinsights.com`), estilos do site
(`'unsafe-inline'` para os atributos de estilo que o Recharts e o framer-motion definem), tipos de
letra só do site (estão alojados em `frontend/src/assets/fonts`, e o build nunca os embute como
URIs `data:`), e imagens do site, `data:`, `app.parlamento.pt` (as fotografias dos deputados em
`picture_url`) e `www.parlamento.pt` (as fotografias na demografia dos partidos). Um novo anfitrião
externo de imagens, tipos de letra ou scripts precisa de uma linha aqui, e
`tests/test_pages_deploy.py` falha quando o frontend ou `PICTURE_URL` usam um anfitrião de imagens
que a CSP não permite.

Se os ficheiros da API passarem para outra origem (`VITE_API_BASE_URL`), acrescente-a a
`connect-src`.

## Antes do domínio próprio

- Um deploy de produção a partir de `master` verificado em `fiscaliza-ceg.pages.dev`.
- O domínio próprio `fiscaliza.pt` adicionado ao projeto do Pages (a Cloudflare acrescenta o
  registo DNS, já que a zona está na Cloudflare).
