import React, { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { tokens } from '../styles/tokens';

/**
 * Any path the app has no route for (#113). On Pages the server answers it with 404.html (the
 * app) and status 404; this view says so and asks search engines not to index it.
 */
const NotFound = () => {
  useEffect(() => {
    const meta = document.createElement('meta');
    meta.name = 'robots';
    meta.content = 'noindex';
    document.head.appendChild(meta);
    const title = document.title;
    document.title = 'Página não encontrada · Fiscaliza';
    return () => {
      document.head.removeChild(meta);
      document.title = title;
    };
  }, []);

  return (
    <div style={{ maxWidth: '640px', margin: '0 auto', padding: '4rem 1.5rem', textAlign: 'center' }}>
      <p style={{ fontFamily: tokens.fonts.mono, fontSize: '0.875rem', color: tokens.colors.textMuted }}>404</p>
      <h1
        style={{
          fontFamily: tokens.fonts.headline,
          fontSize: '2rem',
          fontWeight: 700,
          color: tokens.colors.textPrimary,
          margin: '0.5rem 0 1rem',
        }}
      >
        Página não encontrada
      </h1>
      <p style={{ fontFamily: tokens.fonts.body, color: tokens.colors.textSecondary, marginBottom: '2rem' }}>
        O endereço que abriu não existe no Fiscaliza.
      </p>
      <Link
        to="/"
        style={{
          fontFamily: tokens.fonts.body,
          fontWeight: 600,
          color: tokens.colors.primary,
          textDecoration: 'underline',
        }}
      >
        Voltar ao início
      </Link>
    </div>
  );
};

export default NotFound;
