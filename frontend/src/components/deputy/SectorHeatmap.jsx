/**
 * SectorHeatmap Component
 *
 * Grid visualization showing sectors with declared interests vs active legislation.
 * Uses factual, non-accusatory language per political analyst recommendations.
 *
 * Part of the Constitutional Modernism design system.
 */

import React, { useState } from 'react';
import {
  AlertTriangle,
  Shield,
  FileText,
  Building2,
  Briefcase,
  Heart,
  Zap,
  Landmark,
  Factory,
  GraduationCap,
  Car,
  TreePine,
  Wifi,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Info,
} from 'lucide-react';
import { tokens } from '../../styles/tokens';

/**
 * Sector icons mapping
 */
const SECTOR_ICONS = {
  energia: Zap,
  saude: Heart,
  banca: Landmark,
  imobiliario: Building2,
  industria: Factory,
  educacao: GraduationCap,
  transportes: Car,
  ambiente: TreePine,
  telecomunicacoes: Wifi,
  default: Briefcase,
};

/**
 * Status configuration with non-accusatory language
 */
const STATUS_CONFIG = {
  attention: {
    label: 'Atenção',
    description: 'Interesse declarado em sector com legislação ativa',
    color: tokens.colors.sectorAttention,
    bg: tokens.colors.sectorAttentionBg,
    border: '#FDBA74',
  },
  context: {
    label: 'Contexto',
    description: 'Interesse em sector com alguma atividade legislativa',
    color: tokens.colors.sectorContext,
    bg: tokens.colors.sectorContextBg,
    border: tokens.colors.statusAmberBorder,
  },
  clear: {
    label: 'Sem interesse',
    description: 'Sem interesses declarados neste sector',
    color: tokens.colors.sectorClear,
    bg: tokens.colors.sectorClearBg,
    border: tokens.colors.statusGreenBorder,
  },
  noLegislation: {
    label: 'Sector inativo',
    description: 'Interesse declarado, sem legislação ativa',
    color: tokens.colors.textMuted,
    bg: tokens.colors.bgSecondary,
    border: tokens.colors.border,
  },
};

/**
 * SectorHeatmap - Grid showing sector interests vs legislation
 *
 * @param {Object} props
 * @param {Array} props.data - Array of sector data objects
 * @param {boolean} props.showLegend - Show status legend
 * @param {boolean} props.showDetails - Allow expanding rows for details
 */
