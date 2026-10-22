// Browser-side answers from the static export (#90). Run with `npm test` (node --test).
import test from 'node:test';
import assert from 'node:assert/strict';
import { createStaticApi, legislatureName, slug } from './staticApi.js';

const person = (id, nome, nomeCompleto, active = true, inCurrent = active) => ({
  id_cadastro: id,
  nome,
  nome_completo: nomeCompleto,
  career_info: { is_currently_active: active, in_current_legislature: inCurrent, total_mandates: 1 },
});

const intervention = (id, tipo, data) => ({ id, tipo, data });

const FILES = {
  'deputados.json': {
    deputados: [
      person(1, 'José Sá', 'José Maria Sá'),
      person(2, 'Ana Lopes', 'Ana Conceição Lopes'),
      person(3, 'Rui Gonçalves', 'Rui Gonçalves Antunes', false),
      // Resigned in the current legislature: no longer in office, still on its list.
      person(4, 'Inês Faria', 'Inês Faria Costa', false, true),
    ],
    registos: [1, 2, 3, 4],
    filters: { active_deputies_count: 2, seated_deputies_count: 2 },
  },
  'deputados/7.json': {
    legislatura_atual: 'XVII',
    detalhes: { nome: 'Sete' },
    atividades: {
      XVII: {
        legislatura: { numero: 'XVII' },
        intervencoes: [
          intervention(5, 'Intervenção', '2026-09-18'),
          intervention(4, 'Pergunta', '2026-09-18'),
          intervention(3, 'Intervenção', '2026-09-16'),
          intervention(9, 'Declaração política', null),
        ],
      },
    },
    voting_analytics: { XVII: { legislatura: 'XVII' } },
  },
  'deputados/8.json': {
    legislatura_atual: 'Constituinte',
    atividades: { Constituinte: { intervencoes: [] } },
    voting_analytics: {},
    voting_analytics_atual: { legislatura: 'Constituinte' },
  },
  'partidos/mdp-cde/deputados.json': { partido: 'MDP/CDE' },
  'partidos/ps/voting-analytics/xvii.json': { legislatura: 'XVII' },
};

const api = (files = FILES, calls = []) =>
  createStaticApi({
    load: async (path) => {
      calls.push(path);
      if (path in files) return { ok: true, status: 200, text: JSON.stringify(files[path]) };
      return { ok: false, status: 404, text: '' };
    },
  });

test('path form matches the export: accents and slashes slugged', () => {
  assert.equal(slug('PàF'), 'paf');
  assert.equal(slug('MDP/CDE'), 'mdp-cde');
  assert.equal(slug('CDS-PP'), 'cds-pp');
  assert.equal(slug('  Ação  Nova '), 'acao-nova');
  assert.equal(legislatureName('17'), 'XVII');
  assert.equal(legislatureName('xiv'), 'XIV');
});

test('deputy search ignores case and accents and matches either name', async () => {
  const a = api();
  const jose = await a.get('deputados?active_only=false&search=jose');
  assert.deepEqual(jose.body.deputados.map((d) => d.id_cadastro), [1]);
  const conceicao = await a.get('deputados?active_only=false&search=CONCEICAO');
  assert.deepEqual(conceicao.body.deputados.map((d) => d.id_cadastro), [2]);
  assert.equal(conceicao.body.filters.total_deputy_records, 2);
  const none = await a.get('deputados?active_only=false&search=zzz');
  assert.deepEqual(none.body.deputados, []);
  assert.equal(none.body.pagination.pages, 0);
});

test('deputy list pages and filters like the API', async () => {
  const a = api();
  const page = await a.get('deputados?page=2&per_page=1&active_only=false');
  assert.deepEqual(page.body.deputados.map((d) => d.id_cadastro), [2]);
  assert.deepEqual(page.body.pagination, { page: 2, per_page: 1, total: 4, pages: 4, has_next: true, has_prev: true });
  // The default list is the current legislature, a resigned deputy included, as the API lists it.
  const active = await a.get('deputados');
  assert.deepEqual(active.body.deputados.map((d) => d.id_cadastro), [1, 2, 4]);
  assert.equal(active.body.filters.active_only, true);
});

