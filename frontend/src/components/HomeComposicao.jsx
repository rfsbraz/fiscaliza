import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiFetch } from '../config/api';
import { tokens, partidoCores } from '../styles/tokens';
import { formatDate, formatNumber, plural } from '../utils/format';

/**
 * The home page composition strip and the state of the sources (#265). Every date is the date
 * of the data, never today's. Gaps in the sources are coverage of the data, not a political
 * problem. Reads estatisticas/inicio.
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
const link = { color: 'inherit', textDecoration: 'underline' };

const seats = (grupos) => grupos.map((g) => `${g.sigla} ${formatNumber(g.deputados)}`).join(', ');

const EVENTO = { inicio: 'começa funções', fim: 'termina funções' };

export const ComposicaoView = ({ composicao }) => {
  const { data, lugares, substituicoes_temporarias: temporarios, governo, grupos = [], mudancas } = composicao;
  const apoiam = grupos.filter((g) => g.apoia_governo);
  const outros = grupos.filter((g) => !g.apoia_governo);
  const itens = mudancas?.itens || [];

  return (
    <section style={box} aria-labelledby="home-composicao">
      <h2 id="home-composicao" style={title}>Composição e mudanças de mandato</h2>
      <p style={until}>
        Em funções a {formatDate(data)} · {formatNumber(lugares)} lugares
      </p>
      <div
        role="img"
        aria-label={`Lugares por grupo: ${seats(grupos)}`}
        style={{ display: 'flex', height: '28px', borderRadius: '2px', overflow: 'hidden', gap: '1px', backgroundColor: colors.bgSecondary }}
      >
        {grupos.map((g) => (
          <div
            key={g.sigla}
            title={`${g.sigla} ${g.deputados}`}
            style={{
              flex: g.deputados,
              backgroundColor: partidoCores[g.sigla] || '#78716C',
              color: '#FFFFFF',
              fontFamily: fonts.mono,
              fontSize: '0.6875rem',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              overflow: 'hidden',
              whiteSpace: 'nowrap',
              outline: g.apoia_governo ? `2px solid ${colors.textPrimary}` : 'none',
              outlineOffset: '-2px',
            }}
          >
            {g.deputados >= 20 ? `${g.sigla} ${g.deputados}` : ''}
          </div>
        ))}
      </div>
      {apoiam.length > 0 ? (
        <>
          <p style={small}>
            <strong>Apoiam o Governo: {seats(apoiam)}</strong>{' '}
            {governo && (
              <>
                (<a href={governo.fonte} target="_blank" rel="noopener noreferrer" style={link}>{governo.nome}</a>)
              </>
            )}
          </p>
          <p style={{ ...small, marginTop: '0.25rem' }}>Outros grupos: {seats(outros)}</p>
        </>
      ) : (
        <p style={small}>Grupos: {seats(grupos)}</p>
      )}
      <p style={{ ...small, marginTop: '0.25rem' }}>
        {plural(temporarios || 0, 'lugar ocupado', 'lugares ocupados')} por substitutos temporários (Efetivo Temporário).
      </p>

      <h3 style={{ fontSize: '0.875rem', fontWeight: 600, color: colors.textPrimary, margin: '1.25rem 0 0.25rem' }}>
        Mudanças de mandato de {formatDate(mudancas?.desde)} a {formatDate(mudancas?.ate)}
      </h3>
      {itens.length === 0 ? (
        <p style={small}>Nenhuma mudança de mandato registada neste período.</p>
      ) : (
        <ul style={{ ...small, paddingLeft: '1.25rem', margin: '0.25rem 0 0' }}>
          {itens.map((m) => (
            <li key={`${m.data}-${m.cadastro_id}-${m.evento}`}>
              {formatDate(m.data)} ·{' '}
              <Link to={`/deputados/${m.cadastro_id}`} style={link}>{m.nome}</Link>
              {m.grupo ? ` (${m.grupo})` : ''} {EVENTO[m.evento]} ({m.situacao})
            </li>
          ))}
        </ul>
      )}
      <p style={{ ...small, fontSize: '0.8125rem', color: colors.textMuted }}>
        Cada linha é o início ou o fim de um período de mandato registado pela AR. A AR não diz quem substitui quem.
      </p>
    </section>
  );
};

export const EstadoFontesView = ({ fontes }) => {
  const { tag, source_updated: sourceUpdated, conjuntos = [], lacunas = [] } = fontes;
  return (
    <section style={box} aria-labelledby="home-fontes">
      <h2 id="home-fontes" style={title}>Estado das fontes</h2>
      <p style={until}>
        Versão dos dados {tag}
        {sourceUpdated ? ` · fonte atualizada a ${formatDate(sourceUpdated)}` : ''}
      </p>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
        <tbody>
          {conjuntos.map((c) => (
            <tr key={c.nome} style={{ borderBottom: `1px solid ${colors.border}` }}>
              <td style={{ padding: '0.5rem 0', color: colors.textPrimary }}>{c.nome}</td>
              <td style={{ padding: '0.5rem 0', textAlign: 'right', fontFamily: fonts.mono, color: colors.textSecondary }}>
                {c.dados_ate ? `dados até ${formatDate(c.dados_ate)}` : 'sem data'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {lacunas.length > 0 && (
        <>
          <h3 style={{ fontSize: '0.875rem', fontWeight: 600, color: colors.textPrimary, margin: '1rem 0 0.25rem' }}>
            Lacunas conhecidas
          </h3>
          <ul style={{ ...small, paddingLeft: '1.25rem', margin: 0 }}>
            {lacunas.map((l) => (
              <li key={l.conjunto}>
                <strong>{l.conjunto}:</strong> {l.texto}
              </li>
            ))}
          </ul>
        </>
      )}
      <p style={{ ...small, fontSize: '0.8125rem', color: colors.textMuted }}>
        São lacunas de cobertura dos dados, não problemas políticos.{' '}
        <Link to="/metodologia" style={link}>Lacunas conhecidas e como reportar um erro</Link>
      </p>
    </section>
  );
};

const HomeComposicao = () => {
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState(null);

  useEffect(() => {
    let vivo = true;
    apiFetch('estatisticas/inicio')
      .then((response) => response.json())
      .then((body) => vivo && setDados(body))
      .catch((e) => vivo && setErro(e.message));
    return () => {
      vivo = false;
    };
  }, []);

  if (erro) return <p style={{ ...small, marginBottom: '1.5rem' }}>{erro}</p>;
  if (!dados) return null;
  return (
    <>
      {dados.fontes && <EstadoFontesView fontes={dados.fontes} />}
      {dados.composicao && <ComposicaoView composicao={dados.composicao} />}
    </>
  );
};

export default HomeComposicao;
