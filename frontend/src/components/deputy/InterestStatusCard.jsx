/**
 * InterestStatusCard Component
 *
 * Factual status card for conflicts of interest tab.
 * Uses non-accusatory language per political analyst recommendations.
 * Never implies wrongdoing - only presents factual information.
 *
 * Part of the Constitutional Modernism design system.
 */

import React from 'react';
import { Shield, AlertTriangle, AlertCircle, HelpCircle, FileText, Clock, ExternalLink } from 'lucide-react';
import { tokens } from '../../styles/tokens';

/**
 * Status types and their configurations
 * Language is deliberately factual, never accusatory
 */
const statusConfig = {
  clear: {
    bg: tokens.colors.sectorClearBg,
    border: tokens.colors.statusGreenBorder,
    color: tokens.colors.statusGreen,
    Icon: Shield,
    title: 'Sem interesses em sectores com legislação ativa',
    description: 'Não foram identificados interesses declarados em sectores com propostas legislativas em discussão na atual legislatura.',
  },
  context: {
    bg: tokens.colors.sectorContextBg,
    border: tokens.colors.statusAmberBorder,
    color: tokens.colors.statusAmber,
    Icon: AlertTriangle,
    title: 'Interesses declarados em sectores com atividade legislativa',
    description: 'O deputado declarou atividades ou participações em sectores com propostas legislativas em discussão.',
  },
  attention: {
    bg: tokens.colors.sectorAttentionBg,
    border: '#FDBA74', // Orange border
    color: tokens.colors.sectorAttention,
    Icon: AlertCircle,
    title: 'Múltiplos interesses em sectores regulados',
    description: 'A declaração inclui participações em vários sectores sujeitos a regulação estatal.',
  },
  missing: {
    bg: tokens.colors.sectorMissingBg,
    border: tokens.colors.statusNeutralBorder,
    color: tokens.colors.statusNeutral,
    Icon: HelpCircle,
    title: 'Declaração não submetida ou incompleta',
    description: 'Não consta declaração de interesses atualizada ou há campos obrigatórios por preencher.',
    isMissing: true,
  },
};

/**
 * Determine status based on interest data
 */
const determineStatus = (data) => {
  if (!data || !data.hasDeclaration) {
    return 'missing';
  }

  // Check for multiple interests in regulated sectors
  const regulatedSectorCount = data.regulatedSectorInterests || 0;
  if (regulatedSectorCount >= 3) {
    return 'attention';
  }

  // Check for interests in sectors with active legislation
  if (data.hasInterestsInActiveLegislation) {
    return 'context';
  }

  return 'clear';
};

/**
 * InterestStatusCard - Displays factual status of interest declarations
 *
 * @param {Object} props
 * @param {Object} props.data - Interest declaration data
 * @param {boolean} props.data.hasDeclaration - Whether declaration exists
 * @param {boolean} props.data.hasInterestsInActiveLegislation - Has interests in sectors with active bills
 * @param {number} props.data.regulatedSectorInterests - Count of regulated sector interests
 * @param {string} props.data.lastUpdated - Last update date
 * @param {string} props.data.declarationUrl - URL to official declaration PDF
 * @param {number} props.data.daysOverdue - Days past legal deadline (if missing)
 * @param {boolean} props.showDetails - Whether to show detailed breakdown
 * @param {Function} props.onViewDetails - Callback when "view details" is clicked
 */
