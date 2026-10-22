import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { apiFetch } from '../config/api';
import { tokens } from '../styles/tokens';
import { LoadingSpinner } from './common';

/**
 * /perguntas and /perguntas/:legislatura (#114). Written questions (perguntas) from deputies to
 * the Government in one legislature: how many got an answer and the median days to the first
 * answer, per recipient. /perguntas shows the latest legislature. The open legislature is marked
 * provisional. No deadline figure: the legal answer period has not been checked yet.
 */
const integer = (n) => (n ?? 0).toLocaleString('pt-PT');
const percent = (n) =>
  n === null || n === undefined
    ? 'sem dados'
    : `${n.toLocaleString('pt-PT', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;
const days = (n) =>
  n === null || n === undefined ? 'sem dados' : n.toLocaleString('pt-PT', { maximumFractionDigits: 1 });

const cell = {
  padding: '10px 12px',
  borderBottom: `1px solid ${tokens.colors.border}`,
  fontSize: '0.875rem',
  color: tokens.colors.textPrimary,
};
const numberCell = { ...cell, textAlign: 'right', fontFamily: tokens.fonts.mono, whiteSpace: 'nowrap' };
const headCell = {
  ...cell,
  fontSize: '0.75rem',
  fontWeight: 600,
  color: tokens.colors.textSecondary,
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
};
const note = { fontSize: '0.8125rem', color: tokens.colors.textSecondary, margin: '0 0 0.5rem 0' };

const Figure = ({ label, value, detail }) => (
  <div
    style={{
      backgroundColor: tokens.colors.bgSecondary,
      border: `1px solid ${tokens.colors.border}`,
      borderRadius: '6px',
      padding: '16px 20px',
    }}
  >
    <div style={{ ...headCell, padding: 0, border: 'none', marginBottom: '8px' }}>{label}</div>
    <div style={{ fontSize: '1.75rem', fontWeight: 700, fontFamily: tokens.fonts.mono, color: tokens.colors.textPrimary }}>
      {value}
    </div>
    {detail && <div style={{ ...note, margin: '4px 0 0 0' }}>{detail}</div>}
  </div>
);

/**
 * The figures per recipient: a table on larger screens and one card per recipient on small ones,
 * so the answer rate and the median stay in view without scrolling sideways.
 */
export const Destinatarios = ({ rows }) => (
  <>
    <div className="hidden md:block" style={{ overflowX: 'auto', marginBottom: '1rem' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', backgroundColor: tokens.colors.bgSecondary }}>
        <thead>
          <tr>
            <th style={{ ...headCell, textAlign: 'left' }}>Destinatário</th>
            <th style={{ ...headCell, textAlign: 'right' }}>Perguntas</th>
            <th style={{ ...headCell, textAlign: 'right' }}>Respondidas</th>
            <th style={{ ...headCell, textAlign: 'right' }}>Taxa de resposta</th>
            <th style={{ ...headCell, textAlign: 'right' }}>Mediana de dias até à resposta</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((d) => (
            <tr key={d.destinatario}>
              <td style={cell}>{d.destinatario}</td>
              <td style={numberCell}>{integer(d.perguntas)}</td>
              <td style={numberCell}>{integer(d.respondidas)}</td>
              <td style={numberCell}>{percent(d.taxa_resposta)}</td>
              <td style={numberCell}>{days(d.mediana_dias)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
    <ul className="md:hidden" style={{ listStyle: 'none', padding: 0, margin: '0 0 1rem 0' }}>
      {rows.map((d) => (
        <li
          key={d.destinatario}
          style={{
            backgroundColor: tokens.colors.bgSecondary,
            border: `1px solid ${tokens.colors.border}`,
            borderRadius: '6px',
            padding: '12px 16px',
            marginBottom: '8px',
          }}
        >
          <div style={{ fontSize: '0.9375rem', fontWeight: 600, color: tokens.colors.textPrimary, marginBottom: '8px' }}>
            {d.destinatario}
          </div>
          <dl style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px 16px', margin: 0 }}>
            {[
              ['Perguntas', integer(d.perguntas)],
              ['Respondidas', integer(d.respondidas)],
              ['Taxa de resposta', percent(d.taxa_resposta)],
              ['Mediana de dias até à resposta', days(d.mediana_dias)],
            ].map(([label, value]) => (
              <div key={label}>
                <dt style={{ fontSize: '0.75rem', color: tokens.colors.textSecondary, lineHeight: 1.3 }}>{label}</dt>
                <dd style={{ margin: '2px 0 0 0', fontSize: '1rem', fontFamily: tokens.fonts.mono, color: tokens.colors.textPrimary }}>
                  {value}
                </dd>
              </div>
            ))}
          </dl>
        </li>
      ))}
    </ul>
  </>
);

const PerguntasPage = () => {
  const { legislatura } = useParams();
  const [index, setIndex] = useState(null);
  const [page, setPage] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    setPage(null);
    (async () => {
      try {
        const listed = index || (await (await apiFetch('perguntas')).json());
        if (cancelled) return;
        setIndex(listed);
        const chosen = legislatura || listed.legislaturas[0]?.legislatura;
        if (!chosen) {
          setError('Não há perguntas ao Governo nos dados.');
          return;
        }
        const response = await apiFetch(`perguntas/${chosen}`);
        if (!response.ok) throw new Error(`Não há perguntas ao Governo para a legislatura ${chosen}.`);
        const body = await response.json();
        if (!cancelled) setPage(body);
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [legislatura]);

  if (error) {
    return <p style={{ fontFamily: tokens.fonts.body, color: tokens.colors.textSecondary }}>{error}</p>;
  }
  if (!page || !index) {
    return <LoadingSpinner message="A carregar perguntas ao Governo" />;
  }

  const t = page.totais;
  return (
    <div style={{ maxWidth: '960px', margin: '0 auto', fontFamily: tokens.fonts.body }}>
      <h1
        style={{
          fontFamily: tokens.fonts.headline,
          fontSize: '2.25rem',
          fontWeight: 700,
          color: tokens.colors.textPrimary,
          margin: '0 0 0.75rem 0',
        }}
      >
        Perguntas ao Governo
      </h1>
      <p style={{ fontSize: '1rem', lineHeight: 1.6, color: tokens.colors.textSecondary, margin: '0 0 1.25rem 0' }}>
        Perguntas escritas dos deputados ao Governo e quantas tiveram resposta, por destinatário. Uma pergunta enviada
        a mais de um membro do Governo conta uma vez para cada um. As perguntas retiradas ou devolvidas não contam para
        a taxa de resposta nem para a mediana.
      </p>

      <nav aria-label="Legislaturas" style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '1.5rem' }}>
        {index.legislaturas.map((l) => {
          const active = l.legislatura === page.legislatura;
          return (
            <Link
              key={l.legislatura}
              to={`/perguntas/${l.legislatura}`}
              aria-current={active ? 'page' : undefined}
              style={{
                padding: '6px 12px',
                borderRadius: '4px',
                border: `1px solid ${active ? tokens.colors.primary : tokens.colors.border}`,
                backgroundColor: active ? tokens.colors.primary : tokens.colors.bgSecondary,
                color: active ? '#FFFFFF' : tokens.colors.textPrimary,
                fontSize: '0.875rem',
                textDecoration: 'none',
              }}
            >
              {l.legislatura}
              {l.provisoria ? ' (provisório)' : ''}
            </Link>
          );
        })}
      </nav>

      <h2
        style={{
          fontFamily: tokens.fonts.headline,
          fontSize: '1.375rem',
          fontWeight: 700,
          color: tokens.colors.textPrimary,
          margin: '0 0 0.75rem 0',
        }}
      >
        {page.legislatura} Legislatura
      </h2>

      {page.provisoria && (
        <p
          role="note"
          style={{
            padding: '12px 16px',
            margin: '0 0 1.25rem 0',
            backgroundColor: tokens.colors.bgWarm || '#F8F6F0',
            border: `1px solid ${tokens.colors.borderWarm || '#E8E4DA'}`,
            borderRadius: '6px',
            fontSize: '0.875rem',
            color: tokens.colors.textPrimary,
          }}
        >
          <strong>Provisório.</strong> A {page.legislatura} Legislatura está em curso. As perguntas mais recentes podem
          ainda vir a ter resposta, por isso estes números vão mudar.
        </p>
      )}

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '12px',
          marginBottom: '1.5rem',
        }}
      >
        <Figure label="Perguntas" value={integer(t.perguntas)} />
        <Figure label="Taxa de resposta" value={percent(t.taxa_resposta)} detail={`${integer(t.respondidas)} com resposta`} />
        <Figure label="Mediana de dias até à resposta" value={days(t.mediana_dias)} />
      </div>

      <Destinatarios rows={page.destinatarios} />

      <p style={note}>
        Fora das contas: {integer(t.retiradas)} retiradas e {integer(t.devolvidas)} devolvidas.
        {t.respondidas_sem_data > 0 &&
          ` ${integer(t.respondidas_sem_data)} com resposta sem data utilizável (em falta ou anterior ao envio) contam como respondidas e ficam fora da mediana.`}
      </p>
      <p style={note}>
        A mediana conta os dias entre o envio da pergunta a cada destinatário e a primeira resposta desse destinatário.
        Fonte: dados abertos da Assembleia da República.
      </p>
    </div>
  );
};

export default PerguntasPage;
