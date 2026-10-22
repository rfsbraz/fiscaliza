import React from 'react';
import * as Sentry from '@sentry/react';
import { tokens } from '../styles/tokens';

/**
 * What the app shows when a render throws. It sits outside the router, so the way home is a
 * plain link that reloads the app.
 */
export const ErrorFallback = () => (
  <div style={{ maxWidth: '640px', margin: '0 auto', padding: '4rem 1.5rem', textAlign: 'center' }}>
    <h1
      style={{
        fontFamily: tokens.fonts.headline,
        fontSize: '2rem',
        fontWeight: 700,
        color: tokens.colors.textPrimary,
        margin: '0.5rem 0 1rem',
      }}
    >
      Algo correu mal
    </h1>
    <p style={{ fontFamily: tokens.fonts.body, color: tokens.colors.textSecondary, marginBottom: '2rem' }}>
      Recarregue a página ou volte ao início.
    </p>
    <a
      href="/"
      style={{
        fontFamily: tokens.fonts.body,
        fontWeight: 600,
        color: tokens.colors.primary,
        textDecoration: 'underline',
      }}
    >
      Voltar ao início
    </a>
  </div>
);

/** Reports the error to Sentry (when it is set up) and shows the fallback. */
const AppErrorBoundary = ({ children }) => (
  <Sentry.ErrorBoundary fallback={<ErrorFallback />}>{children}</Sentry.ErrorBoundary>
);

export default AppErrorBoundary;