const InterestStatusCard = ({
  data = {},
  showDetails = true,
  onViewDetails,
}) => {
  const status = data.status || determineStatus(data);
  const config = statusConfig[status];
  const StatusIcon = config.Icon;

  const containerStyle = {
    backgroundColor: config.bg,
    border: `2px solid ${config.border}`,
    borderRadius: '4px',
    padding: '20px 24px',
    fontFamily: tokens.fonts.body,
  };

  const headerStyle = {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '16px',
  };

  const iconContainerStyle = {
    flexShrink: 0,
    width: '48px',
    height: '48px',
    borderRadius: '4px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: `${config.color}15`,
    border: `1px solid ${config.border}`,
  };

  const contentStyle = {
    flex: 1,
    minWidth: 0,
  };

  const titleStyle = {
    fontFamily: tokens.fonts.body,
    fontSize: '1rem',
    fontWeight: 600,
    color: tokens.colors.textPrimary,
    margin: 0,
    marginBottom: '8px',
  };

  const descriptionStyle = {
    fontFamily: tokens.fonts.body,
    fontSize: '0.875rem',
    lineHeight: 1.6,
    color: tokens.colors.textSecondary,
    margin: 0,
  };

  const metaStyle = {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '16px',
    marginTop: '16px',
    paddingTop: '16px',
    borderTop: `1px solid ${config.border}`,
  };

  const metaItemStyle = {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '0.8125rem',
    color: tokens.colors.textMuted,
  };

  const linkStyle = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    color: tokens.colors.primary,
    textDecoration: 'none',
    fontSize: '0.8125rem',
    fontWeight: 500,
    cursor: 'pointer',
  };

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <div style={iconContainerStyle}>
          <StatusIcon
            size={24}
            style={{ color: config.color }}
          />
        </div>
        <div style={contentStyle}>
          <h4 style={titleStyle}>{config.title}</h4>
          <p style={descriptionStyle}>{config.description}</p>

          {/* Missing declaration warning */}
          {config.isMissing && data.daysOverdue > 0 && (
            <div
              style={{
                marginTop: '12px',
                padding: '12px',
                backgroundColor: tokens.colors.statusRedBg,
                border: `1px solid ${tokens.colors.statusRedBorder}`,
                borderRadius: '2px',
              }}
            >
              <p
                style={{
                  margin: 0,
                  fontSize: '0.8125rem',
                  color: tokens.colors.statusRed,
                  fontWeight: 500,
                }}
              >
                Prazo legal: 30 dias após tomada de posse (Lei n.º 52/2019)
              </p>
              <p
                style={{
                  margin: '4px 0 0 0',
                  fontSize: '0.8125rem',
                  color: tokens.colors.textSecondary,
                }}
              >
                Dias em atraso: {data.daysOverdue}
              </p>
            </div>
          )}

          {/* Meta information */}
          {showDetails && !config.isMissing && (
            <div style={metaStyle}>
              {data.lastUpdated && (
                <div style={metaItemStyle}>
                  <Clock size={14} />
                  <span>Última atualização: {data.lastUpdated}</span>
                </div>
              )}
              {data.declarationUrl && (
                <a
                  href={data.declarationUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={linkStyle}
                >
                  <FileText size={14} />
                  <span>Ver declaração original (PDF)</span>
                  <ExternalLink size={12} />
                </a>
              )}
              {onViewDetails && (
                <button
                  onClick={onViewDetails}
                  style={{
                    ...linkStyle,
                    background: 'none',
                    border: 'none',
                    padding: 0,
                  }}
                >
                  Ver detalhes abaixo
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

/**
 * ExclusivityBadge - Shows exclusivity regime status
 */
export const ExclusivityBadge = ({ isExclusive, showExplanation = true }) => {
  const config = isExclusive
    ? {
        bg: tokens.colors.statusGreenBg,
        border: tokens.colors.statusGreenBorder,
        color: tokens.colors.statusGreen,
        label: 'Regime de Exclusividade',
        description: 'O deputado declarou dedicar-se exclusivamente ao mandato parlamentar.',
      }
    : {
        bg: tokens.colors.statusNeutralBg,
        border: tokens.colors.statusNeutralBorder,
        color: tokens.colors.textSecondary,
        label: 'Regime Não Exclusivo',
        description: 'O deputado exerce outras atividades profissionais paralelamente ao mandato (regime legalmente previsto).',
      };

  return (
    <div
      style={{
        backgroundColor: config.bg,
        border: `1px solid ${config.border}`,
        borderRadius: '4px',
        padding: '16px 20px',
        fontFamily: tokens.fonts.body,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          marginBottom: showExplanation ? '8px' : 0,
        }}
      >
        <span
          style={{
            display: 'inline-block',
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: config.color,
          }}
        />
        <span
          style={{
            fontSize: '0.875rem',
            fontWeight: 600,
            color: tokens.colors.textPrimary,
          }}
        >
          {config.label}
        </span>
      </div>
      {showExplanation && (
        <p
          style={{
            margin: 0,
            fontSize: '0.8125rem',
            lineHeight: 1.6,
            color: tokens.colors.textSecondary,
          }}
        >
          {config.description}
        </p>
      )}
    </div>
  );
};

/**
 * SectorInterestRow - Single row in sector interest list
 */
export const SectorInterestRow = ({
  sector,
  interest,
  legislationCount,
  status = 'clear',
}) => {
  const statusColors = {
    attention: { bg: tokens.colors.sectorAttentionBg, color: tokens.colors.sectorAttention },
    context: { bg: tokens.colors.sectorContextBg, color: tokens.colors.sectorContext },
    clear: { bg: tokens.colors.sectorClearBg, color: tokens.colors.sectorClear },
  };

  const colors = statusColors[status] || statusColors.clear;

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr 1fr auto',
        gap: '16px',
        alignItems: 'center',
        padding: '12px 16px',
        backgroundColor: colors.bg,
        borderRadius: '2px',
        marginBottom: '4px',
        fontFamily: tokens.fonts.body,
        fontSize: '0.875rem',
      }}
    >
      <span style={{ fontWeight: 500, color: tokens.colors.textPrimary }}>
        {sector}
      </span>
      <span style={{ color: tokens.colors.textSecondary }}>
        {interest || 'Nenhum'}
      </span>
      <span style={{ color: tokens.colors.textSecondary }}>
        {legislationCount} {legislationCount === 1 ? 'diploma' : 'diplomas'}
      </span>
      <span
        style={{
          fontSize: '0.75rem',
          fontWeight: 600,
          color: colors.color,
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
        }}
      >
        {status === 'attention' ? 'Atenção' : status === 'context' ? 'Contexto' : 'Sem interesse'}
      </span>
    </div>
  );
};

export default InterestStatusCard;
