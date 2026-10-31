// The three deputy counts on the home page (#254). Run with `npm test` (node --test).
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
const { default: Dashboard } = await vite.ssrLoadModule('/src/components/Dashboard.jsx');

// Synthetic figures: 1230 seated, 1256 who held a seat, 1283 on the lists.
const STATS = {
  totais: {
    deputados: 1230,
    deputados_em_exercicio: 1230,
    seated_deputies: 1230,
    deputados_eleitos: 1256,
    deputados_listados: 1283,
    partidos: 2,
    circulos: 1,
  },
  distribuicao_partidos: [
    { id: 'PSD', sigla: 'PSD', nome: 'Partido A', deputados: 1000 },
    { id: 'PS', sigla: 'PS', nome: 'Partido B', deputados: 230 },
  ],
  distribuicao_circulos: [{ circulo: 'Lisboa', deputados: 1230 }],
  legislatura: { numero: 'XVII', data_referencia: '2026-10-29' },
};

const render = (stats) =>
  renderToStaticMarkup(React.createElement(MemoryRouter, null, React.createElement(Dashboard, { stats })))
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ');

test('the home page says what each of the three deputy counts is', () => {
  const text = render(STATS);
  assert.match(text, /1\s?230 deputados em exercício na data dos dados/);
  assert.match(text, /1\s?256 pessoas tiveram lugar em algum momento da legislatura, substitutos incluídos/);
  assert.match(text, /1\s?283 estão nas listas da legislatura/);
  assert.match(text, /suspendeu o mandato antes de tomar lugar/);
});

test('with no lists count the note leaves that sentence out', () => {
  const { deputados_listados, ...totais } = STATS.totais;
  const text = render({ ...STATS, totais });
  assert.match(text, /pessoas tiveram lugar em algum momento da legislatura/);
  assert.doesNotMatch(text, /nas listas da legislatura/);
});
