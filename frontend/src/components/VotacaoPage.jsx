import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { apiFetch } from '../config/api';
import { tokens } from '../styles/tokens';
import { formatDate } from '../utils/format';
import { phaseNote } from '../utils/votePhase';
import NotFound from './NotFound';

/**
 * The page of one plenary vote (#191), at /votacoes/:id. Group positions are shown exactly as
 * the AR published them; positions inferred from a unanimous vote are not shown as groups. The
 * deputies the AR named are listed apart from the group counts, without matching one to the
 * other. Nothing is computed from group sizes. Reads votacoes/:id.
 */

const { colors, fonts } = tokens;

const box = {
  backgroundColor: colors.bgSecondary,
  border: `1px solid ${colors.border}`,
  borderRadius: '4px',
  padding: '1.25rem 1.5rem',
};
const h2 = { fontFamily: fonts.headline, fontSize: '1.125rem', fontWeight: 700, color: colors.textPrimary, margin: 0 };
const h3 = { fontSize: '0.875rem', fontWeight: 600, color: colors.textPrimary, margin: '1.25rem 0 0.25rem' };
const small = { fontSize: '0.875rem', color: colors.textSecondary, lineHeight: 1.6, margin: '0.5rem 0 0' };
const tag = {
  display: 'inline-block',
  fontSize: '0.75rem',
  border: `1px solid ${colors.borderStrong}`,
  borderRadius: '2px',
  padding: '0.0625rem 0.375rem',
  marginRight: '0.375rem',
  color: colors.textSecondary,
};
const link = { color: 'inherit', textDecoration: 'underline' };

const POSITIONS = [
  ['favor', 'A favor'],
  ['contra', 'Contra'],
  ['abstencao', 'Abstenção'],
  ['ausentes', 'Ausentes'],
];
const NAMED = { favor: 'votou a favor', contra: 'votou contra', abstencao: 'absteve-se', ausente: 'esteve ausente' };

const groupLabel = ({ grupo, deputados }) =>
  deputados == null ? grupo : `${grupo} (${deputados} ${deputados === 1 ? 'deputado' : 'deputados'})`;

const initiativeName = (i) => {
  const name = i.tipo || 'Iniciativa';
  return i.numero != null ? `${name} n.º ${i.numero}/${i.legislatura}` : name;
};

const Posicoes = ({ vote }) => {
  const rows = POSITIONS.filter(([key]) => (vote.posicoes?.[key] || []).length > 0);
  if (rows.length === 0) {
    return (
      <p style={small}>
        {vote.unanimidade
          ? 'A AR registou esta votação como unânime e não publicou a posição de cada grupo.'
          : 'A AR não publicou as posições dos grupos nesta votação.'}
      </p>
    );
  }
  return (
    <dl style={{ margin: '0.75rem 0 0', fontSize: '0.875rem', lineHeight: 1.6 }}>
      {rows.map(([key, label]) => (
        <div key={key} style={{ display: 'grid', gridTemplateColumns: '5.75rem minmax(0, 1fr)', columnGap: '0.75rem' }}>
          <dt style={{ fontWeight: 600, color: colors.textSecondary }}>{label}</dt>
          <dd style={{ margin: 0, color: colors.textPrimary }}>{vote.posicoes[key].map(groupLabel).join(', ')}</dd>
        </div>
      ))}
    </dl>
  );
};

const Nomeados = ({ votos }) =>
  votos.length === 0 ? (
    <p style={small}>A AR não nomeou votos individuais de deputados de grupos parlamentares nesta votação.</p>
  ) : (
    <ul style={{ ...small, paddingLeft: '1.25rem' }}>
      {votos.map((v) => (
        <li key={`${v.id_cadastro ?? v.nome}-${v.posicao}`}>
          {v.id_cadastro ? (
            <Link to={`/deputados/${v.id_cadastro}`} style={link}>
              {v.nome}
            </Link>
          ) : (
            v.nome
          )}{' '}
          ({v.grupo}) {NAMED[v.posicao] || v.posicao}
        </li>
      ))}
    </ul>
  );

