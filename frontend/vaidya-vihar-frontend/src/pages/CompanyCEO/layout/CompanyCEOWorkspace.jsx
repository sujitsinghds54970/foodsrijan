import { useEffect, useState } from 'react';
import LoadingSkeleton from '../../../components/SuperCEO/common/LoadingSkeleton';
import { companyCeoApi } from '../../../services/companyCeoApi';
import { apiErrorMessage } from '../../../services/companyManagementApi';
import CompanyCEOAccessGuard from './CompanyCEOAccessGuard';
import CompanyCEOShell from './CompanyCEOShell';
import useThemeUpdates from '../../../hooks/useThemeUpdates';
import ThemeProvider from '../../../context/ThemeContext';
import '@fontsource/fraunces/500.css';
import '@fontsource/fraunces/600.css';
import '@fontsource/manrope/400.css';
import '@fontsource/manrope/500.css';
import '@fontsource/manrope/600.css';
import '@fontsource/manrope/700.css';
import '../../../styles/exec-tokens.css';
import '../../../styles/super-ceo-profile.css';
import '../../../styles/company-ceo.css';

function WorkspaceLoader() {
  const [workspace, setWorkspace] = useState(null);
  const [error, setError] = useState('');
  useThemeUpdates();

  const load = async () => {
    setError('');
    try {
      const response = await companyCeoApi.workspace();
      setWorkspace(response.data);
    } catch (requestError) {
      setError(apiErrorMessage(requestError, 'Unable to load your company workspace.'));
    }
  };

  useEffect(() => { void load(); }, []);
  if (!workspace && !error) return <main className="company-ceo-loading"><LoadingSkeleton /></main>;
  if (error || !workspace) return <main className="company-ceo-loading"><div className="company-ceo-error" role="alert"><strong>Company workspace unavailable</strong><p>{error}</p><button type="button" onClick={() => void load()}>Retry</button></div></main>;
  return <CompanyCEOShell workspace={workspace} />;
}

export default function CompanyCEOWorkspace() {
  return <CompanyCEOAccessGuard><ThemeProvider><WorkspaceLoader /></ThemeProvider></CompanyCEOAccessGuard>;
}
