// The status badge on each card of /deputados (#201). Run with `npm test` (node --test).
import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';

const root = fileURLToPath(new URL('../..', import.meta.url));
const vite = await createServer({
  root,
  appType: 'custom',
  logLevel: 'silent',
  server: { middlewareMode: true, hmr: false, watch: null },
});
after(() => vite.close());
const { statusBadge } = await vite.ssrLoadModule('/src/components/DeputadosPage.jsx');

const deputado = (mandateStatus, isSeated, isActive) => ({
  is_seated: isSeated,
  mandate_status: mandateStatus,
  career_info: { is_seated: isSeated, mandate_status: mandateStatus, is_currently_active: isActive },
});

test('a suspended mandate reads "Mandato suspenso", as on the deputy page', () => {
  assert.equal(typeof statusBadge, 'function', 'DeputadosPage exports statusBadge');
  assert.equal(statusBadge(deputado('Suspenso(Eleito)', false, true)), 'Mandato suspenso');
  assert.equal(statusBadge(deputado('Suspenso(Não Eleito)', false, true)), 'Mandato suspenso');
});

test('the other badges keep their labels', () => {
  assert.equal(statusBadge(deputado('Efetivo', true, true)), 'Em Exercício');
  assert.equal(statusBadge(deputado('Renunciou', false, false)), 'Renunciou');
  assert.equal(statusBadge(deputado('Suplente', false, true)), 'Ativo');
  assert.equal(statusBadge(deputado('Efetivo', false, false)), 'Inativo');
});
