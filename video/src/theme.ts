// Palette mirrors the live PlanComparisonPanel so the video feels on-brand.
export const theme = {
  bg: '#0A0B0D',
  bgElevated: '#15171C',
  border: '#23262D',
  text: '#FFFFFF',
  textMuted: '#8A8F98',
  green: '#34D399',
  blue: '#60A5FA',
  purple: '#A78BFA',
  red: '#F87171',
  amber: '#FBBF24',
};

// System font stack — looks like Inter on most machines, SF on macOS. No
// network dependency at render time (unlike @remotion/google-fonts).
export const FONT =
  "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif";
export const MONO = "'SF Mono', 'JetBrains Mono', Menlo, Consolas, monospace";
