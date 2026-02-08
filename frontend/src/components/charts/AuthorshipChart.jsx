/**
 * AuthorshipChart Component
 *
 * Visualizes initiative authorship patterns (Individual vs Group vs Cross-party).
 * Pure CSS/SVG implementation without external charting libraries.
 *
 * Part of the Constitutional Modernism design system.
 */

import React from 'react';
import { User, Users, Handshake, FileText } from 'lucide-react';
import { tokens } from '../../styles/tokens';

/**
 * AuthorshipChart - Horizontal bar chart showing authorship breakdown
 *
 * @param {Object} props
 * @param {number} props.individual - Count of individual initiatives
 * @param {number} props.party - Count of party/group initiatives
 * @param {number} props.crossParty - Count of cross-party initiatives
 * @param {boolean} props.showLegend - Show legend below chart
 * @param {boolean} props.showCounts - Show counts next to bars
 * @param {string} props.size - 'compact' | 'normal' | 'large'
 */
const AuthorshipChart = ({
  individual = 0,
  party = 0,
  crossParty = 0,
  showLegend = true,
  showCounts = true,
  size = 'normal',
}) => {
  const total = individual + party + crossParty;

  if (total === 0) {
    return (
      <div
        style={{
          padding: '20px',
          textAlign: 'center',
          backgroundColor: tokens.colors.bgTertiary,
          borderRadius: '4px',
          fontFamily: tokens.fonts.body,
          fontSize: '0.875rem',
          color: tokens.colors.textMuted,
        }}
      >
        Sem dados de autoria disponíveis
      </div>
    );
  }

  const categories = [
    {
      key: 'individual',
      label: 'Individual',
      count: individual,
      percentage: (individual / total) * 100,
      color: tokens.colors.primary,
      Icon: User,
      description: 'Iniciativas apresentadas individualmente pelo deputado',
    },
    {
      key: 'party',
      label: 'Grupo Parlamentar',
      count: party,
      percentage: (party / total) * 100,
      color: tokens.colors.statusAmber,
      Icon: Users,
      description: 'Iniciativas do grupo parlamentar',
    },
    {
      key: 'crossParty',
      label: 'Transpartidário',
      count: crossParty,
      percentage: (crossParty / total) * 100,
      color: tokens.colors.statusGreen,
      Icon: Handshake,
      description: 'Iniciativas com deputados de outros partidos',
    },
  ].filter(c => c.count > 0);

  const sizeConfig = {
    compact: { barHeight: 12, gap: 8, fontSize: '0.75rem', iconSize: 14 },
    normal: { barHeight: 20, gap: 12, fontSize: '0.8125rem', iconSize: 16 },
    large: { barHeight: 28, gap: 16, fontSize: '0.875rem', iconSize: 18 },
  };

  const s = sizeConfig[size];

  return (
    <div style={{ fontFamily: tokens.fonts.body }}>
      {/* Stacked bar */}
      <div
        style={{
          height: s.barHeight,
          borderRadius: '4px',
          backgroundColor: tokens.colors.bgTertiary,
          overflow: 'hidden',
          display: 'flex',
        }}
      >
        {categories.map((cat, index) => (
          <div
            key={cat.key}
            style={{
              width: `${cat.percentage}%`,
              height: '100%',
              backgroundColor: cat.color,
              transition: 'width 0.3s ease',
            }}
            title={`${cat.label}: ${cat.count} (${cat.percentage.toFixed(1)}%)`}
          />
        ))}
      </div>

      {/* Legend */}
      {showLegend && (
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: s.gap,
            marginTop: s.gap,
          }}
        >
          {categories.map(cat => {
            const CatIcon = cat.Icon;
            return (
              <div
                key={cat.key}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <CatIcon size={s.iconSize} style={{ color: cat.color }} />
                <span
                  style={{
                    fontSize: s.fontSize,
                    color: tokens.colors.textSecondary,
                  }}
                >
                  {cat.label}:
                </span>
                {showCounts && (
                  <span
                    style={{
                      fontFamily: tokens.fonts.mono,
                      fontSize: s.fontSize,
                      fontWeight: 600,
                      color: tokens.colors.textPrimary,
                    }}
                  >
                    {cat.count}
                  </span>
                )}
                <span
                  style={{
                    fontSize: s.fontSize,
                    color: tokens.colors.textMuted,
                  }}
                >
                  ({cat.percentage.toFixed(0)}%)
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

/**
 * AuthorshipBreakdown - Detailed breakdown with descriptions
 */
export const AuthorshipBreakdown = ({
  individual = 0,
  party = 0,
  crossParty = 0,
}) => {
  const total = individual + party + crossParty;

  const categories = [
    {
      key: 'individual',
      label: 'Iniciativas Individuais',
      count: individual,
      percentage: total > 0 ? (individual / total) * 100 : 0,
      color: tokens.colors.primary,
      Icon: User,
      description: 'Projetos e propostas apresentados individualmente pelo deputado',
    },
    {
      key: 'party',
      label: 'Iniciativas do Grupo Parlamentar',
      count: party,
      percentage: total > 0 ? (party / total) * 100 : 0,
      color: tokens.colors.statusAmber,
      Icon: Users,
      description: 'Iniciativas subscritas pelo grupo parlamentar ou múltiplos deputados do mesmo partido',
    },
    {
      key: 'crossParty',
      label: 'Iniciativas Transpartidárias',
      count: crossParty,
      percentage: total > 0 ? (crossParty / total) * 100 : 0,
      color: tokens.colors.statusGreen,
      Icon: Handshake,
      description: 'Iniciativas conjuntas com deputados de outros partidos, demonstrando colaboração interpartidária',
    },
  ];

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
      }}
    >
      {categories.map(cat => {
        const CatIcon = cat.Icon;
        return (
          <div
            key={cat.key}
            style={{
              display: 'flex',
              alignItems: 'stretch',
              gap: '12px',
              padding: '14px 16px',
              backgroundColor: cat.count > 0 ? `${cat.color}08` : tokens.colors.bgSecondary,
              border: `1px solid ${cat.count > 0 ? cat.color : tokens.colors.border}`,
              borderRadius: '4px',
            }}
          >
            <div
              style={{
                width: '40px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              <CatIcon
                size={22}
                style={{ color: cat.count > 0 ? cat.color : tokens.colors.textMuted }}
              />
            </div>
            <div style={{ flex: 1 }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'baseline',
                  gap: '8px',
                  marginBottom: '4px',
                }}
              >
                <span
                  style={{
                    fontFamily: tokens.fonts.body,
                    fontSize: '0.875rem',
                    fontWeight: 600,
                    color: tokens.colors.textPrimary,
                  }}
                >
                  {cat.label}
                </span>
                <span
                  style={{
                    fontFamily: tokens.fonts.mono,
                    fontSize: '1rem',
                    fontWeight: 700,
                    color: cat.color,
                  }}
                >
                  {cat.count}
                </span>
                {total > 0 && (
                  <span
                    style={{
                      fontFamily: tokens.fonts.body,
                      fontSize: '0.8125rem',
                      color: tokens.colors.textMuted,
                    }}
                  >
                    ({cat.percentage.toFixed(0)}%)
                  </span>
                )}
              </div>
              <p
                style={{
                  margin: 0,
                  fontFamily: tokens.fonts.body,
                  fontSize: '0.8125rem',
                  color: tokens.colors.textSecondary,
                  lineHeight: 1.5,
                }}
              >
                {cat.description}
              </p>
              {/* Progress bar */}
              {total > 0 && (
                <div
                  style={{
                    marginTop: '8px',
                    height: '6px',
                    borderRadius: '3px',
                    backgroundColor: tokens.colors.bgTertiary,
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      width: `${cat.percentage}%`,
                      height: '100%',
                      backgroundColor: cat.color,
                      transition: 'width 0.3s ease',
                    }}
                  />
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};

/**
 * AuthorshipCompact - Minimal authorship indicator
 */
export const AuthorshipCompact = ({ type, count }) => {
  const configs = {
    individual: { Icon: User, label: 'Individual', color: tokens.colors.primary },
    party: { Icon: Users, label: 'Grupo', color: tokens.colors.statusAmber },
    crossParty: { Icon: Handshake, label: 'Trans.', color: tokens.colors.statusGreen },
  };

  const config = configs[type];
  if (!config) return null;

  const TypeIcon = config.Icon;

  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        padding: '4px 8px',
        backgroundColor: `${config.color}15`,
        border: `1px solid ${config.color}30`,
        borderRadius: '4px',
      }}
    >
      <TypeIcon size={14} style={{ color: config.color }} />
      <span
        style={{
          fontFamily: tokens.fonts.body,
          fontSize: '0.75rem',
          color: config.color,
          fontWeight: 500,
        }}
      >
        {config.label}
      </span>
      {count !== undefined && (
        <span
          style={{
            fontFamily: tokens.fonts.mono,
            fontSize: '0.75rem',
            fontWeight: 600,
            color: config.color,
          }}
        >
          {count}
        </span>
      )}
    </div>
  );
};

/**
 * CollaborationIndicator - Shows cross-party collaboration level
 */
export const CollaborationIndicator = ({
  crossPartyCount,
  totalCount,
  showLabel = true,
}) => {
  const ratio = totalCount > 0 ? (crossPartyCount / totalCount) * 100 : 0;

  let level, color, label;
  if (ratio >= 20) {
    level = 'high';
    color = tokens.colors.statusGreen;
    label = 'Elevada colaboração transpartidária';
  } else if (ratio >= 10) {
    level = 'moderate';
    color = tokens.colors.statusAmber;
    label = 'Colaboração transpartidária moderada';
  } else if (ratio > 0) {
    level = 'low';
    color = tokens.colors.primary;
    label = 'Alguma colaboração transpartidária';
  } else {
    level = 'none';
    color = tokens.colors.textMuted;
    label = 'Sem colaboração transpartidária registada';
  }

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        padding: '10px 14px',
        backgroundColor: `${color}10`,
        border: `1px solid ${color}30`,
        borderRadius: '4px',
      }}
    >
      <Handshake size={18} style={{ color }} />
      <div>
        <div
          style={{
            display: 'flex',
            alignItems: 'baseline',
            gap: '6px',
          }}
        >
          <span
            style={{
              fontFamily: tokens.fonts.mono,
              fontSize: '1rem',
              fontWeight: 700,
              color,
            }}
          >
            {crossPartyCount}
          </span>
          <span
            style={{
              fontFamily: tokens.fonts.body,
              fontSize: '0.8125rem',
              color: tokens.colors.textSecondary,
            }}
          >
            de {totalCount} ({ratio.toFixed(0)}%)
          </span>
        </div>
        {showLabel && (
          <span
            style={{
              fontFamily: tokens.fonts.body,
              fontSize: '0.75rem',
              color: tokens.colors.textMuted,
            }}
          >
            {label}
          </span>
        )}
      </div>
    </div>
  );
};

export default AuthorshipChart;
