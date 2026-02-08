/**
 * TrafficLightIndicator Component
 *
 * Traffic light status indicator for transparency metrics.
 * Shows green/amber/red based on configurable thresholds.
 *
 * Part of the Constitutional Modernism design system.
 */

import React from 'react';
import { CheckCircle, AlertTriangle, AlertCircle, HelpCircle, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { tokens } from '../../styles/tokens';

/**
 * Default thresholds for common metrics
 */
export const ATTENDANCE_THRESHOLDS = {
  green: 85,   // >85% - Above expectations
  amber: 70,   // 70-85% - Needs context
  // Below 70% - Red
};

export const ACTIVITY_THRESHOLDS = {
  green: 20,   // >20 interventions/year - Active
  amber: 5,    // 5-20 - Moderate
  // Below 5 - Red
};

/**
 * Get status based on value and thresholds
 */
const getStatus = (value, thresholds, invertScale = false) => {
  if (value === null || value === undefined) {
    return 'neutral';
  }

  const { green, amber } = thresholds;

  if (invertScale) {
    // For metrics where lower is better (e.g., unjustified absences)
    if (value <= amber) return 'green';
    if (value <= green) return 'amber';
    return 'red';
  }

  // Standard: higher is better
  if (value >= green) return 'green';
  if (value >= amber) return 'amber';
  return 'red';
};

/**
 * Status configurations
 */
const statusConfig = {
  green: {
    bg: tokens.colors.statusGreenBg,
    border: tokens.colors.statusGreenBorder,
    color: tokens.colors.statusGreen,
    Icon: CheckCircle,
    defaultLabel: 'Acima da média',
  },
  amber: {
    bg: tokens.colors.statusAmberBg,
    border: tokens.colors.statusAmberBorder,
    color: tokens.colors.statusAmber,
    Icon: AlertTriangle,
    defaultLabel: 'Requer contexto',
  },
  red: {
    bg: tokens.colors.statusRedBg,
    border: tokens.colors.statusRedBorder,
    color: tokens.colors.statusRed,
    Icon: AlertCircle,
    defaultLabel: 'Abaixo do esperado',
  },
  neutral: {
    bg: tokens.colors.statusNeutralBg,
    border: tokens.colors.statusNeutralBorder,
    color: tokens.colors.statusNeutral,
    Icon: HelpCircle,
    defaultLabel: 'Dados indisponíveis',
  },
};

/**
 * TrafficLightIndicator - Displays a traffic light status indicator
 *
 * @param {Object} props
 * @param {number} props.value - The value to evaluate
 * @param {Object} props.thresholds - { green: number, amber: number }
 * @param {boolean} props.invertScale - If true, lower values are better
 * @param {Object} props.labels - { green: string, amber: string, red: string }
 * @param {string} props.unit - Unit to display (e.g., '%')
 * @param {boolean} props.showValue - Whether to show the numeric value
 * @param {boolean} props.showIcon - Whether to show the status icon
 * @param {boolean} props.showLabel - Whether to show the status label
 * @param {boolean} props.showComparison - Whether to show comparison info
 * @param {number} props.comparisonValue - Value to compare against
 * @param {string} props.comparisonLabel - Label for comparison (e.g., 'média parlamentar')
 * @param {'compact' | 'normal' | 'large'} props.size - Size variant
 * @param {'card' | 'inline' | 'badge'} props.variant - Display variant
 */
const TrafficLightIndicator = ({
  value,
  thresholds = ATTENDANCE_THRESHOLDS,
  invertScale = false,
  labels = {},
  unit = '%',
  showValue = true,
  showIcon = true,
  showLabel = true,
  showComparison = false,
  comparisonValue,
  comparisonLabel = 'média parlamentar',
  size = 'normal',
  variant = 'card',
}) => {
  const status = getStatus(value, thresholds, invertScale);
  const config = statusConfig[status];
  const label = labels[status] || config.defaultLabel;

  // Size configurations
  const sizeConfig = {
    compact: {
      padding: '8px 12px',
      fontSize: '0.75rem',
      iconSize: 14,
      valueSize: '1rem',
      gap: '8px',
    },
    normal: {
      padding: '16px 20px',
      fontSize: '0.875rem',
      iconSize: 18,
      valueSize: '1.5rem',
      gap: '12px',
    },
    large: {
      padding: '20px 24px',
      fontSize: '1rem',
      iconSize: 24,
      valueSize: '2rem',
      gap: '16px',
    },
  };

  const sizeStyles = sizeConfig[size];
  const StatusIcon = config.Icon;

  // Calculate comparison delta
  const delta = comparisonValue !== undefined && value !== null
    ? value - comparisonValue
    : null;

  // Card variant (default)
  if (variant === 'card') {
    return (
      <div
        style={{
          backgroundColor: config.bg,
          border: `2px solid ${config.border}`,
          borderRadius: '4px',
          padding: sizeStyles.padding,
          fontFamily: tokens.fonts.body,
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: sizeStyles.gap,
          }}
        >
          {showIcon && (
            <div
              style={{
                backgroundColor: `${config.color}15`,
                borderRadius: '4px',
                padding: '8px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <StatusIcon
                size={sizeStyles.iconSize}
                style={{ color: config.color }}
              />
            </div>
          )}
          <div style={{ flex: 1 }}>
            {showValue && value !== null && (
              <div
                style={{
                  fontSize: sizeStyles.valueSize,
                  fontWeight: 700,
                  color: config.color,
                  fontFamily: tokens.fonts.mono,
                  lineHeight: 1.2,
                }}
              >
                {typeof value === 'number' ? value.toFixed(1) : value}{unit}
              </div>
            )}
            {showLabel && (
              <div
                style={{
                  fontSize: sizeStyles.fontSize,
                  color: tokens.colors.textSecondary,
                  marginTop: showValue ? '4px' : 0,
                }}
              >
                {label}
              </div>
            )}
            {showComparison && delta !== null && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '0.75rem',
                  color: delta >= 0 ? tokens.colors.statusGreen : tokens.colors.statusRed,
                  marginTop: '8px',
                }}
              >
                {delta >= 0 ? (
                  <TrendingUp size={14} />
                ) : (
                  <TrendingDown size={14} />
                )}
                <span>
                  {delta >= 0 ? '+' : ''}{delta.toFixed(1)} pp vs. {comparisonLabel}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Inline variant (for use within text or tables)
  if (variant === 'inline') {
    return (
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '6px',
          fontFamily: tokens.fonts.body,
        }}
      >
        {showIcon && (
          <StatusIcon
            size={sizeStyles.iconSize - 4}
            style={{ color: config.color }}
          />
        )}
        {showValue && value !== null && (
          <span
            style={{
              fontWeight: 600,
              color: config.color,
              fontFamily: tokens.fonts.mono,
            }}
          >
            {typeof value === 'number' ? value.toFixed(1) : value}{unit}
          </span>
        )}
        {showLabel && (
          <span
            style={{
              color: tokens.colors.textMuted,
              fontSize: '0.875em',
            }}
          >
            ({label})
          </span>
        )}
      </span>
    );
  }

  // Badge variant (minimal, for lists)
  if (variant === 'badge') {
    return (
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '4px',
          backgroundColor: config.bg,
          border: `1px solid ${config.border}`,
          borderRadius: '2px',
          padding: '2px 8px',
          fontSize: '0.75rem',
          fontWeight: 600,
          color: config.color,
          fontFamily: tokens.fonts.mono,
        }}
      >
        {showIcon && <StatusIcon size={12} />}
        {showValue && value !== null && (
          <span>{typeof value === 'number' ? value.toFixed(1) : value}{unit}</span>
        )}
      </span>
    );
  }

  return null;
};

