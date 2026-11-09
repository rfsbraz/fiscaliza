// The agenda's activity figures and recent vote cards (#266). Run with `npm test` (node --test).
// West of UTC a YYYY-MM-DD read with `new Date` is midnight UTC, the evening before locally,
// so the cards are rendered in the Azores.
process.env.TZ = 'Atlantic/Azores';

import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const root = fileURLToPath(new URL('../..', import.meta.url));
const vite = await createServer({
  root,
  appType: 'custom',
  logLevel: 'silent',
  server: { middlewareMode: true, hmr: false, watch: null },
});
after(() => vite.close());
const { ActivityStats, VoteCard } = await vite.ssrLoadModule('/src/components/AgendaPage.jsx');

const text = (element) =>
  renderToStaticMarkup(element)
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ');

// Synthetic vote.
const VOTE = {
  id: 1,
  data: '2026-10-28',
  titulo: 'Iniciativa 1',
  descricao: 'Votação final global',
  resultado: 'Aprovado',
  unanime: false,
  favor: ['PSD', 'PS'],
  contra: ['CH'],
  abstencao: [],
  ausentes: [],
};

test('a vote card shows the day of the vote in the Azores too', () => {
  assert.equal(new Date().getTimezoneOffset() > 0, true, 'the test runs west of UTC');
  const card = text(React.createElement(VoteCard, { votacao: VOTE }));
  assert.match(card, /28\/10\/2026/);
  assert.doesNotMatch(card, /27\/10\/2026/);
});

test('a vote card leaves out positions no group took, with no "-" placeholder', () => {
  const card = text(React.createElement(VoteCard, { votacao: VOTE }));
  assert.match(card, /PSD, PS A favor/i);
  assert.match(card, /CH Contra/i);
  assert.doesNotMatch(card, /Abstenção|Ausentes/i);
  assert.doesNotMatch(card, / - /);
  const unanimous = text(
    React.createElement(VoteCard, { votacao: { ...VOTE, unanime: true, favor: [], contra: [] } }),
  );
  assert.doesNotMatch(unanimous, / - |A favor|Contra/i);
  assert.match(unanimous, /unanimidade/);
});

// Synthetic year.
const STATS = {
  sessoes_plenarias: { total_ano: 87, fonte: 'Sessões do Plenário nas listas de presenças' },
  votacoes: { total_ano: 1240, processuais: 212 },
  iniciativas: { apresentadas: 640 },
  assiduidade: { media_presencas: 93.1, reunioes: 87 },
};

test('the votes figure says how many were procedural and gives no approval rate', () => {
  const stats = text(React.createElement(ActivityStats, { estatisticas: STATS, periodo: '2026' }));
  assert.match(stats, /1\s?240 em plenário em 2026, 212 processuais/);
  assert.doesNotMatch(stats, /aprovadas/);
});

test('each figure names the calendar year it counts', () => {
  const stats = text(React.createElement(ActivityStats, { estatisticas: STATS, periodo: '2026' }));
  assert.match(stats, /87 em 2026/);
  assert.match(stats, /640 apresentadas em 2026/);
  assert.match(stats, /93,1\s?% média das listas de presenças de 2026/);
  assert.doesNotMatch(stats, /este ano/);
});
