// One number per concept on /deputados/:id, each with its scope (#244). Run with `npm test` (node --test).
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
const { default: DeputadoDetalhes } = await vite.ssrLoadModule('/src/components/DeputadoDetalhes.jsx');

globalThis.window ??= { addEventListener() {}, removeEventListener() {}, scrollTo() {}, location: { hash: '' } };
globalThis.document ??= { title: '', head: { appendChild() {}, removeChild() {} }, createElement: () => ({}) };

const signing = { grupo: 300, restrita: 0, outros_grupos: 3 };
const record = (legislatura, aberta) => ({ legislatura, aberta, assinatura: signing, aprovacao: [] });

// 60 interventions in XVII: the 55 newest are "Intervenção", the 5 oldest "Pergunta", so the
// first page of 50 holds no Pergunta at all.
const interventions = Array.from({ length: 60 }, (_, i) => ({
  id: i + 1,
  tipo: i < 55 ? 'Intervenção' : 'Pergunta',
  data: `2026-${String(9 - Math.floor(i / 10)).padStart(2, '0')}-${String(28 - (i % 10)).padStart(2, '0')}`,
  publicacao: {},
}));

const BUNDLE = {
  legislatura_atual: 'XVII',
  detalhes: {
    id_cadastro: 7,
    nome: 'Deputada Sete',
    nome_completo: 'Deputada Sete',
    partido: { id: 'PAN', sigla: 'PAN', nome: 'PAN' },
    circulo: 'Lisboa',
    legislatura: { numero: 'XVII', designacao: 'XVII Legislatura', ativa: true },
    legislatura_numero: 'XVII',
    mandato: { inicio: '2025-06-03', fim: null, situacao: 'Efetivo', em_exercicio: true },
    is_seated: true,
    career_info: { is_currently_active: true, is_seated: true },
    estatisticas: {
      iniciativas_por_tipo: [],
      intervencoes_parlamentares: 1320,
      tempo_servico_anos: 7,
      total_mandatos: 2,
      legislaturas_servidas: 'XVI, XVII',
      iniciativas_legislaturas: [record('XVII', true), record('XVI', false)],
      // Still in older files: the page must not chart it.
      evolucao_legislaturas: [
        { legislatura: 'XVII', iniciativas: 300, intervencoes: 60 },
        { legislatura: 'XVI', iniciativas: 250, intervencoes: 272 },
      ],
      comparacao: {},
    },
    mandatos_historico: [
      { legislatura_numero: 'XVII', legislatura_nome: 'XVII Legislatura', partido_sigla: 'PAN', is_current: true },
      { legislatura_numero: 'XVI', legislatura_nome: 'XVI Legislatura', partido_sigla: 'PAN', is_current: false },
    ],
  },
  atividades: {
    XVII: {
      legislatura: { numero: 'XVII', designacao: 'XVII Legislatura' },
      deputado: { id_cadastro: 7, served_in_legislature: true },
      intervencoes: interventions,
      iniciativas: [],
      aprovacao: [],
    },
  },
};

globalThis.fetch = async (url) =>
  String(url) === '/api/deputados/7.json'
    ? { ok: true, status: 200, text: async () => JSON.stringify(BUNDLE) }
    : { ok: false, status: 404, text: async () => '' };

const render = async (url) => {
  let renderer;
  await act(async () => {
    renderer = TestRenderer.create(
      React.createElement(
        MemoryRouter,
        { initialEntries: [url] },
        React.createElement(
          Routes,
          null,
          React.createElement(Route, { path: '/deputados/:cadId', element: React.createElement(DeputadoDetalhes) }),
        ),
      ),
    );
  });
  await act(async () => new Promise((r) => setTimeout(r, 50)));
  const text = (node) => (typeof node === 'string' ? node : (node?.children || []).map(text).join(' '));
  return text({ children: [].concat(renderer.toJSON() || []) }).replace(/\s+/g, ' ');
};

const page = await render('/deputados/7#intervencoes');
const has = (re) => assert.ok(re.test(page), `no ${re} on the page`);
const hasNot = (re) => assert.ok(!re.test(page), `${re} is on the page`);

test('the career count and the legislature count each say what they cover', () => {
  has(/1[\s.]?320 em plenário, em todos os mandatos/);
  has(/60 intervenções na XVII Legislatura/);
  hasNot(/intervenções nesta legislatura/);
});

test('"Por tipo" counts every intervention of the legislature, not the 50 loaded', () => {
  has(/Intervenção\s*:\s*55/);
  has(/Pergunta\s*:\s*5\b/);
});

test('no chart that adds initiatives to interventions', () => {
  hasNot(/Evolução por Legislatura/);
});

test('the latest legislature is shown once; the per-legislature block keeps the earlier ones', () => {
  assert.equal(page.match(/XVII Legislatura \(em curso\)/g)?.length, 1);
  has(/XVI Legislatura/);
});
