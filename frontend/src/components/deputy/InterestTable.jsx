/**
 * InterestTable - items of an interest declaration as published in the AR open data.
 *
 * Only the fields the release has are shown, and a column is drawn only when at least one row
 * has a value for it. Dates are shown as the declaration gives them; some give only a year.
 */
import React from 'react';
import { tokens } from '../../styles/tokens';

const hasValue = (value) => value !== null && value !== undefined && String(value).trim() !== '';

const formatDate = (raw) => {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(raw || '');
  return match ? `${match[3]}/${match[2]}/${match[1]}` : raw;
};

export const formatPeriod = (start, end) => {
  if (hasValue(start) && hasValue(end)) return `${formatDate(start)} a ${formatDate(end)}`;
  if (hasValue(start)) return `desde ${formatDate(start)}`;
  if (hasValue(end)) return `até ${formatDate(end)}`;
  return null;
};

export const ACTIVITY_COLUMNS = [
  { key: 'function_type', label: 'Cargo ou função' },
  { key: 'entity_name', label: 'Entidade' },
  { key: 'location', label: 'Local' },
  { key: 'period', label: 'Período' },
];

export const SHAREHOLDING_COLUMNS = [
  { key: 'entity_name', label: 'Entidade' },
  { key: 'share_percentage', label: 'Participação' },
  { key: 'location', label: 'Local' },
];

const cellStyle = {
  padding: '10px 12px',
  borderBottom: `1px solid ${tokens.colors.border}`,
  fontFamily: tokens.fonts.body,
  fontSize: '0.875rem',
  color: tokens.colors.textPrimary,
  verticalAlign: 'top',
  textAlign: 'left',
};

const InterestTable = ({ title, columns, items }) => {
  const rows = (items || []).map((item) => ({ ...item, period: formatPeriod(item.start_date, item.end_date) }));
  if (rows.length === 0) return null;
  const shown = columns.filter((column) => rows.some((row) => hasValue(row[column.key])));

  return (
    <div style={{
      backgroundColor: tokens.colors.bgSecondary,
      border: `1px solid ${tokens.colors.border}`,
      borderRadius: '4px',
      padding: '20px',
    }}>
      <h4 style={{
        margin: '0 0 12px 0',
        fontFamily: tokens.fonts.body,
        fontSize: '0.875rem',
        fontWeight: 600,
        color: tokens.colors.textPrimary,
      }}>
        {title}
      </h4>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              {shown.map((column) => (
                <th
                  key={column.key}
                  style={{
                    ...cellStyle,
                    fontSize: '0.6875rem',
                    fontWeight: 600,
                    color: tokens.colors.textMuted,
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                  }}
                >
                  {column.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => (
              <tr key={idx}>
                {shown.map((column) => (
                  <td key={column.key} style={cellStyle}>
                    {hasValue(row[column.key]) ? row[column.key] : ''}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default InterestTable;
