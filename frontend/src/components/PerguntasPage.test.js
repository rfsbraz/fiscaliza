// The per-recipient figures on /perguntas (#114). Run with `npm test` (node --test).
// Vite loads the page as the build does, and react-dom/server renders the recipient rows.
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
const { Destinatarios } = await vite.ssrLoadModule('/src/components/PerguntasPage.jsx');

const ROWS = [
  { destinatario: 'Ministra da Saúde', perguntas: 337, respondidas: 160, taxa_resposta: 47.5, mediana_dias: 62 },
  { destinatario: 'Primeiro-Ministro', perguntas: 12, respondidas: 0, taxa_resposta: 0, mediana_dias: null },
];

const render = () => renderToStaticMarkup(React.createElement(Destinatarios, { rows: ROWS }));
const text = (html) => html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
const cards = (html) => [...html.matchAll(/<li\b[^>]*>(.*?)<\/li>/gs)].map((m) => text(m[1]));

test('small screens get one card per recipient with the answer rate and the median', () => {
  assert.equal(typeof Destinatarios, 'function', 'PerguntasPage exports Destinatarios');
  const [saude, pm] = cards(render());
  assert.ok(saude && pm, 'one card per recipient');
  assert.match(saude, /^Ministra da Saúde /);
  assert.match(saude, /Perguntas 337/);
  assert.match(saude, /Respondidas 160/);
  assert.match(saude, /Taxa de resposta 47,5%/);
  assert.match(saude, /Mediana de dias até à resposta 62/);
  assert.match(pm, /Taxa de resposta 0,0%/);
  assert.match(pm, /Mediana de dias até à resposta sem dados/);
});

test('the wide table is kept for larger screens and the cards replace it on small ones', () => {
  const html = render();
  const table = html.match(/<div class="([^"]*)"[^>]*><table/);
  const list = html.match(/<ul class="([^"]*)"/);
  assert.ok(table && list, 'the table and the card list are both rendered');
  assert.deepEqual(table[1].split(' ').sort(), ['hidden', 'md:block']);
  assert.ok(list[1].split(' ').includes('md:hidden'));
  assert.equal(
    text(html.match(/<thead>(.*?)<\/thead>/s)[1]),
    'Destinatário Perguntas Respondidas Taxa de resposta Mediana de dias até à resposta',
  );
  assert.equal((html.match(/<tbody>.*?<\/tbody>/s)[0].match(/<tr/g) || []).length, ROWS.length);
});
