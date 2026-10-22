import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';

// The head in index.html is what link previews (WhatsApp, X, Facebook) read: they don't run JS.
const root = new URL('../', import.meta.url);
const html = readFileSync(new URL('index.html', root), 'utf8');
const publicFile = (name) => new URL(`public/${name}`, root);

const meta = (attr, key) => {
  const tag = html.match(new RegExp(`<meta\\s+${attr}="${key}"[^>]*>`));
  return tag && tag[0].match(/content="([^"]*)"/)[1];
};
const link = (rel) => {
  const tag = html.match(new RegExp(`<link\\s+rel="${rel}"[^>]*>`));
  return tag && tag[0].match(/href="([^"]*)"/)[1];
};

test('Open Graph and Twitter card tags', () => {
  assert.equal(meta('property', 'og:site_name'), 'Fiscaliza');
  assert.equal(meta('property', 'og:locale'), 'pt_PT');
  assert.equal(meta('property', 'og:type'), 'website');
  assert.equal(meta('property', 'og:url'), 'https://fiscaliza.pt/');
  assert.equal(meta('property', 'og:image'), 'https://fiscaliza.pt/og-image.png');
  assert.equal(meta('property', 'og:image:width'), '1200');
  assert.equal(meta('property', 'og:image:height'), '630');
  assert.ok(meta('property', 'og:image:alt'));
  assert.equal(meta('name', 'twitter:card'), 'summary_large_image');
  assert.equal(link('canonical'), 'https://fiscaliza.pt/');
});

test('og:image is a 1200x630 PNG and stays small', () => {
  const png = readFileSync(publicFile('og-image.png'));
  assert.equal(png.subarray(1, 4).toString(), 'PNG');
  assert.equal(png.readUInt32BE(16), 1200);
  assert.equal(png.readUInt32BE(20), 630);
  assert.ok(png.length < 100_000, `${png.length} bytes`);
});

test('the favicons the head links to exist', () => {
  assert.equal(link('icon'), '/favicon.ico');
  const ico = readFileSync(publicFile('favicon.ico'));
  assert.deepEqual([...ico.subarray(0, 4)], [0, 0, 1, 0]);
  assert.ok(html.includes('<link rel="icon" type="image/svg+xml" href="/favicon.svg" />'));
  assert.ok(existsSync(publicFile('favicon.svg')));
});
