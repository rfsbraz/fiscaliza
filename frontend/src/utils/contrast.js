/** WCAG 2 contrast for text drawn on a party colour. */

const LIGHT = '#FFFFFF';
const DARK = '#000000';

const channel = (c) => {
  const s = c / 255;
  return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
};

const luminance = (hex) => {
  const n = parseInt(hex.replace('#', ''), 16);
  return 0.2126 * channel((n >> 16) & 255) + 0.7152 * channel((n >> 8) & 255) + 0.0722 * channel(n & 255);
};

export const contrastRatio = (a, b) => {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
};

/** White or black, whichever contrasts more with the background. The better of the two is
 * always at least 4.58:1 (the square root of 21), so any colour passes 4.5:1. */
export const labelColor = (bg) => (contrastRatio(LIGHT, bg) >= contrastRatio(DARK, bg) ? LIGHT : DARK);
