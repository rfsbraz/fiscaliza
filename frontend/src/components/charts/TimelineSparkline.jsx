/**
 * TimelineSparkline Component
 *
 * A compact, inline chart showing activity frequency over time.
 * Pure CSS/SVG implementation without external charting libraries.
 *
 * Part of the Constitutional Modernism design system.
 */

import React, { useMemo } from 'react';
import { tokens } from '../../styles/tokens';

/**
 * TimelineSparkline - Compact activity visualization
 *
 * @param {Object} props
 * @param {Array} props.data - Array of { date: string, value: number } objects
 * @param {number} props.width - Chart width in pixels (default: 200)
 * @param {number} props.height - Chart height in pixels (default: 40)
 * @param {string} props.color - Line color (default: primary)
 * @param {boolean} props.showArea - Fill area under line (default: true)
 * @param {boolean} props.showDots - Show data point dots (default: false)
 * @param {boolean} props.showTrend - Show trend indicator (default: true)
 * @param {string} props.label - Optional label to display
 */
const TimelineSparkline = ({
  data = [],
  width = 200,
  height = 40,
  color = tokens.colors.primary,
  showArea = true,
  showDots = false,
  showTrend = true,
  label,
}) => {
  // Process data and calculate points
  const { points, pathD, areaD, trend, minValue, maxValue, avgValue } = useMemo(() => {
    if (!data || data.length < 2) {
      return { points: [], pathD: '', areaD: '', trend: 0, minValue: 0, maxValue: 0, avgValue: 0 };
    }

    const padding = 4;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;

    // Extract values and calculate stats
    const values = data.map(d => d.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const avg = values.reduce((a, b) => a + b, 0) / values.length;
    const range = max - min || 1;

    // Calculate trend (comparing last third to first third)
    const thirdLength = Math.floor(values.length / 3);
    const firstThirdAvg = values.slice(0, thirdLength).reduce((a, b) => a + b, 0) / thirdLength;
    const lastThirdAvg = values.slice(-thirdLength).reduce((a, b) => a + b, 0) / thirdLength;
    const trendValue = firstThirdAvg > 0 ? ((lastThirdAvg - firstThirdAvg) / firstThirdAvg) * 100 : 0;

    // Generate points
    const pts = data.map((d, i) => ({
      x: padding + (i / (data.length - 1)) * chartWidth,
      y: padding + chartHeight - ((d.value - min) / range) * chartHeight,
      value: d.value,
      date: d.date,
    }));

    // Generate path
    const path = pts.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');

    // Generate area path (closed polygon)
    const area = pts.length > 0
      ? `${path} L ${pts[pts.length - 1].x} ${height - padding} L ${padding} ${height - padding} Z`
      : '';

    return {
      points: pts,
      pathD: path,
      areaD: area,
      trend: trendValue,
      minValue: min,
      maxValue: max,
      avgValue: avg,
    };
  }, [data, width, height]);

  if (!data || data.length < 2) {
    return (
      <div style={{
        width,
        height,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: tokens.colors.bgTertiary,
        borderRadius: '4px',
        fontFamily: tokens.fonts.body,
        fontSize: '0.75rem',
        color: tokens.colors.textMuted,
      }}>
        Dados insuficientes
      </div>
    );
  }

  const getTrendColor = () => {
    if (trend > 10) return tokens.colors.statusGreen;
    if (trend < -10) return tokens.colors.statusRed;
    return tokens.colors.textMuted;
  };

  const getTrendIcon = () => {
    if (trend > 10) return '↑';
    if (trend < -10) return '↓';
    return '→';
  };

  return (
    <div style={{ display: 'inline-flex', flexDirection: 'column', gap: '4px' }}>
      {label && (
        <span style={{
          fontFamily: tokens.fonts.body,
          fontSize: '0.75rem',
          color: tokens.colors.textMuted,
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
        }}>
          {label}
        </span>
      )}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <svg width={width} height={height} style={{ display: 'block' }}>
          {/* Area fill */}
          {showArea && (
            <path
              d={areaD}
              fill={`${color}20`}
              stroke="none"
            />
          )}

          {/* Line */}
          <path
            d={pathD}
            fill="none"
            stroke={color}
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Dots */}
          {showDots && points.map((p, i) => (
            <circle
              key={i}
              cx={p.x}
              cy={p.y}
              r="3"
              fill={tokens.colors.bgPrimary}
              stroke={color}
              strokeWidth="2"
            />
          ))}

          {/* End dot (always show) */}
          {points.length > 0 && (
            <circle
              cx={points[points.length - 1].x}
              cy={points[points.length - 1].y}
              r="3"
              fill={color}
              stroke={tokens.colors.bgPrimary}
              strokeWidth="1.5"
            />
          )}
        </svg>

        {/* Trend indicator */}
        {showTrend && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '2px',
            color: getTrendColor(),
            fontFamily: tokens.fonts.mono,
            fontSize: '0.75rem',
            fontWeight: 600,
          }}>
            <span>{getTrendIcon()}</span>
            <span>{Math.abs(trend).toFixed(0)}%</span>
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * ActivityHeatmap - Calendar-style heatmap showing activity intensity
 *
 * @param {Object} props
 * @param {Array} props.data - Array of { date: string, value: number } objects
 * @param {number} props.weeks - Number of weeks to show (default: 12)
 * @param {string} props.color - Base color for heatmap
 */
export const ActivityHeatmap = ({
  data = [],
  weeks = 12,
  color = tokens.colors.primary,
}) => {
  const cellSize = 12;
  const cellGap = 2;
  const daysPerWeek = 7;

  // Process data into a map
  const dataMap = useMemo(() => {
    const map = new Map();
    data.forEach(d => {
      const dateKey = new Date(d.date).toISOString().split('T')[0];
      map.set(dateKey, d.value);
    });
    return map;
  }, [data]);

  // Generate cells for the last N weeks
  const cells = useMemo(() => {
    const result = [];
    const today = new Date();
    const startDate = new Date(today);
    startDate.setDate(startDate.getDate() - (weeks * 7));

    // Find max value for normalization
    const values = Array.from(dataMap.values());
    const maxValue = Math.max(...values, 1);

    for (let week = 0; week < weeks; week++) {
      for (let day = 0; day < daysPerWeek; day++) {
        const cellDate = new Date(startDate);
        cellDate.setDate(cellDate.getDate() + week * 7 + day);

        if (cellDate > today) continue;

        const dateKey = cellDate.toISOString().split('T')[0];
        const value = dataMap.get(dateKey) || 0;
        const intensity = value / maxValue;

        result.push({
          x: week * (cellSize + cellGap),
          y: day * (cellSize + cellGap),
          value,
          intensity,
          date: dateKey,
        });
      }
    }
    return result;
  }, [dataMap, weeks]);

  const width = weeks * (cellSize + cellGap);
  const height = daysPerWeek * (cellSize + cellGap);

  return (
    <div style={{ display: 'inline-block' }}>
      <svg width={width} height={height}>
        {cells.map((cell, i) => (
          <rect
            key={i}
            x={cell.x}
            y={cell.y}
            width={cellSize}
            height={cellSize}
            rx="2"
            fill={cell.intensity > 0
              ? `rgba(${hexToRgb(color)}, ${0.2 + cell.intensity * 0.8})`
              : tokens.colors.bgTertiary
            }
            style={{ cursor: 'pointer' }}
          >
            <title>{`${cell.date}: ${cell.value} atividades`}</title>
          </rect>
        ))}
      </svg>
      {/* Legend */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '4px',
        marginTop: '8px',
        justifyContent: 'flex-end',
      }}>
        <span style={{
          fontFamily: tokens.fonts.body,
          fontSize: '0.625rem',
          color: tokens.colors.textMuted,
        }}>
          Menos
        </span>
        {[0, 0.25, 0.5, 0.75, 1].map((intensity, i) => (
          <span
            key={i}
            style={{
              width: '10px',
              height: '10px',
              borderRadius: '2px',
              backgroundColor: intensity > 0
                ? `rgba(${hexToRgb(color)}, ${0.2 + intensity * 0.8})`
                : tokens.colors.bgTertiary,
            }}
          />
        ))}
        <span style={{
          fontFamily: tokens.fonts.body,
          fontSize: '0.625rem',
          color: tokens.colors.textMuted,
        }}>
          Mais
        </span>
      </div>
    </div>
  );
};

