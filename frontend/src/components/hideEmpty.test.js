// What has no data is not shown (#246). Run with `npm test` (node --test).
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
const { default: AgendaPage } = await vite.ssrLoadModule('/src/components/AgendaPage.jsx');
const { default: DeputadoDetalhes } = await vite.ssrLoadModule('/src/components/DeputadoDetalhes.jsx');

globalThis.window ??= { addEventListener() {}, removeEventListener() {}, scrollTo() {}, location: { hash: '' } };
globalThis.document ??= { title: '', head: { appendChild() {}, removeChild() {} }, createElement: () => ({}) };

const deputy = (id, extra) => ({
  legislatura_atual: 'XVII',
  detalhes: {
    id_cadastro: id,
    nome: 'Deputada',
    nome_completo: 'Deputada',
    partido: { id: 'PAN', sigla: 'PAN', nome: 'PAN' },
    legislatura: { numero: 'XVII', designacao: 'XVII Legislatura', ativa: true },
    mandato: { inicio: '2025-06-03', fim: null, em_exercicio: true },
    career_info: { is_currently_active: true, is_seated: true },
    estatisticas: { iniciativas_por_tipo: [], intervencoes_parlamentares: 1, iniciativas_legislaturas: [], comparacao: {} },
    mandatos_historico: [],
    ...extra,
  },
  atividades: {
    XVII: {
      legislatura: { numero: 'XVII', designacao: 'XVII Legislatura' },
      deputado: { id_cadastro: id, served_in_legislature: true },
      intervencoes: [{ id: 1, tipo: 'Intervenção', data: '2026-09-18', url_video: null, publicacao: {} }],
      iniciativas: [],
      aprovacao: [],
    },
  },
});

const FILES = {
  '/api/votacoes/recentes/5.json': { resumo: { periodo: 'últimos 30 dias' }, votacoes: [] },
  '/api/estatisticas/atividade.json': { estatisticas: {} },
  '/api/deputados/1.json': deputy(1, { profissao: 'Jurista' }),
  '/api/deputados/2.json': deputy(2, {}),
};
const errors = [];
console.error = (...args) => errors.push(args.join(' '));
globalThis.fetch = async (url) =>
  String(url) in FILES
    ? { ok: true, status: 200, text: async () => JSON.stringify(FILES[String(url)]) }
    : { ok: false, status: 404, text: async () => '' };

const render = async (url, path, element) => {
  let renderer;
  await act(async () => {
    renderer = TestRenderer.create(
      React.createElement(
        MemoryRouter,
        { initialEntries: [url] },
        React.createElement(Routes, null, React.createElement(Route, { path, element: React.createElement(element) })),
      ),
    );
  });
  await act(async () => new Promise((r) => setTimeout(r, 50)));
  const text = (node) => (typeof node === 'string' ? node : (node?.children || []).map(text).join(' '));
  return text({ children: [].concat(renderer.toJSON() || []) }).replace(/\s+/g, ' ');
};

test('the agenda shows no Hoje or Esta Semana tab while the agenda has no data', async () => {
  errors.length = 0;
  const page = await render('/agenda', '/agenda', AgendaPage);
  assert.ok(!/Esta Semana/.test(page), 'Esta Semana tab is shown');
  assert.ok(!/\bHoje\b/.test(page), 'Hoje tab is shown');
  assert.ok(!/indisponível/.test(page), 'an unavailable panel is shown');
  assert.ok(/últimos 30 dias/.test(page), 'the votes tab is not the one open');
  assert.deepEqual(errors.filter((e) => /agenda/.test(e)), []);
});

test('the biographical dossier shows only the sections with records', async () => {
  const page = await render('/deputados/1#biografia', '/deputados/:cadId', DeputadoDetalhes);
  assert.ok(/Dossier Biográfico/.test(page));
  assert.ok(/Percurso Profissional/.test(page));
  assert.ok(!/Sem registos/.test(page), '"Sem registos" is shown');
  assert.ok(!/Habilitações Académicas/.test(page), 'an empty section is shown');
});

test('no dossier at all when nothing is on record', async () => {
  const page = await render('/deputados/2#biografia', '/deputados/:cadId', DeputadoDetalhes);
  assert.ok(!/Dossier Biográfico/.test(page), 'an empty dossier is shown');
});

test('no video count when no intervention has a video', async () => {
  const page = await render('/deputados/1#intervencoes', '/deputados/:cadId', DeputadoDetalhes);
  assert.ok(/Total intervenções/.test(page), 'the interventions summary is not on the page');
  assert.ok(!/com vídeo/.test(page), '"0 com vídeo" is shown');
});
