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
