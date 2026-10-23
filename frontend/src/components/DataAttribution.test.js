// The AR attribution line in the footer (#185: the date reads dd/mm/aaaa). Run with `npm test`.
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
const { AttributionView } = await vite.ssrLoadModule('/src/components/DataAttribution.jsx');

const render = (release) => renderToStaticMarkup(React.createElement(AttributionView, { release }));

test('the footer date reads dd/mm/aaaa', () => {
  const html = render({ source_updated: '2026-10-22', tag: 'data-2026-10-23' });
  assert.ok(html.includes('Fonte: Assembleia da República, dados abertos, atualizados a 22/10/2026.'));
  assert.ok(!html.includes('2026-10-22'));
  assert.match(html, /parlamento-aberto \(data-2026-10-23\)/);
});

test('without a release the footer keeps the source line, with no date', () => {
  const html = render(null);
  assert.ok(html.includes('Fonte: Assembleia da República, dados abertos.'));
  assert.ok(!html.includes('atualizados a'));
});
