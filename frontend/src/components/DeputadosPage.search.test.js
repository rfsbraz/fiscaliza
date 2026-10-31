// The search on /deputados (#248). Run with `npm test` (node --test).
import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import React from 'react';
import TestRenderer, { act } from 'react-test-renderer';
import { MemoryRouter } from 'react-router-dom';

const root = fileURLToPath(new URL('../..', import.meta.url));
const vite = await createServer({
  root,
  appType: 'custom',
  logLevel: 'silent',
  server: { middlewareMode: true, hmr: false, watch: null },
});
after(() => vite.close());
const { default: DeputadosPage } = await vite.ssrLoadModule('/src/components/DeputadosPage.jsx');

const person = (id, nome, parties) => ({
  id_cadastro: id,
  deputado_id: id,
  nome,
  nome_completo: nome,
  partido_sigla: parties[0],
  career_info: { is_currently_active: true, total_mandates: 1, parties_served: parties },
});
const INDEX = {
  deputados: [person(1, 'José Sá', ['PSD']), person(2, 'Ana Lopes', ['CH']), person(3, 'Rui Melo', ['PS'])],
  registos: [1, 2, 3],
  grupos: { PSD: ['Partido Social Democrata'], CH: ['Chega'], PS: ['Partido Socialista'] },
  filters: { active_deputies_count: 3, seated_deputies_count: 3 },
};
globalThis.fetch = async (url) =>
  String(url) === '/api/deputados.json'
    ? { ok: true, status: 200, text: async () => JSON.stringify(INDEX) }
    : { ok: false, status: 404, text: async () => '' };

const text = (node) => (typeof node === 'string' ? node : (node?.children || []).map(text).join(' '));
const settle = () => act(async () => new Promise((r) => setTimeout(r, 30)));

const page = async () => {
  let r;
  await act(async () => {
    r = TestRenderer.create(React.createElement(MemoryRouter, null, React.createElement(DeputadosPage)));
  });
  await settle();
  const read = () => text({ children: [].concat(r.toJSON() || []) }).replace(/\s+/g, ' ');
  const search = async (value) => {
    await act(async () => r.root.findByType('input').props.onChange({ target: { value } }));
    await settle();
    return read();
  };
  return { read, search };
};

test('a party name or acronym finds its deputies', async () => {
  const p = await page();
  const chega = await p.search('Chega');
  assert.ok(/Ana Lopes/.test(chega) && !/José Sá/.test(chega), 'Chega does not list its deputy');
  const psd = await p.search('PSD');
  assert.ok(/José Sá/.test(psd) && !/Rui Melo/.test(psd), 'PSD does not list its deputy');
});

test('no match says so and keeps the totals of the header', async () => {
  const p = await page();
  assert.ok(/3 pessoas únicas · 6 mandatos totais/.test(p.read()));
  const none = await p.search('zzz');
  assert.ok(/Nenhum deputado corresponde a «zzz»/.test(none), 'no empty state');
  assert.ok(/3 pessoas únicas · 6 mandatos totais/.test(none), 'the header changed with the search');
  assert.ok(!/A mostrar todos os deputados/.test(none), 'still says it shows everyone');
});

test('a search says how many it found', async () => {
  const p = await page();
  assert.ok(/1 resultado para «Chega»/.test(await p.search('Chega')));
});
