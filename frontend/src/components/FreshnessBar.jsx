import { Link } from 'react-router-dom';
import { Download } from 'lucide-react';
import { useHealth } from '../config/health';
import { daysBetween, formatDate, relativeDay, todayInLisbon } from '../utils/format';
import { tokens } from '../styles/tokens';

// Amber after more than this many days: the same limit as the daily freshness check (#179).
export const MAX_DAYS = 7;

const { colors, fonts } = tokens;

const css = `
  .freshness-bar-row { padding: 0.375rem 1.5rem; font-size: 0.8125rem; }
  .freshness-short { display: none; }
  @media (max-width: 640px) {
    .freshness-bar-row { padding: 0.375rem 1rem; font-size: 0.75rem; }
    .freshness-long { display: none; }
    .freshness-short { display: inline; }
  }
`;

/**
 * When the AR data was last updated (source_updated) and how long ago, on every page (#185).
 * Renders nothing without a date. The right side of the row is left free for the
 * "Descarregar dados" link (#186).
 */
export const FreshnessBarView = ({ sourceUpdated, today }) => {
  const days = daysBetween(sourceUpdated, today);
  if (days === null) return null;
  const stale = days > MAX_DAYS;
  const date = <strong style={{ fontWeight: 600, color: colors.textPrimary }}>{formatDate(sourceUpdated)}</strong>;
  const age = ` (${relativeDay(days)}).`;

  return (
    <div
      data-stale={String(stale)}
      style={{
        backgroundColor: stale ? colors.statusAmberBg : colors.bgWarm,
        borderBottom: `1px solid ${stale ? colors.statusAmberBorder : colors.borderWarm}`,
      }}
    >
      <style>{css}</style>
      <div
        className="freshness-bar-row"
        style={{
          maxWidth: '1280px',
          margin: '0 auto',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
          fontFamily: fonts.body,
          color: colors.textSecondary,
          lineHeight: 1.35,
        }}
      >
        <p style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span
            aria-hidden="true"
            style={{
              width: 7,
              height: 7,
              borderRadius: '50%',
              flex: 'none',
              backgroundColor: stale ? colors.statusAmber : colors.statusGreen,
            }}
          />
          <span className="freshness-long">
            Dados da Assembleia da República atualizados a {date}
            {age}
            {stale && ' A atualização diária está atrasada.'}{' '}
            <Link to="/metodologia" style={{ color: '#1B4332', textDecoration: 'underline' }}>
              Como atualizamos
            </Link>
          </span>
          <span className="freshness-short">
            Dados da AR atualizados a {date}
            {age}
            {stale && ' Atualização atrasada.'}
          </span>
        </p>
        <Link
          to="/dados"
          style={{ display: 'inline-flex', alignItems: 'center', gap: '0.375rem', flex: 'none', color: '#1B4332', fontWeight: 600, textDecoration: 'none' }}
        >
          <Download size={14} aria-hidden="true" />
          <span className="freshness-long">Descarregar dados</span>
          <span className="freshness-short">Dados</span>
        </Link>
      </div>
    </div>
  );
};

const FreshnessBar = () => {
  const release = useHealth();
  return <FreshnessBarView sourceUpdated={release?.source_updated} today={todayInLisbon()} />;
};

export default FreshnessBar;