/**
 * TrafficLightBar - Horizontal progress bar with traffic light colors
 */
export const TrafficLightBar = ({
  value,
  thresholds = ATTENDANCE_THRESHOLDS,
  invertScale = false,
  showMarkers = true,
  height = 8,
}) => {
  const status = getStatus(value, thresholds, invertScale);
  const config = statusConfig[status];
  const percentage = Math.min(100, Math.max(0, value || 0));

  return (
    <div
      style={{
        width: '100%',
        backgroundColor: tokens.colors.bgTertiary,
        borderRadius: height / 2,
        height,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Progress fill */}
      <div
        style={{
          width: `${percentage}%`,
          height: '100%',
          backgroundColor: config.color,
          borderRadius: height / 2,
          transition: 'width 0.3s ease',
        }}
      />
      {/* Threshold markers */}
      {showMarkers && (
        <>
          <div
            style={{
              position: 'absolute',
              left: `${thresholds.amber}%`,
              top: 0,
              bottom: 0,
              width: '2px',
              backgroundColor: tokens.colors.statusAmber,
              opacity: 0.5,
            }}
          />
          <div
            style={{
              position: 'absolute',
              left: `${thresholds.green}%`,
              top: 0,
              bottom: 0,
              width: '2px',
              backgroundColor: tokens.colors.statusGreen,
              opacity: 0.5,
            }}
          />
        </>
      )}
    </div>
  );
};

/**
 * StatusDot - Simple colored dot indicator
 */
export const StatusDot = ({ status, size = 8, pulse = false }) => {
  const config = statusConfig[status] || statusConfig.neutral;

  return (
    <span
      style={{
        display: 'inline-block',
        width: size,
        height: size,
        borderRadius: '50%',
        backgroundColor: config.color,
        animation: pulse ? 'pulse 2s infinite' : 'none',
      }}
    />
  );
};

export default TrafficLightIndicator;
