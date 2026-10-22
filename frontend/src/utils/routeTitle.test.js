import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { SITE_TITLE, routeTitle } from './routeTitle.js';

// deploy/pages.py writes each route's title into its HTML. In the browser the tab keeps it only
// on the page it was loaded for; any other route gets the site title back (or sets its own).
const landing = { path: '/deputados/2105', title: 'José Luís Carneiro (PS) · Fiscaliza' };

test('the landing route keeps the title from its HTML', () => {
  assert.equal(routeTitle(landing, '/deputados/2105'), landing.title);
});

test('another route gets the site title', () => {
  assert.equal(routeTitle(landing, '/deputados/99'), SITE_TITLE);
  assert.equal(routeTitle(landing, '/'), SITE_TITLE);
});

test('the site title is the one in index.html', () => {
  const html = readFileSync(new URL('../../index.html', import.meta.url), 'utf8');
  assert.equal(html.match(/<title>([^<]*)<\/title>/)[1], SITE_TITLE);
});
