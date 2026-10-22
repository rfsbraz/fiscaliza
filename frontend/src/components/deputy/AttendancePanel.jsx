/**
 * Plenary attendance of a deputy, from deputados/{id}/attendance (app/services/attendance.py).
 *
 * The rate is present, in another body or on mission, over the ordinary and extraordinary
 * sittings in the AR's attendance lists; the strict rate (present only) and every category go
 * next to it, always with the number of sittings. Legislatures without lists say so instead
 * of showing zeros. Only the code of an absence is published, never its reason.
 */
import React, { useState } from 'react';
import { Activity, Info } from 'lucide-react';
import { tokens } from '../../styles/tokens';
import { legislatureName } from '../../utils/format';

// Under this many sittings one absence moves the rate by several points.
const FEW_MEETINGS = 20;
const RECORDS_SHOWN = 30;

export const CATEGORY_ROWS = [
  { key: 'presente', label: 'Presente no Plenário', color: tokens.colors.statusGreen },
  { key: 'outro_orgao_ou_missao', label: 'Noutro órgão, em comissão autorizada ou em missão parlamentar', color: tokens.colors.primaryLight },
  { key: 'justificadas', label: 'Falta justificada', color: tokens.colors.statusAmber },
  { key: 'quorum_votacao', label: 'Falta ao quórum de votação', color: '#B45309' },
  { key: 'por_justificar', label: 'Falta por justificar (ainda no prazo)', color: tokens.colors.statusNeutral },
  { key: 'nao_classificadas', label: 'Falta não classificada pela AR', color: '#9CA3AF' },
  { key: 'injustificadas', label: 'Falta injustificada', color: tokens.colors.statusRed },
];

const CATEGORY_STYLE = {
  present: { bg: tokens.colors.statusGreenBg, text: tokens.colors.statusGreen, border: tokens.colors.statusGreenBorder },
  other_body_or_mission: { bg: tokens.colors.contextEducationalBg, text: tokens.colors.primary, border: tokens.colors.borderWarm },
  justified: { bg: tokens.colors.statusAmberBg, text: '#92400E', border: tokens.colors.statusAmberBorder },
  missed_quorum_vote: { bg: tokens.colors.statusAmberBg, text: '#92400E', border: tokens.colors.statusAmberBorder },
  pending: { bg: tokens.colors.statusNeutralBg, text: tokens.colors.statusNeutral, border: tokens.colors.statusNeutralBorder },
  unclassified: { bg: tokens.colors.statusNeutralBg, text: tokens.colors.statusNeutral, border: tokens.colors.statusNeutralBorder },
  unjustified: { bg: tokens.colors.statusRedBg, text: tokens.colors.statusRed, border: tokens.colors.statusRedBorder },
};

const pct = (value) => (value === null || value === undefined ? '-' : `${value.toLocaleString('pt-PT', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`);
const day = (iso) => (iso ? new Date(`${iso}T12:00:00`).toLocaleDateString('pt-PT') : '');
const sessions = (n) => `${n.toLocaleString('pt-PT')} ${n === 1 ? 'reunião plenária' : 'reuniões plenárias'}`;

const box = {
  backgroundColor: tokens.colors.bgSecondary,
  border: `1px solid ${tokens.colors.border}`,
  borderRadius: '4px',
  padding: '20px 24px',
};
const heading = {
  fontFamily: tokens.fonts.body,
  fontSize: '0.875rem',
  fontWeight: 600,
  color: tokens.colors.textPrimary,
  margin: '0 0 12px 0',
};
const muted = { fontFamily: tokens.fonts.body, fontSize: '0.8125rem', color: tokens.colors.textMuted, margin: 0 };

/** The profile card: the latest legislature with lists (estatisticas.assiduidade). */
export const AttendanceCard = ({ assiduidade, onOpen }) => (
  <article
    style={{ ...box, padding: '20px', borderRadius: '6px', cursor: onOpen ? 'pointer' : 'default' }}
    onClick={onOpen}
    aria-label="Presenças nas reuniões plenárias"
  >
    <header style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '16px' }}>
      <div style={{ padding: '10px', backgroundColor: tokens.colors.primary, borderRadius: '4px' }}>
        <Activity style={{ width: '20px', height: '20px', color: '#FFFFFF' }} />
      </div>
      <span style={{ fontSize: '0.75rem', color: tokens.colors.textMuted }}>{legislatureName(assiduidade.legislatura)}</span>
    </header>
    <h4 style={{ fontSize: '0.75rem', fontWeight: 600, color: tokens.colors.primary, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '12px' }}>
      Presença no Plenário
    </h4>
    <div style={{ marginBottom: '8px' }}>
      <span style={{ fontSize: '2rem', fontWeight: 700, fontFamily: tokens.fonts.mono, color: tokens.colors.textPrimary }}>
        {pct(assiduidade.taxa_presenca)}
      </span>
      <span style={{ fontSize: '0.875rem', color: tokens.colors.textSecondary, marginLeft: '8px' }}>
        em {sessions(assiduidade.reunioes)}
      </span>
    </div>
    <p style={muted}>
      Conta as missões parlamentares e a presença noutro órgão. Só presenças no Plenário: {pct(assiduidade.taxa_presenca_estrita)}.
    </p>
  </article>
);

