/**
 * InitiativeRecord
 *
 * How a deputy signs projetos and how they end, per legislature, and how the deputy compares
 * with their own group. Counts only: no career total and no ranking.
 */

import React from 'react';
import { tokens } from '../../styles/tokens';
import { legislatureName } from '../../utils/format';

const TYPE_LABELS = {
  J: 'Projetos de lei',
  R: 'Projetos de resolução',
  D: 'Projetos de deliberação',
};

const formatNumber = (value) => (value ?? 0).toLocaleString('pt-PT');
const formatRate = (value) => value.toLocaleString('pt-PT', { minimumFractionDigits: 1, maximumFractionDigits: 1 });

export const SIGNING_NOTE =
  'Nos dados da Assembleia, as iniciativas de um grupo parlamentar costumam listar todos os seus deputados como autores. Estes números mostram como o deputado assina, não quem redigiu cada iniciativa.';

export const APPROVAL_NOTE =
  'Conta apenas iniciativas com votação final, ou rejeitadas na generalidade. Iniciativas que caducaram com o fim da legislatura, retiradas ou ainda por votar aparecem à parte e não entram na taxa.';

const noteStyle = {
  margin: '8px 0 0 0',
  fontSize: '0.75rem',
  lineHeight: 1.5,
  color: tokens.colors.textMuted,
  fontFamily: tokens.fonts.body,
};

/**
 * SigningCounts: the three ways a deputy's projetos were signed, side by side, never totalled.
 */
export const SigningCounts = ({ assinatura, showNote = true }) => {
  if (!assinatura) return null;
  const items = [
    { key: 'grupo', label: 'Iniciativas do grupo parlamentar', value: assinatura.grupo_parlamentar },
    { key: 'restrita', label: 'Com subscrição restrita', value: assinatura.subscricao_restrita },
    { key: 'outros', label: 'Com outros grupos', value: assinatura.outros_grupos },
  ];
  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
        {items.map((item) => (
          <div key={item.key}>
            <div style={{
              fontFamily: tokens.fonts.mono,
              fontSize: '1.25rem',
              fontWeight: 600,
              color: tokens.colors.textPrimary,
            }}>
              {formatNumber(item.value)}
            </div>
            <div style={{ fontSize: '0.75rem', color: tokens.colors.textSecondary, lineHeight: 1.3 }}>
              {item.label}
            </div>
          </div>
        ))}
      </div>
      {showNote && <p style={noteStyle}>{SIGNING_NOTE}</p>}
    </div>
  );
};

/**
 * ApprovalLines: per type of projeto, the rate over decided initiatives and the undecided count.
 */
export const ApprovalLines = ({ aprovacao, aberta, showNote = true }) => {
  if (!aprovacao || aprovacao.length === 0) return null;
  return (
    <div>
      {aprovacao.map((tipo) => (
        <p key={tipo.codigo} style={{
          margin: '0 0 6px 0',
          fontSize: '0.8125rem',
          lineHeight: 1.5,
          color: tokens.colors.textSecondary,
          fontFamily: tokens.fonts.body,
        }}>
          <strong style={{ color: tokens.colors.textPrimary }}>{TYPE_LABELS[tipo.codigo] || tipo.descricao}:</strong>{' '}
          {tipo.taxa_aprovacao != null
            ? `taxa de aprovação de ${formatRate(tipo.taxa_aprovacao)}% das iniciativas votadas (${formatNumber(tipo.aprovadas)} de ${formatNumber(tipo.votadas)}).`
            : `${formatNumber(tipo.aprovadas)} aprovadas e ${formatNumber(tipo.rejeitadas)} rejeitadas; sem taxa com menos de 10 iniciativas votadas.`}
          {tipo.aprovadas_parcialmente > 0 && ` ${formatNumber(tipo.aprovadas_parcialmente)} aprovadas só em parte, numa votação ponto a ponto.`}
          {' '}{aberta ? 'Ainda sem votação final' : 'Sem votação final'}: {formatNumber(tipo.sem_votacao)}.
        </p>
      ))}
      {showNote && <p style={noteStyle}>{APPROVAL_NOTE}</p>}
    </div>
  );
};

/**
 * InitiativeRecordTable: one block per legislature, newest first.
 */
export const InitiativeRecordTable = ({ rows }) => {
  if (!rows || rows.length === 0) return null;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {rows.map((row) => (
        <div key={row.legislatura} style={{
          paddingBottom: '16px',
          borderBottom: `1px solid ${tokens.colors.border}`,
        }}>
          <h5 style={{
            margin: '0 0 10px 0',
            fontSize: '0.875rem',
            fontWeight: 600,
            color: tokens.colors.primary,
            fontFamily: tokens.fonts.body,
          }}>
            {legislatureName(row.legislatura)}{row.aberta ? ' (em curso)' : ''}
          </h5>
          <SigningCounts assinatura={row.assinatura} showNote={false} />
          <div style={{ marginTop: '10px' }}>
            <ApprovalLines aprovacao={row.aprovacao} aberta={row.aberta} showNote={false} />
          </div>
        </div>
      ))}
      <p style={{ ...noteStyle, marginTop: 0 }}>{SIGNING_NOTE}</p>
      <p style={{ ...noteStyle, marginTop: 0 }}>{APPROVAL_NOTE}</p>
    </div>
  );
};

/**
 * GroupComparison: the deputy against the people of their group seated at least half of the
 * legislature, per year of mandate. Shows the note instead of an average when there is none.
 */
export const GroupComparison = ({ comparacao, label, closedLabel = false }) => {
  if (!comparacao) return null;
  const legislature = comparacao.legislatura
    ? `${legislatureName(comparacao.legislatura)}${closedLabel ? ' (última concluída)' : ''}`
    : null;
  return (
    <div style={{ fontSize: '0.8125rem', color: tokens.colors.textSecondary, fontFamily: tokens.fonts.body }}>
      <div style={{ fontSize: '0.75rem', color: tokens.colors.textMuted, marginBottom: '4px' }}>
        {label}{legislature ? `, ${legislature}` : ''}
      </div>
      {comparacao.media_grupo_por_ano != null ? (
        <p style={{ margin: 0 }}>
          <strong style={{ color: tokens.colors.textPrimary, fontFamily: tokens.fonts.mono }}>
            {formatRate(comparacao.deputado_por_ano)}
          </strong>{' '}
          por ano de mandato; média do grupo {comparacao.grupo}:{' '}
          <strong style={{ fontFamily: tokens.fonts.mono }}>{formatRate(comparacao.media_grupo_por_ano)}</strong>{' '}
          ({formatNumber(comparacao.pares)} outros deputados do grupo com mandato em pelo menos metade da legislatura).
        </p>
      ) : (
        <p style={{ margin: 0 }}>{comparacao.nota}</p>
      )}
    </div>
  );
};

export default InitiativeRecordTable;
