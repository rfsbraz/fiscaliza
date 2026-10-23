// The privacy note on /privacidade (#220). Run with `npm test` (node --test).
// Vite loads the page as the build does, and react-dom/server renders the note.
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
const { PrivacyNote } = await vite.ssrLoadModule('/src/components/Privacidade.jsx');

const html = renderToStaticMarkup(React.createElement(PrivacyNote));

test('the note renders with its title, labels and contact link', () => {
  assert.match(html, /<h1[^>]*>Privacidade<\/h1>/);
  assert.equal(html.match(/<p\b/g).length, 6, 'one paragraph per block of the note');
  for (const label of ['Contagem de visitas.', 'Erros.', 'Alojamento.', 'Tipos de letra.']) {
    assert.ok(html.includes(`<strong>${label}</strong>`), label);
  }
  assert.match(html, /<a href="mailto:rfsbraz@gmail\.com"[^>]*>rfsbraz@gmail\.com<\/a>/);
  assert.ok(!html.includes('**'), 'no markdown left in the page');
});
