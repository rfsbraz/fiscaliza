/**
 * ContextBox Component
 *
 * Reusable context/educational info box for deputy profile tabs.
 * Provides consistent styling for informational, educational, warning,
 * and alert messages across the transparency platform.
 *
 * Part of the Constitutional Modernism design system.
 */

import React, { useState } from 'react';
import { Info, BookOpen, AlertTriangle, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react';
import { tokens } from '../../styles/tokens';

/**
 * Context box types and their associated styling
 */
const contextStyles = {
  info: {
    bg: tokens.colors.contextInfoBg,
    border: tokens.colors.contextInfoBorder,
    iconColor: tokens.colors.contextInfoBorder,
    Icon: Info,
  },
  educational: {
    bg: tokens.colors.contextEducationalBg,
    border: tokens.colors.contextEducationalBorder,
    iconColor: tokens.colors.primary,
    Icon: BookOpen,
  },
  warning: {
    bg: tokens.colors.contextWarningBg,
    border: tokens.colors.contextWarningBorder,
    iconColor: tokens.colors.statusAmber,
    Icon: AlertTriangle,
  },
  alert: {
    bg: tokens.colors.contextAlertBg,
    border: tokens.colors.contextAlertBorder,
    iconColor: tokens.colors.statusRed,
    Icon: AlertCircle,
  },
};

/**
 * ContextBox - Displays contextual information with consistent styling
 *
 * @param {Object} props
 * @param {'info' | 'educational' | 'warning' | 'alert'} props.type - Type of context box
 * @param {string} props.title - Optional title for the box
 * @param {React.ReactNode} props.children - Content to display
 * @param {boolean} props.collapsible - Whether the box can be collapsed
 * @param {boolean} props.defaultExpanded - Initial expanded state (for collapsible)
 * @param {React.ReactNode} props.icon - Custom icon (overrides default)
 * @param {string} props.className - Additional CSS classes
 */
const ContextBox = ({
  type = 'info',
  title,
  children,
  collapsible = false,
  defaultExpanded = true,
  icon: CustomIcon,
  className = '',
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const style = contextStyles[type] || contextStyles.info;
  const IconComponent = CustomIcon || style.Icon;

  const containerStyle = {
    backgroundColor: style.bg,
    borderLeft: `4px solid ${style.border}`,
    borderRadius: '2px',
    padding: '16px 20px',
    marginBottom: '16px',
    fontFamily: tokens.fonts.body,
  };

  const headerStyle = {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '12px',
    cursor: collapsible ? 'pointer' : 'default',
  };

  const iconContainerStyle = {
    flexShrink: 0,
    marginTop: '2px',
  };

  const contentWrapperStyle = {
    flex: 1,
    minWidth: 0,
  };

  const titleStyle = {
    fontFamily: tokens.fonts.body,
    fontSize: '0.875rem',
    fontWeight: 600,
    color: tokens.colors.textPrimary,
    margin: 0,
    marginBottom: title && children ? '8px' : 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  };

  const bodyStyle = {
    fontFamily: tokens.fonts.body,
    fontSize: '0.875rem',
    lineHeight: 1.6,
    color: tokens.colors.textSecondary,
    margin: 0,
  };

  const toggleStyle = {
    background: 'none',
    border: 'none',
    padding: '4px',
    cursor: 'pointer',
    color: style.iconColor,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: '2px',
    transition: 'background-color 0.15s ease',
  };

  const handleToggle = () => {
    if (collapsible) {
      setIsExpanded(!isExpanded);
    }
  };

  return (
    <div style={containerStyle} className={className}>
      <div
        style={headerStyle}
        onClick={handleToggle}
        role={collapsible ? 'button' : undefined}
        aria-expanded={collapsible ? isExpanded : undefined}
      >
        <div style={iconContainerStyle}>
          <IconComponent
            size={18}
            style={{ color: style.iconColor }}
          />
        </div>
        <div style={contentWrapperStyle}>
          {title && (
            <p style={titleStyle}>
              <span>{title}</span>
              {collapsible && (
                <button
                  style={toggleStyle}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleToggle();
                  }}
                  aria-label={isExpanded ? 'Recolher' : 'Expandir'}
                >
                  {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </button>
              )}
            </p>
          )}
          {(!collapsible || isExpanded) && children && (
            <div style={bodyStyle}>
              {children}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

/**
 * Pre-configured context boxes for common use cases
 */

/**
 * Educational context box - explains how to interpret data
 */
export const EducationalBox = ({ title = 'Como interpretar esta informação', children, ...props }) => (
  <ContextBox type="educational" title={title} {...props}>
    {children}
  </ContextBox>
);

/**
 * Important context box - highlights critical context for data interpretation
 */
export const ImportantContextBox = ({ title = 'Contexto Importante', children, ...props }) => (
  <ContextBox type="info" title={title} {...props}>
    {children}
  </ContextBox>
);

/**
 * Warning context box - flags potential issues that need explanation
 */
export const WarningContextBox = ({ title = 'Atenção', children, ...props }) => (
  <ContextBox type="warning" title={title} {...props}>
    {children}
  </ContextBox>
);

/**
 * Alert context box - highlights serious concerns
 */
export const AlertContextBox = ({ title = 'Alerta', children, ...props }) => (
  <ContextBox type="alert" title={title} {...props}>
    {children}
  </ContextBox>
);

/**
 * Methodology note - explains data sources and methodology
 */
export const MethodologyNote = ({ children, ...props }) => (
  <ContextBox
    type="educational"
    title="Nota metodológica"
    collapsible={true}
    defaultExpanded={false}
    {...props}
  >
    {children}
  </ContextBox>
);

export default ContextBox;
