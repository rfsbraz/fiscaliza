import React from 'react';
import { motion } from 'framer-motion';
import { tokens } from '../../styles/tokens';

/**
 * LoadingSpinner - Reusable loading indicator component
 *
 * @param {string} size - 'small' | 'medium' | 'large' (default: 'medium')
 * @param {string} message - Optional loading message to display
 * @param {boolean} fullHeight - Whether to take full viewport height (default: true)
 */
const LoadingSpinner = ({ size = 'medium', message = 'A carregar dados', fullHeight = true }) => {
  const sizes = {
    small: { width: '24px', height: '24px', border: '2px' },
    medium: { width: '48px', height: '48px', border: '3px' },
    large: { width: '64px', height: '64px', border: '4px' },
  };

  const currentSize = sizes[size] || sizes.medium;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '1rem',
        minHeight: fullHeight ? '24rem' : 'auto',
        padding: '2rem',
      }}
    >
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
        style={{
          width: currentSize.width,
          height: currentSize.height,
          border: `${currentSize.border} solid ${tokens.colors.border}`,
          borderTopColor: tokens.colors.primary,
          borderRadius: '50%',
        }}
      />
      {message && (
        <p
          style={{
            fontFamily: tokens.fonts.body,
            fontSize: '0.875rem',
            color: tokens.colors.textMuted,
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            margin: 0,
          }}
        >
          {message}
        </p>
      )}
    </div>
  );
};

export default LoadingSpinner;
