# Metodologia e fontes

Esta página explica de onde vêm os dados do Fiscaliza, como se calcula cada número e o que os dados não dizem. Se encontrar um erro, veja no fim como o reportar.

## Fontes e licença

Todos os números do Fiscaliza vêm dos dados abertos da Assembleia da República (AR). Não usamos outras fontes nem acrescentamos dados à mão.

Os dados chegam ao Fiscaliza através do parlamento-aberto, um repositório público que descarrega os ficheiros de dados abertos da AR, os normaliza e publica, em cada versão (release), um conjunto de tabelas prontas a consultar. Os dados são atualizados automaticamente sempre que o parlamento-aberto publica alterações, e só depois de o site passar todos os testes. A data dos dados está indicada no site.

Licenças:

- Os dados da AR são reutilizados nos termos da AR, que permite a reutilização livre desde que se mencione a fonte. Como pede a Lei n.º 26/2016, art. 19.º, n.º 5, indicamos a fonte e a data da última atualização em todas as páginas.
- As tabelas que o parlamento-aberto constrói estão sob a licença Creative Commons Atribuição 4.0 Internacional (CC BY 4.0), na parte que é trabalho desse repositório. Os dados da AR que contêm continuam sujeitos aos termos da AR.
- As declarações de interesses publicadas pela Entidade para a Transparência (EpT) não entram nos dados publicados enquanto a EpT não responder sobre a sua reutilização. Por isso o Fiscaliza não as mostra.

Para citar: Fonte: Assembleia da República, dados abertos, atualizados a {source_updated}. Dados tratados por parlamento-aberto ({tag}), sob CC BY 4.0.

## Data dos dados

- Dados da AR atualizados a: {source_updated}
- Versão dos dados (parlamento-aberto): {tag}

A data de atualização é a última data em que um ficheiro da AR foi recolhido com alterações. O que a AR publicou depois dessa data ainda não aparece no site.

## Presenças no Plenário

A AR publica, para cada reunião plenária, a lista de quem tinha lugar nessa reunião (substitutos incluídos) com um código para cada deputado. O Fiscaliza conta esses códigos. Não usa o motivo da falta: as listas trazem um texto livre com o motivo, mas ele não entra no site. Só o código conta.

**Presente ou em funções parlamentares.** É o número principal: as reuniões em que o deputado esteve presente no Plenário, noutro órgão, em comissão autorizada pelo Presidente da AR ou em missão parlamentar, sobre as reuniões plenárias ordinárias e extraordinárias em que constava da lista. Conta os códigos:

- PT, PR e PP: presença. PT usou-se de 1991 a fevereiro de 2021, PP de 1991 a março de 2009 e PR desde maio de 2020.
- PNO: presença noutro órgão.
- CO: presença em comissão autorizada pelo Presidente da AR.
- ME e MP: ausência em missão parlamentar.

**Só presenças no Plenário.** Ao lado do número principal mostramos a taxa estrita, que conta só PT, PR e PP sobre as mesmas reuniões. As duas taxas aparecem sempre com o número de reuniões.

As restantes categorias aparecem em separado, cada uma com a sua contagem:

- Falta justificada: FJ, FIJ, FAJ e QVJ.
- Falta ao quórum de votação: QV.
- Falta por justificar: FA numa reunião com menos de 60 dias na data dos dados. O prazo para justificar uma falta é de cinco dias parlamentares (Resolução da AR n.º 21/2009, n.º 11 e 12), mas há FA que ficam meses sem classificação nos dados.
- Falta não classificada pela AR: FA numa reunião com 60 dias ou mais.
- Falta injustificada: FI. É o único código que contamos como falta injustificada. Um FA nunca conta como injustificada.

As reuniões solenes e comemorativas contam à parte e ficam fora das taxas. Quando há menos de 20 reuniões numa legislatura, avisamos que cada falta pesa vários pontos na taxa. Numa legislatura em curso, indicamos a data da última reunião nos dados.

Também mostramos a taxa de todos os deputados da legislatura, calculada da mesma forma sobre todos os lugares nas mesmas listas.

A AR não publica legenda para estes códigos. Os significados vêm da comparação, deputado a deputado, entre o código nos dados abertos e o rótulo na página de cada reunião em parlamento.pt, e da Resolução da AR n.º 21/2009, que aprova o regime de presenças e faltas ao Plenário.

## Taxa de aprovação de iniciativas

Mostramos uma taxa de aprovação para projetos de lei, projetos de resolução e projetos de deliberação, por legislatura, no deputado e no grupo parlamentar.

- Conta só as iniciativas que tiveram um desfecho em plenário: aprovadas numa votação final, ou rejeitadas numa votação final ou na generalidade.
- Uma iniciativa aprovada só em parte, numa votação ponto a ponto, conta como aprovada e aparece também numa linha à parte.
- As iniciativas que caducaram com o fim da legislatura, foram retiradas ou ainda não foram votadas não entram na taxa e aparecem à parte. Os dados não distinguem estes três casos.
- Só mostramos a taxa quando há pelo menos 10 iniciativas votadas. Abaixo disso mostramos só as contagens.
- Uma iniciativa conjunta conta para cada grupo que a assina.

