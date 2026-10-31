/**
 * InterventionsSummaryBar Component
 *
 * Activity metrics dashboard for the Intervenções tab.
 * Shows interventions count, comparison to averages, and key metrics.
 *
 * Part of the Constitutional Modernism design system.
 */

import React from 'react';
import { MessageSquare, TrendingUp, TrendingDown, Minus, Video, Award, Calendar, BarChart2 } from 'lucide-react';
import { tokens } from '../../styles/tokens';
import { formatDecimal } from '../../utils/format';

/**
 * InterventionsSummaryBar - Activity metrics at the top of interventions tab
 *
 * @param {Object} props
 * @param {number} props.totalInterventions - Total number of interventions
 * @param {Object} props.comparison - The deputy against their group, per year of mandate
 *   (deputado_por_ano, media_grupo_por_ano, grupo, pares, legislatura, nota). No average while
 *   the legislature is open, for a short mandate or a small group: then only the note shows.
 * @param {number} props.videoCount - Number of interventions with video
 * @param {string} props.lastInterventionDate - Date of last intervention
 * @param {Object} props.typeBreakdown - Breakdown by intervention type
 */
const InterventionsSummaryBar = ({
  totalInterventions = 0,
  comparison = null,
  videoCount = 0,
  lastInterventionDate,
  typeBreakdown = {},
}) => {
  const groupAverage = comparison?.media_grupo_por_ano;
  const hasComparison = groupAverage != null && groupAverage > 0;
  const vsGroup = hasComparison ? ((comparison.deputado_por_ano - groupAverage) / groupAverage) * 100 : 0;

  const neutralStatus = {
    bg: tokens.colors.bgSecondary,
    border: tokens.colors.border,
    color: tokens.colors.textPrimary,
  };
  const config = {
    ...neutralStatus,
    label: hasComparison
      ? `${comparison.deputado_por_ano.toLocaleString('pt-PT')} por ano de mandato`
      : 'Sem comparação nesta legislatura',
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: '16px',
      marginBottom: '24px',
    }}>
      {/* Main metrics row */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '16px',
      }}>
        {/* Total Interventions Card */}
        <div style={{
          backgroundColor: config.bg,
          border: `2px solid ${config.border}`,
          borderRadius: '4px',
          padding: '20px',
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: '12px',
          }}>
            <div style={{
              width: '44px',
              height: '44px',
              borderRadius: '4px',
              backgroundColor: `${config.color}15`,
              border: `1px solid ${config.border}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <MessageSquare size={22} style={{ color: config.color }} />
            </div>
            <div>
              <p style={{
                fontFamily: tokens.fonts.mono,
                fontSize: '2rem',
                fontWeight: 700,
                color: config.color,
                margin: 0,
                lineHeight: 1,
              }}>
                {totalInterventions}
              </p>
              <p style={{
                fontFamily: tokens.fonts.body,
                fontSize: '0.8125rem',
                color: tokens.colors.textSecondary,
                margin: '4px 0 0 0',
              }}>
                Total intervenções
              </p>
              <p style={{
                fontFamily: tokens.fonts.body,
                fontSize: '0.75rem',
                color: tokens.colors.textMuted,
                margin: '2px 0 0 0',
              }}>
                {config.label}
              </p>
            </div>
          </div>
        </div>

        {/* Comparison Card */}
        <div style={{
          backgroundColor: tokens.colors.bgSecondary,
          border: `1px solid ${tokens.colors.border}`,
          borderRadius: '4px',
          padding: '20px',
        }}>
          <h4 style={{
            fontFamily: tokens.fonts.body,
            fontSize: '0.75rem',
            fontWeight: 600,
            color: tokens.colors.textMuted,
            margin: '0 0 12px 0',
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
          }}>
            Comparação
          </h4>
          {hasComparison ? (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}>
              <span style={{
                fontFamily: tokens.fonts.body,
                fontSize: '0.8125rem',
                color: tokens.colors.textSecondary,
              }}>
                vs. média do grupo {comparison.grupo} ({groupAverage.toLocaleString('pt-PT')} por ano de mandato)
              </span>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                color: tokens.colors.textPrimary,
              }}>
                {vsGroup >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                <span style={{
                  fontFamily: tokens.fonts.mono,
                  fontSize: '0.8125rem',
                  fontWeight: 600,
                }}>
                  {vsGroup >= 0 ? '+' : ''}{formatDecimal(vsGroup, 0)}%
                </span>
              </div>
            </div>
          ) : (
            <p style={{
              margin: 0,
              fontFamily: tokens.fonts.body,
              fontSize: '0.8125rem',
              color: tokens.colors.textSecondary,
            }}>
              {comparison?.nota || 'Sem comparação nesta legislatura'}
            </p>
          )}
          <p style={{
            margin: '8px 0 0 0',
            fontFamily: tokens.fonts.body,
            fontSize: '0.75rem',
            color: tokens.colors.textMuted,
          }}>
            Compara só com deputados do mesmo grupo que tiveram mandato em pelo menos metade da legislatura.
          </p>
        </div>

        {/* Video & Last Activity Card */}
        <div style={{
          backgroundColor: tokens.colors.bgSecondary,
          border: `1px solid ${tokens.colors.border}`,
          borderRadius: '4px',
          padding: '20px',
        }}>
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}>
            {/* Video count: the export has no videos yet, so show it only when there are */}
            {videoCount > 0 && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}>
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '4px',
                  backgroundColor: tokens.colors.statusGreenBg,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}>
                  <Video size={16} style={{
                    color: tokens.colors.statusGreen,
                  }} />
                </div>
                <div>
                  <span style={{
                    fontFamily: tokens.fonts.mono,
                    fontSize: '1rem',
                    fontWeight: 600,
                    color: tokens.colors.textPrimary,
                  }}>
                    {videoCount}
                  </span>
                  <span style={{
                    fontFamily: tokens.fonts.body,
                    fontSize: '0.8125rem',
                    color: tokens.colors.textSecondary,
                    marginLeft: '4px',
                  }}>
                    com vídeo
                  </span>
                </div>
              </div>
            )}
            {/* Last activity */}
            {lastInterventionDate && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}>
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '4px',
                  backgroundColor: tokens.colors.bgTertiary,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}>
                  <Calendar size={16} style={{ color: tokens.colors.textMuted }} />
                </div>
                <div>
                  <span style={{
                    fontFamily: tokens.fonts.body,
                    fontSize: '0.8125rem',
                    color: tokens.colors.textSecondary,
                  }}>
                    Última: {new Date(lastInterventionDate).toLocaleDateString('pt-PT')}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Type breakdown bar */}
      {Object.keys(typeBreakdown).length > 0 && (
        <div style={{
          backgroundColor: tokens.colors.bgSecondary,
          border: `1px solid ${tokens.colors.border}`,
          borderRadius: '4px',
          padding: '16px 20px',
        }}>
          <h4 style={{
            fontFamily: tokens.fonts.body,
            fontSize: '0.75rem',
            fontWeight: 600,
            color: tokens.colors.textMuted,
            margin: '0 0 12px 0',
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
          }}>
            Por tipo de intervenção
          </h4>

          {/* Stacked bar */}
          <div style={{
            height: '12px',
            borderRadius: '6px',
            backgroundColor: tokens.colors.bgTertiary,
            overflow: 'hidden',
            display: 'flex',
            marginBottom: '12px',
          }}>
            {Object.entries(typeBreakdown).map(([type, count], index) => {
              const colors = [
                tokens.colors.primary,
                tokens.colors.statusAmber,
                tokens.colors.statusGreen,
                tokens.colors.infoSecondary,
                tokens.colors.orange,
              ];
              return (
                <div
                  key={type}
                  style={{
                    width: `${(count / totalInterventions) * 100}%`,
                    backgroundColor: colors[index % colors.length],
                  }}
                />
              );
            })}
          </div>

          {/* Legend */}
          <div style={{
            display: 'flex',
            gap: '16px',
            flexWrap: 'wrap',
          }}>
            {Object.entries(typeBreakdown).map(([type, count], index) => {
              const colors = [
                tokens.colors.primary,
                tokens.colors.statusAmber,
                tokens.colors.statusGreen,
                tokens.colors.infoSecondary,
                tokens.colors.orange,
              ];
              return (
                <div key={type} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}>
                  <span style={{
                    width: '10px',
                    height: '10px',
                    borderRadius: '2px',
                    backgroundColor: colors[index % colors.length],
                  }} />
                  <span style={{
                    fontFamily: tokens.fonts.body,
                    fontSize: '0.75rem',
                    color: tokens.colors.textSecondary,
                  }}>
                    {type}: {count}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

/**
 * ActivityBadge - Achievement badge for exceptional activity
 */
export const ActivityBadge = ({
  type = 'topQuestioner',
  label,
  description,
}) => {
  const badgeConfig = {
    topQuestioner: {
      bg: tokens.colors.statusGreenBg,
      border: tokens.colors.statusGreenBorder,
      color: tokens.colors.statusGreen,
      Icon: Award,
      defaultLabel: 'Top Questionador',
      defaultDescription: 'Acima do percentil 90 em perguntas ao Governo',
    },
    policyExpert: {
      bg: tokens.colors.contextEducationalBg,
      border: tokens.colors.contextEducationalBorder,
      color: tokens.colors.primary,
      Icon: BarChart2,
      defaultLabel: 'Especialista Temático',
      defaultDescription: 'Foco consistente em área política específica',
    },
    regionalAdvocate: {
      bg: tokens.colors.statusAmberBg,
      border: tokens.colors.statusAmberBorder,
      color: tokens.colors.statusAmber,
      Icon: MessageSquare,
      defaultLabel: 'Defensor Regional',
      defaultDescription: 'Forte ligação às questões do círculo eleitoral',
    },
  };

  const config = badgeConfig[type] || badgeConfig.topQuestioner;
  const BadgeIcon = config.Icon;

  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '8px',
      backgroundColor: config.bg,
      border: `1px solid ${config.border}`,
      borderRadius: '4px',
      padding: '8px 12px',
    }}>
      <BadgeIcon size={16} style={{ color: config.color }} />
      <div>
        <span style={{
          fontFamily: tokens.fonts.body,
          fontSize: '0.8125rem',
          fontWeight: 600,
          color: config.color,
        }}>
          {label || config.defaultLabel}
        </span>
        {(description || config.defaultDescription) && (
          <p style={{
            fontFamily: tokens.fonts.body,
            fontSize: '0.75rem',
            color: tokens.colors.textMuted,
            margin: '2px 0 0 0',
          }}>
            {description || config.defaultDescription}
          </p>
        )}
      </div>
    </div>
  );
};

/**
 * VideoIndicator - Prominent video availability indicator
 */
export const VideoIndicator = ({ hasVideo, videoUrl }) => {
  if (!hasVideo) return null;

  return (
    <a
      href={videoUrl}
      target="_blank"
      rel="noopener noreferrer"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        backgroundColor: tokens.colors.statusGreenBg,
        border: `1px solid ${tokens.colors.statusGreenBorder}`,
        borderRadius: '2px',
        padding: '4px 8px',
        fontSize: '0.75rem',
        fontWeight: 600,
        color: tokens.colors.statusGreen,
        textDecoration: 'none',
        cursor: 'pointer',
        transition: 'background-color 0.15s ease',
      }}
    >
      <Video size={12} />
      <span>Ver vídeo</span>
    </a>
  );
};

export default InterventionsSummaryBar;
