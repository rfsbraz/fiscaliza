import React, { useEffect } from 'react';
import { tokens } from '../styles/tokens';
import content from '../content/privacidade.md?raw';

/**
 * /privacidade (#220). The copy is content/privacidade.md, the reviewed note as written: a
 * "## " title, paragraphs that open with a **bold** label, and the contact email as a mailto link.
 */
const EMAIL_PATTERN = /([\w.+-]+@[\w-]+\.[\w.]+)/;

const bodyText = {
  fontFamily: tokens.fonts.body,
  fontSize: '1rem',
  lineHeight: 1.65,
  color: tokens.colors.textSecondary,
  margin: '0 0 1rem 0',
};

const inline = (text, key) =>
  text.split(/(\*\*[^*]+\*\*)/).map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={`${key}-${i}`}>{part.slice(2, -2)}</strong>;
    }
    return part.split(EMAIL_PATTERN).map((piece, j) =>
      EMAIL_PATTERN.test(piece) ? (
        <a key={`${key}-${i}-${j}`} href={`mailto:${piece}`} style={{ color: tokens.colors.primary, textDecoration: 'underline' }}>
          {piece}
        </a>
      ) : (
        piece
      )
    );
  });

export const PrivacyNote = () =>
  content
    .trim()
    .split(/\n\s*\n/)
    .map((block, index) =>
      block.startsWith('## ') ? (
        <h1
          key={index}
          style={{
            fontFamily: tokens.fonts.headline,
            fontSize: '2.25rem',
            fontWeight: 700,
            color: tokens.colors.textPrimary,
            margin: '0 0 1.25rem 0',
          }}
        >
          {block.slice(3)}
        </h1>
      ) : (
        <p key={index} style={bodyText}>
          {inline(block, index)}
        </p>
      )
    );

const Privacidade = () => {
  useEffect(() => {
    const title = document.title;
    document.title = 'Privacidade · Fiscaliza';
    return () => {
      document.title = title;
    };
  }, []);

  return (
    <article style={{ maxWidth: '760px', margin: '0 auto', padding: '3rem 1.5rem 4rem' }}>
      <PrivacyNote />
    </article>
  );
};

export default Privacidade;
