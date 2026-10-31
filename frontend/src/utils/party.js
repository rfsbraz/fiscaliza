// The party page's route and links (#242). A sigla can hold a slash (MDP/CDE): the export writes
// that page at /partidos/MDP/CDE (deploy/pages.py), so the route takes the rest of the path.
export const PARTY_ROUTE = '/partidos/*';

// Groups in the AR data that are not parties and have no page.
const NOT_A_PARTY = { Indep: 'Independente', Ninsc: 'Não inscrito' };

/** The party page's path, encoded as the sitemap has it, or null for a group with no page. */
export const partyPath = (sigla) =>
  !sigla || sigla in NOT_A_PARTY ? null : `/partidos/${String(sigla).split('/').map(encodeURIComponent).join('/')}`;

/** "Independente" or "Não inscrito" for those groups, else null. */
export const notAPartyName = (sigla) => NOT_A_PARTY[sigla] ?? null;
