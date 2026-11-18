import test from 'node:test';
import assert from 'node:assert/strict';
import { contrastRatio, labelColor } from './contrast.js';
import { partidoCores } from '../styles/tokens.js';

test('contrast ratio follows WCAG relative luminance', () => {
  assert.equal(contrastRatio('#FFFFFF', '#000000').toFixed(2), '21.00');
  assert.equal(contrastRatio('#FFFFFF', '#FF6B35').toFixed(2), '2.84');
  assert.equal(contrastRatio('#FFFFFF', '#E91E63').toFixed(2), '4.35');
});

test('labels on every party colour reach 4.5:1', () => {
  assert.equal(labelColor('#1565C0'), '#FFFFFF');
  assert.equal(labelColor('#FF6B35'), '#000000');
  assert.equal(labelColor('#E91E63'), '#000000');
  for (const bg of [...Object.values(partidoCores), '#78716C']) {
    assert.ok(contrastRatio(labelColor(bg), bg) >= 4.5, bg);
  }
});
