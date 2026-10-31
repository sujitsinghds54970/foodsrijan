export type ThemeMode = 'dark' | 'light' | 'high_contrast';

export const BASE_THEME = {
  mode: 'dark' as ThemeMode,
  color: {
    palette: {
      navy950: '#0a0e1a',
      navy900: '#111827',
      navy800: '#1a2138',
      gold500: '#d4af37',
      gold300: '#f4d03f',
      blue400: '#00d4ff',
      emerald500: '#10b981',
      rose500: '#f43f5e',
      amethyst500: '#8b5cf6',
      white: '#f8fafc',
      slate400: '#94a3b8',
      slate500: '#64748b',
    },
    semantic: {
      background: '#0a0e1a',
      surface: '#111827',
      surfaceElevated: '#1a2138',
      textPrimary: '#f8fafc',
      textSecondary: '#94a3b8',
      border: 'rgba(255,255,255,0.12)',
      primary: '#d4af37',
      secondary: '#00d4ff',
      accent: '#8b5cf6',
      success: '#10b981',
      warning: '#f4d03f',
      danger: '#f43f5e',
    },
  },
  typography: {
    fontFamily: {
      display: '"Cormorant Garamond", Georgia, serif',
      body: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      mono: '"JetBrains Mono", "SFMono-Regular", Consolas, monospace',
    },
    size: { xs: '0.72rem', sm: '0.8rem', md: '0.95rem', lg: '1.25rem', xl: '2rem' },
    weight: { regular: 400, medium: 500, semibold: 600, bold: 700 },
    lineHeight: { tight: 1.15, normal: 1.5, relaxed: 1.7 },
    letterSpacing: { normal: '0', wide: '0.08em' },
  },
  spacing: { xs: '0.25rem', sm: '0.5rem', md: '0.75rem', lg: '1rem', xl: '1.5rem', '2xl': '2rem' },
  radius: { sm: '0.5rem', md: '0.75rem', lg: '1rem', xl: '1.5rem', pill: '999px' },
  shadow: {
    sm: '0 2px 8px rgba(0,0,0,0.25)',
    md: '0 4px 12px rgba(0,0,0,0.4)',
    lg: '0 20px 40px rgba(0,0,0,0.5)',
  },
  motion: { fast: '120ms', normal: '200ms', slow: '320ms', easing: 'cubic-bezier(0.2, 0.8, 0.2, 1)' },
  opacity: { disabled: 0.45, muted: 0.7, overlay: 0.64 },
  zIndex: { sidebar: 20, topbar: 30, overlay: 40, modal: 50, toast: 60 },
  gradient: {
    authority: 'linear-gradient(135deg, #d4af37 0%, #f4d03f 100%)',
    executive: 'linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%)',
  },
  iconography: { set: 'system', size: '1rem', strokeWidth: 1.8 },
};

export default BASE_THEME;
