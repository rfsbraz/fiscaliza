// pt-PT number formatting for the site (#112): "16 366", "2,4", "100,0%".
const LOCALE = 'pt-PT';

export const formatNumber = (value) => Number(value ?? 0).toLocaleString(LOCALE);

export const formatDecimal = (value, digits = 1) =>
  Number(value ?? 0).toLocaleString(LOCALE, { minimumFractionDigits: digits, maximumFractionDigits: digits });

export const formatPercent = (value, digits = 1) => `${formatDecimal(value, digits)}%`;

// "1 mandato", "2 mandatos".
export const plural = (count, one, many) => `${formatNumber(count)} ${count === 1 ? one : many}`;

// "XVII Legislatura", but the first assembly is the Assembleia Constituinte (#108). Mirrors
// legislature_designation in app/services/core.py.
export const legislatureName = (numero) => (numero === 'Constituinte' ? 'Assembleia Constituinte' : `${numero} Legislatura`);

// "sem lugares" for a coalition party that won no seat on any of its lists (com_lugares false,
// #181), else null.
export const seatsNote = (comLugares) => (comLugares === false ? 'sem lugares' : null);

// Which list and elections a coalition page is (#111): its region, if it ran only in the Açores
// or Madeira, and its election years. "Açores, 2025", "2024 e 2025", "1987 a 2025". Same text as
// coalition_scope in deploy/pages.py.
export const coalitionScope = ({ ambito, eleicoes } = {}) => {
  let years = (eleicoes || []).filter((y) => y !== null && y !== undefined).map(String);
  if (years.length > 2) years = [`${years[0]} a ${years[years.length - 1]}`];
  return [ambito, years.join(' e ')].filter(Boolean).join(', ');
};
