import SuperCEOAccessGuard from './SuperCEOAccessGuard';
import SuperCEOThemeProvider from './SuperCEOThemeProvider';
import SuperCEOShell from './SuperCEOShell';
import useThemeUpdates from '../../../hooks/useThemeUpdates';
import '@fontsource/fraunces/500.css';
import '@fontsource/fraunces/600.css';
import '@fontsource/manrope/400.css';
import '@fontsource/manrope/500.css';
import '@fontsource/manrope/600.css';
import '@fontsource/manrope/700.css';
import '../../../styles/exec-tokens.css';
import '../../../styles/super-ceo.css';
import '../../../styles/super-ceo-profile.css';

function ThemeUpdateSubscriber() {
  useThemeUpdates();
  return <SuperCEOShell />;
}

export default function SuperCEOWorkspace() {
  return <SuperCEOAccessGuard><SuperCEOThemeProvider><ThemeUpdateSubscriber /></SuperCEOThemeProvider></SuperCEOAccessGuard>;
}
