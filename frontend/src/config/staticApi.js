/**
 * Answers API requests from the static export (fiscaliza_data/export.py), the way Flask does.
 *
 * Each request maps to one JSON file. Deputy search and the deputies list are answered from
 * one index file, and a deputy's interventions are filtered, sorted and paged here, so the
 * pages get the same answers the Flask endpoints give. tests/test_static_export.py checks that
 * against Flask. No browser APIs or Vite here, so node can run it.
 *
 * Paths use slug() for legislatures, parties and coalitions, the same form as the export.
 */

const MAX_PER_PAGE = 100;
const ROMAN = [
  [10, 'X'],
  [9, 'IX'],
  [5, 'V'],
  [4, 'IV'],
  [1, 'I'],
];
// Not in the data release yet: answered "not available" until their step lands, then the
// export renders them like the rest.
const PENDING = {
  agenda: { reason: 'A agenda parlamentar ainda não está na release do parlamento-aberto.', planned: 'S13' },
};
const INTERVENTION_ORDER = {
  newest: [['data', -1], ['id', -1]],
  oldest: [['data', 1], ['id', 1]],
  type: [['tipo', 1], ['data', -1], ['id', -1]],
};

const answer = (status, body) => ({ status, body });
const notFound = () => answer(404, { error: 'Não encontrado' });
const pending = (key) => answer(503, { status: 'not_available', ...PENDING[key] });

