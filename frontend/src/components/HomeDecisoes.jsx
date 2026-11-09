import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiFetch } from '../config/api';
import { tokens } from '../styles/tokens';
import { formatDate, plural } from '../utils/format';

/**
 * Decisões do Plenário and the Government box on the home page (#264). The cards are exactly the
 * decisions the published rule picks for the last day with plenary votes (#263), with the group
 * positions as the AR publishes them: a unanimous vote gets no inferred groups. Each whole card
 * links to its vote page (#191). Reads estatisticas/decisoes.
 */

const { colors, fonts } = tokens;

const box = {
  backgroundColor: colors.bgSecondary,
  border: `1px solid ${colors.border}`,
  borderRadius: '4px',
  padding: '1.25rem 1.5rem',
  marginBottom: '1.5rem',
};
const title = { fontFamily: fonts.headline, fontSize: '1.125rem', fontWeight: 700, color: colors.textPrimary, margin: 0 };
const until = { fontSize: '0.8125rem', color: colors.textMuted, margin: '0.25rem 0 1rem' };
const small = { fontSize: '0.875rem', color: colors.textSecondary, lineHeight: 1.6, margin: '0.5rem 0 0' };
const grid = { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 19rem), 1fr))', gap: '0.75rem' };
const tag = {
  display: 'inline-block',
  fontSize: '0.6875rem',
  border: `1px solid ${colors.borderStrong}`,
  borderRadius: '2px',
  padding: '0.0625rem 0.375rem',
  margin: '0 0.375rem 0.25rem 0',
  color: colors.textSecondary,
};

const ROWS = [
  ['favor', 'A favor'],
  ['contra', 'Contra'],
  ['abstencao', 'Abstenção'],
  ['ausentes', 'Ausentes'],
];
const RESOLUCAO = 'Projeto de Resolução';

const initiativeName = (i) => `${i.tipo} n.º ${i.numero}/${i.legislatura}`;
const group = (p) => (p.deputados == null ? p.grupo : `${p.grupo} (${plural(p.deputados, 'deputado', 'deputados')})`);

/** The cards first, and the final votes on projetos de resolução folded under them. A day with
 * only projetos de resolução shows them as the cards. */
export const splitDecisions = (decisoes) => {
  const resolucao = (d) => d.tipo === 'final' && d.iniciativas.every((i) => i.tipo === RESOLUCAO);
  const main = decisoes.filter((d) => !resolucao(d));
  return main.length ? { main, resolucoes: decisoes.filter(resolucao) } : { main: decisoes, resolucoes: [] };
};

const summary = (decisoes) => {
  const finais = decisoes.filter((d) => d.tipo === 'final').length;
  const generalidade = decisoes.length - finais;
  return [
    finais && plural(finais, 'votação final', 'votações finais'),
    generalidade &&
      `${plural(generalidade, 'votação', 'votações')} na generalidade de ${generalidade === 1 ? 'uma proposta' : 'propostas'} de lei`,
  ]
    .filter(Boolean)
    .join(' e ');
};

const Positions = ({ decisao }) => {
  const rows = ROWS.filter(([key]) => decisao.posicoes[key].length);
  if (!rows.length) {
    return (
      <p style={{ ...small, fontSize: '0.8125rem' }}>
        {decisao.unanimidade
          ? 'Unanimidade. A AR não publicou a posição de cada grupo.'
          : 'A AR não publicou as posições dos grupos nesta votação.'}
      </p>
    );
  }
  return (
    <dl style={{ margin: '0.5rem 0 0', fontSize: '0.8125rem' }}>
      {rows.map(([key, label]) => (
        <div key={key} style={{ display: 'grid', gridTemplateColumns: '5.25rem minmax(0, 1fr)', gap: '0.5rem' }}>
          <dt style={{ color: colors.textMuted, fontWeight: 600 }}>{label}</dt>
          <dd style={{ margin: 0, color: colors.textPrimary }}>{decisao.posicoes[key].map(group).join(', ')}</dd>
        </div>
      ))}
    </dl>
  );
};

