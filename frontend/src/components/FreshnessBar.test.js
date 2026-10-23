// The data freshness bar under the navigation (#185). Run with `npm test` (node --test).
// Vite loads the bar as the build does, and react-dom/server renders each state.
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
const { FreshnessBarView, MAX_DAYS } = await vite.ssrLoadModule('/src/components/FreshnessBar.jsx');
const { createHealthLoader } = await vite.ssrLoadModule('/src/config/health.js');

const render = (props) =>
  renderToStaticMarkup(React.createElement(MemoryRouter, null, React.createElement(FreshnessBarView, props)));
const text = (html) => html.replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim();
const part = (html, cls) => text(html.match(new RegExp(`<span class="${cls}">(.*?)</span>(?=<span class="freshness-|</p>)`, 's'))[1]);

test('fresh data: the date, how long ago, and the methodology link on desktop only', () => {
  const html = render({ sourceUpdated: '2026-10-22', today: '2026-10-23' });
  assert.equal(part(html, 'freshness-long'), 'Dados da Assembleia da República atualizados a 22/10/2026 (ontem). Como atualizamos');
  assert.equal(part(html, 'freshness-short'), 'Dados da AR atualizados a 22/10/2026 (ontem).');
  assert.match(html, /<a href="\/metodologia"[^>]*>Como atualizamos<\/a>/);
  assert.ok(!html.includes('atrasada'));
  assert.match(html, /data-stale="false"/);
});

test('the bar turns amber only after more than 7 days', () => {
  assert.equal(MAX_DAYS, 7, 'same limit as the daily freshness check (#179)');
  const seven = render({ sourceUpdated: '2026-10-16', today: '2026-10-23' });
  assert.match(seven, /data-stale="false"/);
  assert.match(text(seven), /\(há 7 dias\)/);
  const stale = render({ sourceUpdated: '2026-10-12', today: '2026-10-23' });
  assert.match(stale, /data-stale="true"/);
  assert.equal(
    part(stale, 'freshness-long'),
    'Dados da Assembleia da República atualizados a 12/10/2026 (há 11 dias). A atualização diária está atrasada. Como atualizamos',
  );
  assert.equal(part(stale, 'freshness-short'), 'Dados da AR atualizados a 12/10/2026 (há 11 dias). Atualização atrasada.');
});

test('no date, or a date that does not parse, renders no bar', () => {
  assert.equal(render({ sourceUpdated: null, today: '2026-10-23' }), '');
  assert.equal(render({ sourceUpdated: '22/10/2026', today: '2026-10-23' }), '');
});

test('a failed health.json fetch gives no release, so the bar is hidden', async () => {
  const load = createHealthLoader(() => Promise.reject(new Error('Não foi possível carregar os dados (erro 503).')));
  assert.equal(await load(), null);
  const bad = createHealthLoader(() => Promise.resolve(new Response('not json')));
  assert.equal(await bad(), null);
});

test('the bar and the footer share one health.json fetch', async () => {
  let calls = 0;
  const load = createHealthLoader(() => {
    calls += 1;
    return Promise.resolve(Response.json({ status: 'healthy', data: { source_updated: '2026-10-22', tag: 'data-2026-10-23' } }));
  });
  const [a, b] = await Promise.all([load(), load()]);
  assert.equal(calls, 1);
  assert.equal(a, b);
  assert.equal(a.source_updated, '2026-10-22');
});
