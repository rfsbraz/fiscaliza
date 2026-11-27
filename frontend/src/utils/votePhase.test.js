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

test('procedural votes are described without assuming they passed', () => {
  // The page shows the note whatever the result, so it says what was voted, not what followed.
  for (const phase of ['Baixa comissão especialidade', 'Requerimento avocação plenário']) {
    assert.match(phaseNote(phase), /^Votação sobre /, phase);
  }
});