No deputado, contamos as iniciativas que ele assina. Nos dados da AR, as iniciativas de um grupo parlamentar costumam listar todos os deputados do grupo como autores, por isso estes números mostram como o deputado assina, não quem redigiu cada iniciativa.

A taxa de aprovação não mede a eficácia de um deputado ou de um grupo. A oposição apresenta muitas vezes iniciativas para levar um tema a debate, sem expectativa de as ver aprovadas.

## Sentido de voto

A AR não publica uma votação nominal, deputado a deputado. Para cada votação em plenário publica o sentido de voto de cada grupo parlamentar e, quando os há, os nomes dos deputados que votaram de forma diferente do seu grupo.

Por isso, no separador Votações de cada deputado:

- O título é "Sentido de voto do grupo nas votações em que o deputado tinha lugar". Para cada votação, atribuímos ao deputado o sentido de voto do seu grupo nesse dia, exceto quando o registo da votação o nomeia com outro sentido.
- "Tinha lugar" quer dizer que o deputado estava em funções nesse dia. Não quer dizer que estivesse presente. O registo das votações quase nunca nomeia quem faltou, por isso estes números não servem para saber se o deputado votou. A presença está no separador Presenças.
- Em vez de uma percentagem de alinhamento com o grupo, mostramos "Votos diferentes do grupo registados: N", o número de votações em que o registo nomeia o deputado com um sentido de voto diferente do do seu grupo.
- Quando o grupo se dividiu e os deputados nomeados não chegam para explicar a divisão, o sentido de voto dos restantes fica desconhecido.
- Há votações não unânimes sem detalhe publicado: a AR dá o resultado, mas não diz como votou cada grupo. Ficam fora destas contagens e não inferimos nada para elas.

Nas páginas dos partidos, mostramos "Votações sem votos diferentes registados": quantas votações em que o registo não nomeia nenhum deputado do grupo com outro sentido de voto. O registo só nomeia quem vota de forma diferente, e um grupo pequeno tem poucos deputados que possam ser nomeados, por isso este número não serve para comparar grupos.

## Intervenções

As intervenções vêm do ficheiro de intervenções que a AR publica para cada legislatura. A cobertura é desigual:

- Não há ficheiro para a Assembleia Constituinte, a I Legislatura (I-A e I-B) nem a III.
- Há lacunas grandes na II, IV, VII, XII e XIV. Por exemplo, a XII não tem nada antes de setembro de 2013 e a XIV não tem nenhuma reunião entre setembro de 2020 e setembro de 2021.
- Numa legislatura em curso, a AR publica as intervenções com atraso. Na XVII, os dados têm por agora {n} intervenções. Nessas legislaturas a lista está incompleta e não fazemos comparações.

A comparação com o grupo parlamentar usa intervenções por ano de mandato (o número de intervenções a dividir pelos dias em funções, vezes 365,25). A média do grupo conta só os deputados do mesmo grupo com lugar durante pelo menos metade da legislatura. Não mostramos média quando o deputado esteve em funções menos de metade da legislatura ou quando o grupo tem menos de 5 outros deputados nessas condições.

As perguntas escritas ao Governo não são intervenções e não entram nesta contagem.

## Declarações de interesses

Os dados abertos da AR só têm declarações de interesses da XI à XV Legislatura. Mesmo nesse período, os ficheiros da AR só incluem as pessoas que constam das listas da XVII Legislatura, incluindo suplentes. Quem já não está nessas listas não tem declaração nos dados abertos, mesmo que a tenha entregue na altura. Os dados têm declaração para {com_declaracao} de {total} deputados com mandato da XI à XV Legislatura.

Por isso, quando os dados não têm a declaração de um deputado, não concluímos nada. Dizemos que os dados abertos do Parlamento não incluem a declaração, e que isso não significa que não tenha sido entregue. Para legislaturas anteriores à XI, dizemos que os dados abertos não cobrem esse período. O registo de interesses pode ser consultado no site do Parlamento e no site da Entidade para a Transparência.

Desde a XVI Legislatura, as declarações são entregues à Entidade para a Transparência. Os dados da EpT ainda não são republicados, enquanto a EpT não responder sobre a sua reutilização.

O prazo legal: a Lei n.º 52/2019, art. 13.º, n.º 1, fixa um prazo de 60 dias, a contar do início de funções, para entregar a declaração. Só mostramos este prazo para mandatos a que a lei se aplica, ou seja, a partir da XIV Legislatura.

Quando há declaração, mostramos a mais recente que os dados publicam, com os campos tal como foram publicados. As datas ficam como foram escritas na declaração, o que às vezes é só um ano.

## Eleitos, em exercício e mandatos suspensos

Distinguimos quem foi eleito de quem esteve em funções.

