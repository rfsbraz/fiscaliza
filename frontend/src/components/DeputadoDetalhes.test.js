// The header's mandate line on /deputados/:id (#171). Run with `npm test` (node --test).
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
const { mandateLine } = await vite.ssrLoadModule('/src/components/DeputadoDetalhes.jsx');

const mandato = (situacao, inicio, fim, situacaoInicio = null, situacaoFim = null) => ({
  situacao,
  inicio,
  fim,
  situacao_inicio: situacaoInicio,
  situacao_fim: situacaoFim,
});

test('a seat that ended says when it ended', () => {
  assert.equal(typeof mandateLine, 'function', 'DeputadoDetalhes exports mandateLine');
  // Resigned on 2026-01-01: seated from 2025-06-03 to 2025-12-31.
  const resigned = mandato('Renunciou', '2025-06-03', '2025-12-31', '2026-01-01');
  assert.equal(mandateLine(resigned, false, 'XVII'), 'Mandato de 03/06/2025 a 31/12/2025');
});

test('a seat held now, a suspended mandate and an election without a seat keep their lines', () => {
  assert.equal(mandateLine(mandato('Efetivo', '2025-06-03', '2026-10-21'), true, 'XVII'), 'Mandato desde 03/06/2025');
  assert.equal(
    mandateLine(mandato('Suspenso(Eleito)', null, null, '2025-06-03'), false, 'XVII'),
    'Mandato suspenso desde 03/06/2025',
  );
  assert.equal(mandateLine(mandato('Suspenso(Eleito)', null, null), false, 'XVII'), 'Eleito na XVII Legislatura');
});
