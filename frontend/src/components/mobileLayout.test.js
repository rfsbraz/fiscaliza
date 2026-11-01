// At 390 px nothing may push the page sideways or hide a tab behind a scroll with no scrollbar
// (#252). The renderer has no layout, so this reads the styles that decide it. Run with `npm test`.
import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import React from 'react';
import TestRenderer, { act } from 'react-test-renderer';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { PARTY_ROUTE } from '../utils/party.js';

const root = fileURLToPath(new URL('../..', import.meta.url));
const vite = await createServer({
  root,
  appType: 'custom',
  logLevel: 'silent',
  server: { middlewareMode: true, hmr: false, watch: null },
});
after(() => vite.close());
const load = async (name) => (await vite.ssrLoadModule(`/src/components/${name}.jsx`)).default;
const [PartidosPage, PartidoDetalhes, ColigacaoDetalhes, DeputadoDetalhes] = await Promise.all(
  ['PartidosPage', 'PartidoDetalhes', 'ColigacaoDetalhes', 'DeputadoDetalhes'].map(load),
);

globalThis.window ??= { addEventListener() {}, removeEventListener() {}, scrollTo() {}, location: { hash: '' } };
globalThis.document ??= { title: '', head: { appendChild() {}, removeChild() {} }, createElement: () => ({}) };

const pessoa = (i) => ({ id: i, id_cadastro: i, nome: `Pessoa ${i}`, circulo: 'Lisboa', ultima_legislatura: 'XVII', mandato_ativo: true });
const FILES = {
  '/api/partidos.json': { partidos: [{ id: 'XP', sigla: 'XP', nome: 'Partido Exemplo', num_deputados: 2 }] },
  '/api/coligacoes.json': { coligacoes: [] },
  '/api/legislaturas.json': { legislaturas: [{ numero: 'XVII', designacao: 'XVII Legislatura', ativa: true }] },
  '/api/partidos/xp/deputados.json': {
    partido: { sigla: 'XP', nome: 'Partido Exemplo' },
    deputados: [pessoa(1), pessoa(2)],
    total: 2,
    mandatos_ativos: 2,
  },
  '/api/coligacoes/ad-2024.json': { sigla: 'AD', nome: 'Aliança Democrática', deputy_count: 88, ativa: true },
  '/api/coligacoes/ad-2024/deputados.json': { deputados: [pessoa(1)] },
  '/api/coligacoes/ad-2024/partidos.json': { partidos: [] },
  '/api/deputados/1.json': {
    legislatura_atual: 'XVII',
    detalhes: {
      id_cadastro: 1,
      nome: 'Deputada',
      nome_completo: 'Deputada',
      partido: { id: 'XP', sigla: 'XP', nome: 'Partido Exemplo' },
      legislatura: { numero: 'XVII', designacao: 'XVII Legislatura', ativa: true },
      mandato: { inicio: '2025-06-03', fim: null, em_exercicio: true },
      career_info: { is_currently_active: true, is_seated: true },
      estatisticas: { iniciativas_por_tipo: [], intervencoes_parlamentares: 0, iniciativas_legislaturas: [], comparacao: {} },
      mandatos_historico: [],
    },
    atividades: {
      XVII: {
        legislatura: { numero: 'XVII', designacao: 'XVII Legislatura' },
        deputado: { id_cadastro: 1, served_in_legislature: true },
        intervencoes: [],
        iniciativas: [],
        aprovacao: [],
      },
    },
  },
};
globalThis.fetch = async (url) =>
  String(url) in FILES
    ? { ok: true, status: 200, text: async () => JSON.stringify(FILES[String(url)]) }
    : { ok: false, status: 404, text: async () => '' };

const render = async (url, path, element) => {
  let r;
  await act(async () => {
    r = TestRenderer.create(
      React.createElement(
        MemoryRouter,
        { initialEntries: [url] },
        React.createElement(Routes, null, React.createElement(Route, { path, element: React.createElement(element) })),
      ),
    );
  });
  await act(async () => new Promise((res) => setTimeout(res, 50)));
  return r;
};
const text = (node) => (typeof node === 'string' ? node : (node?.children || []).map(text).join(' '));

const tabsWrap = (r, page) => {
  const navs = r.root.findAll((n) => n.type === 'nav');
  assert.ok(navs.length > 0, `${page} has no tab bar`);
  for (const nav of navs) {
    assert.equal(nav.props.style.flexWrap, 'wrap', `${page}: the tabs that do not fit are hidden`);
    assert.notEqual(nav.props.style.overflowX, 'auto', `${page}: the tabs scroll sideways`);
  }
};

test('the statistics of /partidos fall into rows on a phone', async () => {
  const r = await render('/partidos', '/partidos', PartidosPage);
  const grid = r.root.find((n) => typeof n.type === 'string' && n.props.style?.display === 'grid' && /COLIGAÇÕES ATIVAS/.test(text(n)));
  assert.ok(!/repeat\(\d+,/.test(grid.props.style.gridTemplateColumns), 'four fixed columns at any width');
});

test('the coalition header and tabs fit a phone', async () => {
  const r = await render('/coligacoes/ad-2024#partidos', '/coligacoes/:coligacaoId', ColigacaoDetalhes);
  const row = r.root.find(
    (n) => typeof n.type === 'string' && n.props.style?.justifyContent === 'space-between' && /deputados/.test(text(n)) && /Aliança Democrática/.test(text(n)),
  );
  assert.equal(row.props.style.flexWrap, 'wrap', 'the count sits beside the name at any width');
  tabsWrap(r, 'coligação');
});

test('the party and deputy tabs wrap instead of hiding', async () => {
  tabsWrap(await render('/partidos/XP#deputados', PARTY_ROUTE, PartidoDetalhes), 'partido');
  tabsWrap(await render('/deputados/1#biografia', '/deputados/:cadId', DeputadoDetalhes), 'deputado');
});
