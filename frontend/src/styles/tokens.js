/**
 * Design System Tokens
 *
 * Centralized design tokens for the Parliament transparency platform.
 * Constitutional Modernism style - journalistic data observatory aesthetic.
 * Inspired by ProPublica, FiveThirtyEight, Guardian, Público.
 */

export const tokens = {
  colors: {
    // Core institutional colors
    primary: '#1D4E3E',           // Deep parliamentary green
    primaryLight: '#2D6A4F',
    accent: '#9B2335',            // Republic red accent

    // Background hierarchy
    bgPrimary: '#FAFAFA',
    bgSecondary: '#FFFFFF',
    bgTertiary: '#F5F5F5',
    bgWarm: '#F8F6F0',            // Warm paper tone for context frames

    // Text hierarchy
    textPrimary: '#1A1A1A',
    textSecondary: '#4A4A4A',
    textMuted: '#6B6B6B',

    // Borders
    border: '#E5E5E5',
    borderStrong: '#D4D4D4',
    borderWarm: '#E8E4DA',        // Warm border for context frames

    // Semantic colors
    success: '#166534',
    warning: '#CA8A04',
    danger: '#991B1B',
    orange: '#EA580C',

    // Constitutional Modernism accents
    ouroConstitucional: '#C9A227', // Gold accent for context/notes
    verdeClaro: '#2D6A4F',
    infoPrimary: '#1E3A5F',
    infoSecondary: '#3D5A80',

    // Traffic Light Status Colors (for transparency indicators)
    statusGreen: '#166534',         // >85% - Above expectations
    statusGreenBg: '#F0FDF4',
    statusGreenBorder: '#BBF7D0',
    statusAmber: '#D97706',         // 70-85% - Needs context
    statusAmberBg: '#FFFBEB',
    statusAmberBorder: '#FDE68A',
    statusRed: '#991B1B',           // <70% - Below expectations
    statusRedBg: '#FEF2F2',
    statusRedBorder: '#FECACA',
    statusNeutral: '#6B7280',       // No data / not applicable
    statusNeutralBg: '#F9FAFB',
    statusNeutralBorder: '#E5E7EB',

    // Context Box Colors
    contextInfoBg: '#EFF6FF',
    contextInfoBorder: '#3B82F6',
    contextEducationalBg: '#F5F2EC',
    contextEducationalBorder: '#1D4E3E',
    contextWarningBg: '#FFFBEB',
    contextWarningBorder: '#D97706',
    contextAlertBg: '#FEF2F2',
    contextAlertBorder: '#991B1B',

    // Sector/Interest Status Colors (for conflicts tab)
    sectorAttention: '#EA580C',     // Multiple interests in regulated sector
    sectorAttentionBg: '#FFF7ED',
    sectorContext: '#D97706',       // Interest declared, needs context
    sectorContextBg: '#FFFBEB',
    sectorClear: '#166534',         // No interests in sector
    sectorClearBg: '#F0FDF4',
    sectorMissing: '#6B7280',       // Declaration missing
    sectorMissingBg: '#F9FAFB',
  },
  fonts: {
    headline: "'Fraunces', 'Libre Baskerville', Georgia, serif",
    body: "'Source Sans 3', sans-serif",
    mono: "'JetBrains Mono', monospace",
  },

  // Shadows for cards
  shadows: {
    card: '0 1px 3px rgba(0,0,0,0.06), 0 4px 12px rgba(0,0,0,0.04)',
    cardHover: '0 2px 8px rgba(0,0,0,0.08), 0 8px 24px rgba(0,0,0,0.06)',
  },
};

// Party colors - official or close approximations
export const partidoCores = {
  'PSD': '#FF6B35',
  'PS': '#E91E63',
  'CH': '#1565C0',
  'IL': '#00BCD4',
  'BE': '#9C27B0',
  'PCP': '#F44336',
  'L': '#4CAF50',
  'CDS-PP': '#FF9800',
  'PAN': '#8BC34A',
  'JPP': '#673AB7',
};

export default tokens;
