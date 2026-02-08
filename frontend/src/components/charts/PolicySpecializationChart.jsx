/**
 * PolicySpecializationChart Component
 *
 * Horizontal bar chart showing policy area specialization.
 * Displays top themes with counts and percentages.
 *
 * Part of the Constitutional Modernism design system.
 */

import React from 'react';
import { Target, TrendingUp, Info } from 'lucide-react';
import { tokens } from '../../styles/tokens';

/**
 * Policy area color palette
 */
const POLICY_COLORS = [
  tokens.colors.primary,
  tokens.colors.statusAmber,
  tokens.colors.statusGreen,
  tokens.colors.infoSecondary,
  '#8B5CF6', // Purple
  '#EC4899', // Pink
  '#F97316', // Orange
  '#14B8A6', // Teal
];

/**
 * PolicySpecializationChart - Horizontal bar chart for policy areas
 *
 * @param {Object} props
 * @param {Array} props.data - Array of { area: string, count: number } objects
 * @param {number} props.maxDisplay - Maximum number of areas to show (default: 6)
 * @param {boolean} props.showPercentages - Show percentage values
 * @param {boolean} props.showSpecialization - Show specialization indicator
 * @param {string} props.deputyName - Deputy name for context
 */
const PolicySpecializationChart = ({
  data = [],
  maxDisplay = 6,
  showPercentages = true,
  showSpecialization = true,
  deputyName,
}) => {
  if (!data || data.length === 0) {
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
        Sem dados de especialização disponíveis
      </div>
    );
  }

  // Sort by count and take top N
  const sortedData = [...data].sort((a, b) => b.count - a.count).slice(0, maxDisplay);
  const total = data.reduce((sum, d) => sum + d.count, 0);
  const maxCount = Math.max(...sortedData.map(d => d.count));

  // Calculate specialization level
  const topAreaPercentage = sortedData[0] ? (sortedData[0].count / total) * 100 : 0;
  const specializationLevel = topAreaPercentage >= 40
    ? 'high'
    : topAreaPercentage >= 25
      ? 'moderate'
      : 'diverse';

  const specializationConfig = {
    high: {
      label: 'Especialização elevada',
      description: `Foco concentrado em ${sortedData[0]?.area}`,
      color: tokens.colors.statusGreen,
    },
    moderate: {
      label: 'Especialização moderada',
      description: 'Atividade distribuída por áreas principais',
      color: tokens.colors.statusAmber,
    },
    diverse: {
      label: 'Atuação diversificada',
      description: 'Participação em múltiplas áreas temáticas',
      color: tokens.colors.primary,
    },
  };

  const spec = specializationConfig[specializationLevel];

  return (
    <div style={{ fontFamily: tokens.fonts.body }}>
      {/* Specialization indicator */}
      {showSpecialization && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            padding: '12px 16px',
            backgroundColor: `${spec.color}10`,
            border: `1px solid ${spec.color}30`,
            borderRadius: '4px',
            marginBottom: '16px',
          }}
        >
          <Target size={18} style={{ color: spec.color }} />
          <div>
            <span
              style={{
                display: 'block',
                fontSize: '0.875rem',
                fontWeight: 600,
                color: tokens.colors.textPrimary,
              }}
            >
              {spec.label}
            </span>
            <span
              style={{
                fontSize: '0.8125rem',
                color: tokens.colors.textSecondary,
              }}
            >
              {spec.description}
            </span>
          </div>
        </div>
      )}

      {/* Bar chart */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {sortedData.map((item, index) => {
          const percentage = (item.count / total) * 100;
          const barWidth = (item.count / maxCount) * 100;
          const color = POLICY_COLORS[index % POLICY_COLORS.length];

          return (
            <div key={item.area} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              {/* Area label */}
              <div
                style={{
                  width: '140px',
                  flexShrink: 0,
                  fontSize: '0.8125rem',
                  color: tokens.colors.textSecondary,
                  textAlign: 'right',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
                title={item.area}
              >
                {item.area}
              </div>

              {/* Bar container */}
              <div style={{ flex: 1, position: 'relative' }}>
                <div
                  style={{
                    height: '24px',
                    borderRadius: '4px',
                    backgroundColor: tokens.colors.bgTertiary,
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      width: `${barWidth}%`,
                      height: '100%',
                      backgroundColor: color,
                      borderRadius: '4px',
                      transition: 'width 0.3s ease',
                      display: 'flex',
                      alignItems: 'center',
                      paddingLeft: '8px',
                    }}
                  >
                    {barWidth > 30 && (
                      <span
                        style={{
                          fontFamily: tokens.fonts.mono,
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          color: '#fff',
                        }}
                      >
                        {item.count}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Count and percentage */}
              <div
                style={{
                  width: '80px',
                  flexShrink: 0,
                  display: 'flex',
                  alignItems: 'baseline',
                  gap: '4px',
                }}
              >
                {barWidth <= 30 && (
                  <span
                    style={{
                      fontFamily: tokens.fonts.mono,
                      fontSize: '0.875rem',
                      fontWeight: 600,
                      color: tokens.colors.textPrimary,
                    }}
                  >
                    {item.count}
                  </span>
                )}
                {showPercentages && (
                  <span
                    style={{
                      fontFamily: tokens.fonts.body,
                      fontSize: '0.75rem',
                      color: tokens.colors.textMuted,
                    }}
                  >
                    ({percentage.toFixed(0)}%)
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Show "others" if there are more */}
      {data.length > maxDisplay && (
        <div
          style={{
            marginTop: '12px',
            paddingTop: '12px',
            borderTop: `1px solid ${tokens.colors.border}`,
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: '0.8125rem',
            color: tokens.colors.textMuted,
          }}
        >
          <Info size={14} />
          <span>
            +{data.length - maxDisplay} outras áreas ({data.slice(maxDisplay).reduce((sum, d) => sum + d.count, 0)} iniciativas)
          </span>
        </div>
      )}
    </div>
  );
};

/**
 * PolicyRadar - Radar/spider chart for multi-dimensional policy assessment
 * Pure SVG implementation
 */
export const PolicyRadar = ({
  data = [],
  size = 200,
  maxValue,
  showLabels = true,
  fillColor = tokens.colors.primary,
}) => {
  if (!data || data.length < 3) {
    return (
      <div
        style={{
          width: size,
          height: size,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: tokens.colors.bgTertiary,
          borderRadius: '4px',
          fontFamily: tokens.fonts.body,
          fontSize: '0.75rem',
          color: tokens.colors.textMuted,
        }}
      >
        Mínimo 3 dimensões necessárias
      </div>
    );
  }

  const center = size / 2;
  const radius = (size - 60) / 2; // Leave space for labels
  const angleStep = (2 * Math.PI) / data.length;
  const max = maxValue || Math.max(...data.map(d => d.value), 1);

  // Calculate points for each axis
  const points = data.map((d, i) => {
    const angle = i * angleStep - Math.PI / 2; // Start from top
    const normalizedValue = d.value / max;
    return {
      x: center + Math.cos(angle) * radius * normalizedValue,
      y: center + Math.sin(angle) * radius * normalizedValue,
      labelX: center + Math.cos(angle) * (radius + 20),
      labelY: center + Math.sin(angle) * (radius + 20),
      label: d.label,
      value: d.value,
    };
  });

  // Generate polygon path
  const polygonPath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ') + ' Z';

  // Generate grid lines
  const gridLevels = [0.25, 0.5, 0.75, 1];

  return (
    <svg width={size} height={size} style={{ display: 'block' }}>
      {/* Grid circles */}
      {gridLevels.map((level, i) => (
        <circle
          key={i}
          cx={center}
          cy={center}
          r={radius * level}
          fill="none"
          stroke={tokens.colors.border}
          strokeWidth="1"
          strokeDasharray={i < gridLevels.length - 1 ? '4,4' : undefined}
        />
      ))}

      {/* Axis lines */}
      {data.map((_, i) => {
        const angle = i * angleStep - Math.PI / 2;
        return (
          <line
            key={i}
            x1={center}
            y1={center}
            x2={center + Math.cos(angle) * radius}
            y2={center + Math.sin(angle) * radius}
            stroke={tokens.colors.border}
            strokeWidth="1"
          />
        );
      })}

      {/* Data polygon */}
      <path
        d={polygonPath}
        fill={`${fillColor}30`}
        stroke={fillColor}
        strokeWidth="2"
      />

      {/* Data points */}
      {points.map((p, i) => (
        <circle
          key={i}
          cx={p.x}
          cy={p.y}
          r="4"
          fill={fillColor}
          stroke={tokens.colors.bgPrimary}
          strokeWidth="2"
        >
          <title>{`${p.label}: ${p.value}`}</title>
        </circle>
      ))}

      {/* Labels */}
      {showLabels && points.map((p, i) => (
        <text
          key={i}
          x={p.labelX}
          y={p.labelY}
          textAnchor="middle"
          dominantBaseline="middle"
          fill={tokens.colors.textSecondary}
          fontSize="11"
          fontFamily={tokens.fonts.body}
        >
          {p.label.length > 12 ? p.label.substring(0, 10) + '...' : p.label}
        </text>
      ))}
    </svg>
  );
};

/**
 * PolicyComparisonChart - Compare deputy's focus vs party/parliament average
 */
export const PolicyComparisonChart = ({
  deputyData = [],
  partyData = [],
  parliamentData = [],
  showDeputy = true,
  showParty = true,
  showParliament = true,
  maxDisplay = 5,
}) => {
  // Get all unique areas
  const allAreas = new Set([
    ...deputyData.map(d => d.area),
    ...partyData.map(d => d.area),
    ...parliamentData.map(d => d.area),
  ]);

  // Create comparison data
  const comparisonData = Array.from(allAreas)
    .map(area => ({
      area,
      deputy: deputyData.find(d => d.area === area)?.percentage || 0,
      party: partyData.find(d => d.area === area)?.percentage || 0,
      parliament: parliamentData.find(d => d.area === area)?.percentage || 0,
    }))
    .sort((a, b) => b.deputy - a.deputy)
    .slice(0, maxDisplay);

  return (
    <div style={{ fontFamily: tokens.fonts.body }}>
      {/* Legend */}
      <div
        style={{
          display: 'flex',
          gap: '16px',
          marginBottom: '16px',
        }}
      >
        {showDeputy && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span
              style={{
                width: '12px',
                height: '12px',
                borderRadius: '2px',
                backgroundColor: tokens.colors.primary,
              }}
            />
            <span style={{ fontSize: '0.8125rem', color: tokens.colors.textSecondary }}>
              Deputado
            </span>
          </div>
        )}
        {showParty && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span
              style={{
                width: '12px',
                height: '12px',
                borderRadius: '2px',
                backgroundColor: tokens.colors.statusAmber,
              }}
            />
            <span style={{ fontSize: '0.8125rem', color: tokens.colors.textSecondary }}>
              Grupo Parlamentar
            </span>
          </div>
        )}
        {showParliament && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span
              style={{
                width: '12px',
                height: '12px',
                borderRadius: '2px',
                backgroundColor: tokens.colors.textMuted,
              }}
            />
            <span style={{ fontSize: '0.8125rem', color: tokens.colors.textSecondary }}>
              Parlamento
            </span>
          </div>
        )}
      </div>

      {/* Bars */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {comparisonData.map((item, index) => (
          <div key={item.area}>
            <div
              style={{
                fontSize: '0.8125rem',
                color: tokens.colors.textSecondary,
                marginBottom: '6px',
              }}
            >
              {item.area}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {showDeputy && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div
                    style={{
                      flex: 1,
                      height: '8px',
                      borderRadius: '4px',
                      backgroundColor: tokens.colors.bgTertiary,
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        width: `${item.deputy}%`,
                        height: '100%',
                        backgroundColor: tokens.colors.primary,
                        borderRadius: '4px',
                      }}
                    />
                  </div>
                  <span
                    style={{
                      width: '40px',
                      fontFamily: tokens.fonts.mono,
                      fontSize: '0.75rem',
                      color: tokens.colors.primary,
                      fontWeight: 600,
                    }}
                  >
                    {item.deputy.toFixed(0)}%
                  </span>
                </div>
              )}
              {showParty && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div
                    style={{
                      flex: 1,
                      height: '6px',
                      borderRadius: '3px',
                      backgroundColor: tokens.colors.bgTertiary,
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        width: `${item.party}%`,
                        height: '100%',
                        backgroundColor: tokens.colors.statusAmber,
                        borderRadius: '3px',
                      }}
                    />
                  </div>
                  <span
                    style={{
                      width: '40px',
                      fontFamily: tokens.fonts.mono,
                      fontSize: '0.625rem',
                      color: tokens.colors.statusAmber,
                    }}
                  >
                    {item.party.toFixed(0)}%
                  </span>
                </div>
              )}
              {showParliament && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div
                    style={{
                      flex: 1,
                      height: '4px',
                      borderRadius: '2px',
                      backgroundColor: tokens.colors.bgTertiary,
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        width: `${item.parliament}%`,
                        height: '100%',
                        backgroundColor: tokens.colors.textMuted,
                        borderRadius: '2px',
                      }}
                    />
                  </div>
                  <span
                    style={{
                      width: '40px',
                      fontFamily: tokens.fonts.mono,
                      fontSize: '0.625rem',
                      color: tokens.colors.textMuted,
                    }}
                  >
                    {item.parliament.toFixed(0)}%
                  </span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

/**
 * TopicTag - Compact topic/theme tag
 */
export const TopicTag = ({ label, count, color, size = 'medium' }) => {
  const sizeConfig = {
    small: { padding: '3px 8px', fontSize: '0.6875rem' },
    medium: { padding: '4px 10px', fontSize: '0.75rem' },
    large: { padding: '6px 12px', fontSize: '0.8125rem' },
  };

  const s = sizeConfig[size];
  const tagColor = color || tokens.colors.primary;

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        padding: s.padding,
        backgroundColor: `${tagColor}15`,
        border: `1px solid ${tagColor}30`,
        borderRadius: '4px',
        fontFamily: tokens.fonts.body,
        fontSize: s.fontSize,
        color: tagColor,
        fontWeight: 500,
      }}
    >
      {label}
      {count !== undefined && (
        <span
          style={{
            fontFamily: tokens.fonts.mono,
            fontWeight: 600,
          }}
        >
          ({count})
        </span>
      )}
    </span>
  );
};

export default PolicySpecializationChart;
