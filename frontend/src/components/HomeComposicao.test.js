// The composition strip and the state of the sources on the home page (#265). Run with `npm test`.
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
const { ComposicaoView, EstadoFontesView } = await vite.ssrLoadModule('/src/components/HomeComposicao.jsx');

const render = (el) =>
  renderToStaticMarkup(React.createElement(MemoryRouter, null, el)).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');

// Synthetic figures.
const COMPOSICAO = {
  data: '2026-10-19',
  legislatura: 'XVII',
  lugares: 12,
  substituicoes_temporarias: 3,
  governo: { nome: 'Governo de teste', fonte: 'https://example.org/governo' },
  grupos: [
    { sigla: 'PSD', nome: 'Partido A', deputados: 5, apoia_governo: true },
    { sigla: 'CDS-PP', nome: 'Partido B', deputados: 1, apoia_governo: true },
    { sigla: 'PS', nome: 'Partido C', deputados: 4, apoia_governo: false },
    { sigla: 'L', nome: 'Partido D', deputados: 2, apoia_governo: false },
  ],
  mudancas: {
    desde: '2026-09-20',
    ate: '2026-10-19',
    itens: [
      { data: '2026-10-01', cadastro_id: 500, nome: 'Deputado 500', grupo: 'PS', evento: 'inicio', situacao: 'Efetivo Temporário' },
      { data: '2026-09-30', cadastro_id: 150, nome: 'Deputado 150', grupo: 'PS', evento: 'fim', situacao: 'Efetivo' },
    ],
  },
};

const FONTES = {
  tag: 'data-2026-10-20',
  source_updated: '2026-10-19',
  conjuntos: [
    { nome: 'Votações em Plenário', dados_ate: '2026-10-15' },
    { nome: 'Intervenções', dados_ate: '2026-09-18' },
    { nome: 'Mandatos', dados_ate: null },
  ],
  lacunas: [{ tipo: 'atraso', conjunto: 'Intervenções', texto: 'A AR publicou intervenções até 18/09/2026.' }],
};

test('the strip gives the seats, the government groups first and the substitutes', () => {
  const text = render(React.createElement(ComposicaoView, { composicao: COMPOSICAO }));
  assert.match(text, /Em funções a 19\/10\/2026 · 12 lugares/);
  assert.match(text, /Apoiam o Governo: PSD 5, CDS-PP 1/);
  assert.match(text, /Outros grupos: PS 4, L 2/);
  assert.match(text, /3 lugares ocupados por substitutos temporários/);
  assert.doesNotMatch(text, /maioria|Oposição|Fragmentação/i);
});

test('each change is a start or an end of a mandate, with its own date', () => {
  const text = render(React.createElement(ComposicaoView, { composicao: COMPOSICAO }));
  assert.match(text, /Mudanças de mandato de 20\/09\/2026 a 19\/10\/2026/);
  assert.match(text, /01\/10\/2026 · Deputado 500 \(PS\) começa funções \(Efetivo Temporário\)/);
  assert.match(text, /30\/09\/2026 · Deputado 150 \(PS\) termina funções \(Efetivo\)/);
});

test('no changes says so', () => {
  const composicao = { ...COMPOSICAO, mudancas: { ...COMPOSICAO.mudancas, itens: [] } };
  assert.match(render(React.createElement(ComposicaoView, { composicao })), /Nenhuma mudança de mandato registada/);
});

test('without a government on record there is no government label', () => {
  const composicao = { ...COMPOSICAO, governo: null, grupos: COMPOSICAO.grupos.map((g) => ({ ...g, apoia_governo: false })) };
  const text = render(React.createElement(ComposicaoView, { composicao }));
  assert.doesNotMatch(text, /Apoiam o Governo/);
  assert.match(text, /Grupos: PSD 5, CDS-PP 1, PS 4, L 2/);
});

test('the sources list a date per dataset and the gaps as coverage', () => {
  const text = render(React.createElement(EstadoFontesView, { fontes: FONTES }));
  assert.match(text, /Votações em Plenário dados até 15\/10\/2026/);
  assert.match(text, /Intervenções dados até 18\/09\/2026/);
  assert.match(text, /Mandatos sem data/);
  assert.match(text, /A AR publicou intervenções até 18\/09\/2026\./);
  assert.match(text, /lacunas de cobertura dos dados, não problemas políticos/);
  assert.match(text, /data-2026-10-20/);
});