const SectorHeatmap = ({
  data = [],
  showLegend = true,
  showDetails = true,
}) => {
  const [expandedSector, setExpandedSector] = useState(null);

  if (!data || data.length === 0) {
    return (
      <div
        style={{
          padding: '24px',
          textAlign: 'center',
          backgroundColor: tokens.colors.bgSecondary,
          border: `1px solid ${tokens.colors.border}`,
          borderRadius: '4px',
        }}
      >
        <Shield size={32} style={{ color: tokens.colors.statusGreen, marginBottom: '12px' }} />
        <p
          style={{
            margin: 0,
            fontFamily: tokens.fonts.body,
            fontSize: '0.875rem',
            color: tokens.colors.textSecondary,
          }}
        >
          Sem dados de sectores para apresentar
        </p>
      </div>
    );
  }

  // Categorize sectors by status
  const attentionSectors = data.filter(d => d.status === 'attention');
  const contextSectors = data.filter(d => d.status === 'context');

  return (
    <div style={{ fontFamily: tokens.fonts.body }}>
      {/* Summary bar */}
      {(attentionSectors.length > 0 || contextSectors.length > 0) && (
        <div
          style={{
            display: 'flex',
            gap: '16px',
            marginBottom: '16px',
            padding: '12px 16px',
            backgroundColor: tokens.colors.bgSecondary,
            border: `1px solid ${tokens.colors.border}`,
            borderRadius: '4px',
          }}
        >
          {attentionSectors.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div
                style={{
                  width: '12px',
                  height: '12px',
                  borderRadius: '2px',
                  backgroundColor: STATUS_CONFIG.attention.color,
                }}
              />
              <span style={{ fontSize: '0.8125rem', color: tokens.colors.textSecondary }}>
                <strong style={{ color: tokens.colors.textPrimary }}>{attentionSectors.length}</strong>{' '}
                {attentionSectors.length === 1 ? 'sector' : 'sectores'} com atenção
              </span>
            </div>
          )}
          {contextSectors.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div
                style={{
                  width: '12px',
                  height: '12px',
                  borderRadius: '2px',
                  backgroundColor: STATUS_CONFIG.context.color,
                }}
              />
              <span style={{ fontSize: '0.8125rem', color: tokens.colors.textSecondary }}>
                <strong style={{ color: tokens.colors.textPrimary }}>{contextSectors.length}</strong>{' '}
                {contextSectors.length === 1 ? 'sector' : 'sectores'} com contexto
              </span>
            </div>
          )}
        </div>
      )}

      {/* Legend */}
      {showLegend && (
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '12px',
            marginBottom: '16px',
            padding: '12px 16px',
            backgroundColor: tokens.colors.bgTertiary,
            borderRadius: '4px',
          }}
        >
          {Object.entries(STATUS_CONFIG).map(([key, config]) => (
            <div
              key={key}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <div
                style={{
                  width: '16px',
                  height: '16px',
                  borderRadius: '2px',
                  backgroundColor: config.bg,
                  border: `1px solid ${config.border}`,
                }}
              />
              <span style={{ fontSize: '0.75rem', color: tokens.colors.textMuted }}>
                {config.label}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Table header */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr 120px 100px',
          gap: '12px',
          padding: '10px 16px',
          backgroundColor: tokens.colors.bgTertiary,
          borderRadius: '4px 4px 0 0',
          fontSize: '0.75rem',
          fontWeight: 600,
          color: tokens.colors.textMuted,
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
        }}
      >
        <span>Sector</span>
        <span>Interesse Declarado</span>
        <span>Legislação Ativa</span>
        <span>Estado</span>
      </div>

      {/* Table rows */}
      <div
        style={{
          border: `1px solid ${tokens.colors.border}`,
          borderTop: 'none',
          borderRadius: '0 0 4px 4px',
          overflow: 'hidden',
        }}
      >
        {data.map((sector, index) => {
          const statusConfig = STATUS_CONFIG[sector.status] || STATUS_CONFIG.clear;
          const SectorIcon = SECTOR_ICONS[sector.sectorKey] || SECTOR_ICONS.default;
          const isExpanded = expandedSector === sector.sectorKey;

          return (
            <div key={sector.sectorKey || index}>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr 120px 100px',
                  gap: '12px',
                  alignItems: 'center',
                  padding: '14px 16px',
                  backgroundColor: statusConfig.bg,
                  borderBottom: index < data.length - 1 ? `1px solid ${tokens.colors.border}` : 'none',
                  cursor: showDetails && sector.details ? 'pointer' : 'default',
                }}
                onClick={() => {
                  if (showDetails && sector.details) {
                    setExpandedSector(isExpanded ? null : sector.sectorKey);
                  }
                }}
              >
                {/* Sector name */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <SectorIcon size={18} style={{ color: statusConfig.color, flexShrink: 0 }} />
                  <span
                    style={{
                      fontSize: '0.875rem',
                      fontWeight: 500,
                      color: tokens.colors.textPrimary,
                    }}
                  >
                    {sector.sectorName}
                  </span>
                  {showDetails && sector.details && (
                    isExpanded ? (
                      <ChevronUp size={16} style={{ color: tokens.colors.textMuted }} />
                    ) : (
                      <ChevronDown size={16} style={{ color: tokens.colors.textMuted }} />
                    )
                  )}
                </div>

                {/* Interest description */}
                <span
                  style={{
                    fontSize: '0.8125rem',
                    color: sector.interest ? tokens.colors.textSecondary : tokens.colors.textMuted,
                  }}
                >
                  {sector.interest || '—'}
                </span>

                {/* Legislation count */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <FileText size={14} style={{ color: tokens.colors.textMuted }} />
                  <span
                    style={{
                      fontFamily: tokens.fonts.mono,
                      fontSize: '0.875rem',
                      fontWeight: 600,
                      color: sector.legislationCount > 0 ? tokens.colors.textPrimary : tokens.colors.textMuted,
                    }}
                  >
                    {sector.legislationCount}
                  </span>
                  <span style={{ fontSize: '0.75rem', color: tokens.colors.textMuted }}>
                    {sector.legislationCount === 1 ? 'diploma' : 'diplomas'}
                  </span>
                </div>

                {/* Status badge */}
                <span
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    padding: '4px 8px',
                    borderRadius: '4px',
                    backgroundColor: `${statusConfig.color}20`,
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    color: statusConfig.color,
                    textTransform: 'uppercase',
                    letterSpacing: '0.3px',
                  }}
                >
                  {statusConfig.label}
                </span>
              </div>

              {/* Expanded details */}
              {isExpanded && sector.details && (
                <div
                  style={{
                    padding: '16px 16px 16px 48px',
                    backgroundColor: tokens.colors.bgPrimary,
                    borderBottom: index < data.length - 1 ? `1px solid ${tokens.colors.border}` : 'none',
                  }}
                >
                  {sector.details.interestDescription && (
                    <div style={{ marginBottom: '12px' }}>
                      <h5
                        style={{
                          margin: '0 0 6px 0',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          color: tokens.colors.textMuted,
                          textTransform: 'uppercase',
                        }}
                      >
                        Descrição do interesse
                      </h5>
                      <p
                        style={{
                          margin: 0,
                          fontSize: '0.875rem',
                          color: tokens.colors.textSecondary,
                          lineHeight: 1.6,
                        }}
                      >
                        {sector.details.interestDescription}
                      </p>
                    </div>
                  )}

                  {sector.details.legislation && sector.details.legislation.length > 0 && (
                    <div>
                      <h5
                        style={{
                          margin: '0 0 8px 0',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          color: tokens.colors.textMuted,
                          textTransform: 'uppercase',
                        }}
                      >
                        Legislação relacionada ({sector.details.legislation.length})
                      </h5>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {sector.details.legislation.map((leg, i) => (
                          <div
                            key={i}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '8px',
                              padding: '8px 12px',
                              backgroundColor: tokens.colors.bgSecondary,
                              borderRadius: '4px',
                            }}
                          >
                            <FileText size={14} style={{ color: tokens.colors.textMuted }} />
                            <span
                              style={{
                                flex: 1,
                                fontSize: '0.8125rem',
                                color: tokens.colors.textSecondary,
                              }}
                            >
                              {leg.title}
                            </span>
                            <span
                              style={{
                                fontSize: '0.75rem',
                                color: tokens.colors.textMuted,
                              }}
                            >
                              {leg.phase}
                            </span>
                            {leg.url && (
                              <a
                                href={leg.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                style={{ color: tokens.colors.primary }}
                                onClick={e => e.stopPropagation()}
                              >
                                <ExternalLink size={14} />
                              </a>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

/**
 * SectorOverlapSummary - Summary card showing overlap between interests and legislation
 */
export const SectorOverlapSummary = ({
  totalSectors,
  overlappingSectors,
  showContext = true,
}) => {
  const overlapPercentage = totalSectors > 0 ? (overlappingSectors / totalSectors) * 100 : 0;

  let statusLevel, statusColor;
  if (overlappingSectors === 0) {
    statusLevel = 'clear';
    statusColor = tokens.colors.statusGreen;
  } else if (overlappingSectors <= 2) {
    statusLevel = 'context';
    statusColor = tokens.colors.statusAmber;
  } else {
    statusLevel = 'attention';
    statusColor = tokens.colors.sectorAttention;
  }

  return (
    <div
      style={{
        backgroundColor: tokens.colors.bgSecondary,
        border: `2px solid ${statusColor}`,
        borderRadius: '4px',
        padding: '20px',
        fontFamily: tokens.fonts.body,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '16px' }}>
        <div
          style={{
            width: '48px',
            height: '48px',
            borderRadius: '4px',
            backgroundColor: `${statusColor}15`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          {statusLevel === 'clear' ? (
            <Shield size={24} style={{ color: statusColor }} />
          ) : (
            <AlertTriangle size={24} style={{ color: statusColor }} />
          )}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px', marginBottom: '8px' }}>
            <span
              style={{
                fontFamily: tokens.fonts.mono,
                fontSize: '2rem',
                fontWeight: 700,
                color: statusColor,
                lineHeight: 1,
              }}
            >
              {overlappingSectors}
            </span>
            <span
              style={{
                fontSize: '0.875rem',
                color: tokens.colors.textSecondary,
              }}
            >
              de {totalSectors} sectores com sobreposição
            </span>
          </div>

          {showContext && (
            <p
              style={{
                margin: 0,
                fontSize: '0.8125rem',
                color: tokens.colors.textMuted,
                lineHeight: 1.6,
              }}
            >
              {statusLevel === 'clear'
                ? 'Não foram identificados sectores onde o deputado tenha interesses declarados e onde existam propostas legislativas em discussão.'
                : `O deputado declarou interesses em ${overlappingSectors} ${overlappingSectors === 1 ? 'sector' : 'sectores'} onde existem atualmente propostas legislativas em discussão. Esta informação é apresentada para contexto e transparência.`}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

/**
 * VotingInterestCrossReference - Shows votes in sectors where deputy has interests
 * Uses factual, non-accusatory language
 */
export const VotingInterestCrossReference = ({
  votes = [],
  showExplanation = true,
}) => {
  if (votes.length === 0) {
    return null;
  }

  return (
    <div
      style={{
        backgroundColor: tokens.colors.bgSecondary,
        border: `1px solid ${tokens.colors.border}`,
        borderRadius: '4px',
        padding: '20px',
        fontFamily: tokens.fonts.body,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
        <Info size={18} style={{ color: tokens.colors.primary }} />
        <h4
          style={{
            margin: 0,
            fontSize: '0.9375rem',
            fontWeight: 600,
            color: tokens.colors.textPrimary,
          }}
        >
          Votações em sectores com interesse declarado
        </h4>
      </div>

      {showExplanation && (
        <p
          style={{
            margin: '0 0 16px 0',
            padding: '12px',
            backgroundColor: tokens.colors.contextImportantBg,
            borderLeft: `3px solid ${tokens.colors.contextImportantBorder}`,
            fontSize: '0.8125rem',
            color: tokens.colors.textSecondary,
            lineHeight: 1.6,
          }}
        >
          Esta secção apresenta votações em matérias relacionadas com sectores onde o deputado declarou
          interesses. A participação em votações é um dever parlamentar, mesmo em áreas onde o deputado
          tenha interesses declarados. A declaração prévia dos interesses cumpre os requisitos de transparência.
        </p>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {votes.map((vote, index) => (
          <div
            key={index}
            style={{
              display: 'grid',
              gridTemplateColumns: '100px 1fr 80px 80px',
              gap: '12px',
              alignItems: 'center',
              padding: '12px',
              backgroundColor: tokens.colors.bgPrimary,
              borderRadius: '4px',
            }}
          >
            <span
              style={{
                fontSize: '0.75rem',
                color: tokens.colors.textMuted,
              }}
            >
              {vote.date}
            </span>
            <span
              style={{
                fontSize: '0.8125rem',
                color: tokens.colors.textSecondary,
              }}
            >
              {vote.description}
            </span>
            <span
              style={{
                fontSize: '0.75rem',
                color: tokens.colors.statusAmber,
                fontWeight: 500,
              }}
            >
              {vote.sector}
            </span>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '4px 8px',
                borderRadius: '4px',
                fontSize: '0.75rem',
                fontWeight: 600,
                backgroundColor:
                  vote.vote === 'favor'
                    ? tokens.colors.statusGreenBg
                    : vote.vote === 'contra'
                      ? tokens.colors.statusRedBg
                      : tokens.colors.bgTertiary,
                color:
                  vote.vote === 'favor'
                    ? tokens.colors.statusGreen
                    : vote.vote === 'contra'
                      ? tokens.colors.statusRed
                      : tokens.colors.textMuted,
              }}
            >
              {vote.vote === 'favor' ? 'A favor' : vote.vote === 'contra' ? 'Contra' : 'Abstenção'}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SectorHeatmap;
