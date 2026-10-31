import React, { Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { WorkspaceProvider } from './context/WorkspaceContext';
import { Toaster } from 'react-hot-toast';
import './App.css';

// Lazy load components
const MainPage = React.lazy(() => import('./pages/index'));

// Loading component
const LoadingSpinner = () => (
  <div style={{
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    height: '100vh',
    fontSize: '1.5rem'
  }}>
    Loading...
  </div>
);

function App() {
  return (
    <AuthProvider>
      <WorkspaceProvider>
        <Router>
          <div className="App">
            <Toaster
              position="top-right"
              toastOptions={{
                duration: 4000,
                style: {
                  background: '#363636',
                  color: '#fff',
                },
                success: {
                  duration: 3000,
                  iconTheme: {
                    primary: '#4ade80',
                    secondary: '#fff',
                  },
                },
                error: {
                  duration: 4000,
                  iconTheme: {
                    primary: '#ef4444',
                    secondary: '#fff',
                  },
                },
              }}
            />
            <Suspense fallback={<LoadingSpinner />}>
              <Routes>
                <Route path="/*" element={<MainPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Suspense>
          </div>
        </Router>
      </WorkspaceProvider>
    </AuthProvider>
  );
}

export default App;
