// Party links and the party page for a sigla with no data (#242). Run with `npm test` (node --test).
import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import React from 'react';
import TestRenderer, { act } from 'react-test-renderer';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

const root = fileURLToPath(new URL('../..', import.meta.url));
const vite = await createServer({
  root,
  appType: 'custom',
  logLevel: 'silent',
  server: { middlewareMode: true, hmr: false, watch: null },
});
after(() => vite.close());
const { default: PartidoDetalhes } = await vite.ssrLoadModule('/src/components/PartidoDetalhes.jsx');
const { partyPath, PARTY_ROUTE } = await vite.ssrLoadModule('/src/utils/party.js');

globalThis.window ??= { addEventListener() {}, removeEventListener() {} };
globalThis.document ??= { title: '', head: { appendChild() {}, removeChild() {} }, createElement: () => ({}) };

const requested = [];
const serve = (files) => {
  globalThis.fetch = async (url) => {
    requested.push(String(url));
    const body = files[String(url)];
    return body === undefined
      ? { ok: false, status: 404, text: async () => '' }
      : { ok: true, status: 200, text: async () => JSON.stringify(body) };
  };
};

const render = async (url) => {
  let renderer;
  await act(async () => {
    renderer = TestRenderer.create(
      React.createElement(
        MemoryRouter,
        { initialEntries: [url] },
        React.createElement(Routes, null, React.createElement(Route, { path: PARTY_ROUTE, element: React.createElement(PartidoDetalhes) })),
      ),
    );
  });
  await act(async () => new Promise((r) => setTimeout(r, 20)));
  const text = (node) => (typeof node === 'string' ? node : (node.children || []).map(text).join(''));
  return text(renderer.toJSON() ? { children: [].concat(renderer.toJSON()) } : { children: [] });
};

test('independents and non-registered deputies get no party link', () => {
  assert.equal(partyPath('Indep'), null);
  assert.equal(partyPath('Ninsc'), null);
  assert.equal(partyPath(null), null);
});

test('party links keep the slash of MDP/CDE, as the sitemap does, and encode the rest', () => {
  assert.equal(partyPath('PS'), '/partidos/PS');
  assert.equal(partyPath('MDP/CDE'), '/partidos/MDP/CDE');
  assert.equal(partyPath('A B'), '/partidos/A%20B');
});

test('a party with no data shows the 404 page, not the raw error', async () => {
  serve({});
  const text = await render('/partidos/xyz');
  assert.match(text, /Página não encontrada/);
  assert.doesNotMatch(text, /erro 404/);
});

test('/partidos/MDP/CDE opens the MDP/CDE page', async () => {
  requested.length = 0;
  serve({
    '/api/partidos/mdp-cde/deputados.json': {
      partido: { sigla: 'MDP/CDE', nome: 'Movimento Democrático Português' },
      deputados: [],
      total: 0,
    },
  });
  const text = await render('/partidos/MDP/CDE');
  assert.ok(requested.includes('/api/partidos/mdp-cde/deputados.json'), `asked for ${requested}`);
  assert.doesNotMatch(text, /Página não encontrada/);
});
