// pt-PT number formatting for the site (#112): "16 366", "2,4", "100,0%".
const LOCALE = 'pt-PT';

export const formatNumber = (value) => Number(value ?? 0).toLocaleString(LOCALE);

export const formatDecimal = (value, digits = 1) =>
  Number(value ?? 0).toLocaleString(LOCALE, { minimumFractionDigits: digits, maximumFractionDigits: digits });

// A value the data doesn't have: "n.d." (não disponível), never the English N/A.
export const NOT_AVAILABLE = 'n.d.';

export const formatPercent = (value, digits = 1) => `${formatDecimal(value, digits)}%`;

// "1 mandato", "2 mandatos".
export const plural = (count, one, many) => `${formatNumber(count)} ${count === 1 ? one : many}`;

// "XVII Legislatura", but the first assembly is the Assembleia Constituinte (#108). Mirrors
// legislature_designation in app/services/core.py.
export const legislatureName = (numero) => (numero === 'Constituinte' ? 'Assembleia Constituinte' : `${numero} Legislatura`);

// "sem lugares" for a coalition party that won no seat on any of its lists (com_lugares false,
// #181), else null.
export const seatsNote = (comLugares) => (comLugares === false ? 'sem lugares' : null);

// A coalition page counts the deputies elected on its lists (#197, contagem "eleitos"). The
// second figure is who held the seat on the legislature's last day, or on the data date while it
// is open: "75 em funções no último dia da legislatura", "87 em funções a 21/10/2026". Null when
// the page already counts the deputies in office (a legislature with no seats per list).
const dayMonthYear = (iso) => (iso ? iso.slice(0, 10).split('-').reverse().join('/') : '');

const ISO_DAY = /^(\d{4})-(\d{2})-(\d{2})/;

// "22/10/2026" from "2026-10-22" (or a timestamp that starts with it), "" for anything else.
export const formatDate = (iso) => (ISO_DAY.test(String(iso ?? '')) ? dayMonthYear(String(iso)) : '');

// Whole calendar days from one YYYY-MM-DD date to another, counted in UTC so a DST change does
// not shift it. Null when either is not a date.
export const daysBetween = (fromIso, toIso) => {
  const day = (iso) => {
    const m = ISO_DAY.exec(String(iso ?? ''));
    return m ? Date.UTC(+m[1], +m[2] - 1, +m[3]) : null;
  };
  const [from, to] = [day(fromIso), day(toIso)];
  return from === null || to === null ? null : Math.round((to - from) / 86400000);
};

// How old the data is (#185): "hoje", "ontem", "há 11 dias".
export const relativeDay = (days) => (days <= 0 ? 'hoje' : days === 1 ? 'ontem' : `há ${formatNumber(days)} dias`);

// Today's date in Lisbon as YYYY-MM-DD, whatever the visitor's clock zone.
export const todayInLisbon = (now = new Date()) =>
  new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Lisbon' }).format(now);

export const seatedNote = ({ contagem, deputados_em_funcoes, data_em_funcoes, legislatura_aberta } = {}) => {
  if (contagem !== 'eleitos' || deputados_em_funcoes === null || deputados_em_funcoes === undefined) return null;
  const when = legislatura_aberta && data_em_funcoes
    ? `a ${dayMonthYear(data_em_funcoes)}`
    : 'no último dia da legislatura';
  return `${formatNumber(deputados_em_funcoes)} em funções ${when}`;
};

// Which list and elections a coalition page is (#111): its region, if it ran only in the Açores
// or Madeira, and its election years. "Açores, 2025", "2024 e 2025", "1987 a 2025". Same text as
// coalition_scope in deploy/pages.py.
export const coalitionScope = ({ ambito, eleicoes } = {}) => {
  let years = (eleicoes || []).filter((y) => y !== null && y !== undefined).map(String);
  if (years.length > 2) years = [`${years[0]} a ${years[years.length - 1]}`];
  return [ambito, years.join(' e ')].filter(Boolean).join(', ');
};
