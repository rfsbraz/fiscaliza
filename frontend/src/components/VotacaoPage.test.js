// The page of one plenary vote (#191). Run with `npm test` (node --test).
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
const { VotacaoView } = await vite.ssrLoadModule('/src/components/VotacaoPage.jsx');

const none = { favor: [], contra: [], abstencao: [], ausentes: [] };
const g = (grupo, deputados = null) => ({ grupo, deputados });
const VOTE = {
  id: 182922,
  legislatura: 'XVII',
  data: '2026-09-25',
  resultado: 'Rejeitado',
  unanimidade: false,
  descricao: null,
  fase: 'Votação na generalidade',
  iniciativas: [
    {
      id: 377264,
      legislatura: 'XVII',
      tipo: 'Projeto de Resolução',
      numero: 1269,
      titulo: 'Pela defesa do serviço público de televisão',
      fase: 'Votação na generalidade',
      autoria: ['PAN'],
      url: 'https://www.parlamento.pt/ActividadeParlamentar/Paginas/DetalheIniciativa.aspx?BID=377264',
    },
  ],
  posicoes: {
    favor: [g('BE'), g('L'), g('PS', 1)],
    contra: [g('CH'), g('PSD')],
    abstencao: [g('PCP'), g('PS')],
    ausentes: [],
  },
  votos_nomeados: [{ nome: 'Pedro Delgado Alves', grupo: 'PS', posicao: 'favor', id_cadastro: 4453 }],
};

const render = (vote) =>
  renderToStaticMarkup(React.createElement(MemoryRouter, null, React.createElement(VotacaoView, { vote })));
const text = (html) => html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();

test('a vote shows its initiative, result, phase and published positions', () => {
  const t = text(render(VOTE));
  assert.match(t, /Projeto de Resolução n\.º 1269\/XVII/);
  assert.match(t, /Pela defesa do serviço público de televisão/);
  assert.match(t, /Autoria: PAN/);
  assert.match(t, /Plenário de 25\/09\/2026/);
  assert.match(t, /Rejeitado · Votação na generalidade/);
  assert.match(t, /o Plenário vota o princípio/);
  assert.match(t, /A favor BE, L, PS \(1 deputado\)/);
  assert.match(t, /Contra CH, PSD/);
  assert.match(t, /Abstenção PCP, PS/);
  assert.doesNotMatch(t, /Ausentes/);
  assert.doesNotMatch(t, /por \d+ votos|margem/i);
});

test('named votes are listed as the AR names them, with a link to the deputy', () => {
  const html = render(VOTE);
  assert.match(text(html), /Pedro Delgado Alves \(PS\) votou a favor/);
  assert.match(html, /href="\/deputados\/4453"/);
});

test('the source links go to the initiative on the AR site and to the data', () => {
  const html = render(VOTE);
  assert.match(html, /href="https:\/\/www\.parlamento\.pt\/ActividadeParlamentar\/Paginas\/DetalheIniciativa\.aspx\?BID=377264"/);
  assert.match(html, /href="\/dados"/);
  assert.match(html, /href="\/agenda"/);
});

test('a unanimous vote says so and shows no group chips', () => {
  const t = text(render({ ...VOTE, resultado: 'Aprovado', unanimidade: true, posicoes: none, votos_nomeados: [] }));
  assert.match(t, /Aprovado por unanimidade/);
  assert.match(t, /não publicou a posição de cada grupo/);
  assert.doesNotMatch(t, /A favor/);
});

test('a contested vote with no positions says the source has none', () => {
  const t = text(render({ ...VOTE, posicoes: none, votos_nomeados: [] }));
  assert.match(t, /A AR não publicou as posições dos grupos nesta votação/);
  assert.match(t, /A AR não nomeou votos individuais nesta votação/);
  assert.doesNotMatch(t, / - /);
});

test('a vote with no initiative or description is titled by its day and says it has no AR link', () => {
  const t = text(render({ ...VOTE, iniciativas: [], fase: null, posicoes: none, votos_nomeados: [] }));
  assert.match(t, /Votação 182922 no Plenário de 25\/09\/2026/);
  assert.match(t, /A AR não publicou o assunto desta votação/);
  assert.match(t, /não têm ligação para esta votação no site da AR/);
});
