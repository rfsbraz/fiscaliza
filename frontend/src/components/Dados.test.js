// The download page, /dados (#186). Run with `npm test` (node --test).
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
const { DadosView, GROUPS, fileSize, groupSets } = await vite.ssrLoadModule('/src/components/Dados.jsx');

const TAG = 'data-2026-10-23';
const DL = `https://github.com/rfsbraz/parlamento-aberto/releases/download/${TAG}/`;
const file = (nome, bytes, published) => ({ nome, bytes, url: published ? DL + nome : null });
const set = (nome, linhas, published, cc = true) => ({
  nome,
  linhas,
  licenca: cc ? 'CC BY 4.0' : 'Dados da Entidade para a Transparência, fora da licença dos marts',
  cc_by: cc,
  parquet: file(`${nome}.parquet`, 2_400_000, published),
  csv: file(`${nome}.csv.gz`, 3_100_000, published),
});
const dados = (published) => ({
  tag: TAG,
  source_updated: '2026-10-22',
  publicado: published,
  release_url: published ? `https://github.com/rfsbraz/parlamento-aberto/releases/tag/${TAG}` : null,
  manifest: file('manifest.json', 41_000, published),
  conjuntos: [set('deputies', 7441, published), set('interests', 2782, published, false), set('new_mart', 3, published)],
  total_parquet: 7_200_000,
  total_csv: 9_300_000,
});
const render = (d) => renderToStaticMarkup(React.createElement(DadosView, { dados: d }));
const text = (html) => html.replace(/<style>.*?<\/style>/s, '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');

test('a published release links every file, the manifest and the release', () => {
  const html = render(dados(true));
  for (const name of ['deputies.parquet', 'deputies.csv.gz', 'interests.parquet', 'interests.csv.gz', 'manifest.json']) {
    assert.ok(html.includes(`href="${DL}${name}"`), name);
  }
  assert.match(html, /href="https:\/\/github.com\/rfsbraz\/parlamento-aberto\/releases\/tag\/data-2026-10-23"/);
  const t = text(html);
  assert.match(t, /Release data-2026-10-23/);
  assert.match(t, /atualizados a 22\/10\/2026/);
  assert.match(t, /3 conjuntos/);
  assert.match(t, /7,2 MB em Parquet e 9,3 MB em CSV/);
  assert.ok(!t.includes('ainda não está publicada'));
});

test('a local build of the pin lists the files with no links and says so', () => {
  const html = render(dados(false));
  assert.ok(!html.includes('/releases/download/') && !html.includes('/releases/tag/'));
  assert.match(text(html), /ainda não está publicada no GitHub/);
  assert.match(text(html), /Parquet 2,4 MB/);
});

test('sets outside the CC BY 4.0 carry the badge and the EpT note', () => {
  const html = render(dados(true));
  const interests = html.match(/data-set="interests".*?<\/code>/s)[0];
  assert.match(interests, /Fora da CC BY 4.0/);
  assert.ok(!html.match(/data-set="deputies".*?<\/code>/s)[0].includes('Fora da CC BY'));
  assert.match(text(html), /2 dos 3 conjuntos estão sob a CC BY 4.0/);
  const note = text(html);
  assert.ok(note.includes('com indicação da Entidade para a Transparência (EpT) como fonte'));
  assert.ok(note.includes('Lei n.º 52/2019, art. 15.º, n.º 1, e da Lei n.º 26/2016 (LADA), art. 21.º, n.º 1'));
  assert.ok(note.includes('Fica excluído apenas o NIF dos titulares.'));
  assert.ok(!note.includes('rendimentos e património'));
  assert.ok(!note.includes('filiações associativas'));
  assert.ok(!note.includes('não entram nos ficheiros publicados'));
});

test('groups follow the page order, and a set the page does not know goes last', () => {
  const groups = groupSets(dados(true).conjuntos);
  assert.deepEqual(
    groups.map(([title, items]) => [title, items.map((s) => s.nome)]),
    [
      ['Deputados e mandatos', ['deputies']],
      ['Interesses declarados', ['interests']],
      ['Outros conjuntos', ['new_mart']],
    ],
  );
  assert.equal(groups[0][1][0].descricao, 'Deputados, um por registo da AR');
  // Every set of the current release has a description.
  assert.equal(GROUPS.flatMap(([, items]) => items).length, 24);
});

test('sizes read like the release page', () => {
  assert.equal(fileSize(41_000), '41 kB');
  assert.equal(fileSize(400), '1 kB');
  assert.equal(fileSize(12_345_678), '12,3 MB');
  assert.equal(fileSize(null), '');
});
