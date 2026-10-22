import test from 'node:test';
import assert from 'node:assert/strict';
import { formatNumber, formatDecimal, formatPercent, legislatureName, plural, seatsNote, coalitionScope } from './format.js';

test('integers use the pt-PT thousands separator', () => {
  assert.equal(formatNumber(16366).replace(/\s/g, ' '), '16 366');
  assert.equal(formatNumber(230), '230');
  assert.equal(formatNumber(null), '0');
});

test('decimals use a comma and a fixed number of places', () => {
  assert.equal(formatDecimal(2.4, 1), '2,4');
  assert.equal(formatDecimal(100, 1), '100,0');
  assert.equal(formatDecimal(62.5, 0), '63');
});

test('percentages', () => {
  assert.equal(formatPercent(100), '100,0%');
  assert.equal(formatPercent(62.5, 0), '63%');
});

test('plural picks the noun by count', () => {
  assert.equal(plural(1, 'mandato', 'mandatos'), '1 mandato');
  assert.equal(plural(2, 'mandato', 'mandatos'), '2 mandatos');
  assert.equal(plural(0, 'mandato', 'mandatos'), '0 mandatos');
});

test('the first assembly is the Assembleia Constituinte', () => {
  assert.equal(legislatureName('Constituinte'), 'Assembleia Constituinte');
  assert.equal(legislatureName('XVII'), 'XVII Legislatura');
});

test('a coalition party that won no seats is marked', () => {
  assert.equal(seatsNote(false), 'sem lugares');
  assert.equal(seatsNote(true), null);
  assert.equal(seatsNote(undefined), null);
});

test('a coalition page says which list and elections it is', () => {
  assert.equal(coalitionScope({ ambito: 'Açores', eleicoes: [2025] }), 'Açores, 2025');
  assert.equal(coalitionScope({ ambito: null, eleicoes: [2024, 2025] }), '2024 e 2025');
  assert.equal(coalitionScope({ ambito: null, eleicoes: [1987, 1991, 1995] }), '1987 a 1995');
  assert.equal(coalitionScope({ ambito: 'Madeira', eleicoes: [] }), 'Madeira');
  assert.equal(coalitionScope({}), '');
});
