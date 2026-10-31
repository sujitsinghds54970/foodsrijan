import { useCallback, useEffect, useState } from 'react';
import LoadingSkeleton from '../../../components/SuperCEO/common/LoadingSkeleton';
import ThemeProvider from '../../../context/ThemeContext';
import useThemeUpdates from '../../../hooks/useThemeUpdates';
import { apiErrorMessage } from '../../../services/companyManagementApi';
import { staffApi } from '../../../services/staffApi';
import StaffAccessGuard from './StaffAccessGuard';
import StaffShell from './StaffShell';
import '@fontsource/fraunces/500.css';
import '@fontsource/fraunces/600.css';
import '@fontsource/manrope/400.css';
import '@fontsource/manrope/500.css';
import '@fontsource/manrope/600.css';
import '@fontsource/manrope/700.css';
import '../../../styles/exec-tokens.css';
import '../../../styles/super-ceo-profile.css';
import '../../../styles/manager.css';
import '../../../styles/staff.css';

function WorkspaceLoader() {
  const [workspace, setWorkspace] = useState(null);
  const [error, setError] = useState('');
  useThemeUpdates();

  const load = useCallback(async () => {
    setError('');
    try {
      setWorkspace(await staffApi.loadWorkspace());
    } catch (requestError) {
      setWorkspace(null);
      setError(apiErrorMessage(requestError, 'Unable to load the staff workspace.'));
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  if (!workspace && !error) {
    return <main className="manager-loading" role="status" aria-live="polite"><LoadingSkeleton /></main>;
  }

  if (error || !workspace) {
    return (
      <main className="manager-loading">
        <div className="manager-error" role="alert">
          <strong>Staff workspace unavailable</strong>
          <p>{error}</p>
          <button type="button" onClick={() => void load()}>Retry</button>
        </div>
      </main>
    );
  }

  return <StaffShell workspace={workspace} refreshWorkspace={load} onWorkspaceChange={setWorkspace} />;
}

export default function StaffWorkspace() {
  return (
    <StaffAccessGuard>
      <ThemeProvider>
        <WorkspaceLoader />
      </ThemeProvider>
    </StaffAccessGuard>
  );
}