- Cada deputado tem na sua página todas as legislaturas em que foi eleito, em qualquer situação, com a situação mais recente e as datas. Por exemplo: "Mandato suspenso desde 03/06/2025".
- Quem foi eleito e suspendeu o mandato antes de tomar lugar continua na lista de deputados e na pesquisa, com a indicação "Sem período em exercício registado".
- Tudo o que se conta em dias de funções (presenças, votações, tempo de serviço, número de mandatos e comparações) conta só as legislaturas em que a pessoa teve lugar.
- Um único dia em funções seguido, no mesmo dia ou no dia seguinte, da suspensão do mandato ou da renúncia não conta como lugar quando a pessoa vinha de um período sem lugar. É o que acontece aos deputados que tomam posse como membros do Governo, como em 05/06/2025. Esse dia continua na página do deputado, com as datas.
- Os dados dizem que um mandato está suspenso, mas não dizem porquê. Não indicamos o motivo de nenhuma suspensão.
- Há períodos em funções de um só dia, por exemplo na mudança de Governo em junho de 2025. São registos da AR e mantemo-los no histórico.

No topo da lista de deputados, "230 em exercício" é o número de deputados com lugar na data dos dados. O segundo número conta todas as pessoas que tiveram lugar em algum momento da legislatura, substitutos incluídos, por isso é maior do que os 230 lugares.

Nas páginas das coligações, o número principal são os deputados eleitos pelas listas da coligação, como no resultado das eleições. Até à VI Legislatura vêm das listas de eleitos publicadas; a partir da VII, dos mandatos que começam no primeiro dia da legislatura, incluindo quem suspendeu o mandato ou renunciou logo nesse dia. Um nome da lista que não conseguimos ligar a um deputado conta na mesma, sem página. Por baixo mostramos quantos deputados dos partidos da coligação, nos círculos onde a lista elegeu, estavam em funções no último dia da legislatura (ou na data dos dados, se a legislatura está em curso). A diferença vem de substituições e de mudanças de grupo.

## I Legislatura: I-A e I-B

A I Legislatura está dividida em duas partes nos dados da AR: a I-A, de 3 de junho de 1976 a 2 de janeiro de 1980, e a I-B, de 3 de janeiro a 12 de novembro de 1980. A AR publica a mesma lista de deputados nas duas partes. Para não mostrar deputados de 1976 a 1979 como se tivessem estado em funções em 1980, cada parte fica só com os períodos de mandato que se sobrepõem às suas datas. As datas publicadas não são cortadas, por isso um período que atravessa a mudança de parte aparece nas duas.

A primeira assembleia eleita, em 1975, aparece como Assembleia Constituinte.

## Sessões plenárias

Na agenda, "Sessões plenárias" conta as reuniões do Plenário no ano civil que constam das listas de presenças, sem as sessões solenes ou comemorativas. É o mesmo conjunto de reuniões usado nas taxas de presença. As reuniões extraordinárias contam.

## Lacunas conhecidas

São lacunas na fonte. Não as corrigimos à mão.

- **Presenças:** não há listas de presenças antes da VI Legislatura, além de uma reunião da V.
- **Intervenções:** sem ficheiro para a Constituinte, a I e a III; lacunas grandes na II, IV, VII, XII e XIV; a legislatura em curso tem só parte das intervenções.
- **Declarações de interesses:** só da XI à XV nos dados abertos da AR. A XVI e a XVII estão na Entidade para a Transparência e aguardam autorização de reutilização.
- **Votações:** há votações não unânimes sem o sentido de voto de cada grupo. Não existe votação nominal, deputado a deputado.
- **Biografias:** a AR só publica registo biográfico de parte dos deputados das legislaturas anteriores. A idade e a profissão só contam para quem tem registo.
- **Perguntas escritas ao Governo:** os ficheiros começam na VI Legislatura.
- **Lugares por dia, da Constituinte à VI:** a fonte não fecha alguns períodos de substituição, por isso em alguns dias há mais pessoas com lugar do que lugares. Não inferimos quem substituiu quem.

## Reportar um erro nos dados

O Fiscaliza não corrige dados à mão. Se um número estiver errado porque o dado está errado, a correção é feita no parlamento-aberto e chega ao site na versão seguinte dos dados.

Para reportar, abra um pedido com o formulário "Correção de dados" do parlamento-aberto, no GitHub:
https://github.com/rfsbraz/parlamento-aberto/issues/new?template=correcao-de-dados.yml

Use o mesmo formulário para erros no próprio site, como um rótulo errado ou uma página que não funciona.

O formulário pede o tipo de pedido, onde está o dado (a página do Fiscaliza serve), o que está errado e, se existir, uma ligação para a fonte oficial com o valor correto. O pedido é público: não escreva dados pessoais, indique só onde está o problema.

Pedidos de correção ou remoção de dados pessoais podem usar o mesmo formulário ou o reporte privado de vulnerabilidades do GitHub no parlamento-aberto, que não fica público.

Lembre-se de que o parlamento-aberto republica o que a AR publica. Se o erro estiver na própria fonte da AR, só a AR o pode corrigir.