const Card = ({ decisao }) => {
  const [first, ...rest] = decisao.iniciativas;
  return (
    <Link
      to={`/votacoes/${decisao.vote_id}`}
      className="home-decisao"
      style={{
        display: 'flex',
        flexDirection: 'column',
        padding: '0.875rem 1rem',
        border: `1px solid ${colors.border}`,
        borderRadius: '4px',
        backgroundColor: colors.bgTertiary,
        color: 'inherit',
        textDecoration: 'none',
      }}
    >
      <div>
        {decisao.iniciativas.map((i) => (
          <span key={`${i.legislatura}-${i.id}`} style={tag}>{initiativeName(i)}</span>
        ))}
        {first.autoria && <span style={tag}>{first.autoria}</span>}
      </div>
      <h3 style={{ fontFamily: fonts.headline, fontSize: '1rem', lineHeight: 1.3, margin: '0.375rem 0', color: colors.textPrimary }}>
        {first.titulo || initiativeName(first)}
        {rest.length > 0 && ` (e mais ${rest.length})`}
      </h3>
      <div style={{ fontSize: '0.75rem', fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase', color: colors.textSecondary }}>
        {decisao.resultado}
        {decisao.unanimidade && ' por unanimidade'} · {decisao.fase}
      </div>
      <Positions decisao={decisao} />
      <span className="home-decisao-link" style={{ marginTop: 'auto', paddingTop: '0.625rem', fontSize: '0.8125rem', color: colors.primary, textDecoration: 'underline' }}>
        Ver a votação
      </span>
    </Link>
  );
};

export const DecisoesView = ({ body }) => {
  const { data, decisoes = [] } = body;
  const { main, resolucoes } = splitDecisions(decisoes);
  return (
    <section style={box} aria-labelledby="home-decisoes">
      <h2 id="home-decisoes" style={title}>Decisões do Plenário</h2>
      {!data ? (
        <p style={small}>Ainda não há votações em Plenário nos dados.</p>
      ) : (
        <>
          <p style={until}>
            Plenário de {formatDate(data)}, o último dia com votações nos dados · {summary(decisoes)}
          </p>
          {decisoes.length === 0 && <p style={small}>Nenhuma votação deste dia conta como decisão pela regra publicada.</p>}
          <div style={grid}>
            {main.map((d) => <Card key={d.vote_id} decisao={d} />)}
          </div>
          {resolucoes.length > 0 && (
            <details style={{ marginTop: '0.875rem' }}>
              <summary style={{ cursor: 'pointer', fontSize: '0.875rem', color: colors.textPrimary, textDecoration: 'underline' }}>
                Mais {plural(resolucoes.length, 'votação final', 'votações finais')} de projetos de resolução neste dia
              </summary>
              <div style={{ ...grid, marginTop: '0.75rem' }}>
                {resolucoes.map((d) => <Card key={d.vote_id} decisao={d} />)}
              </div>
            </details>
          )}
          <p style={{ ...small, fontSize: '0.8125rem' }}>
            Votações finais e votações na generalidade de propostas de lei, pela{' '}
            <Link to="/metodologia" style={{ color: 'inherit', textDecoration: 'underline' }}>regra publicada</Link>. Posições
            dos grupos tal como a Assembleia da República as publica.
          </p>
        </>
      )}
      <style>{`.home-decisao:hover .home-decisao-link, .home-decisao:focus-visible .home-decisao-link { text-decoration-thickness: 2px; }
.home-decisao:hover { border-color: ${colors.borderStrong}; }`}</style>
    </section>
  );
};

export const GovernoView = ({ body }) => {
  const { data, decisoes = [], governo } = body;
  if (!data || !governo) return null;
  const byId = new Map(decisoes.map((d) => [d.vote_id, d]));
  const rejeitadas = governo.rejeitadas.map((id) => byId.get(id)).filter(Boolean);
  const dia = formatDate(data);
  return (
    <section style={box} aria-labelledby="home-governo">
      <h2 id="home-governo" style={title}>Problemas institucionais</h2>
      <p style={until}>Votações até {dia}</p>
      <div style={{ border: `1px dashed ${colors.borderStrong}`, borderRadius: '4px', padding: '0.875rem 1rem', backgroundColor: colors.bgTertiary }}>
        <h3 style={{ fontSize: '0.9375rem', fontWeight: 700, margin: 0, color: colors.textPrimary }}>Iniciativas do Governo rejeitadas</h3>
        {rejeitadas.length === 0 ? (
          <p style={small}>
            Nenhuma em {dia}.{' '}
            {governo.votadas === 0
              ? 'Não houve decisões sobre iniciativas do Governo neste dia.'
              : `${governo.votadas === 1 ? 'A decisão' : `As ${governo.votadas} decisões`} sobre iniciativas do Governo neste dia ${governo.votadas === 1 ? 'foi aprovada' : 'foram aprovadas'}.`}
          </p>
        ) : (
          <>
            <ul style={{ margin: '0.5rem 0 0', paddingLeft: '1.125rem', fontSize: '0.875rem', lineHeight: 1.6 }}>
              {rejeitadas.map((d) => (
                <li key={d.vote_id}>
                  <Link to={`/votacoes/${d.vote_id}`} style={{ color: 'inherit', textDecoration: 'underline' }}>
                    {initiativeName(d.iniciativas[0])}: {d.iniciativas[0].titulo}
                  </Link>{' '}
                  · {d.fase}
                </li>
              ))}
            </ul>
            <p style={small}>
              {rejeitadas.length} de {plural(governo.votadas, 'decisão', 'decisões')} sobre iniciativas do Governo neste dia.
            </p>
          </>
        )}
        <p style={{ ...small, fontSize: '0.8125rem' }}>
          Só contam as iniciativas que a AR regista como do Governo, rejeitadas numa votação final ou na generalidade.
        </p>
      </div>
    </section>
  );
};

const HomeDecisoes = () => {
  const [body, setBody] = useState(null);
  const [erro, setErro] = useState(null);

  useEffect(() => {
    let vivo = true;
    apiFetch('estatisticas/decisoes')
      .then((response) => response.json())
      .then((b) => vivo && setBody(b))
      .catch((e) => vivo && setErro(e.message));
    return () => {
      vivo = false;
    };
  }, []);

  if (erro) return <p style={{ ...small, marginBottom: '1.5rem' }}>{erro}</p>;
  if (!body) return null;
  return (
    <>
      <DecisoesView body={body} />
      <GovernoView body={body} />
    </>
  );
};

export default HomeDecisoes;
