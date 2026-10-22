// The mandate line on each card of /deputados (#107). Run with `npm test` (node --test).
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
const { mandateSummary } = await vite.ssrLoadModule('/src/components/DeputadosPage.jsx');

const deputado = (career) => ({ legislatura_nome: 'XVII', career_info: { in_current_legislature: true, ...career } });

test('a seat held in the current legislature is the current mandate, suspended or not', () => {
  assert.equal(typeof mandateSummary, 'function', 'DeputadosPage exports mandateSummary');
  const seated = { is_currently_active: true, seated_in_current_legislature: true };
  assert.deepEqual(mandateSummary(deputado(seated)), ['Mandato Atual:', 'XVII']);
});

test('elected to the current legislature without ever sitting is not a mandate', () => {
  const elected = { is_currently_active: true, seated_in_current_legislature: false };
  assert.deepEqual(mandateSummary(deputado(elected)), ['Eleito na', 'XVII Legislatura']);
});

test('a former deputy keeps the latest completed mandate', () => {
  const former = {
    is_currently_active: false,
    in_current_legislature: false,
    seated_in_current_legislature: false,
    latest_completed_mandate: { legislatura: 'XVI', periodo: '2024-2025' },
  };
  assert.deepEqual(mandateSummary({ legislatura_nome: 'XVI', career_info: former }), [
    'Último mandato:',
    'XVI (2024-2025)',
  ]);
});
