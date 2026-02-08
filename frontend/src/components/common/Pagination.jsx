import React from 'react';
import { tokens } from '../../styles/tokens';

/**
 * Pagination - Reusable pagination component
 *
 * @param {object} pagination - Pagination object with page, pages, has_prev, has_next
 * @param {function} onPageChange - Callback when page changes
 * @param {object} style - Additional inline styles
 */
const Pagination = ({ pagination, onPageChange, style = {} }) => {
  if (!pagination || pagination.pages <= 1) {
    return null;
  }

  const buttonStyle = (enabled) => ({
    padding: '0.5rem 1rem',
    fontFamily: tokens.fonts.body,
    fontSize: '0.875rem',
    fontWeight: 500,
    color: enabled ? tokens.colors.textPrimary : tokens.colors.textMuted,
    backgroundColor: tokens.colors.bgSecondary,
    border: `1px solid ${tokens.colors.border}`,
    borderRadius: '2px',
    cursor: enabled ? 'pointer' : 'not-allowed',
    opacity: enabled ? 1 : 0.5,
    transition: 'border-color 150ms ease',
  });

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '0.75rem',
        marginTop: '1rem',
        ...style,
      }}
    >
      <button
        disabled={!pagination.has_prev}
        onClick={() => onPageChange(pagination.page - 1)}
        style={buttonStyle(pagination.has_prev)}
        onMouseEnter={(e) => {
          if (pagination.has_prev) {
            e.currentTarget.style.borderColor = tokens.colors.primary;
          }
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = tokens.colors.border;
        }}
      >
        Anterior
      </button>
      <span
        style={{
          padding: '0.5rem 1rem',
          fontFamily: tokens.fonts.mono,
          fontSize: '0.8125rem',
          color: tokens.colors.textSecondary,
        }}
      >
        Página {pagination.page} de {pagination.pages}
      </span>
      <button
        disabled={!pagination.has_next}
        onClick={() => onPageChange(pagination.page + 1)}
        style={buttonStyle(pagination.has_next)}
        onMouseEnter={(e) => {
          if (pagination.has_next) {
            e.currentTarget.style.borderColor = tokens.colors.primary;
          }
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = tokens.colors.border;
        }}
      >
        Próxima
      </button>
    </div>
  );
};

export default Pagination;
