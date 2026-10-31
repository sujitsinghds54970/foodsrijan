import ThemeProvider from '../../../context/ThemeContext';

export default function SuperCEOThemeProvider({ children }) {
  return <ThemeProvider>{children}</ThemeProvider>;
}
