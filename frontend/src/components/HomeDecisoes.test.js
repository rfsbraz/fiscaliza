// Decisões do Plenário and the Government box on the home page (#264). Run with `npm test`.
import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';

const root = fileURLToPath(new URL('../..', import.meta.url));
const vite = await createServer({
  root,
  appType: 'custom',
  logLevel: 'silent',
  server: { middlewareMode: true, hmr: false, watch: null },
});
after(() => vite.close());
const { DecisoesView, GovernoView, splitDecisions } = await vite.ssrLoadModule('/src/components/HomeDecisoes.jsx');

const html = (el) => renderToStaticMarkup(React.createElement(MemoryRouter, null, el));
const text = (el) => html(el).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');

const g = (grupo, deputados = null) => ({ grupo, deputados });
const none = { favor: [], contra: [], abstencao: [], ausentes: [] };
const ini = (id, tipo, numero, titulo, autoria) => ({ id, legislatura: 'XVII', tipo, numero, titulo, autoria });

// Synthetic day, as tests/site_decisions.py.
const BODY = {
  data: '2026-10-15',
  decisoes: [
    {
      vote_id: 401, data: '2026-10-15', fase: 'Votação na generalidade', tipo: 'generalidade', resultado: 'Rejeitado', unanimidade: false,
      iniciativas: [ini(81, 'Proposta de Lei', 81, 'Iniciativa 81', 'Governo')],
      posicoes: { ...none, favor: [g('CDS-PP'), g('PSD')], contra: [g('CH'), g('PS')], abstencao: [g('IL')] },
    },
    {
      vote_id: 402, data: '2026-10-15', fase: 'Votação final global', tipo: 'final', resultado: 'Aprovado', unanimidade: true,
      iniciativas: [ini(82, 'Projeto de Lei', 82, 'Iniciativa 82', 'Cidadãos')],
      posicoes: none,
    },
    {
      vote_id: 403, data: '2026-10-15', fase: 'Votação final', tipo: 'final', resultado: 'Aprovado', unanimidade: false,
      iniciativas: [ini(83, 'Projeto de Resolução', 83, 'Iniciativa 83', 'Grupos Parlamentares')],
      posicoes: { ...none, favor: [g('PS', 1), g('PSD')], abstencao: [g('PS')] },
    },
    {
      vote_id: 404, data: '2026-10-15', fase: 'Votação final global', tipo: 'final', resultado: 'Aprovado', unanimidade: false,
      iniciativas: [ini(84, 'Proposta de Lei', 84, 'Iniciativa 84', 'Governo')],
      posicoes: { ...none, favor: [g('PSD')], contra: [g('PCP')] },
    },
  ],
  governo: { votadas: 2, rejeitadas: [401] },
};

test('the subtitle gives the day of the data and what the decisions are', () => {
  const t = text(React.createElement(DecisoesView, { body: BODY }));
  assert.match(t, /Decisões do Plenário/);
  assert.match(t, /Plenário de 15\/10\/2026, o último dia com votações nos dados/);
  assert.match(t, /3 votações finais e 1 votação na generalidade de uma proposta de lei/);
});

test('every decision is a card that links to its vote page', () => {
  const h = html(React.createElement(DecisoesView, { body: BODY }));
  for (const id of [401, 402, 403, 404]) assert.match(h, new RegExp(`href="/votacoes/${id}"`));
  assert.equal(h.match(/Ver a votação/g).length, 4);
  // The whole card is the link, so it holds the title and there is no second link inside.
  assert.match(h, /<a [^>]*href="\/votacoes\/401"[^>]*>(?:(?!<\/a>).)*Iniciativa 81(?:(?!<\/a>).)*Ver a votação/s);
});

test('a card names the initiative, its author, the result and the phase', () => {
  const t = text(React.createElement(DecisoesView, { body: BODY }));
  assert.match(t, /Proposta de Lei n\.º 81\/XVII Governo Iniciativa 81 Rejeitado · Votação na generalidade/);
});

test('positions are the published ones, a count inside a group keeps its number', () => {
  const t = text(React.createElement(DecisoesView, { body: BODY }));
  assert.match(t, /A favor CDS-PP, PSD Contra CH, PS Abstenção IL/);
  assert.match(t, /A favor PS \(1 deputado\), PSD Abstenção PS/);
});

test('a unanimous vote says so and shows no inferred groups', () => {
  const t = text(React.createElement(DecisoesView, { body: BODY }));
  assert.match(t, /Iniciativa 82 Aprovado por unanimidade · Votação final global/);
  assert.match(t, /Unanimidade\. A AR não publicou a posição de cada grupo\./);
  assert.doesNotMatch(t, /todos os grupos/);
});

test('empty positions render nothing, not a placeholder', () => {
  const t = text(React.createElement(DecisoesView, { body: BODY }));
  assert.doesNotMatch(t, /Ausentes/);
  assert.doesNotMatch(t, / - /);
  assert.doesNotMatch(t, /—/);
});

test('final votes on projetos de resolução fold under the other decisions', () => {
  const { main, resolucoes } = splitDecisions(BODY.decisoes);
  assert.deepEqual(main.map((d) => d.vote_id), [401, 402, 404]);
  assert.deepEqual(resolucoes.map((d) => d.vote_id), [403]);
  const h = html(React.createElement(DecisoesView, { body: BODY }));
  assert.match(h, /<details[^>]*>.*Mais 1 votação final de projetos de resolução neste dia.*href="\/votacoes\/403"/s);
});

test('a day with only projetos de resolução shows them as the cards', () => {
  const only = BODY.decisoes.filter((d) => d.vote_id === 403);
  const { main, resolucoes } = splitDecisions(only);
  assert.deepEqual(main.map((d) => d.vote_id), [403]);
  assert.deepEqual(resolucoes, []);
});

test('no plenary votes in the data says so', () => {
  const t = text(React.createElement(DecisoesView, { body: { data: null, decisoes: [], governo: { votadas: 0, rejeitadas: [] } } }));
  assert.match(t, /Ainda não há votações em Plenário nos dados\./);
});

test('the Government box lists the rejected Government initiatives with their vote', () => {
  const h = html(React.createElement(GovernoView, { body: BODY }));
  const t = text(React.createElement(GovernoView, { body: BODY }));
  assert.match(t, /Iniciativas do Governo rejeitadas/);
  assert.match(t, /Votações até 15\/10\/2026/);
  assert.match(t, /Proposta de Lei n\.º 81\/XVII: Iniciativa 81 · Votação na generalidade/);
  assert.match(h, /href="\/votacoes\/401"/);
  assert.match(t, /1 de 2 decisões sobre iniciativas do Governo neste dia/);
});

test('with no rejection the Government box says how many passed', () => {
  const body = { ...BODY, governo: { votadas: 2, rejeitadas: [] } };
  assert.match(text(React.createElement(GovernoView, { body })), /Nenhuma em 15\/10\/2026\. As 2 decisões sobre iniciativas do Governo neste dia foram aprovadas\./);
  const zero = { ...BODY, governo: { votadas: 0, rejeitadas: [] } };
  assert.match(text(React.createElement(GovernoView, { body: zero })), /Nenhuma em 15\/10\/2026\. Não houve decisões sobre iniciativas do Governo neste dia\./);
});
