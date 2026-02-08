import React from 'react';
import { tokens } from '../../styles/tokens';

/**
 * Card - Reusable card container component
 *
 * @param {React.ReactNode} children - Card content
 * @param {object} style - Additional inline styles
 * @param {boolean} hover - Enable hover effects (default: true)
 * @param {string} padding - Padding size: 'none' | 'small' | 'medium' | 'large' (default: 'medium')
 */
const Card = ({ children, style = {}, hover = true, padding = 'medium', ...props }) => {
  const paddingSizes = {
    none: '0',
    small: '0.75rem',
    medium: '1.25rem',
    large: '1.5rem',
  };

  const [isHovered, setIsHovered] = React.useState(false);

  return (
    <div
      style={{
        backgroundColor: tokens.colors.bgSecondary,
        border: `1px solid ${isHovered && hover ? tokens.colors.borderStrong : tokens.colors.border}`,
        borderRadius: '4px',
        padding: paddingSizes[padding] || paddingSizes.medium,
        transition: 'border-color 150ms ease',
        ...style,
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      {...props}
    >
      {children}
    </div>
  );
};

/**
 * Section - Card with header and optional sublabel
 *
 * @param {string} title - Section title
 * @param {string} subtitle - Optional subtitle/description
 * @param {React.ReactNode} children - Section content
 * @param {React.ReactNode} headerRight - Optional content for right side of header
 * @param {object} style - Additional inline styles for container
 */
const Section = ({ title, subtitle, children, headerRight, style = {} }) => {
  return (
    <div
      style={{
        backgroundColor: tokens.colors.bgSecondary,
        border: `1px solid ${tokens.colors.border}`,
        borderRadius: '4px',
        ...style,
      }}
    >
      <div
        style={{
          padding: '1.25rem 1.5rem',
          borderBottom: `1px solid ${tokens.colors.border}`,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <div>
          <h2
            style={{
              fontFamily: tokens.fonts.headline,
              fontSize: '1.125rem',
              fontWeight: 700,
              color: tokens.colors.textPrimary,
              margin: 0,
            }}
          >
            {title}
          </h2>
          {subtitle && (
            <p
              style={{
                fontSize: '0.8125rem',
                color: tokens.colors.textMuted,
                margin: '0.25rem 0 0',
              }}
            >
              {subtitle}
            </p>
          )}
        </div>
        {headerRight && <div>{headerRight}</div>}
      </div>
      <div style={{ padding: '1.5rem' }}>{children}</div>
    </div>
  );
};

/**
 * PageHeader - Reusable page header with title and description
 *
 * @param {string} title - Page title
 * @param {React.ReactNode} description - Page description (can be string or JSX)
 * @param {object} style - Additional inline styles
 */
const PageHeader = ({ title, description, style = {} }) => {
  return (
    <div style={{ textAlign: 'center', marginBottom: '0.5rem', ...style }}>
      <h1
        style={{
          fontFamily: tokens.fonts.headline,
          fontSize: '2.25rem',
          fontWeight: 700,
          color: tokens.colors.textPrimary,
          marginBottom: '0.5rem',
        }}
      >
        {title}
      </h1>
      {description && (
        <p
          style={{
            fontFamily: tokens.fonts.body,
            fontSize: '1rem',
            color: tokens.colors.textSecondary,
          }}
        >
          {description}
        </p>
      )}
    </div>
  );
};

/**
 * MetricCard - Display a metric with label and sublabel
 *
 * @param {string|number} value - The metric value
 * @param {string} label - Label for the metric
 * @param {string} sublabel - Optional sublabel
 * @param {string} accent - Optional accent color: 'primary' | 'accent'
 */
const MetricCard = ({ value, label, sublabel, accent }) => (
  <div
    style={{
      backgroundColor: tokens.colors.bgSecondary,
      padding: '1.25rem 1.5rem',
      textAlign: 'center',
      borderLeft:
        accent === 'primary'
          ? `3px solid ${tokens.colors.primary}`
          : accent === 'accent'
          ? `3px solid ${tokens.colors.accent}`
          : 'none',
    }}
  >
    <div
      style={{
        fontFamily: tokens.fonts.mono,
        fontSize: '2rem',
        fontWeight: 700,
        color:
          accent === 'primary'
            ? tokens.colors.primary
            : accent === 'accent'
            ? tokens.colors.accent
            : tokens.colors.textPrimary,
        lineHeight: 1,
        marginBottom: '0.5rem',
      }}
    >
      {value}
    </div>
    <div
      style={{
        fontSize: '0.6875rem',
        fontWeight: 600,
        textTransform: 'uppercase',
        letterSpacing: '0.08em',
        color: tokens.colors.textMuted,
        marginBottom: '0.125rem',
      }}
    >
      {label}
    </div>
    {sublabel && (
      <div
        style={{
          fontSize: '0.75rem',
          color: tokens.colors.textMuted,
        }}
      >
        {sublabel}
      </div>
    )}
  </div>
);

export { Card, Section, PageHeader, MetricCard };
export default Card;
