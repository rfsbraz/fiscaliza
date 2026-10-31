// The deputies tab of /partidos/:id shows one page at a time (#250). Run with `npm test` (node --test).
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

const TOTAL = 120;
const deputado = (i) => ({
  id: i,
  id_cadastro: i,
  nome: `Pessoa ${String(i).padStart(3, '0')}`,
  circulo: i % 2 ? 'Lisboa' : 'Porto',
  picture_url: `/foto/${i}.jpg`,
  ultima_legislatura: 'XVII',
  mandato_ativo: i <= 10,
});
const PARTY = {
  partido: { sigla: 'XP', nome: 'Partido Exemplo' },
  deputados: Array.from({ length: TOTAL }, (_, i) => deputado(i + 1)),
  total: TOTAL,
  mandatos_ativos: 10,
  historico: { periodo_atividade: '1976-2026', total_legislaturas: 17, total_circulos: 2 },
};
globalThis.fetch = async (url) =>
  String(url) === '/api/partidos/xp/deputados.json'
    ? { ok: true, status: 200, text: async () => JSON.stringify(PARTY) }
    : { ok: false, status: 404, text: async () => '' };

// The page follows hashchange on window; the renderer has no DOM.
globalThis.window ??= { addEventListener() {}, removeEventListener() {} };

const text = (node) => (typeof node === 'string' ? node : (node?.children || []).map(text).join(' '));

const render = async () => {
  let r;
  await act(async () => {
    r = TestRenderer.create(
      React.createElement(
        MemoryRouter,
        { initialEntries: ['/partidos/XP#deputados'] },
        React.createElement(Routes, null, React.createElement(Route, { path: '/partidos/:partidoId', element: React.createElement(PartidoDetalhes) })),
      ),
    );
  });
  await act(async () => new Promise((res) => setTimeout(res, 30)));
  const read = () => text({ children: [].concat(r.toJSON() || []) }).replace(/\s+/g, ' ');
  const names = () => read().match(/Pessoa \d{3}/g) || [];
  return { r, read, names };
};

test('the deputies tab draws one page, not every deputy of the party', async () => {
  const { read, names } = await render();
  const shown = new Set(names());
  assert.ok(shown.has('Pessoa 001'), 'the first deputy is missing');
  assert.ok(shown.size <= 50, `draws ${shown.size} deputies at once`);
  assert.ok(/Página 1 de \d/.test(read()), 'no pagination');
  assert.ok(/Histórico completo de 120 deputados/.test(read()), 'the header stopped counting everyone');
  assert.ok(/Lisboa 60/.test(read()) && /Porto 60/.test(read()), 'the distribution stopped counting everyone');
});

test('the next page shows the next deputies', async () => {
  const { r, names } = await render();
  const first = new Set(names()).size;
  const next = r.root.findAll((n) => n.type === 'button' && text(n) === 'Próxima')[0];
  await act(async () => next.props.onClick());
  const shown = new Set(names());
  assert.ok(shown.has(`Pessoa ${String(first + 1).padStart(3, '0')}`), 'the second page does not follow the first');
  assert.ok(!shown.has('Pessoa 001'), 'the second page still shows the first deputy');
});

test('photos load lazily', async () => {
  const { r } = await render();
  const imgs = r.root.findAllByType('img');
  assert.ok(imgs.length > 0 && imgs.every((i) => i.props.loading === 'lazy'), 'photos load eagerly');
});