const Rate = ({ label, value, note }) => (
  <div style={{ ...box, padding: '16px 20px' }}>
    <p style={{ ...muted, fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>{label}</p>
    <p style={{ fontFamily: tokens.fonts.mono, fontSize: '1.75rem', fontWeight: 700, color: tokens.colors.textPrimary, margin: 0 }}>{pct(value)}</p>
    {note && <p style={{ ...muted, marginTop: '4px' }}>{note}</p>}
  </div>
);

const Categories = ({ contagens, reunioes }) => (
  <div style={box}>
    <h4 style={heading}>Como se repartem as {sessions(reunioes)}</h4>
    <div style={{ display: 'flex', height: '8px', borderRadius: '4px', overflow: 'hidden', backgroundColor: tokens.colors.bgTertiary, marginBottom: '16px' }}>
      {CATEGORY_ROWS.map(({ key, color }) => (
        <div key={key} style={{ width: `${(contagens[key] / reunioes) * 100}%`, backgroundColor: color }} />
      ))}
    </div>
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
      {CATEGORY_ROWS.map(({ key, label, color }) => (
        <div key={key} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.875rem', color: tokens.colors.textSecondary }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '2px', backgroundColor: color, flexShrink: 0 }} />
            {label}
          </span>
          <span style={{ fontFamily: tokens.fonts.mono, fontSize: '0.875rem', fontWeight: 600, color: tokens.colors.textPrimary }}>
            {contagens[key].toLocaleString('pt-PT')}
          </span>
        </div>
      ))}
    </div>
  </div>
);

const CodeChip = ({ code, category }) => {
  const style = CATEGORY_STYLE[category] || CATEGORY_STYLE.unclassified;
  return (
    <span style={{ display: 'inline-flex', padding: '2px 8px', borderRadius: '2px', fontSize: '0.75rem', fontFamily: tokens.fonts.mono, fontWeight: 600, backgroundColor: style.bg, color: style.text, border: `1px solid ${style.border}` }}>
      {code}
    </span>
  );
};

const Records = ({ registos, showGroup }) => {
  const [all, setAll] = useState(false);
  const shown = all ? registos : registos.slice(0, RECORDS_SHOWN);
  return (
    <div style={box}>
      <h4 style={heading}>Reuniões sem presença no Plenário</h4>
      {registos.length === 0 ? (
        <p style={muted}>Presente no Plenário em todas as reuniões das listas desta legislatura.</p>
      ) : (
        <>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
            <thead>
              <tr style={{ textAlign: 'left', color: tokens.colors.textMuted, fontSize: '0.75rem' }}>
                <th style={{ padding: '6px 8px' }}>Data</th>
                <th style={{ padding: '6px 8px' }}>Reunião</th>
                <th style={{ padding: '6px 8px' }}>Registo</th>
                {showGroup && <th style={{ padding: '6px 8px' }}>Grupo</th>}
              </tr>
            </thead>
            <tbody>
              {shown.map((r) => (
                <tr key={`${r.reuniao_id}-${r.codigo}`} style={{ borderTop: `1px solid ${tokens.colors.border}` }}>
                  <td style={{ padding: '8px', fontFamily: tokens.fonts.mono, whiteSpace: 'nowrap' }}>{day(r.data)}</td>
                  <td style={{ padding: '8px', color: tokens.colors.textSecondary }}>
                    {r.tipo_reuniao}{r.solene ? ' (fora da taxa)' : ''}
                  </td>
                  <td style={{ padding: '8px' }}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                      <CodeChip code={r.codigo} category={r.categoria} />
                      <span style={{ color: tokens.colors.textSecondary }}>{r.descricao}</span>
                    </span>
                  </td>
                  {showGroup && <td style={{ padding: '8px', color: tokens.colors.textSecondary }}>{r.grupo}</td>}
                </tr>
              ))}
            </tbody>
          </table>
          {registos.length > RECORDS_SHOWN && (
            <button
              type="button"
              onClick={() => setAll(!all)}
              style={{ marginTop: '12px', background: 'none', border: 'none', color: tokens.colors.primary, cursor: 'pointer', fontSize: '0.875rem', padding: 0 }}
            >
              {all ? 'Mostrar menos' : `Mostrar as ${registos.length} reuniões`}
            </button>
          )}
        </>
      )}
    </div>
  );
};

const Notice = ({ children }) => (
  <div style={{ ...box, display: 'flex', gap: '12px', alignItems: 'flex-start', backgroundColor: tokens.colors.bgWarm, borderColor: tokens.colors.borderWarm }}>
    <Info style={{ width: '18px', height: '18px', color: tokens.colors.primary, flexShrink: 0, marginTop: '2px' }} />
    <div style={{ fontSize: '0.875rem', color: tokens.colors.textSecondary }}>{children}</div>
  </div>
);

const Legislature = ({ leg, atualizado }) => {
  if (!leg.com_listas) {
    return (
      <Notice>
        A AR não publica listas de presenças da {legislatureName(leg.legislatura)}. Há listas a partir da VI Legislatura.
      </Notice>
    );
  }
  if (!leg.reunioes) {
    return (
      <Notice>
        Este deputado não consta das listas de presenças das reuniões ordinárias ou extraordinárias da {legislatureName(leg.legislatura)}.
      </Notice>
    );
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
        <Rate label="Taxa de presença" value={leg.taxa_presenca} note={`em ${sessions(leg.reunioes)}`} />
        <Rate label="Só presenças no Plenário" value={leg.taxa_presenca_estrita} note="sem missões nem outros órgãos" />
        <Rate label={`Todos os deputados da ${leg.legislatura}`} value={leg.legislatura_taxa_presenca} note="todos os lugares nas mesmas listas" />
      </div>
      {(leg.reunioes < FEW_MEETINGS || leg.em_curso) && (
        <Notice>
          {leg.reunioes < FEW_MEETINGS && <p style={{ margin: 0 }}>Poucas reuniões nesta legislatura: cada falta pesa vários pontos na taxa.</p>}
          {leg.em_curso && (
            <p style={{ margin: 0 }}>
              Legislatura em curso. Reuniões até {day(leg.ultima_reuniao)}, dados de {day(atualizado)}.
            </p>
          )}
        </Notice>
      )}
      <Categories contagens={leg.contagens} reunioes={leg.reunioes} />
      {leg.solenes.reunioes > 0 && (
        <p style={muted}>
          Mais {sessions(leg.solenes.reunioes)} solenes ou comemorativas, fora da taxa: presente em {leg.solenes.contagens.presente}.
        </p>
      )}
      <Records registos={leg.registos} showGroup={leg.grupos.length > 1} />
    </div>
  );
};

const AttendancePanel = ({ data }) => {
  const legislatures = data?.legislaturas || [];
  const [selected, setSelected] = useState(null);
  if (!data) {
    return <Notice>Os dados de presença não estão disponíveis de momento.</Notice>;
  }
  const leg = legislatures.find((l) => l.legislatura === selected) || legislatures[0];
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {legislatures.length > 1 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }} role="tablist" aria-label="Legislatura">
          {legislatures.map((l) => {
            const active = l.legislatura === leg.legislatura;
            return (
              <button
                key={l.legislatura}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => setSelected(l.legislatura)}
                style={{
                  padding: '6px 12px',
                  borderRadius: '4px',
                  border: `1px solid ${active ? tokens.colors.primary : tokens.colors.border}`,
                  backgroundColor: active ? tokens.colors.primary : tokens.colors.bgSecondary,
                  color: active ? '#FFFFFF' : tokens.colors.textSecondary,
                  fontFamily: tokens.fonts.mono,
                  fontSize: '0.8125rem',
                  cursor: 'pointer',
                }}
              >
                {l.legislatura}
              </button>
            );
          })}
        </div>
      )}
      {leg && <Legislature leg={leg} atualizado={data.atualizado} />}
      <div style={box}>
        <h4 style={heading}>Como se conta</h4>
        <ul style={{ margin: '0 0 16px 0', paddingLeft: '18px', fontSize: '0.8125rem', color: tokens.colors.textSecondary, display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <li><strong>Taxa de presença:</strong> {data.definicao.taxa_presenca}</li>
          <li><strong>Só presenças:</strong> {data.definicao.taxa_presenca_estrita}</li>
          <li>{data.definicao.solenes}</li>
          <li>{data.definicao.por_justificar}</li>
          <li>{data.definicao.cobertura} {data.definicao.motivo}</li>
        </ul>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '8px' }}>
          {data.codigos.map((c) => (
            <div key={c.codigo} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8125rem', color: tokens.colors.textSecondary }}>
              <CodeChip code={c.codigo} category={c.categoria} />
              {c.descricao}
            </div>
          ))}
        </div>
        <p style={{ ...muted, marginTop: '12px' }}>Fonte: listas de presenças do Plenário nos dados abertos da AR, via parlamento-aberto.</p>
      </div>
    </div>
  );
};

export default AttendancePanel;