/**
 * TrendIndicator - Compact trend display with arrow
 */
export const TrendIndicator = ({
  value,
  label,
  positiveIsGood = true,
  showLabel = true,
}) => {
  const isPositive = value > 0;
  const isGood = positiveIsGood ? isPositive : !isPositive;
  const color = Math.abs(value) < 5
    ? tokens.colors.textMuted
    : isGood
      ? tokens.colors.statusGreen
      : tokens.colors.statusRed;

  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '4px',
    }}>
      <span style={{
        color,
        fontFamily: tokens.fonts.mono,
        fontSize: '0.875rem',
        fontWeight: 600,
      }}>
        {isPositive ? '↑' : value < 0 ? '↓' : '→'}
        {Math.abs(value).toFixed(0)}%
      </span>
      {showLabel && label && (
        <span style={{
          fontFamily: tokens.fonts.body,
          fontSize: '0.75rem',
          color: tokens.colors.textMuted,
        }}>
          {label}
        </span>
      )}
    </div>
  );
};

/**
 * BarSparkline - Compact bar chart for comparing values
 */
export const BarSparkline = ({
  data = [],
  width = 120,
  height = 24,
  color = tokens.colors.primary,
  showLabels = false,
}) => {
  if (!data || data.length === 0) return null;

  const maxValue = Math.max(...data.map(d => d.value), 1);
  const barWidth = (width - (data.length - 1) * 2) / data.length;

  return (
    <div style={{ display: 'inline-block' }}>
      <svg width={width} height={height + (showLabels ? 16 : 0)}>
        {data.map((d, i) => {
          const barHeight = (d.value / maxValue) * height;
          return (
            <g key={i}>
              <rect
                x={i * (barWidth + 2)}
                y={height - barHeight}
                width={barWidth}
                height={barHeight}
                fill={d.color || color}
                rx="1"
              >
                <title>{`${d.label}: ${d.value}`}</title>
              </rect>
              {showLabels && (
                <text
                  x={i * (barWidth + 2) + barWidth / 2}
                  y={height + 12}
                  textAnchor="middle"
                  fill={tokens.colors.textMuted}
                  fontSize="8"
                  fontFamily={tokens.fonts.body}
                >
                  {d.label?.substring(0, 3)}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
};

// Helper function to convert hex to RGB
function hexToRgb(hex) {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}`
    : '0, 0, 0';
}

export default TimelineSparkline;
