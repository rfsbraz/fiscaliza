import React, { useEffect, useState } from 'react';
import { apiFetch } from '../config/api';
import { tokens } from '../styles/tokens';
import content from '../content/metodologia.md?raw';

/**
 * /metodologia (#113). The copy is content/metodologia.md, the reviewed draft without the reviewer
 * notes. The page renders it as written and fills in values from the data: {source_updated} and
 * {tag} from health.json (as the footer does); {n}, the interventions published for the XVII, and
 * {com_declaracao} of {total}, the interest-declaration coverage, from legislaturas.json. The page
 * is indexable.
 */
const MISSING = '(indisponível)';
const URL_PATTERN = /(https:\/\/[^\s]+)/;

const fill = (text, values) => text.replace(/\{(\w+)\}/g, (_, key) => values[key] ?? MISSING);

// **bold** and bare https links.
const inline = (text, key) =>
  text.split(/(\*\*[^*]+\*\*)/).map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={`${key}-${i}`}>{part.slice(2, -2)}</strong>;
    }
    return part.split(URL_PATTERN).map((piece, j) =>
      URL_PATTERN.test(piece) ? (
        <a
          key={`${key}-${i}-${j}`}
          href={piece}
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: tokens.colors.primary, textDecoration: 'underline', wordBreak: 'break-all' }}
        >
          {piece}
        </a>
      ) : (
        piece
      )
    );
  });

const bodyText = {
  fontFamily: tokens.fonts.body,
  fontSize: '1rem',
  lineHeight: 1.65,
  color: tokens.colors.textSecondary,
  margin: '0 0 1rem 0',
};

const renderBlock = (block, index) => {
  const lines = block.split('\n');
  if (block.startsWith('# ')) {
    return (
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
        {block.slice(2)}
      </h1>
    );
  }
  if (block.startsWith('## ')) {
    const title = block.slice(3);
    return (
      <h2
        key={index}
        id={title.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/g, '-')}
        style={{
          fontFamily: tokens.fonts.headline,
          fontSize: '1.375rem',
          fontWeight: 700,
          color: tokens.colors.textPrimary,
          margin: '2.25rem 0 0.75rem 0',
          paddingBottom: '0.5rem',
          borderBottom: `1px solid ${tokens.colors.border}`,
        }}
      >
        {title}
      </h2>
    );
  }
  if (lines.every((line) => line.startsWith('- '))) {
    return (
      <ul key={index} style={{ ...bodyText, listStyle: 'disc', paddingLeft: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
        {lines.map((line, i) => (
          <li key={i}>{inline(line.slice(2), `${index}-${i}`)}</li>
        ))}
      </ul>
    );
  }
  return (
    <p key={index} style={bodyText}>
      {lines.map((line, i) => (
        <React.Fragment key={i}>
          {i > 0 && <br />}
          {inline(line, `${index}-${i}`)}
        </React.Fragment>
      ))}
    </p>
  );
};

const Metodologia = () => {
  const [values, setValues] = useState({});

  useEffect(() => {
    const title = document.title;
    document.title = 'Metodologia e fontes · Fiscaliza';
    apiFetch('health')
      .then((response) => response.json())
      .then((body) => setValues((v) => ({ ...v, source_updated: body.data?.source_updated, tag: body.data?.tag })))
      .catch(() => {});
    apiFetch('legislaturas')
      .then((response) => response.json())
      .then((body) => {
        const xvii = (body.legislaturas || []).find((leg) => leg.numero === 'XVII');
        if (xvii?.intervencoes_publicadas != null) {
          setValues((v) => ({ ...v, n: xvii.intervencoes_publicadas.toLocaleString('pt-PT') }));
        }
        const coverage = body.cobertura_declaracoes;
        if (coverage?.com_declaracao != null && coverage?.total != null) {
          setValues((v) => ({
            ...v,
            com_declaracao: coverage.com_declaracao.toLocaleString('pt-PT'),
            total: coverage.total.toLocaleString('pt-PT'),
          }));
        }
      })
      .catch(() => {});
    return () => {
      document.title = title;
    };
  }, []);

  const blocks = fill(content, values).trim().split(/\n\s*\n/);

  return (
    <article style={{ maxWidth: '760px', margin: '0 auto', padding: '3rem 1.5rem 4rem' }}>
      {blocks.map(renderBlock)}
    </article>
  );
};

export default Metodologia;
