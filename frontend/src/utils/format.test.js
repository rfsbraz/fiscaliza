import test from 'node:test';
import assert from 'node:assert/strict';
import { formatNumber, formatDecimal, formatPercent, legislatureName, plural, seatsNote, seatedNote, coalitionScope, NOT_AVAILABLE, formatDate, daysBetween, relativeDay, todayInLisbon } from './format.js';

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

test('a missing value reads n.d., not N/A', () => {
  assert.equal(NOT_AVAILABLE, 'n.d.');
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

test('a coalition page names who was in office as a second figure', () => {
  const closed = { contagem: 'eleitos', deputados_em_funcoes: 78, data_em_funcoes: '1980-11-12', legislatura_aberta: false };
  assert.equal(seatedNote(closed), '78 em funções no último dia da legislatura');
  const open = { contagem: 'eleitos', deputados_em_funcoes: 87, data_em_funcoes: '2026-10-21', legislatura_aberta: true };
  assert.equal(seatedNote(open), '87 em funções a 21/10/2026');
  assert.equal(seatedNote({ ...closed, contagem: 'em_funcoes' }), null);
  assert.equal(seatedNote({}), null);
});

test('dates read dd/mm/aaaa (#185)', () => {
  assert.equal(formatDate('2026-10-22'), '22/10/2026');
  assert.equal(formatDate('2026-10-23 08:37:48.794144+00'), '23/10/2026');
  assert.equal(formatDate(null), '');
  assert.equal(formatDate('22/10/2026'), '');
});

test('whole days between two dates, null when one is not a date', () => {
  assert.equal(daysBetween('2026-10-22', '2026-10-23'), 1);
  assert.equal(daysBetween('2026-10-23', '2026-10-23'), 0);
  assert.equal(daysBetween('2026-03-28', '2026-03-30'), 2, 'the DST change does not shift the count');
  assert.equal(daysBetween('2025-12-31', '2026-01-08'), 8);
  assert.equal(daysBetween(null, '2026-10-23'), null);
  assert.equal(daysBetween('ontem', '2026-10-23'), null);
});

test('the age of the data reads hoje, ontem or há N dias', () => {
  assert.equal(relativeDay(0), 'hoje');
  assert.equal(relativeDay(-1), 'hoje', 'a date ahead of the clock still reads hoje');
  assert.equal(relativeDay(1), 'ontem');
  assert.equal(relativeDay(2), 'há 2 dias');
  assert.equal(relativeDay(11), 'há 11 dias');
});

test('today is the date in Lisbon, not in UTC', () => {
  assert.equal(todayInLisbon(new Date('2026-10-23T08:00:00Z')), '2026-10-23');
  assert.equal(todayInLisbon(new Date('2026-07-01T23:30:00Z')), '2026-07-02', 'WEST is UTC+1');
  assert.equal(todayInLisbon(new Date('2026-12-31T23:30:00Z')), '2026-12-31', 'WET is UTC+0');
});