export const VotacaoView = ({ vote }) => {
  const iniciativas = vote.iniciativas || [];
  const first = iniciativas[0];
  const title = first?.titulo || vote.descricao || `Votação ${vote.id} no Plenário de ${formatDate(vote.data)}`;
  const resultado = [vote.resultado || 'Resultado não publicado', vote.unanimidade ? 'por unanimidade' : null]
    .filter(Boolean)
    .join(' ');
  const note = phaseNote(vote.fase);

  return (
    <article>
      <nav aria-label="Caminho" style={{ fontSize: '0.8125rem', color: colors.textMuted, marginBottom: '0.75rem' }}>
        <Link to="/agenda" style={link}>
          Agenda
        </Link>{' '}
        › Votação {vote.id}
      </nav>
      {first ? (
        <div>
          <span style={tag}>{initiativeName(first)}</span>
          {first.autoria?.length > 0 && <span style={tag}>Autoria: {first.autoria.join(', ')}</span>}
        </div>
      ) : null}
      <h1
        style={{
          fontFamily: fonts.headline,
          fontSize: '1.75rem',
          lineHeight: 1.25,
          color: colors.textPrimary,
          margin: '0.5rem 0 0.25rem',
          overflowWrap: 'anywhere',
        }}
      >
        {title}
      </h1>
      {iniciativas.length > 1 && <p style={small}>E mais {iniciativas.length - 1} iniciativas na mesma votação.</p>}
      {first?.titulo && vote.descricao && <p style={small}>Descrição da AR: {vote.descricao}</p>}
      <p style={{ fontSize: '0.875rem', color: colors.textMuted, margin: '0 0 1.5rem' }}>
        Plenário de {formatDate(vote.data)} · votação {vote.id} da AR
      </p>
      {!first && !vote.descricao && <p style={small}>A AR não publicou o assunto desta votação.</p>}

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 320px), 1fr))',
          gap: '1.25rem',
          margin: '1rem 0 1.25rem',
        }}
      >
        <section style={box} aria-labelledby="votacao-resultado">
          <h2 id="votacao-resultado" style={h2}>
            Resultado
          </h2>
          <p style={{ fontWeight: 700, fontSize: '0.9375rem', letterSpacing: '0.02em', margin: '0.75rem 0 0' }}>
            {[resultado, vote.fase].filter(Boolean).join(' · ')}
          </p>
          {note && <p style={small}>{note}</p>}
        </section>
        <section style={box} aria-labelledby="votacao-posicoes">
          <h2 id="votacao-posicoes" style={h2}>
            Posições dos grupos
          </h2>
          <Posicoes vote={vote} />
          <h3 style={h3}>Votos individuais nomeados</h3>
          <Nomeados votos={vote.votos_nomeados || []} />
        </section>
      </div>

      <section style={box} aria-labelledby="votacao-fonte">
        <h2 id="votacao-fonte" style={h2}>
          Fonte
        </h2>
        {iniciativas.length > 0 ? (
          <ul style={{ ...small, paddingLeft: '1.25rem' }}>
            {iniciativas.map((i) => (
              <li key={i.id}>
                <a href={i.url} target="_blank" rel="noopener noreferrer" style={link}>
                  {initiativeName(i)} no site da AR
                </a>
                {i.titulo && iniciativas.length > 1 ? `: ${i.titulo}` : ''}
              </li>
            ))}
          </ul>
        ) : (
          <p style={small}>Os dados abertos não têm ligação para esta votação no site da AR.</p>
        )}
        <p style={small}>
          Posições dos grupos e votos nomeados tal como a Assembleia da República os publica.{' '}
          <Link to="/dados" style={link}>
            Descarregar dados
          </Link>{' '}
          ·{' '}
          <Link to="/metodologia" style={link}>
            Como lemos as votações
          </Link>
        </p>
      </section>
    </article>
  );
};

const VotacaoPage = () => {
  const { voteId } = useParams();
  const [state, setState] = useState({ vote: null, status: 'loading' });

  useEffect(() => {
    let live = true;
    setState({ vote: null, status: 'loading' });
    apiFetch(`votacoes/${encodeURIComponent(voteId)}`)
      .then((r) => r.json())
      .then((vote) => live && setState({ vote, status: 'ok' }))
      .catch((e) => live && setState({ vote: null, status: e.status === 404 ? 'missing' : 'error' }));
    return () => {
      live = false;
    };
  }, [voteId]);

  if (state.status === 'missing') return <NotFound />;
  if (state.status === 'error') {
    return <p style={small}>Não foi possível carregar esta votação. Tente de novo dentro de momentos.</p>;
  }
  if (!state.vote) return <p style={small}>A carregar a votação…</p>;
  return <VotacaoView vote={state.vote} />;
};

export default VotacaoPage;
