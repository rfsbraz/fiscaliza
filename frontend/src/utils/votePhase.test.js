import test from 'node:test';
import assert from 'node:assert/strict';
import { phaseNote } from './votePhase.js';

test('the common plenary phases get a short plain explanation', () => {
  for (const phase of [
    'Votação na generalidade',
    'Votação na especialidade',
    'Votação final global',
    'Votação final',
    'Votação global',
    'Baixa comissão especialidade',
    'Requerimento avocação plenário',
  ]) {
    const note = phaseNote(phase);
    assert.ok(note && note.length < 260, phase);
    assert.doesNotMatch(note, /—/);
  }
});

test('a phase with no explanation gets none, not a guess', () => {
  assert.equal(phaseNote('Votação Deliberação'), null);
  assert.equal(phaseNote(null), null);
  assert.equal(phaseNote(undefined), null);
});
