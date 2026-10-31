import { Outlet } from 'react-router-dom';

export default function CompanyCEOContent({ workspace }) {
  return (
    <main id="company-ceo-content" className="company-ceo-content" tabIndex={-1}>
      <Outlet context={workspace} />
    </main>
  );
}
