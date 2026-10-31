import React, { createContext, ReactNode, useContext, useEffect, useMemo, useState } from 'react';
import BASE_THEME, { ThemeMode } from '../styles/tokens/base-theme';
import api from '../services/api';

type ThemeTokens = typeof BASE_THEME & { mode: ThemeMode };

interface ThemeContextValue {
  theme: ThemeTokens;
  mode: ThemeMode;
  setMode: (mode: ThemeMode) => void;
  updateTheme: (tokens: Partial<ThemeTokens>) => void;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);
const CACHE_KEY = 'foodsrijan.platform-theme';
const API_BASE = 'http://127.0.0.1:8000';

const flattenTokens = (value: unknown, prefix = 'fs'): Record<string, string> => {
  if (!value || typeof value !== 'object') return {};
  return Object.entries(value as Record<string, unknown>).reduce<Record<string, string>>((result, [key, child]) => {
    if (key === 'mode') return result;
    const nextPrefix = `${prefix}-${key.replace(/[A-Z]/g, (letter) => `-${letter.toLowerCase()}`)}`;
    if (typeof child === 'string' || typeof child === 'number') result[nextPrefix] = String(child);
    else Object.assign(result, flattenTokens(child, nextPrefix));
    return result;
  }, {});
};

const applyCssVariables = (theme: ThemeTokens) => {
  const root = document.documentElement;
  Object.entries(flattenTokens(theme)).forEach(([name, value]) => root.style.setProperty(`--${name}`, value));
  const color = theme.color as typeof theme.color & {
    surface?: { default?: string; panel?: string; elevated?: string };
    text?: { primary?: string; secondary?: string; tertiary?: string };
  };
  const typography = theme.typography as typeof theme.typography & {
    family?: { display?: string; body?: string; mono?: string };
  };
  const primary = color.semantic?.primary;
  const secondary = color.semantic?.secondary;
  const accent = color.semantic?.accent;
  const background = color.surface?.default || color.semantic?.background;
  const surface = color.surface?.panel || color.semantic?.surface;
  const elevated = color.surface?.elevated || color.semantic?.surfaceElevated;
  const textPrimary = color.text?.primary || color.semantic?.textPrimary;
  const textSecondary = color.text?.secondary || color.semantic?.textSecondary;
  root.dataset.themeMode = theme.mode;
  if (background) {
    root.style.setProperty('--sce-bg-base', background);
    root.style.setProperty('--exec-ink', background);
  }
  if (surface) {
    root.style.setProperty('--sce-bg-elevated', surface);
    root.style.setProperty('--exec-night', surface);
  }
  if (elevated) {
    root.style.setProperty('--sce-bg-surface', elevated);
    root.style.setProperty('--exec-panel', elevated);
  }
  if (textPrimary) {
    root.style.setProperty('--sce-text-primary', textPrimary);
    root.style.setProperty('--exec-text-primary', textPrimary);
    root.style.setProperty('--exec-text-hero', textPrimary);
  }
  if (textSecondary) {
    root.style.setProperty('--sce-text-secondary', textSecondary);
    root.style.setProperty('--exec-text-secondary', textSecondary);
  }
  if (primary) {
    root.style.setProperty('--exec-gold', primary);
    root.style.setProperty('--exec-gold-light', primary);
    root.style.setProperty('--exec-authority-gold', theme.gradient?.authority || `linear-gradient(135deg, ${primary}, ${secondary || accent || primary})`);
  }
  if (secondary) root.style.setProperty('--exec-teal', secondary);
  if (accent) root.style.setProperty('--exec-violet', accent);
  if (typography.family?.display || typography.fontFamily?.display) root.style.setProperty('--font-display', typography.family?.display || typography.fontFamily.display);
  if (typography.family?.body || typography.fontFamily?.body) root.style.setProperty('--font-body', typography.family?.body || typography.fontFamily.body);
};

export const ThemeProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [theme, setTheme] = useState<ThemeTokens>(() => {
    try {
      const cached = localStorage.getItem(CACHE_KEY);
      return cached ? { ...BASE_THEME, ...JSON.parse(cached) } : BASE_THEME;
    } catch {
      return BASE_THEME;
    }
  });

  useEffect(() => {
    applyCssVariables(theme);
    localStorage.setItem(CACHE_KEY, JSON.stringify(theme));
  }, [theme]);

  useEffect(() => {
    api.get(`${API_BASE}/api/themes/resolved`)
      .then((response) => {
        const remoteTheme = response.data?.theme?.tokens;
        if (remoteTheme && typeof remoteTheme === 'object') {
          setTheme((current) => ({ ...current, ...remoteTheme }));
        }
      })
      .catch(() => {
        // The cached or bundled platform theme remains the last-known-good fallback.
      });
  }, []);

  const value = useMemo<ThemeContextValue>(() => ({
    theme,
    mode: theme.mode,
    setMode: (mode) => setTheme((current) => ({ ...current, mode })),
    updateTheme: (tokens) => setTheme((current) => ({ ...current, ...tokens })),
  }), [theme]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};

export const useTheme = (): ThemeContextValue => {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('useTheme must be used within ThemeProvider');
  return context;
};

export default ThemeProvider;
