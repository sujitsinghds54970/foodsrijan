import { Outlet } from 'react-router-dom';

export default function StaffContent({ workspace, refreshWorkspace, onWorkspaceChange }) {
  return (
    <main id="manager-content" className="manager-content" tabIndex={-1}>
      <Outlet context={{ ...workspace, refreshWorkspace, onWorkspaceChange }} />
    </main>
  );
}