test('interventions are filtered, sorted and paged in the browser', async () => {
  const a = api();
  const ids = async (q) => (await a.get(`deputados/7/atividades?${q}`)).body.intervencoes.map((i) => i.id);
  assert.deepEqual(await ids('legislatura=XVII'), [5, 4, 3, 9]);
  assert.deepEqual(await ids('ordenacao_intervencoes=oldest'), [3, 4, 5, 9]);
  assert.deepEqual(await ids('ordenacao_intervencoes=type'), [9, 5, 3, 4]);
  assert.deepEqual(await ids('tipo_intervencao=interven'), [5, 3]);
  assert.deepEqual(await ids('page=2&per_page=3'), [9]);
  const meta = (await a.get('deputados/7/atividades?tipo_intervencao=Pergunta&per_page=50')).body.intervention_metadata;
  assert.deepEqual(meta, { total: 1, page: 1, per_page: 50, pages: 1 });
});

test('one file per deputy, fetched once for all their endpoints', async () => {
  const calls = [];
  const a = api(FILES, calls);
  await Promise.all([
    a.get('deputados/7/detalhes'),
    a.get('deputados/7/atividades?page=1'),
    a.get('deputados/7/voting-analytics'),
  ]);
  assert.deepEqual(calls, ['deputados/7.json']);
  assert.equal((await a.get('deputados/7/voting-analytics?legislatura=17')).body.legislatura, 'XVII');
  assert.equal((await a.get('deputados/7/conflitos-interesse')).status, 404);
});

test('legislatures are looked up the way each endpoint takes them', async () => {
  const a = api();
  // Voting analytics takes "17" or a numeral in any case; with none it is the latest served.
  assert.equal((await a.get('deputados/8/voting-analytics')).body.legislatura, 'Constituinte');
  assert.equal((await a.get('deputados/8/voting-analytics?legislatura=Constituinte')).status, 404);
  // Activities take the name exactly as the data has it.
  assert.equal((await a.get('deputados/8/atividades?legislatura=Constituinte')).status, 200);
  assert.equal((await a.get('deputados/7/atividades?legislatura=17')).status, 404);
});

test('party names with slashes map to one path', async () => {
  const a = api();
  assert.equal((await a.get('partidos/MDP/CDE/deputados')).body.partido, 'MDP/CDE');
  assert.equal((await a.get('partidos/MDP%2FCDE/deputados')).body.partido, 'MDP/CDE');
  assert.equal((await a.get('partidos/PS/voting-analytics?legislatura=17')).status, 200);
});

test('a host that answers a missing file with index.html still reads as not found', async () => {
  const a = createStaticApi({ load: async () => ({ ok: true, status: 200, text: '<!doctype html><html></html>' }) });
  assert.equal((await a.get('deputados/8/detalhes')).status, 404);
});

test('the agenda says not available until S13', async () => {
  const a = api();
  assert.equal((await a.get('agenda/hoje')).body.planned, 'S13');
  assert.equal((await a.get('agenda/semana')).status, 503);
});

test('attendance is read from the deputy file, and is not found when the file has none', async () => {
  const files = { ...FILES, 'deputados/7.json': { ...FILES['deputados/7.json'], attendance: { taxa: 0.9 } } };
  assert.deepEqual((await api(files).get('deputados/7/attendance')).body, { taxa: 0.9 });
  assert.equal((await api(files).get('deputados/8/attendance')).status, 404);
  assert.equal((await api(files).get('deputados/7/attendance?legislatura=XVII')).status, 404);
});

test('requests the export does not render are not found', async () => {
  const a = api();
  assert.equal((await a.get('estatisticas?legislatura=XVI')).status, 404);
  assert.equal((await a.get('nao/existe')).status, 404);
});