/** The path form of a legislature, party or coalition name: same as export.slug in Python. */
export const slug = (value) =>
  String(value)
    .normalize('NFKD')
    .replace(/[^\x00-\x7F]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');

/** The legislature as the data names it; the party page sends a number ("17"). */
export const legislatureName = (value) => {
  const text = String(value).trim();
  if (!/^\d+$/.test(text)) return text.toUpperCase();
  let n = parseInt(text, 10);
  let out = '';
  for (const [size, numeral] of ROMAN) {
    while (n >= size) {
      out += numeral;
      n -= size;
    }
  }
  return out;
};

const fold = (text) =>
  String(text ?? '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{M}/gu, '');

// Flask's request.args.get(name, default, type=int): the default unless it is a whole number.
const intArg = (params, name, fallback) => {
  const raw = params.get(name);
  return raw !== null && /^\s*[-+]?\d+\s*$/.test(raw) ? parseInt(raw, 10) : fallback;
};
const flagArg = (params, name, fallback) => (params.get(name) ?? fallback).toLowerCase() === 'true';
const clamp = (value, low, high) => Math.min(Math.max(value, low), high);

// SQL order: nulls last in both directions.
const compareBy = (keys) => (a, b) => {
  for (const [key, dir] of keys) {
    const x = a[key];
    const y = b[key];
    if (x === y) continue;
    if (x === null || x === undefined) return 1;
    if (y === null || y === undefined) return -1;
    if (x < y) return -dir;
    if (x > y) return dir;
  }
  return 0;
};

const only = (params, allowed) => [...params.keys()].every((k) => allowed.includes(k));

function deputyList(index, params) {
  const page = Math.max(intArg(params, 'page', 1), 1);
  const perPage = clamp(intArg(params, 'per_page', 20), 1, MAX_PER_PAGE);
  const activeOnly = flagArg(params, 'active_only', 'true');
  const search = params.get('search') || null;
  const needle = search === null ? null : fold(search);
  const matched = [];
  let records = 0;
  index.deputados.forEach((d, i) => {
    // In office, as the API lists it: a resigned deputy is not (#171).
    if (activeOnly && !d.career_info.is_currently_active) return;
    if (needle !== null && !fold(d.nome).includes(needle) && !fold(d.nome_completo).includes(needle)) return;
    matched.push(d);
    records += index.registos[i];
  });
  const total = matched.length;
  return answer(200, {
    deputados: matched.slice((page - 1) * perPage, page * perPage),
    pagination: {
      page,
      per_page: perPage,
      total,
      pages: Math.ceil(total / perPage),
      has_next: page * perPage < total,
      has_prev: page > 1,
    },
    filters: {
      total_deputy_records: records,
      active_deputies_count: index.filters.active_deputies_count,
      seated_deputies_count: index.filters.seated_deputies_count,
      legislatura: null,
      active_only: activeOnly,
    },
    legislatura: null,
  });
}

function activities(bundle, params) {
  // The activities endpoint takes the legislature exactly as the data names it.
  const leg = params.get('legislatura') || bundle.legislatura_atual;
  const found = bundle.atividades?.[leg];
  if (!found) return notFound();
  const page = Math.max(intArg(params, 'page', 1), 1);
  const perPage = clamp(intArg(params, 'per_page', 50), 1, MAX_PER_PAGE);
  const kind = params.get('tipo_intervencao') ? params.get('tipo_intervencao').toLowerCase() : null;
  const order = INTERVENTION_ORDER[params.get('ordenacao_intervencoes')] || INTERVENTION_ORDER.newest;
  const matched = found.intervencoes.filter((i) => kind === null || (i.tipo != null && i.tipo.toLowerCase().includes(kind)));
  matched.sort(compareBy(order));
  const total = matched.length;
  return answer(200, {
    ...found,
    intervencoes: matched.slice((page - 1) * perPage, page * perPage),
    intervention_metadata: { total, page, per_page: perPage, pages: Math.ceil(total / perPage) },
  });
}

function votingAnalytics(bundle, params) {
  if (!only(params, ['legislatura'])) return notFound();
  const leg = params.get('legislatura');
  const found = leg
    ? bundle.voting_analytics?.[legislatureName(leg)]
    : (bundle.voting_analytics?.[bundle.legislatura_atual] ?? bundle.voting_analytics_atual);
  return found ? answer(200, found) : notFound();
}

// A field of the deputy's file, for an endpoint that takes no parameters.
const field = (name) => (bundle, params) =>
  only(params, []) && bundle[name] !== undefined ? answer(200, bundle[name]) : null;

// Every endpoint of the deputy page and how it is answered from the deputy's file
// (fiscaliza_data/export.py, DEPUTY_SECTIONS). A section missing from the file answers 404,
// or 503 "not available" while it is in PENDING.
const DEPUTY_SECTIONS = {
  detalhes: field('detalhes'),
  'conflitos-interesse': field('conflitos_interesse'),
  atividades: activities,
  'voting-analytics': votingAnalytics,
  attendance: field('attendance'),
};
const DEPUTY = new RegExp(`^deputados/(\\d+)/(${Object.keys(DEPUTY_SECTIONS).join('|')})$`);

/**
 * createStaticApi({ load }) where load(path) resolves to { ok, status, text } for a file path
 * relative to the export root. get(endpoint) resolves to { status, body }.
 */
export function createStaticApi({ load }) {
  const cache = new Map();

  // A host that answers a missing file with index.html (SPA fallback) gives HTML, not JSON.
  const file = (path) => {
    if (!cache.has(path)) {
      cache.set(
        path,
        load(path).then(
          (r) => {
            if (!r.ok) return null;
            try {
              return JSON.parse(r.text);
            } catch {
              return null;
            }
          },
          // A network error is not cached, so the next request tries again.
          () => {
            cache.delete(path);
            return null;
          },
        ),
      );
    }
    return cache.get(path);
  };
  const serve = async (path) => {
    const body = await file(path);
    return body === null ? notFound() : answer(200, body);
  };

  async function get(endpoint) {
    const [rawPath, query = ''] = String(endpoint).replace(/^\/+/, '').split('?');
    const route = decodeURIComponent(rawPath);
    const params = new URLSearchParams(query);
    const none = [...params.keys()].length === 0;

    if (route === 'legislaturas' && none) return serve('legislaturas.json');
    if (route === 'estatisticas' && none) return serve('estatisticas.json');
    if (route === 'estatisticas/atividade' && none) return serve('estatisticas/atividade.json');
    if (route === 'partidos' && none) return serve('partidos.json');
    if (route === 'health' && none) return serve('health.json');
    if (route === 'dados' && none) return serve('dados.json');
    if (route === 'perguntas' && none) return serve('perguntas.json');
    if (route.startsWith('perguntas/') && none) return serve(`perguntas/${slug(route.slice('perguntas/'.length))}.json`);
    if (route === 'agenda/hoje' || route === 'agenda/semana') return pending('agenda');
    if (route === 'votacoes/recentes' && only(params, ['limite'])) {
      return serve(`votacoes/recentes/${intArg(params, 'limite', 10)}.json`);
    }
    if (route === 'coligacoes' && only(params, ['include_inactive'])) {
      return serve(flagArg(params, 'include_inactive', 'false') ? 'coligacoes-todas.json' : 'coligacoes.json');
    }
    if (route.startsWith('coligacoes/') && none) {
      const rest = route.slice('coligacoes/'.length);
      const part = rest.match(/^(.+)\/(deputados|partidos)$/);
      return part ? serve(`coligacoes/${slug(part[1])}/${part[2]}.json`) : serve(`coligacoes/${slug(rest)}.json`);
    }
    if (route === 'deputados' && only(params, ['page', 'per_page', 'active_only', 'search'])) {
      const index = await file('deputados.json');
      return index === null ? notFound() : deputyList(index, params);
    }
    const deputy = route.match(DEPUTY);
    if (deputy) {
      const [, id, endpoint] = deputy;
      const bundle = await file(`deputados/${id}.json`);
      const found = bundle === null ? null : DEPUTY_SECTIONS[endpoint](bundle, params);
      if (found !== null && found.status !== 404) return found;
      return endpoint in PENDING ? pending(endpoint) : found || notFound();
    }
    const party = route.match(/^partidos\/(.+)\/(deputados|voting-analytics)$/);
    if (party) {
      const [, sigla, what] = party;
      if (what === 'deputados' && none) return serve(`partidos/${slug(sigla)}/deputados.json`);
      if (what === 'voting-analytics' && only(params, ['legislatura'])) {
        const leg = params.get('legislatura');
        return serve(
          leg
            ? `partidos/${slug(sigla)}/voting-analytics/${slug(legislatureName(leg))}.json`
            : `partidos/${slug(sigla)}/voting-analytics.json`,
        );
      }
    }
    return notFound();
  }

  return { get };
}
